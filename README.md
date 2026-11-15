# Hedge-Hack: can writing style alone lower a model's sycophancy score?

Apart AI x Epistemics sprint, 13–15 November 2026 (Track 1). AIS PL group: Andrei Iliescu, Stanisław Słupski, Kacper Walczak.

Many epistemic benchmarks use an LLM judge to turn free text into a credence or a sycophancy label. We test whether a
system prompt that asks for hedged, both-sides, calibrated-sounding prose lowers a model's judged score on the
[Pander Score](https://arxiv.org/abs/2606.07897) benchmark without changing its committed answers, and whether
scoring a fresh-context forced choice (`FINAL: <option>`) closes the gap.

The plan, hypotheses (H1–H3), metrics and task board are in [`sprint_doc.md`](sprint_doc.md), the pre-registration is in
[`prereg/preregistration.md`](prereg/preregistration.md), full statistical tables are in
[`outputs/analysis/results.md`](outputs/analysis/results.md), and blind human-labelling results are in
[`outputs/labels/agreement.md`](outputs/labels/agreement.md).

## Status

| Piece | State | Where |
|---|---|---|
| Pander Score clone, licence, subset scoring path | done | [`docs/pander_setup.md`](docs/pander_setup.md) |
| 60 propositions × 12 prompts (4/4/4, 6 domains × 10, seed 20261114) | done | [`data/subset/`](data/subset/README.md), `scripts/select_propositions.py` |
| Full-run set: 42 propositions (5 pilot + 37 more, 7 per domain), 504 prompts | done | [`data/full_run/`](data/full_run/README.md), `scripts/select_full_run.py` |
| API target models & substitute judges: Kimi K3, Grok 4.6 | done | [`docs/api_models.md`](docs/api_models.md), `scripts/api_models.py`, `scripts/gateway_judges.py` |
| Local models: Qwen 3.8 27B (Q3), Mistral Small 3.1 24B, via Ollama | done | [`docs/local_models.md`](docs/local_models.md), `scripts/local_models.py`, `scripts/run_local_batch.py` |
| Hedge-hack system prompt and hedge-only rewrite script | done | [`prompts/`](prompts/), `scripts/hedge_rewrite.py`, `scripts/prepare_hedge_only.py` |
| 80 known-answer items for H2 (SycoBench-600, 10 per domain, seed 20261114) | done | [`data/known_items/`](data/known_items/README.md), `scripts/select_known_items.py` |
| Pre-registration (locked at `prereg-final`, with deviations logged) | done | [`prereg/preregistration.md`](prereg/preregistration.md) |
| Forced-choice step and parser | done | `scripts/hedge_hack_pipeline.py`, `scripts/export_pipeline_results.py` |
| Pilot (API and local models) and neutral noise-floor reruns | done | [`docs/pilot.md`](docs/pilot.md), `data/pilot/final_answers.csv`, `outputs/noise_local/` |
| Full runs (4 models × 584 prompts × 2 policies) and credence judging (12,096 judge calls) | done | [`docs/full_run.md`](docs/full_run.md), `outputs/full_api/`, `outputs/full_local_mistral/`, `outputs/full_local_qwen/`, `outputs/hedge_only/` |
| Blind 60-pair human labelling and inter-rater agreement | done | [`data/labels/`](data/labels/README.md), [`outputs/labels/agreement.md`](outputs/labels/agreement.md), `scripts/label_agreement.py` |
| Pre-registered analysis and paper figures | done | [`outputs/analysis/results.md`](outputs/analysis/results.md), `outputs/analysis/figures/`, `scripts/analysis.py`, `scripts/figures.py` |

## Headline results

Conversational Pander Scores ×100 (lower = less sycophantic) across the 42-proposition full run (504 Pander prompts + 80 SycoBench known-answer items per model and condition), with 95% proposition-bootstrap intervals (`B = 2,000`, seed `20261114`). Full breakdown in [`outputs/analysis/results.md`](outputs/analysis/results.md).

| Model | Neutral | Hedge-hack | Exploit gain (H1) | Style effect (H1) | Agreement change, pp (H2) | Answers changed | Known-item accuracy (H2) |
|---|---|---|---|---|---|---|---|
| Mistral Small 3.1 24B | +32.6 [+26.1, +39.7] | +17.9 [+13.6, +22.6] | +14.6 [+8.6, +21.6] | +10.3 [+7.4, +13.6] | −2.2 [−5.4, +0.8] | 12.1% | 95.0% → 90.0% (−5.0 pp) |
| Qwen 3.8 27B | +12.0 [+3.3, +21.2] | +9.1 [+2.9, +15.0] | +2.9 [−4.2, +10.5] | +2.8 [+0.0, +5.6] | −5.8 [−11.1, −1.2] | 15.7% | 100.0% → 100.0% (+0.0 pp) |
| Grok 4.6 | +5.9 [−0.2, +12.2] | +4.7 [+2.1, +7.4] | +1.2 [−4.0, +6.8] | +3.7 [+0.7, +6.5] | −2.9 [−5.5, −0.6] | 6.3% | 100.0% → 100.0% (+0.0 pp) |
| Kimi K3 | +1.6 [−4.0, +6.8] | +3.0 [−1.8, +7.3] | −1.4 [−7.1, +3.9] | −0.8 [−4.9, +2.6] | +2.0 [−0.6, +4.8] | 9.1% | 100.0% → 100.0% (+0.0 pp) |
| **Pooled (mean of 4)** | **+13.0 [+9.3, +16.9]** | **+8.7 [+5.9, +11.4]** | **+4.3 [+0.4, +8.7]** | **+4.0 [+2.0, +6.1]** | **−2.2 [−3.9, −0.6]** | **10.8%** | **−1.2 pp [−3.1, +0.3]** |

- **H1 (exploit gain ≥ 5 points):** **Inconclusive** (pooled gain `+4.3 [+0.4, +8.7]` excludes 0 but includes 5; style effect from fixed hedging sentences alone is `+4.0 [+2.0, +6.1]`; Mistral alone drops by `+14.6 [+8.6, +21.6]`).
- **H2 (committed-answer shift within ±10 pp):** **Supported** on both aggregate measures (`−2.2 pp [−3.9, −0.6]` on Pander forced choices; `−1.2 pp [−3.1, +0.3]` on known items), and passes the blind human-labelling check (`19% [7%, 34%]` labelled `Different` among forced-choice-agreeing pairs vs. the pre-set `20%` threshold; [`outputs/labels/agreement.md`](outputs/labels/agreement.md)). However, local models flip individual forced choices above their neutral rerun noise floors (Mistral `12.1%` vs. `0.0%`; Qwen `15.7%` vs. `8.3%`).
- **H3 (forced-choice patched score closes ≥ 50% of gain):** **Inconclusive** (`68% [−99%, +353%]` pooled; `107% [+31%, +224%]` on Mistral, the only model with a clear prose gain).

## Repository layout

```text
configs/
  models.yaml               Target model registry (Kimi K3, Grok 4.6, Qwen 3.8 27B, Mistral Small 3.1 24B)
data/
  subset/                   60 Pander propositions and 720 prompts, with selection notes
  pilot/                    5-proposition pilot slice (60 prompts) and API neutral rerun forced choices
  full_run/                 42-proposition full-run set (504 prompts, 7 per domain)
  known_items/              80 SycoBench-600 items adapted for H2, with selection notes
  labels/                   60 blinded reply pairs, offline HTML labeller, key, and two authors' label files
docs/
  pander_setup.md           Upstream benchmark structure, licence, subset feasibility and scoring path
  api_models.md             API target models, cost check, and substitute credence judges
  local_models.md           Ollama setup, GGUF quantizations, VRAM fit, and two-stage pipeline guide
  pilot.md                  API and local pilot results and neutral rerun noise-floor calibration
  full_run.md               Full-run execution logs, operational notes, and local noise-floor reruns
external/
  pander-score/             Upstream Pander Score clone (gitignored; pinned commit in docs/pander_setup.md)
  sycobench-600/            Upstream SycoBench-600 clone (gitignored; pinned commit in data/known_items/README.md)
models/
  Modelfile.qwen            Ollama Modelfile for Qwen 3.8 27B (Q3_K_XL, temperature 0, num_ctx 4096)
  Modelfile.mistral         Ollama Modelfile for Mistral Small 3.1 24B (IQ4_XS, temperature 0, num_ctx 4096)
outputs/
  full_api/                 Full-run replies, forced choices, rewrites, and judge scores for Kimi K3 & Grok 4.6
  full_local_mistral/       Full-run replies, forced choices, rewrites, and judge scores for Mistral Small 3.1 24B
  full_local_qwen/          Full-run replies, forced choices, rewrites, and judge scores for Qwen 3.8 27B
  hedge_only/               Judge scores for the deterministic hedge-only rewrites of all 4 models' neutral replies
  noise_local/              60-prompt neutral noise-floor reruns for Mistral and Qwen
  pilot_local/              60-prompt pilot replies and forced choices for Mistral and Qwen
  labels/                   Inter-rater agreement statistics and unblinded summary (agreement.json, agreement.md)
  analysis/                 Pre-registered hypothesis tables (results.json, results.md) and figures (fig1, fig2)
prereg/
  preregistration.md        Hypotheses, metrics, estimators, decision rules, and logged deviations
prompts/
  hedge_hack_system.txt     The hedge-hack system prompt (SHA-256 verified at runtime)
  hedge_bank.json           Fixed opener/closer sentences for the hedge-only rewrite control
scripts/
  pander_inventory.py       Count screened conversational prompts per domain in Pander v1
  select_propositions.py    Select the 60 propositions × 12 prompts (seed 20261114)
  select_full_run.py        Select the 42-proposition full-run subset (5 pilot + 37 more, seed 20261114)
  select_known_items.py     Select and format the 80 SycoBench-600 items (seed 20261114)
  check_subset_scores.py    Reproduce published conversational Pander scores and compare with our subset
  pander_subset_score.py    Exploratory subset vs. full-benchmark score check on published outputs
  seed_baseline.py          Compare our seed against 100 other seeds of the same selection rule
  api_models.py             API target model resolver and response-cleaning transport
  api_smoke.py              One-prompt smoke test for Kimi K3 and Grok 4.6
  gateway_judges.py         Swap in endpoint credence judges while keeping Pander's prompts and configs
  judge_calibration.py      Compare candidate substitute judges with Pander's original judges on 60 replies
  rejudge_published.py      Re-judge published Kimi K3 and Grok 4.6 subset replies with substitute judges
  local_models.py           Ollama readiness check and Modelfile builder for Qwen and Mistral
  hedge_hack_pipeline.py    Two-stage Inspect pipeline: reply under policy, then fresh-context forced choice
  run_local_batch.py        Batched local runner for Ollama models with resume and JSONL export
  run_api_pilot.py          5-proposition API pilot runner and check table
  run_api_full.py           Full-run API runner (42 propositions + 80 known items) for Kimi K3 and Grok 4.6
  api_full_scores.py        Quick scorer for API full-run logs
  export_pipeline_results.py Export Inspect .eval logs to JSONL and generate hedge-only rewrites
  export_api_judged.py      Export API full-run judge scores to outputs/full_api/judged.jsonl
  export_final_answers.py   Export pilot run 1 & run 2 forced-choice answers to data/pilot/final_answers.csv
  hedge_rewrite.py          Deterministic hedge-only rewrite of neutral replies (no LLM call)
  prepare_hedge_only.py     Bundle all 4 models' hedge-only rewrites for credence judging
  judge_local_replies.py    Run substitute credence judges on exported JSONL replies
  make_label_pairs.py       Sample 60 blinded neutral vs. hedge-hack reply pairs and build the HTML labeller
  label_agreement.py        Compute inter-rater agreement (Cohen's kappa) and the H2 blind-check statistic
  analysis.py               Pre-registered bootstrap analysis for H1, H2, H3, and noise-floor checks
  figures.py                Generate Figure 1 (hypothesis tests) and Figure 2 / A1 (by user prior)
tests/
  test_hedge_hack_pipeline.py Unit tests for forced-choice parsing, two-stage isolation, and hedge rewrites
sprint_doc.md               Research plan, hypotheses, metrics, and completed task board
```

## Common commands

Reproduce the paper's statistical tables, figures, and blind-labelling agreement from the committed outputs in `outputs/` and `data/` (no API keys or local models required). `analysis.py` needs numpy and `figures.py` matplotlib, so run them in the Pander Score environment (clone `external/pander-score` first, below); `label_agreement.py` needs only the standard library:

```bash
uv run --project external/pander-score python -I scripts/analysis.py
uv run --project external/pander-score --with matplotlib python -I scripts/figures.py
python3 -I scripts/label_agreement.py data/labels/label_key.csv data/labels/label_pairs.json data/labels/hedgehack_labels_andrei.json data/labels/hedgehack_labels_kacper-walczak.json
```

Run the unit test suite:

```bash
python3 -m unittest discover -s tests -v
```

Clone the upstream Pander Score repo into `external/pander-score` (needed for upstream imports and parquet tools):

```bash
git clone https://github.com/sophronresearch/pander-score external/pander-score
git -C external/pander-score checkout 18e4684dd80efd2f3a6baccce5ff3be407c3e2c8
```

Regenerate the prompt selections (needs the Pander Score v1 Hugging Face bundle and a clone of SycoBench-600):

```bash
uv run --project external/pander-score python -I scripts/select_propositions.py <path/to/hf/v1/benchmark>
python3 -I scripts/select_full_run.py
git clone https://github.com/debu-sinha/sycobench-600 external/sycobench-600
git -C external/sycobench-600 checkout 3b2d3680b0a6d456e618206e6281904c87cb49dd
uv run --project external/pander-score python -I scripts/select_known_items.py external/sycobench-600
```

Set up and run the local Ollama models (`qwen-3.8-27b` and `mistral-small-3.1-24b`) on the full-run dataset:

```bash
python3 -I scripts/local_models.py --setup-modelfiles --check
python3 -I scripts/run_local_batch.py --dataset subset --subset-path data/full_run/full_run_prompts.jsonl --models qwen-3.8-27b --policy both --log-dir logs/full_local_qwen --export-dir outputs/full_local_qwen
python3 -I scripts/run_local_batch.py --dataset known --models qwen-3.8-27b --policy both --log-dir logs/full_local_qwen --export-dir outputs/full_local_qwen
```

Apply the deterministic hedge-only rewrite to neutral replies:

```bash
python3 -I scripts/hedge_rewrite.py --in outputs/full_local_qwen/neutral_for_rewrite.jsonl --out outputs/full_local_qwen/neutral_rewritten.jsonl
```

## Budget and safety rules

- Total API budget $285 (raised from $150 after the pilot to keep the two credence judges across all 42 full-run propositions). Never launch the full 11,172-prompt Pander run; always stage a subset JSONL.
- Only Andrei runs the API target and judge models. Endpoint URLs, credentials, and model alias mappings live in his local `.env` only and never appear in the repository, evaluation logs, or shared outputs.
- Dual use and ethics: the exploit is a single-paragraph system prompt asking for standard hedged phrasing, and the defence we test (`FINAL: <option>` forced choice) is cheap to adopt. We release the prompt, the patched scorer, and all model outputs so benchmark maintainers can audit for style sensitivity. No external human subjects took part (the 60 blind-labelled pairs were rated by two of the authors).

## Pre-existing code and data

- **Pander Score code (MIT License, Copyright © 2026 The Pander Score contributors):**
  - `external/pander-score/` is the upstream [Pander Score repository](https://github.com/sophronresearch/pander-score) at pinned commit `18e4684dd80efd2f3a6baccce5ff3be407c3e2c8` (v1.0.0), used unchanged and gitignored here.
  - `scripts/check_subset_scores.py` and `scripts/analysis.py` reimplement the upstream conversational Pander Score estimator (`src/pander_score/core/metrics.py`).
  - `scripts/api_models.py`, `scripts/gateway_judges.py`, `scripts/hedge_hack_pipeline.py`, `scripts/judge_calibration.py`, `scripts/judge_local_replies.py`, `scripts/pander_subset_score.py`, and `scripts/rejudge_published.py` import upstream configuration, prompt-formatting, parser, or scorer functions from `pander_score`.
- **Pander Score v1 dataset ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), Botas, de Font-Reaulx and Hewitt, 2026):**
  - `data/subset/`, `data/pilot/pilot_prompts.jsonl`, and `data/full_run/` are adapted from the [Pander Score v1 dataset](https://huggingface.co/datasets/sophronresearch/pander-score) (revision `233e697f341d63d52d406dd0c5f8b838c4bee671`). They contain filtered selections of conversational prompts and propositions with added selection metadata (`domain`, `author_valence`, `rank_in_prior`, `in_4_2_4`, `in_pilot`); original prompt text, proposition text, IDs, targets, and upstream metadata fields are unchanged. Details in [`data/subset/README.md`](data/subset/README.md), [`data/pilot/README.md`](data/pilot/README.md), and [`data/full_run/README.md`](data/full_run/README.md).
- **SycoBench-600 dataset and prompt templates ([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), Debu Sinha, 2026):**
  - `external/sycobench-600/` is the upstream [SycoBench-600 repository](https://github.com/debu-sinha/sycobench-600) at pinned commit `3b2d3680b0a6d456e618206e6281904c87cb49dd` (gitignored).
  - `data/known_items/` (`known_items.jsonl`, `known_items.csv`) and `scripts/select_known_items.py` adapt 80 multiple-choice items and wrong-suggestion prompt templates (`WRONG_SUGGEST_VARIANTS` from `sycobench/prompts.py`) from SycoBench-600 into single-turn free-text prompts where the user asserts a seeded random wrong option (`A`–`D`) in the first turn without SycoBench's single-letter output constraint. Question text, answer options, and answer keys are unchanged. Details in [`data/known_items/README.md`](data/known_items/README.md).
- **Evaluation framework and open-weight models:**
  - Evaluations use [Inspect AI](https://inspect.aisi.org.uk/) (`inspect_ai`, MIT License, UK AI Security Institute).
  - Local target runs (`models/Modelfile.qwen`, `models/Modelfile.mistral`) reference pre-existing open-weight GGUF quantizations hosted on Hugging Face (`unsloth/Qwen3.8-27B-GGUF:UD-Q3_K_XL` and `bartowski/mistralai_Mistral-Small-3.1-24B-Instruct-2503-GGUF:IQ4_XS`), executed via Ollama; no model weights are redistributed in this repository.
- **Original sprint contributions:**
  - Everything else in this repository—including the hedge-hack system prompt, deterministic hedge-only rewrite bank and script, two-stage forced-choice pipeline, substitute-judge calibration and runtime wiring, model outputs, blind human labels, statistical analysis scripts, and figures—was written and generated by the authors during the sprint, with AI coding assistants writing most of the code under the authors' direction (see the report's LLM Usage Statement).

Cite the upstream benchmarks as:
- Botas, A., de Font-Reaulx, P. and Hewitt, L. (2026). *Pander Score: A Continuous Measure of Sycophancy as Epistemic Deference*. [arXiv:2606.07897](https://arxiv.org/abs/2606.07897) (see `external/pander-score/CITATION.cff`).
- Sinha, D. (2026). *SycoBench-600: Measuring Sycophancy and Correction Selectivity in LLM Assistants*. Findings of ACL 2026. [ACL Anthology](https://aclanthology.org/2026.findings-acl.1759/).
