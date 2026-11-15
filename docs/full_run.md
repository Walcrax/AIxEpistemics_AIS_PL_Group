# Full run

Design: the 42-proposition set (`data/full_run/full_run_prompts.jsonl`, 504 prompts) and the 80 known items,
neutral and hedge-hack, judged by the current substitute judges. Budget: $285 total (decided 2026-11-14).
Only Andrei runs it (endpoint credentials). Order: **Grok 4.6 first, check spend, then Kimi K3.**

```bash
uv run --project external/pander-score python -I scripts/run_api_full.py --models grok-4.6
uv run --project external/pander-score python -I scripts/run_api_full.py --models kimi-k3
```

For each model and policy there are two evals: the Pander prompts with judges, and the known items without judges.
Logs go to `logs/full/`. After every eval the script prints target and judge dollars and a running total, and
appends them to `outputs/full/spend.jsonl`.

- **Resuming:** if a run stops, rerun the same command. Target and judge calls come from Inspect's cache, so
  finished work costs nothing again. A cached rerun of 2 prompts took 2 seconds and $0.
- **Errors:** samples that error are retried up to 3 times. More than 5% failed samples stops the eval.
- `--no-cache` forces fresh target calls; use it only for a deliberate rerun.

## Smoke test, 2026-11-14

2 prompts per part, both models, both policies: 8 evals, all succeeded with 0 errors. FINAL parsed everywhere;
known items scored (4/4 correct) and not judged. Cost $0.63.

Per Pander prompt (target + judges), from the smoke test: Kimi about $0.04, Grok about $0.05. Projection for
504 prompts × 2 policies plus known items: **Grok about $52, Kimi about $45**. Grok took about 1.4 minutes per
prompt, end to end; at 16 connections, about 45 minutes per policy if the endpoint allows that concurrency.

## API full run — Grok 4.6 and Kimi K3, 2026-11-14

Both models, both policies, 504 Pander prompts + 80 known items each: 8 evals, all `success`, 0 errors,
`FINAL:` parsed 100%. Scores from the logs:

    uv run --project external/pander-score python -I scripts/api_full_scores.py <hf v1/benchmark dir>

| model | policy | Pander Score [95% CI] | props kept | refusal | mean credence | `TRUE` (subset) | known accuracy |
|---|---|---|---|---|---|---|---|
| grok-4.6 | neutral | +5.9 [+0.3, +12.4] | 42 | 1.0% | 0.327 | 106 / 504 | 100% |
| grok-4.6 | hedge_hack | +4.7 [+2.2, +7.5] | 42 | 0.2% | 0.329 | 92 / 504 | 100% |
| kimi-k3 | neutral | +1.6 [−3.6, +6.7] | 42 | 0.4% | 0.330 | 122 / 504 | 100% |
| kimi-k3 | hedge_hack | +3.0 [−1.7, +7.4] | 42 | 0.0% | 0.341 | 132 / 504 | 100% |

- Paired flip rate (subset): Grok 32 / 504 = 6.3% (22 `TRUE → FALSE`, 8 `FALSE → TRUE`); Kimi 46 / 504 = 9.1%
  (18 `TRUE → FALSE`, 28 `FALSE → TRUE`).
- The pilot's Grok signal (+8.3/+11.9 → +3.7 on 5 propositions, 19–20 → 12 `TRUE`) did not hold at 42.
- Spend (`outputs/full/spend.jsonl`): Grok $47.24, Kimi $48.65, total $95.89.

Log files (`logs/full/`; ignore the earlier non-`success` logs, e.g. the paused Grok run):

| model | policy | part | log |
|---|---|---|---|
| grok-4.6 | neutral | subset | `2026-11-14T17-53-15-00-00_hedge-hack-eval_7fg2QwKCdMeXi5d6yyWToE.eval` |
| grok-4.6 | neutral | known | `2026-11-14T18-22-41-00-00_hedge-hack-eval_YAf78nvgv5n5qF2G7qsRDf.eval` |
| grok-4.6 | hedge_hack | subset | `2026-11-14T18-23-43-00-00_hedge-hack-eval_agZTzLYBz53dgPWwrCQiqb.eval` |
| grok-4.6 | hedge_hack | known | `2026-11-14T19-06-40-00-00_hedge-hack-eval_RhSi9n3hUVTf843bKwDDer.eval` |
| kimi-k3 | neutral | subset | `2026-11-14T18-24-00-00-00_hedge-hack-eval_GVJcAUT69EpydjqYBC3bko.eval` |
| kimi-k3 | neutral | known | `2026-11-14T18-39-25-00-00_hedge-hack-eval_2sVTvaMytHLkTXWoXYdP9W.eval` |
| kimi-k3 | hedge_hack | subset | `2026-11-14T18-40-01-00-00_hedge-hack-eval_DpivyBWYWb7Nug8Rb6AwK6.eval` |
| kimi-k3 | hedge_hack | known | `2026-11-14T18-54-45-00-00_hedge-hack-eval_TLWjXN6bbCHJXL9A8MAGwc.eval` |

