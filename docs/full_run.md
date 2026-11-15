# Full run (API models)

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

