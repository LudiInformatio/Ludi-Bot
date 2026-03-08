# Canonical LLM Training Methodologies — Research Reference

**Created:** March 8, 2026
**Purpose:** Comprehensive lookup table of academic LLM training paradigms, their origins, and applicability to Ludi-Bot
**Source session:** ULTRATHINK research sprint — 3 parallel agents, 30+ academic papers, 15+ architectures

---

## Model Architectures

### Encoder-Only (Bidirectional — Understanding)

| Model | Year | Key Innovation | Training Objective | Prompt Lesson | Key Paper |
|-------|------|---------------|-------------------|---------------|-----------|
| **BERT** | 2018 | Bidirectional context via masked tokens | MLM (mask 15% of tokens, predict from both sides) + NSP | Surrounding context matters — structure prompts with context on BOTH sides of the question | Devlin et al. 2018 |
| **RoBERTa** | 2019 | Removed NSP (it was noise), dynamic masking, larger batches | MLM only (no NSP) | Don't add artificial "next sentence" framing — just provide content directly | Liu et al. 2019 |
| **ALBERT** | 2020 | Parameter sharing + Sentence Order Prediction (SOP) | MLM + SOP | Example ordering matters (easy→hard > random) | Lan et al. 2020, ICLR 2020 |
| **ELECTRA** | 2020 | Discriminator classifies EVERY token as real/fake (not just 15% masked) | Replaced Token Detection | Negative/contrastive examples are 4× more training-efficient than positive-only | Clark et al. 2020 |
| **DeBERTa** | 2021 | Disentangled attention (content vs position as separate vectors) | MLM + disentangled attention | Prompt STRUCTURE (headers, XML tags) matters independently from content quality | He et al. 2021, ICLR 2021 |

### Decoder-Only (Autoregressive — Generation)

| Model | Year | Key Innovation | Training Objective | Prompt Lesson | Key Paper |
|-------|------|---------------|-------------------|---------------|-----------|
| **GPT-2** | 2019 | Showed unsupervised pre-training → zero-shot transfer | CLM (predict next token, left→right) | Prompt order is critical — earlier tokens influence output more | Radford et al. 2019 |
| **GPT-3** | 2020 | In-context learning (few-shot works without fine-tuning) | CLM at 175B scale | 3-5 examples in-context can match fine-tuning for many tasks | Brown et al. 2020 |
| **GPT-4** | 2023 | Multimodal (text+image), RLHF alignment | CLM + RLHF | Aligned models follow complex multi-step instructions | OpenAI 2023 |
| **LLaMA 3** | 2024 | RoPE, GQA, 15T+ tokens, open-weight | CLM | Knowledge distillation works (3.3 70B matches 405B) — methodology > scale | Meta 2024 |
| **Mistral 7B** | 2023 | Sliding Window Attention, outperforms 13B models | CLM + SWA | Efficiency-first design — smaller models with better architecture beat larger naive ones | Jiang et al. 2023 |
| **Mixtral 8x7B** | 2024 | Mixture of Experts (47B total, 13B active) | CLM + sparse MoE routing | Specialized sub-networks > monolithic; maps to our multi-employee architecture | Jiang et al. 2024 |
| **Phi-3** | 2024 | "Textbook-quality" synthetic data, 3.8B rivals 10× larger | CLM on curated data | Data QUALITY beats quantity — 3 perfect examples > 10 mediocre ones | Abdin et al. 2024 |
| **DeepSeek-R1** | 2025 | Pure RL → emergent chain-of-thought reasoning | CLM + GRPO | CoT reasoning emerges from training on verifiable rewards — "think step by step" works because it aligns with how reasoning-trained models process | DeepSeek-AI 2025 |

### Encoder-Decoder (Sequence-to-Sequence)

| Model | Year | Key Innovation | Training Objective | Prompt Lesson | Key Paper |
|-------|------|---------------|-------------------|---------------|-----------|
| **T5** | 2020 | ALL tasks as text-to-text ("translate: X" → "Y") | Span corruption (mask multi-word spans, decoder generates them) | Every task as "given input, produce output" — clear task framing = better results | Raffel et al. 2020 |
| **FLAN-T5** | 2022 | T5 fine-tuned on 1,800+ tasks with natural instructions | Span corruption + instruction tuning | The more your prompt resembles instruction-tuning data (clear task + input + format), the better | Chung et al. 2022 |
| **BART** | 2020 | Denoising autoencoder (corrupt input → reconstruct) | Denoising (mask, delete, shuffle, rotate) | Multiple corruption strategies > single; varied examples > uniform | Lewis et al. 2020 |

