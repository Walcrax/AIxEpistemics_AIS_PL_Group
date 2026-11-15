# Proposed To-Do List (Remaining Tasks Before Submission)

Status as of **2026-11-15**: All 4 target model evaluations (`grok-4.6`, `kimi-k3`, `mistral-small-3.1-24b`, `qwen-3.8-27b`), substitute judge runs, hedge-only rewrites, and noise-floor neutral reruns are **complete and committed** under `outputs/`.

Below is the checklist of remaining items needed to complete the action board in `sprint_doc.md` and satisfy `prereg/preregistration.md`.

---

## 1. Blind Human Labelling & Cohen's $\kappa$ (`sprint_doc.md` Row 14 — *In progress*)

- [ ] **Agree on the numeric threshold for `"often differ"` before unblinding:**
  - Both `sprint_doc.md` and `data/labels/README.md` note that `prereg/preregistration.md` does not fix a numeric cutoff for when conclusions `"often differ"`. Record the agreed threshold before inspecting `data/labels/label_key.csv` or comparing exported label files.
- [ ] **Finish blind labelling (60 pairs, 2 labellers):**
  - Export `hedgehack_labels_<name>.json` from `data/labels/labeling_offline.html` (or the online page).
- [ ] **Write label-scoring script (e.g., `scripts/score_labels.py`) and record results:**
  - Verify `pairs_sha256` against `data/labels/label_pairs.json`.
  - Join the two labellers' exports with `data/labels/label_key.csv`.
  - Compute **Cohen's $\kappa$** and the rate of `"different"` substantive conclusions overall, per model (15 pairs each), and split by the 30 `FINAL`-agree vs. 30 `FINAL`-differ pairs.

---

## 2. Formal Pre-Registered H1–H3 Statistical Analysis Script (`sprint_doc.md` Row 15 — *Not started*)

All required input files exist (`outputs/full_api/judged.jsonl`, `outputs/full_api/known_results.jsonl`, `outputs/full_local_mistral/{judged.jsonl,pipeline_results.jsonl}`, `outputs/full_local_qwen/{judged.jsonl,pipeline_results.jsonl}`, and `outputs/hedge_only/judged.jsonl`), but the formal analysis script referenced in `docs/full_run.md` is not yet in `scripts/`:

- [ ] **Implement synchronized 2,000-draw bootstrap (`prereg/preregistration.md`, "Measures"):**
  - Use the **exact same 2,000 proposition resamples** across all 4 models and conditions (`neutral`, `hedge_hack`, `hedge_only`), and 2,000 item resamples for the 80 SycoBench known items (`seed 20261114`).
  - Compute both **pooled** (mean across the 4 models, used for hypothesis decisions) and **per-model** estimates with 95% percentile bootstrap intervals (no $p$-values).
- [ ] **H1 (`Exploit gain` & `Style effect`):**
  - Canonical Pander Score ($\times 100$) differences: `neutral − hedge_hack` (exploit gain) and `neutral − hedge_only` (style effect), evaluated against the pre-registered bands ($>5$, $>0$ including $5$, $(0,5)$, or includes $0$).
- [ ] **H2 (`Agreement change`, `Known-item change`, and descriptive `Flip rate`):**
  - `Agreement change`: percentage-point shift in `FINAL: TRUE` (`hedge_hack − neutral`) on the 504 Pander prompts, tested for equivalence within $\pm M = \pm 10\text{ pp}$.
  - `Known-item change`: percentage-point shift in accuracy (`hedge_hack − neutral`) on the 80 SycoBench items, tested within $\pm M = \pm 10\text{ pp}$.
  - Descriptive paired `FINAL:` flip rate vs. each model's neutral rerun noise floor (`16.7%` API, `0.0%` Mistral same-Mac, `8.3%` Qwen same-PC).
- [ ] **H3 (`Linear-scale prose vs. patched scores` & `Gain closed`):**
  - Per proposition, regress outcome on author valence ($0\text{–}1$, no logit), average slopes weighted by surviving prompts ($\times 100$), for both consensus judge credence (prose score) and `FINAL: TRUE = 1, FALSE = 0` (patched score).
  - Compute `Gain closed` $= 1 - (\text{exploit gain of patched score} \div \text{exploit gain of prose score})$ (if H1 interval $> 0$).
- [ ] **Exclusions & drop-rate reporting (`prereg/preregistration.md`, "Exclusions and reporting"):**
  - Tabulate per model and condition (`neutral`, `hedge_hack`, `hedge_only`): judge disagreement drops ($>0.2$ apart), uninformative drops, surviving prompt counts, propositions with $<4$ surviving prompts (if any), and `FINAL:` parse rates.

---

## 3. Figures for the Paper (`sprint_doc.md` Row 16 — *Not started*)

- [ ] **Write figure-generation script (e.g., `scripts/make_figures.py` $\rightarrow$ `figures/`):**
  - **Figure 1 (H1):** Canonical Pander Score under `neutral`, `hedge_only`, and `hedge_hack` (per model + pooled, with 95% bootstrap CIs), illustrating how much of the exploit gain is pure hedging style.
  - **Figure 2 (H2):** Equivalence plot of `Agreement change` and `Known-item change` against the $\pm 10\text{ pp}$ equivalence bounds ($M=10$), alongside paired flip rates vs. same-machine neutral noise floors.
  - **Figure 3 (H3):** Linear-scale prose vs. forced-choice patched valence slopes across the 4 models.

---

## 4. Paper Manuscript & Required Appendix (`sprint_doc.md` Rows 17–19, 21 — *Not started*)

- [ ] **Methods and results draft:** Include the documented deviations (`Gateway substitute judges`, `42 propositions for budget`, and `Deviation 1: known-item Stage 2 prompt fix`) and exact local Ollama GGUF/Modelfile specs (`docs/local_models.md`).
- [ ] **Related work & limitations:** Include partial unblinding of hedge-hack style during human labelling, non-zero temperature-0 batching noise on CUDA (`max_connections=4`), and low baseline sycophancy on `grok-4.6` / `kimi-k3` / `qwen-3.8-27b` relative to `mistral-small-3.1-24b`.
- [ ] **Dual-Use and Ethics Appendix (*Required*):** Document responsible disclosure / maintainer notification and why we evaluate a diagnostic defense (Stage 2 forced-choice patch) rather than releasing an optimized adversarial attack set.
- [ ] **Abstract (150–250 words) & final PDF ($\le 8$ pages on official template).**

---

## 5. Repository Freeze & Root `README.md` Cleanup (`sprint_doc.md` Row 20 — *Not started*)

- [ ] **Update `README.md` before final freeze:**
  - Update the status table (`prereg-final` tagged; full runs, rewrites, and noise reruns completed).
  - Update budget note (`$150` $\rightarrow$ `$285`).
  - Add `data/full_run/`, `data/labels/`, `data/pilot/`, `docs/full_run.md`, `docs/local_models.md`, `docs/pilot.md`, `outputs/`, and the new pipeline/analysis scripts to the repository layout section while keeping pre-existing vs. sprint-written code clearly marked.
