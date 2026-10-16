"""Command-line interface: ``python -m walle <command> ...``"""
from __future__ import annotations

import argparse
import json
import sys

from .config import dump_raw, generate_mission, load_config


def main(argv=None):
    ap = argparse.ArgumentParser(prog="walle", description="WALL-E & EVE's Signal - autonomous search agent")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run one mission from a config file")
    r.add_argument("config")
    r.add_argument("--agent", default="bayesian", help="bayesian | bayesian-naive | greedy | random")
    r.add_argument("--out", help="output directory for trace/report/plots (default runs/<config-name>)")
    r.add_argument("--no-plots", action="store_true")
    r.add_argument("--gif", action="store_true", help="also render an animated GIF")
    r.add_argument("--live", action="store_true", help="animate the run in the terminal (ASCII)")
    r.add_argument("--quiet", action="store_true")
    r.add_argument("--robots", type=int, default=1, help="team size (WALL-E, M-O, ...) sharing one belief")

    g = sub.add_parser("generate", help="write a random mission config")
    g.add_argument("--seed", type=int, default=0)
    g.add_argument("--width", type=int, default=30)
    g.add_argument("--height", type=int, default=20)
    g.add_argument("--decoys", type=int, default=0)
    g.add_argument("--clues", type=int, default=6)
    g.add_argument("--status", choices=["active", "low_power", "damaged"])
    g.add_argument("--out", required=True, help=".yaml or .json path")

    b = sub.add_parser("benchmark", help="compare agents across random missions")
    b.add_argument("--n", type=int, default=30, help="missions per difficulty")
    b.add_argument("--agents", default="bayesian,bayesian@2,bayesian-naive,greedy,random",
                   help="comma-separated; NAME@N runs a team of N robots; 'llm' needs an API key")
    b.add_argument("--out", default="benchmarks")
    b.add_argument("--seed0", type=int, default=1000)

    a = ap.parse_args(argv)
    if a.cmd == "run":
        from pathlib import Path

        from .runner import run_mission
        cfg = load_config(a.config)
        out = a.out or (f"runs/{Path(a.config).stem}" + ("" if a.agent == "bayesian" else f"_{a.agent}")
                        + ("" if a.robots == 1 else f"_team{a.robots}"))
        run_mission(cfg, a.agent, out, plots=not a.no_plots, gif=a.gif, live=a.live, quiet=a.quiet,
                    n_robots=a.robots)
    elif a.cmd == "generate":
        raw = generate_mission(seed=a.seed, width=a.width, height=a.height, n_decoys=a.decoys,
                               n_clues=a.clues, eve_status=a.status)
        dump_raw(raw, a.out)
        print(f"wrote {a.out}")
    elif a.cmd == "benchmark":
        from .benchmark import run_benchmark
        res = run_benchmark(a.n, a.agents.split(","), a.out, a.seed0)
        json.dump(res["summary"], sys.stdout, indent=2)
        print()


if __name__ == "__main__":
    main()
