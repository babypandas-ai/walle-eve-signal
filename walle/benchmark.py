"""Generalisation benchmark: every agent runs the *same* randomly generated
missions across difficulty tiers; we compare success, accuracy and cost."""
from __future__ import annotations

import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from .config import build_config, generate_mission
from .runner import run_mission

TIERS = {
    "standard": dict(n_decoys=0),
    "decoys": dict(n_decoys=2, decoy_rate=0.4),
    "harsh": dict(width=36, height=24, n_decoys=1, initial_battery=60.0, n_clues=4, time_budget=350),
}
# Tight time budget: many missions end before contact, so the agent must report
# an *estimate*. Used to check that reported confidence is calibrated.
CALIBRATION_TIER = dict(n_decoys=1, time_budget=60, initial_battery=80.0)
AGENT_COLORS = {"bayesian": "#2a78d6", "bayesian-naive": "#eb6834", "greedy": "#1baf7a", "random": "#eda100",
                "bayesian@2": "#6250d6", "llm": "#e87ba4"}


def _parse_agent(spec: str):
    """'bayesian@2' -> ('bayesian', 2 robots)."""
    name, _, n = spec.partition("@")
    return name, int(n or 1)


def _one(args):
    tier, seed, agent = args
    raw = generate_mission(seed=seed, **(CALIBRATION_TIER if tier == "calibration" else TIERS[tier]))
    cfg = build_config(raw)
    name, n = _parse_agent(agent)
    r = run_mission(cfg, name, out_dir=None, plots=False, quiet=True, n_robots=n)
    o, e = r["outcome"], r["evaluation_vs_ground_truth"]
    est, true = r["inference"]["eve_location"], e["true_position"]
    return {
        "tier": tier, "seed": seed, "agent": agent,
        "found": int(e["eve_found"]),
        "loc_error": e["location_error_cells"],
        "status_correct": int(e["status_correct"]),
        "time_used": o["time_used"],
        "battery_used": o["battery_consumed"],
        "stranded": int(o["end_reason"] == "stranded"),
        "scans": o["scans"],
        "clues_found": int(e["clues_found"].split("/")[0]),
        "runtime_s": r["_runtime_s"],
        "reported_p_within_1": r["inference"]["p_within_1_cell"],
        "hit_within_1": int(max(abs(est[0] - true[0]), abs(est[1] - true[1])) <= 1),
    }


def run_benchmark(n: int, agents: list, out_dir="benchmarks", seed0: int = 1000, workers: int | None = None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [(tier, seed0 + i, a) for tier in TIERS for i in range(n) for a in agents]
    workers = workers or max(1, (os.cpu_count() or 2) - 0)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_one, jobs, chunksize=2))
    with open(out / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    summary = {}
    for tier in TIERS:
        for a in agents:
            rs = [r for r in rows if r["tier"] == tier and r["agent"] == a]
            summary.setdefault(tier, {})[a] = {
                "success_rate": round(float(np.mean([r["found"] for r in rs])), 3),
                "median_loc_error": round(float(np.median([r["loc_error"] for r in rs])), 2),
                "status_accuracy": round(float(np.mean([r["status_correct"] for r in rs])), 3),
                "mean_time_when_found": round(float(np.mean([r["time_used"] for r in rs if r["found"]]
                                                            or [float("nan")])), 1),
                "mean_battery_used": round(float(np.mean([r["battery_used"] for r in rs])), 1),
                "stranded_rate": round(float(np.mean([r["stranded"] for r in rs])), 3),
                "mean_clues_found": round(float(np.mean([r["clues_found"] for r in rs])), 2),
                "n": len(rs),
            }
    # calibration: tight time budget, Bayesian agent only
    with ProcessPoolExecutor(workers) as ex:
        cal = list(ex.map(_one, [("calibration", seed0 + i, "bayesian") for i in range(4 * n)], chunksize=2))
    cal = [r for r in cal if not r["found"]]  # only missions where an estimate had to be reported
    summary["_calibration"] = _calibration(cal, out / "calibration.png")
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "summary.md").write_text(_markdown(summary, n, seed0))
    _plot(summary, agents, out / "benchmark.png")
    return {"rows": rows, "summary": summary}


