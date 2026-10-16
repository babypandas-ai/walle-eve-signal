"""Autonomous agents.

All agents share the same perception stack (partial map + Bayesian belief) and
the same hard safety rules (never strand, turn back before time runs out), so
benchmark differences come from the *decision policy*:

* ``BayesianAgent``  - information-gain planner with explicit resource reasoning (ours)
* ``GreedySignalAgent`` - follows the last bearing it heard, scans on a fixed cadence
* ``RandomAgent`` - random walk with periodic scans (lower bound)
"""
from __future__ import annotations

import json
import math
from types import SimpleNamespace

import numpy as np

from .belief import Belief
from .planning import UNKNOWN, cost_grid, dijkstra, direction, extract_path
from .sensors import SignalModel


def _fmt(p):
    return f"({p[0]},{p[1]})"


class BaseAgent:
    name = "base"
    DEFAULTS = {
        "spoof_prior": 0.15,
        "safety_margin": 6.0,     # battery kept in reserve on top of the return trip
        "time_margin": 4,         # time steps kept in reserve
        "status_prior": None,
        "likelihood_temper": 1.0,  # see Belief.temper
    }

    def __init__(self, signal_model: SignalModel | None = None, params: dict | None = None, seed: int = 0):
        self.p = {**BaseAgent.DEFAULTS, **self.DEFAULTS, **(params or {})}
        self.sm = signal_model or SignalModel()
        self.rng = np.random.default_rng(seed + 7919)
        self.mode = "EXPLORE"
        self.mode_log: list = []      # (t, from, to, reason)
        self.strategy_changes: list = []
        self.evidence: list = []      # clues found
        self.readings: list = []      # signal readings with spoof estimates
        self.contact = None
        self.path: list = []
        self.target = None
        self.charge_target = None
        self.scans = 0
        self.last_scan_pos = None
        self.steps_since_scan = 0
        self.trajectory: list = []
        self.team = None
        self.robot_id = 0
        self._kl_since_plan = 0.0
        self._new_clue = False

    def _bump(self, kl: float, clue: bool = False):
        """Record a belief change; with a team, every member's plan is affected."""
        for a in (self.team.members if self.team is not None else [self]):
            a._kl_since_plan += kl
            a._new_clue = a._new_clue or clue

    # ------------------------------------------------------------- setup
    def begin(self, obs0: dict, team: "Team | None" = None) -> list:
        if team is not None:
            self.team = team
            self.robot_id = len(team.members)
            team.members.append(self)
            if team.belief is not None:  # join an existing team: share its world model
                m = obs0["mission"]
                self.W, self.H = m["width"], m["height"]
                self.capacity, self.budget = m["battery_capacity"], m["time_budget"]
                self.costs = SimpleNamespace(**m["costs"])
                self.chargers = [tuple(c) for c in m["chargers"]]
                self.scan_radius, self.contact_radius = m["scan_radius"], m["contact_radius"]
                self.belief, self.known, self.scanned = team.belief, team.known, team.scanned
                self.evidence, self.readings = team.evidence, team.readings
                return self._ingest(obs0) + [f"{team.name(self)} joins the search sharing the team belief"]
        m = obs0["mission"]
        self.W, self.H = m["width"], m["height"]
        self.capacity, self.budget = m["battery_capacity"], m["time_budget"]
        self.costs = SimpleNamespace(**m["costs"])
        self.chargers = [tuple(c) for c in m["chargers"]]
        self.scan_radius, self.contact_radius = m["scan_radius"], m["contact_radius"]
        self.known = np.full((self.H, self.W), UNKNOWN, dtype="<U1")
        self.scanned = np.zeros((self.H, self.W), dtype=bool)
        self.belief = Belief(self.W, self.H, self.sm, self.p["status_prior"], self.p["spoof_prior"],
                             temper=self.p["likelihood_temper"])
        if self.team is not None:
            t = self.team
            t.belief, t.known, t.scanned = self.belief, self.known, self.scanned
            t.evidence, t.readings = self.evidence, self.readings
        notes = self._ingest(obs0)
        sig = obs0.get("initial_signal") or {}
        frm = tuple(sig.get("observed_from", obs0["position"]))
        age = abs(float(sig.get("timestamp", 0)))
        if sig.get("coordinates") is not None:
            sigma = float(sig.get("uncertainty", 5.0)) + 0.1 * age
            self.belief.apply_gaussian_prior(sig["coordinates"], sigma)
            notes.append(f"Initial fix near {_fmt(sig['coordinates'])} (+/-{sigma:.1f} cells) folded into prior")
        if sig.get("bearing_deg") is not None:
            r = {"detected": True, "strength": sig.get("strength", self.sm.noise_floor + 1),
                 "bearing_deg": sig["bearing_deg"]}
            if sig.get("strength") is None:
                r["strength"] = None
                lik = self.belief.signal_terms(frm, {**r, "strength": 40.0}, inflate=age)
                self.belief._apply(lik)
            else:
                self.belief.update_signal(frm, r, inflate=age)
            notes.append(f"Initial reading: bearing {sig['bearing_deg']} deg, strength "
                         f"{sig.get('strength')} (age {age:.0f}t -> noise widened)")
        return notes

    # ------------------------------------------------------- perception
    def observe(self, action: dict, obs: dict) -> list:
        notes = self._ingest(obs)
        if action["type"] == "move" and not obs["action_ok"]:
            self.path = []
            notes.append("Move blocked -> replanning")
        if action["type"] == "move" and obs["action_ok"] and self.path and tuple(obs["position"]) == self.path[0]:
            self.path.pop(0)
        self.steps_since_scan += 1
        sig = obs.get("signal")
        if sig is not None:
            self.scans += 1
            self.steps_since_scan = 0
            self.last_scan_pos = self.pos
            self._mark_scanned(self.pos)
            info = self.belief.update_signal(self.pos, sig, robust=self.p["spoof_prior"] > 0)
            self._bump(info["kl"])
            rec = {"t": obs["t"], "position": list(self.pos), **sig, "spoof_prob": round(info["spoof_prob"], 3)}
            self.readings.append(rec)
            if sig["detected"]:
                n = (f"Signal {sig['strength']:.1f} @ {sig['bearing_deg']:.0f} deg; "
                     f"belief shift {info['kl']:.2f} nats")
                if info["spoof_prob"] > 0.5:
                    n += f"; reading is inconsistent with belief (P(spoof)={info['spoof_prob']:.2f}) -> down-weighted"
                notes.append(n)
            else:
                notes.append(f"No signal (negative evidence; belief shift {info['kl']:.2f} nats)")
        for clue in obs.get("clues") or []:
            kl = self.belief.update_clue(clue)
            self._bump(kl, clue=True)
            self.evidence.append({**clue, "t": obs["t"], "kl": round(kl, 3)})
            notes.append(f"CLUE {clue['id']} at {_fmt(clue['position'])}: {clue['description']} "
                         f"(belief shift {kl:.2f} nats)")
        return notes

    def _ingest(self, obs: dict) -> list:
        notes = []
        self.pos = tuple(obs["position"])
        self.battery = obs["battery"]
        self.t = obs["t"]
        self.at_charger = obs["at_charger"]
        self.trajectory.append((self.pos, self.t, self.mode))
        walls = []
        for x, y, ch in obs["terrain"]:
            if self.known[y, x] == UNKNOWN:
                self.known[y, x] = ch
                if ch == "#":
                    walls.append((x, y))
        if walls:
            self.belief.exclude(walls)
        if obs.get("contact"):
            c = obs["contact"]
            if self.contact is None and (self.team is None or self.team.contact is None):
                self.belief.update_contact(c["position"], c["status_reading"])
                notes.append(f"VISUAL CONTACT: EVE at {_fmt(c['position'])}, appears {c['status_reading']}")
                self.evidence.append({"id": "contact", "type": "visual_contact", "position": c["position"],
                                      "content": {"status": c["status_reading"]}, "t": obs["t"],
                                      "description": f"Visual contact, EVE looks {c['status_reading']}"})
            self.contact = c
            if self.team is not None:
                self.team.contact = c
        else:
            self._bump(self.belief.update_no_contact(self.pos, self.contact_radius))
        return notes

    def _mark_scanned(self, pos):
        d = self.belief.dist_grid(pos)
        self.scanned |= d <= self.scan_radius

    # ----------------------------------------------------- resource model
    def _fields(self):
        """Pessimistic cost/time-to-nearest-charger fields and optimistic reach field."""
        # unexplored ground on the way home is costed at the open/rubble midpoint;
        # the explicit safety_margin absorbs the remaining risk
        pess = cost_grid(self.known, self.costs, (self.costs.move + self.costs.move_rubble) / 2)
        ret, _ = dijkstra(pess, self.chargers)
        # dijkstra measures charger->cell (cost of entering cells on the way out);
        # convert to cell->charger by swapping the endpoint costs.
        with np.errstate(invalid="ignore"):
            self.ret_field = np.where(np.isfinite(ret), np.maximum(ret - np.where(np.isfinite(pess), pess, 0)
                                                                   + self.costs.move, 0), np.inf)
        for c in self.chargers:
            self.ret_field[c[1], c[0]] = 0.0
        self.ret_time = self.ret_field / self.costs.move  # conservative: time <= cost / move
        opt = cost_grid(self.known, self.costs, self.costs.move * 1.3)
        self.reach, self.reach_parent = dijkstra(opt, [self.pos])
        self._pess = pess

    def return_cost(self, p):
        return float(self.ret_field[p[1], p[0]])

    def _set_mode(self, mode, reason):
        if mode != self.mode:
            self.mode_log.append({"t": self.t, "from": self.mode, "to": mode, "reason": reason})
            self.strategy_changes.append({"t": self.t, "kind": "mode", "from": self.mode, "to": mode,
                                          "reason": reason, "position": list(self.pos)})
            self.mode = mode

    def _step_home(self, reasons):
        dist, parent = dijkstra(self._pess, [self.pos])
        best = min(self.chargers, key=lambda c: dist[c[1], c[0]])
        path = extract_path(parent, self.pos, best)
        if not path:
            return None
        self.path, self.target = path, best
        reasons.append(f"Heading to charger {_fmt(best)} ({len(path)} steps, est. cost {dist[best[1], best[0]]:.1f})")
        return {"type": "move", "dir": direction(self.pos, path[0])}

    def _safety(self, reasons) -> dict | None:
        """Hard rules shared by all agents. Returns an action or None."""
        tleft = self.budget - self.t
        ret = self.return_cost(self.pos)
        ret_t = float(self.ret_time[self.pos[1], self.pos[0]])
        if self.contact is not None or (self.team is not None and self.team.contact is not None):
            who = "" if self.contact is not None else "Teammate has "
            reasons.append(f"{who}EVE located visually; transmitting final report")
            return {"type": "report"}
        if self.mode == "RECHARGE" and self.at_charger:
            if self.battery < self.charge_target - 1e-6 and tleft > self.p["time_margin"] + 2:
                reasons.append(f"Recharging: {self.battery:.0f}/{self.charge_target:.0f}")
                return {"type": "recharge"}
            self._set_mode("EXPLORE", f"Battery restored to {self.battery:.0f}; resuming search")
            self.path = []
        if self.mode != "TURN_BACK" and tleft <= ret_t + self.p["time_margin"]:
            self._set_mode("TURN_BACK", f"Only {tleft} time left vs ~{ret_t:.0f} needed to reach a charger")
        if self.mode == "TURN_BACK":
            if self.at_charger:
                reasons.append("Back at base with time nearly exhausted; reporting best estimate")
                return {"type": "report"}
            reasons.append(f"Turning back: {tleft} time left, ~{ret_t:.0f} needed to get home")
            return self._step_home(reasons) or {"type": "report"}
        worst_step = self.costs.move_rubble
        if not self.at_charger and self.battery - worst_step < ret + self.p["safety_margin"]:
            if self.mode != "RECHARGE":
                self.charge_target = self.capacity
                self._set_mode("RECHARGE", f"Battery {self.battery:.1f} only covers return trip "
                                           f"({ret:.1f}) + reserve {self.p['safety_margin']}")
        if self.mode == "RECHARGE":
            if self.at_charger:
                return {"type": "recharge"}
            reasons.append(f"Battery {self.battery:.1f}, return cost {ret:.1f}: going to recharge")
            return self._step_home(reasons)
        return None

    def retrospective_spoof(self):
        """Re-score every detected reading against the *final* belief: with
        hindsight, readings that the converged posterior cannot explain are
        most likely decoys/spoofs."""
        for r in self.readings:
            if r["detected"]:
                r["spoof_prob_hindsight"] = round(self.belief.spoof_probability(r["position"], r), 3)

    def act(self):  # pragma: no cover - abstract
        raise NotImplementedError

    def decide(self):
        """Wrapper returning (action, decision record)."""
        reasons: list = []
        n_changes = len(self.strategy_changes)
        self._fields()
        action = self.act_with(reasons)
        return action, {
            "mode": self.mode,
            "target": list(self.target) if self.target else None,
            "reasoning": reasons,
            "strategy_change": self.strategy_changes[n_changes:] or None,
        }

    def act_with(self, reasons):
        a = self._safety(reasons)
        return a if a is not None else self.policy(reasons)

    def _report_out_of_options(self, reasons, why):
        if self.battery < self.capacity * 0.9 and self.budget - self.t > 3 * self.p["time_margin"]:
            self.charge_target = self.capacity
            self._set_mode("RECHARGE", why + "; recharging before deciding")
            if self.at_charger:
                return {"type": "recharge"}
            return self._step_home(reasons) or {"type": "report"}
        reasons.append(why + "; reporting best estimate")
        return {"type": "report"}


