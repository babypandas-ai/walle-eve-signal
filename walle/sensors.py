"""Sensor models shared by the simulator (to *generate* readings) and the agent
(to *explain* readings). The agent is given a calibrated model of its own
sensors, but never the ground truth that drives them.

Conventions
-----------
* Grid coordinates are ``(x, y)`` with ``x`` growing east and ``y`` growing south.
* Bearings are compass degrees: 0 = North, 90 = East, 180 = South, 270 = West.
* Signal strength is a dB-like number in roughly [0, 100].
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

STATUSES = ("active", "low_power", "damaged")


def bearing_deg(frm, to) -> float:
    """Compass bearing from cell ``frm`` to cell ``to``."""
    dx = to[0] - frm[0]
    dy = to[1] - frm[1]
    return math.degrees(math.atan2(dx, -dy)) % 360.0


def ang_diff(a, b):
    """Signed smallest angular difference a-b in degrees (works on arrays)."""
    return (np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0


def _erf(x):
    """Vectorised erf (Abramowitz & Stegun 7.1.26, |err| < 1.5e-7)."""
    x = np.asarray(x, dtype=float)
    s = np.sign(x)
    a = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t
               + 0.254829592) * t * np.exp(-a * a)
    return s * y


def norm_cdf(x):
    return 0.5 * (1.0 + _erf(np.asarray(x) / math.sqrt(2.0)))


def norm_pdf(x, sigma):
    return np.exp(-0.5 * (np.asarray(x) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))


@dataclass
class SignalModel:
    """EVE's homing beacon as seen by WALL-E's receiver.

    Expected strength decays logarithmically with distance:
        mu(d) = power[status] - path_loss * log2(1 + d)
    A reading is ``mu + N(0, sigma[status])``; if it falls below the noise floor,
    or the beacon drops out (more likely when EVE is low on power or damaged),
    the receiver reports *no signal* -- which is itself evidence.
    """

    power: dict = field(default_factory=lambda: {"active": 80.0, "low_power": 64.0, "damaged": 74.0})
    sigma: dict = field(default_factory=lambda: {"active": 3.0, "low_power": 4.0, "damaged": 9.0})
    dropout: dict = field(default_factory=lambda: {"active": 0.03, "low_power": 0.20, "damaged": 0.35})
    bearing_sigma: dict = field(default_factory=lambda: {"active": 10.0, "low_power": 14.0, "damaged": 24.0})
    path_loss: float = 15.0
    noise_floor: float = 8.0
    bearing_outlier: float = 0.05  # chance a bearing is pure multipath garbage
    max_strength: float = 100.0
    # handshake/authentication quality of a detected packet (genuine vs spoofed)
    auth_genuine: tuple = (0.72, 0.15)
    auth_spoof: tuple = (0.40, 0.15)

    @classmethod
    def from_dict(cls, d: dict | None) -> "SignalModel":
        m = cls()
        for k, v in (d or {}).items():
            if not hasattr(m, k):
                raise ValueError(f"unknown signal model parameter: {k}")
            cur = getattr(m, k)
            if isinstance(cur, dict):
                cur = dict(cur)
                cur.update(v)
                v = cur
            setattr(m, k, v)
        return m

    def _vec(self, name):
        d = getattr(self, name)
        return np.array([d[s] for s in STATUSES], dtype=float).reshape(-1, 1, 1)

    # ------------------------------------------------------------------ simulate
    def mean_strength(self, d, status: str):
        return self.power[status] - self.path_loss * np.log2(1.0 + np.asarray(d, dtype=float))

    def sample(self, d: float, true_bearing: float, status: str, rng: np.random.Generator,
               power_override: float | None = None, force_detect: bool = False, spoof: bool = False) -> dict:
        power = self.power[status] if power_override is None else power_override
        mu = power - self.path_loss * math.log2(1.0 + d)
        s = mu + rng.normal(0.0, self.sigma[status])
        dropped = rng.random() < self.dropout[status]
        if not force_detect and (dropped or s < self.noise_floor):
            return {"detected": False, "strength": None, "bearing_deg": None}
        s = float(min(max(s, self.noise_floor), self.max_strength))
        if rng.random() < self.bearing_outlier:
            b = rng.uniform(0, 360)
        else:
            b = true_bearing + rng.normal(0.0, self.bearing_sigma[status])
        mu_a, sd_a = self.auth_spoof if spoof else self.auth_genuine
        auth = float(np.clip(rng.normal(mu_a, sd_a), 0.0, 1.0))
        return {"detected": True, "strength": round(s, 2), "bearing_deg": round(float(b) % 360.0, 1),
                "auth": round(auth, 2)}

    def auth_likelihood(self, reading: dict, spoof: bool) -> float:
        if reading.get("auth") is None:
            return 1.0
        mu, sd = self.auth_spoof if spoof else self.auth_genuine
        return float(norm_pdf(reading["auth"] - mu, sd))

    # ---------------------------------------------------------------- likelihood
    def likelihood(self, reading: dict, D: np.ndarray, B: np.ndarray, inflate: float = 0.0) -> np.ndarray:
        """P(reading | EVE at each cell, status) -> array shaped (S, H, W).

        ``D``/``B`` are distance / bearing grids from the scan position.
        ``inflate`` widens the noise for stale readings (seconds of age).
        """
        mu = self._vec("power") - self.path_loss * np.log2(1.0 + D)[None]
        sig = self._vec("sigma") + 0.15 * inflate
        pd = self._vec("dropout")
        if not reading.get("detected"):
            return pd + (1 - pd) * norm_cdf((self.noise_floor - mu) / sig)
        ls = norm_pdf(reading["strength"] - mu, sig)
        bsig = self._vec("bearing_sigma") + 0.5 * inflate
        db = ang_diff(reading["bearing_deg"], B)[None]
        lb = (1 - self.bearing_outlier) * norm_pdf(db, bsig) + self.bearing_outlier / 360.0
        return (1 - pd) * ls * lb

    def background_likelihood(self) -> float:
        """Density of a spoofed/decoy reading: uniform strength x uniform bearing."""
        return 1.0 / (self.max_strength - self.noise_floor) / 360.0


# ---------------------------------------------------------------------- clues
CLUE_TYPES = {
    # type: (description template, status likelihood ratios)
    "hover_tracks": ("Fresh hover-scorch tracks pointing ~{bearing_deg:.0f} deg",
                     {"active": 1.6, "low_power": 0.9, "damaged": 0.6}),
    "debris": ("EVE armour fragment; scatter pattern says source within {within} cells",
               {"active": 0.5, "low_power": 0.8, "damaged": 2.5}),
    "power_cell": ("Discarded EVE power cell; drag marks lead within {within} cells",
                   {"active": 0.6, "low_power": 2.5, "damaged": 1.0}),
    "beacon_log": ("Corrupted beacon log fragment: EVE {axis} in [{min}, {max}]",
                   {"active": 1.0, "low_power": 1.0, "damaged": 1.0}),
    "plant": ("A seedling in an old boot! EVE must be within {within} cells",
              {"active": 1.3, "low_power": 1.0, "damaged": 0.9}),
}

CLUE_BEARING_SIGMA = 18.0  # agent's model of how far tracks can mislead
