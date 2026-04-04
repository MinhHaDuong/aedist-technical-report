"""Base Worker class with lease semantics for the job board.

Workers poll for pending jobs, acquire exclusive leases via atomic file
renames, execute the query pipeline, and write results to done/ or failed/.
"""

from __future__ import annotations

import re
import signal
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .schema import (
    JobSpec,
    LeaseInfo,
    Method,
    MethodParams,
    ResourceUse,
    RunRecord,
)

_PENDING_RE = re.compile(r"^(\d{3})-(.+)\.yaml$")


class Worker:
    """Base worker that implements the poll-acquire-execute-complete lifecycle."""

    def __init__(self, worker_id: str, jobs_root: Path = Path("jobs")) -> None:
        self.worker_id = worker_id
        self.jobs_root = jobs_root
        for subdir in ("pending", "running", "done", "failed"):
            (self.jobs_root / subdir).mkdir(parents=True, exist_ok=True)

    # -- polling ---------------------------------------------------------------

    def poll(self) -> JobSpec | None:
        """Scan pending/ for the highest-priority job.

        Returns the highest-priority JobSpec, or None if the queue is empty.
        Priority is sorted descending (higher number first); ties broken
        by job_id lexicographically (FIFO within same priority).
        """
        pending_dir = self.jobs_root / "pending"
        candidates: list[tuple[int, str, Path]] = []
        for path in pending_dir.glob("*.yaml"):
            m = _PENDING_RE.match(path.name)
            if m:
                priority = int(m.group(1))
                job_id = m.group(2)
                candidates.append((priority, job_id, path))
        if not candidates:
            return None
        # Sort: highest priority first, then job_id ascending (FIFO)
        candidates.sort(key=lambda t: (-t[0], t[1]))
        best = candidates[0]
        text = best[2].read_text()
        return JobSpec.from_yaml(text)

    # -- lease acquisition -----------------------------------------------------

    def acquire(self, job: JobSpec) -> LeaseInfo:
        """Atomically move a pending job to running/ with a lease timestamp.

        Uses Path.rename() for POSIX atomicity.
        """
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=job.timeout_seconds)
        expiry_str = expiry.strftime("%Y%m%dT%H%M%SZ")
        src = self._find_pending_file(job)
        dst = self.jobs_root / "running" / f"{job.job_id}-lease-{expiry_str}.yaml"
        src.rename(dst)
        return LeaseInfo(
            job_id=job.job_id,
            worker_id=self.worker_id,
            start_time=now,
            expiry_time=expiry,
        )

    # -- execution (abstract) --------------------------------------------------

    def execute(self, job: JobSpec) -> dict:
        """Subclasses override to call appropriate query pipeline based on job.mode."""
        raise NotImplementedError

    # -- completion ------------------------------------------------------------

    def complete(self, job: JobSpec, result: dict) -> RunRecord:
        """Move the running file to done/ and return a RunRecord."""
        src = self._find_running_file(job)
        dst = self.jobs_root / "done" / f"{job.job_id}.yaml"
        src.rename(dst)

        record = RunRecord(
            method=Method(job.mode),
            method_params=MethodParams(model=job.model_filter or "unknown"),
            resource_use=ResourceUse(
                wall_s=result.get("wall_seconds"),
                cost_usd=result.get("cost_usd"),
                tokens_in=result.get("tokens_in"),
                tokens_out=result.get("tokens_out"),
            ),
            result_file=result.get("result_file"),
        )
        return record

    # -- failure ---------------------------------------------------------------

    def fail(self, job: JobSpec, error: Exception) -> None:
        """Move the running file to failed/ and write an error log."""
        src = self._find_running_file(job)
        dst = self.jobs_root / "failed" / f"{job.job_id}.yaml"
        src.rename(dst)
        error_file = self.jobs_root / "failed" / f"{job.job_id}.error.txt"
        error_file.write_text(
            "".join(traceback.format_exception(type(error), error, error.__traceback__))
            or str(error)
        )

    # -- convenience -----------------------------------------------------------

    def run_one(self) -> RunRecord | None:
        """Poll, acquire, execute, and complete/fail a single job.

        Returns a RunRecord on success, or None if no job was available.
        Uses signal.alarm for timeout enforcement on POSIX systems.
        """
        job = self.poll()
        if job is None:
            return None
        self.acquire(job)

        def _timeout_handler(signum: int, frame: object) -> None:
            raise TimeoutError(
                f"Job {job.job_id} exceeded timeout of {job.timeout_seconds}s"
            )

        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        try:
            signal.alarm(job.timeout_seconds)
            result = self.execute(job)
            signal.alarm(0)
            return self.complete(job, result)
        except Exception as exc:
            signal.alarm(0)
            self.fail(job, exc)
            return None
        finally:
            signal.signal(signal.SIGALRM, old_handler)

    # -- helpers ---------------------------------------------------------------

    def _find_pending_file(self, job: JobSpec) -> Path:
        """Find the pending file for a given job."""
        matches = list(
            self.jobs_root.glob(f"pending/*-{job.job_id}.yaml")
        )
        if not matches:
            msg = f"No pending file found for job {job.job_id}"
            raise FileNotFoundError(msg)
        return matches[0]

    def _find_running_file(self, job: JobSpec) -> Path:
        """Find the running file for a given job."""
        matches = list(
            self.jobs_root.glob(f"running/{job.job_id}-lease-*.yaml")
        )
        if not matches:
            msg = f"No running file found for job {job.job_id}"
            raise FileNotFoundError(msg)
        return matches[0]
