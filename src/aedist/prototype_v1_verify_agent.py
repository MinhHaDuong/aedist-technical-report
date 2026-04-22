"""Prototype v1 web-verification agent using deepagents / LangGraph.

Demonstrates the core v1 capability missing from v0: a **multi-step,
planner-driven verification loop** where the agent decides whether the
initial web search was sufficient, or whether targeted follow-up queries
are needed before committing to a confidence score.

This is distinct from verify.py's one-shot ``verify_web`` mode, which
performs a single Tavily search per plant with no follow-up.

Usage::

    python -m aedist.prototype_v1_verify_agent --plant "Pha Lai" --country Vietnam
    python -m aedist.prototype_v1_verify_agent --plant "Mong Duong 1" --country Vietnam
    python -m aedist.prototype_v1_verify_agent --plant "Song Hau 1" --country Vietnam

Requirements:
    ANTHROPIC_API_KEY and TAVILY_API_KEY must be set (or in ~/.claude/.env).

Architecture:
    deepagents.create_deep_agent wraps a LangGraph react loop with:
    - write_todos (planner): agent structures its verification plan
    - web_search (custom tool): Tavily search, returns raw snippets
    - A structured response_format (PlantVerification pydantic model)

    The agent may call web_search multiple times before producing output.
    The number of search steps is the key de-risking metric.
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Annotated

import httpx
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------


class SourceEvidence(BaseModel):
    url: str = Field(description="URL of the source (empty string if not available)")
    title: str = Field(description="Title or description of the source")
    source_type: str = Field(description="'primary', 'secondary', or 'unknown'")


class PlantVerification(BaseModel):
    """Structured verification result for a single power plant."""

    name: str = Field(description="Plant name as found in sources")
    country: str = Field(description="Country where the plant is located")
    fuel: str = Field(
        description="Primary fuel type: 'coal', 'gas', 'oil', 'biomass', or 'unknown'"
    )
    capacity_mw: float | None = Field(
        description="Installed capacity in MW (None if not found)", default=None
    )
    status: str = Field(
        description="Plant status: 'operational', 'planned', 'cancelled', 'proposed', or 'unknown'"
    )
    confidence: float = Field(
        description="Confidence score 0.0-1.0 based on source quality: "
        "0.0=not found, 0.5=secondary source only, 0.8=one primary source, "
        "1.0=multiple primary sources",
        ge=0.0,
        le=1.0,
    )
    sources: list[SourceEvidence] = Field(
        description="Up to 3 sources found (empty if no evidence)", default_factory=list
    )
    search_queries_used: list[str] = Field(
        description="All search queries the agent executed", default_factory=list
    )
    verification_notes: str = Field(
        description="Brief explanation of the evidence and any uncertainties", default=""
    )


# ---------------------------------------------------------------------------
# Custom web search tool
# ---------------------------------------------------------------------------

# Primary-source domains for Vietnamese energy infrastructure
_PRIMARY_DOMAINS = {
    "gov.vn",
    "chinhphu.vn",
    "moit.gov.vn",
    "evn.com.vn",
    "globalenergymonitor.org",
    "gem.wiki",
    "iea.org",
    "irena.org",
}
_SECONDARY_DOMAINS = {"wikipedia.org", "bbc.com", "reuters.com", "bloomberg.com", "nikkei.com"}


def _classify_domain(url: str) -> str:
    url_lower = url.lower()
    for d in _PRIMARY_DOMAINS:
        if d in url_lower:
            return "primary"
    for d in _SECONDARY_DOMAINS:
        if d in url_lower:
            return "secondary"
    return "unknown"


@tool
def web_search(query: Annotated[str, "The search query to execute"]) -> str:
    """Search the web for information about power plants or energy infrastructure.

    Returns up to 5 search results with title, URL, and content snippet.
    Use targeted queries: include the plant name, country, and specific
    attribute (capacity, fuel, status) you are trying to verify.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return "ERROR: TAVILY_API_KEY not set"
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": 5,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return "No results found for this query."
        parts = []
        for r in results:
            url = r.get("url", "")
            domain_type = _classify_domain(url)
            parts.append(
                f"[{domain_type.upper()} SOURCE] {r.get('title', '')}\n"
                f"URL: {url}\n"
                f"Snippet: {r.get('content', '')[:500]}\n---"
            )
        return "\n".join(parts)
    except httpx.HTTPError as e:
        return f"Search error: {e}"


# ---------------------------------------------------------------------------
# Agent construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a power plant data verification agent. Your task is to verify
attributes (fuel type, capacity in MW, operational status) for a specific
power plant using web search.

