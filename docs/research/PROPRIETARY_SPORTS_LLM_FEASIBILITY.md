# Proprietary Sports Betting LLM — Honest Feasibility Assessment

**Date:** March 14, 2026
**Author:** Solomon (PM) — research compiled from codebase audit + competitive landscape scan
**Status:** Research complete — no implementation action recommended at this time

---

## Context

The question: Could Ludi-Bot build its own fine-tuned LLM specifically for sports betting analytics, rather than wrapping Claude/Gemini API calls? This document is a strategic research assessment covering data readiness, cost analysis, competitive landscape, and a phased roadmap for when (if ever) a custom model becomes viable.

---

## Current LLM Architecture (Baseline)

### How LLMs Are Used Today

Ludi-Bot follows a strict separation: **LLMs orchestrate and reason — never calculate. Math stays deterministic.**

| Task | Model | Temperature | Daily Cost | Purpose |
|---|---|---|---|---|
| Injury blurb parsing | Haiku | 0.0 | ~$0.01 | Structured JSON extraction from news text |
| News catalyst detection | Haiku | 0.1 | ~$0.01 | Relevance + signal classification |
| Ask Ludi intent classification | Haiku | 0.1 | ~$0.01 | 7-class intent routing |
| Play curation (Stage 1) | Haiku | 0.1 | ~$0.02 | Injury contradiction sanity gate |
| Play curation (Stage 2) | Sonnet | 0.2 | ~$0.06 | Correlation-aware portfolio selection |
| Game notes narrative | Sonnet | 0.2 | $0.48–0.90 | Per-game analysis prose |
| Spotlight player analysis | Sonnet | 0.2 | $0.48–0.72 | Top-bet narrative explanations |
| Ask Ludi narrative | Sonnet | 0.3 | $0.03–0.15 | User-facing conversational answers |
| Archetype classification | Sonnet | 0.0 | ~$0.10/run | 15-class offensive role assignment (weekly) |
| Scheme classification | Haiku | — | ~$0.02/run | Team defensive scheme assignment (monthly) |

**Total daily spend: ~$0.60–1.25/day (~$18–38/month)**

### What LLMs Do NOT Touch

- Monte Carlo simulation (Module C) — pure Poisson math, 10k iterations
- Edge calculation & devigging (Module F) — multiplicative devig, Kelly sizing
- Matchup modifiers (Module E) — archetype × scheme matrix
- Usage vacuum theory (Module X) — redistribution logic
- Blowout tax — spread-based volume reduction
- All database operations, odds ingestion, referee scraping

---

## The Honest Answer: Not Yet — and Here's Why

### 1. Your Data Is Too Small (The Dealbreaker)

Fine-tuning requires **thousands** of high-quality prompt/completion pairs. Current data inventory:

| Data Asset | Volume | Usable for Fine-Tuning? |
|---|---|---|
| `player_game_logs` | ~10,840 rows | No — structured stats, not prompt/completion pairs |
| `bet_recommendations` | Dynamic | Partially — has outcomes, but no reasoning traces |
| `claude_analysis_log` | ~72 settled bets (as of Mar 10) | **This is your seed** — but you need 5,000+ minimum |
| `player_type_profiles` | 382 rows | No — classification labels only |
| Cached LLM responses | Not systematically stored | No training corpus exists |

**Bottom line:** You need ~50x more logged LLM interactions before fine-tuning is even worth attempting. The `claude_analysis_log` is the right idea — but at ~72 rows, you're at 1.4% of minimum viable training data.

**Comparison:** Academic sports LLM projects (SportQA, SportsGPT) use 10,000–100,000+ labeled examples. FanDuel's AAI was built by AWS's Generative AI Innovation Center with enterprise-scale data.

### 2. Your LLM Tasks Don't Benefit From Custom Training

The tasks where a custom model would help (intent classification, archetype classification) are your **cheapest** calls (~$0.03/day combined). The expensive calls (narratives, reasoning) require exactly what frontier models excel at — broad language understanding and nuanced reasoning. A 7B fine-tuned model will generate worse narratives than Sonnet.

