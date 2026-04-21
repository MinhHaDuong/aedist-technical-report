# LangChain Deep Agents / LangGraph Evaluation

**Ticket:** 0076 | **Date:** 2026-04-21 | **Author:** claude (Sonnet 4.6)

**Question:** Could the `deepagents` library or LangGraph replace or augment
the current AEDIST production pipeline? If so, which stages and at what cost?

---

## 1. What deepagents and LangGraph actually are (as of April 2026)

**LangGraph** (v1.0+, released October 2025) is a graph-based agent runtime
from LangChain Inc. Execution is modeled as a directed graph: nodes are
callables, edges carry a typed state object, and every node transition is
checkpointed. It provides durable execution (resume after crash), streaming,
human-in-the-loop interrupts, and "time-travel" debugging (replay any prior
state snapshot). LangGraph can be used without the rest of the LangChain stack
and is explicitly positioned as the successor to legacy LangChain agents for
orchestration work.

**deepagents** (v0.5.3, April 2026; beta) is an opinionated harness built on
top of LangGraph, directly modeled on Claude Code / Manus / Deep Research. It
adds four capabilities to a plain LangGraph agent:

| Primitive | Implementation |
|-----------|---------------|
| Planning | `write_todos` tool — a structuring no-op that keeps the agent on-track across long horizons |
| Virtual filesystem | `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep` — swappable backends (in-memory, disk, Modal/Daytona sandbox) |
| Sub-agent spawning | `task` tool — spawns a child agent in an isolated context window for a specific subtask |
| Shell execution | `execute` tool — sandboxed shell access |

The library ships opinionated system prompts, provider-agnostic model
selection, and native LangSmith tracing. It targets long-horizon autonomous
tasks where the agent decides its own execution path. It does not expose a
fixed-plan sweep: the agent drives itself.

Dependencies pull in `langchain-core`, `langgraph`, at least one provider SDK
(Anthropic/OpenAI/Google), and optional sandbox providers. The wheel is 139 kB
but the transitive closure is materially heavier than the current `openai` +
`pydantic` + `yaml` baseline.

---

## 2. AEDIST pipeline stages mapped to framework primitives

The current pipeline is a **pre-planned sweep**: `manager.py` fans out a
Cartesian product of (model × prompt-config × run-index) into deterministic
`JobSpec` files, each with a sha256-stable ID. `worker.py` executes jobs
sequentially or in parallel via lease semantics. Post-processing is fully
deterministic ETL (extract, evaluate, tabulate). `measurements.jsonl` is the
single source of truth, diff-able in plain text.

| AEDIST stage | deepagents primitive | Fit |
|---|---|---|
| `manager.py` — sweep fan-out | Planner (`write_todos`) | **Does not fit.** The sweep is a static, deterministic Cartesian product enumerated before any LLM is called. The deepagents planner is designed for _agent-decided_ task decomposition. There is nothing for it to plan. |
| `worker.py` — job lease + dispatch | Sub-agent (`task` tool) | **Partial, with overhead.** Each job is already one-shot and embarrassingly parallel. Expressing jobs as sub-agent spawns would add LangGraph graph overhead, opinionated system prompts, and sub-agent lifecycle management to what is currently a trivial `query_single_turn` call. |
| `query_*.py` — LLM calls | Tool-calling loop node | **Possible but regressive.** The current query scripts make a single structured API call per job. A deepagents node would wrap this in a loop-until-done pattern, adding latency and token overhead to one-shot calls. |
| `extract.py` + `evaluate.py` — CSV parsing and scoring | No equivalent primitive | **No fit.** These are deterministic Python functions with no LLM component. Wrapping them as tools serves no purpose. |
| `tabulate_*.py` + `plot_*.py` — reporting | No equivalent primitive | **No fit.** Same — pure deterministic ETL. |
| `verify.py` — multi-mode verification | Sub-agent or tool | **Plausible at the LangGraph level.** The `web` verify mode chains a Tavily search per plant followed by an LLM judgment call. This multi-step, result-dependent loop is the one stage that resembles an agentic pattern. |
| `measurements.jsonl` — artifact store | Virtual filesystem | **Format mismatch.** deepagents uses its filesystem for context management and inter-agent notes. `measurements.jsonl` is a structured append-only database consumed by downstream analysis scripts. Storing it in a virtual filesystem backend would break all downstream consumers and provide no benefit. |

