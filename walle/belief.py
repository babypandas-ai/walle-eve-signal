"""Bayesian belief over EVE's hidden state.

The belief is a discrete joint posterior ``P[status, y, x]`` -- where EVE is
*and* what condition she is in. The two are coupled because a damaged or
low-power EVE transmits differently, so a weak reading could mean "far away"
or "nearby but failing"; keeping the joint distribution lets later evidence
(clues, dropouts, visual contact) disentangle the two.
"""
from __future__ import annotations

import math

import numpy as np

from .sensors import CLUE_BEARING_SIGMA, CLUE_TYPES, STATUSES, SignalModel, ang_diff, norm_pdf

DEFAULT_STATUS_PRIOR = {"active": 0.4, "low_power": 0.35, "damaged": 0.25}


class Belief:
    def __init__(self, width: int, height: int, signal_model: SignalModel,
                 status_prior: dict | None = None, spoof_prior: float = 0.15, floor: float = 1e-5,
                 temper: float = 1.0):
        self.W, self.H = width, height
        self.sm = signal_model
        self.spoof_prior = spoof_prior
        # likelihood tempering (L ** temper): consecutive readings are not truly
        # independent (multipath, decoys, model mismatch), so full-strength Bayes
        # updates are over-confident. temper < 1 discounts each reading.
        self.temper = temper
        self.floor = floor  # mixing weight that keeps the belief from ever fully committing
        prior = status_prior or DEFAULT_STATUS_PRIOR
        sp = np.array([prior[s] for s in STATUSES], dtype=float)
        self.P = np.ones((len(STATUSES), height, width)) * (sp / sp.sum())[:, None, None]
        self.mask = np.ones((height, width), dtype=bool)  # cells EVE could physically occupy
        self.P /= self.P.sum()
        self.xs, self.ys = np.meshgrid(np.arange(width), np.arange(height))
        self._init_spoof_model()

    # ------------------------------------------------------------ geometry
    def dist_grid(self, pos):
        return np.hypot(self.xs - pos[0], self.ys - pos[1])

    def bearing_grid(self, pos):
        return np.degrees(np.arctan2(self.xs - pos[0], -(self.ys - pos[1]))) % 360.0

    def cheb_grid(self, pos):
        return np.maximum(np.abs(self.xs - pos[0]), np.abs(self.ys - pos[1]))

    # ------------------------------------------------------------- updates
    def _apply(self, L: np.ndarray) -> float:
        """Multiply by likelihood, renormalise; returns KL(new || old) in nats."""
        old = self.P
        new = old * L
        new[:, ~self.mask] = 0.0
        z = new.sum()
        if not np.isfinite(z) or z <= 0:
            return 0.0  # evidence contradicts everything we believe: ignore it
        new /= z
        if self.floor > 0:
            u = self.mask[None] * new.sum(axis=(1, 2), keepdims=True) / self.mask.sum()
            new = (1 - self.floor) * new + self.floor * u
            new /= new.sum()
        with np.errstate(divide="ignore", invalid="ignore"):
            kl = float(np.nansum(np.where(new > 0, new * np.log(new / np.maximum(old, 1e-300)), 0.0)))
        self.P = new
        return kl

    def signal_terms(self, pos, reading, inflate=0.0):
        D, B = self.dist_grid(pos), self.bearing_grid(pos)
        return self.sm.likelihood(reading, D, B, inflate=inflate)

    # --------------------------------------------------- spoof / decoy model
    @property
    def spoof_rate(self) -> float:
        return self._spoof_a / (self._spoof_a + self._spoof_b)

    def _init_spoof_model(self):
        # Beta prior on the fraction of readings that are spoofed (mean = spoof_prior)
        self._spoof_a = 10.0 * self.spoof_prior
        self._spoof_b = 10.0 * (1 - self.spoof_prior)
        # belief over where a decoy transmitter sits (if any)
        self.Q = np.ones((self.H, self.W)) / (self.H * self.W)

    def spoof_terms(self, pos, reading: dict):
        """Likelihood of a detected reading under the spoof hypothesis, per
        candidate decoy cell (H, W), plus the location-free background term."""
        D, B = self.dist_grid(pos), self.bearing_grid(pos)
        Ld = self.sm.likelihood(reading, D, B)[0]  # decoys transmit like a healthy beacon
        a = self.sm.auth_likelihood(reading, spoof=True)
        return Ld * a, self.sm.background_likelihood() * a

    def spoof_probability(self, pos, reading: dict) -> float:
        """P(reading was spoofed | everything believed now)."""
        if not reading.get("detected") or self.spoof_prior <= 0:
            return 0.0
        eps = self.spoof_rate
        Le = self.signal_terms(pos, reading) * self.sm.auth_likelihood(reading, spoof=False)
        Ld, Lb = self.spoof_terms(pos, reading)
        ev_e = float((self.P * Le).sum())
        ev_d = 0.7 * float((self.Q * Ld).sum()) + 0.3 * Lb
        return eps * ev_d / (eps * ev_d + (1 - eps) * ev_e + 1e-300)

    def update_signal(self, pos, reading: dict, inflate: float = 0.0, robust: bool = True) -> dict:
        """Robust update. A detected reading is explained by a mixture of
        (a) EVE's genuine beacon and (b) a spoof: either a decoy transmitter at
        an unknown location (tracked in ``Q``) or unstructured interference.
        We use an assumed-density (factorised) filter: P and Q are each updated
        with the other hypothesis marginalised out, and the spoof rate is
        learned online from the posterior responsibilities (soft EM)."""
        Le = self.signal_terms(pos, reading, inflate)
        if not (reading.get("detected") and robust and self.spoof_prior > 0):
            return {"kl": self._apply(Le ** self.temper), "spoof_prob": 0.0}
        eps = self.spoof_rate
        Le = Le * self.sm.auth_likelihood(reading, spoof=False)
        Ld, Lb = self.spoof_terms(pos, reading)
        ev_e = float((self.P * Le).sum())
        ev_d = 0.7 * float((self.Q * Ld).sum()) + 0.3 * Lb
        r = eps * ev_d / (eps * ev_d + (1 - eps) * ev_e + 1e-300)
        kl = self._apply(((1 - eps) * Le + eps * ev_d) ** self.temper)
        Qn = self.Q * (eps * (0.7 * Ld + 0.3 * Lb) + (1 - eps) * ev_e)
        if Qn.sum() > 0:
            Qn /= Qn.sum()
            self.Q = 0.995 * Qn + 0.005 / Qn.size
        self._spoof_a += r
        self._spoof_b += 1 - r
        return {"kl": kl, "spoof_prob": r}

    def decoy_estimate(self):
        y, x = np.unravel_index(int(np.argmax(self.Q)), self.Q.shape)
        m = float(self.Q[self.cheb_grid((x, y)) <= 1].sum())
        return (int(x), int(y)), m

    def update_clue(self, clue: dict) -> float:
        t, c, pos = clue["type"], clue["content"], clue["position"]
        if t == "hover_tracks":
            db = ang_diff(c["bearing_deg"], self.bearing_grid(pos))
            Lp = 0.9 * norm_pdf(db, CLUE_BEARING_SIGMA) + 0.1 / 360.0
            Lp = np.where(self.dist_grid(pos) < 0.5, 1 / 360.0, Lp)
        elif t in ("debris", "power_cell", "plant"):
            inside = self.dist_grid(pos) <= c["within"] + 0.5
            hi = 0.97 if t == "plant" else 0.9
            Lp = np.where(inside, hi, 1 - hi)
        elif t == "beacon_log":
            g = self.xs if c["axis"] == "x" else self.ys
            Lp = np.where((g >= c["min"]) & (g <= c["max"]), 0.92, 0.08)
        else:
            raise ValueError(t)
        lr = CLUE_TYPES[t][1]
        Ls = np.array([lr[s] for s in STATUSES]).reshape(-1, 1, 1)
        return self._apply(Lp[None] * Ls)

    def update_no_contact(self, pos, radius: int, miss_prob: float = 0.03) -> float:
        """WALL-E is here and does not see EVE -> she is not within ``radius``."""
        near = self.cheb_grid(pos) <= radius
        if not (self.P[:, near].sum() > 0):
            return 0.0
        L = np.where(near, miss_prob, 1.0)[None]
        return self._apply(L)

    def update_contact(self, eve_pos, status_reading: str, accuracy: float = 0.95) -> float:
        Lp = np.zeros((self.H, self.W))
        Lp[eve_pos[1], eve_pos[0]] = 1.0
        Ls = np.array([accuracy if s == status_reading else (1 - accuracy) / 2 for s in STATUSES])
        self.floor = 0.0
        return self._apply(Lp[None] * Ls.reshape(-1, 1, 1))

    def exclude(self, cells) -> None:
        """Cells known to be walls cannot hold EVE."""
        changed = False
        for x, y in cells:
            if self.mask[y, x]:
                self.mask[y, x] = False
                changed = True
        if changed:
            self.P[:, ~self.mask] = 0.0
            self.P /= self.P.sum()

    def apply_gaussian_prior(self, center, sigma: float) -> float:
        d = self.dist_grid(center)
        return self._apply(np.exp(-0.5 * (d / sigma) ** 2)[None] + 1e-3)

    # ------------------------------------------------------------ queries
    def position(self) -> np.ndarray:
        return self.P.sum(axis=0)

    def status(self) -> dict:
        s = self.P.sum(axis=(1, 2))
        return {k: float(v) for k, v in zip(STATUSES, s)}

    def entropy(self) -> float:
        p = self.P[self.P > 0]
        return float(-(p * np.log(p)).sum())

    def position_entropy(self) -> float:
        p = self.position()
        p = p[p > 0]
        return float(-(p * np.log(p)).sum())

    def map_cell(self) -> tuple:
        pm = self.position()
        y, x = np.unravel_index(int(np.argmax(pm)), pm.shape)
        return int(x), int(y)

    def mean(self) -> tuple:
        pm = self.position()
        return float((pm * self.xs).sum()), float((pm * self.ys).sum())

    def mass_within(self, pos, radius: int = 1) -> float:
        return float(self.position()[self.cheb_grid(pos) <= radius].sum())

    def best_neighbourhood(self, radius: int = 1):
        """Cell maximising mass within a Chebyshev radius (box filter)."""
        pm = self.position()
        k = 2 * radius + 1
        padded = np.pad(pm, radius)
        c = np.cumsum(np.cumsum(padded, 0), 1)
        c = np.pad(c, ((1, 0), (1, 0)))
        box = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
        y, x = np.unravel_index(int(np.argmax(box)), box.shape)
        return (int(x), int(y)), float(box[y, x])

    def credible_region(self, mass: float = 0.9) -> int:
        """Number of cells in the smallest region holding ``mass`` probability."""
        p = np.sort(self.position().ravel())[::-1]
        return int(np.searchsorted(np.cumsum(p), mass) + 1)

    def summary(self) -> dict:
        x, y = self.map_cell()
        pm = self.position()
        st = self.status()
        return {
            "map_cell": [x, y],
            "map_prob": round(float(pm[y, x]), 4),
            "p_within_1": round(self.mass_within((x, y), 1), 4),
            "entropy": round(self.entropy(), 3),
            "cred90_cells": self.credible_region(0.9),
            "status": {k: round(v, 3) for k, v in st.items()},
        }

    # --------------------------------------------- expected information gain
    def expected_info_gain(self, pos, rng: np.random.Generator, samples: int = 16) -> float:
        """Monte-Carlo estimate of the entropy reduction from scanning at ``pos``."""
        flat = self.P.ravel()
        idx = rng.choice(flat.size, size=samples, p=flat / flat.sum())
        s_idx, ys, xs = np.unravel_index(idx, self.P.shape)
        D, B = self.dist_grid(pos), self.bearing_grid(pos)
        H0 = self.entropy()
        hs = []
        for s, y, x in zip(s_idx, ys, xs):
            d = math.hypot(x - pos[0], y - pos[1])
            b = math.degrees(math.atan2(x - pos[0], -(y - pos[1]))) % 360.0
            r = self.sm.sample(d, b, STATUSES[s], rng)
            post = self.P * self.sm.likelihood(r, D, B)
            z = post.sum()
            if z <= 0:
                continue
            post = post[post > 0] / z
            hs.append(float(-(post * np.log(post)).sum()))
        return max(0.0, H0 - float(np.mean(hs))) if hs else 0.0
