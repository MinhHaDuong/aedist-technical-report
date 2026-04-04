"""Tests for aedist.observer — lease monitoring and job board status."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aedist.observer import find_expired, requeue_expired, status_report


def _make_running(jobs_root: Path, job_id: str, expiry: datetime) -> Path:
    """Create a running job file with a lease timestamp."""
    running_dir = jobs_root / "running"
    running_dir.mkdir(parents=True, exist_ok=True)
    expiry_str = expiry.strftime("%Y%m%dT%H%M%SZ")
    path = running_dir / f"{job_id}-lease-{expiry_str}.yaml"
    path.write_text(f"job_id: {job_id}\n")
    return path


def _make_pending(jobs_root: Path, job_id: str) -> Path:
    """Create a pending job file."""
    pending_dir = jobs_root / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    path = pending_dir / f"050-{job_id}.yaml"
    path.write_text(f"job_id: {job_id}\n")
    return path


def _make_done(jobs_root: Path, job_id: str) -> Path:
    """Create a done job file."""
    done_dir = jobs_root / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    path = done_dir / f"{job_id}.yaml"
    path.write_text(f"job_id: {job_id}\n")
    return path


class TestFindExpired:
    def test_no_running_dir(self, tmp_path):
        assert find_expired(tmp_path) == []

    def test_no_expired(self, tmp_path):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        _make_running(tmp_path, "job1", future)
        assert find_expired(tmp_path) == []

    def test_detects_expired(self, tmp_path):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        _make_running(tmp_path, "job1", past)
        expired = find_expired(tmp_path)
        assert len(expired) == 1
        assert expired[0][0] == "job1"

    def test_mixed_expired_and_active(self, tmp_path):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        _make_running(tmp_path, "expired-job", past)
        _make_running(tmp_path, "active-job", future)
        expired = find_expired(tmp_path)
        assert len(expired) == 1
        assert expired[0][0] == "expired-job"


class TestRequeueExpired:
    def test_requeues_to_pending(self, tmp_path):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        _make_running(tmp_path, "stale", past)

        requeued = requeue_expired(tmp_path)

        assert requeued == ["stale"]
        assert not list((tmp_path / "running").glob("*.yaml"))
        assert list((tmp_path / "pending").glob("*stale*"))

    def test_no_expired_to_requeue(self, tmp_path):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        _make_running(tmp_path, "active", future)

        requeued = requeue_expired(tmp_path)
        assert requeued == []
        assert list((tmp_path / "running").glob("*.yaml"))


class TestStatusReport:
    def test_empty_board(self, tmp_path):
        report = status_report(tmp_path)
        assert report["counts"] == {"pending": 0, "running": 0, "done": 0, "failed": 0}
        assert report["expired_leases"] == 0

    def test_counts_all_dirs(self, tmp_path):
        _make_pending(tmp_path, "p1")
        _make_pending(tmp_path, "p2")
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        _make_running(tmp_path, "r1", future)
        _make_done(tmp_path, "d1")

        report = status_report(tmp_path)
        assert report["counts"]["pending"] == 2
        assert report["counts"]["running"] == 1
        assert report["counts"]["done"] == 1
        assert report["counts"]["failed"] == 0

    def test_reports_expired(self, tmp_path):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        _make_running(tmp_path, "stale", past)

        report = status_report(tmp_path)
        assert report["expired_leases"] == 1
        assert "stale" in report["expired_jobs"]
