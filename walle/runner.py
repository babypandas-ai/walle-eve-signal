"""Runs one mission end-to-end: env <-> agent loop, trace logging, report, visuals."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .agents import Team, make_agent
from .config import MissionConfig
from .environment import Environment
from .report import build_report, report_markdown
from .viz import ascii_belief, ascii_map

MAX_STEPS = 5000


def _visible_obs(obs: dict) -> dict:
    """Agent-visible observation, compacted for the trace."""
    o = {k: v for k, v in obs.items() if k not in ("terrain", "mission", "initial_signal")}
    o["cells_in_view"] = len(obs.get("terrain", []))
    return o


def team_starts(cfg: MissionConfig, n: int) -> list:
    """Start cells per robot: ``team.starts`` from the config, padded with the truck."""
    starts = [tuple(p) for p in (cfg.raw.get("team") or {}).get("starts", [])] or [cfg.start]
    return (starts + [cfg.start] * n)[:n]


class TeamView:
    """Presents a team of agents through the single-agent interface used by
    the report and the visualisations."""

    def __init__(self, team, agents, agent_name):
        self.team, self.agents = team, agents
        self.name = f"team of {len(agents)} x {agent_name}"
        self.robot_names = [team.name(a) for a in agents]

    def __getattr__(self, k):  # belief, evidence, readings, known, pos, mode, ...
        return getattr(self.agents[0], k)

    @property
    def contact(self):
        return self.team.contact

    @property
    def scans(self):
        return sum(a.scans for a in self.agents)

    @property
    def strategy_changes(self):
        out = [dict(c, robot=self.team.name(a)) for a in self.agents for c in a.strategy_changes]
        return sorted(out, key=lambda c: c["t"])

    @property
    def trajectory(self):
        others = [p for a in self.agents[1:] for p in a.trajectory]
        return others + self.agents[0].trajectory

    def paths(self):
        from .viz import ROBOT_COLORS
        return [(a.trajectory, ROBOT_COLORS[i % len(ROBOT_COLORS)]) for i, a in enumerate(self.agents)]

    def mode_at(self, t):
        return " / ".join(f"{self.team.name(a)}:{_mode_at(a, t)}" for a in self.agents)

    def retrospective_spoof(self):
        self.agents[0].retrospective_spoof()


def _mode_at(agent, t):
    m = agent.trajectory[0][2]
    for p in agent.trajectory:
        if p[1] > t:
            break
        m = p[2]
    return m


def run_mission(cfg: MissionConfig, agent_name: str = "bayesian", out_dir: str | Path | None = None,
                plots: bool = True, gif: bool = False, live: bool = False, agent_params: dict | None = None,
                quiet: bool = False, n_robots: int = 1) -> dict:
    t0 = time.time()
    env = Environment(cfg, n_robots=n_robots, starts=team_starts(cfg, n_robots))
    obs0 = env.reset()
    params = {**cfg.agent, **(agent_params or {})}
    team = Team() if n_robots > 1 else None
    agents, notes = [], []
    for i in range(n_robots):
        o = obs0 if i == 0 else env.observe_initial(i)
        a = make_agent(agent_name, cfg.signal_model, params, seed=cfg.seed + 101 * i)
        notes += a.begin(o, team=team) if team else a.begin(o)
        agents.append(a)
    view = agents[0] if team is None else TeamView(team, agents, agent_name)
    names = view.robot_names if team else ["WALL-E"]

    out = Path(out_dir) if out_dir else None
    trace_f = None
    if out:
        out.mkdir(parents=True, exist_ok=True)
        trace_f = open(out / "trace.jsonl", "w")

    def log(rec):
        if trace_f:
            trace_f.write(json.dumps(rec) + "\n")

    log({"type": "mission_start", "mission": cfg.name, "agent": view.name, "robots": names, "seed": cfg.seed,
         "observation": {k: v for k, v in obs0.items() if k != "terrain"}, "notes": notes,
         "belief": view.belief.summary()})

    def snapshot(t):
        h = {"t": t, "mode": agents[0].mode, "battery": agents[0].battery, **_bel(view)}
        if team:
            h["batteries"] = [a.battery for a in agents]
            h["robot_names"] = names
        return h

    history = [snapshot(0)]
    frames = [(0, view.belief.position().copy(), 0)]
    counts = {"recharges": 0, "moves": 0, "decoy_readings": 0, "decoy_flagged": 0, "genuine_flagged": 0}
    per_robot = [{"robot": n, "moves": 0, "scans": 0, "recharges": 0} for n in names]
    sources = []  # ground-truth source of each detected reading (evaluation only)
    step = 0
    while not env.all_done and step < MAX_STEPS:
        # event-driven: whoever is earliest on their own clock acts next
        i = min((j for j in range(n_robots) if not env.robots[j]["done"]), key=lambda j: (env.robots[j]["t"], j))
        agent = agents[i]
        action, decision = agent.decide()
        obs = env.step(action, robot=i)
        truth = dict(env.last_truth)
        notes = agent.observe(action, obs)
        if action["type"] == "recharge" and obs["action_ok"]:
            counts["recharges"] += 1
            per_robot[i]["recharges"] += 1
        if action["type"] == "move" and obs["action_ok"]:
            counts["moves"] += 1
            per_robot[i]["moves"] += 1
        if action["type"] == "scan":
            per_robot[i]["scans"] += 1
        if obs.get("signal", {}) and obs["signal"].get("detected"):
            sources.append((agent.readings[-1], truth.get("signal_source")))
        rec = {"type": "step", "step": step, "t": obs["t"], "mode": decision["mode"], "action": action,
               "decision": decision, "observation": _visible_obs(obs), "belief_update_notes": notes,
               "belief": view.belief.summary(), "battery": obs["battery"], "hidden_truth": truth or None}
        if team:
            rec["robot"] = names[i]
        log(rec)
        h = snapshot(obs["t"])
        h["scan_detected"] = obs["signal"]["detected"] if obs.get("signal") else None
        history.append(h)
        if plots:
            frames.append((len(agent.trajectory) - 1, view.belief.position().copy(), obs["t"]))
        if live and not quiet:
            _live(cfg, agent, decision, action, notes, names[i])
        step += 1

    view.retrospective_spoof()
    for r, src in sources:
        flagged = r["spoof_prob"] > 0.5 or r.get("spoof_prob_hindsight", 0) > 0.5
        if src == "decoy":
            counts["decoy_readings"] += 1
            counts["decoy_flagged"] += flagged
        elif flagged:
            counts["genuine_flagged"] += 1
    reasons = [r["done_reason"] for r in env.robots]
    end_reason = ("reported" if "reported" in reasons else reasons[0]) or "step_limit"
    for k, r in enumerate(env.robots):
        per_robot[k].update(battery_used=round(r["battery_used"], 1), battery_left=round(r["battery"], 1),
                            end=r["done_reason"])
    outcome = {"end_reason": end_reason, "time": max(r["t"] for r in env.robots),
               "battery": sum(r["battery"] for r in env.robots),
               "battery_used": sum(r["battery_used"] for r in env.robots), **counts}
    if team:
        outcome["robots"] = per_robot
    report = build_report(cfg, env, view, outcome)
    others = [(a.pos, "M") for a in agents[1:]]
    amap = ascii_map(cfg, view.trajectory, {e["id"] for e in view.evidence}, view.belief.map_cell(), others=others)
    log({"type": "mission_end", "outcome": report["outcome"], "inference": report["inference"],
         "confidence": report["confidence"], "recommended_next_step": report["recommended_next_step"],
         "ground_truth": env.truth()})
    if trace_f:
        trace_f.close()
    llm = [a for a in agents if hasattr(a, "llm_log")]
    if llm:
        report["llm_planner"] = {"model": llm[0].p["llm_model"], "calls": sum(a.llm_calls for a in llm),
                                 "fallbacks": sum(a.llm_fallbacks for a in llm)}
    if out and llm:
        with open(out / "llm_decisions.jsonl", "w") as f:
            for a in llm:
                for rec in a.llm_log:
                    f.write(json.dumps(rec) + "\n")
    if out:
        (out / "report.json").write_text(json.dumps(report, indent=2))
        (out / "report.md").write_text(report_markdown(report, amap))
        (out / "final_map.txt").write_text(amap + "\n\n" + ascii_belief(view.belief.position(), view.pos) + "\n")
        if plots:
            from .viz import animate, plot_mission, plot_timeline
            plot_mission(out / "mission.png", cfg, view, frames, f"{cfg.name} - {view.name} agent")
            plot_timeline(out / "timeline.png", history, cfg.time_budget, cfg.battery_capacity)
            if gif:
                animate(out / "mission.gif", cfg, view, frames, every=max(1, len(frames) // 90))
            from .replay import write_replay
            write_replay(out / "replay.html", cfg, view, frames, out / "trace.jsonl", report)
    report["_runtime_s"] = round(time.time() - t0, 2)
    report["_history"] = history
    if not quiet:
        print(amap)
        print()
        print(f"Outcome: {report['outcome']['end_reason']} | EVE visually located: "
              f"{report['outcome']['eve_located_visually']} | estimate {tuple(report['inference']['eve_location'])} "
              f"(true {tuple(cfg.eve_position)}) | status {report['inference']['status']} "
              f"(true {cfg.eve_status}) | time {outcome['time']}/{cfg.time_budget}")
        print(f"Next step: {report['recommended_next_step']}")
        if out:
            print(f"Artifacts written to {out}/")
    return report


def _bel(agent):
    b = agent.belief
    x, y = b.map_cell()
    return {"entropy": b.entropy(), "p_within_1": b.mass_within((x, y), 1)}


def _live(cfg, agent, decision, action, notes, name="WALL-E"):
    print("\033[2J\033[H", end="")
    print(ascii_map(cfg, agent.trajectory, {e["id"] for e in agent.evidence}, agent.belief.map_cell(),
                    show_truth=False, known=agent.known))
    print(f"[{name}] t={agent.t} battery={agent.battery:.1f} mode={agent.mode} action={action}")
    for r in decision["reasoning"] + notes:
        print("  -", r)
    time.sleep(0.03)
