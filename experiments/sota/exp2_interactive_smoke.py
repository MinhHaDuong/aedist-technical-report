"""Exp 2 SOTA-agent smoke — Phase A (design) + Phase B (run) on one agent.

Ticket 0185. Read-only consumer of ``src/aedist/adapter_*.py``. Built
to support two modes:

- **Interactive** (default): SPACE-gated between phases for a human
  reviewer to inspect the meta-prompt, the Phase A response, and the
  Phase B request before each API call.
- **Agentic** (``--no-confirm``): pipeline runs end-to-end without
  prompting. Every step still writes its artefact to disk so an
  out-of-band reviewer (or this script's caller) can inspect after.

Web search is *available* in both phases — Phase A may or may not
search while designing the prompt; we observe what the model does
rather than suppressing the tool (per author direction 2026-05-21).

Output layout under ``--output-dir`` (default
``experiments/outputs/sota_exp2_smoke/``):

- ``{agent}_meta_prompt.txt`` — exact bytes sent to Phase A
- ``{agent}_phase_a.raw.json`` — raw provider response, Phase A
- ``{agent}_phase_a.json``      — parsed RunRecord, Phase A
- ``{agent}_phase_a_design.json`` — extracted designed prompt + settings
- ``{agent}_phase_b.raw.json`` — raw provider response, Phase B
- ``{agent}_phase_b.json``      — parsed RunRecord, Phase B
"""

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import yaml

from aedist import adapter_mistral
from aedist.schema import MethodParams, ResourceUse, ResultSummary, RunRecord

_TRIPLE_QUOTE_RE = re.compile(r'"""(.*?)"""', re.DOTALL)
_TOKENS_PER_MTOK = 1_000_000

# --- Policy locked by ticket 0207 (option B, multi-turn auto-reply) --------
PHASE_B_TOTAL_BUDGET_USD = 10.00
BUDGET_TRIGGER_FRAC = 0.20  # terminal reply when remaining ≤ this fraction of cap
STANDARD_REPLY = "Proceed as you think is best in autonomous agentic mode."
TERMINAL_REPLY = (
    "I have no additional directive to give you. Please proceed to "
    "generating the report without further asking. If you cannot, we "
    "would appreciate to know why, but the discussion will stop here "
    "in any case. Thanks for your understanding."
)
TURN_SAFETY_CAP = 20

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "experiments" / "prompts" / "prompt_complete.txt"
QUALITY_BAR_PATH = REPO_ROOT / "slides" / "manuscript" / "main.md"
MODELS_YAML = REPO_ROOT / "experiments" / "models.yaml"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "experiments" / "outputs" / "sota_exp2_smoke"

QUALITY_BAR_START = "## Second, the quality bar"
QUALITY_BAR_END = "## Third,"

FAMILY_BY_AGENT = {
    "mistral": "mistral-direct",
    "openai": "openai-direct",
    "anthropic": "anthropic-direct",
    "qwen": "qwen-direct",
}


def extract_quality_bar(manuscript_text: str) -> str:
    """Slice the §2 quality-bar block from the manuscript text."""
    start = manuscript_text.find(QUALITY_BAR_START)
    end = manuscript_text.find(QUALITY_BAR_END)
    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            f"Could not locate §2 quality-bar markers "
            f"({QUALITY_BAR_START!r} ... {QUALITY_BAR_END!r}) in manuscript"
        )
    return manuscript_text[start:end].strip()


