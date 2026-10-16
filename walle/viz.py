"""Visualisation: ASCII maps (always available) and matplotlib figures/GIFs
(optional - only imported when requested)."""
from __future__ import annotations

import numpy as np

CLUE_CHAR = {"hover_tracks": "t", "debris": "d", "power_cell": "p", "beacon_log": "b", "plant": "g"}
MODE_COLOR = {"EXPLORE": "#2a78d6", "PURSUE": "#1baf7a", "RECHARGE": "#eda100", "TURN_BACK": "#e34948"}
SHADES = " .:-=+*%@"
ROBOT_COLORS = ["#eb6834", "#008300", "#e34948", "#1baf7a"]  # WALL-E orange, M-O green, ...
CLUE_COLOR = "#0b0b0b"  # team plots: colour = robot


def _paths(agent):
    """[(trajectory, colour or None)] - None means 'colour by strategy mode'."""
    if hasattr(agent, "paths"):
        return agent.paths()
    return [(agent.trajectory, None)]

ASCII_LEGEND = ("Legend: # wall  ~ rubble  C charger  S start  * WALL-E path  W WALL-E  E EVE (truth)\n"
                "        e agent's estimate  t/d/p/b/g clue found (tracks/debris/power cell/log/plant)\n"
                "        ? clue missed  D decoy transmitter")


def ascii_map(cfg, trajectory, found_ids, estimate=None, show_truth=True, known=None, others=None) -> str:
    """Render the map. With ``known`` (the agent's partial map) unexplored cells are blank."""
    if known is not None:
        g = [[" " if ch == "?" else ch for ch in row] for row in known.tolist()]
    else:
        g = [row[:] for row in cfg.grid]
    for (x, y), *_ in trajectory:
        if g[y][x] in ".~":
            g[y][x] = "*"
    if show_truth:
        for d in cfg.decoys:
            x, y = d["position"]
            g[y][x] = "D"
        for c in cfg.clues:
            x, y = c["position"]
            g[y][x] = CLUE_CHAR[c["type"]] if c["id"] in found_ids else "?"
    sx, sy = cfg.start
    g[sy][sx] = "S"
    if estimate is not None:
        g[estimate[1]][estimate[0]] = "e"
    if show_truth:
        ex, ey = cfg.eve_position
        g[ey][ex] = "E"
    for (ox, oy), ch in others or []:
        g[oy][ox] = ch
    wx, wy = trajectory[-1][0]
    g[wy][wx] = "W"
    border = "+" + "-" * cfg.width + "+"
    return "\n".join([border] + ["|" + "".join(r) + "|" for r in g] + [border, ASCII_LEGEND])


def ascii_belief(pos_marginal: np.ndarray, walle=None) -> str:
    p = pos_marginal / max(pos_marginal.max(), 1e-12)
    rows = []
    for y in range(p.shape[0]):
        row = ""
        for x in range(p.shape[1]):
            if walle is not None and (x, y) == tuple(walle):
                row += "W"
            else:
                row += SHADES[min(int(p[y, x] * (len(SHADES) - 1) + 0.5), len(SHADES) - 1)]
        rows.append("|" + row + "|")
    border = "+" + "-" * p.shape[1] + "+"
    return "\n".join([border] + rows + [border, "Belief over EVE's position (darker glyph = more likely)"])


# ------------------------------------------------------------- matplotlib
def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#a3a29b", "axes.labelcolor": "#52514e",
                         "xtick.color": "#52514e", "ytick.color": "#52514e", "axes.titleweight": "bold",
                         "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
    return plt


def _terrain_rgb(cfg):
    col = {".": (0.99, 0.99, 0.98), "~": (0.89, 0.85, 0.76), "#": (0.30, 0.30, 0.29), "C": (0.99, 0.99, 0.98)}
    return np.array([[col[ch] for ch in row] for row in cfg.grid])


