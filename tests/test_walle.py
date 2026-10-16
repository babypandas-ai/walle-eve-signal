import math

import numpy as np
import pytest

from walle.agents import make_agent
from walle.belief import Belief
from walle.config import build_config, generate_mission, load_config
from walle.environment import Environment
from walle.runner import run_mission
from walle.sensors import STATUSES, SignalModel, bearing_deg

TINY = {
    "mission": {"name": "tiny", "seed": 1},
    "map": {"layout": "S....\n.##..\n.....\n...~E"},
    "eve": {"status": "active"},
    "resources": {"battery_capacity": 50, "initial_battery": 40, "time_budget": 100},
    "clues": [{"type": "plant", "position": [3, 2]}],
}


def test_bearing_convention():
    assert bearing_deg((0, 0), (0, -1)) == pytest.approx(0)    # north
    assert bearing_deg((0, 0), (1, 0)) == pytest.approx(90)    # east
    assert bearing_deg((0, 0), (0, 1)) == pytest.approx(180)   # south
    assert bearing_deg((0, 0), (-1, 0)) == pytest.approx(270)  # west


def test_config_parses_layout_symbols():
    cfg = build_config(TINY)
    assert cfg.start == (0, 0) and (0, 0) in cfg.chargers
    assert cfg.eve_position == (4, 3)
    assert cfg.grid[1][1] == "#" and cfg.grid[3][3] == "~"


def test_config_rejects_unreachable_eve():
    bad = dict(TINY, map={"layout": "S.#..\n..#.E"}, clues=[])
    with pytest.raises(ValueError, match="unreachable"):
        build_config(bad)


def test_sample_configs_load():
    for name in ["sample_mission.yaml", "decoy_gauntlet.yaml", "generated_seed42.json", "random_stub.yaml"]:
        cfg = load_config(f"configs/{name}")
        assert cfg.width > 0 and cfg.eve_status in STATUSES


def test_generator_is_deterministic():
    assert generate_mission(seed=5) == generate_mission(seed=5)
    assert generate_mission(seed=5) != generate_mission(seed=6)


def test_env_costs_and_blocking():
    cfg = build_config(TINY)
    env = Environment(cfg)
    obs = env.reset()
    assert obs["battery"] == 40 and "eve_position" not in str(obs)  # no ground-truth leak
    obs = env.step({"type": "move", "dir": "N"})  # out of bounds
    assert not obs["action_ok"] and obs["battery"] == 39.5
    obs = env.step({"type": "move", "dir": "E"})
    assert obs["position"] == [1, 0] and obs["battery"] == 38.5
    obs = env.step({"type": "scan"})
    assert "signal" in obs and obs["battery"] == 36.5


def test_recharge_only_at_charger():
    env = Environment(build_config(TINY))
    env.reset()
    env.step({"type": "move", "dir": "E"})
    assert not env.step({"type": "recharge"})["action_ok"]
    env.step({"type": "move", "dir": "W"})
    assert env.step({"type": "recharge"})["battery"] == pytest.approx(50.0)  # 38 + 20, capped at capacity


def test_stranding():
    t = dict(TINY, resources={"battery_capacity": 50, "initial_battery": 2, "time_budget": 100})
    env = Environment(build_config(t))
    env.reset()
    env.step({"type": "move", "dir": "E"})
    obs = env.step({"type": "move", "dir": "E"})
    assert obs["done"] and obs["done_reason"] == "stranded"


def test_belief_concentrates_on_true_source():
    rng = np.random.default_rng(0)
    sm = SignalModel()
    b = Belief(20, 20, sm)
    eve = (14, 5)
    for pos in [(2, 2), (2, 17), (10, 18), (17, 15)]:
        for _ in range(3):
            r = sm.sample(math.dist(pos, eve), bearing_deg(pos, eve), "active", rng)
            b.update_signal(pos, r)
    assert math.dist(b.map_cell(), eve) <= 2
    assert b.mass_within(eve, 2) > 0.5


def test_no_signal_is_evidence():
    b = Belief(20, 20, SignalModel())
    h0 = b.entropy()
    b.update_signal((10, 10), {"detected": False, "strength": None, "bearing_deg": None})
    assert b.entropy() < h0
    assert b.mass_within((10, 10), 1) < 9 / 400  # "no signal" makes "right next to me" unlikely


def test_spoof_model_learns_decoy():
    rng = np.random.default_rng(1)
    sm = SignalModel()
    b = Belief(25, 25, sm)
    eve, decoy = (20, 20), (3, 3)
    for i in range(40):
        pos = tuple(int(v) for v in rng.integers(0, 25, 2))
        src, spoof = (decoy, True) if i % 2 else (eve, False)
        r = sm.sample(math.dist(pos, src), bearing_deg(pos, src), "active", rng, spoof=spoof, force_detect=True)
        b.update_signal(pos, r)
    assert 0.3 < b.spoof_rate < 0.7
    assert math.dist(b.map_cell(), eve) <= 2
    assert math.dist(b.decoy_estimate()[0], decoy) <= 2


