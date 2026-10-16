"""Ablation: does likelihood tempering (L ** tau) improve confidence calibration?

Seeds 5000-5099 are disjoint from the benchmark seeds (1000+), so this is
evaluated on held-out missions. Writes benchmarks/tempering.md.

    python experiments/likelihood_tempering.py
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from walle.benchmark import CALIBRATION_TIER, TIERS  # noqa: E402
from walle.config import build_config, generate_mission  # noqa: E402
from walle.runner import run_mission  # noqa: E402

TAUS = [1.0, 0.7, 0.5, 0.35]
CAL_SEEDS = range(5000, 5100)
SUCCESS_SEEDS = range(5000, 5012)


def calibration_run(args):
    seed, tau = args
    cfg = build_config(generate_mission(seed=seed, **CALIBRATION_TIER))
    r = run_mission(cfg, "bayesian", None, plots=False, quiet=True, agent_params={"likelihood_temper": tau})
    e = r["evaluation_vs_ground_truth"]
    est, true = r["inference"]["eve_location"], e["true_position"]
    hit = int(max(abs(est[0] - true[0]), abs(est[1] - true[1])) <= 1)
    return e["eve_found"], r["inference"]["p_within_1_cell"], hit


def success_run(args):
    tier, seed, tau = args
    cfg = build_config(generate_mission(seed=seed, **TIERS[tier]))
    r = run_mission(cfg, "bayesian", None, plots=False, quiet=True, agent_params={"likelihood_temper": tau})
    return r["outcome"]["eve_located_visually"], r["outcome"]["time_used"]


def main():
    lines = ["# Likelihood tempering ablation", "",
             f"Calibration: {len(CAL_SEEDS)} held-out missions with a 60-step budget (scored only when they end "
             f"without contact). Success/time: {len(SUCCESS_SEEDS)} decoys + {len(SUCCESS_SEEDS)} harsh missions.",
             "", "| tau | missions | Brier | mean reported P | observed hit rate | mid-range (0.2-0.8) reported | "
             "mid-range observed | success | mean time |", "|---|---|---|---|---|---|---|---|---|"]
    with ProcessPoolExecutor() as ex:
        for tau in TAUS:
            rs = [r for r in ex.map(calibration_run, [(s, tau) for s in CAL_SEEDS]) if not r[0]]
            p = np.array([r[1] for r in rs])
            h = np.array([r[2] for r in rs])
            mid = (p > 0.2) & (p < 0.8)
            ss = list(ex.map(success_run, [(t, s, tau) for t in ("decoys", "harsh") for s in SUCCESS_SEEDS]))
            row = (f"| {tau} | {len(rs)} | {np.mean((p - h) ** 2):.4f} | {p.mean():.3f} | {h.mean():.3f} | "
                   f"{p[mid].mean():.2f} | {h[mid].mean():.2f} | {np.mean([x[0] for x in ss]):.0%} | "
                   f"{np.mean([x[1] for x in ss]):.0f} |")
            lines.append(row)
            print(row, flush=True)
    Path("benchmarks/tempering.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
