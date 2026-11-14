# Hedge-Hack: can writing style alone raise a model's honesty score?

Apart AI x Epistemics sprint, 13–15 November 2026 (Track 1). AIS PL group: Andrei Iliescu, Stanisław Słupski, Kacper.

Many epistemic benchmarks use an LLM judge to turn free text into a credence or a sycophancy label. We test whether a
system prompt that asks for hedged, both-sides, calibrated-sounding prose raises a model's judged score on the
[Pander Score](https://arxiv.org/abs/2606.07897) benchmark without changing its committed answers, and whether
scoring a fresh-context forced choice (`FINAL: <option>`) closes the gap.

The plan, hypotheses (H1–H3), metrics and task board are in [`sprint_doc.md`](sprint_doc.md), the source of truth.

## Status

| Piece | State | Where |
|---|---|---|
| Pander Score clone, licence, subset scoring path | done | [`docs/pander_setup.md`](docs/pander_setup.md) |
| 60 propositions × 12 prompts (4/4/4, 6 domains × 10, seed 20261114) | done | [`data/subset/`](data/subset/README.md) |
| API target models: Kimi K3, Grok 4.6 | done | [`docs/api_models.md`](docs/api_models.md) |
| Local models: Qwen 3.8 27B (Q3), Mistral Small 3.1 24B, via Ollama | done (batched runner + Modelfiles) | [`docs/local_models.md`](docs/local_models.md), `scripts/local_models.py`, `scripts/run_local_batch.py` |
| Hedge-hack system prompt and hedge-only rewrite script | done | [`prompts/`](prompts/), `scripts/hedge_rewrite.py` |
| 80 known-answer items for H2 (SycoBench-600, 10 per domain, seed 20261114) | done | [`data/known_items/`](data/known_items/README.md) |
| Pre-registration (H2 margin and forced-choice wording open until the pilot) | draft committed | [`prereg/preregistration.md`](prereg/preregistration.md) |
| Forced-choice step and parser | done | `scripts/hedge_hack_pipeline.py`, `scripts/export_pipeline_results.py` |
| Pilot, full runs, analysis, paper | not started | |

## Repository layout

```
sprint_doc.md                      plan, hypotheses, action board
configs/models.yaml                API target aliases and model families
data/subset/                       the 720-prompt subset (Inspect JSONL + CSV index) and its README
data/known_items/                  the 80 known-answer items for H2 (Inspect JSONL + CSV index) and their README
prereg/preregistration.md          hypotheses, measures, decision rules; open items fixed after the pilot
prompts/hedge_hack_system.txt      the hedge-hack system prompt (the neutral arm has none)
prompts/hedge_bank.json            hedge sentences for the hedge-only control
docs/pander_setup.md               Pander Score clone, licence, how subsets are run and scored
docs/api_models.md                 API model choice, settings, cost check
scripts/select_propositions.py     regenerate the subset from the Hugging Face release
scripts/check_subset_scores.py     published models' scores on our subset (pilot references)
scripts/seed_baseline.py           is our seeded draw typical? (100 other seeds)
scripts/pander_inventory.py        prompt counts and screen survival per proposition
scripts/pander_subset_score.py     earlier subset-rule check on published outputs
scripts/api_models.py              resolve API target aliases to Inspect models
scripts/api_smoke.py               one short call per API model
scripts/select_known_items.py      draw the 80 known-answer items from SycoBench-600
scripts/hedge_rewrite.py           hedge-only control: add bank sentences to neutral replies, reply kept verbatim
external/pander-score/             upstream clone (gitignored, not edited)
external/sycobench-600/            upstream clone for the known items (gitignored, not edited)
```

## Setup

Python tooling runs in the Pander Score project environment (Python ≥ 3.13, `uv`).

```bash
# 1. Upstream benchmark at the pinned commit (see docs/pander_setup.md)
git clone https://github.com/sophronresearch/pander-score external/pander-score
git -C external/pander-score checkout 18e4684dd80efd2f3a6baccce5ff3be407c3e2c8
uv sync --project external/pander-score

# 2. Published outputs and prompt attributes (Hugging Face, pinned revision)
uv run --project external/pander-score hf download sophronresearch/pander-score \
    --repo-type dataset --revision 233e697f341d63d52d406dd0c5f8b838c4bee671
BENCH=$(ls -d ~/.cache/huggingface/hub/datasets--sophronresearch--pander-score/snapshots/*/v1/benchmark)

# 3. Secrets
cp .env.example .env   # fill in the providers you use; never commit .env
```

Running the Pander credence judges needs OpenAI and Google keys, whatever the target model.

## Common commands

```bash
# Regenerate the subset (checks input hashes against the release manifest)
uv run --project external/pander-score python -I scripts/select_propositions.py "$BENCH"

# Published models' scores on our 720 prompts, zero API calls
uv run --project external/pander-score python -I scripts/check_subset_scores.py "$BENCH"

# Check API model access (under 1 cent)
uv run --project external/pander-score python -I scripts/api_smoke.py
```

Scripts that read third-party data run with `python -I` and take paths as arguments.

## Budget and safety rules

- Total budget $150. Never launch the full 11,172-prompt Pander run; always stage a subset JSONL.
- Only Andrei runs the API models. Their endpoint, credentials and model mapping live in his local `.env` only and
  must not appear in the repo, eval logs or shared output.
- The method is dual-use: we describe the hedge-hack prompt but don't release an optimised attack set, and we contact
  the benchmark's maintainers before publishing (see the ethics appendix).

## Pre-existing code and data

- `external/pander-score/` is the upstream Pander Score code (MIT, © 2026 The Pander Score contributors), used unchanged
  and not committed here.
- `data/subset/` is adapted from the Pander Score v1 dataset (CC BY 4.0): a selection with added metadata fields; prompt
  text and original fields are unchanged. Details in [`data/subset/README.md`](data/subset/README.md).
- `scripts/check_subset_scores.py` reimplements the upstream conversational estimator (`src/pander_score/core/metrics.py`).
  `scripts/api_models.py` and `scripts/pander_subset_score.py` import upstream functions.
- Everything else in this repository was written during the sprint.

Cite the benchmark as: Botas, de Font-Reaulx and Hewitt, *Pander Score*, arXiv 2606.07897 (see
`external/pander-score/CITATION.cff`).