def _draw_map(ax, cfg, belief_pm, paths, found_ids, estimate, t_upto=None, scans=None, title=None):
    """``paths``: [(trajectory, colour|None)]; ``t_upto``: only draw moves up to this mission time."""
    from matplotlib.colors import LinearSegmentedColormap
    ax.imshow(_terrain_rgb(cfg), origin="upper", interpolation="nearest")
    if belief_pm is not None:
        cmap = LinearSegmentedColormap.from_list("b", [(0.16, 0.47, 0.84, 0.0), (0.05, 0.25, 0.60, 0.85)])
        ax.imshow(belief_pm / max(belief_pm.max(), 1e-12), cmap=cmap, origin="upper",
                  interpolation="nearest", vmin=0, vmax=1)
    ends = []
    for traj, colour in paths:
        pts = traj if t_upto is None else [p for p in traj if p[1] <= t_upto]
        xs = [p[0][0] for p in pts]
        ys = [p[0][1] for p in pts]
        modes = [p[2] for p in pts]
        for i in range(1, len(pts)):
            ax.plot(xs[i - 1:i + 1], ys[i - 1:i + 1], color=colour or MODE_COLOR.get(modes[i], "#2a78d6"),
                    lw=2, solid_capstyle="round", zorder=3)
        if pts:
            ends.append((pts[-1][0], colour))
    for cx, cy in cfg.chargers:
        ax.scatter(cx, cy, marker="s", s=70, c="#eda100", edgecolors="#fcfcfb", lw=1.5, zorder=4)
    if scans:
        ax.scatter([s[0] for s in scans], [s[1] for s in scans], s=22, facecolors="#fcfcfb",
                   edgecolors="#2a78d6", lw=1.2, zorder=5)
    for c in cfg.clues:
        x, y = c["position"]
        if c["id"] in found_ids:
            ax.scatter(x, y, marker="D", s=60, c=CLUE_COLOR, edgecolors="#fcfcfb", lw=1.5, zorder=6)
            ax.annotate(c["type"].replace("_", " "), (x, y), xytext=(4, 4), textcoords="offset points",
                        fontsize=7, color="#0b0b0b", zorder=7)
        else:
            ax.scatter(x, y, marker="D", s=40, facecolors="none", edgecolors="#898781", lw=1, zorder=6)
    for d in cfg.decoys:
        ax.scatter(*d["position"], marker="X", s=80, c="#6250d6", edgecolors="#fcfcfb", lw=1.2, zorder=6)
    if estimate is not None:
        ax.scatter(*estimate, marker="o", s=200, facecolors="none", edgecolors="#0b0b0b", lw=2, zorder=8)
    ax.scatter(*cfg.eve_position, marker="*", s=220, c="#e87ba4", edgecolors="#0b0b0b", lw=0.8, zorder=9)
    for end, colour in ends:
        ax.scatter(*end, marker="o", s=70, c=colour or "#0b0b0b", edgecolors="#fcfcfb", lw=1.5, zorder=10)
    ax.set_xticks([])
    ax.set_yticks([])
    if title:
        ax.set_title(title, loc="left")


def _legend(ax, has_decoys, robot_names=None):
    from matplotlib.lines import Line2D
    if robot_names:
        h = [Line2D([], [], color=ROBOT_COLORS[i % len(ROBOT_COLORS)], lw=2, marker="o", label=n)
             for i, n in enumerate(robot_names)]
    else:
        h = [Line2D([], [], color=c, lw=2, label=m.title().replace("_", " ")) for m, c in MODE_COLOR.items()]
    h += [Line2D([], [], marker="o", ls="", mfc="#fcfcfb", mec="#2a78d6", label="Scan"),
          Line2D([], [], marker="D", ls="", color=CLUE_COLOR, mec="#fcfcfb", label="Clue found"),
          Line2D([], [], marker="D", ls="", mfc="none", mec="#898781", label="Clue missed"),
          Line2D([], [], marker="s", ls="", color="#eda100", label="Charger"),
          Line2D([], [], marker="*", ls="", ms=12, color="#e87ba4", mec="#0b0b0b", label="EVE (truth)"),
          Line2D([], [], marker="o", ls="", ms=10, mfc="none", mec="#0b0b0b", label="Agent's estimate"),
          ] + ([] if robot_names else [Line2D([], [], marker="o", ls="", color="#0b0b0b", label="WALL-E")])
    if has_decoys:
        h.append(Line2D([], [], marker="X", ls="", color="#6250d6", label="Decoy"))
    ax.legend(handles=h, loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=8)


