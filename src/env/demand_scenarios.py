"""STEP-10 demand-scenario module (D-P6-007, researcher-selected 2026-10-19).

Implements the APPROVED demand-uncertainty selection recorded in
``docs/PHASE6_DECISION_REGISTER.md`` (D-P6-007):

  temporal structure U1  : one demand multiplier per 96 h episode, constant;
  distribution     M1    : truncated normal, mu=1.0, sigma=0.1, bounds [0.7, 1.3]
                           (the only range with project-record precedent,
                           Hu et al. 2023 -- a design precedent, NOT a
                           field-calibrated BWSN-1 demand distribution);
  spatial (train + in-distribution eval) S1 : ONE global multiplier shared by
                           every demand-bearing junction;
  spatial (OOD eval)      S2 : independent per-junction multipliers, same
                           truncated-normal marginal;
  training                : a reproducible RNG stream that DRAWS A NEW scenario
                           at every episode reset (NOT a fixed set of eight);
  evaluation              : fixed, reproducible, disjoint scenario IDs
                           (val/0..3, test/0..3, ood/0..1) + the native anchor.

MECHANICS (verified against the frozen working INP)
---------------------------------------------------
The working model is GPM/psi; WNTR loads demands into SI ``TimeSeries`` objects
whose ``base_value`` carries the junction's base demand. Multiplying every
positive ``base_value`` by a factor f scales that junction's demand by exactly f
at EVERY report instant (verified: uniform 1.5 scaling of all junctions gives
``expected_demand`` ratio exactly 1.5 at t=0, 1800, 86400, 172800 ... i.e. across
the full 96 h horizon and across segment boundaries). Patterns, pattern phase,
pattern timestep, emitters, PDA options and solver settings are NEVER touched,
so the native 48 h demand-pattern phase and all frozen hydraulics are preserved.
The leak instrument (``epanet_adapter.default_leak_coefficients``) is a
deterministic property of the NATIVE network and is deliberately NOT re-scaled:
a scenario changes leakage only through the physics (pressures), never through
the instrument.

The same ``scenario.apply(wn)`` call must reach BOTH hydraulic paths
(``SteppingHydraulicDriver`` does this -- segment models AND the full-horizon
model used for requested-demand accounting); this module only defines the
transformation.

RNG DESIGN
----------
All randomness flows through ``numpy.random.default_rng`` seeded from
``SeedSequence(entropy=master_seed, spawn_key=...)`` with INTEGER group keys,
so the training stream (key 0) and the fixed evaluation groups (keys 1..3) are
logically separate streams that cannot collide: a fixed scenario is reproducible
from (identifier, ScenarioConfig) alone, and a training draw is reproducible
from (master seed, draw index). Truncated-normal sampling is EXACT
inverse-CDF via ``statistics.NormalDist`` (stdlib; no new dependency), not
clipping of an ordinary normal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import NormalDist

import numpy as np

# --- frozen STEP-10 selection (D-P6-007, researcher directive 2026-10-19) -----
MASTER_SEED = 20261019
MU = 1.0
SIGMA = 0.1
LOWER = 0.7
UPPER = 1.3

# Fixed evaluation-set sizes (researcher selection).
N_VALIDATION = 4
N_TEST = 4
N_OOD = 2

# Integer spawn keys: SeedSequence spawn_key must be a tuple of ints; distinct
# keys give logically independent streams (no train/eval leakage by construction).
_TRAIN_KEY = 0
_VALIDATION_KEY = 1
_TEST_KEY = 2
_OOD_KEY = 3

_GROUP_KEYS = {"val": _VALIDATION_KEY, "test": _TEST_KEY, "ood": _OOD_KEY}
_GROUP_COUNTS = {"val": N_VALIDATION, "test": N_TEST, "ood": N_OOD}


@dataclass(frozen=True)
class ScenarioConfig:
    """Master seed + the frozen M1 truncated-normal parameters."""
    master_seed: int = MASTER_SEED
    mu: float = MU
    sigma: float = SIGMA
    lower: float = LOWER
    upper: float = UPPER

    def distribution_dict(self) -> dict:
        return {"family": "truncated_normal", "mu": self.mu, "sigma": self.sigma,
                "lower": self.lower, "upper": self.upper}


DEFAULT_CONFIG = ScenarioConfig()


# --------------------------------------------------------------------------- #
# exact truncated-normal sampling (inverse CDF, NOT clipping)                  #
# --------------------------------------------------------------------------- #
def truncnorm_ppf(u: float, config: ScenarioConfig = DEFAULT_CONFIG) -> float:
    """Inverse CDF of N(mu, sigma) truncated to [lower, upper], at probability u.

    u is interpreted on the truncated support's own probability scale
    (u in [0, 1]). Exact closed form via ``statistics.NormalDist`` (stdlib);
    clipping an ordinary normal is a different distribution and is NOT used.
    """
    nd = NormalDist(config.mu, config.sigma)
    p_lo = nd.cdf(config.lower)
    p_hi = nd.cdf(config.upper)
    p = p_lo + u * (p_hi - p_lo)
    # Guard the open endpoints so inv_cdf never sees exactly 0/1.
    p = min(max(p, p_lo), p_hi)
    p = min(max(p, np.nextafter(0.0, 1.0)), np.nextafter(1.0, 0.0))
    return nd.inv_cdf(p)


def sample_truncnorm(rng: np.random.Generator,
                     config: ScenarioConfig = DEFAULT_CONFIG) -> float:
    """Draw one exact truncated-normal sample from a numpy Generator."""
    return truncnorm_ppf(float(rng.random()), config)


def demand_junctions(wn) -> list[str]:
    """Sorted junctions carrying positive base demand in ``wn``.

    Derived from the model's own declarations (same auditability rule as
    ``p6_s3_prv_finechar.service_nodes``), NOT hard-coded: junctions with zero
    base demand contribute no demand and are left untouched by every scenario.
    On the frozen working INP this yields 79 junctions (PATTERN-0: 77,
    PATTERN-1: 5, three junctions carry both categories).
    """
    out = []
    for j in wn.junction_name_list:
        nd = wn.get_node(j)
        if any(ts.base_value > 0.0 for ts in nd.demand_timeseries_list):
            out.append(j)
    return sorted(out)


# --------------------------------------------------------------------------- #
# scenarios                                                                     #
# --------------------------------------------------------------------------- #
class DemandScenario:
    """Base: an episode-level demand perturbation with full provenance."""

    scenario_id: str = "native"
    family: str = "none"          # "none" | "U1"
    spatial: str = "none"         # "none" | "S1" | "S2"
    perturbed: bool = False

    def apply(self, wn) -> None:
        """Mutate ``wn``'s base demands in place (identity for native)."""

    def to_dict(self) -> dict:
        raise NotImplementedError


