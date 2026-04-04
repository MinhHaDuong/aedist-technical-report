"""Observer for lease monitoring and job board status.

Scans job directories, detects stale leases, requeues expired jobs,
and reports pipeline status. Read-only by default.

Usage:
    python -m aedist.observer                  # status report
    python -m aedist.observer --requeue        # also requeue expired leases
    python -m aedist.observer --json           # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_LEASE_RE = re.compile(r"^(.+)-lease-(\d{8}T\d{6}Z)\.yaml$")


def _parse_expiry(filename: str) -> tuple[str, datetime] | None:
    """Extract job_id and expiry from a running/ filename."""
    m = _LEASE_RE.match(filename)
    if not m:
        return None
    job_id = m.group(1)
    expiry = datetime.strptime(m.group(2), "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )
    return job_id, expiry


def find_expired(
    jobs_root: Path, now: datetime | None = None,
) -> list[tuple[str, Path, datetime]]:
    """Find running jobs with expired leases.

    Returns list of (job_id, path, expiry) for expired jobs.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    expired = []
    running_dir = jobs_root / "running"
    if not running_dir.exists():
        return expired
    for path in running_dir.glob("*.yaml"):
        parsed = _parse_expiry(path.name)
        if parsed is None:
            continue
        job_id, expiry = parsed
        if now > expiry:
            expired.append((job_id, path, expiry))
    return expired


def requeue_expired(
    jobs_root: Path, now: datetime | None = None,
) -> list[str]:
    """Move expired running jobs back to pending/.

    Returns list of requeued job IDs.
    """
    expired = find_expired(jobs_root, now)
    requeued = []
    pending_dir = jobs_root / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    for job_id, path, _expiry in expired:
        dst = pending_dir / f"000-{job_id}.yaml"
        path.rename(dst)
        requeued.append(job_id)
        log.info("Requeued expired job: %s", job_id)
    return requeued


def status_report(jobs_root: Path) -> dict:
    """Generate a status report of the job board."""
    dirs = ("pending", "running", "done", "failed")
    counts: dict[str, int] = {}
    for d in dirs:
        p = jobs_root / d
        counts[d] = len(list(p.glob("*.yaml"))) if p.exists() else 0

    now = datetime.now(timezone.utc)
    expired = find_expired(jobs_root, now)

    return {
        "counts": counts,
        "expired_leases": len(expired),
        "expired_jobs": [job_id for job_id, _, _ in expired],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Monitor job board and detect expired leases"
    )
    parser.add_argument(
        "--jobs-root", type=Path, default=Path("jobs"),
        help="Root directory for job board (default: jobs/)",
    )
    parser.add_argument(
        "--requeue", action="store_true",
        help="Move expired running jobs back to pending/",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output status as JSON",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.requeue:
        requeued = requeue_expired(args.jobs_root)
        if requeued:
            log.info("Requeued %d expired jobs: %s", len(requeued), requeued)
        else:
            log.info("No expired leases to requeue.")

    report = status_report(args.jobs_root)

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        c = report["counts"]
        log.info("Job board: %s", args.jobs_root)
        log.info("  Pending:  %d", c.get("pending", 0))
        log.info("  Running:  %d", c.get("running", 0))
        log.info("  Done:     %d", c.get("done", 0))
        log.info("  Failed:   %d", c.get("failed", 0))
        if report["expired_leases"]:
            log.info("  Expired:  %d — %s", report["expired_leases"],
                     report["expired_jobs"])


if __name__ == "__main__":
    main()