def assemble_meta_prompt(baseline_path: Path, quality_bar_path: Path) -> str:
    """Build the Phase A meta-prompt: baseline + quality bar + design task."""
    baseline = baseline_path.read_text(encoding="utf-8").strip()
    quality_bar = extract_quality_bar(quality_bar_path.read_text(encoding="utf-8"))
    return f"""You are a state-of-the-art AI assistant being evaluated on a structured statistical-inventory task. In the NEXT turn you will be asked to produce the inventory itself. In THIS turn, you design how you want to do it.

# BUDGET (ticket 0207 policy, fixed condition)

Your budget for this entire engagement is **${PHASE_B_TOTAL_BUDGET_USD:.2f} total**. All your tool calls, search calls, and thinking tokens are billed against this cap. After this design turn, you will be in a multi-turn execution conversation; each of our replies will remind you of your remaining budget both in plain text and (where the provider supports it) via a structured metadata field. When the remaining budget drops below {int(BUDGET_TRIGGER_FRAC * 100)}%, we will send a single terminal reply asking you to finalise; the next response after that is the last one we accept. Prioritise producing the final report — do not stall on planning.

You will be given:
- a BASELINE PROMPT that defines the task
- a QUALITY BAR (four dimensions) on which your output will be judged

# BASELINE PROMPT

\"\"\"
{baseline}
\"\"\"

# QUALITY BAR

The inventory you produce on the next turn will be judged on these four dimensions:

\"\"\"
{quality_bar}
\"\"\"

# YOUR DESIGN TASK NOW

Design an improved prompt and a settings configuration aimed at maximising your performance on the four quality dimensions. You have full freedom to rewrite, expand, or restructure the baseline prompt. You may use web search if it helps you design; web search will also be available when you execute the designed prompt.

Return ONLY a single JSON object with this exact shape:

{{
  "designed_prompt": "<the prompt you want to receive next turn — sent to you verbatim>",
  "settings": {{
    "thinking": true_or_false,
    "max_tokens": <int>,
    "rationale_for_settings": "<short string>"
  }},
  "rationale": "<2-4 sentences naming which of the four dimensions your changes target and how>"
}}

Output ONLY the JSON object. No markdown fence, no prose around it.
"""


def load_model_meta(agent: str) -> dict:
    """Read the SOTA-route registry entry for ``agent`` from models.yaml."""
    registry = yaml.safe_load(MODELS_YAML.read_text())
    target_family = FAMILY_BY_AGENT[agent]
    if isinstance(registry, dict):
        registry = registry.get("models", [])
    for entry in registry:
        if entry.get("family") == target_family:
            return entry
    raise ValueError(f"No entry with family={target_family!r} found in {MODELS_YAML}")


def wait_for_space(prompt: str, *, no_confirm: bool) -> None:
    """Pause for human review; no-op when ``--no-confirm`` is set."""
    if no_confirm:
        log.info("[auto-continue] %s", prompt)
        return
    sys.stdout.write(f"\n{prompt}\nPRESS ENTER to continue, or 'q' to abort > ")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if line.strip().lower() == "q":
        log.warning("Aborted by user.")
        sys.exit(0)


def extract_narrative_from_mistral_raw(raw: dict) -> str:
    """Concatenate text chunks from message.output items in a Mistral raw response.

    The Mistral Conversations API returns ``content`` in two shapes empirically:
    - a flat ``str`` (observed 2026-05-21, Phase A smoke)
    - a ``list[dict]`` of ``{type, text}`` chunks (the shape adapter_mistral
      assumes; observed in the 2026-05-20 derisk fixture)

    Handle both so the smoke is resilient to either response shape.
    """
    chunks: list[str] = []
    for item in raw.get("outputs", []):
        if item.get("type") != "message.output":
            continue
        content = item.get("content")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "text":
                    chunks.append(c.get("text", ""))
                elif isinstance(c, str):
                    chunks.append(c)
    return "".join(chunks).strip()


def _normalize_python_triple_quotes(text: str) -> str:
    """Convert Python-style ``\"\"\"...\"\"\"`` blocks to valid JSON string literals.

    SOTA models occasionally use Python triple-quoted strings inside JSON
    despite that being invalid JSON syntax (observed in Mistral Phase A
    2026-05-21: 16K-char response with a triple-quoted ``designed_prompt``).
    ``json.dumps`` produces a correctly escaped JSON string literal.
    """
    return _TRIPLE_QUOTE_RE.sub(lambda m: json.dumps(m.group(1)), text)


