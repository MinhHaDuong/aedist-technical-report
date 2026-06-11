"""Audit prompt-cache utilisation in Exp 2 SOTA arms 3 & 4 (ticket 0369).

Aggregates token usage from the raw per-call JSON files recorded under the
arm 3 / arm 4 run directories and reports, per agent per arm:

- total input tokens billed at full rate
- cache_read / cache_creation tokens (Anthropic), cached_tokens (OpenAI/Qwen)
- cache_hit_rate = cache_read / (cache_read + cache_write + input)

Read-only: makes no API calls, mutates nothing.
"""

import argparse
import glob
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_ARM3 = "experiments/outputs/sota_exp3_arm3_batch1"
DEFAULT_ARM4 = "experiments/outputs/sota_exp3_arm4_batch1"

AGENTS = ("anthropic", "openai", "mistral", "qwen")


def usage_from_raw(raw: dict) -> dict | None:
    """Normalise one raw response JSON into a flat usage row, or None."""
    u = raw.get("usage")
    if not isinstance(u, dict):
        return None
    if "input_tokens" in u:  # Anthropic / OpenAI Responses / Qwen
        cached = u.get("cache_read_input_tokens")
        if cached is None:
            cached = (u.get("input_tokens_details") or {}).get("cached_tokens")
        if cached is None:
            cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)
        return {
            "input": int(u["input_tokens"]),
            "cache_read": int(cached or 0),
            "cache_write": int(u.get("cache_creation_input_tokens") or 0),
            "output": int(u.get("output_tokens") or 0),
        }
    if "prompt_tokens" in u:  # Mistral chat-completions shape
        return {
            "input": int(u["prompt_tokens"]),
            "cache_read": 0,
            "cache_write": 0,
            "output": int(u.get("completion_tokens") or 0),
        }
    return None


def collect_rows(arm3_dir: Path, arm4_dir: Path) -> list[dict]:
    """Walk both arm directories and return one row per recorded API call."""
    patterns = [
        # arm 4: per-turn raw replies, one subdir per agent rep
        (4, str(arm4_dir / "run*" / "{agent}_run*" / "{agent}_turn_*.raw.json")),
        # arm 3: single-call direct records and probe raw replies
        (3, str(arm3_dir / "run*" / "{agent}-direct-*.json")),
        (3, str(arm3_dir / "run*" / "{agent}_probe.raw.json")),
    ]
    rows: list[dict] = []
    for agent in AGENTS:
        for arm, pat in patterns:
            for f in sorted(glob.glob(pat.format(agent=agent))):
                try:
                    raw = json.loads(Path(f).read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    logger.warning("unreadable raw file skipped: %s", f)
                    continue
                # arm-3 direct records nest the reply under "response" in
                # some variants; fall back to a recursive usage search.
                u = usage_from_raw(raw) if isinstance(raw, dict) else None
                if u is None and isinstance(raw, dict):
                    u = _find_usage(raw)
                if u is None:
                    continue
                rows.append({"arm": arm, "agent": agent, "file": f, **u})
    return rows


def _find_usage(obj) -> dict | None:
    """Depth-first search for a usage-shaped dict inside a nested record."""
    if isinstance(obj, dict):
        u = usage_from_raw({"usage": obj}) if "input_tokens" in obj else None
        if u:
            return u
        for v in obj.values():
            u = _find_usage(v)
            if u:
                return u
    elif isinstance(obj, list):
        for v in obj:
            u = _find_usage(v)
            if u:
                return u
    return None


def aggregate(rows: list[dict]) -> list[dict]:
    """Per (arm, agent) aggregate with cache_hit_rate."""
    out = []
    for arm in (3, 4):
        for agent in AGENTS:
            sub = [r for r in rows if r["arm"] == arm and r["agent"] == agent]
            if not sub:
                continue
            inp = sum(r["input"] for r in sub)
            cr = sum(r["cache_read"] for r in sub)
            cw = sum(r["cache_write"] for r in sub)
            denom = cr + cw + inp
            out.append(
                {
                    "arm": arm,
                    "agent": agent,
                    "n_calls": len(sub),
                    "input_tokens": inp,
                    "cache_read_tokens": cr,
                    "cache_write_tokens": cw,
                    "cache_hit_rate": round(cr / denom, 4) if denom else 0.0,
                }
            )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm3-dir", type=Path, default=Path(DEFAULT_ARM3))
    parser.add_argument("--arm4-dir", type=Path, default=Path(DEFAULT_ARM4))
    parser.add_argument(
        "--per-call", action="store_true", help="also print one row per call"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = collect_rows(args.arm3_dir, args.arm4_dir)
    if args.per_call:
        for r in rows:
            print(
                f"arm{r['arm']} {r['agent']:<10} in={r['input']:>8,} "
                f"cr={r['cache_read']:>8,} cw={r['cache_write']:>8,}  {r['file']}"
            )
    print(f"{'arm':<4}{'agent':<11}{'calls':>6}{'input':>13}{'cache_read':>12}"
          f"{'cache_write':>12}{'hit_rate':>10}")
    for a in aggregate(rows):
        print(
            f"{a['arm']:<4}{a['agent']:<11}{a['n_calls']:>6}"
            f"{a['input_tokens']:>13,}{a['cache_read_tokens']:>12,}"
            f"{a['cache_write_tokens']:>12,}{a['cache_hit_rate']:>10.3f}"
        )


if __name__ == "__main__":
    main()
