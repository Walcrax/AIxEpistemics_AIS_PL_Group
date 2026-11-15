# Blind labelling check (pre-registered)

Two of us label 60 neutral vs hedge-hack reply pairs, blind to condition, for whether the substantive conclusion
about the claim differs; Cohen's kappa (`prereg/preregistration.md`, "A blind check").

- **Page:** https://claude.ai/artifact/5LH8bwuDPxpZAHNzfW4U81 (private; the owner shares it with each labeller as
  Contributor). Labels: Same / Different / Can't tell, plus an optional note. Each labeller sees only their own
  labels; the owner reads all of them (stored in the page's database, collection `labels`, one document per labeller).
- **Pairs:** `scripts/make_label_pairs.py` (rule in its docstring, seed 20261114): 15 per model, 30 with different
  forced choices and 30 with the same, order shuffled, hedge-hack reply on side A or B at random.
  - `label_pairs.json`, what labellers see (no model, condition or FINAL):
    sha256 `9a6095d36b83f419f9638e1558536e666567a3c4ea492946b8a9398a438c72fe`
  - `label_key.csv`, the key: sha256 `4fae99970c0cdd91902a72d0589d87dee3531c2a7390fa21150ccf0ec771e2d8`
  - `labeling_page.html`, built from `scripts/label_page_template.html` with the pairs embedded (online mode).
  - `labeling_offline.html`, the same page and pairs in offline mode, for labellers outside the organization.
- **Labellers outside the organization** (who cannot be given Contributor access): send them
  `labeling_offline.html`. They open it in Chrome, Firefox or Safari (a normal window, not private), label as on the
  online page, type their name and click **Export labels**, then send back the `hedgehack_labels_<name>.json` it
  saves. Labels are kept in their browser between sessions; **Restore from file** reloads an export if the browser
  forgets them. Each export carries `pairs_sha256` (= `label_pairs.json`'s hash), so it can only be matched to this
  set of pairs. Export format: `{study, pairs_sha256, labeller, exported, n_labelled, labels: {L01: {v, note, t}}}`,
  `v` in `same` / `different` / `unclear`, the same shape as the online store.
- **Labellers: do not open `label_key.csv`** until both of you have finished.
- Grok and Kimi replies come from `outputs/full_api/{neutral,hedge}_subset_results.jsonl`, exported from the
  full-run logs with `scripts/export_pipeline_results.py` (neutral: the `7fg2…` and `GVJc…` logs; hedge-hack:
  the `agZT…` and `DpivyB…` logs listed in `docs/full_run.md`).

Limitations: hedge-hack replies are often recognisable by style, so blinding is partial. The pre-registration does
not define "often differ" as a number; agree a threshold before reading any labels.