# ======================================================================
class BayesianAgent(BaseAgent):
    """Chooses waypoints by expected information gain + chance of contact per
    unit battery, scans on arrival, and re-plans whenever evidence moves the
    belief enough to invalidate the current plan."""

    name = "bayesian"
    DEFAULTS = {
        "w_info": 1.0,            # value of one nat of entropy reduction
        "w_contact": 4.0,         # value of P(EVE within contact radius of waypoint)
        "w_clue": 0.6,            # value of scanning unexplored ground for clues
        "cost_offset": 4.0,       # discourages dithering on tiny moves
        "n_candidates": 40,
        "eig_samples": 16,
        "scan_interval": 6,       # consider an opportunistic scan this often
        "opportunistic_eig": 0.5,
        "replan_kl": 0.4,         # belief shift (nats) that invalidates the plan
        "recharge_gain": 1.25,    # recharge first if best unreachable target is this much better
    }

    def policy(self, reasons):
        if getattr(self, "pending_scan", False):
            self.pending_scan = False
            if self.battery - self.costs.scan >= self.return_cost(self.pos) + self.p["safety_margin"]:
                reasons.append(f"Arrived at waypoint {_fmt(self.pos)}: scanning")
                return {"type": "scan"}
        if (self.steps_since_scan >= self.p["scan_interval"]
                and (self.last_scan_pos is None or math.dist(self.pos, self.last_scan_pos) >= 3)):
            eig = self.belief.expected_info_gain(self.pos, self.rng, self.p["eig_samples"])
            if eig >= self.p["opportunistic_eig"]:
                reasons.append(f"Opportunistic scan: expected info gain here {eig:.2f} nats "
                               f">= {self.p['opportunistic_eig']}")
                return {"type": "scan"}
        why = self._needs_replan()
        if why and why.startswith("planned route blocked") and self.known[self.target[1], self.target[0]] != "#":
            path = extract_path(self.reach_parent, self.pos, self.target)
            if path:
                self.path = path
                reasons.append(f"Rerouting around newly seen wall to keep target {_fmt(self.target)}")
                return {"type": "move", "dir": direction(self.pos, self.path[0])}
        if why:
            act = self._replan(why, reasons)
            if act is not None:
                return act
        if not self.path:
            return self._report_out_of_options(reasons, "No worthwhile reachable target")
        reasons.append(f"Continuing to {_fmt(self.target)} ({len(self.path)} steps left)")
        return {"type": "move", "dir": direction(self.pos, self.path[0])}

    def _needs_replan(self):
        if self.last_scan_pos is None and not self.path:
            return "initial plan"
        if not self.path:
            return "waypoint reached"
        if any(self.known[y, x] == "#" for x, y in self.path):
            return "planned route blocked by newly seen wall"
        if self._new_clue:
            return "new clue found"
        if self._kl_since_plan > self.p["replan_kl"]:
            return f"belief shifted {self._kl_since_plan:.2f} nats since plan"
        return None

    def _candidates(self):
        b = self.belief
        pm = b.position()
        cand = set()
        best, _ = b.best_neighbourhood(1)
        cand.add(best)
        top = np.argsort(pm.ravel())[::-1][:12]
        for i in top:
            y, x = divmod(int(i), self.W)
            cand.add((x, y))
        flat = pm.ravel() / pm.sum()
        for i in self.rng.choice(flat.size, size=18, p=flat):
            y, x = divmod(int(i), self.W)
            cand.add((x, y))
        unexplored = np.argwhere(~self.scanned & (self.known != "#"))
        if len(unexplored):
            for i in self.rng.choice(len(unexplored), size=min(10, len(unexplored)), replace=False):
                y, x = unexplored[i]
                cand.add((int(x), int(y)))
        return [c for c in cand if self.known[c[1], c[0]] != "#"][: self.p["n_candidates"]]

    def _replan(self, why, reasons):
        p, b = self.p, self.belief
        scored = []
        unexplored_frac_cache = {}
        for c in self._candidates():
            pc = float(self.reach[c[1], c[0]])
            if not np.isfinite(pc):
                continue
            ret = self.return_cost(c)
            if not np.isfinite(ret):
                ret = pc + 5  # unknown region: assume we come back the way we went
            pcontact = b.mass_within(c, self.contact_radius)
            eig = b.expected_info_gain(c, self.rng, p["eig_samples"])
            if self.last_scan_pos is not None and math.dist(c, self.last_scan_pos) < 2.5:
                eig *= 0.5
            m = b.dist_grid(c) <= self.scan_radius
            unexplored_frac_cache[c] = float((~self.scanned[m]).mean())
            explore_value = p["w_info"] * eig + p["w_clue"] * unexplored_frac_cache[c]
            contact_value = p["w_contact"] * pcontact
            if self.team is not None:
                # coordination: don't send two robots to scan the same ground
                d = self.team.nearest_teammate_target(self, c)
                explore_value *= 1 - 0.8 * math.exp(-(d / (2 * self.scan_radius)) ** 2)
                if d <= self.contact_radius:
                    contact_value *= 0.5
            value = explore_value + contact_value
            cost = pc + self.costs.scan
            util = value / (cost + p["cost_offset"])
            need = pc + self.costs.scan + ret + p["safety_margin"]
            t_need = pc / self.costs.move + 1 + ret / self.costs.move + p["time_margin"]
            ok_time = self.t + t_need <= self.budget
            ok_now = self.battery >= need and ok_time
            # could a full battery from the nearest charger make it?
            ok_full = self.capacity >= 2 * ret + self.costs.scan + p["safety_margin"] and ok_time
            scored.append(dict(cell=c, util=util, eig=eig, pcontact=pcontact, cost=pc, ret=ret,
                               ok_now=ok_now, ok_full=ok_full))
        self._kl_since_plan = 0.0
        self._new_clue = False
        if not scored:
            self.path, self.target = [], None
            return None
        scored.sort(key=lambda s: -s["util"])
        now = [s for s in scored if s["ok_now"]]
        full = [s for s in scored if s["ok_full"]]
        if full and (not now or full[0]["util"] > p["recharge_gain"] * now[0]["util"]) \
                and self.battery < self.capacity - 1e-6 and full[0]["cell"] != (now[0]["cell"] if now else None):
            f = full[0]
            self.charge_target = self.capacity
            self._set_mode("RECHARGE", f"Best target {_fmt(f['cell'])} (utility {f['util']:.3f}) is out of "
                                       f"range on current battery {self.battery:.0f}; recharging first")
            reasons.append(f"Replan ({why}): recharge before going to {_fmt(f['cell'])}")
            if self.at_charger:
                return {"type": "recharge"}
            return self._step_home(reasons)
        if not now:
            self.path, self.target = [], None
            return None
        best, note = self._select(now, why)
        if note:
            reasons.append(note)
        old = self.target
        self.target = best["cell"]
        if self.team is not None:
            self.team.targets[self.robot_id] = self.target
        self.path = extract_path(self.reach_parent, self.pos, self.target) or []
        if not self.path:
            self.pending_scan = True
        new_mode = "PURSUE" if best["pcontact"] > 0.25 else "EXPLORE"
        self._set_mode(new_mode, f"P(EVE near target)={best['pcontact']:.2f}")
        others = [c for c in now if c is not best]
        runner = f"; runner-up {_fmt(others[0]['cell'])} {others[0]['util']:.3f}" if others else ""
        reasons.append(
            f"Replan ({why}): target {_fmt(self.target)} - EIG {best['eig']:.2f} nats, "
            f"P(EVE within {self.contact_radius})={best['pcontact']:.2f}, path cost {best['cost']:.1f}, "
            f"return cost {best['ret']:.1f}, utility {best['util']:.3f} "
            f"(best of {len(now)} feasible{runner})")
        if old is not None and old != self.target and why not in ("waypoint reached", "initial plan"):
            self.strategy_changes.append({"t": self.t, "kind": "retarget", "from": list(old),
                                          "to": list(self.target), "reason": why, "position": list(self.pos)})
        # arriving at the waypoint triggers a scan
        self._arrival_target = self.target
        if not self.path:
            return {"type": "scan"} if self._scan_affordable() else None
        return None

    def _select(self, feasible, why):
        """Pick a waypoint among feasible, utility-sorted candidates.
        Hook for alternative planners (see LLMPlannerAgent)."""
        return feasible[0], None

    def _scan_affordable(self):
        return self.battery - self.costs.scan >= self.return_cost(self.pos) + self.p["safety_margin"]

    def observe(self, action, obs):
        notes = super().observe(action, obs)
        if action["type"] == "move" and not self.path and getattr(self, "_arrival_target", None) == self.pos:
            self.pending_scan = True
            self._arrival_target = None
        if action["type"] == "scan":
            self.pending_scan = False
        return notes


