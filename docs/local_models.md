# Local Ollama Models and Two-Stage Pipeline Setup

This guide documents the local Ollama setup (Task 3) and the two-stage forced-choice Inspect
pipeline (Task 4) for the two local target models:

- `qwen-3.8-27b` -> Ollama `qwen-sprint` (`hf.co/unsloth/Qwen3.8-27B-GGUF:UD-Q3_K_XL`)
- `mistral-small-3.1-24b` -> Ollama `mistral-sprint` (`hf.co/bartowski/mistralai_Mistral-Small-3.1-24B-Instruct-2503-GGUF:IQ4_XS`)

## Key Findings & Design Fixes

1. **Disabling Qwen 3.8 hidden thinking without breaking Neutral prompts:**
   - Qwen 3.8 27B ignores `/no_think` `TEMPLATE` overrides in Modelfiles (which also violate the
     pre-registration rule that Neutral has **no system prompt**) and ignores `"think": false`.
   - `inspect_ai`'s `OllamaAPI` drops `GenerateConfig(reasoning_effort="none")`. Passing
     `extra_body={"reasoning": {"effort": "none"}}` in [`configs/models.yaml`](../configs/models.yaml)
     cleanly disables reasoning tokens while keeping the base GGUF `TEMPLATE` and `stop` tokens intact.
2. **VRAM fit & batch concurrency on a 16 GB GPU (RTX 4060 Ti):**
   - At the base `8192` context window, Mistral Small 3.1 spills partially to CPU (`5% CPU / 95% GPU`).
   - With `PARAMETER num_ctx 4096` in [`models/Modelfile.qwen`](../models/Modelfile.qwen) and
     [`models/Modelfile.mistral`](../models/Modelfile.mistral), both models fit **100% in GPU VRAM**
     (`13 GB` in `ollama ps`) while leaving plenty of context for long prompts, full Stage 1 replies,
     and the Stage 2 forced-choice follow-up.
   - Concurrent batching improves throughput nearly 2x over serial execution at `num_ctx 4096`:
     - `mistral-sprint`: `18.13 tok/s` (`concurrency=1`) -> `36.42 tok/s` (`concurrency=2`), `36.24 tok/s` (`concurrency=4`)
     - `qwen-sprint` (`reasoning.effort=none`): `16.84 tok/s` (`concurrency=1`) -> `30.68 tok/s` (`concurrency=2`), `31.11 tok/s` (`concurrency=4`)
   - [`scripts/run_local_batch.py`](../scripts/run_local_batch.py) executes one model at a time
     (keeping that model resident in VRAM across both `neutral` and `hedge_hack` runs) with
     `max_connections=4`.
3. **Pre-registered two-stage separation:**
   - Stage 1 preserves `neutral` (no system prompt) and `hedge_hack` (exact SHA-256 verified text
     of [`prompts/hedge_hack_system.txt`](../prompts/hedge_hack_system.txt)) and leaves
     `state.messages` and `state.output` untouched for Pander's `credence_scorer`.
   - Stage 2 creates a fresh **no-system-prompt** conversation `[User(original_prompt), Assistant(stage1_reply), User(forced_choice)]`, supporting both `FINAL: TRUE` / `FINAL: FALSE` (Pander propositions) and `FINAL: A|B|C|D` (SycoBench known items), with one clean retry on parse failure.

## Quick Commands

Create or refresh the local Ollama tags from the repo Modelfiles and verify readiness:

```powershell
python -I scripts/local_models.py --setup-modelfiles --check
```

Run a fast mixed smoke test (2 subset propositions + 2 known-answer items across both models and both policies):

```powershell
python -I scripts/run_local_batch.py --dataset smoke
```

Run the 5-proposition local pilot matching [`scripts/run_api_pilot.py`](../scripts/run_api_pilot.py) (`240` samples -> `logs/pilot_local/` and `outputs/pilot_local/`, ready for `scripts/judge_local_replies.py`; see [`docs/pilot.md`](pilot.md)):

```powershell
python -I scripts/run_local_batch.py --dataset subset --subset-path data/pilot/pilot_prompts.jsonl --policy both --log-dir logs/pilot_local --export-dir outputs/pilot_local
```

Or generate a slice dynamically via `--props 5` / explicit proposition IDs:

```powershell
python -I scripts/run_local_batch.py --props 5
python -I scripts/run_local_batch.py --proposition-ids prop_id_1 prop_id_2 ...
```

Run Stage A (`4x2x4` slice) or the full 720-prompt Pander subset + 80 known items:

```powershell
python -I scripts/run_local_batch.py --dataset subset --only-4-2-4 --policy both
python -I scripts/run_local_batch.py --dataset subset --policy both
python -I scripts/run_local_batch.py --dataset known --policy both
```

Resume an interrupted Inspect `.eval` log without re-running completed samples:

```powershell
inspect eval-retry logs\<unfinished_log>.eval
```

Export `.eval` logs into normalized JSONL, Neutral inputs, and offline hedge-only rewrites:

```powershell
python -I scripts/export_pipeline_results.py logs --out outputs/pipeline_results.jsonl --rewrite-out outputs/neutral_for_rewrite.jsonl --rewritten-out outputs/neutral_rewritten.jsonl
```
