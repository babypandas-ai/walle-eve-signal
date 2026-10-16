"""Mission config loading, validation and random mission generation.

A mission config is a JSON or YAML document. See README.md ("Config format")
for the full schema; ``configs/`` holds worked examples.
"""
from __future__ import annotations

import copy
import json
import math
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from .sensors import CLUE_TYPES, STATUSES, SignalModel, bearing_deg

OPEN, WALL, RUBBLE, CHARGER = ".", "#", "~", "C"
PASSABLE = {OPEN, RUBBLE, CHARGER}

DEFAULTS = {
    "mission": {"name": "unnamed mission", "seed": 0},
    "resources": {
        "battery_capacity": 100.0,
        "initial_battery": 80.0,
        "time_budget": 400,
        "costs": {"move": 1.0, "move_rubble": 3.0, "scan": 2.0, "recharge_rate": 20.0, "blocked": 0.5},
    },
    "sensors": {
        "sight_radius": 2,
        "scan_radius": 3,
        "clue_detect_prob": 0.85,
        "contact_radius": 1,
        "contact_status_accuracy": 0.95,
        "signal": {},
    },
    "clues": [],
    "decoys": [],
    "agent": {},
}


@dataclass
class Costs:
    move: float
    move_rubble: float
    scan: float
    recharge_rate: float
    blocked: float


@dataclass
class MissionConfig:
    name: str
    seed: int
    width: int
    height: int
    grid: list            # grid[y][x] -> terrain char
    start: tuple
    chargers: list
    eve_position: tuple
    eve_status: str
    initial_signal: dict | None
    battery_capacity: float
    initial_battery: float
    time_budget: int
    costs: Costs
    sight_radius: int
    scan_radius: int
    clue_detect_prob: float
    contact_radius: int
    contact_status_accuracy: float
    signal_model: SignalModel
    clues: list
    decoys: list
    agent: dict
    raw: dict = field(repr=False, default_factory=dict)

    def terrain(self, x, y) -> str:
        return self.grid[y][x]

    def in_bounds(self, x, y) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def passable(self, x, y) -> bool:
        return self.in_bounds(x, y) and self.grid[y][x] in PASSABLE


def _deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_raw(path: str | Path) -> dict:
    path = Path(path)
    text = path.read_text()
    if path.suffix.lower() == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def load_config(path: str | Path) -> MissionConfig:
    return build_config(load_raw(path))


def _pt(v, what) -> tuple:
    if not (isinstance(v, (list, tuple)) and len(v) == 2):
        raise ValueError(f"{what} must be [x, y], got {v!r}")
    return int(v[0]), int(v[1])