Verification protocol:
1. Use write_todos to plan your verification steps (fuel, capacity, status).
2. Run an initial broad search: "{plant_name} power plant {country}".
3. Inspect results. If key attributes are missing or uncertain, run targeted
   follow-up searches (e.g., "{plant_name} capacity MW", "{plant_name} status 2024").
4. Stop searching when you have found at least one source confirming each
   attribute, or when 4 searches have produced no new information.
5. Return a structured result via the response format.

Source quality hierarchy:
- PRIMARY: government decisions, utility reports, GEM, IRENA, IEA (gov.vn, evn.com.vn,
  globalenergymonitor.org, iea.org, irena.org)
- SECONDARY: Wikipedia, news outlets (wikipedia.org, reuters.com, bloomberg.com)
- UNKNOWN: all other domains

Confidence scoring:
- 0.0: plant not found at all
- 0.5: secondary sources only
- 0.8: one primary source confirms the plant
- 1.0: two or more primary sources, or one primary with capacity from official data

Track all search queries you execute in search_queries_used.
"""


def build_agent(model_id: str = "anthropic:claude-haiku-4-5"):
    """Build the deepagents verification agent."""
    import deepagents

    model = init_chat_model(model_id)
    agent = deepagents.create_deep_agent(
        model=model,
        tools=[web_search],
        system_prompt=_SYSTEM_PROMPT,
        response_format=PlantVerification,
    )
    return agent


# ---------------------------------------------------------------------------
# Run verification
# ---------------------------------------------------------------------------


def verify_plant(plant_name: str, country: str, model_id: str = "anthropic:claude-haiku-4-5"):
    """Run the deepagents verification loop for a single plant.

    Returns a PlantVerification instance plus runtime metadata.
    """
    agent = build_agent(model_id)

    task = (
        f"Verify this power plant: name='{plant_name}', country='{country}'. "
        "Find and confirm: fuel type, capacity in MW, and operational status. "
        "Return a structured PlantVerification with confidence score and sources."
    )

    t0 = time.perf_counter()
    result = agent.invoke({"messages": [{"role": "user", "content": task}]})
    elapsed = time.perf_counter() - t0

    # Extract structured output from agent result
    # deepagents returns the structured response in result["structured_response"]
    # or as the last message with response_format applied
    structured = result.get("structured_response")
    if structured is None:
        # Fallback: check messages for tool call result
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if hasattr(msg, "content") and isinstance(msg.content, dict):
                try:
                    structured = PlantVerification(**msg.content)
                    break
                except Exception:
                    pass

    return structured, elapsed, result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="v1 prototype: multi-step web verification agent for power plants"
    )
    parser.add_argument("--plant", required=True, help="Plant name to verify")
    parser.add_argument("--country", default="Vietnam", help="Country (default: Vietnam)")
    parser.add_argument(
        "--model",
        default="anthropic:claude-haiku-4-5",
        help="LangChain model string (default: anthropic:claude-haiku-4-5)",
    )
    parser.add_argument("--output", default=None, help="Save JSON result to this path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Load env from ~/.claude/.env if present
    env_file = Path.home() / ".claude" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

    log.info("Verifying plant: %s (%s) with model %s", args.plant, args.country, args.model)

    structured, elapsed, raw = verify_plant(args.plant, args.country, args.model)

    if structured is None:
        log.error("Agent did not return a structured result. Raw output:")
        log.error(raw)
        return

    result_dict = structured.model_dump()
    result_dict["elapsed_seconds"] = round(elapsed, 1)

    print("\n" + "=" * 60)
    print(f"PLANT: {structured.name} ({structured.country})")
    print(f"Fuel:     {structured.fuel}")
    print(f"Capacity: {structured.capacity_mw} MW")
    print(f"Status:   {structured.status}")
    print(f"Confidence: {structured.confidence:.2f}")
    print(f"Sources ({len(structured.sources)}):")
    for s in structured.sources:
        print(f"  [{s.source_type.upper()}] {s.title}")
        print(f"    {s.url}")
    print(f"Search queries ({len(structured.search_queries_used)}):")
    for q in structured.search_queries_used:
        print(f"  - {q}")
    print(f"Notes: {structured.verification_notes}")
    print(f"Elapsed: {elapsed:.1f}s")
    print("=" * 60)

    if args.output:
        Path(args.output).write_text(json.dumps(result_dict, indent=2, ensure_ascii=False))
        log.info("Saved to %s", args.output)


if __name__ == "__main__":
    main()