### Non-Transformer (Emerging)

| Model | Year | Key Innovation | Training Objective | Prompt Lesson | Key Paper |
|-------|------|---------------|-------------------|---------------|-----------|
| **Mamba** | 2023 | State Space Model — O(n) vs transformer O(n²), 5× throughput | Selective state space modeling | Hybrid SSM+attention (7:1 ratio) emerging as optimal. Signals future architecture direction | Gu & Dao 2023 |
| **Jamba** | 2024 | First production hybrid (Mamba + Transformer + MoE), 52B/12B active | Hybrid SSM+attention+MoE | Pure transformers are not the endgame — hybrid architectures are coming | Lieber et al. 2024, ICLR 2025 |

---

## Training Techniques

### Pre-Training Objectives

| Objective | Used By | Tokens Trained Per Pass | Bidirectional? | Key Insight |
|-----------|---------|------------------------|----------------|-------------|
| **MLM** (Masked Language Model) | BERT, RoBERTa, ALBERT | 15% | Yes | Deep bidirectional understanding, but wasteful (85% of tokens unused per pass) |
| **CLM** (Causal Language Model) | GPT, LLaMA, Claude | 100% | No (left→right only) | Efficient (every token is a prediction target) but can't "look ahead" |
| **Span Corruption** | T5 | ~15% (multi-word spans) | Encoder: yes, Decoder: no | More natural than single-token masking — real information gaps are multi-word |
| **Replaced Token Detection** | ELECTRA | 100% | Yes | Best of both worlds — 100% of tokens, bidirectional. 4× more sample-efficient than MLM |
| **SOP** (Sentence Order Prediction) | ALBERT | N/A (binary task) | Yes | ORDER of information carries meaning beyond the content itself |
| **Denoising** | BART, UL2 | Variable | Encoder: yes | Multiple corruption types = more robust representations |

### Alignment & Post-Training

| Technique | What It Does | Requires Training? | Prompt-Level Equivalent | Key Paper |
|-----------|-------------|-------------------|------------------------|-----------|
| **RLHF** | Human preference pairs → reward model → PPO optimization | Yes (GPU cluster) | Aligned prompts ("be helpful, precise") work because model was trained this way | Ouyang et al. 2022 (InstructGPT) |
| **DPO** | Direct optimization on preferred/dispreferred pairs, no reward model | Yes (simpler than RLHF) | **Negative few-shot** — showing wrong outputs alongside correct mirrors DPO training | Rafailov et al. 2023 |
| **GRPO** | Group sampling + relative comparison within group, no reward model | Yes (pure RL) | CoT prompting works because reasoning-trained models process this way | DeepSeek-AI 2025 |
| **Constitutional AI / RLAIF** | AI self-critiques against explicit principles | Yes (Anthropic) | **System prompts with explicit rules** ARE prompt-level Constitutional AI | Bai et al. 2022 (Anthropic) |
| **RLVR** | RL with objectively verifiable rewards (math, code, logic) | Partially | Clear success criteria in prompts (JSON schema, checkable facts) mirror RLVR signals | Emerging 2024-2025 |
| **Instruction Tuning** | Fine-tune on 1,800+ tasks with natural language instructions | Yes | Clear task description + input + expected format = resembles instruction-tuning data | Wei et al. 2022 (FLAN) |

### Efficiency & Scaling

| Technique | What It Does | Trainable Params | Prompt-Level Use? | Key Insight |
|-----------|-------------|-----------------|-------------------|-------------|
| **LoRA** | Inject small trainable matrices into attention layers | 0.01-1% | No (requires model access) | Understanding why instruction-tuned ≠ base model |
| **QLoRA** | LoRA + 4-bit quantization | 0.01-1% on 4-bit | No | Consumer GPU fine-tuning is accessible but NOT needed for API users |
| **Knowledge Distillation** | Small model mimics large model | Student model only | **Yes — Pattern 7** (Sonnet→Haiku) | LIMA finding: 1,000 quality examples = massive datasets. Quality > quantity |
| **MoE** (Mixture of Experts) | Specialized sub-networks, 1-2 active per token | All experts | No (architecture-level) | Explains why some large models are fast — only a fraction activates per token |
| **Test-Time Compute** | Longer reasoning chains at inference | None (inference-time) | **Yes** — "think step by step", `<thinking>` tags | Trade speed for accuracy. DeepSeek-R1, OpenAI o1/o3 |

---

## Prompting Paradigms

### Currently Used in Ludi-Bot (BERT-Derived, Patterns 1-9)

