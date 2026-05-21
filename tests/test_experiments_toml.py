"""Live experiments.toml audit (ticket 0139).

Loads every ``[sweeps.*]`` section through ``JobSpec.from_toml_section`` to
catch silent-drop regressions before a sweep is launched. Sweeps routed
externally (verification, fusion) are exempted explicitly with a comment so
the exemption set stays auditable.

This is the test that would have caught the original ``seed`` silent-drop
bug — a sweep config carrying a key that JobSpec doesn't declare would now
raise ValidationError under ``extra='forbid'``.
"""

import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from aedist.schema import JobSpec

_REPO_ROOT = Path(__file__).resolve().parent.parent
_EXPERIMENTS_TOML = _REPO_ROOT / "experiments" / "experiments.toml"

# Sweeps that bypass manager.generate / JobSpec.from_toml_section. Each entry
# here has a comment justifying why it is exempt.
_EXTERNALLY_ROUTED_SWEEPS = {
    # query_verification.py drives these directly; mode/models_file are not
    # required because verification is N>1 model-by-model verification, not
    # a single dispatched job. Verification mode raises NotImplementedError
    # in worker.execute.
    "sweep_rag_verification",
    "sweep_rag_verification_poc",
    "sweep_rag_verification_multi",
    # prototype_v1_fusion.py / worker._execute_fusion read fusion sweep
    # config out of job.method_params.extra, not from JobSpec fields. The
    # singular ``model`` and ``provider`` keys here are intentional.
    "sweep_fusion",
    "sweep_fusion_dev",
}


def _load_sweeps() -> dict:
    with open(_EXPERIMENTS_TOML, "rb") as f:
        return tomllib.load(f).get("sweeps", {})


def test_all_manager_routed_sweeps_load():
    """Every ``[sweeps.*]`` section that flows through manager.generate must
    load cleanly under JobSpec's ``extra='forbid'`` schema. New silent-drop
    bugs land here loudly instead of disappearing into the void.
    """
    sweeps = _load_sweeps()
    failures = []
    for name, section in sweeps.items():
        if name in _EXTERNALLY_ROUTED_SWEEPS:
            continue
        if not isinstance(section, dict):
            continue
        try:
            JobSpec.from_toml_section(dict(section))
        except ValidationError as exc:
            failures.append(f"{name}: {exc}")
    assert not failures, "JobSpec load failures (ticket 0139):\n" + "\n\n".join(failures)


@pytest.mark.parametrize("sweep_name", sorted(_EXTERNALLY_ROUTED_SWEEPS))
def test_externally_routed_sweep_still_present(sweep_name: str):
    """Exempted sweeps must still exist; otherwise we're carrying a stale
    exemption. If a sweep was deleted, drop it from
    ``_EXTERNALLY_ROUTED_SWEEPS`` in the same PR.
    """
    sweeps = _load_sweeps()
    assert sweep_name in sweeps, (
        f"Stale exemption: {sweep_name!r} is in _EXTERNALLY_ROUTED_SWEEPS "
        f"but no such sweep exists in experiments.toml."
    )