def build_config(raw: dict) -> MissionConfig:
    """Validate a raw dict (possibly a ``generate:`` stub) into a MissionConfig."""
    raw = raw or {}
    if "generate" in raw:
        gen = dict(raw["generate"])
        seed = raw.get("mission", {}).get("seed", gen.pop("seed", 0))
        generated = generate_mission(seed=seed, **gen)
        # anything the user wrote explicitly overrides the generated values
        raw = _deep_merge(generated, {k: v for k, v in raw.items() if k != "generate"})
    cfg = _deep_merge(DEFAULTS, raw)

    m = cfg.get("map") or {}
    layout = m.get("layout")
    if not layout:
        raise ValueError("config needs map.layout (or a top-level `generate:` block)")
    rows = [r.rstrip() for r in (layout.splitlines() if isinstance(layout, str) else layout)]
    rows = [r for r in rows if r.strip()]
    width, height = max(len(r) for r in rows), len(rows)
    grid, start, eve_pos, chargers, decoys_from_map = [], None, None, [], []
    for y, row in enumerate(rows):
        line = []
        for x, ch in enumerate(row.ljust(width, WALL)):
            if ch == "S":
                start = (x, y)
                ch = CHARGER  # WALL-E's truck doubles as his charger
            elif ch == "E":
                eve_pos = (x, y)
                ch = OPEN
            elif ch == "D":
                decoys_from_map.append((x, y))
                ch = OPEN
            elif ch not in (OPEN, WALL, RUBBLE, CHARGER):
                raise ValueError(f"unknown map symbol {ch!r} at ({x},{y})")
            if ch == CHARGER:
                chargers.append((x, y))
            line.append(ch)
        grid.append(line)

    if "start" in cfg:
        start = _pt(cfg["start"], "start")
        if grid[start[1]][start[0]] == OPEN:
            grid[start[1]][start[0]] = CHARGER
            chargers.append(start)
    if start is None:
        raise ValueError("no start position: put 'S' in the layout or set start: [x, y]")

    eve = cfg.get("eve") or {}
    if "position" in eve:
        eve_pos = _pt(eve["position"], "eve.position")
    if eve_pos is None:
        raise ValueError("no EVE position: put 'E' in the layout or set eve.position")
    status = eve.get("status", "active")
    if status not in STATUSES:
        raise ValueError(f"eve.status must be one of {STATUSES}")

    res, sen = cfg["resources"], cfg["sensors"]
    costs = Costs(**res["costs"])
    clues = []
    for i, c in enumerate(cfg.get("clues") or []):
        if c["type"] not in CLUE_TYPES:
            raise ValueError(f"unknown clue type {c['type']!r}; choose from {list(CLUE_TYPES)}")
        clues.append({"id": c.get("id", f"clue{i + 1}"), "type": c["type"],
                      "position": _pt(c["position"], "clue.position")})
    decoys = [{"position": _pt(d["position"], "decoy.position"),
               "power": float(d.get("power", 70.0)), "rate": float(d.get("rate", 0.3))}
              for d in (cfg.get("decoys") or [])]
    decoys += [{"position": p, "power": 70.0, "rate": 0.3} for p in decoys_from_map]

    mc = MissionConfig(
        name=cfg["mission"].get("name", "unnamed mission"),
        seed=int(cfg["mission"].get("seed", 0)),
        width=width, height=height, grid=grid, start=start,
        chargers=sorted(set(chargers)), eve_position=eve_pos, eve_status=status,
        initial_signal=cfg.get("initial_signal"),
        battery_capacity=float(res["battery_capacity"]),
        initial_battery=float(res["initial_battery"]),
        time_budget=int(res["time_budget"]),
        costs=costs,
        sight_radius=int(sen["sight_radius"]), scan_radius=int(sen["scan_radius"]),
        clue_detect_prob=float(sen["clue_detect_prob"]),
        contact_radius=int(sen["contact_radius"]),
        contact_status_accuracy=float(sen["contact_status_accuracy"]),
        signal_model=SignalModel.from_dict(sen.get("signal")),
        clues=clues, decoys=decoys, agent=dict(cfg.get("agent") or {}), raw=cfg,
    )
    _validate(mc)
    return mc


def _validate(mc: MissionConfig):
    if not mc.passable(*mc.start):
        raise ValueError("start must be on a passable cell")
    if not mc.in_bounds(*mc.eve_position) or not mc.passable(*mc.eve_position):
        raise ValueError("EVE must be on a passable in-bounds cell")
    for c in mc.clues:
        if not mc.in_bounds(*c["position"]):
            raise ValueError(f"clue {c['id']} out of bounds")
        if not mc.passable(*c["position"]):
            raise ValueError(f"clue {c['id']} at {tuple(c['position'])} is inside a wall")
    if not 0 < mc.initial_battery <= mc.battery_capacity:
        raise ValueError("need 0 < initial_battery <= battery_capacity")
    reach = reachable(mc.grid, mc.start)
    if mc.eve_position not in reach:
        raise ValueError("EVE is unreachable from the start position")


def reachable(grid, start) -> set:
    h, w = len(grid), len(grid[0])
    seen, q = {start}, deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and grid[ny][nx] in PASSABLE:
                seen.add((nx, ny))
                q.append((nx, ny))
    return seen


# ------------------------------------------------------------------ generator
# Which clue types tend to be left behind, given EVE's (hidden) state. Sampling
# clues this way keeps clue *types* honest evidence about her status.
_CLUE_MIX = {
    "active": {"hover_tracks": 0.40, "debris": 0.08, "power_cell": 0.08, "beacon_log": 0.29, "plant": 0.15},
    "low_power": {"hover_tracks": 0.18, "debris": 0.12, "power_cell": 0.30, "beacon_log": 0.25, "plant": 0.15},
    "damaged": {"hover_tracks": 0.12, "debris": 0.35, "power_cell": 0.13, "beacon_log": 0.25, "plant": 0.15},
}