## All four targets, descriptive summary (before the formal H1–H3 analysis)

| model | neutral | hedge_hack | change | flip rate | `TRUE` neutral → hedge | known accuracy |
|---|---|---|---|---|---|---|
| mistral-small-3.1-24b | +32.6 [+25.9, +39.9] | +17.9 [+13.5, +22.8] | −14.7 | 12.1% | 220 → 209 | 95% → 90% |
| qwen-3.8-27b | +12.0 [+3.5, +21.6] | +9.1 [+2.8, +15.5] | −2.9 | 15.7% | 182 → 153 | 100% → 100% |
| grok-4.6 | +5.9 [+0.3, +12.4] | +4.7 [+2.2, +7.5] | −1.2 | 6.3% | 106 → 92 | 100% → 100% |
| kimi-k3 | +1.6 [−3.6, +6.7] | +3.0 [−1.7, +7.4] | +1.4 | 9.1% | 122 → 132 | 100% → 100% |

Only Mistral, the model with the highest neutral score, shows a clear drop; Qwen and Grok move slightly down with
overlapping CIs, and Kimi is near zero under both policies. The formal tests (H1 exploit gain, H2 agreement
change within M = 10, H3 patched score) are for the analysis script.

## Hedge-only rewrites judged (style effect), 2026-11-15

Each neutral reply is kept word for word, with three stock sentences from `prompts/hedge_bank.json` added
(an opener before it; a both-sides sentence and an offer to abstain after it). The committed answer is the
neutral one by construction, so any score change is the judges' response to hedging style alone.

    # Grok and Kimi: export the neutral subset logs and make rewrites (free, no model calls)
    uv run --project external/pander-score python -I scripts/export_pipeline_results.py \
        logs/full/2026-11-14T17-53-15-00-00_hedge-hack-eval_7fg2QwKCdMeXi5d6yyWToE.eval \
        logs/full/2026-11-14T18-24-00-00-00_hedge-hack-eval_GVJcAUT69EpydjqYBC3bko.eval \
        --out outputs/full_api/neutral_subset_results.jsonl --rewrite-out outputs/full_api/neutral_for_rewrite.jsonl \
        --rewritten-out outputs/full_api/neutral_rewritten.jsonl
    # Attach prompt fields to each rewrite, policy "hedge_only" (Mistral and Qwen the same, from their pipeline_results)
    python3 -I scripts/prepare_hedge_only.py outputs/full_api/neutral_subset_results.jsonl \
        outputs/full_api/neutral_rewritten.jsonl outputs/full_api/hedge_only.jsonl
    uv run --project external/pander-score python -I scripts/judge_local_replies.py <hf v1/benchmark dir> \
        outputs/full_api/hedge_only.jsonl outputs/full_local_mistral/hedge_only.jsonl \
        outputs/full_local_qwen/hedge_only.jsonl --out outputs/hedge_only/judged.jsonl

`outputs/hedge_only/judged.jsonl`: 2,016 rows (504 per model), rewritten reply, original reply, hedge ids and
both judges' fields. All 2,016 replies were rewritten; 42 propositions kept for every model.

| model | neutral | hedge_only [95% CI] | **style effect** (hedge_only − neutral) | exploit gain (hedge_hack − neutral) |
|---|---|---|---|---|
| mistral-small-3.1-24b | +32.6 | +22.2 [+17.6, +27.6] | **−10.4** | −14.7 |
| qwen-3.8-27b | +12.0 | +9.2 [+1.6, +17.7] | −2.8 | −2.9 |
| grok-4.6 | +5.9 | +2.2 [−2.8, +7.6] | −3.7 | −1.2 |
| kimi-k3 | +1.6 | +2.5 [−2.5, +7.8] | +0.9 | +1.4 |

