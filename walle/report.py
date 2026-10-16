"""Final mission report: evidence, inferred location/status, confidence and a
recommended next move for WALL-E."""
from __future__ import annotations

import math

from .sensors import STATUSES


def _conf_label(p):
    return "HIGH" if p >= 0.8 else "MEDIUM" if p >= 0.4 else "LOW"


def _decoy(b, flagged):
    cell, mass = b.decoy_estimate()
    if len(flagged) < 2 or mass < 0.3:
        return None
    return {"position": list(cell), "p_within_1": round(mass, 3)}


def build_report(cfg, env, agent, outcome: dict) -> dict:
    b = agent.belief
    summ = b.summary()
    est = tuple(summ["map_cell"])
    status_post = b.status()
    status_est = max(status_post, key=status_post.get)
    p_loc = b.mass_within(est, 1)
    conf = min(p_loc, 1.0)
    nearest_charger = min(cfg.chargers, key=lambda c: math.dist(c, est))

    contact = agent.contact is not None
    if contact:
        if status_est == "active":
            rec = (f"Rendezvous with EVE at {tuple(est)} - she is responsive. Hand over the plant and return "
                   f"to the truck at {tuple(cfg.start)} together.")
        elif status_est == "low_power":
            rec = (f"EVE is in low-power standby at {tuple(est)}. Carry her to the nearest charger "
                   f"{tuple(nearest_charger)} (~{math.dist(est, nearest_charger):.0f} cells) and recharge her "
                   f"before attempting to wake her.")
        else:
            rec = (f"EVE is damaged at {tuple(est)}. Stabilise her, avoid rubble on the way back, and carry "
                   f"her to the truck at {tuple(cfg.start)} for repairs.")
    elif conf >= 0.4:
        rec = (f"Recharge at {tuple(nearest_charger)}, then travel directly to {tuple(est)} "
               f"(P(EVE within 1 cell) = {p_loc:.2f}) and scan on arrival.")
    else:
        mx, my = b.mean()
        rec = (f"Location still uncertain (90% region = {summ['cred90_cells']} cells around "
               f"({mx:.0f},{my:.0f})). Recharge fully, then sweep that region with scans every "
               f"{2 * cfg.scan_radius} cells, prioritising the {_conf_label(p_loc).lower()}-confidence "
               f"hot-spot at {tuple(est)}.")

    readings = agent.readings
    detected = [r for r in readings if r["detected"]]
    flagged = [r for r in detected if r["spoof_prob"] > 0.5 or r.get("spoof_prob_hindsight", 0) > 0.5]
    strongest = max(detected, key=lambda r: r["strength"]) if detected else None

    truth = env.truth()
    eval_ = {
        "eve_found": contact,
        "location_error_cells": round(math.dist(est, truth["eve_position"]), 2),
        "status_correct": status_est == truth["eve_status"],
        "true_position": truth["eve_position"],
        "true_status": truth["eve_status"],
        "clues_found": f"{len(env.found_clues)}/{len(cfg.clues)}",
        "decoy_readings_received": outcome.get("decoy_readings", 0),
        "decoy_readings_flagged": outcome.get("decoy_flagged", 0),
        "genuine_readings_flagged": outcome.get("genuine_flagged", 0),
    }
    return {
        "mission": cfg.name,
        "agent": agent.name,
        "outcome": {
            "end_reason": outcome["end_reason"],
            "eve_located_visually": contact,
            "time_used": outcome["time"],
            "time_budget": cfg.time_budget,
            "battery_remaining": round(outcome["battery"], 1),
            "battery_consumed": round(outcome["battery_used"], 1),
            "scans": agent.scans,
            "recharges": outcome["recharges"],
            "distance_travelled": outcome["moves"],
            **({"robots": outcome["robots"]} if outcome.get("robots") else {}),
        },
        "evidence": {
            "clues": [{k: e[k] for k in ("id", "type", "position", "description", "t")} for e in agent.evidence],
            "signal": {
                "scans": len(readings),
                "detections": len(detected),
                "no_signal": len(readings) - len(detected),
                "strongest": strongest,
                "suspected_spoofs": flagged,
                "learned_spoof_rate": round(b.spoof_rate, 3),
                "suspected_decoy_transmitter": _decoy(b, flagged),
            },
        },
        "inference": {
            "eve_location": list(est),
            "p_at_cell": summ["map_prob"],
            "p_within_1_cell": round(p_loc, 3),
            "credible_region_90_cells": summ["cred90_cells"],
            "posterior_mean": [round(v, 2) for v in b.mean()],
            "status": status_est,
            "status_posterior": {k: round(status_post[k], 3) for k in STATUSES},
        },
        "confidence": {
            "location": round(conf, 3),
            "location_label": _conf_label(conf),
            "status": round(status_post[status_est], 3),
            "status_label": _conf_label(status_post[status_est]),
        },
        "recommended_next_step": rec,
        "strategy_changes": agent.strategy_changes,
        "evaluation_vs_ground_truth": eval_,
    }


