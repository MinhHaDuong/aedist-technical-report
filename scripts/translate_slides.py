#!/usr/bin/env python3
"""Translate the English slide deck (source of truth) into the French deck.

`slides/slides-en.tex` is the single source of truth for slide prose; the
French deck `slides/slides.tex` is a derived translation. This script
replaces the manual "align FR on EN" loop by calling the `claude` CLI to
translate prose only, preserving every byte of LaTeX scaffolding.

Safety is split into two tiers that must never be conflated:

- Tier 1 (work-loss insurance): before any claude call or write, check that
  the prior FR is git-recoverable and that EN is not older than FR. All git
  checks are fail-closed — any git error aborts.
- Tier 2 (correctness): after claude returns, before the write, verify the
  candidate looks like the deck, is not truncated, and is structurally
  identical to EN (same frames, figure paths, includes, labels). A failed
  guard leaves `slides.tex` untouched.

Direction is hardcoded EN -> FR. There is intentionally no --from/--to: the
only path this script ever writes is `slides.tex`; `slides-en.tex` is
read-only here. The script never commits and never clobbers; the human
reviews `git diff` and commits.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_TIMEOUT = 600.0
LENGTH_FLOOR = 0.8  # FR byte length must be >= this fraction of EN's.

# Repo-relative; resolved against the git toplevel in main() so the script is
# cwd-independent. These are the ONLY paths the script touches.
SLIDES_EN = "slides/slides-en.tex"
SLIDES_FR = "slides/slides.tex"

TRANSLATION_PROMPT = (
    "You are a professional translator for an academic LaTeX Beamer deck.\n"
    "Translate ONLY the human-readable prose from English to French.\n"
    "Preserve ALL LaTeX verbatim and byte-for-byte: command names, environment\n"
    "names, optional/mandatory arguments, \\includegraphics paths, \\input and\n"
    "\\InputIfFileExists paths, \\label and \\ref keys, macro names, \\definecolor\n"
    "definitions, lengths, and ALL comments (including disabled \\iffalse ... \\fi\n"
    "blocks and their contents).\n"
    "Do not add, drop, reorder, or merge frames. Do not translate label/ref keys\n"
    "or file paths. Keep the same number of \\begin{frame}/\\end{frame}.\n"
    "Output the complete .tex document and NOTHING else: no markdown code fences,\n"
    "no leading or trailing commentary, no explanation."
)


class TranslationAborted(Exception):  # noqa: N818 — name fixed by ticket 0363 test contract
    """A Tier-1 or Tier-2 guard tripped; the FR deck is left untouched."""


class GitError(Exception):
    """A git invocation failed or git was unavailable (fail-closed)."""


# ---------------------------------------------------------------------------
# Git helpers (fail-closed, repo-root-relative)
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: str | None = None) -> str:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True
        )
    except FileNotFoundError as exc:
        raise GitError("git not found on PATH") from exc
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {(proc.stderr or '').strip()}")
    return proc.stdout


def _repo_root() -> Path:
    return Path(_git(["rev-parse", "--show-toplevel"]).strip())


def _relpath(path: str | Path, root: Path) -> str:
    return str(Path(path).resolve().relative_to(root.resolve()))


def _commit_time(rel: str, root: Path) -> int | None:
    out = _git(["log", "-1", "--format=%ct", "--", rel], cwd=str(root)).strip()
    return int(out) if out else None


def fr_is_committed(path: str | Path) -> bool:
    """True iff FR is a tracked file with no uncommitted changes.

    Untracked (`??`) or modified -> False (overwriting would lose work with
    no git recovery). Any git error propagates as GitError (fail-closed).
    """
    root = _repo_root()
    rel = _relpath(path, root)
    if _git(["status", "--porcelain", "--", rel], cwd=str(root)).strip():
        return False  # modified or untracked
    return bool(_git(["ls-files", "--", rel], cwd=str(root)).strip())


def en_at_least_as_new(en: str | Path, fr: str | Path) -> bool:
    """True unless FR's last commit is strictly newer than EN's.

    Uses git commit timestamps, not filesystem mtimes (a fresh clone stamps
    every file with checkout time). Edge cases that mean "EN is newest, so
    translating is safe": EN has uncommitted edits (we translate the working
    tree), EN was never committed, or FR was never committed.
    """
    root = _repo_root()
    en_rel = _relpath(en, root)
    fr_rel = _relpath(fr, root)
    if _git(["status", "--porcelain", "--", en_rel], cwd=str(root)).strip():
        return True  # EN dirty: working tree is newer than any commit
    en_ct = _commit_time(en_rel, root)
    if en_ct is None:
        return True  # EN never committed: nothing older to clobber
    fr_ct = _commit_time(fr_rel, root)
    if fr_ct is None:
        return True  # FR never committed: cannot be "newer"
    return en_ct >= fr_ct


# ---------------------------------------------------------------------------
# claude CLI wrapper (no shell, stdin, timeout)
# ---------------------------------------------------------------------------


def run_claude(document: str, *, model: str = DEFAULT_MODEL, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Translate `document` via `claude --print`; return the raw model text.

    The EN document is passed on stdin (never interpolated into a shell
    string); the translation instructions ride on --append-system-prompt.
    `--bare` skips hooks/CLAUDE.md discovery; --allowedTools "" disallows
    every tool so the model only translates.
    """
    cmd = [
        "claude",
        "--print",
        "--bare",
        "--model",
        model,
        "--output-format",
        "json",
        "--allowedTools",
        "",
        "--no-session-persistence",
        "--append-system-prompt",
        TRANSLATION_PROMPT,
    ]
    try:
        proc = subprocess.run(
            cmd, input=document, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError as exc:
        raise TranslationAborted("claude CLI not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise TranslationAborted(f"claude CLI timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise TranslationAborted(
            f"claude CLI exited {proc.returncode}: {(proc.stderr or '').strip()[:500]}"
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise TranslationAborted(f"claude CLI returned non-JSON output: {exc}") from exc
    if data.get("is_error"):
        raise TranslationAborted(f"claude CLI error: {data.get('result', 'unknown')}")
    return data.get("result", "")


# ---------------------------------------------------------------------------
# Deterministic include-path remap (code owns localization, not the model)
# ---------------------------------------------------------------------------

_PATH_CMD = re.compile(
    r"(\\(?:includegraphics(?:\[[^\]]*\])?|input|InputIfFileExists)\{)([^}]*)(\})"
)


def remap_include_paths(text: str) -> str:
    """Flip EN figure/table variants back to FR base names.

    Strips an `_en` suffix immediately before `.pdf`/`.tex` on the target of
    \\includegraphics / \\input / \\InputIfFileExists. Today a no-op (the EN
    deck still shares FR paths); becomes meaningful once ticket 0356 lands
    `_en` variants. Other paths pass through untouched.
    """

    def repl(m: re.Match[str]) -> str:
        path = re.sub(r"_en(\.(?:pdf|tex))$", r"\1", m.group(2))
        return m.group(1) + path + m.group(3)

    return _PATH_CMD.sub(repl, text)


# ---------------------------------------------------------------------------
# Tier-2 correctness guards
# ---------------------------------------------------------------------------


def check_looks_like_deck(text: str) -> None:
    if not text or not text.strip():
        raise TranslationAborted("Tier-2: empty translation output.")
    if "```" in text:
        raise TranslationAborted("Tier-2: output contains markdown code fences (```).")
    if not text.strip().startswith("\\documentclass"):
        raise TranslationAborted(
            "Tier-2: output does not start with \\documentclass (leading prose?)."
        )
    if "\\end{document}" not in text:
        raise TranslationAborted("Tier-2: output missing \\end{document}.")


def check_length_floor(fr_text: str, en_text: str, floor: float = LENGTH_FLOOR) -> None:
    en_len = len(en_text.encode("utf-8"))
    fr_len = len(fr_text.encode("utf-8"))
    if en_len and fr_len < floor * en_len:
        raise TranslationAborted(
            f"Tier-2: FR length {fr_len}B < {floor:.0%} of EN {en_len}B (truncation?)."
        )


def _structure(text: str) -> dict:
    return {
        "frame_begin": len(re.findall(r"\\begin\{frame\}", text)),
        "frame_end": len(re.findall(r"\\end\{frame\}", text)),
        "includegraphics": sorted(
            re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", text)
        ),
        "inputs": sorted(re.findall(r"\\(?:input|InputIfFileExists)\{([^}]*)\}", text)),
        "labels": sorted(re.findall(r"\\label\{([^}]*)\}", text)),
    }


def check_structural_invariants(en_text: str, fr_text: str) -> None:
    """Assert EN and candidate-FR share frames, figure paths, includes, labels.

    Apply remap_include_paths to EN before calling so the path sets line up.
    """
    en = _structure(en_text)
    fr = _structure(fr_text)
    problems: list[str] = []
    if en["frame_begin"] != fr["frame_begin"]:
        problems.append(f"frame count: EN {en['frame_begin']} vs FR {fr['frame_begin']}")
    if fr["frame_begin"] != fr["frame_end"]:
        problems.append(
            f"unbalanced frames in FR: {fr['frame_begin']} begin / {fr['frame_end']} end"
        )
    if en["frame_begin"] != en["frame_end"]:
        problems.append(
            f"unbalanced frames in EN: {en['frame_begin']} begin / {en['frame_end']} end"
        )
    for key in ("includegraphics", "inputs", "labels"):
        if en[key] != fr[key]:
            missing = sorted(set(en[key]) - set(fr[key]))
            extra = sorted(set(fr[key]) - set(en[key]))
            problems.append(f"{key} mismatch: missing in FR={missing}, extra in FR={extra}")
    if problems:
        raise TranslationAborted("Tier-2 structural drift:\n  " + "\n  ".join(problems))


# ---------------------------------------------------------------------------
# Atomic write + compile + diff
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".translate_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _compile(fr_path: Path) -> None:
    proc = subprocess.run(
        ["tectonic", fr_path.name],
        cwd=str(fr_path.parent),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise TranslationAborted(
            "Tier-2: tectonic failed to compile the FR deck "
            f"(FR was written; recover the prior version via git if needed):\n"
            f"{(proc.stderr or '')[-1000:]}"
        )
    print("Compiled clean.")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def translate(
    en: str | Path,
    fr: str | Path,
    *,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT,
    dry_run: bool = False,
    do_compile: bool = False,
    show_diff: bool = False,
) -> None:
    en_path = Path(en)
    fr_path = Path(fr)

    # Tier 1 — fail-closed work-loss guards (BEFORE any claude call or write).
    try:
        if not fr_is_committed(fr_path):
            raise TranslationAborted(
                f"Tier-1: {fr} is not tracked + committed-clean. Commit or stash "
                "it first so its prior content is git-recoverable."
            )
        if not en_at_least_as_new(en_path, fr_path):
            raise TranslationAborted(
                f"Tier-1: {fr} was committed more recently than {en}. Translating "
                "would overwrite newer French work — reconcile by hand first."
            )
    except GitError as exc:
        raise TranslationAborted(f"Tier-1 git error (fail-closed): {exc}") from exc

    en_text = en_path.read_text(encoding="utf-8")

    if dry_run:
        print("[dry-run] Tier-1 guards passed.")
        print(f"[dry-run] EN source : {en} ({len(en_text.encode('utf-8'))} bytes)")
        print(f"[dry-run] FR target : {fr}")
        print(f"[dry-run] model     : {model}")
        print("[dry-run] system prompt:")
        print(TRANSLATION_PROMPT)
        print("[dry-run] No claude call, no write.")
        return

    candidate = run_claude(en_text, model=model, timeout=timeout)
    candidate = remap_include_paths(candidate)

    # Tier 2 — correctness (BEFORE the write).
    check_looks_like_deck(candidate)
    check_length_floor(candidate, en_text)
    check_structural_invariants(remap_include_paths(en_text), candidate)

    _atomic_write(fr_path, candidate)

    if do_compile:
        _compile(fr_path)

    print(f"Wrote {fr}. Review the diff before committing — this is the review surface:")
    print(f"  git diff -- {fr}")
    if show_diff:
        try:
            root = _repo_root()
            print(_git(["diff", "--", _relpath(fr_path, root)], cwd=str(root)))
        except GitError as exc:
            print(f"(could not show diff: {exc})", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Translate slides/slides-en.tex (EN source of truth) -> "
            "slides/slides.tex (FR). Direction is hardcoded; there is "
            "intentionally no --from/--to."
        )
    )
    p.add_argument("--model", default=DEFAULT_MODEL, help="claude model id (default: %(default)s)")
    p.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT, help="claude timeout in seconds (default: %(default)s)"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Run Tier-1 guards and print the prompt/plan; no claude call, no write.",
    )
    p.add_argument(
        "--compile", action="store_true", help="Run `tectonic` on the FR deck after writing."
    )
    p.add_argument(
        "--show-diff", action="store_true", help="Print `git diff` of the FR deck after writing."
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = _repo_root()
    except GitError as exc:
        print(f"ABORTED: not inside a git repository ({exc}).", file=sys.stderr)
        return 1
    try:
        translate(
            en=str(root / SLIDES_EN),
            fr=str(root / SLIDES_FR),
            model=args.model,
            timeout=args.timeout,
            dry_run=args.dry_run,
            do_compile=args.compile,
            show_diff=args.show_diff,
        )
    except TranslationAborted as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