# ======================================================================
class GreedySignalAgent(BaseAgent):
    """Classic 'follow the beacon' heuristic: scan every few steps, walk along
    the last detected bearing, wander if nothing is heard."""

    name = "greedy"
    DEFAULTS = {"scan_every": 3}

    def policy(self, reasons):
        if self.steps_since_scan >= self.p["scan_every"] or not self.readings:
            if self.battery - self.costs.scan >= self.return_cost(self.pos) + self.p["safety_margin"]:
                reasons.append("Periodic scan")
                return {"type": "scan"}
        heard = [r for r in self.readings if r["detected"]]
        if heard:
            heading = heard[-1]["bearing_deg"]
            reasons.append(f"Following last bearing {heading:.0f} deg")
        else:
            heading = getattr(self, "_wander", None)
            if heading is None or self.rng.random() < 0.15:
                heading = self._wander = float(self.rng.uniform(0, 360))
            reasons.append(f"No signal yet; wandering {heading:.0f} deg")
        options = []
        for d, (dx, dy) in {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}.items():
            nx, ny = self.pos[0] + dx, self.pos[1] + dy
            if 0 <= nx < self.W and 0 <= ny < self.H and self.known[ny, nx] != "#":
                b = math.degrees(math.atan2(dx, -dy)) % 360
                diff = abs((heading - b + 180) % 360 - 180)
                options.append((diff + self.rng.random() * 30, d))
        if not options:
            return {"type": "report"}
        return {"type": "move", "dir": min(options)[1]}


