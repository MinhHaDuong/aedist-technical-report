"""Live verification for ticket 0369: Anthropic 1h prompt-cache wiring fires.

Drives run_anthropic_call (the production code path) over two turns with a
synthetic ~8K-token turn-1 prompt (above the 4096-token Opus cache minimum)
and checks usage counters:
  turn 1 -> cache_creation ephemeral_1h_input_tokens > 0  (breakpoints 1+2 write)
  turn 2 -> cache_read_input_tokens > 0                   (prefix read back)

Cost: ~$0.10-0.30. Run from the t0369 worktree:
  PYTHONPATH=. uv run --env-file .env python scripts/verify_anthropic_cache_live.py --outdir /tmp/cache_smoke

Spends real money (~$0.10-0.30); not part of any test suite or Make target.
"""

import argparse
import json
import logging
import secrets
from pathlib import Path

from experiments.sota.exp2_interactive_smoke import run_anthropic_call

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.outdir.mkdir(parents=True, exist_ok=True)

    nonce = secrets.token_hex(8)  # defeat any pre-existing cache entry
    filler = " ".join(
        f"register entry {i} token {nonce} capacity {i * 7 % 991} MW" for i in range(1200)
    )
    turn1_prompt = (
        f"Synthetic cache-verification payload {nonce}.\n{filler}\n"
        "Reply with exactly: ACK"
    )
    system_prompt = "You are a terse test assistant. Reply minimally."

    r1 = run_anthropic_call(
        turn1_prompt,
        cap_usd=1.0,
        agent_mode="cache_smoke",
        raw_output_path=args.outdir / "turn1.raw.json",
        max_tokens=2048,
        system_prompt=system_prompt,
    )
    u1 = json.loads((args.outdir / "turn1.raw.json").read_text())["usage"]
    logger.info("turn1 usage: %s", json.dumps(u1, indent=1))

    reply1 = (r1.justification or {}).get("output_text") or "ACK"
    r2 = run_anthropic_call(
        "Reply with exactly: ACK2",
        cap_usd=1.0,
        agent_mode="cache_smoke",
        raw_output_path=args.outdir / "turn2.raw.json",
        max_tokens=2048,
        continuation={
            "messages": [
                {"role": "user", "content": turn1_prompt},
                {"role": "assistant", "content": reply1},
            ]
        },
        system_prompt=system_prompt,
    )
    del r2
    u2 = json.loads((args.outdir / "turn2.raw.json").read_text())["usage"]
    logger.info("turn2 usage: %s", json.dumps(u2, indent=1))

    write_1h = (u1.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
    read_2 = u2.get("cache_read_input_tokens", 0)
    assert write_1h > 0, f"turn 1 wrote no 1h cache: {u1}"
    assert read_2 > 0, f"turn 2 read no cache: {u2}"
    logger.info("PASS: turn1 1h-cache write=%s tok, turn2 cache read=%s tok", write_1h, read_2)


if __name__ == "__main__":
    main()