| # | Pattern | Source Concept | Status | Primary File |
|---|---------|---------------|--------|-------------|
| 1 | Label Space First | `DataProcessor.get_labels()` | ✅ Done | `curate_plays.py`, `claude_prompts.py` |
| 2 | Sentence-Pair (text_a/text_b) | BERT `InputExample` two-sequence | ✅ Done | `claude_prompts.py` templates |
| 3 | Few-Shot (3-5 examples) | BERT 3-epoch convergence | ✅ Done | `claude_prompts.py`, `curate_plays.py` |
| 4 | Token Budget | `max_seq_length` truncation | ✅ Done | `morning_brief.py` |
| 5 | NSP Relevance Gate | Next Sentence Prediction | ✅ Done | `morning_brief.py` |
| 6 | Domain Pre-training | Domain-specific corpus injection | ✅ Done | `curate_plays.py` WR context |
| 7 | Knowledge Distillation | Teacher-student (large→small) | 🟡 Partial | Phase 8.23 Layer 1 collecting |
| 8 | Output Contract Validation | `assert len == max_seq_length` | ✅ Done | `curate_plays.py` parse logging |
| 9 | Negative Few-Shot | ELECTRA replaced token detection | 🟡 Partial | `classify_archetypes.py` only |

### New Paradigms Identified (Patterns 10-16, Phase 9)

| # | Pattern | Source | What It Does | Ludi-Bot Application | Effort |
|---|---------|--------|-------------|---------------------|--------|
| 10 | Chain-of-Thought (CoT) | Wei et al. 2022 | Force reasoning traces before output | Curation: require `"thinking"` field before `"grade"` | Low |
| 11 | Many-Shot ICL | Google DeepMind 2024 | 50-100 examples >> 3-5 for structured tasks | `_select_icl_examples()` from 9,293+ settled bets | Medium |
| 12 | Response Prefilling | Anthropic API | Start assistant message mid-JSON to force format | `assistant_prefill='[{"bet_id":'` eliminates parse failures | Low |
| 13 | Self-Consistency | Wang et al. 2023 | Generate N answers, take majority vote | Backtest: run curation 3×, check grade agreement | Medium |
| 14 | Debate / Adversarial | TradingAgents 2024 | Bull vs bear arguments before final decision | Maren strategist: opposing cases before curation grade | Medium |
| 15 | Reflexion | Shinn et al. 2023 | Reflect on failures → store in memory → retry with wisdom | Inject yesterday's STRONG+LOSS mistakes into curation prompt | Medium |
| 16 | Confidence Scoring | LLM-as-Judge 2024 | Every output gets uncertainty level | All employees: HIGH/MEDIUM/LOW confidence on every output | Low |

---

## Domain-Specific Research Findings

### Sports Analytics + Betting

| Finding | Source | Impact | Ludi-Bot Action |
|---------|--------|--------|-----------------|
| **Calibration > accuracy** — calibration-optimized models: +34.69% ROI vs accuracy-optimized: -35.17% ROI | ML in Sports Betting 2024 | CRITICAL | Brier Score as primary backtest metric |
| LLMs lag humans on complex sports scenario reasoning | SportQA, NAACL 2024 | Validates architecture | "LLMs orchestrate, never calculate" confirmed |
| **Position bias** in LLM-as-Judge — items earlier in list get higher grades | LLM-as-Judge Survey, Dec 2024 | HIGH | Randomize bet order in Sonnet curation |
| LLM debate → **overconfidence** (72.9% → 83%, rational: 50%) | LLM Debate Study, May 2025 | WARNING | If debate pattern implemented, NEVER trust raw LLM confidence |
| TF-IDF example selection outperforms random and semantic embedding | Few-Shot Dilemma 2025 | MEDIUM | ICL example selection by stat+archetype similarity |
| Haiku→Sonnet cascade: **40% cost reduction at equivalent quality** | C3PO, PMLR 2025 | Validates architecture | Current Haiku→Sonnet cascade is academically validated |
| Many-shot (50-1000 examples) >> few-shot for structured tasks | Google DeepMind 2024 | HIGH | 9,293 settled bets = massive ICL example bank |

### Structured Data + LLMs

| Finding | Source | Ludi-Bot Impact |
|---------|--------|-----------------|
| Serialization consistency > specific format | Tabular LLM Survey 2024 | `_format_player_block()` canonical template is correct |
| Post-generation numerical verification prevents hallucination | Hallucination Survey 2024 | Add bet_id verification after JSON parse in curation |
| Multi-trait specialization improves grading | LLM-as-Judge 2024 | Consider separate edge/injury/matchup grades before composite |

### Math Calibration (ML, Not LLM)