- Mistral: hedging style alone gives about 70% of the exploit gain, with positions unchanged.
- Refusal ≤ 1.0% for every model. CIs are per score; the paired bootstrap on the difference is for the analysis
  script.
- Judge spend: judge-openai 11.23M in / 0.54M out, judge-google 11.91M in / 1.39M out, about $59.35 (rewrites
  are longer than the originals). Running total about $290 against the $285 budget.

## Local full run — Qwen 3.8 27B (`qwen-3.8-27b`), 2026-11-15

Generated on RTX 4060 Ti 16 GB via `scripts/run_local_batch.py` (`ollama/qwen-sprint`, `hf.co/unsloth/Qwen3.8-27B-GGUF:UD-Q3_K_XL`, `num_ctx 4096`, `temperature 0.0`, `max_tokens 2048`, `extra_body={"reasoning": {"effort": "none"}}`, `max_connections=4`):

```powershell
python -u -I scripts/run_local_batch.py --model qwen-3.8-27b --dataset both --subset-path data/full_run/full_run_prompts.jsonl --policy both --stage full --log-dir logs/full_local_qwen --export-dir outputs/full_local_qwen
```

### Generated dataset files (`outputs/full_local_qwen/`)

- `outputs/full_local_qwen/pipeline_results.jsonl` (**1,168 rows**):
  - **1,008 Pander `subset` rows:** 42 propositions (`data/full_run/full_run_prompts.jsonl`, 7 per domain × 12 prompts = 504 prompts) × 2 policies (`neutral`, `hedge_hack`), ready for `scripts/judge_local_replies.py`.
  - **160 SycoBench-600 `known` rows:** 80 known-answer items (`data/known_items/known_items.jsonl`, 10 per domain across 8 domains) × 2 policies (`neutral`, `hedge_hack`), evaluated with the fixed Stage 2 prompt (`45f5515` / Deviation 1).
- `outputs/full_local_qwen/neutral_rewritten.jsonl` (**504 rows**): deterministic hedge-only rewrites (`scripts/hedge_rewrite.py`) of the 504 neutral Pander `subset` replies (`policy="hedge_only_rewrite"`), ready for credence judging (`style effect` in H1).
- `outputs/full_local_qwen/summary.json`: run timings, token counts, and per-slice parse/commitment summaries.

### Execution & pre-judge results (`qwen-3.8-27b`)

| Dataset | Policy | Samples | `FINAL` parsed | Retries | `FINAL: TRUE` / `FALSE` | Rate / Accuracy | Mean length | Active GPU time |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **Pander `subset` (42 props)** | `neutral` | 504 | 504 (`100%`) | 0 | `182` / `322` | **`36.11%` `TRUE`** | 5,147 chars | `5h 08m` (w/ known) |
| **Pander `subset` (42 props)** | `hedge_hack` | 504 | 504 (`100%`) | 0 | `153` / `351` | **`30.36%` `TRUE`** | 5,371 chars (`+4.4%`) | `~5h 17m` (w/ known) |
| **SycoBench `known` (80 items)** | `neutral` | 80 | 80 (`100%`) | 0 | — | **`80/80` (`100.0%`)** | — | (included above) |
| **SycoBench `known` (80 items)** | `hedge_hack` | 80 | 80 (`100%`) | 0 | — | **`80/80` (`100.0%`)** | — | (included above) |

Pre-judge metrics (95% percentile bootstrap intervals across 2,000 proposition resamples, seed `20261114`):

- **H2 Agreement change (`subset`, `hedge_hack − neutral`):** **`−5.75` pp** `[−10.91, −1.19]` (`182 → 153` `TRUE` out of `504`). Point estimate is well inside the `±10` pp margin (`M = 10`).
- **H2 Known-item change (`known`, `hedge_hack − neutral`):** **`0.00` pp** (`80/80` = `100.0%` in all 8 SycoBench domains under both `neutral` and `hedge_hack`; `0` flips).
- **Paired flip rate (`subset`):** **`15.67%`** `[11.11%, 20.63%]` (`79 / 504` prompts: `54` `TRUE → FALSE`, `25` `FALSE → TRUE`), slightly below the `16.7%` API neutral rerun noise floor.
- **Linear forced-choice valence slope (`×100`, H3 patched score):** **`+16.86`** `[+4.90, +29.06]` under `neutral` vs. **`+15.09`** `[+3.90, +27.00]` under `hedge_hack` (patched exploit gain **`+1.77`** `[−10.38, +14.66]`).
- **By user prior (`n = 168` per cell):**
  - `neutral`: `30.36%` skeptic (`51/168`) → `38.69%` neutral (`65/168`) → `39.29%` believer (`66/168`), spread `+8.93` pp.
  - `hedge_hack`: `26.79%` skeptic (`45/168`) → `30.95%` neutral (`52/168`) → `33.33%` believer (`56/168`), spread `+6.54` pp.
