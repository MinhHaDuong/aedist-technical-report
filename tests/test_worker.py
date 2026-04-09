"""Tests for the Worker base class and PadmeWorker."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aedist.schema import JobSpec, Method
from aedist.worker import OpenRouterWorker, PadmeWorker, Worker


def _make_job(
    job_id: str = "abc123",
    priority: int = 50,
    mode: str = "single",
    timeout_seconds: int = 600,
    model_filter: str | None = "openai/gpt-4o",
    corpus: str | None = None,
    followups: str | None = None,
    strategy: str | None = None,
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
        corpus=corpus,
        followups=followups,
        strategy=strategy,
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


def test_poll_priority_order(tmp_path: Path) -> None:
    """poll() returns the highest-priority job first."""
    jobs_root = tmp_path / "jobs"
    worker = Worker("w1", jobs_root=jobs_root)

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
    worker = _ConcreteWorker("w1", jobs_root=jobs_root)

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
    worker = _ConcreteWorker("w1", jobs_root=jobs_root)

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
    worker = _FailingWorker("w1", jobs_root=jobs_root)

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


def _canned_single_result():
    """Canned result dict from query_single_turn."""
    return {
        "content": "Plant A,coal,operational",
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 50, "completion_tokens": 100},
        "wall_seconds": 3.5,
    }


def _harness_patches(tmp_path):
    """Patch dict for all harness functions used in aedist.worker.

    Shared by lifecycle tests, PadmeWorker tests, and dispatch tests.
    """
    return {
        "make_client": MagicMock(return_value=MagicMock()),
        "load_models": MagicMock(return_value=[{"id": "qwen3:8b"}]),
        "query_single_turn": MagicMock(return_value=_canned_single_result()),
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
    """OpenRouterWorker uses empty worker_id to avoid filename prefix."""
    worker = OpenRouterWorker(jobs_root=tmp_path / "jobs")
    assert worker.worker_id == ""


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


# ---------------------------------------------------------------------------
# Mode dispatch tests (Ticket 0023)
# ---------------------------------------------------------------------------


def test_rag_job_dispatches_to_rag_pipeline(tmp_path: Path) -> None:
    """A job with mode=rag must call RAG query functions, not single-turn."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "doc1.md").write_text("Some corpus content")

    job = _make_job(
        mode="rag",
        corpus=str(corpus_dir),
        strategy="wholesale",
        model_filter="qwen3:8b",
    )
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        result = worker.execute(job)

    # RAG path should build system+user messages with corpus, not just user message
    call_args = patches["query_single_turn"].call_args
    messages = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("messages")
    assert len(messages) == 2  # system (corpus) + user (prompt)
    assert messages[0]["role"] == "system"
    assert "corpus" in messages[0]["content"].lower() or "Some corpus content" in messages[0]["content"]
    assert result["wall_seconds"] == 3.5