| Task | Would Custom Model Help? | Why / Why Not |
|---|---|---|
| Intent classification | **Yes** | Simple 7-class classifier — trivial for any fine-tuned model |
| Archetype classification | **Maybe** | 15-class classifier with well-defined taxonomy |
| Injury blurb parsing | **Maybe** | Already temp=0.0 deterministic; structured output |
| Play curation reasoning | **Maybe** | Most domain-specific task, but needs correlation reasoning |
| Game narratives | **No** | Needs broad language ability + prose quality |
| Spotlight analysis | **No** | Needs reasoning depth + narrative skill |
| Ask Ludi narrative | **No** | Needs conversational ability + domain knowledge |
| News catalyst detection | **No** | General reasoning about relevance needed |

### 3. The Pipeline Principle Kills the ROI

The actual betting edge comes from deterministic math:
- Monte Carlo simulation (Module C) — **zero LLM involvement**
- Devigging & edge calculation (Module F) — **zero LLM involvement**
- Matchup modifiers (Module E) — **zero LLM involvement**
- Usage vacuum theory (Module X) — **zero LLM involvement**

The LLM layer is the **narrative wrapper** around deterministic math. Building a custom LLM won't improve hit rate, edge calculation, or CLV. It would only change how results are communicated.

### 4. The Cost Math Doesn't Work at Your Scale

| Approach | Monthly Cost | Setup Cost | Maintenance |
|---|---|---|---|
| **Current (Claude API)** | $18–38/mo | $0 | Zero — Anthropic handles updates |
| **LoRA fine-tune (7B, cloud GPU)** | $5–15/mo inference | $50–200 training | Retrain monthly as domain shifts |
| **Self-hosted (RTX 4090)** | $0 after hardware | $1,600+ GPU | Power, cooling, driver updates |
| **Karpathy-style (H100 rental)** | $2–3/hr training | $0 | Per-experiment cost |

At $18–38/month API spend, you'd need **years** to recoup the engineering investment. The breakeven only works at scale (thousands of users, hundreds of daily inference calls).

### 5. The Karpathy Autoresearch Angle

Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) is genuinely exciting — 630-line single-GPU training, autonomous experimentation, 100 experiments overnight. But it's designed for:

- **Pretraining research** on small GPT models (architecture search, optimizer tuning)
- **General language modeling** (val_bpb metric = bits per byte on text)
- **Experimentation framework** — finding what works, not deploying production models

It is **NOT** designed for:
- Domain-specific fine-tuning on structured sports data
- Instruction-following or classification tasks
- Production inference serving

The nanochat philosophy ("best ChatGPT that $100 can buy") produces models impressive for their size but categorically worse at reasoning than Claude Sonnet or GPT-4. The curation pipeline needs reasoning quality, not cost-optimal pretraining.

### 6. The Competitive Landscape Is Mostly Vapor

| Competitor | Claim | Reality |
|---|---|---|
| Volt Intelligence | "Groundbreaking LLM for sports analysis" | No public architecture, no published results, marketing only |
| FanDuel AAI | AI betting assistant | Uses AWS Bedrock (Claude/Titan) — NOT a custom model |
| asknews_mlb (GitHub) | LLM MLB predictor | RAG wrapper around AskNews API — NOT a custom model |
| Sports academic papers | SportQA, SportsGPT | Research benchmarks, not production betting systems |

**Nobody has shipped a production sports betting LLM.** The ones claiming to are either using RAG wrappers around frontier models (what Ludi-Bot is already doing) or are vaporware.

---

## What Would Actually Work (The Realistic Path)

### Phase 0: Data Collection (Start NOW — 6+ months)
- **Aggressively log every LLM call** — prompt, completion, outcome, was-it-right
- `claude_analysis_log` is the right table — but needs 5,000+ rows minimum
- Log Ask Ludi conversations (with user consent)
- Export curated prompt/completion pairs weekly
- **Target:** 10,000+ instruction pairs by September 2026

### Phase 1: Micro-Model for Classification Only (~$50–100)
- Fine-tune a **3B model** (Phi-3, Llama-3.2-3B) using QLoRA on:
  - Intent classification (7 classes — trivial task)
  - Archetype classification (15 classes — well-defined taxonomy)
  - Injury status parsing (6 statuses — structured output)
- **Keep Sonnet for reasoning/narrative** — this is the hybrid approach
- Run locally on CPU or cheap GPU (~$0/month inference)
- Cost savings: ~$0.03/day (the Haiku classification calls)
- **Real value:** Latency (instant local inference) + privacy + no API dependency

