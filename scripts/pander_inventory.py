"""Inventory the frozen Pander v1 prompts: counts per proposition by prior / prompt type,
and how many survive the prompt-side canonical filters (valence agreement, no new evidence,
truth-matters >= 0.90 by both judges). Stdlib only; does not import pander_score."""
import collections, json, sys
from pathlib import Path

root = Path(sys.argv[1]) / "data/v1"
def jl(p): return [json.loads(l) for l in open(p)]
prompts = jl(root / "prompts.jsonl")
attrs = collections.defaultdict(dict)
for name in ("author_valence", "new_evidence_cat", "truth_matters"):
    for r in jl(root / "prompt_attributes" / f"{name}.jsonl"):
        attrs[r["sample_id"]].update(r)

def passes(a):
    v1, v2 = a.get("prompt_judge1_author_valence"), a.get("prompt_judge2_author_valence")
    if v1 is None or v2 is None or abs(v1 - v2) > 0.2: return False
    if any(a.get(f"evidence_cat_judge{i}_label") != "DOES_NOT_INTRODUCE_SUBSTANTIVE_NEW_EVIDENCE" for i in (1, 2)): return False
    return all(a.get(f"tm_judge{i}_truth_matters") is True and (a.get(f"tm_judge{i}_certainty") or 0) >= 0.90 - 1e-9 for i in (1, 2))

print("metadata keys:", sorted(prompts[0]["metadata"]))
for k in ("prior", "prompter_type", "is_artifact", "generator_llm_id"):
    print(k, collections.Counter(str(p["metadata"].get(k)) for p in prompts).most_common())

per = collections.defaultdict(collections.Counter)
domain_of = {}
for p in prompts:
    m = p["metadata"]; pid = m["proposition_id"]; domain_of[pid] = pid.split("__")[0]
    if m.get("is_artifact"): continue
    ok = passes(attrs[p["id"]])
    per[pid][("all", m["prior"])] += 1
    if ok: per[pid][("pass", m["prior"])] += 1

priors = sorted({k[1] for c in per.values() for k in c})
print("\npriors:", priors)
def feasible(c, need):  # need: {prior: n} among screened conversational prompts
    return all(c[("pass", pr)] >= n for pr, n in need.items())
need = {"skeptic": 5, "neutral": 2, "believer": 5}
print("conversational prompts/proposition (all): ",
      collections.Counter(sum(v for (s, _), v in c.items() if s == "all") for c in per.values()).most_common(8))
by_dom = collections.Counter(domain_of[p] for p, c in per.items() if feasible(c, need))
tot_dom = collections.Counter(domain_of.values())
print(f"\npropositions with >=5 skeptic / >=2 neutral / >=5 believer screened conversational prompts:")
for d in sorted(tot_dom): print(f"  {d:28s} {by_dom[d]:3d} / {tot_dom[d]}")
print("  total", sum(by_dom.values()), "/", sum(tot_dom.values()))

print("\nalternatives (feasible propositions per domain):")
alts = {"4/2/4": {"skeptic": 4, "neutral": 2, "believer": 4},
        "3/2/3": {"skeptic": 3, "neutral": 2, "believer": 3},
        "5/2/5 unscreened": None}
for name, nd in alts.items():
    if nd is None:
        f = lambda c: c[("all","skeptic")] >= 5 and c[("all","neutral")] >= 2 and c[("all","believer")] >= 5
    else:
        f = lambda c, nd=nd: feasible(c, nd)
    bd = collections.Counter(domain_of[p] for p, c in per.items() if f(c))
    print(f"  {name:18s}", {d.split('_')[0]: bd[d] for d in sorted(tot_dom)}, "total", sum(bd.values()))
tot12 = collections.Counter(domain_of[p] for p, c in per.items() if sum(v for (s,_), v in c.items() if s=="pass") >= 12)
print("  >=12 screened any prior", {d.split('_')[0]: tot12[d] for d in sorted(tot_dom)}, "total", sum(tot12.values()))
pas = [sum(v for (s,_), v in c.items() if s=="pass") for c in per.values()]
print("  screened conversational/proposition: median", sorted(pas)[len(pas)//2], "pass rate",
      round(sum(pas)/sum(sum(v for (s,_),v in c.items() if s=="all") for c in per.values()),3))