def _scale_demand_entries(wn, factor_for) -> None:
    """Multiply every positive demand ``base_value`` by its junction's factor.

    Applies to ALL demand categories of a demand-bearing junction (a junction
    with both PATTERN-0 and PATTERN-1 categories has both scaled), never to
    zero-demand junctions, emitter coefficients, patterns, or timing options.
    """
    for j in wn.junction_name_list:
        nd = wn.get_node(j)
        f = factor_for(j)
        if f == 1.0:
            continue
        for ts in nd.demand_timeseries_list:
            if ts.base_value > 0.0:
                ts.base_value = ts.base_value * f


class NativeScenario(DemandScenario):
    """The unperturbed native demand pattern (frozen anchor path)."""

    scenario_id = "native"
    family = "none"
    spatial = "none"
    perturbed = False

    def __init__(self, config: ScenarioConfig = DEFAULT_CONFIG):
        self.config = ScenarioConfig(config.master_seed, config.mu, config.sigma,
                                     config.lower, config.upper)

    def apply(self, wn) -> None:
        """Identity: the native path stays byte-identical (no call needed)."""

    def to_dict(self) -> dict:
        return {"scenario_id": "native", "family": "none", "spatial": "none",
                "perturbed": False, "distribution": self.config.distribution_dict()}


class GlobalFactorScenario(DemandScenario):
    """U1 + S1: one multiplier for ALL demand-bearing junctions, held 96 h."""

    family = "U1"
    spatial = "S1"
    perturbed = True

    def __init__(self, multiplier: float, scenario_id: str,
                 config: ScenarioConfig = DEFAULT_CONFIG,
                 draw_index: int | None = None):
        self.multiplier = float(multiplier)
        self.scenario_id = str(scenario_id)
        self.config = ScenarioConfig(config.master_seed, config.mu, config.sigma,
                                     config.lower, config.upper)
        self.draw_index = draw_index

    def apply(self, wn) -> None:
        _scale_demand_entries(wn, lambda _j: self.multiplier)

    def to_dict(self) -> dict:
        d = {"scenario_id": self.scenario_id, "family": self.family,
             "spatial": self.spatial, "perturbed": True,
             "multiplier": self.multiplier,
             "master_seed": self.config.master_seed,
             "distribution": self.config.distribution_dict()}
        if self.draw_index is not None:
            d["draw_index"] = self.draw_index
        return d