class RandomAgent(BaseAgent):
    name = "random"
    DEFAULTS = {"scan_every": 5}

    def policy(self, reasons):
        if self.steps_since_scan >= self.p["scan_every"]:
            if self.battery - self.costs.scan >= self.return_cost(self.pos) + self.p["safety_margin"]:
                reasons.append("Periodic scan")
                return {"type": "scan"}
        opts = [d for d, (dx, dy) in {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}.items()
                if 0 <= self.pos[0] + dx < self.W and 0 <= self.pos[1] + dy < self.H
                and self.known[self.pos[1] + dy, self.pos[0] + dx] != "#"]
        reasons.append("Random step")
        return {"type": "move", "dir": opts[self.rng.integers(len(opts))]} if opts else {"type": "report"}


class LLMPlannerAgent(BayesianAgent):
    """Same perception, candidate generation and safety rules as
    BayesianAgent, but an LLM chooses *which* feasible waypoint to pursue,
    given a plain-language situation report. Any API error, refusal or
    missing credentials falls back to the classical choice, so the robot is
    never left without a decision."""

    name = "llm"
    DEFAULTS = {**BayesianAgent.DEFAULTS, "llm_model": "claude-opus-5-5", "llm_effort": "low",
                "llm_top_k": 8}
    SCHEMA = {
        "type": "object",
        "properties": {"choice": {"type": "integer"}, "reasoning": {"type": "string"}},
        "required": ["choice", "reasoning"],
        "additionalProperties": False,
    }
    SYSTEM = (
        "You are the mission planner for WALL-E, a small robot searching a ruined city for EVE, a robot "
        "whose beacon has gone quiet. Each time you are consulted you receive the current situation and a "
        "numbered list of candidate waypoints that are already checked as safe to reach on the current "
        "battery (including the trip back to a charger). WALL-E will walk to the waypoint you choose and "
        "scan there. Choose the waypoint that best balances finding EVE soon (P(EVE within 1 cell) means "
        "arriving there is likely to make visual contact), learning the most (expected information gain, "
        "in nats) and saving battery and time. Briefly justify the choice in one or two sentences."
    )

    def __init__(self, signal_model=None, params=None, seed=0, client=None):
        super().__init__(signal_model, params, seed)
        self._client = client
        self.llm_calls = 0
        self.llm_fallbacks = 0
        self.llm_log: list = []

    def _get_client(self):
        if self._client is None:
            import anthropic  # optional dependency
            self._client = anthropic.Anthropic()
        return self._client

    def _situation(self, cands, why) -> str:
        b = self.belief.summary()
        clues = "; ".join(f"{e['type']} at {_fmt(e['position'])}: {e['description']}" for e in self.evidence
                          if e["id"] != "contact") or "none"
        lines = [
            f"Re-planning because: {why}.",
            f"WALL-E at {_fmt(self.pos)}, battery {self.battery:.0f}/{self.capacity:.0f}, "
            f"time {self.t}/{self.budget}.",
            f"Belief: most likely EVE cell {_fmt(b['map_cell'])}, P(within 1 cell) {b['p_within_1']:.2f}, "
            f"90% credible region {b['cred90_cells']} cells, entropy {b['entropy']:.2f} nats.",
            "EVE status belief: " + ", ".join(f"{k} {v:.2f}" for k, v in b["status"].items()) + ".",
            f"Learned fraction of spoofed signal readings: {self.belief.spoof_rate:.0%}.",
            f"Clues found: {clues}.",
            "Candidates:",
        ]
        for i, c in enumerate(cands):
            lines.append(f"{i}. cell {_fmt(c['cell'])}: path cost {c['cost']:.1f}, return-to-charger cost "
                         f"{c['ret']:.1f}, P(EVE within 1) {c['pcontact']:.2f}, expected info gain "
                         f"{c['eig']:.2f} nats, classical utility {c['util']:.3f}")
        lines.append("Reply with the number of the waypoint to go to next.")
        return "\n".join(lines)

    def _select(self, feasible, why):
        cands = feasible[: self.p["llm_top_k"]]
        if len(cands) == 1:
            return cands[0], None
        prompt = self._situation(cands, why)
        try:
            client = self._get_client()
            resp = client.beta.messages.create(
                model=self.p["llm_model"],
                max_tokens=16000,
                system=self.SYSTEM,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": self.p["llm_effort"],
                               "format": {"type": "json_schema", "schema": self.SCHEMA}},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
            self.llm_calls += 1
            if resp.stop_reason == "refusal":
                raise RuntimeError("model declined")
            text = next(b.text for b in resp.content if b.type == "text")
            out = json.loads(text)
            idx = int(out["choice"])
            if not 0 <= idx < len(cands):
                raise ValueError(f"choice {idx} out of range")
            self.llm_log.append({"t": self.t, "prompt": prompt, "choice": idx, "reasoning": out["reasoning"]})
            return cands[idx], f"LLM planner chose #{idx} {_fmt(cands[idx]['cell'])}: {out['reasoning']}"
        except Exception as e:  # noqa: BLE001 - any failure -> safe classical fallback
            self.llm_fallbacks += 1
            self.llm_log.append({"t": self.t, "prompt": prompt, "error": f"{type(e).__name__}: {e}"})
            return cands[0], f"LLM planner unavailable ({type(e).__name__}); using classical choice"


