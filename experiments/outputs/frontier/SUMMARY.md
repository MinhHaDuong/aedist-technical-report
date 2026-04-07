# Frontier Deep Research Benchmark — Results

**Date**: 2026-04-07
**Prompt**: Comprehensive Vietnam thermal power sector inventory with context,
per-plant sourced discussion, statistical tables, annotated bibliography.
**Total spend**: $1.23 (14 models × 1 run each)

## Inventory prompt — 14 models across 10 labs

| Model | Lab | Tokens | Time | Cost | Chars | Table rows | Source refs | Status |
|-------|-----|--------|------|------|-------|------------|-------------|--------|
| Claude Opus 4.6 | Anthropic | 31,374 | 491s | $0.790 | 77,114 | 162 | 46 | OK |
| MiniMax M2.7 | MiniMax | 24,784 | 468s | $0.030 | 85,877 | 231 | 0 | OK |
| Tongyi DeepResearch 30B | Alibaba | 21,845 | 155s | $0.010 | 17,042 | 84 | 10 | OK |
| Sonar Deep Research | Perplexity | 19,585 | 179s | $0.159 | 64,136 | 95 | 0 | OK |
| Kimi K2 Thinking | Moonshot | 14,086 | 195s | $0.029 | 35,737 | 93 | 0 | OK |
| GLM-5 Turbo | Zhipu AI | 12,302 | 387s | $0.051 | 26,396 | 99 | 12 | OK |
| Qwen3 Max Thinking | Alibaba | 9,645 | 290s | $0.039 | 25,321 | 95 | 97 | OK |
| GLM-5 | Zhipu AI | 8,833 | 92s | $0.021 | 19,873 | 77 | 17 | OK |
| DeepSeek V3.2 | DeepSeek | 8,695 | 281s | $0.004 | 27,067 | 85 | 32 | OK |
| o3 | OpenAI | 8,027 | 57s | $0.066 | 18,831 | 73 | 0 | OK |
| DeepSeek R1 0528 | DeepSeek | 7,938 | 242s | $0.018 | 14,018 | 54 | 33 | OK |
| ERNIE 4.5 Thinking | Baidu | 6,185 | 65s | $0.002 | 17,267 | 30 | 0 | OK |
| GPT-5.4 | OpenAI | 626 | 12s | $0.012 | 2,946 | 0 | 0 | REFUSED |
| Grok 4.20 | xAI | 502 | 3s | $0.005 | 2,579 | 0 | 0 | REFUSED |
| o3 Deep Research | OpenAI | 30,099 | 517s | $1.958 | 0 | 0 | 0 | OPAQUE |

## Key findings

### 1. Chinese models dominate value
- **DeepSeek V3.2** at $0.004 delivers 85 table rows and 32 source refs — 200× cheaper than Opus
- **MiniMax M2.7** at $0.03 produces 231 table rows (more than Opus) in 86k chars
- **ERNIE 4.5 Thinking** at $0.002 is the cheapest to produce any output at all

### 2. Quality tiers
- **Tier 1 — Opus-class**: Only Opus delivers all sections with deep Vietnamese expertise (25 Vietnamese-language citations), per-plant narratives, and zero fabricated URLs
- **Tier 2 — Comprehensive**: MiniMax, Sonar, Kimi, GLM-5 Turbo deliver all 5 sections with moderate source coverage
- **Tier 3 — Adequate**: DeepSeek, Qwen, GLM-5, o3 deliver structured reports but thinner on per-plant detail
- **Tier 4 — Refused/Opaque**: GPT-5.4 (accuracy concern), Grok (safety refusal), o3 Deep Research (opaque — spent $1.96 on web research but returned nothing through OpenRouter's chat completions API; requires OpenAI native Responses API)

### 3. Refusal behavior reveals model personality
- **GPT-5.4**: Honest epistemological refusal — "I can't verify from memory"
- **Grok 4.20**: Safety over-calibration — classified public PDP data as sensitive infrastructure
- **All 5 Chinese models**: Zero refusals. All delivered comprehensive reports
- **Reasoning models** (o3, DeepSeek R1, Qwen Max Thinking, Kimi Thinking, ERNIE Thinking): Zero refusals

### 4. URL honesty
- **Zero fabricated URLs**: Opus, MiniMax, Sonar, DeepSeek V3.2, GLM-5, o3
- **2 fabricated URLs**: Qwen3 Max Thinking (only model to violate the "don't fabricate" instruction)
- All models used "URL not verified" annotation for uncertain sources

### 5. Vietnamese language competence
- **Opus**: 25 Vietnamese-language references (Quyết định, Nghị quyết, etc.)
- **Sonar**: 15
- **Qwen3 Max Thinking**: 6
- **DeepSeek V3.2**: 4
- **MiniMax**: 3

## Cost breakdown by lab

| Lab | Model | Cost | Relative to Opus |
|-----|-------|------|-----------------|
| Anthropic | Opus 4.6 | $0.790 | 1× (baseline) |
| Perplexity | Sonar Deep Research | $0.159 | 5× cheaper |
| OpenAI | o3 | $0.066 | 12× cheaper |
| Zhipu AI | GLM-5 Turbo | $0.051 | 15× cheaper |
| Alibaba | Qwen3 Max Thinking | $0.039 | 20× cheaper |
| MiniMax | M2.7 | $0.030 | 26× cheaper |
| Moonshot | Kimi K2 Thinking | $0.029 | 27× cheaper |
| Zhipu AI | GLM-5 | $0.021 | 38× cheaper |
| DeepSeek | R1 0528 | $0.018 | 44× cheaper |
| Alibaba | Tongyi DeepResearch | $0.010 | 79× cheaper |
| DeepSeek | V3.2 | $0.004 | 198× cheaper |
| Baidu | ERNIE 4.5 Thinking | $0.002 | 395× cheaper |

## Multi-prompt comparison (3 prompts × 3 models)

| Prompt | Opus 4.6 | o3 | Tongyi DR |
|--------|----------|-----|-----------|
| Inventory | $0.79 / 77k chars | $0.07 / 19k | $0.01 / 17k |
| Scenarios | $0.46 / 54k chars | $0.04 / 12k | $0.004 / 9k |
| Skill gen | $0.57 / 78k chars | $0.04 / 17k | $0.002 / 12k |
| **Total** | **$1.82** | **$0.14** | **$0.016** |
