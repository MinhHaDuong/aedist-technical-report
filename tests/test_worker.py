"""Tests for the Worker base class and PadmeWorker."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from aedist.schema import JobSpec, Method, WorkerPool
from aedist.worker import OpenRouterWorker, PadmeWorker, Worker


def _make_job(
    job_id: str = "abc123",
    priority: int = 50,
    mode: str = "single",
    timeout_seconds: int = 600,
    model_filter: str | None = "openai/gpt-4o",
) -> JobSpec:
    """Create a minimal JobSpec for testing."""
    return JobSpec(
        job_id=job_id,
        priority=priority,
        mode=Method(mode),
        prompt="prompts/test.txt",
        models_file="models.yaml",
        model_filter=model_filter,
        output_dir="outputs/test",
        timeout_seconds=timeout_seconds,
    )


def _write_pending(jobs_root: Path, job: JobSpec) -> Path:
    """Write a job's YAML to the pending directory and return the path."""
    filename = f"{job.priority:03d}-{job.job_id}.yaml"
    path = jobs_root / "pending" / filename
    path.write_text(job.to_yaml())
    return path


class _ConcreteWorker(Worker):
    """Concrete subclass that returns a canned result."""

    def __init__(self, *args, result: dict | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.canned_result = result or {
            "result_file": "outputs/test/result.json",
            "wall_seconds": 12.5,
            "cost_usd": 0.03,
            "tokens_in": 1000,
            "tokens_out": 500,
        }

    def execute(self, job: JobSpec) -> dict:
        return self.canned_result


# -- Tests --------------------------------------------------------------------


def test_poll_empty(tmp_path: Path) -> None:
    """poll() returns None when pending/ is empty."""
    worker = Worker("w1", jobs_root=tmp_path / "jobs")
    assert worker.poll() is None


def test_poll_filters_by_pool(tmp_path: Path) -> None:
    """poll() only returns jobs matching the worker's pool."""
    jobs_root = tmp_path / "jobs"
    padme_worker = Worker("padme", jobs_root=jobs_root)
    or_worker = Worker("openrouter", jobs_root=jobs_root)

    or_job = _make_job(job_id="or-job")  # default pool = openrouter
    _write_pending(jobs_root, or_job)

    assert padme_worker.poll() is None
    assert or_worker.poll() is not None


def test_poll_priority_order(tmp_path: Path) -> None:
    """poll() returns the highest-priority job first."""
    jobs_root = tmp_path / "jobs"
    worker = Worker("openrouter", jobs_root=jobs_root)

    low = _make_job(job_id="job-low", priority=10)
    mid = _make_job(job_id="job-mid", priority=50)
    high = _make_job(job_id="job-high", priority=90)

    _write_pending(jobs_root, low)
    _write_pending(jobs_root, mid)
    _write_pending(jobs_root, high)

    result = worker.poll()
    assert result is not None
    assert result.job_id == "job-high"
    assert result.priority == 90


def test_acquire_renames_file(tmp_path: Path) -> None:
    """acquire() moves the file from pending/ to running/ with lease timestamp."""
    jobs_root = tmp_path / "jobs"
    worker = Worker("w1", jobs_root=jobs_root)

    job = _make_job(job_id="acq-test")
    pending_path = _write_pending(jobs_root, job)

    worker.acquire(job)

    assert not pending_path.exists()
    running_files = list((jobs_root / "running").glob("acq-test-lease-*.yaml"))
    assert len(running_files) == 1


def test_acquire_lease_info(tmp_path: Path) -> None:
    """acquire() returns a LeaseInfo with correct fields."""
    jobs_root = tmp_path / "jobs"
    worker = Worker("w1", jobs_root=jobs_root)

    job = _make_job(job_id="lease-test", timeout_seconds=300)
    _write_pending(jobs_root, job)

    lease = worker.acquire(job)

    assert lease.job_id == "lease-test"
    assert lease.worker_id == "w1"
    assert lease.expiry_time > lease.start_time
    delta = (lease.expiry_time - lease.start_time).total_seconds()
    assert 299 <= delta <= 301


def test_complete_moves_to_done(tmp_path: Path) -> None:
    """complete() moves the running file to done/."""
    jobs_root = tmp_path / "jobs"
    worker = Worker("w1", jobs_root=jobs_root)

    job = _make_job(job_id="done-test")
    _write_pending(jobs_root, job)
    worker.acquire(job)

    result = {"result_file": "out.json", "wall_seconds": 5.0}
    worker.complete(job, result)

    assert (jobs_root / "done" / "done-test.yaml").exists()
    assert not list((jobs_root / "running").glob("done-test-lease-*.yaml"))


def test_complete_returns_runrecord(tmp_path: Path) -> None:
    """complete() returns a RunRecord with correct method and model."""
    jobs_root = tmp_path / "jobs"
    worker = Worker("w1", jobs_root=jobs_root)

    job = _make_job(job_id="rr-test", model_filter="openai/gpt-4o")
    _write_pending(jobs_root, job)
    worker.acquire(job)

    result = {
        "result_file": "out.json",
        "wall_seconds": 10.0,
        "cost_usd": 0.05,
        "tokens_in": 2000,
        "tokens_out": 800,
    }
    record = worker.complete(job, result)

    assert record.method == Method.SINGLE
    assert record.method_params.model == "openai/gpt-4o"
    assert record.resource_use.wall_s == 10.0
    assert record.resource_use.cost_usd == 0.05
    assert record.resource_use.tokens_in == 2000
    assert record.resource_use.tokens_out == 800
    assert record.result_file == "out.json"


def test_fail_moves_to_failed(tmp_path: Path) -> None:
    """fail() moves the running file to failed/."""
    jobs_root = tmp_path / "jobs"
    worker = Worker("w1", jobs_root=jobs_root)

    job = _make_job(job_id="fail-test")
    _write_pending(jobs_root, job)
    worker.acquire(job)

    worker.fail(job, RuntimeError("boom"))

    assert (jobs_root / "failed" / "fail-test.yaml").exists()
    assert not list((jobs_root / "running").glob("fail-test-lease-*.yaml"))


def test_fail_writes_error_log(tmp_path: Path) -> None:
    """fail() writes an .error.txt file with the error message."""
    jobs_root = tmp_path / "jobs"
    worker = Worker("w1", jobs_root=jobs_root)

    job = _make_job(job_id="err-test")
    _write_pending(jobs_root, job)
    worker.acquire(job)

    worker.fail(job, RuntimeError("something broke"))

    error_file = jobs_root / "failed" / "err-test.error.txt"
    assert error_file.exists()
    content = error_file.read_text()
    assert "something broke" in content


def test_full_lifecycle(tmp_path: Path) -> None:
    """Full lifecycle: poll -> acquire -> execute -> complete."""
    jobs_root = tmp_path / "jobs"
    worker = _ConcreteWorker("openrouter", jobs_root=jobs_root)

    job = _make_job(job_id="lifecycle", priority=75)
    _write_pending(jobs_root, job)

    # poll
    polled = worker.poll()
    assert polled is not None
    assert polled.job_id == "lifecycle"

    # acquire
    lease = worker.acquire(polled)
    assert lease.job_id == "lifecycle"
    assert not list((jobs_root / "pending").glob("*lifecycle*"))
    assert list((jobs_root / "running").glob("lifecycle-lease-*.yaml"))

    # execute + complete
    result = worker.execute(polled)
    record = worker.complete(polled, result)

    assert (jobs_root / "done" / "lifecycle.yaml").exists()
    assert not list((jobs_root / "running").glob("lifecycle-lease-*.yaml"))
    assert record.method == Method.SINGLE
    assert record.method_params.model == "openai/gpt-4o"
    assert record.resource_use.wall_s == 12.5


def test_run_one_success(tmp_path: Path) -> None:
    """run_one() completes the full lifecycle and returns a RunRecord."""
    jobs_root = tmp_path / "jobs"
    worker = _ConcreteWorker("openrouter", jobs_root=jobs_root)

    job = _make_job(job_id="runone-ok", priority=50)
    _write_pending(jobs_root, job)

    record = worker.run_one()

    assert record is not None
    assert record.method == Method.SINGLE
    assert record.resource_use.wall_s == 12.5
    assert (jobs_root / "done" / "runone-ok.yaml").exists()
    assert not list((jobs_root / "pending").iterdir())


def test_run_one_empty(tmp_path: Path) -> None:
    """run_one() returns None when no jobs are pending."""
    worker = _ConcreteWorker("w1", jobs_root=tmp_path / "jobs")
    assert worker.run_one() is None


class _FailingWorker(Worker):
    """Worker whose execute() always raises."""

    def execute(self, job: JobSpec) -> dict:
        raise RuntimeError("execution failed")


def test_run_one_failure(tmp_path: Path) -> None:
    """run_one() catches execute errors, moves job to failed/, returns None."""
    jobs_root = tmp_path / "jobs"
    worker = _FailingWorker("openrouter", jobs_root=jobs_root)

    job = _make_job(job_id="runone-fail")
    _write_pending(jobs_root, job)

    record = worker.run_one()

    assert record is None
    assert (jobs_root / "failed" / "runone-fail.yaml").exists()
    error_txt = (jobs_root / "failed" / "runone-fail.error.txt").read_text()
    assert "execution failed" in error_txt


# ---------------------------------------------------------------------------
# PadmeWorker tests
# ---------------------------------------------------------------------------


def test_padme_worker_id(tmp_path: Path) -> None:
    """PadmeWorker always has worker_id='padme'."""
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")
    assert worker.worker_id == "padme"


def test_padme_worker_base_url(tmp_path: Path) -> None:
    """PadmeWorker uses the Ollama base URL by default."""
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")
    assert "11434" in worker.base_url


def test_padme_worker_custom_base_url(tmp_path: Path) -> None:
    """PadmeWorker accepts a custom base URL."""
    worker = PadmeWorker(jobs_root=tmp_path / "jobs", base_url="http://gpu:8080/v1")
    assert worker.base_url == "http://gpu:8080/v1"


def _harness_patches(tmp_path):
    """Context manager dict for patching harness functions in aedist.worker."""
    return {
        "make_client": MagicMock(),
        "load_models": MagicMock(return_value=[{"id": "qwen3:8b"}]),
        "query_single_turn": MagicMock(
            return_value={
                "content": "Plant A,coal,operational",
                "finish_reason": "stop",
                "usage": {"prompt_tokens": 50, "completion_tokens": 100},
                "wall_seconds": 3.5,
            }
        ),
        "compute_cost": MagicMock(return_value=0.0),
        "model_metadata": MagicMock(return_value={}),
        "save_json": MagicMock(),
        "should_skip": MagicMock(return_value=False),
        "output_path": MagicMock(return_value=tmp_path / "out" / "r.json"),
    }


def test_padme_worker_execute(tmp_path: Path) -> None:
    """PadmeWorker.execute() calls harness functions correctly."""
    jobs_root = tmp_path / "jobs"
    worker = PadmeWorker(jobs_root=jobs_root)

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = JobSpec(
        job_id="padme-test",
        priority=50,
        mode=Method.SINGLE,
        prompt=str(prompt_file),
        models_file="models.yaml",
        model_filter="qwen3:8b",
        output_dir=str(tmp_path / "out"),
        repeat=1,
        budget_usd=1.0,
    )

    with patch.multiple("aedist.worker", **_harness_patches(tmp_path)):
        result = worker.execute(job)

    assert result["wall_seconds"] == 3.5
    assert result["tokens_in"] == 50
    assert result["tokens_out"] == 100


def test_padme_full_lifecycle(tmp_path: Path) -> None:
    """PadmeWorker full lifecycle: poll -> run_one with mocked harness."""
    jobs_root = tmp_path / "jobs"
    worker = PadmeWorker(jobs_root=jobs_root)

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = JobSpec(
        job_id="padme-lc",
        priority=50,
        mode=Method.SINGLE,
        prompt=str(prompt_file),
        models_file="models.yaml",
        model_filter="qwen3:8b",
        output_dir=str(tmp_path / "out"),
        repeat=1,
        budget_usd=1.0,
        worker_pool=WorkerPool.PADME,
    )
    _write_pending(jobs_root, job)

    with patch.multiple("aedist.worker", **_harness_patches(tmp_path)):
        record = worker.run_one()

    assert record is not None
    assert record.method == Method.SINGLE
    assert (jobs_root / "done" / "padme-lc.yaml").exists()


# ---------------------------------------------------------------------------
# OpenRouterWorker tests
# ---------------------------------------------------------------------------


def test_openrouter_worker_id(tmp_path: Path) -> None:
    """OpenRouterWorker always has worker_id='openrouter'."""
    worker = OpenRouterWorker(jobs_root=tmp_path / "jobs")
    assert worker.worker_id == "openrouter"


def test_openrouter_worker_execute(tmp_path: Path) -> None:
    """OpenRouterWorker.execute() runs a single query."""
    jobs_root = tmp_path / "jobs"
    worker = OpenRouterWorker(jobs_root=jobs_root)

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = JobSpec(
        job_id="or-test",
        priority=50,
        mode=Method.SINGLE,
        prompt=str(prompt_file),
        models_file="models.yaml",
        model_filter="qwen3:8b",
        output_dir=str(tmp_path / "out"),
        repeat=1,
        budget_usd=10.0,
    )

    with patch.multiple("aedist.worker", **_harness_patches(tmp_path)):
        result = worker.execute(job)

    # 1 model x 1 run = 1 query
    assert result["wall_seconds"] == 3.5
    assert result["tokens_in"] == 50
    assert result["tokens_out"] == 100


def test_openrouter_full_lifecycle(tmp_path: Path) -> None:
    """OpenRouterWorker full lifecycle: poll -> run_one with mocked harness."""
    jobs_root = tmp_path / "jobs"
    worker = OpenRouterWorker(jobs_root=jobs_root)

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = JobSpec(
        job_id="or-lc",
        priority=50,
        mode=Method.SINGLE,
        prompt=str(prompt_file),
        models_file="models.yaml",
        model_filter="qwen3:8b",
        output_dir=str(tmp_path / "out"),
        repeat=1,
        budget_usd=10.0,
    )
    _write_pending(jobs_root, job)

    with patch.multiple("aedist.worker", **_harness_patches(tmp_path)):
        record = worker.run_one()

    assert record is not None
    assert record.method == Method.SINGLE
    assert (jobs_root / "done" / "or-lc.yaml").exists()