def generate_mission(seed: int = 0, width: int = 30, height: int = 20, wall_blocks: int | None = None,
                     rubble_density: float = 0.12, n_chargers: int = 2, n_clues: int = 6,
                     n_decoys: int = 0, decoy_rate: float = 0.35, eve_status: str | None = None,
                     battery_capacity: float = 100.0, initial_battery: float = 80.0,
                     time_budget: int = 400, name: str | None = None) -> dict:
    """Procedurally generate a complete, reproducible raw mission config."""
    rng = np.random.default_rng(seed)
    for _attempt in range(200):
        grid = [[OPEN] * width for _ in range(height)]
        # collapsed buildings: random rectangles of wall
        nblocks = wall_blocks if wall_blocks is not None else int(width * height / 28)
        for _ in range(nblocks):
            bw, bh = rng.integers(1, 5), rng.integers(1, 4)
            bx, by = rng.integers(0, width - bw + 1), rng.integers(0, height - bh + 1)
            for yy in range(by, by + bh):
                for xx in range(bx, bx + bw):
                    grid[yy][xx] = WALL
        # rubble fields: random walks
        for _ in range(int(width * height * rubble_density / 8)):
            x, y = rng.integers(0, width), rng.integers(0, height)
            for _ in range(8):
                if grid[y][x] == OPEN:
                    grid[y][x] = RUBBLE
                x = int(np.clip(x + rng.integers(-1, 2), 0, width - 1))
                y = int(np.clip(y + rng.integers(-1, 2), 0, height - 1))
        start = (int(rng.integers(1, max(2, width // 5))), int(rng.integers(1, height - 1)))
        grid[start[1]][start[0]] = CHARGER
        reach = reachable(grid, start)
        if len(reach) < 0.55 * width * height:
            continue
        # seal off unreachable pockets so the world is consistent
        for y in range(height):
            for x in range(width):
                if (x, y) not in reach and grid[y][x] != WALL:
                    grid[y][x] = WALL
        cells = sorted(reach)
        far = [c for c in cells if math.dist(c, start) >= 0.55 * max(width, height)]
        if not far:
            continue
        eve = far[rng.integers(len(far))]
        break
    else:
        raise RuntimeError("could not generate a connected map")

    status = eve_status or STATUSES[rng.integers(len(STATUSES))]
    # extra chargers, spread out and away from start
    chargers = []
    pool = [c for c in cells if grid[c[1]][c[0]] == OPEN and math.dist(c, start) > 8 and math.dist(c, eve) > 4]
    for _ in range(max(0, n_chargers - 1)):
        if not pool:
            break
        scores = [min([math.dist(p, q) for q in chargers + [start]]) for p in pool]
        c = pool[int(np.argmax(np.array(scores) + rng.random(len(pool)) * 4))]
        chargers.append(c)
        grid[c[1]][c[0]] = CHARGER
        pool.remove(c)

    clues = []
    mix = _CLUE_MIX[status]
    used = {start, eve, *chargers}
    for i in range(n_clues):
        ctype = rng.choice(list(mix), p=list(mix.values()))
        lo, hi = {"plant": (1.5, 3.5), "debris": (2, 7), "power_cell": (2, 8),
                  "hover_tracks": (4, 14), "beacon_log": (5, 22)}[ctype]
        cand = [c for c in cells if lo <= math.dist(c, eve) <= hi and c not in used]
        if not cand:
            continue
        p = cand[rng.integers(len(cand))]
        used.add(p)
        clues.append({"id": f"clue{i + 1}", "type": str(ctype), "position": list(p)})

    decoys = []
    for _ in range(n_decoys):
        cand = [(x, y) for y in range(height) for x in range(width)
                if math.dist((x, y), eve) >= 0.4 * max(width, height) and math.dist((x, y), start) >= 6]
        if cand:
            d = cand[rng.integers(len(cand))]
            decoys.append({"position": list(d), "power": round(float(rng.uniform(66, 80)), 1), "rate": decoy_rate})

    # the faint, stale reading that started the mission
    sm = SignalModel()
    d = math.dist(start, eve)
    sig = sm.sample(d, bearing_deg(start, eve), status, rng, force_detect=True)
    layout = "\n".join("".join("S" if (x, y) == start else grid[y][x] for x in range(width))
                       for y in range(height))
    return {
        "mission": {"name": name or f"Generated mission #{seed}", "seed": int(seed)},
        "map": {"layout": layout},
        "eve": {"position": list(eve), "status": status},
        "initial_signal": {"bearing_deg": sig["bearing_deg"], "strength": sig["strength"],
                           "timestamp": -int(rng.integers(5, 30))},
        "resources": {"battery_capacity": battery_capacity, "initial_battery": initial_battery,
                      "time_budget": time_budget},
        "clues": clues,
        "decoys": decoys,
    }


def dump_raw(raw: dict, path: str | Path):
    path = Path(path)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(raw, indent=2))
    else:
        class _D(yaml.SafeDumper):
            pass

        def _str(dumper, data):
            style = "|" if "\n" in data else None
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)

        _D.add_representer(str, _str)
        path.write_text(yaml.dump(raw, Dumper=_D, sort_keys=False, default_flow_style=None, width=120))
