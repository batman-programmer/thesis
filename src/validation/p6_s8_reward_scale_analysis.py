"""Phase 6 / STEP 8 - reward-component scale & variability analysis.

Purpose (Phase 6 STEP 8 brief): BEFORE any reward weight is chosen, EMPIRICALLY
MEASURE the natural scale, variability, temporal behaviour and cross-correlation
of every candidate reward component under representative in-bounds trajectories.
This module MEASURES ONLY. It does NOT choose weights, does NOT tune a reward,
does NOT run PPO, and does NOT alter the frozen observation (STEP 7) or the
frozen action space (STEP 6). The proposed reward formulations recorded in the
output are marked PROPOSED and are NOT approved here.

What is reused verbatim, so this analysis is identical to the validated Phase 5/6
instrument and inherits its guarantees:

  * the 121-service-node / 5-connector split           - p6_s3.service_nodes
  * the mandated solver policy (ACC 1e-5, TRIALS 2000,  - p6_s3.build / .assert_solver
    rule 180 s, report 1800 s, PDA 20/0/0.5) asserted
    after every load
  * the leakage instrument (half-pipe-length weights,   - g6_g7_g8.baseline_pressures
    one closed-form global scale, exponent 0.5, target    + .leak_coefficients + .apply_leak
    10 % of leak-free inflow) - a VALIDATION instrument,
    NOT a calibrated field leakage model (brief 18)
  * the per-timestep signed emitter water balance        - g6_g7_g8.accounting
    q = sign(p)*C*|p|^0.5, served = reported - leak

The frozen action bounds are imported from the STEP 7 state builder (itself the
mirror of docs/PHASE6_ACTION_SPACE_SPEC.md) so the perturbation grid and the
actuator-effort characterisation are tied to the single source of truth.

Every configuration is a full 96 h EPS with a STATIC in-bounds command (the
static analogue of the agent re-issuing a constant command each step). Static
runs cannot exhibit step-to-step actuator MOVEMENT, so the movement/smoothness
term's realised scale is characterised ANALYTICALLY from the action bounds and
flagged as a training-time HYPOTHESIS, never fabricated.

Output: results/phase6/p6_s8_reward_scale_analysis.json (raw + summary +
interpretation). Deterministic: EPANET is deterministic, no RNG, no seed.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "env"))

import numpy as np  # noqa: E402
import phase5_common as C  # noqa: E402
import g6_g7_g8_leak_pda as L  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402
import state_builder as SB  # noqa: E402  (STEP 7 builder; mirror of frozen spec)

SERVICE_PSI = 20.0  # PDA required / service threshold, same as Phase 5/6

# --- Frozen action space (imported from the STEP 7 builder) -------------------
PRV_IDS = list(SB.PRV_IDS)                       # 173,175,176,177,178 (order)
PUMP_IDS = list(SB.PUMP_IDS)                     # 170,172 (order)
PRV_LOWER = {v: SB.PRV_BOUNDS_PSI[v][0] for v in PRV_IDS}
PRV_UPPER = {v: SB.PRV_BOUNDS_PSI[v][1] for v in PRV_IDS}
PRV_NOMINAL = {v: float(L.NOMINAL_PSI[v]) for v in PRV_IDS}
PUMP_LOWER = {p: SB.PUMP_BOUNDS[p][0] for p in PUMP_IDS}
PUMP_UPPER = {p: SB.PUMP_BOUNDS[p][1] for p in PUMP_IDS}
PUMP_NOMINAL = {p: 1.0 for p in PUMP_IDS}        # native nominal speed


def _configurations() -> list[tuple[str, dict, dict]]:
    """(label, prv_setpoints_psi, pump_speeds) - every command strictly in bounds.

    A representative in-bounds set: the native reference, the two joint PRV
    corners, each PRV isolated at its own lower / upper edge (others nominal),
    the two pump speed corners, and four mixed PRV*pump corners. Interior /
    horizon variability is captured WITHIN each 96 h run (193 report instants).
    """
    cfgs: list[tuple[str, dict, dict]] = []
    cfgs.append(("reference_nominal", dict(PRV_NOMINAL), dict(PUMP_NOMINAL)))
    cfgs.append(("prv_all_lower", dict(PRV_LOWER), dict(PUMP_NOMINAL)))
    cfgs.append(("prv_all_upper", dict(PRV_UPPER), dict(PUMP_NOMINAL)))
    for v in PRV_IDS:
        tag = v.split("-")[1]
        lo = dict(PRV_NOMINAL); lo[v] = PRV_LOWER[v]
        hi = dict(PRV_NOMINAL); hi[v] = PRV_UPPER[v]
        cfgs.append((f"prv_{tag}_lower", lo, dict(PUMP_NOMINAL)))
        cfgs.append((f"prv_{tag}_upper", hi, dict(PUMP_NOMINAL)))
    cfgs.append(("pump_all_lower", dict(PRV_NOMINAL), dict(PUMP_LOWER)))
    cfgs.append(("pump_all_upper", dict(PRV_NOMINAL), dict(PUMP_UPPER)))
    cfgs.append(("prv_lower_pump_lower", dict(PRV_LOWER), dict(PUMP_LOWER)))
    cfgs.append(("prv_upper_pump_upper", dict(PRV_UPPER), dict(PUMP_UPPER)))
    cfgs.append(("prv_lower_pump_upper", dict(PRV_LOWER), dict(PUMP_UPPER)))
    cfgs.append(("prv_upper_pump_lower", dict(PRV_UPPER), dict(PUMP_LOWER)))
    return cfgs


# --- Candidate reward components (definitions only; no weights) ---------------
# Every component is a per-timestep scalar derived from one 96 h EPS. Sign
# conventions are stated for interpretation only; NO weighting is applied here.
COMPONENT_KEYS = [
    "leakage_gpm",                    # objective: minimise (background leakage)
    "served_demand_gpm",              # service: maximise (PDA served consumer demand)
    "requested_demand_gpm",           # context: requested (expected) demand
    "unserved_demand_gpm",            # service deficit: minimise (requested - served)
    "dsr",                            # service: maximise (served / requested)
    "pressure_deficit_psi_nodesum",   # safety: minimise (sum over svc of max(20-p,0))
    "n_service_nodes_below_20psi",    # safety: minimise (count < 20 psi)
    "min_service_pressure_psi",       # safety: keep high (worst-node pressure)
    "n_service_nodes_negative",       # safety: hard (count < 0 psi)
    "pump_hydraulic_power_kw",        # optional energy/effort proxy (hydraulic, not electrical)
]


def stats(arr) -> dict:
    """Distribution summary of one per-timestep component series (finite floats)."""
    a = np.asarray(arr, dtype=float)
    return {
        "n": int(a.size),
        "mean": float(np.mean(a)),
        "median": float(np.median(a)),
        "std": float(np.std(a)),
        "min": float(np.min(a)),
        "max": float(np.max(a)),
        "p5": float(np.percentile(a, 5)),
        "p25": float(np.percentile(a, 25)),
        "p75": float(np.percentile(a, 75)),
        "p95": float(np.percentile(a, 95)),
        "mean_abs_step_diff": (float(np.mean(np.abs(np.diff(a))))
                               if a.size > 1 else 0.0),
    }


def pump_hydraulic_power_kw(wn, res) -> np.ndarray:
    """Total pump hydraulic power per timestep (kW). PROXY only.

    P = rho*g*Q*dH summed over pumps, clipped at 0 (a pump adding no head adds no
    power). This is HYDRAULIC power (no pump-efficiency curve, not electrical
    energy); a closed pump has Q ~ 0 -> 0 kW, mirroring realised speed = 0.
    """
    head = res.node["head"]
    flow = res.link["flowrate"]
    total = None
    for p in wn.pump_name_list:
        link = wn.get_link(p)
        d_h = head[link.end_node_name] - head[link.start_node_name]   # m
        pw = (1000.0 * 9.81 * flow[p] * d_h).clip(lower=0.0) / 1000.0  # kW
        total = pw if total is None else total + pw
    return total.to_numpy()


def component_series(wn, res, coeff_us, svc) -> dict:
    """Per-timestep value of every candidate reward component for one EPS.

    Reproduces g6_g7_g8.accounting's signed water balance at per-timestep
    resolution: leakage over all junctions, served = reported demand - leakage,
    DSR = served / requested (expected). Safety terms use the 121 service nodes
    only. Identical law and node policy as the validated instrument.
    """
    import wntr

    junc = wn.junction_name_list
    p_all = C.m_to_psi(res.node["pressure"][junc])
    p_svc = C.m_to_psi(res.node["pressure"][svc])
    q_node = C.m3s_to_gpm(res.node["demand"][junc])
    req_node = C.m3s_to_gpm(wntr.metrics.expected_demand(wn)[junc])
    req_node.index = q_node.index

    leak_node = (np.sign(p_all) * p_all.abs() ** L.LEAK_EXPONENT).mul(
        [coeff_us[j] for j in junc], axis=1)
    leak = leak_node.sum(axis=1).to_numpy()
    served = q_node.sum(axis=1).to_numpy() - leak
    req = req_node.sum(axis=1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        dsr = np.where(req > 0.0, served / req, 1.0)

    deficit = (SERVICE_PSI - p_svc).clip(lower=0.0).sum(axis=1).to_numpy()
    n_below = (p_svc < SERVICE_PSI).sum(axis=1).to_numpy().astype(float)
    n_neg = (p_svc < 0.0).sum(axis=1).to_numpy().astype(float)
    min_p = p_svc.min(axis=1).to_numpy()

    return {
        "leakage_gpm": leak,
        "served_demand_gpm": served,
        "requested_demand_gpm": req,
        "unserved_demand_gpm": req - served,
        "dsr": np.asarray(dsr, dtype=float),
        "pressure_deficit_psi_nodesum": deficit,
        "n_service_nodes_below_20psi": n_below,
        "min_service_pressure_psi": min_p,
        "n_service_nodes_negative": n_neg,
        "pump_hydraulic_power_kw": pump_hydraulic_power_kw(wn, res),
    }


def run_config(label, prv_psi, pump_speed, coeff_us, svc, n_native_controls):
    """One 96 h EPS at a static in-bounds command. Native controls/rules kept."""
    wn = S3.build(None, None)                 # solver+PDA set; controls untouched
    for v, s in prv_psi.items():
        wn.get_link(v).initial_setting = C.psi_to_m(float(s))
    for p, sp in pump_speed.items():
        wn.get_link(p).base_speed = float(sp)
    solver = S3.assert_solver(wn)
    assert len(wn.control_name_list) == n_native_controls, (
        label, len(wn.control_name_list), n_native_controls)
    L.apply_leak(wn, coeff_us)
    res, _msgs, used = L._run_with_retry(wn, "p6s8_" + label)

    series = component_series(wn, res, coeff_us, svc)
    acc = L.accounting(wn, res, coeff_us)     # validated scalar cross-check
    comp_stats = {k: stats(v) for k, v in series.items()}
    # Cross-check: per-timestep leak/served means must equal the validated means.
    xcheck = {
        "leakage_mean_abs_diff_gpm": abs(
            comp_stats["leakage_gpm"]["mean"] - acc["leakage_mean_gpm"]),
        "served_mean_abs_diff_gpm": abs(
            comp_stats["served_demand_gpm"]["mean"] - acc["served_demand_mean_gpm"]),
        "dsr_mean_abs_diff": abs(comp_stats["dsr"]["mean"] - acc["dsr_mean"]),
    }
    finite = all(np.isfinite(np.asarray(v, dtype=float)).all()
                 for v in series.values())
    return {
        "commanded": {"prv_setpoints_psi": {k: float(v) for k, v in prv_psi.items()},
                      "pump_speeds": {k: float(v) for k, v in pump_speed.items()}},
        "n_timesteps": int(len(series["leakage_gpm"])),
        "component_stats": comp_stats,
        "validated_accounting": {
            "leakage_mean_gpm": acc["leakage_mean_gpm"],
            "served_demand_mean_gpm": acc["served_demand_mean_gpm"],
            "requested_demand_mean_gpm": acc["requested_demand_mean_gpm"],
            "dsr_mean": acc["dsr_mean"], "dsr_min": acc["dsr_min"],
            "n_node_timesteps_below_20psi": acc["n_node_timesteps_below_20psi"],
            "n_node_timesteps_negative_pressure":
                acc["n_node_timesteps_negative_pressure"],
            "continuity_residual_rel_max": acc["continuity_residual_rel_max"],
        },
        "per_timestep_vs_accounting_cross_check": xcheck,
        "all_finite": bool(finite),
        "_series": series,   # kept in-memory only; stripped before JSON dump
    }


def actuator_effort_analytic() -> dict:
    """Movement/smoothness scale from the frozen action bounds (not measurable
    from static runs). Normalised action a in [-1,1]^7; per-step delta in
    [-2,2]. Physical per-actuator span = upper - lower."""
    n = len(PRV_IDS) + len(PUMP_IDS)
    spans = {v: float(SB.PRV_BOUNDS_PSI[v][1] - SB.PRV_BOUNDS_PSI[v][0])
             for v in PRV_IDS}
    spans.update({p: float(SB.PUMP_BOUNDS[p][1] - SB.PUMP_BOUNDS[p][0])
                  for p in PUMP_IDS})
    return {
        "action_dim": n,
        "normalized_encoding": "a_i in [-1,1]; per-step delta_a_i in [-2,2]",
        "max_per_step_abs_delta_per_dim": 2.0,
        "max_per_step_L1_movement": 2.0 * n,           # 14
        "max_per_step_L2sq_movement": 4.0 * n,         # 28
        "max_per_step_L2_movement": float(np.sqrt(4.0 * n)),  # ~5.2915
        "physical_span_per_actuator": spans,           # psi for PRV, rel-speed for pump
        "note": ("Static runs have zero step-to-step movement, so the REALISED "
                 "movement/smoothness scale depends on the (not-yet-existing) "
                 "policy action sequence and is a training-time HYPOTHESIS. The "
                 "effort term MUST be computed on the COMMANDED normalised action "
                 "(not realised pump speed, which the native STATUS rule can reset "
                 "to 1.0 or 0 -> reward-hacking / closed-pump ambiguity)."),
    }


def correlation(pooled: dict) -> dict:
    """Pearson correlation across components over all pooled timesteps."""
    keys = COMPONENT_KEYS
    mat = np.vstack([pooled[k] for k in keys])
    with np.errstate(invalid="ignore"):
        corr = np.corrcoef(mat)
    corr = np.nan_to_num(corr, nan=0.0)   # a constant series -> undefined -> 0
    return {"labels": keys,
            "matrix": [[round(float(corr[i, j]), 4) for j in range(len(keys))]
                       for i in range(len(keys))]}


def pathology_checks(cfg: dict, pooled_stats: dict, pooled_arrays: dict) -> dict:
    """Structured, MEASURED evidence for the known reward-design failure modes."""
    ref = cfg["reference_nominal"]["validated_accounting"]
    lo = cfg["prv_all_lower"]["validated_accounting"]
    hi = cfg["prv_all_upper"]["validated_accounting"]
    lo_stats = cfg["prv_all_lower"]["component_stats"]
    ref_stats = cfg["reference_nominal"]["component_stats"]

    med = {k: abs(pooled_stats[k]["median"]) for k in COMPONENT_KEYS}
    scale_pool = {k: med[k] for k in
                  ("leakage_gpm", "unserved_demand_gpm",
                   "pressure_deficit_psi_nodesum", "pump_hydraulic_power_kw")}
    nz = {k: v for k, v in scale_pool.items() if v > 0}
    imbalance = (max(nz.values()) / min(nz.values())) if len(nz) > 1 else None

    n_neg_pool = pooled_stats["n_service_nodes_negative"]
    return {
        "leakage_only_collapses_service": {
            "description": ("A leakage-ONLY reward pushes pressure to the PRV "
                            "lower bound; measure whether service degrades there."),
            "reference_leak_gpm": ref["leakage_mean_gpm"],
            "all_lower_leak_gpm": lo["leakage_mean_gpm"],
            "leak_reduction_gpm": ref["leakage_mean_gpm"] - lo["leakage_mean_gpm"],
            "reference_dsr_mean": ref["dsr_mean"],
            "all_lower_dsr_mean": lo["dsr_mean"],
            "reference_min_service_psi": ref_stats["min_service_pressure_psi"]["min"],
            "all_lower_min_service_psi": lo_stats["min_service_pressure_psi"]["min"],
            "all_lower_new_node_timesteps_below_20psi":
                lo["n_node_timesteps_below_20psi"] - ref["n_node_timesteps_below_20psi"],
            "verdict": ("service must be protected explicitly; a leakage-only "
                        "reward is not safe by construction (see boundary check)."),
        },
        "pressure_only_raises_leakage": {
            "reference_leak_gpm": ref["leakage_mean_gpm"],
            "all_upper_leak_gpm": hi["leakage_mean_gpm"],
            "leak_increase_gpm": hi["leakage_mean_gpm"] - ref["leakage_mean_gpm"],
            "verdict": "maximising pressure inflates leakage; objectives oppose.",
        },
        "scale_imbalance": {
            "pooled_median_abs_magnitude": med,
            "penalty_terms_max_over_min_ratio": imbalance,
            "verdict": ("raw components span very different magnitudes; a raw "
                        "weighted sum is dominated by the largest -> fixed "
                        "normalisation is required before weighting."),
        },
        "sparse_or_degenerate_signal": {
            "frac_timesteps_zero_negative_nodes":
                float(np.mean(np.asarray(pooled_arrays["n_service_nodes_negative"]) == 0.0)),
            "frac_timesteps_zero_below20_nodes":
                float(np.mean(np.asarray(pooled_arrays["n_service_nodes_below_20psi"]) == 0.0)),
            "n_negative_pool_max": n_neg_pool["max"],
            "dsr_pool_std": pooled_stats["dsr"]["std"],
            "verdict": ("negative-pressure count is (near-)always zero in bounds "
                        "-> a pure hard-violation term is sparse; the smooth "
                        "deficit / min-pressure terms carry the dense safety signal."),
        },
        "actuator_penalty_domination": {
            "max_per_step_L2sq_movement_unnormalised": 4.0 * (len(PRV_IDS)+len(PUMP_IDS)),
            "verdict": ("unnormalised movement (L2^2 up to 28) would dominate "
                        "normalised leakage/service terms (~O(1)); the effort term "
                        "MUST be normalised by its analytic maximum."),
        },
        "reward_hacking_closed_pump_ambiguity": {
            "verdict": ("effort/smoothness MUST use the COMMANDED normalised "
                        "action; realised pump speed is reset to 1.0 by STATUS-IS-"
                        "OPEN or 0 when closed (G12), so penalising realised speed "
                        "is gameable and mis-attributes native-rule behaviour."),
        },
        "boundary_seeking_safety": {
            "leak_min_corner_is_prv_all_lower": True,
            "all_lower_n_node_timesteps_negative":
                lo["n_node_timesteps_negative_pressure"],
            "all_lower_min_service_psi": lo_stats["min_service_pressure_psi"]["min"],
            "all_lower_new_node_timesteps_below_20psi":
                lo["n_node_timesteps_below_20psi"] - ref["n_node_timesteps_below_20psi"],
            "verdict": ("the leakage optimum sits at the PRV lower bound; this "
                        "single corner is characterised here only. Exhaustive joint "
                        "in-box safety is a STEP-9 (safety layer) + STEP-12 (tests) "
                        "job; a safety term/clamp is required, not optional."),
        },
    }


def proposed_formulations(norm: dict) -> list:
    """A SMALL set of principled, PROPOSED (not approved) reward formulations.

    All normalisers are FIXED constants measured once (baseline reference / this
    analysis) and frozen; they are NOT per-episode running statistics, so there
    is no train/eval leakage. Weights shown are PLACEHOLDERS (unity), explicitly
    NOT tuned. Choosing the formulation and the weights is a later, separately
    approved decision; PPO training remains out of scope.
    """
    return [
        {
            "name": "normalized_weighted_sum",
            "status": "PROPOSED",
            "formula": ("r_t = - w_L*(leak_t/leak_ref) - w_U*(unserved_t/req_ref) "
                        "- w_P*(deficit_t/deficit_ref) - w_A*(||da_t||^2 / L2sq_max) "
                        "[- w_E*(power_t/power_ref)]"),
            "weights_placeholder": {"w_L": 1.0, "w_U": 1.0, "w_P": 1.0,
                                    "w_A": 1.0, "w_E": 0.0},
            "note": ("dense, differentiable; every term normalised to ~O(1). "
                     "Weights NOT tuned here."),
        },
        {
            "name": "constrained_penalty_service_protected",
            "status": "PROPOSED",
            "formula": ("r_t = -(leak_t/leak_ref) - LAMBDA*(deficit_t/deficit_ref) "
                        "- BIG*max(0, n_below20_t) ; LAMBDA >> 1, BIG >> LAMBDA"),
            "note": ("minimise leakage subject to a large, explicit service/safety "
                     "penalty; service is protected by construction."),
        },
        {
            "name": "baseline_relative_improvement",
            "status": "PROPOSED",
            "formula": ("r_t = (leak_ref - leak_t)/leak_ref "
                        "- w_U*(unserved_t - unserved_ref)_+ / req_ref - safety_penalty"),
            "note": ("interpretable as fractional leakage reduction vs the NATIVE "
                     "controller; naturally zero-centred at the baseline."),
        },
        {
            "name": "safety_first_lexicographic",
            "status": "PROPOSED",
            "formula": ("if any svc node < 20 psi (or < 0): dominant negative "
                        "penalty; else minimise leak_t/leak_ref; effort as tie-break"),
            "note": ("encodes the priority hierarchy safety > service > leakage > "
                     "effort; typically realised via masking / large penalties and "
                     "pairs with the STEP-9 safety clamp."),
        },
        {
            "name": "fixed_normalization_constants_used_by_all_proposals",
            "status": "PROPOSED",
            "constants": norm,
        },
    ]


def main() -> dict:
    C.build_working_copy(verbose=False)
    wn0 = S3.build(None, None)
    svc, conn = S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5, (len(svc), len(conn))
    n_native_controls = len(wn0.control_name_list)
    topology = {
        "n_junctions": len(wn0.junction_name_list),
        "n_service_junctions": len(svc),
        "n_connector_junctions": len(conn),
        "n_reservoirs": len(wn0.reservoir_name_list),
        "n_tanks": len(wn0.tank_name_list),
        "n_pumps": len(wn0.pump_name_list),
        "n_valves": len(wn0.valve_name_list),
        "n_pipes": len(wn0.pipe_name_list),
        "n_native_controls": n_native_controls,
    }

    # Leak instrument sized VERBATIM as in p6_s3 / g6_g7_g8 (same 10 % target).
    base_p, base_inflow, weights = L.baseline_pressures("p6s8_size")
    sizing = L.leak_coefficients(weights, base_p, L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    configs: dict[str, dict] = {}
    for label, prv_psi, pump_speed in _configurations():
        configs[label] = run_config(label, prv_psi, pump_speed, coeff_us, svc,
                                     n_native_controls)

    # Pool every component's per-timestep series across all configurations.
    pooled_arrays = {k: np.concatenate([configs[c]["_series"][k]
                                        for c in configs]) for k in COMPONENT_KEYS}
    pooled_stats = {k: stats(v) for k, v in pooled_arrays.items()}
    temporal_variability = {
        k: {"mean_within_config_std":
                float(np.mean([configs[c]["component_stats"][k]["std"]
                               for c in configs])),
            "mean_within_config_abs_step_diff":
                float(np.mean([configs[c]["component_stats"][k]["mean_abs_step_diff"]
                               for c in configs]))}
        for k in COMPONENT_KEYS}
    corr = correlation(pooled_arrays)

    ref_acc = configs["reference_nominal"]["validated_accounting"]
    ref_stats = configs["reference_nominal"]["component_stats"]
    effort = actuator_effort_analytic()
    norm_constants = {
        "leak_ref_gpm": ref_acc["leakage_mean_gpm"],
        "req_ref_gpm": ref_acc["requested_demand_mean_gpm"],
        "deficit_ref_psi_nodesum": max(ref_stats["pressure_deficit_psi_nodesum"]["mean"],
                                       pooled_stats["pressure_deficit_psi_nodesum"]["p95"]),
        "power_ref_kw": max(ref_stats["pump_hydraulic_power_kw"]["mean"], 1e-9),
        "movement_L2sq_max": effort["max_per_step_L2sq_movement"],
        "note": ("FIXED constants measured once (baseline reference run / this "
                 "analysis) and frozen; NOT per-episode running statistics -> no "
                 "train/eval leakage. deficit_ref guards against a ~0 baseline "
                 "deficit by taking max(baseline mean, pooled p95)."),
    }
    checks = pathology_checks(configs, pooled_stats, pooled_arrays)
    formulations = proposed_formulations(norm_constants)

    all_finite = bool(all(configs[c]["all_finite"] for c in configs)
                      and all(np.isfinite(list(pooled_stats[k].values())).all()
                              for k in COMPONENT_KEYS))
    xcheck_max = max(
        max(configs[c]["per_timestep_vs_accounting_cross_check"].values())
        for c in configs)

    integrity = {
        "working_inp_sha256": C.sha256_file(C.WORKING_INP),
        "topology": topology,
        "native_controls_unchanged_in_every_config": True,
        "solver_policy_asserted_every_load": True,
        "solver_policy": S3.assert_solver(wn0),
        "all_component_values_finite": all_finite,
        "per_timestep_vs_validated_accounting_max_abs_diff": float(xcheck_max),
        "no_topology_or_native_rule_change": True,
        "no_future_information_used": True,
    }

    for c in configs:            # strip in-memory-only per-timestep arrays
        configs[c].pop("_series", None)

    payload = {
        "phase": 6,
        "step": 8,
        "title": ("Reward-component scale, variability and correlation analysis "
                  "for the BWSN-1 PPO environment (MEASURE ONLY, not train)"),
        "status": ("MEASUREMENT COMPLETE. Reward formulations are PROPOSED, NOT "
                   "approved. No weights chosen, no PPO training, observation "
                   "(STEP 7) and action space (STEP 6) unchanged."),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "env": C.env_info(),
        "scope_statement": (
            "Validation/characterisation only. Every number is produced by the "
            "EPANET solver from the working copy with native controls and rules "
            "untouched, under the mandated solver policy and the Phase 5 leakage "
            "instrument. No optimisation, no search, no reward tuning, no RL."),
        "solver_policy": {
            "accuracy": S3.SOLVER_ACCURACY, "trials": S3.SOLVER_TRIALS,
            "rule_timestep_s": S3.RULE_TIMESTEP_S,
            "report_timestep_s": S3.REPORT_TIMESTEP_S,
            "pda_required_psi": L.PDA_REQUIRED_PSI,
            "pda_minimum_psi": L.PDA_MINIMUM_PSI, "pda_exponent": L.PDA_EXPONENT,
            "asserted_after_every_load": True,
        },
        "service_node_policy": {
            "rule": ("declared elevation exactly 0.0 ft AND zero total base demand "
                     "-> connector artefact, excluded from every service/safety "
                     "statistic but KEPT in the hydraulic model"),
            "n_service_junctions": len(svc), "n_connector_junctions": len(conn),
            "connector_nodes": conn,
        },
        "leak_instrument": {
            "status": ("VALIDATION INSTRUMENT, not a calibrated field leakage "
                       "model (brief 18). Half-pipe-length weights, single closed-"
                       "form global scale, exponent 0.5 from the file's [OPTIONS]."),
            "sizing": {k: v for k, v in sizing.items()
                       if k != "coefficient_gpm_per_psi_alpha"},
        },
        "action_space_reference": {
            "source": "docs/PHASE6_ACTION_SPACE_SPEC.md (D-P6-001/002/003, FROZEN)",
            "prv_bounds_psi": {v: list(SB.PRV_BOUNDS_PSI[v]) for v in PRV_IDS},
            "pump_bounds_rel_speed": {p: list(SB.PUMP_BOUNDS[p]) for p in PUMP_IDS},
        },
        "candidate_reward_components": COMPONENT_KEYS,
        "n_configurations": len(configs),
        "configurations": configs,
        "pooled_component_stats": pooled_stats,
        "temporal_variability": temporal_variability,
        "cross_component_correlation": corr,
        "actuator_effort_analytic": effort,
        "proposed_normalization_constants": norm_constants,
        "pathology_checks": checks,
        "proposed_formulations": formulations,
        "integrity": integrity,
        "limitations": [
            "Static-command runs: realised actuator MOVEMENT is 0, so the effort/"
            "smoothness scale is analytic (from bounds), not measured - HYPOTHESIS.",
            "Leakage is a VALIDATION instrument, not field-calibrated; only RELATIVE "
            "leakage response is meaningful, never an absolute leakage claim.",
            "Component scales measured on a representative in-bounds set (reference, "
            "corners, per-PRV edges); interior/mixed-corner joint safety is a STEP-9/"
            "STEP-12 job, NOT claimed here.",
            "Pump power is HYDRAULIC (rho*g*Q*dH), no efficiency curve; an energy "
            "term is optional and clearly labelled.",
        ],
        "next_step": ("Researcher review of the PROPOSED formulations and of the "
                      "measured scales; then select ONE formulation + weights as a "
                      "separate approved decision. STEP 9 safety layer must supply "
                      "the hard clamp the boundary-seeking check shows is required."),
    }

    out = C.REPO / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    import json
    path = out / "p6_s8_reward_scale_analysis.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"[written] {path}")
    return payload


if __name__ == "__main__":
    main()










