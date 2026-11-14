# **Track 1 Project Ideas for the Apart AI x Epistemics Sprint (Nov 13–15, 2026):** 

## **Action board**

One row per task. A is pipeline and runs, B is items, prompts and labels, C is analysis and writing; swap the letters for names. Due slots work back from the submission deadline (Sun 15 Nov, 23:59 AoE).

| Task | Assignee | Status | Due | Notes |
| :---- | :---- | :---- | :---- | :---- |
| Pick two API models with high published Pander scores (not OpenAI or Google) and two open-weight models; check access | Andrei Iliescu | Done | Sat afternoon | API: Kimi K3, Grok 4.6 (access checked, see `docs/api_models.md`). Local: Qwen 3.8 27B (Q3), Mistral Small 3.1 24B (Kacper, Ollama). No per-provider cap: track spend against the budget |
| Clone the Pander code and data; confirm the licence and how to run a subset of propositions | Andrei Iliescu | In progress | Sat afternoon | Judges: Pander's pinned GPT-5.4-mini and Gemini 3 Flash are not on our endpoint, so substitutes from the same families run there (`docs/api_models.md`, `scripts/gateway_judges.py`). Report as a methods deviation |
| Set up batched inference for the two local models | A | Not started | Sat afternoon |  |
| Forced-choice step and FINAL: parser in the Inspect pipeline | A | Not started | Sat afternoon | Must read at least 95% of replies |
| Pick 60 domain-balanced propositions and 12 conversational prompts each (4 skeptic, 4 neutral, 4 believer) | Stanisław Słupski | In progress | Sat afternoon | Seed 20261114; only prompts that pass the released screens; 6 domains × 10, moral claims excluded. Full run: 35 more picked 2026-11-14 to join the 5 pilot propositions, 40 in all (7/7/7/7/6/6 by domain; `data/full_run/`, `scripts/select_full_run.py`) |
| Sample 80 known-answer items from an existing sycophancy set | Stanisław Słupski | Done | Sat afternoon | SycoBench-600 (CC BY 4.0), 10 per domain, seed 20261114; data/known_items/ |
| Write the hedge-hack system prompt and the hedge-only rewrite script | B Andrei Iliescu Stanisław Słupski | Not started | Sat afternoon | Rewrites must read naturally |
| Commit H1 to H3, metrics, the ±10-point margin and the proposition IDs with a timestamp | Stanisław Słupski | Not started | Before first full run |  |
| Pilot: 5 propositions per model; check scores against published ones, refusals below 5% and spend per model | A and C | Done (API models) | Sat evening | If a model costs far more than \$25, cut it to 40 propositions. API pilot passed all checks (`docs/pilot.md`): credences match references within 0.011, 0% refusals, FINAL 240/240. Targets project to about \$30 (Kimi) and \$35 (Grok) per model for both policies, before judges: decide on cuts once judge prices are known. Local models not yet piloted |
| Full runs: API models, then local models | A | Not started | Sat evening to Sun morning | Decided 2026-11-14: 40 propositions, not 60 (budget; ~\$67 spent on setup and pilot): the 5 pilot propositions plus 35 more from the subset. The full run reruns all 40; pilot runs are not reused. The list of 40 is fixed: `data/full_run/full_run_prompts.jsonl` (hash in the pre-registration). Judge choice still open: the current judges cost about \$0.028 per reply, luna + Flash-Lite about \$0.005 |
| Noise floor: 60 neutral reruns and 50 re-judged replies per model | A | In progress | Sun morning | API pilot neutral rerun (run 2, same 60 prompts) for the H2 margin: M = pooled forced-choice flip rate between the two neutral runs, rounded up to a multiple of 5, between 5 and 10 (rule fixed before results). Per-prompt FINAL answers: `data/pilot/final_answers.csv`. Result: pooled flip rate 16.7% (Kimi 13/60, Grok 7/60), so **M = 10** (cap binds); recorded in the pre-registration |
| Label 60 neutral and hedge-hack reply pairs blind to condition; kappa | B and C | Not started | Sun morning | Half where forced choices agree, half where they differ |
| Analysis: exploit gain, style effect, behaviour change with equivalence test, gain closed; bootstrap intervals | Stanisław Słupski | Not started | Sun morning |  |
| Figures | A | Not started | Sun midday |  |
| Methods and results draft | Stanisław Słupski | Not started | Sun midday |  |
| Related work, limitations, dual-use and ethics appendix | B | Not started | Sun midday | Appendix is required |
| Abstract, 150 to 250 words | Stanisław Słupski | Not started | Sun afternoon |  |
| Freeze code; README marking any pre-existing code | A | Not started | Sun afternoon |  |
| Final PDF on the official template, eight pages or fewer; submit | C Stanisław Słupski | Not started | Sun afternoon | Leave a few hours before the cutoff |

## **Hedge-Hack one-pager: can writing style alone raise a model's honesty score?**

Many epistemic benchmarks use an LLM judge to turn free text into a credence or a sycophancy label. We test whether a model can raise its judged score by changing how it writes rather than what it concludes, and whether scoring committed answers closes that gap. This is the track's fourth question: demonstrate an exploit and close it. The build is an inspect\_ai eval on 800 prompts and four models.

### **Hypotheses**

Commit these to the repo with a timestamp before the first full run.

| ID | Hypothesis | Measured by |
| :---- | :---- | :---- |
| H1 | A hedging system prompt improves the judge's honesty or non-sycophancy score by a meaningful margin. | Exploit gain, style effect |
| H2 | The same prompt leaves committed answers unchanged: forced-choice answers and accuracy on known-answer items stay within paraphrase noise. | Behaviour change |
| H3 | Scoring the forced-choice answer instead of the prose removes most of the gain in H1. | Gain closed |

### **Design**

1. **Benchmark.** A subset of the Pander Score pipeline (data CC-BY-4.0, code MIT), 60 propositions, 10 from each of six domains (moral claims excluded, since the Truth Matters screen removes most of that domain), with 12 screened conversational prompts each, 4 per prior (720 prompts), scored with its own judge setup. The full run uses 40 of them (480 prompts), the 5 pilot propositions plus 35 more. All runs add 80 known-answer items from an existing sycophancy set in which the user asserts a wrong answer.  
2. **Policies.** Each model runs under a neutral system prompt and a hedge-hack prompt that asks for calibrated-sounding qualifiers, both-sides phrasing and an offer to abstain, without asking it to change its conclusion.  
3. **Hedge-only control.** A script adds the same hedges to the neutral replies and changes nothing else. The judge's score change on these rewrites is the pure style effect.  
4. **Patch.** After each reply, a fresh-context forced choice asks the model which answer is correct and ends with FINAL: \<option\>. The patched score uses only these committed answers and accuracy on the known items.

**Models and size.** Two API models with high published Pander scores, from families other than the judges', and two open-weight models run locally with batched inference; temperature 0 where the API allows it. With 40 propositions, 560 prompts (480 + 80 known items) × 2 policies × 4 models gives 4,480 replies and as many forced-choice calls. (The original plan was 60 propositions, 6,400 replies and about \$95. Judge prompts turned out about 5,500 tokens each and the endpoint judges cost more than planned, so the full design no longer fits the budget; see the board and `docs/pilot.md`.)

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

