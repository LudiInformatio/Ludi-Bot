# LLM Training Methodologies: Full Landscape Research

**Date:** March 8, 2026
**Purpose:** Explore academic LLM training paradigms beyond BERT for potential application in Ludi-Bot
**Current Baseline:** 9 BERT-derived prompt patterns in `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md`

---

## Architectures Beyond BERT

### Encoder-Only (BERT Family)
- **RoBERTa** — Better BERT: dynamic masking, no NSP, larger batches. Lesson: NSP was noise. (Liu et al. 2019)
- **ALBERT** — Sentence Order Prediction (SOP) replaces NSP. Lesson: example ordering matters. (Lan et al. 2020, ICLR 2020)
- **ELECTRA** — Discriminator classifies every token as real/fake. 4x sample-efficient. Lesson: negative examples > positive-only. (Clark et al. 2020)
- **DeBERTa** — Disentangled attention (content vs position as separate vectors). Lesson: prompt structure matters independently from content. (He et al. 2021, ICLR 2021)

### Decoder-Only (GPT Family)
- **GPT-3/4** — Autoregressive CLM. Trains on 100% of tokens (vs BERT's 15%). Lesson: earlier tokens influence later output more. (Brown et al. 2020)
- **LLaMA 3/3.3** — Open-weight. 3.3 (70B) matches 405B via distillation. Lesson: methodology > scale. (Meta 2024)
- **Mistral/Mixtral** — MoE: 47B total, 13B active. Lesson: specialized sub-networks per task. (Jiang et al. 2024)
- **Phi-3** — "Textbook-quality" synthetic data. 3.8B rivals 10x larger. Lesson: data quality > quantity. (Abdin et al. 2024)

### Encoder-Decoder
- **T5/FLAN-T5** — All tasks as text-to-text. FLAN: 1,800+ instruction-tuned tasks. Lesson: clear task+input+format = better results. (Raffel et al. 2020, Chung et al. 2022)

### Non-Transformer
- **Mamba** (SSMs) — Linear-time O(n) vs transformer O(n^2). 5x throughput. (Gu & Dao 2023)
- **Jamba** — Hybrid 7:1 SSM:attention. 52B total, 12B active. Signals future architecture direction. (Lieber et al. 2024, ICLR 2025)

---

## Training Techniques

### Pre-Training Objectives
| Objective | Model | Prompt Lesson |
|-----------|-------|---------------|
| MLM (15% masked) | BERT | Bidirectional context matters |
| CLM (next token) | GPT/Claude | Earlier information has more influence |
| Span Corruption | T5 | Multi-word gaps > single-token gaps |
| Replaced Token Detection | ELECTRA | Negative examples are more efficient |
| SOP (Sentence Order) | ALBERT | Information order carries meaning |

### Alignment Techniques
- **RLHF** — Human preference pairs train reward model + PPO. (Ouyang et al. 2022)
- **DPO** — Direct optimization on preferred/dispreferred pairs, no reward model. Simpler, more stable. Used by LLaMA 3.1. (Rafailov et al. 2023)
- **GRPO** — Group sampling + relative comparison. DeepSeek-R1 achieved 71% AIME from 15.6% with pure RL. (DeepSeek-AI 2025)
- **Constitutional AI / RLAIF** — AI feedback guided by explicit principles. (Bai et al. 2022, Anthropic)
- **RLVR** — RL with verifiable rewards (math, code). Clear success criteria improve output.
- **Instruction Tuning** — 1,800+ tasks with natural instructions = zero-shot generalization. (Wei et al. 2022)

### Efficiency
- **LoRA/QLoRA** — 0.01-1% trainable params. Requires open-weight models. (Hu et al. 2022)
- **Knowledge Distillation** — Small model mimics large. LIMA: 1,000 quality examples suffice. (Hinton et al. 2015)
- **MoE** — Specialized experts, 1-2 active per token. Nearly all frontier open models use MoE now.
- **Test-Time Compute** — Longer reasoning chains at inference. "Think step by step" is the prompt version. (DeepSeek-R1, OpenAI o1)

---

## Prompt Engineering Paradigms

### Currently Used in Ludi-Bot (BERT-derived)
1. Label Space First, 2. Sentence-Pair (text_a/text_b), 3. Few-Shot (3-5), 4. Token Budget, 5. NSP Gate, 6. Domain Pre-training, 7. Knowledge Distillation (partial), 8. Parse Logging, 9. Negative Few-Shot (partial)

### Not Yet Used — High Potential
| Technique | Source | What It Does | Ludi-Bot Application |
|-----------|--------|-------------|---------------------|
| Chain-of-Thought | Wei et al. 2022 | Show reasoning traces before answer | Curation grades — force explicit reasoning |
| Many-Shot ICL | Google DeepMind 2024 | 50-100 examples >> 3-5 | 9,293 settled bets as example bank for curation |
| Response Prefilling | Anthropic API | Start assistant message mid-JSON | Eliminate curation parse failures |
| Self-Consistency | Wang et al. 2023 | N answers → majority vote | Backtest validation runs |
| Debate/Adversarial | TradingAgents 2024 | Bull/bear before decision | Maren strategist pattern |
| Reflexion | Shinn et al. 2023 | Reflect on failures → memory → retry | MEMORY.md → curation injection |
| Least-to-Most | Zhou et al. 2023 | Easy→hard sub-problems | Complex multi-player injury scenarios |
| Skeleton-of-Thought | 2024 | Outline first, fill in parallel | Game notes generation |

### Emerging 2024-2025
- **Graph-of-Thought** — Arbitrary graph reasoning (merge/split/loop nodes). Research-stage.
- **Chain-of-X** — 40+ variants: Chain-of-Symbol, Chain-of-Knowledge, Chain-of-Verification, Chain-of-Note. (ACL 2025 survey)
- **Skeleton-of-Thought** — Generate outline → parallel fill. Reduces latency.

---

## Domain-Specific Research Findings

### Sports Analytics
- **Calibration > Accuracy** — Calibration-optimized models: +34.69% ROI. Accuracy-optimized: -35.17% ROI. 69.86% higher returns. (ML in Sports Betting, 2024)
- **SportQA** — LLMs lag humans on complex scenario reasoning. Validates "LLMs orchestrate, never calculate." (NAACL 2024)
- **LLM-as-Prophet** — LLMs show decent calibration but fail near resolution time. (Oct 2025)
- **NBA Uncertainty Quantification** — Direct relevance to Module C confidence intervals. (2024)

### Structured Data + LLMs
- **LLM-as-Judge biases** — Position bias (earlier items graded higher), verbosity bias, self-enhancement bias. Fix: randomize order, multi-trait specialization. (Dec 2024 survey)
- **Hallucination prevention** — Decompose→verify claims, constraint validation gates, multi-agent verification.
- **Serialization consistency** — Format consistency > specific format choice. Our `_format_player_block()` is correct.

### Multi-Model Patterns
- **Cascade routing validated** — 40% cost reduction at equivalent quality. Our Haiku→Sonnet cascade is correct. (PMLR 2025, C3PO)
- **LLM Debate overconfidence** — Models start 72.9% confidence (rational: 50%), increase to 83%. Never trust raw LLM confidence in debate. (May 2025)
- **TF-IDF example selection** — Outperforms random and semantic embedding for ICL. (Few-Shot Dilemma, 2025)
- **Many-Shot ICL** — 50-1000 examples >> few-shot for structured tasks. (Google DeepMind, 2024)

---

## Recommended Actions (Ranked)

### Tier 1 — Immediate
1. **Brier Score in backtest** — calibration is the #1 predictor of betting profitability
2. **Randomize bet order in Sonnet curation** — removes position bias (trivial)
3. **Response prefilling** — start assistant message with `{"` for JSON compliance

### Tier 2 — Next Sprint
4. **Many-Shot ICL** — `_select_icl_examples()` from 9,293 historical bets, TF-IDF selection
5. **CoT in curation** — explicit reasoning trace before grade
6. **Expand Pattern 9** (negative few-shot) to curation + injury parsing

### Tier 3 — Future
7. **Debate pattern** for Maren — with external calibration, not raw LLM confidence
8. **Reflexion** — inject "what went wrong" from memory into curation
9. **Post-generation numerical verification** — parse JSON output, verify numbers match input

---

## Key Academic Sources
- Devlin et al. 2018 (BERT) | Liu et al. 2019 (RoBERTa) | Clark et al. 2020 (ELECTRA)
- He et al. 2021 (DeBERTa, ICLR) | Brown et al. 2020 (GPT-3) | Raffel et al. 2020 (T5)
- Gu & Dao 2023 (Mamba) | Lieber et al. 2024 (Jamba, ICLR 2025)
- Rafailov et al. 2023 (DPO) | DeepSeek-AI 2025 (GRPO/R1) | Bai et al. 2022 (Constitutional AI)
- Wei et al. 2022 (Chain-of-Thought) | Wei et al. 2022 (FLAN instruction tuning)
- Wang et al. 2023 (Self-Consistency) | Shinn et al. 2023 (Reflexion)
- Google DeepMind 2024 (Many-Shot ICL) | ACL 2025 (Chain-of-X survey)
- NAACL 2024 (SportQA) | ML in Sports Betting 2024 (Calibration > Accuracy)
- PMLR 2025 (C3PO cascade) | Dec 2024 (LLM-as-Judge survey)