| Technique | Replaces | Source Data | Expected Impact |
|-----------|---------|-------------|-----------------|
| **Isotonic regression** per stat | Static 19%/14% deflators in Module F | 9,293+ settled bets | +0.5-1.2% CLV |
| **Per-stat variance** (MLE) | Uniform SIM_VARIANCE=0.35 in Module C | 30K+ game logs | +0.3-0.5 RMSE pts |
| **Bayesian season blending** | Hardcoded 15-game threshold in Module C | 30K+ game logs | +0.1-0.3 pts thin-sample |
| **K-means defense clustering** | 30 hardcoded team scheme assignments | Tracking data (team_lineups) | +0.4-0.8 matchup accuracy |
| **Asymmetric vig estimation** | Symmetric devigging in Module F | 100-day odds history | +0.2-0.5 edge pts |
| **Learned absorption rates** | 60%/30% hardcoded in Module X | 10,669 WOWY lineup rows | +0.3-0.7 pts beneficiaries |

---

## Academic Sources (Full Bibliography)

### Model Architecture Papers
- Devlin et al. 2018 — "BERT: Pre-training of Deep Bidirectional Transformers"
- Liu et al. 2019 — "RoBERTa: A Robustly Optimized BERT Pretraining Approach"
- Lan et al. 2020 — "ALBERT: A Lite BERT for Self-supervised Learning" (ICLR 2020)
- Clark et al. 2020 — "ELECTRA: Pre-training Text Encoders as Discriminators"
- He et al. 2021 — "DeBERTa: Decoding-enhanced BERT with Disentangled Attention" (ICLR 2021)
- Brown et al. 2020 — "Language Models are Few-Shot Learners" (GPT-3)
- OpenAI 2023 — "GPT-4 Technical Report"
- Meta 2024 — "Llama 3" (and Llama 3.3 distillation)
- Jiang et al. 2023 — "Mistral 7B"
- Jiang et al. 2024 — "Mixtral of Experts"
- Abdin et al. 2024 — "Phi-3 Technical Report"
- Raffel et al. 2020 — "Exploring the Limits of Transfer Learning with T5"
- Chung et al. 2022 — "Scaling Instruction-Finetuned Language Models" (FLAN-T5/PaLM)
- Lewis et al. 2020 — "BART: Denoising Sequence-to-Sequence Pre-training"
- Gu & Dao 2023 — "Mamba: Linear-Time Sequence Modeling with Selective State Spaces"
- Lieber et al. 2024 — "Jamba: A Hybrid Transformer-Mamba Language Model" (ICLR 2025)

### Training Technique Papers
- Ouyang et al. 2022 — "Training language models to follow instructions with human feedback" (InstructGPT)
- Rafailov et al. 2023 — "Direct Preference Optimization: Your Language Model is Secretly a Reward Model"
- DeepSeek-AI 2025 — "DeepSeek-R1: Incentivizing Reasoning Capability via Reinforcement Learning"
- Bai et al. 2022 — "Constitutional AI: Harmlessness from AI Feedback" (Anthropic)
- Wei et al. 2022 — "Finetuned Language Models Are Zero-Shot Learners" (FLAN)
- Hinton et al. 2015 — "Distilling the Knowledge in a Neural Network"
- Hu et al. 2022 — "LoRA: Low-Rank Adaptation of Large Language Models"

### Prompting Technique Papers
- Wei et al. 2022 — "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
- Yao et al. 2023 — "Tree of Thoughts: Deliberate Problem Solving with Language Models"
- Wang et al. 2023 — "Self-Consistency Improves Chain of Thought Reasoning"
- Shinn et al. 2023 — "Reflexion: Language Agents with Verbal Reinforcement Learning"
- Yao et al. 2023 — "ReAct: Synergizing Reasoning and Acting in Language Models"
- Google DeepMind 2024 — "Many-Shot In-Context Learning"
- ACL 2025 — "Survey of Chain-of-X Paradigms"

### Domain-Specific Papers
- SportQA (NAACL 2024) — LLM sports reasoning benchmark
- ML in Sports Betting (2024) — Calibration vs accuracy for ROI
- LLM-as-Judge Survey (Dec 2024) — Position bias, verbosity bias
- LLM Debate Overconfidence (May 2025) — 72.9% → 83% confidence inflation
- Few-Shot Dilemma (2025) — TF-IDF selection outperforms random
- C3PO (PMLR 2025) — Cost-constrained cascade routing
- TradingAgents (Dec 2024) — Multi-agent trading framework

---

*Research conducted March 8, 2026 — 3 parallel agents, 6+ hours research time, 30+ academic sources*