def extract_phase_a_design(response_text: str) -> dict:
    """Parse the JSON envelope out of Phase A's narrative response.

    Tolerant in three layers (SOTA agents ignore "Output ONLY JSON" routinely):
    1. Strip a leading/trailing ``` fence if present.
    2. ``json.loads`` on the stripped text.
    3. Fallback — slice from first ``{`` to last ``}`` and retry.

    Raises ``ValueError`` with a short preview if both attempts fail.
    """
    text = response_text.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        if first_nl != -1:
            text = text[first_nl + 1 :]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()
    text = _normalize_python_triple_quotes(text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        first = text.find("{")
        last = text.rfind("}")
        if first == -1 or last == -1 or last <= first:
            preview = text[:400].replace("\n", "\\n")
            raise ValueError(
                f"Phase A response has no JSON object; first 400 chars: {preview!r}"
            ) from None
        try:
            obj = json.loads(text[first : last + 1])
        except json.JSONDecodeError as exc:
            preview = text[:400].replace("\n", "\\n")
            raise ValueError(
                f"Phase A response is not valid JSON: {exc}; first 400 chars: {preview!r}"
            ) from exc
    for key in ("designed_prompt", "settings", "rationale"):
        if key not in obj:
            raise ValueError(f"Phase A JSON missing required key {key!r}; got keys {list(obj)}")
    return obj


def _runrecord_from_raw(
    raw_path: Path,
    meta: dict,
    *,
    agent_mode: str,
    wall_s: float | None = None,
) -> RunRecord:
    """Build a minimal RunRecord from a saved Mistral raw response.

    Used when ``adapter_mistral.parse_response`` raises on an unexpected
    content shape — the raw artefact is the ground truth, this synthesizes
    just enough of a RunRecord for the smoke to continue.
    """
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    usage = raw.get("usage", {}) or {}
    tokens_in = int(usage.get("prompt_tokens", 0) or 0)
    tokens_out = int(usage.get("completion_tokens", 0) or 0)
    p_in = float(meta.get("price_per_mtok_in", 0.0)) / _TOKENS_PER_MTOK
    p_out = float(meta.get("price_per_mtok_out", 0.0)) / _TOKENS_PER_MTOK
    return RunRecord(
        method="frontier",
        method_params=MethodParams(
            model=meta.get("model_id", adapter_mistral.DEFAULT_MODEL),
            max_tokens=tokens_out,
            extra={"recovered_from_raw": True},
        ),
        resource_use=ResourceUse(
            wall_s=wall_s,
            cost_usd=tokens_in * p_in + tokens_out * p_out,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        ),
        result_summary=ResultSummary(status="ok"),
        agent_family=adapter_mistral.AGENT_FAMILY,
        agent_mode=agent_mode,
        finish_reason="stop",
    )


def run_mistral_call(
    prompt: str,
    *,
    cap_usd: float,
    agent_mode: str,
    raw_output_path: Path,
    max_tokens: int,
    continuation: dict | None = None,
    extra_metadata: dict | None = None,
) -> RunRecord:
    """Single Mistral Agents call, with the registry-driven model metadata.

    Wraps ``adapter_mistral.run()`` with a recovery path for the case where
    ``parse_response`` raises on an unexpected content shape (str-content
    bug is fixed on main via PR #394 but defense in depth stays). The
    ``continuation`` and ``extra_metadata`` kwargs were added to the four
    SOTA adapters in PR #396 (ticket 0208); we forward them.
    """
    meta = load_model_meta("mistral")
    t0 = time.monotonic()
    try:
        return adapter_mistral.run(
            prompt,
            dry_run=False,
            model_meta=meta,
            max_tokens=max_tokens,
            cap_usd=cap_usd,
            agent_mode=agent_mode,
            output_path=raw_output_path,
            continuation=continuation,
            extra_metadata=extra_metadata,
        )
    except AttributeError as exc:
        if not raw_output_path.exists():
            raise
        wall_s = round(time.monotonic() - t0, 3)
        log.warning(
            "adapter_mistral.parse_response failed (%s); rebuilding RunRecord from raw artefact.",
            exc,
        )
        return _runrecord_from_raw(raw_output_path, meta, agent_mode=agent_mode, wall_s=wall_s)


def total_cost(record: RunRecord) -> float:
    """Token cost + connector (web_search) cost."""
    return (record.resource_use.cost_usd or 0.0) + (record.tool_calls_cost_usd or 0.0)


# ---------------------------------------------------------------------------
# Multi-turn auto-reply loop (ticket 0207 policy)
# ---------------------------------------------------------------------------


def format_status_line(remaining_usd: float, cap_usd: float, elapsed_s: float) -> str:
    """The exact status-prefix string the harness puts on every Phase B user turn."""
    return (
        f"Status: remaining budget ${remaining_usd:.2f} of ${cap_usd:.2f}; "
        f"wall-clock elapsed {elapsed_s:.1f}s."
    )


def select_reply(remaining_usd: float, cap_usd: float) -> tuple[str, bool]:
    """Return (reply_text, is_terminal) per ticket 0207 policy."""
    if remaining_usd <= BUDGET_TRIGGER_FRAC * cap_usd:
        return TERMINAL_REPLY, True
    return STANDARD_REPLY, False


def _turn_artefact_paths(output_dir: Path, agent: str, turn: int) -> dict[str, Path]:
    """Per-turn artefact paths under output_dir."""
    base = output_dir / f"{agent}_turn_{turn:02d}"
    return {
        "user": Path(str(base) + ".user.txt"),
        "raw": Path(str(base) + ".raw.json"),
        "record": Path(str(base) + ".record.json"),
        "cost": Path(str(base) + ".cost.json"),
    }


def run_phase_b_multiturn(
    designed_prompt: str,
    *,
    output_dir: Path,
    cap_usd: float,
    initial_spent_usd: float,
    max_tokens: int,
    agent: str = "mistral",
) -> dict:
    """Run the Phase B multi-turn auto-reply loop on a single agent.

    Policy: ticket 0207. Per-turn user message is the designed prompt
    on turn 1, and a status-prefixed standard reply on turns 2..N-1.
    When remaining budget ≤ BUDGET_TRIGGER_FRAC × cap, the terminal
    reply fires; the next assistant response is the last accepted one.

    Returns a dict with ``records``, ``turns``, ``total_spent_usd``,
    ``terminal_sent``, and ``agent_id`` (for caller-side cleanup).
    """
    if agent != "mistral":
        raise NotImplementedError(f"--agent {agent!r} not wired for multi-turn yet")

    remaining = cap_usd - initial_spent_usd
    elapsed_s = 0.0
    continuation: dict | None = {}  # empty dict = start multi-turn, keep Mistral agent alive
    agent_id: str | None = None
    terminal_sent = False
    records: list[RunRecord] = []
    turn = 1

    while True:
        if turn == 1:
            user_text = designed_prompt
        else:
            status = format_status_line(remaining, cap_usd, elapsed_s)
            reply, is_terminal = select_reply(remaining, cap_usd)
            if is_terminal:
                terminal_sent = True
            user_text = f"{status}\n\n{reply}"

        paths = _turn_artefact_paths(output_dir, agent, turn)
        paths["user"].write_text(user_text, encoding="utf-8")

        extra_metadata: dict | None = {
            "remaining_budget_usd": f"{remaining:.2f}",
            "cap_usd": f"{cap_usd:.2f}",
        }
        # Per ticket 0212: Mistral's path-bound append endpoint rejects
        # body-level `metadata` with HTTP 422 (empirically confirmed
        # 2026-05-21). On follow-up turns (when `continuation` carries
        # an agent_id), suppress the structured metadata signal — the
        # chat-text status prefix still informs the model. Adapter-side
        # fix is 0212's scope.
        is_followup_turn = bool(continuation and continuation.get("agent_id"))
        if is_followup_turn:
            extra_metadata = None

        record = run_mistral_call(
            user_text,
            cap_usd=max(remaining, 0.01),  # adapter wants positive cap
            agent_mode="phase_b_run",
            raw_output_path=paths["raw"],
            max_tokens=max_tokens,
            continuation=continuation,
            extra_metadata=extra_metadata,
        )
        records.append(record)

        spent_this_turn = total_cost(record)
        remaining -= spent_this_turn
        elapsed_s += record.resource_use.wall_s or 0.0

        paths["record"].write_text(record.model_dump_json(indent=2), encoding="utf-8")
        paths["cost"].write_text(
            json.dumps(
                {
                    "turn": turn,
                    "spent_usd": spent_this_turn,
                    "remaining_usd": remaining,
                    "elapsed_s": elapsed_s,
                    "is_terminal_reply": terminal_sent,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        extra = record.method_params.extra or {}
        if agent_id is None and extra.get("agent_id"):
            agent_id = str(extra["agent_id"])
        conv_id = extra.get("conversation_id")
        if conv_id and agent_id:
            continuation = {"agent_id": agent_id, "conversation_id": conv_id}

        log.info(
            "Phase B turn %d: spent=$%.4f remaining=$%.4f tokens_out=%s web_search=%d%s",
            turn,
            spent_this_turn,
            remaining,
            record.resource_use.tokens_out,
            len(record.web_search_calls or []),
            " [terminal reply sent]" if terminal_sent and turn > 1 else "",
        )

        if terminal_sent:
            break
        if remaining <= 0:
            log.warning("Budget exhausted without terminal reply having fired; stopping.")
            break
        if turn >= TURN_SAFETY_CAP:
            log.warning("Hit safety cap of %d turns; stopping.", TURN_SAFETY_CAP)
            break
        turn += 1

    return {
        "records": records,
        "turns": turn,
        "total_spent_usd": cap_usd - remaining - initial_spent_usd,
        "terminal_sent": terminal_sent,
        "agent_id": agent_id,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--agent",
        required=True,
        choices=sorted(FAMILY_BY_AGENT),
        help="Which SOTA agent to smoke (only 'mistral' wired in this iteration).",
    )
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--no-confirm", action="store_true", help="Skip SPACE gates.")
    p.add_argument("--dry-run", action="store_true", help="Print meta-prompt and exit.")
    p.add_argument("--budget-cap-phase-a", type=float, default=1.0)
    p.add_argument("--budget-cap-phase-b", type=float, default=15.0)
    p.add_argument("--phase-a-max-tokens", type=int, default=8000)
    p.add_argument("--phase-b-max-tokens", type=int, default=12000)
    p.add_argument(
        "--stop-after-phase-a",
        action="store_true",
        help="Exit after Phase A artefacts land; do not call Phase B.",
    )
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    if args.agent != "mistral":
        sys.exit(f"Only --agent mistral is wired in this iteration; got {args.agent!r}.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    meta_prompt = assemble_meta_prompt(BASELINE_PATH, QUALITY_BAR_PATH)
    meta_prompt_path = args.output_dir / f"{args.agent}_meta_prompt.txt"
    meta_prompt_path.write_text(meta_prompt, encoding="utf-8")
    log.info("Meta-prompt assembled (%d chars) -> %s", len(meta_prompt), meta_prompt_path)

    if args.dry_run:
        log.info("--dry-run set; not calling API. Exiting.")
        return 0

    # --- Phase A: design ---
    wait_for_space(
        f"Phase A: send meta-prompt to {args.agent}. Cap ${args.budget_cap_phase_a:.2f}.",
        no_confirm=args.no_confirm,
    )
    phase_a_raw_path = args.output_dir / f"{args.agent}_phase_a.raw.json"
    phase_a = run_mistral_call(
        meta_prompt,
        cap_usd=args.budget_cap_phase_a,
        agent_mode="phase_a_design",
        raw_output_path=phase_a_raw_path,
        max_tokens=args.phase_a_max_tokens,
    )
    phase_a_path = args.output_dir / f"{args.agent}_phase_a.json"
    phase_a_path.write_text(phase_a.model_dump_json(indent=2), encoding="utf-8")
    log.info(
        "Phase A done: cost=$%.4f, wall=%ss, tokens_out=%s, web_search=%d -> %s",
        total_cost(phase_a),
        phase_a.resource_use.wall_s,
        phase_a.resource_use.tokens_out,
        len(phase_a.web_search_calls or []),
        phase_a_path,
    )

    # Pull narrative -> JSON envelope -> designed_prompt
    raw_a = json.loads(phase_a_raw_path.read_text(encoding="utf-8"))
    narrative_a = extract_narrative_from_mistral_raw(raw_a)
    design = extract_phase_a_design(narrative_a)
    design_path = args.output_dir / f"{args.agent}_phase_a_design.json"
    design_path.write_text(json.dumps(design, indent=2, ensure_ascii=False), encoding="utf-8")
    dp = design.get("designed_prompt", "")
    dp_summary = (
        f"str/{len(dp)} chars"
        if isinstance(dp, str)
        else f"{type(dp).__name__}/{len(dp)} top-level keys"
    )
    log.info(
        "Phase A design extracted: designed_prompt=%s, thinking=%s, max_tokens=%s -> %s",
        dp_summary,
        design.get("settings", {}).get("thinking"),
        design.get("settings", {}).get("max_tokens"),
        design_path,
    )

    if args.stop_after_phase_a:
        log.info("--stop-after-phase-a set; exiting before Phase B.")
        return 0

    # --- Phase B: multi-turn auto-reply loop (ticket 0207 policy) ---
    wait_for_space(
        f"Phase B: multi-turn loop on {args.agent}. Total cap ${PHASE_B_TOTAL_BUDGET_USD:.2f} "
        f"(after Phase A's ${total_cost(phase_a):.4f}).",
        no_confirm=args.no_confirm,
    )
    designed_prompt_raw = design["designed_prompt"]
    designed_prompt = (
        designed_prompt_raw
        if isinstance(designed_prompt_raw, str)
        else json.dumps(designed_prompt_raw, indent=2, ensure_ascii=False)
    )
    log.info(
        "Phase B input: designed_prompt is %s, %d chars after serialisation.",
        type(designed_prompt_raw).__name__,
        len(designed_prompt),
    )
    requested_max_tokens = int(
        design.get("settings", {}).get("max_tokens") or args.phase_b_max_tokens
    )

    phase_b = run_phase_b_multiturn(
        designed_prompt,
        output_dir=args.output_dir,
        cap_usd=PHASE_B_TOTAL_BUDGET_USD,
        initial_spent_usd=total_cost(phase_a),
        max_tokens=requested_max_tokens,
        agent=args.agent,
    )

    if phase_b["agent_id"]:
        try:
            adapter_mistral.cleanup_agent(phase_b["agent_id"])
            log.info("Cleaned up Mistral agent %s", phase_b["agent_id"])
        except Exception as exc:  # noqa: BLE001 — cleanup failures should not raise
            log.warning("Mistral agent cleanup failed: %s", exc)

    log.info(
        "SMOKE TOTAL: $%.4f (Phase A $%.4f + Phase B $%.4f over %d turns; terminal_sent=%s).",
        total_cost(phase_a) + phase_b["total_spent_usd"],
        total_cost(phase_a),
        phase_b["total_spent_usd"],
        phase_b["turns"],
        phase_b["terminal_sent"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