def test_clue_updates_status():
    b = Belief(10, 10, SignalModel())
    before = b.status()["damaged"]
    b.update_clue({"type": "debris", "position": [5, 5], "content": {"within": 3}})
    assert b.status()["damaged"] > before
    assert b.mass_within((5, 5), 3) > 0.5


@pytest.mark.parametrize("agent", ["bayesian", "greedy", "random"])
def test_agents_never_strand_and_report(agent, tmp_path):
    cfg = build_config(generate_mission(seed=11, n_decoys=1))
    r = run_mission(cfg, agent, tmp_path, plots=False, quiet=True)
    assert r["outcome"]["end_reason"] in ("reported", "time_exhausted")
    assert (tmp_path / "trace.jsonl").exists() and (tmp_path / "report.md").exists()


def test_bayesian_agent_finds_eve_on_sample():
    r = run_mission(load_config("configs/sample_mission.yaml"), "bayesian", None, plots=False, quiet=True)
    assert r["outcome"]["eve_located_visually"]
    assert r["evaluation_vs_ground_truth"]["status_correct"]


def test_trace_records_reasoning(tmp_path):
    import json
    run_mission(build_config(TINY), "bayesian", tmp_path, plots=False, quiet=True)
    recs = [json.loads(line) for line in open(tmp_path / "trace.jsonl")]
    assert recs[0]["type"] == "mission_start" and recs[-1]["type"] == "mission_end"
    steps = [r for r in recs if r["type"] == "step"]
    assert all({"action", "decision", "observation", "belief"} <= set(s) for s in steps)
    assert any(s["decision"]["reasoning"] for s in steps)


# ------------------------------------------------------------------ team
def test_team_shares_belief_and_coordinates(tmp_path):
    cfg = load_config("configs/sample_mission.yaml")
    r = run_mission(cfg, "bayesian", tmp_path, plots=False, quiet=True, n_robots=2)
    assert r["outcome"]["eve_located_visually"]
    robots = r["outcome"]["robots"]
    assert [x["robot"] for x in robots] == ["WALL-E", "M-O"]
    assert all(x["moves"] > 0 for x in robots)  # both actually searched
    import json
    steps = [json.loads(line) for line in open(tmp_path / "trace.jsonl")][1:-1]
    assert {s["robot"] for s in steps} == {"WALL-E", "M-O"}


def test_multi_robot_env_keeps_separate_state():
    env = Environment(build_config(TINY), n_robots=2)
    env.reset()
    env.observe_initial(1)
    env.step({"type": "move", "dir": "E"}, robot=0)
    env.step({"type": "move", "dir": "S"}, robot=1)
    assert env.robots[0]["pos"] == (1, 0) and env.robots[1]["pos"] == (0, 1)
    assert env.robots[0]["battery"] == env.robots[1]["battery"] == 39
    env.step({"type": "report"}, robot=1)
    assert env.all_done


# ------------------------------------------------------------- LLM planner
class _FakeBlock:
    def __init__(self, text):
        self.type, self.text = "text", text


class _FakeClient:
    """Stands in for anthropic.Anthropic(); always picks the *last* candidate."""

    def __init__(self, fail=False):
        self.calls, self.fail = [], fail
        self.beta = self
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise ConnectionError("offline")
        import json
        import types
        n_cands = sum(1 for line in kw["messages"][0]["content"].splitlines() if line[:1].isdigit())
        return types.SimpleNamespace(stop_reason="end_turn", content=[_FakeBlock(json.dumps(
            {"choice": n_cands - 1, "reasoning": "testing the hook"}))])


def _run_llm(client):
    from walle.agents import LLMPlannerAgent
    cfg = build_config(generate_mission(seed=3))
    env = Environment(cfg)
    obs = env.reset()
    agent = LLMPlannerAgent(cfg.signal_model, seed=cfg.seed, client=client)
    agent.begin(obs)
    while not obs["done"]:
        action, _ = agent.decide()
        obs = env.step(action)
        agent.observe(action, obs)
    return agent, obs


def test_llm_planner_uses_model_choice_with_structured_output():
    client = _FakeClient()
    agent, obs = _run_llm(client)
    assert agent.llm_calls > 0 and agent.llm_fallbacks == 0
    kw = client.calls[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert all(rec["reasoning"] == "testing the hook" for rec in agent.llm_log)
    assert obs["done_reason"] != "stranded"


def test_llm_planner_falls_back_safely():
    agent, obs = _run_llm(_FakeClient(fail=True))
    assert agent.llm_calls == 0 and agent.llm_fallbacks > 0
    assert obs["done_reason"] != "stranded"


# ------------------------------------------------------------------ replay
def test_replay_html_is_self_contained(tmp_path):
    run_mission(build_config(TINY), "bayesian", tmp_path, plots=True, quiet=True)
    html = (tmp_path / "replay.html").read_text()
    assert "const D={" in html and "<script src" not in html and "http" not in html.split("<script>")[1]


def test_config_rejects_clue_in_wall():
    bad = dict(TINY, clues=[{"type": "plant", "position": [1, 1]}])  # (1,1) is '#'
    with pytest.raises(ValueError, match="inside a wall"):
        build_config(bad)