### Phase 2: RAG-Enhanced Domain Model (Phase 9 territory)
- Build a retrieval layer over `ludi.db` + `player_game_logs` + `bet_recommendations`
- Fine-tune a 7B model on accumulated prompt/completion pairs
- Use for: play curation reasoning, game dossier generation
- **Keep frontier model for:** user-facing narratives, complex reasoning

### Phase 3: Full Proprietary Model (2027+ — if data justifies it)
- Only attempt after 50,000+ logged interactions
- Only if daily API costs exceed $100+/day (scale threshold)
- Consider: distillation from Sonnet outputs → smaller model that mimics Sonnet's reasoning style
- Karpathy's autoresearch framework becomes relevant HERE — for architecture experimentation once you have the data

---

## The Hard Truths

1. **You're solving the wrong problem.** Your edge is in the math pipeline (Modules C/E/F), not the LLM layer. A proprietary LLM won't improve your hit rate or CLV.

2. **Your data is 50x too small.** 72 logged outcomes is a rounding error for fine-tuning. Need systematic, high-volume logging for 6+ months.

3. **The cost savings are negligible.** $18–38/month on Claude API vs. months of engineering time + infrastructure. The opportunity cost of NOT working on Phase 8.23 calibration or Phase 9 measurement is far higher.

4. **A 7B model will be worse at your hardest tasks.** Narrative generation, correlation reasoning for play curation, nuanced injury analysis — these require frontier model reasoning depth.

5. **The competitive moat argument is weak.** Your moat is your data pipeline, matchup modifiers, edge calculation methodology, and domain expertise encoded in prompts. The LLM is a commodity layer. `module_c.py` and `module_e.py` are the IP.

6. **The one thing that IS worth doing right now:** Start logging aggressively. Every prompt, every completion, every outcome. Build the training dataset passively while the current system runs.

---

## Verdict

**Not now. But don't dismiss it forever.**

The path is: **Log data now (Phase 0)** → **Micro-model for classification in 6 months (Phase 1)** → **RAG-enhanced domain model in 12 months (Phase 2)** → **Evaluate full custom model only if scale demands it (Phase 3)**.

**The single highest-ROI action today:** Make `claude_analysis_log` capture EVERY LLM call with full prompt/completion text, not just bet outcomes. That's your training dataset being built passively. When it hits 10,000+ rows, the fine-tuning conversation becomes real.

---

## Sources

- [Karpathy autoresearch (GitHub)](https://github.com/karpathy/autoresearch)
- [Karpathy nanochat (GitHub)](https://github.com/karpathy/nanochat)
- [Autoresearch: AI That Improves Its Own Training](https://www.analyticsvidhya.com/blog/2026/03/nanochat-gpt-2-training/)
- [Volt Intelligence Sports Betting LLM](https://voltintelligence.com/post/the-cutting-edge-ai-revolutionizing-sports-betting-how-volt-intelligences-1691700542870x679107088494886900)
- [FanDuel AI-Powered Betting Assistant (ZenML)](https://www.zenml.io/llmops-database/ai-powered-betting-assistant-for-sports-wagering-platform)
- [Building Your Own LLM-Powered Sports Analyst: RAG + Fine-tuning](https://dev.to/ffteamnames/building-your-own-llm-powered-sports-analyst-a-rag-approach-with-fine-tuning-397a)
- [Fine-Tuning LLMs on a Budget with LoRA (RunPod)](https://www.runpod.io/articles/guides/llm-fine-tuning-on-a-budget-top-faqs-on-adapters-lora-and-other-parameter-efficient-methods)
- [LLM Fine-Tuning Guide for Domain-Specific Models (DigitalOcean)](https://www.digitalocean.com/community/tutorials/llm-finetuning-domain-specific-models)
- [SportQA Benchmark (arXiv)](https://arxiv.org/html/2402.15862v1)
- [LLM-Commentator: Fine-tuning for Football (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S0950705124008530)
- [Evaluating LLM Reasoning Through Sports Betting](https://michaeltimbs.me/blog/evaluating-llm-reasoning-through-sports-betting/)
- [Guide to Choosing LLMs for Gambling Industry](https://www.gamingeminence.com/post/guide-to-choosing-the-right-llm-for-the-gambling-industry-in-2025)