**Where the mapping is clean:** nowhere, at present.

**Where the mapping fights the framework:**

1. The plan is static and enumerated externally. deepagents exists precisely for
   cases where the plan is dynamically constructed by the agent. Using its
   planner on a pre-enumerated sweep is like running a scheduler on a batch job
   that finishes in one step.

2. deepagents ships opinionated system prompts. AEDIST uses carefully composed
   modular prompts assembled from `experiments/prompts/modules/` as the
   experimental variable. Overriding deepagents' prompts is possible but
   requires fighting the library's defaults on every model call.

3. Sub-agent spawning adds inter-process LLM overhead. Every job in AEDIST is
   already isolated and stateless. The sub-agent model solves a context-window
   isolation problem that the current architecture does not have.

---

## 3. The reproducibility problem

AEDIST's reproducibility contract rests on two properties:

- Job IDs are `sha256(sweep_path, model_id, run_index)[:12]` — the same
  configuration always produces the same ID and can be re-run or skipped
  idempotently.
- `measurements.jsonl` records the full input hash, model ID, raw response, and
  evaluation metrics. Any run is re-runnable from the sweep config alone.

deepagents agent traces are planner-driven and non-deterministic by design. The
agent chooses which tools to call, in what order, and how many times. LangGraph
checkpointing can replay a saved state graph, but it replays _state snapshots_,
not LLM outputs; the model will generate different tokens on replay unless the
provider honors a seed parameter (best-effort on Anthropic/Google, partial on
OpenAI). There is no mechanism to guarantee that two runs of the same input
through a deepagents workflow produce identical `measurements.jsonl` records.

For a benchmark whose primary contribution is comparative evaluation across
models and prompt configurations, this is a hard constraint. The current
pipeline produces reproducible records because it _does not plan_: the sweep
drives execution fully deterministically.

---

## 4. Verdict

### deepagents: Reject

deepagents is built for the shape of Claude Code and Deep Research — long-horizon,
autonomous, user-driven tasks where the agent designs its own execution path.
AEDIST is a benchmark sweep: the execution path is fully specified by the
operator before any LLM is called. These are different problems. Adopting
deepagents wholesale would add a heavy, opinionated harness on top of a pipeline
that already solves its coordination problem with a Makefile, gaining nothing
while losing prompt control, reproducibility guarantees, and diagnostic
simplicity.

**Deciding factor:** shape mismatch between pre-planned sweep execution and
planner-driven autonomous loops. There is no stage in the current pipeline where
the agent needs to decide its own plan.

### LangGraph (narrow): Defer

The one stage where an agentic pattern is a genuine fit is `verify.py`'s `web`
mode (ticket 0059): per-plant web search → evidence aggregation → LLM judgment
call. This multi-step, result-dependent loop is exactly what LangGraph graph
nodes model well. LangGraph would provide cleaner state threading, retry logic,
and LangSmith traces compared to the current bespoke loop.

However, that stage is not yet production-critical, and adopting LangGraph there
requires adding a new runtime dependency before the benefit is demonstrated.
The recommendation is to defer until ticket 0059 verification is promoted to a
primary pipeline stage, then prototype with LangGraph _only_ (not deepagents)
for that loop, keeping the surrounding sweep harness unchanged.

### Summary table

| Component | Now | deepagents | LangGraph (narrow) |
|---|---|---|---|
| Sweep fan-out | `manager.py` + Makefile | Reject | No change needed |
| Job execution | `worker.py` lease | Reject | No change needed |
| One-shot query | `query.py` family | Reject | No change needed |
| Web verification loop | `verify.py web` | Reject | Defer to ticket 0059 |
| Extract / tabulate | deterministic ETL | Reject | No change needed |
| Artifact store | `measurements.jsonl` | Reject | No change needed |

---

## 5. What to watch

deepagents is at v0.5.3 (beta) with an active release cadence. If a future
AEDIST workload requires a genuinely long-horizon, agent-driven research task —
for example, automated source discovery across a new country/subsector with
unknown document structure — deepagents would be a natural fit at that point.
The current pipeline is not that workload.

LangGraph 1.0 is stable and production-ready. Its dependency footprint is
lighter than deepagents (no provider SDKs required beyond your own choice).
It is worth re-evaluating when the web-verification loop scales up.