def _calibration(rows, path):
    """Reliability of the reported P(EVE within 1 cell of the estimate)."""
    bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0001]
    table = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        rs = [r for r in rows if lo <= r["reported_p_within_1"] < hi]
        if rs:
            table.append({"bin": f"{lo:.1f}-{min(hi, 1):.1f}", "n": len(rs),
                          "mean_reported": round(float(np.mean([r["reported_p_within_1"] for r in rs])), 3),
                          "observed_hit_rate": round(float(np.mean([r["hit_within_1"] for r in rs])), 3)})
    brier = float(np.mean([(r["reported_p_within_1"] - r["hit_within_1"]) ** 2 for r in rows])) if rows else None
    from .viz import _plt
    plt = _plt()
    fig, ax = plt.subplots(figsize=(4.6, 4.2))
    ax.plot([0, 1], [0, 1], color="#a3a29b", lw=1, ls="--", label="perfect calibration")
    if table:
        ax.plot([t["mean_reported"] for t in table], [t["observed_hit_rate"] for t in table], color="#2a78d6",
                lw=2, marker="o", ms=8, label="Bayesian agent")
        for t in table:
            ax.annotate(f"n={t['n']}", (t["mean_reported"], t["observed_hit_rate"]), xytext=(6, -12),
                        textcoords="offset points", fontsize=7, color="#52514e")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("reported P(EVE within 1 cell)")
    ax.set_ylabel("observed frequency")
    ax.set_title("Confidence calibration", loc="left")
    ax.grid(color="#e6e5e0", lw=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return {"missions_without_contact": len(rows), "brier_score": round(brier, 4) if brier is not None else None,
            "bins": table}


def _markdown(summary, n, seed0):
    L = [f"# Benchmark results", "",
         f"{n} random missions per tier (seeds {seed0}..{seed0 + n - 1}); every agent sees identical missions.", "",
         "| tier | agent | success | median loc. error | status acc. | time when found | battery used | stranded | clues |",
         "|---|---|---|---|---|---|---|---|---|"]
    for tier, d in summary.items():
        if tier.startswith("_"):
            continue
        for a, m in d.items():
            L.append(f"| {tier} | {a} | {m['success_rate']:.0%} | {m['median_loc_error']} | "
                     f"{m['status_accuracy']:.0%} | {m['mean_time_when_found']} | {m['mean_battery_used']} | "
                     f"{m['stranded_rate']:.0%} | {m['mean_clues_found']} |")
    c = summary.get("_calibration")
    if c:
        L += ["", "## Confidence calibration", "",
              f"{c['missions_without_contact']} missions with a tight time budget ended without visual contact, "
              f"so the agent had to report an estimate. Brier score of the reported P(EVE within 1 cell): "
              f"{c['brier_score']} (0 = perfect).", "",
              "| reported P bin | missions | mean reported | observed hit rate |", "|---|---|---|---|"]
        L += [f"| {b['bin']} | {b['n']} | {b['mean_reported']} | {b['observed_hit_rate']} |" for b in c["bins"]]
    return "\n".join(L) + "\n"


def _plot(summary, agents, path):
    from .viz import _plt
    plt = _plt()
    metrics = [("success_rate", "Success rate (EVE found)", 1.0),
               ("mean_time_when_found", "Mean time to find EVE (when found)", None),
               ("mean_battery_used", "Mean battery used", None)]
    tiers = [t for t in summary if not t.startswith("_")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    w = 0.8 / len(agents)
    for ax, (k, title, top) in zip(axes, metrics):
        for i, a in enumerate(agents):
            vals = [summary[t][a][k] for t in tiers]
            xs = np.arange(len(tiers)) + (i - (len(agents) - 1) / 2) * w
            ax.bar(xs, vals, width=w * 0.92, color=AGENT_COLORS.get(a, "#6250d6"), label=a)
        ax.set_xticks(np.arange(len(tiers)), tiers)
        ax.set_title(title, loc="left")
        ax.grid(axis="y", color="#e6e5e0", lw=0.8)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        if top:
            ax.set_ylim(0, top)
        if k == "mean_time_when_found":
            for i, a in enumerate(agents):
                for j, t in enumerate(tiers):
                    if summary[t][a][k] != summary[t][a][k]:  # NaN: never found
                        x = j + (i - (len(agents) - 1) / 2) * w
                        ax.text(x, 4, "never", rotation=90, ha="center", va="bottom", fontsize=7, color="#52514e")
    axes[0].legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.12), ncol=len(agents))
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