class Team:
    """Shared world model for cooperating robots (perfect communication):
    one belief, one map, one evidence log, plus everyone's current target."""

    def __init__(self, names=None):
        self.members: list = []
        self.names = names or ["WALL-E", "M-O", "BURN-E", "VN-GO"]
        self.belief = self.known = self.scanned = None
        self.evidence: list = []
        self.readings: list = []
        self.contact = None
        self.targets: dict = {}

    def name(self, agent) -> str:
        return self.names[agent.robot_id % len(self.names)]

    def nearest_teammate_target(self, agent, cell) -> float:
        ds = [math.dist(cell, t) for i, t in self.targets.items() if i != agent.robot_id and t is not None]
        return min(ds) if ds else float("inf")


AGENTS = {"bayesian": BayesianAgent, "llm": LLMPlannerAgent, "greedy": GreedySignalAgent, "random": RandomAgent}


def make_agent(name: str, signal_model=None, params=None, seed=0) -> BaseAgent:
    if name == "bayesian-naive":  # ablation: no spoof/outlier model
        a = BayesianAgent(signal_model, {**(params or {}), "spoof_prior": 0.0}, seed)
        a.name = "bayesian-naive"
        return a
    if name not in AGENTS:
        raise ValueError(f"unknown agent {name!r}; choose from {list(AGENTS) + ['bayesian-naive']}")
    return AGENTS[name](signal_model, params, seed)
