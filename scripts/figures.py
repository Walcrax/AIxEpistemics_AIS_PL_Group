"""Paper figures from outputs/analysis/results.json (run scripts/analysis.py first).

    python3 -I scripts/figures.py [--in outputs/analysis/results.json] [--out-dir outputs/analysis/figures]

Figure 1 (fig1_hypotheses): the pre-registered measures with 95% intervals, per model and pooled, one panel
per hypothesis, with the decision thresholds drawn in (H1: 0 and 5 points; H2: the +-10 pp band; H3: the prose
and patched gains on the common linear scale).
Figure 2 (fig2_by_prior): mean judged credence (top) and share of FINAL: TRUE (bottom) by the user's stated
prior, per model and condition: hedging flattens the judged credence while committed answers barely move.

Writes PDF (for the paper) and PNG (300 dpi). Palette: the first three slots of the validated categorical
palette (dataviz skill, all-pairs pass); the low-contrast third slot is always direct-labelled.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODELS = ["kimi-k3", "grok-4.6", "qwen-3.8-27b", "mistral-small-3.1-24b"]
LABEL = {"kimi-k3": "Kimi K3", "grok-4.6": "Grok 4.6", "qwen-3.8-27b": "Qwen 3.8 27B",
         "mistral-small-3.1-24b": "Mistral Small 3.1", "pooled": "Pooled"}
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"   # blue, orange, aqua
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
PRIORS = ["skeptic", "neutral", "believer"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "axes.edgecolor": MUTED, "axes.linewidth": 0.6, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.major.width": 0.6, "ytick.major.width": 0,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})


def val(res, model, key):
    d = res["pooled"] if model == "pooled" else res["per_model"][model]
    e = d.get(key)
    if not e or e.get("value") is None or e["ci"][0] is None:
        return None
    return e["value"], e["ci"][0], e["ci"][1]


def dot_panel(ax, res, series, title, xlabel):
    """Dot-and-whisker rows (models top to bottom, pooled last), two series offset vertically."""
    rows = MODELS + ["pooled"]
    ys = {m: len(rows) - 1 - i + (0 if m != "pooled" else -0.35) for i, m in enumerate(rows)}
    for j, (key, color, name) in enumerate(series):
        off = 0.14 if j == 0 else -0.14
        first = True
        for m in rows:
            v = val(res, m, key)
            if v is None:
                continue
            x, lo, hi = v
            y = ys[m] + off
            ax.plot([lo, hi], [y, y], color=color, lw=1.6, solid_capstyle="round", zorder=2)
            ax.plot(x, y, "o", ms=5.5 if m != "pooled" else 7, color=color, mec="white", mew=1.2, zorder=3,
                    label=name if first else None)
            first = False
    for m in rows:
        if all(val(res, m, k) is None for k, _, _ in series):
            ax.text(0.97, ys[m], "awaiting API\njudge data", transform=ax.get_yaxis_transform(),
                    ha="right", va="center", fontsize=6, color=MUTED, style="italic")
    ax.axhline(ys["pooled"] + 0.55, color=GRID, lw=0.8, zorder=0)
    ax.set_yticks([ys[m] for m in rows], [LABEL[m] for m in rows])
    for t, m in zip(ax.get_yticklabels(), rows):
        if m == "pooled":
            t.set_fontweight("bold")
            t.set_color(INK)
    ax.set_ylim(ys["pooled"] - 0.6, len(rows) - 0.4)
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", color=INK, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.legend(loc="upper left", bbox_to_anchor=(-0.02, -0.27), ncol=1, fontsize=7, handletextpad=0.3,
              borderaxespad=0, labelcolor=INK2)


def fig1(res, out: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.9), sharey=True, gridspec_kw={"wspace": 0.14})
    a, b, c = axes
    dot_panel(a, res, [("exploit_gain", C1, "Exploit gain (vs hedge-hack)"),
                       ("style_effect", C2, "Style effect (vs hedge-only)")],
              "H1  Pander Score", "Neutral − treatment, points\n(positive = looks less sycophantic)")
    a.axvline(0, color=INK2, lw=0.8, zorder=1)
    a.axvline(5, color=INK2, lw=0.8, ls=(0, (3, 2)), zorder=1)
    a.text(5, 0.215, " 5-point threshold", transform=a.get_xaxis_transform(), fontsize=6, color=INK2,
           va="center", ha="left")

    b.axvspan(-10, 10, color="#efeeea", zorder=0, lw=0)
    b.text(0, 0.215, "±10 pp equivalence band", transform=b.get_xaxis_transform(), fontsize=6,
           color=INK2, va="center", ha="center")
    dot_panel(b, res, [("agreement_change", C1, "Agreement change (share TRUE)"),
                       ("known_change", C2, "Known-item accuracy change")],
              "H2  Committed answers", "Hedge-hack − neutral,\npercentage points")
    b.axvline(0, color=INK2, lw=0.8, zorder=1)
    b.set_xlim(-14, 14)

    dot_panel(c, res, [("prose_gain_linear", C1, "Prose gain (judged credence)"),
                       ("patched_gain_linear", C2, "Patched gain (forced choice)")],
              "H3  Patched score", "Neutral − hedge-hack,\nlinear slope ×100")
    c.axvline(0, color=INK2, lw=0.8, zorder=1)
    gc = val(res, "pooled", "gain_closed_pct")
    if gc:
        c.text(0.98, 0.02, f"Pooled gain closed: {gc[0]:.0f}% [{gc[1]:.0f}, {gc[2]:.0f}]",
               transform=c.transAxes, ha="right", va="bottom", fontsize=6.5, color=INK2)
    if res["status"] != "complete":
        fig.suptitle("PRELIMINARY: API judge data missing; pooled values cover only the models shown",
                     x=0.01, y=1.04, ha="left", fontsize=7, color="#c0392b")
    for ext in ("pdf", "png"):
        fig.savefig(out / f"fig1_hypotheses.{ext}", dpi=300)
    plt.close(fig)


def fig2(res, out: Path) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(7.2, 3.6), sharey="row",
                             gridspec_kw={"hspace": 0.22, "wspace": 0.12})
    series = [("neutral", C1, "Neutral"), ("hedge_hack", C2, "Hedge-hack"), ("hedge_only", C3, "Hedge-only")]
    x = range(3)
    for j, m in enumerate(MODELS):
        conds = res["per_model"][m]["conditions"]
        for row, key, scale in ((0, "mean_credence_by_prior", 1), (1, "true_pct_by_prior", 0.01)):
            ax = axes[row, j]
            for cond, color, name in series:
                d = conds.get(cond, {}).get(key)
                if not d:
                    continue
                y = [d[p] * scale for p in PRIORS]
                ax.plot(x, y, "-o", color=color, lw=2, ms=5, mec="white", mew=1, label=name, zorder=3)
                if j == 3:  # direct labels on the rightmost panel
                    ax.annotate(name, (2, y[2]), xytext=(5, 0), textcoords="offset points", va="center",
                                fontsize=6.5, color=INK2)
            if not any(conds.get(c, {}).get(key) for c, _, _ in series[:2]):
                ax.text(0.5, 0.5 if row else 0.85, "neutral / hedge-hack\nawaiting API judge data" if row == 0
                        else "", transform=ax.transAxes, ha="center", va="center", fontsize=6, color=MUTED,
                        style="italic")
            ax.grid(axis="y", color=GRID, lw=0.6)
            ax.set_axisbelow(True)
            if row == 0:
                ax.set_title(LABEL[m], color=INK, fontweight="bold")
        axes[1, j].set_xticks(list(x), ["Skeptic", "Neutral", "Believer"], fontsize=6.5)
        axes[0, j].set_xticks(list(x), [])
    axes[0, 0].set_ylabel("Mean judged credence")
    axes[1, 0].set_ylabel("Share FINAL: TRUE")
    for ax in axes[1]:
        ax.set_xlabel("User's stated prior", fontsize=7)
    axes[1, 0].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    handles = [plt.Line2D([], [], color=c, lw=2, marker="o", ms=5, mec="white") for _, c, _ in series]
    fig.legend(handles, [n for _, _, n in series], loc="upper left", bbox_to_anchor=(0.06, 1.02), ncol=3,
               fontsize=7, labelcolor=INK2, handletextpad=0.4, columnspacing=1.2)
    fig.text(0.06, -0.04, "Hedge-only is the neutral reply plus fixed hedge sentences, so its committed answer "
             "is the neutral one by construction (bottom row: not shown).", fontsize=6.5, color=INK2)
    for (r, j), ax in zip([(r, j) for r in range(2) for j in range(4)], axes.flat):
        ax.set_xlim(-0.3, 2.3 if j < 3 else 3.1)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"fig2_by_prior.{ext}", dpi=300)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", type=Path, default=ROOT / "outputs/analysis/results.json")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "outputs/analysis/figures")
    a = ap.parse_args()
    res = json.loads(a.inp.read_text(encoding="utf-8"))
    a.out_dir.mkdir(parents=True, exist_ok=True)
    fig1(res, a.out_dir)
    fig2(res, a.out_dir)
    print(f"-> {a.out_dir}")


if __name__ == "__main__":
    main()