def plot_mission(path, cfg, agent, frames, title):
    """Big path map on top; a strip of belief snapshots underneath showing how
    the posterior over EVE's position evolved."""
    plt = _plt()
    aspect = cfg.height / cfg.width
    fig = plt.figure(figsize=(12, 12 * aspect * 0.78 + 12 * aspect * 0.24 + 1.0))
    gs = fig.add_gridspec(2, 4, height_ratios=[3.2, 1], hspace=0.12, wspace=0.05)
    ax = fig.add_subplot(gs[0, :])
    scans = [tuple(r["position"]) for r in agent.readings]
    found = {e["id"] for e in agent.evidence}
    _draw_map(ax, cfg, None, _paths(agent), found, agent.belief.map_cell(), scans=scans, title=title)
    placed = []
    for c in agent.strategy_changes:
        if c["kind"] != "mode":
            continue
        p = tuple(c["position"])
        placed = [q for q in placed if q[0] != p]
        who = f"{c['robot']} " if c.get("robot") else ""
        placed.append((p, f"t{c['t']} {who}{c['to'].lower().replace('_', ' ')}"))
    for p, txt in placed:
        ax.annotate(txt, p, xytext=(5, -11), textcoords="offset points", fontsize=7, color="#0b0b0b",
                    zorder=11, bbox=dict(boxstyle="round,pad=0.15", fc="#fcfcfb", ec="none", alpha=0.85))
    _legend(ax, bool(cfg.decoys), getattr(agent, "robot_names", None))
    # belief snapshots: start, two intermediate, and just before the end
    n = len(frames)
    picks = sorted({0, n // 3, (2 * n) // 3, max(0, n - 2 if agent.contact else n - 1)})
    while len(picks) < 4:
        picks.append(picks[-1])
    for k, i in enumerate(picks[:4]):
        ti, pm, t = frames[i]
        a = fig.add_subplot(gs[1, k])
        y, x = np.unravel_index(int(np.argmax(pm)), pm.shape)
        _draw_map(a, cfg, pm, _paths(agent), set(), None, t_upto=t)
        a.scatter(x, y, marker="o", s=60, facecolors="none", edgecolors="#0b0b0b", lw=1.5, zorder=12)
        ent = abs(float(-(pm[pm > 0] * np.log(pm[pm > 0])).sum()))
        a.set_title(f"belief at t={t}  (H={ent:.1f} nats)", loc="left", fontsize=8, fontweight="normal")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def plot_timeline(path, history, budget, capacity):
    plt = _plt()
    t = [h["t"] for h in history]
    fig, axes = plt.subplots(4, 1, figsize=(10, 7), sharex=True,
                             gridspec_kw={"height_ratios": [0.35, 1, 1, 1]})
    ax = axes[0]
    for i in range(len(history) - 1):
        ax.axvspan(t[i], t[i + 1], color=MODE_COLOR.get(history[i]["mode"], "#2a78d6"), lw=0)
    ax.set_yticks([])
    ax.set_title("Mode (strategy) over time" + (f" - {history[0]['robot_names'][0]}"
                                                 if history[0].get("robot_names") else ""), loc="left")
    series = [("battery", "Battery", capacity, "#2a78d6"),
              ("entropy", "Belief entropy (nats)", None, "#2a78d6"),
              ("p_within_1", "P(EVE within 1 cell of estimate)", 1.0, "#2a78d6")]
    names = history[0].get("robot_names")
    for ax, (k, lab, top, col) in zip(axes[1:], series):
        if k == "battery" and names:
            for i, n in enumerate(names):
                ax.plot(t, [h["batteries"][i] for h in history], color=ROBOT_COLORS[i % len(ROBOT_COLORS)],
                        lw=2, label=n)
            ax.legend(frameon=False, fontsize=8, loc="upper right")
            lab = "Battery per robot"
        else:
            ax.plot(t, [h[k] for h in history], color=col, lw=2)
        ax.set_title(lab, loc="left")
        ax.grid(axis="y", color="#e6e5e0", lw=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(bottom=0, top=top * 1.05 if top else None)
        for h in history:
            if h.get("scan_detected") is not None and k == "entropy":
                ax.axvline(h["t"], color="#d4d3cc", lw=0.6, zorder=0)
    axes[-1].set_xlabel("mission time")
    axes[-1].set_xlim(0, max(t[-1], 1))
    from matplotlib.patches import Patch
    axes[0].legend(handles=[Patch(color=c, label=m.title().replace("_", " ")) for m, c in MODE_COLOR.items()],
                   loc="upper left", bbox_to_anchor=(1.0, 1.4), frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def animate(path, cfg, agent, frames, every=2):
    """frames: list of (step_index_into_trajectory, belief position marginal)."""
    plt = _plt()
    from PIL import Image
    images = []
    found_by_t = [(e["t"], e["id"]) for e in agent.evidence]
    for k, (ti, pm, t) in enumerate(frames):
        if k % every and k != len(frames) - 1:
            continue
        fig, ax = plt.subplots(figsize=(8, 8 * cfg.height / cfg.width + 0.6))
        found = {i for tt, i in found_by_t if tt <= t}
        scans = [tuple(r["position"]) for r in agent.readings if r["t"] <= t]
        y, x = np.unravel_index(int(np.argmax(pm)), pm.shape)
        _draw_map(ax, cfg, pm, _paths(agent), found, (int(x), int(y)), t_upto=t, scans=scans,
                  title=f"t = {t}   mode = {agent.mode_at(t)}" if hasattr(agent, "mode_at")
                  else f"t = {t}   mode = {agent.trajectory[ti][2]}")
        fig.tight_layout()
        fig.canvas.draw()
        images.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3]))
        plt.close(fig)
    if images:
        images[0].save(path, save_all=True, append_images=images[1:] + [images[-1]] * 8,
                       duration=120, loop=0, optimize=True)
