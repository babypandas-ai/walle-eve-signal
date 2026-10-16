"""The simulated world. Holds the ground truth and turns actions into
observations. Nothing in an observation leaks hidden state the robot could not
physically sense: clue locations, EVE's position/status and decoy transmitters
are only revealed through interaction.
"""
from __future__ import annotations

import math

import numpy as np

from .config import CHARGER, RUBBLE, WALL, MissionConfig
from .sensors import CLUE_TYPES, STATUSES, bearing_deg

MOVES = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}


ROBOT_NAMES = ["WALL-E", "M-O", "BURN-E", "VN-GO"]
_PER_ROBOT = ("pos", "battery", "t", "done", "done_reason", "battery_used", "last_truth")


class Environment:
    """Single- or multi-robot world. Each robot keeps its own position,
    battery and clock; clues, EVE and decoys are shared. With one robot the
    API is simply ``reset()`` / ``step(action)``; with a team, pass
    ``robot=i`` to ``step`` and use ``observe_initial(i)`` after ``reset``."""

    def __init__(self, cfg: MissionConfig, n_robots: int = 1, starts: list | None = None):
        self.cfg = cfg
        self.n_robots = n_robots
        self.starts = [tuple(s) for s in (starts or [cfg.start] * n_robots)]
        self.rng = np.random.default_rng(cfg.seed)
        self.reset()

    # per-robot state is exposed as attributes of the *currently acting* robot
    def __getattr__(self, name):
        if name in _PER_ROBOT and "robots" in self.__dict__:
            return self.__dict__["robots"][self.__dict__["_r"]][name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in _PER_ROBOT and "robots" in self.__dict__:
            self.__dict__["robots"][self.__dict__["_r"]][name] = value
        else:
            super().__setattr__(name, value)

    @property
    def all_done(self) -> bool:
        return all(r["done"] for r in self.robots)

    # ------------------------------------------------------------------ api
    def reset(self) -> dict:
        c = self.cfg
        self.__dict__["robots"] = [
            {"pos": s, "battery": float(c.initial_battery), "t": 0, "done": False, "done_reason": None,
             "battery_used": 0.0, "last_truth": {}} for s in self.starts]
        self._r = 0
        self.found_clues: set = set()
        self.eve_contact = False
        return self.observe_initial(0)

    def observe_initial(self, robot: int) -> dict:
        c = self.cfg
        self._r = robot
        name = ROBOT_NAMES[robot % len(ROBOT_NAMES)]
        obs = self._observe(action_ok=True, message=f"{name} boots up.")
        obs["initial_signal"] = self._initial_signal()
        obs["mission"] = {
            "name": c.name, "width": c.width, "height": c.height,
            "battery_capacity": c.battery_capacity, "time_budget": c.time_budget,
            "costs": vars(c.costs), "chargers": [list(p) for p in c.chargers],
            "sight_radius": c.sight_radius, "scan_radius": c.scan_radius,
            "contact_radius": c.contact_radius,
        }
        return obs

    def step(self, action: dict, robot: int = 0) -> dict:
        self._r = robot
        if self.done:
            raise RuntimeError("episode finished")
        kind = action.get("type")
        c, costs = self.cfg, self.cfg.costs
        self.last_truth = {}
        extra: dict = {}
        ok, msg = True, ""

        if kind == "move":
            dx, dy = MOVES[action["dir"]]
            nx, ny = self.pos[0] + dx, self.pos[1] + dy
            if not c.passable(nx, ny):
                ok, msg = False, "bumped into an obstacle"
                self._spend(costs.blocked, 1)
            else:
                rubble = c.terrain(nx, ny) == RUBBLE
                if self._spend(costs.move_rubble if rubble else costs.move, 2 if rubble else 1):
                    self.pos = (nx, ny)
                    msg = f"moved {action['dir']}" + (" through rubble" if rubble else "")
        elif kind == "scan":
            if self._spend(costs.scan, 1):
                extra["signal"] = self._signal_reading()
                extra["clues"] = self._detect_clues()
                msg = "scanned"
        elif kind == "recharge":
            if c.terrain(*self.pos) != CHARGER:
                ok, msg = False, "no charger here"
                self._spend(0.0, 1)
            else:
                gained = min(costs.recharge_rate, c.battery_capacity - self.battery)
                self.battery += gained
                self._spend(0.0, 1)
                msg = f"recharged +{gained:.1f}"
        elif kind == "wait":
            self._spend(0.0, 1)
            msg = "waited"
        elif kind == "report":
            for r in self.robots:  # the report ends the mission for the whole team
                if not r["done"]:
                    r["done"], r["done_reason"] = True, "reported"
            msg = "mission report transmitted"
        else:
            raise ValueError(f"unknown action {action!r}")

        if not self.done and self.t >= c.time_budget:
            self.done, self.done_reason = True, "time_exhausted"
        return self._observe(ok, msg, **extra)

    # ------------------------------------------------------------- internals
    def _spend(self, battery: float, time: int) -> bool:
        if battery > self.battery + 1e-9:
            self.battery_used += self.battery
            self.battery = 0.0
            self.t += time
            self.done, self.done_reason = True, "stranded"
            return False
        self.battery -= battery
        self.battery_used += battery
        self.t += time
        if self.battery <= 1e-9 and self.cfg.terrain(*self.pos) != CHARGER:
            self.done, self.done_reason = True, "stranded"
        return True

    def _initial_signal(self) -> dict:
        s = dict(self.cfg.initial_signal or {})
        if not s or ("bearing_deg" not in s and "coordinates" not in s):
            sm, eve = self.cfg.signal_model, self.cfg.eve_position
            r = sm.sample(math.dist(self.pos, eve), bearing_deg(self.pos, eve), self.cfg.eve_status,
                          self.rng, force_detect=True)
            s = {"bearing_deg": r["bearing_deg"], "strength": r["strength"], "timestamp": -10, **s}
            self.cfg.initial_signal = s  # sample once, share with every robot
        s = dict(s)
        s.setdefault("timestamp", 0)
        s.setdefault("observed_from", list(self.cfg.start))
        s["detected"] = s.get("strength") is not None or "bearing_deg" in s
        return s

    def _signal_reading(self) -> dict:
        c, sm = self.cfg, self.cfg.signal_model
        eve = c.eve_position
        # A decoy transmitter can capture the receiver for this scan.
        for d in c.decoys:
            if self.rng.random() < d["rate"]:
                dist = math.dist(self.pos, d["position"])
                r = sm.sample(dist, bearing_deg(self.pos, d["position"]), "active", self.rng,
                              power_override=d["power"], spoof=True)
                if r["detected"]:
                    self.last_truth = {"signal_source": "decoy", "decoy": list(d["position"])}
                    return r
        r = sm.sample(math.dist(self.pos, eve), bearing_deg(self.pos, eve), c.eve_status, self.rng)
        self.last_truth = {"signal_source": "eve" if r["detected"] else "none"}
        return r

    def _detect_clues(self) -> list:
        c, out = self.cfg, []
        for clue in c.clues:
            if clue["id"] in self.found_clues:
                continue
            if math.dist(self.pos, clue["position"]) > c.scan_radius + 1e-9:
                continue
            if self.rng.random() > c.clue_detect_prob:
                continue  # noisy sensor: missed it this time
            self.found_clues.add(clue["id"])
            out.append(self._clue_content(clue))
        return out

    def _clue_content(self, clue) -> dict:
        eve, p, rng = self.cfg.eve_position, clue["position"], self.rng
        t = clue["type"]
        d = math.dist(p, eve)
        if t == "hover_tracks":
            content = {"bearing_deg": round(float((bearing_deg(p, eve) + rng.normal(0, 10)) % 360), 1)}
        elif t in ("debris", "power_cell"):
            content = {"within": int(math.ceil(d) + rng.integers(1, 4))}
        elif t == "plant":
            content = {"within": int(math.ceil(d) + 1)}
        elif t == "beacon_log":
            axis = "x" if rng.random() < 0.5 else "y"
            v = eve[0] if axis == "x" else eve[1]
            lo = int(v - rng.integers(0, 6))
            content = {"axis": axis, "min": lo, "max": lo + 5}
        else:  # pragma: no cover - validated in config
            content = {}
        return {"id": clue["id"], "type": t, "position": list(p), "content": content,
                "description": CLUE_TYPES[t][0].format(**content)}

    def _observe(self, action_ok: bool, message: str, **extra) -> dict:
        c = self.cfg
        r = c.sight_radius
        terrain = []
        for y in range(self.pos[1] - r, self.pos[1] + r + 1):
            for x in range(self.pos[0] - r, self.pos[0] + r + 1):
                if c.in_bounds(x, y):
                    terrain.append([x, y, c.terrain(x, y)])
        contact = None
        eve = c.eve_position
        if max(abs(eve[0] - self.pos[0]), abs(eve[1] - self.pos[1])) <= c.contact_radius:
            self.eve_contact = True
            st = c.eve_status
            if self.rng.random() > c.contact_status_accuracy:
                st = [s for s in STATUSES if s != st][self.rng.integers(2)]
            contact = {"position": list(eve), "status_reading": st}
        obs = {
            "t": self.t,
            "position": list(self.pos),
            "battery": round(self.battery, 2),
            "at_charger": c.terrain(*self.pos) == CHARGER,
            "action_ok": action_ok,
            "message": message,
            "terrain": terrain,
            "contact": contact,
            "done": self.done,
            "done_reason": self.done_reason,
        }
        obs.update(extra)
        return obs

    # --------------------------------------------------- evaluation helpers
    def truth(self) -> dict:
        c = self.cfg
        return {"eve_position": list(c.eve_position), "eve_status": c.eve_status,
                "clues": [dict(cl, position=list(cl["position"])) for cl in c.clues],
                "decoys": [dict(d, position=list(d["position"])) for d in c.decoys]}


def is_wall(ch: str) -> bool:
    return ch == WALL