class JunctionFactorScenario(DemandScenario):
    """U1 + S2: one constant factor PER JUNCTION, held 96 h (OOD family)."""

    family = "U1"
    spatial = "S2"
    perturbed = True

    def __init__(self, factors: dict[str, float], scenario_id: str,
                 config: ScenarioConfig = DEFAULT_CONFIG):
        self.factors = {str(k): float(v) for k, v in factors.items()}
        self.scenario_id = str(scenario_id)
        self.config = ScenarioConfig(config.master_seed, config.mu, config.sigma,
                                     config.lower, config.upper)

    def apply(self, wn) -> None:
        _scale_demand_entries(wn, lambda j: self.factors.get(j, 1.0))

    def to_dict(self) -> dict:
        vals = np.asarray(list(self.factors.values()), dtype=float)
        return {"scenario_id": self.scenario_id, "family": self.family,
                "spatial": self.spatial, "perturbed": True,
                "n_junctions": int(len(self.factors)),
                "factor_mean": float(vals.mean()) if len(vals) else None,
                "factor_std": float(vals.std()) if len(vals) else None,
                "factors": dict(self.factors),
                "master_seed": self.config.master_seed,
                "distribution": self.config.distribution_dict()}


# --------------------------------------------------------------------------- #
# fixed evaluation scenarios (reproducible from identifier + config)           #
# --------------------------------------------------------------------------- #
def validation_scenario_ids() -> list[str]:
    return [f"val/{i}" for i in range(N_VALIDATION)]


def test_scenario_ids() -> list[str]:
    return [f"test/{i}" for i in range(N_TEST)]


def ood_scenario_ids() -> list[str]:
    return [f"ood/{i}" for i in range(N_OOD)]


def all_fixed_scenario_ids() -> list[str]:
    return (["native"] + validation_scenario_ids() + test_scenario_ids()
            + ood_scenario_ids())


def fixed_scenario(scenario_id: str,
                   config: ScenarioConfig = DEFAULT_CONFIG,
                   demand_junctions_list: list[str] | None = None
                   ) -> DemandScenario:
    """Rebuild a fixed evaluation scenario from its identifier + config.

    ``scenario_id`` is "native" or "<group>/<index>" with group in
    {val, test, ood}. Derivation is deterministic: the scenario's own
    ``SeedSequence(entropy=master_seed, spawn_key=(group_key, index))``. S2
    (OOD) needs the demand-junction list of the frozen working INP (sorted,
    from :func:`demand_junctions`; a frozen property of the network, so
    reproduction needs only the identifier, the config, and the INP).
    """
    if scenario_id in ("native", "native_nominal"):
        return NativeScenario(config)
    if isinstance(scenario_id, DemandScenario):
        return scenario_id
    try:
        group, idx_s = scenario_id.split("/")
        idx = int(idx_s)
    except (ValueError, AttributeError):
        raise ValueError(
            f"unknown scenario id {scenario_id!r}: use 'native', 'train' "
            f"(stream) or '<group>/<index>' with group in {{val, test, ood}}")
    if group not in _GROUP_KEYS:
        raise ValueError(f"unknown scenario group {group!r} in {scenario_id!r}")
    if not (0 <= idx < _GROUP_COUNTS[group]):
        raise ValueError(f"scenario index {idx} out of range for group {group!r}")
    rng = np.random.default_rng(
        np.random.SeedSequence(entropy=config.master_seed,
                               spawn_key=(_GROUP_KEYS[group], idx)))
    if group == "ood":
        if demand_junctions_list is None:
            raise ValueError("S2 (ood) scenarios require demand_junctions_list")
        factors = {j: sample_truncnorm(rng, config)
                   for j in sorted(demand_junctions_list)}
        return JunctionFactorScenario(factors, scenario_id, config)
    m = sample_truncnorm(rng, config)
    return GlobalFactorScenario(m, scenario_id, config)


# Alias used by the env/evaluation harness.
scenario_from_id = fixed_scenario


def _train_rng(master_seed: int) -> np.random.Generator:
    return np.random.default_rng(
        np.random.SeedSequence(entropy=int(master_seed), spawn_key=(_TRAIN_KEY,)))


class TrainingScenarioStream:
    """Reproducible per-episode scenario draws for PPO training.

    Each ``next()`` draws a NEW U1+S1 multiplier from the stream's dedicated
    RNG (spawn key 0, disjoint from every fixed evaluation group). The n-th
    draw is reproducible from (master seed, n). ``reseed`` implements the
    gym ``reset(seed=...)`` contract: a reseed restarts the draw counter, so
    seeding with the same value reproduces the same scenario sequence.
    """

    def __init__(self, config: ScenarioConfig = DEFAULT_CONFIG):
        self.config = ScenarioConfig(config.master_seed, config.mu, config.sigma,
                                     config.lower, config.upper)
        self._rng = _train_rng(self.config.master_seed)
        self._draw = 0

    def reseed(self, seed: int) -> None:
        """Restart the stream from an explicit seed (gym reset contract)."""
        self._rng = _train_rng(int(seed))
        self._draw = 0

    @property
    def draw_index(self) -> int:
        return self._draw

    def next(self) -> GlobalFactorScenario:
        m = sample_truncnorm(self._rng, self.config)
        sc = GlobalFactorScenario(m, f"train/{self._draw}", self.config,
                                  draw_index=self._draw)
        self._draw += 1
        return sc