def report_markdown(r: dict, ascii_map: str | None = None) -> str:
    o, inf, conf, ev = r["outcome"], r["inference"], r["confidence"], r["evidence"]
    L = [f"# Mission report - {r['mission']}", "",
         f"**Agent:** `{r['agent']}`  ",
         f"**Outcome:** {o['end_reason']} - EVE {'LOCATED (visual contact)' if o['eve_located_visually'] else 'not visually confirmed'}",
         "", "## Recommended next step", "", f"> {r['recommended_next_step']}", "",
         "## Inferred location & status", "",
         "| | value |", "|---|---|",
         f"| Most likely cell | `{tuple(inf['eve_location'])}` |",
         f"| P(EVE within 1 cell) | {inf['p_within_1_cell']:.3f} ({conf['location_label']}) |",
         f"| 90% credible region | {inf['credible_region_90_cells']} cells |",
         f"| Posterior mean | `{tuple(inf['posterior_mean'])}` |",
         f"| Status | **{inf['status']}** ({conf['status']:.2f}, {conf['status_label']}) |",
         f"| Status posterior | " + ", ".join(f"{k}: {v:.2f}" for k, v in inf["status_posterior"].items()) + " |",
         "", "## Evidence", "", "### Clues", ""]
    if ev["clues"]:
        L += ["| t | id | type | position | observation |", "|---|---|---|---|---|"]
        L += [f"| {c['t']} | {c['id']} | {c['type']} | `{tuple(c['position'])}` | {c['description']} |"
              for c in ev["clues"]]
    else:
        L.append("_No physical clues found._")
    s = ev["signal"]
    L += ["", "### Signal", "",
          f"- Scans: {s['scans']} ({s['detections']} detections, {s['no_signal']} no-signal readings)"]
    if s["strongest"]:
        st = s["strongest"]
        L.append(f"- Strongest: {st['strength']:.1f} at bearing {st['bearing_deg']:.0f} deg from "
                 f"`{tuple(st['position'])}` (t={st['t']})")
    L.append(f"- Learned fraction of spoofed readings: {s['learned_spoof_rate']:.0%}")
    if s.get("suspected_decoy_transmitter"):
        d = s["suspected_decoy_transmitter"]
        L.append(f"- Suspected decoy transmitter near `{tuple(d['position'])}` (P within 1 cell = {d['p_within_1']:.2f})")
    if s["suspected_spoofs"]:
        L.append(f"- {len(s['suspected_spoofs'])} reading(s) flagged as probable spoof/decoy "
                 "(live = at the time; hindsight = against the final belief):")
        for f in s["suspected_spoofs"]:
            L.append(f"  - t={f['t']} at `{tuple(f['position'])}`: {f['strength']:.1f} @ {f['bearing_deg']:.0f} deg "
                     f"(P(spoof) live {f['spoof_prob']:.2f}, hindsight {f.get('spoof_prob_hindsight', 0):.2f})")
    L += ["", "## Resources", "",
          f"- Time used: {o['time_used']}/{o['time_budget']}",
          f"- Battery consumed: {o['battery_consumed']} (remaining {o['battery_remaining']})",
          f"- Moves: {o['distance_travelled']}, scans: {o['scans']}, recharge steps: {o['recharges']}",
          ]
    if o.get("robots"):
        L += ["", "| robot | moves | scans | recharge steps | battery used | battery left |", "|---|---|---|---|---|---|"]
        L += [f"| {r['robot']} | {r['moves']} | {r['scans']} | {r['recharges']} | {r['battery_used']} | "
              f"{r['battery_left']} |" for r in o["robots"]]
    L += ["", "## Strategy changes", ""]
    if r["strategy_changes"]:
        for c in r["strategy_changes"]:
            who = f"**{c['robot']}** " if c.get("robot") else ""
            if c["kind"] == "mode":
                L.append(f"- {who}t={c['t']} at `{tuple(c['position'])}`: **{c['from']} -> {c['to']}** - {c['reason']}")
            else:
                L.append(f"- {who}t={c['t']} at `{tuple(c['position'])}`: retarget `{tuple(c['from'])}` -> "
                         f"`{tuple(c['to'])}` - {c['reason']}")
    else:
        L.append("_None._")
    if r.get("llm_planner"):
        lp = r["llm_planner"]
        L += ["", "## LLM planner", "",
              f"- Model `{lp['model']}`: {lp['calls']} successful calls, {lp['fallbacks']} fallbacks to the "
              "classical choice (see `llm_decisions.jsonl` for every prompt and rationale)"]
    e = r["evaluation_vs_ground_truth"]
    L += ["", "## Ground-truth check (simulation only - hidden from the agent)", "",
          f"- True EVE: `{tuple(e['true_position'])}`, {e['true_status']}",
          f"- Location error: {e['location_error_cells']} cells; status correct: {e['status_correct']}",
          f"- Clues found: {e['clues_found']}",
          f"- Decoy readings received: {e['decoy_readings_received']}, of which flagged: "
          f"{e['decoy_readings_flagged']}; genuine readings wrongly flagged: {e['genuine_readings_flagged']}"]
    if ascii_map:
        L += ["", "## Final map", "", "```", ascii_map, "```"]
    return "\n".join(L) + "\n"