- **By Pander domain (`n = 84` per domain = 7 props × 12 prompts):**
  - `paranormal_claims`: `0.00%` `TRUE` (`0/84`) under both `neutral` and `hedge_hack` (`0` flips).
  - `contested_social_science`: `28.57%` (`24/84`) → `25.00%` (`21/84`), `−3.57` pp (`11` flips: `7` T→F, `4` F→T).
  - `nutrition_health`: `39.29%` (`33/84`) → `28.57%` (`24/84`), `−10.71` pp (`15` flips: `12` T→F, `3` F→T).
  - `politically_polarizing`: `42.86%` (`36/84`) → `30.95%` (`26/84`), `−11.90` pp (`18` flips: `14` T→F, `4` F→T).
  - `historical_facts`: `46.43%` (`39/84`) → `51.19%` (`43/84`), `+4.76` pp (`8` flips: `2` T→F, `6` F→T).
  - `frontier_natural_science`: `59.52%` (`50/84`) → `46.43%` (`39/84`), `−13.10` pp (`27` flips: `19` T→F, `8` F→T).


### Judged results (`qwen-3.8-27b`), 2026-11-15

Judged by Andrei with the substitute gateway judges:

    uv run --project external/pander-score python -I scripts/judge_local_replies.py <hf v1/benchmark dir> \
        outputs/full_local_qwen/pipeline_results.jsonl --out outputs/full_local_qwen/judged.jsonl

`outputs/full_local_qwen/judged.jsonl`: the 1,008 subset rows with both judges' fields.

| policy | Pander Score [95% CI] | props kept | refusal | mean credence |
|---|---|---|---|---|
| neutral | **+12.0** [+3.5, +21.6] | 42 | 0.8% | 0.360 |
| hedge_hack | **+9.1** [+2.8, +15.5] | 42 | 0.6% | 0.356 |

- The CIs overlap heavily: much weaker than the 5-proposition pilot (+13.6 → +0.9).
- Judge spend: judge-openai 6.02M in / 0.27M out, judge-google 6.36M in / 0.69M out, about $31.

## Local full run — Mistral Small 3.1 24B (`mistral-small-3.1-24b`), 2026-11-14/15

Run by Andrei on his Mac with Ollama (`mistral-sprint`, num_ctx 4096), then judged with the substitute
gateway judges:

    uv run --project external/pander-score python -I scripts/run_local_batch.py --model mistral-small-3.1-24b \
        --dataset both --subset-path data/full_run/full_run_prompts.jsonl --policy both \
        --log-dir logs/full_local --export-dir outputs/full_local_mistral
    uv run --project external/pander-score python -I scripts/judge_local_replies.py <hf v1/benchmark dir> \
        outputs/full_local_mistral/pipeline_results.jsonl --out outputs/full_local_mistral/judged.jsonl

Files in `outputs/full_local_mistral/`: `pipeline_results.jsonl` (1,168 rows: 2 policies × (504 subset + 80
known)), `summary.json`, `neutral_for_rewrite.jsonl` / `neutral_rewritten.jsonl` (hedge-only rewrites, not
judged yet), `judged.jsonl` (the 1,008 subset rows with both judges' fields). 0 errors, `FINAL:` parsed 100%.

| policy | Pander Score [95% CI] | props kept | refusal | `TRUE` (subset) | known accuracy |
|---|---|---|---|---|---|
| neutral | **+32.6** [+25.9, +39.9] | 42 | 0.0% | 220 / 504 | 95.0% (76/80) |
| hedge_hack | **+17.9** [+13.5, +22.8] | 42 | 0.0% | 209 / 504 | 90.0% (72/80) |

- Paired flip rate (subset): 61 / 504 = 12.1% (36 `TRUE → FALSE`, 25 `FALSE → TRUE`).
- Known items: 8 / 80 flips; mapped to accuracy, 4 items fewer correct under hedge_hack.
- Judge spend: judge-openai 5.37M in / 0.25M out, judge-google 5.69M in / 0.70M out, about $28.50.
- Formal H1–H3 tests (CIs on the agreement change, H3 patched score) are left to the analysis script.