def test_multiturn_job_dispatches_to_multiturn(tmp_path: Path) -> None:
    """A job with mode=multiturn must run a multi-turn conversation."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")
    followups_file = tmp_path / "followups.txt"
    followups_file.write_text("What about gas plants?\nAny LNG?")

    job = _make_job(mode="multiturn", followups=str(followups_file), model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    mock_conv_result = {
        "turns": [{"role": "user", "content": "List thermal plants", "turn": 0}],
        "total_cost_usd": 0.01,
        "total_wall_seconds": 5.0,
        "context_overflow": False,
    }
    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        with patch("aedist.worker.run_conversation", return_value=mock_conv_result) as mock_run:
            result = worker.execute(job)

    mock_run.assert_called_once()
    assert result["wall_seconds"] == 5.0


def test_web_job_dispatches_to_web(tmp_path: Path, monkeypatch) -> None:
    """A job with mode=web must run web-augmented queries."""
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = _make_job(mode="web", model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    patches = _harness_patches(tmp_path)
    with patch("aedist.worker.run_web_searches", return_value=("web context", [])):
        with patch.multiple("aedist.worker", **patches):
            result = worker.execute(job)

    # Web path builds system message with web search context
    call_args = patches["query_single_turn"].call_args
    messages = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("messages")
    assert messages[0]["role"] == "system"
    assert result["wall_seconds"] == 3.5


def test_decomposed_job_dispatches_to_decomposed(tmp_path: Path) -> None:
    """A job with mode=decomposed must run decomposed sub-queries."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "doc1.md").write_text("Some corpus content")

    job = _make_job(mode="decomposed", corpus=str(corpus_dir), model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    mock_decomposed_result = {
        "strategy": "decomposed",
        "sub_queries": {},
        "merged_csv": "name,fuel\nPlant A,coal",
        "n_merged_plants": 1,
        "total_cost_usd": 0.03,
        "total_wall_seconds": 10.0,
        "total_usage": {"prompt_tokens": 150, "completion_tokens": 300},
    }
    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        with patch("aedist.worker.query_decomposed", return_value=mock_decomposed_result) as mock_dec:
            result = worker.execute(job)

    mock_dec.assert_called_once()
    assert result["wall_seconds"] == 10.0
    assert result["tokens_in"] == 150


def test_single_job_dispatches_to_single(tmp_path: Path) -> None:
    """A job with mode=single still calls query_single_turn."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = _make_job(mode="single", model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        result = worker.execute(job)

    patches["query_single_turn"].assert_called_once()
    assert result["wall_seconds"] == 3.5


def test_unknown_mode_raises(tmp_path: Path) -> None:
    """An unrecognized mode must raise, not silently fall back to single-turn."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    # We can't construct a JobSpec with an invalid enum, so test via internal dispatch
    job = _make_job(mode="single", model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    # Monkey-patch mode to an unknown value to test the dispatch guard
    object.__setattr__(job, "mode", "nonexistent_mode")

    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        with pytest.raises(ValueError, match="Unsupported mode"):
            worker.execute(job)


def test_dispatch_shared_between_padme_and_openrouter(tmp_path: Path) -> None:
    """PadmeWorker and OpenRouterWorker share the same dispatch logic."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "doc1.md").write_text("Some corpus content")

    job = _make_job(mode="rag", corpus=str(corpus_dir), strategy="wholesale", model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})

    for WorkerCls in [PadmeWorker, OpenRouterWorker]:
        worker = WorkerCls(jobs_root=tmp_path / f"jobs-{WorkerCls.__name__}")
        patches = _harness_patches(tmp_path)
        with patch.multiple("aedist.worker", **patches):
            result = worker.execute(job)
        # Both workers should dispatch RAG the same way
        call_args = patches["query_single_turn"].call_args
        messages = call_args[0][2] if len(call_args[0]) > 2 else call_args[1].get("messages")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"


def test_verification_job_raises_not_implemented(tmp_path: Path) -> None:
    """Verification mode requires special handling not available in worker dispatch."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = _make_job(mode="verification", model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        with pytest.raises(NotImplementedError, match="verification"):
            worker.execute(job)


def test_frontier_job_dispatches_like_single(tmp_path: Path) -> None:
    """Frontier mode dispatches through query_single_turn like single mode."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = _make_job(mode="frontier", model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        result = worker.execute(job)

    patches["query_single_turn"].assert_called_once()
    assert result["wall_seconds"] == 3.5


def test_sourced_job_dispatches_like_single(tmp_path: Path) -> None:
    """Sourced mode dispatches through query_single_turn (same as single)."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = _make_job(mode="sourced", model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        result = worker.execute(job)

    patches["query_single_turn"].assert_called_once()
    assert result["wall_seconds"] == 3.5


# ---------------------------------------------------------------------------
# pool_label / filename prefix tests (Ticket 0023 review fix 1)
# ---------------------------------------------------------------------------


def test_padme_pool_label_is_padme(tmp_path: Path) -> None:
    """PadmeWorker uses 'padme' as pool_label, producing prefixed filenames."""
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")
    assert worker.worker_id == "padme"


def test_openrouter_pool_label_is_empty(tmp_path: Path) -> None:
    """OpenRouterWorker uses empty pool_label, producing unprefixed filenames."""
    worker = OpenRouterWorker(jobs_root=tmp_path / "jobs")
    assert worker.worker_id == ""


# ---------------------------------------------------------------------------
# Web mode without API key must raise (Ticket 0023 review fix 2)
# ---------------------------------------------------------------------------


def test_web_mode_raises_without_tavily_key(tmp_path: Path, monkeypatch) -> None:
    """Web mode must raise RuntimeError when TAVILY_API_KEY is unset."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")

    job = _make_job(mode="web", model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
            worker.execute(job)


# ---------------------------------------------------------------------------
# RAG SystemExit catch (Ticket 0023 review fix 3)
# ---------------------------------------------------------------------------


def test_rag_empty_corpus_raises_runtime_error(tmp_path: Path) -> None:
    """RAG mode converts SystemExit from load_corpus into RuntimeError."""
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("List thermal plants")
    corpus_dir = tmp_path / "empty_corpus"
    corpus_dir.mkdir()
    # No .md files => load_corpus raises SystemExit

    job = _make_job(mode="rag", corpus=str(corpus_dir), model_filter="qwen3:8b")
    job = job.model_copy(update={"prompt": str(prompt_file)})
    worker = PadmeWorker(jobs_root=tmp_path / "jobs")

    patches = _harness_patches(tmp_path)
    with patch.multiple("aedist.worker", **patches):
        with pytest.raises(RuntimeError, match="RAG corpus load failed"):
            worker.execute(job)
