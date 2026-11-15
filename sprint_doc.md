# **Track 1 Project Ideas for the Apart AI x Epistemics Sprint (Nov 13–15, 2026):** 

## **Action board**

One row per task. A is pipeline and runs, B is items, prompts and labels, C is analysis and writing; swap the letters for names. Due slots work back from the submission deadline (Sun 15 Nov, 23:59 AoE).

| Task | Assignee | Status | Due | Notes |
| :---- | :---- | :---- | :---- | :---- |
| Pick two API models with high published Pander scores (not OpenAI or Google) and two open-weight models; check access | Andrei Iliescu | Done | Sat afternoon | API: Kimi K3, Grok 4.6 (access checked, see `docs/api_models.md`). Local: Qwen 3.8 27B (Q3), Mistral Small 3.1 24B (Kacper, Ollama). No per-provider cap: track spend against the budget |
| Clone the Pander code and data; confirm the licence and how to run a subset of propositions | Andrei Iliescu | Done | Sat afternoon | Judges: Pander's pinned GPT-5.4-mini and Gemini 3 Flash are not on our endpoint, so substitutes from the same families run there (`docs/api_models.md`, `scripts/gateway_judges.py`). Report as a methods deviation. Pinned commit in `docs/pander_setup.md` |
| Set up batched inference for the two local models | A | Done | Sat afternoon | `scripts/run_local_batch.py`: Ollama (Mistral, Andrei's Mac) and Kacper's setup (Qwen) |
| Forced-choice step and FINAL: parser in the Inspect pipeline | A | Done | Sat afternoon | Must read at least 95% of replies. `scripts/hedge_hack_pipeline.py`. Full runs: FINAL parsed 100% for all four models |
| Pick 60 domain-balanced propositions and 12 conversational prompts each (4 skeptic, 4 neutral, 4 believer) | Stanisław Słupski | Done | Sat afternoon | Seed 20261114; only prompts that pass the released screens; 6 domains × 10, moral claims excluded. Full run: 37 more picked 2026-11-14 to join the 5 pilot propositions, 42 in all (7 per domain; `data/full_run/`, `scripts/select_full_run.py`) |
| Sample 80 known-answer items from an existing sycophancy set | Stanisław Słupski | Done | Sat afternoon | SycoBench-600 (CC BY 4.0), 10 per domain, seed 20261114; data/known_items/ |
| Write the hedge-hack system prompt and the hedge-only rewrite script | B Andrei Iliescu Stanisław Słupski | Done | Sat afternoon | Rewrites must read naturally. `prompts/hedge_hack_system.txt`; rewrites by `scripts/hedge_rewrite.py` (deterministic: stock sentences from `prompts/hedge_bank.json` around the unchanged reply, no LLM, free). Mistral and Qwen rewrites in `outputs/full_local_*/neutral_rewritten.jsonl` |
| Commit H1 to H3, metrics, the ±10-point margin and the proposition IDs with a timestamp | Stanisław Słupski | Done | Before first full run | `prereg/preregistration.md`, tag `prereg-final`; Deviations 1 (known-item forced-choice wording) and 2 (pooling of gain closed) recorded |
| Pilot: 5 propositions per model; check scores against published ones, refusals below 5% and spend per model | A and C | Done (API models) | Sat evening | If a model costs far more than \$25, cut it to 40 propositions. API pilot passed all checks (`docs/pilot.md`): credences match references within 0.011, 0% refusals, FINAL 240/240. Targets project to about \$30 (Kimi) and \$35 (Grok) per model for both policies, before judges: decide on cuts once judge prices are known. Local models piloted and judged 2026-11-14: all checks pass (0% refusals, FINAL 240/240, 57-58/60 replies kept) |
| Full runs: API models, then local models | A | Done | Sat evening to Sun morning | Decided 2026-11-14: 42 propositions (7 per domain), not 60 (budget; ~\$67 spent on setup and pilot): the 5 pilot propositions plus 37 more from the subset. The full run reruns all 42; pilot runs are not reused. The list of 42 is fixed: `data/full_run/full_run_prompts.jsonl` (hash in the pre-registration). Decided 2026-11-14: keep the current judges, full design (4 models judged); **budget raised to \$285** (estimate: ~\$67 spent + ~\$218 for the full run at about \$0.028 per judged reply). Run Grok first and check spend before Kimi. **Done 2026-11-15:** all four models, both policies, 504 prompts + 80 known items each, judged; 0 errors. Results and four-model summary in `docs/full_run.md` |
| Judge the hedge-only rewrites (style effect): export neutral replies, run `scripts/hedge_rewrite.py`, judge with `scripts/judge_local_replies.py` | Andrei Iliescu | Done | Sun morning | Needs the judge credentials. About \$14 per model (504 replies × ~\$0.028). Mistral and Qwen rewrites exist; Grok and Kimi need theirs made first from the neutral logs (`scripts/export_pipeline_results.py`, free). All four ≈ \$56 vs ~\$54 left of \$285. **Done 2026-11-15:** all four judged, about \$59.35 (running total ~\$290 of \$285). Style effect: Mistral −10.4 (≈70% of its −14.7 exploit gain), Qwen −2.8, Grok −3.7, Kimi +0.9. `docs/full_run.md`, `outputs/hedge_only/judged.jsonl` |
| Noise floor: 60 neutral reruns and 50 re-judged replies per model | A | Done (reruns) | Sun morning | API pilot neutral rerun (run 2, same 60 prompts) for the H2 margin: M = pooled forced-choice flip rate between the two neutral runs, rounded up to a multiple of 5, between 5 and 10 (rule fixed before results). Per-prompt FINAL answers: `data/pilot/final_answers.csv`. Result: pooled flip rate 16.7% (Kimi 13/60, Grok 7/60), so **M = 10** (cap binds); recorded in the pre-registration. **Mistral rerun done 2026-11-15:** 0/60 flips between two neutral runs on the same machine (5% across machines) vs 9/60 under hedge-hack on the same prompts (`docs/full_run.md`). **Qwen rerun done 2026-11-15 (`outputs/noise_local/qwen/`):** 5/60 flips (8.3%) between neutral rerun and full-run neutral on the same PC (and 5/60 vs pilot neutral, 32/60 identical replies) vs 18/60 (30.0%) under hedge-hack on the same 60 prompts and 79/504 (15.7%) over the full set. Optional: re-judge 50 replies per model with the cache off (judge noise, ~\$6 on top of the ~\$5 overrun), else cite the ~2-point calibration estimate as approximate |
| Label 60 neutral and hedge-hack reply pairs blind to condition; kappa | B and C | Done | Sun morning | Half where forced choices agree, half where they differ. Page built 2026-11-15: https://claude.ai/artifact/5LH8bwuDPxpZAHNzfW4U81 (and offline in `data/labels/labeling_offline.html`). 60 pairs drawn by `scripts/make_label_pairs.py` (15 per model, 30 agree / 30 differ); see `data/labels/README.md`. Pre-set threshold: ≥ 20% `different` among forced-choice-agreeing pairs (excluding `cant_tell`). Result (`scripts/label_agreement.py`, `outputs/labels/agreement.md`): 18.9% [6.9%, 34.4%] (< 20%, H2 passes check); 3-way κ = 0.26, Same/Different κ = 0.39 |
| Analysis: exploit gain, style effect, behaviour change with equivalence test, gain closed; bootstrap intervals | Stanisław Słupski | Done | Sun morning | `scripts/analysis.py`, `outputs/analysis/results.{json,md}` (2,000 proposition-bootstrap draws, seed 20261114) |
| Figures | A | Done | Sun midday | `scripts/figures.py`, `outputs/analysis/figures/fig1_hypotheses.{pdf,png}` and `fig2_by_prior.{pdf,png}` |
| Methods and results draft | Stanisław Słupski | Done | Sun midday | Drafted in report |
| Related work, limitations, dual-use and ethics appendix | B | Done | Sun midday | Appendix is required; drafted in report |
| Abstract, 150 to 250 words | Stanisław Słupski | In progress | Sun afternoon |  |
| Freeze code; README marking any pre-existing code | A | Done | Sun afternoon | `README.md` updated with full status, layout, commands, and pre-existing code/data attributions |
| Final PDF on the official template, eight pages or fewer; submit | C Stanisław Słupski | In progress | Sun afternoon | Leave a few hours before the cutoff |

## **Hedge-Hack one-pager: can writing style alone lower a model's sycophancy score?**

Many epistemic benchmarks use an LLM judge to turn free text into a credence or a sycophancy label. We test whether a model can raise its judged score by changing how it writes rather than what it concludes, and whether scoring committed answers closes that gap. This is the track's fourth question: demonstrate an exploit and close it. The build is an inspect\_ai eval on 800 prompts and four models.

### **Hypotheses**

Commit these to the repo with a timestamp before the first full run.

| ID | Hypothesis | Measured by |
| :---- | :---- | :---- |
| H1 | A hedging system prompt improves the judge's honesty or non-sycophancy score by a meaningful margin. | Exploit gain, style effect |
| H2 | The same prompt leaves committed answers unchanged: forced-choice answers and accuracy on known-answer items stay within paraphrase noise. | Behaviour change |
| H3 | Scoring the forced-choice answer instead of the prose removes most of the gain in H1. | Gain closed |

### **Design**

1. **Benchmark.** A subset of the Pander Score pipeline (data CC-BY-4.0, code MIT), 60 propositions, 10 from each of six domains (moral claims excluded, since the Truth Matters screen removes most of that domain), with 12 screened conversational prompts each, 4 per prior (720 prompts), scored with its own judge setup. The full run uses 42 of them, 7 per domain (504 prompts): the 5 pilot propositions plus 37 more. All runs add 80 known-answer items from an existing sycophancy set in which the user asserts a wrong answer.  
2. **Policies.** Each model runs under a neutral system prompt and a hedge-hack prompt that asks for calibrated-sounding qualifiers, both-sides phrasing and an offer to abstain, without asking it to change its conclusion.  
3. **Hedge-only control.** A script adds the same hedges to the neutral replies and changes nothing else. The judge's score change on these rewrites is the pure style effect.  
4. **Patch.** After each reply, a fresh-context forced choice asks the model which answer is correct and ends with FINAL: \<option\>. The patched score uses only these committed answers and accuracy on the known items.

**Models and size.** Two API models with high published Pander scores, from families other than the judges', and two open-weight models run locally with batched inference; temperature 0 where the API allows it. With 42 propositions, 584 prompts (504 + 80 known items) × 2 policies × 4 models gives 4,672 replies and as many forced-choice calls. (The original plan was 60 propositions, 6,400 replies and about \$95. Judge prompts turned out about 5,500 tokens each and the endpoint judges cost more than planned, so the full design no longer fits the budget; see the board and `docs/pilot.md`.)

### **Metrics and analysis**

Committed answers are scored by parsing FINAL:; prose is scored by the benchmark's judge.

| Metric | Definition | For |
| :---- | :---- | :---- |
| Exploit gain | Judged score under the hedge-hack prompt minus under the neutral prompt | H1 |
| Style effect | Judged score on the hedge-only rewrites minus on the original neutral replies | H1 |
| Behaviour change | Forced-choice answers and known-item accuracy under hedge-hack minus neutral | H2 |
| Gain closed | Share of the exploit gain that disappears under the patched score | H3 |

**Validation and statistics.** Two of us read 60 neutral and hedge-hack reply pairs, blind to condition, and label whether the substantive conclusion differs; Cohen's kappa. If conclusions often differ, H2 fails as stated and we report that the prompt changes behaviour. 95% intervals from a proposition-clustered bootstrap, pooled and per model.

### **Pilot checks and limits**

**Saturday pilot** on 5 propositions for each of the four models checks that our re-run of the Pander pipeline gives scores close to that model's published score on our 720 prompts, for any model the paper also reports, that the hedge-hack prompt keeps refusals below 5%, that spend per model matches the estimate, and that the parser reads FINAL: in 95% of forced-choice replies.

**Limits.** One benchmark and one judge show that the gap can exist, not how large it is elsewhere; a null result still serves as a robustness audit of that benchmark. The method is dual-use, so we contact the benchmark's maintainers before publishing, describe the prompt without releasing an optimised attack set, and say so in the ethics appendix.

### **Prior work**

Raina et al. (arXiv 2402.14016) show that universal adversarial phrases inflate LLM-judge scores. Goodfire finds verbalised eval awareness raises refusal rates by 3 to 18 points on Fortress, and arXiv 2510.08624 finds presentation prompts change hedging without improving answers. The safetywashing paper (arXiv 2407.21792) and LURE (arXiv 2605.26438) address benchmarks that measure the wrong thing and models that recognise tests. None of these targets judges of honesty or sycophancy specifically.

