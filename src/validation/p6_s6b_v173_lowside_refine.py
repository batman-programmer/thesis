"""Phase 6 / STEP 6b - focused LOW-SIDE refinement of VALVE-173 only.

WHY THIS EXISTS (scope, deliberately narrow). The STEP 6 sweep
(p6_s6_active_prv_bounds.py -> p6_s6_active_prv_bounds.json) used the coarse grid
[40,50,60,70,80,90,100] for VALVE-173 and found the valve fully CLOSED (0 gpm,
frac_closed = 1.0) at every setpoint 5-50 psi and first ACTIVE at 60 psi. Because
the coarse grid jumps 50 -> 60 psi, the repository contains NO measurement in the
open interval (50, 60): the closed -> active transition is only bracketed to 10 psi.
A proposed DRL lower bound of ~55 psi for VALVE-173 is therefore NOT yet supported
by on-disk evidence. This script resolves that single 10-psi bracket and NOTHING
else. It is NOT a re-run of STEP 6 (the other four PRVs, the high side, the joint
corner and the negative-pressure cliffs are untouched).

WHAT IT MEASURES. VALVE-173 setpoint on an integer grid 50..60 psi, refined to
0.25 psi around the activation crossings, with the other four RL PRVs and both
pumps left at their distributed (nominal) values - identical solver policy, PDA
configuration and leakage validation instrument as STEP 6. For each setpoint it
records the actuator state fractions (closed/active/open), the mean valve flow,
and the service-safety references (min service pressure, n<20 psi, n negative).

WHAT IT DERIVES (the three quantities the researcher asked for, item 2):
  * last setpoint at which VALVE-173 is definitely CLOSED (never regulating);
  * first setpoint at which VALVE-173 is definitely ACTIVE (regulating a majority
    of the 96 h EPS);
  * the practical regulating interval's LOWER edge for this valve.
It does NOT freeze any bound and does NOT mark D-P6-003 APPROVED. Output is a NEW
file (results/phase6/p6_s6b_v173_lowside_refine.json); the STEP 6 JSON is never
overwritten (CLAUDE.md s.12 - experimental evidence is preserved).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import phase5_common as C            # noqa: E402
import g6_g7_g8_leak_pda as L        # noqa: E402
import p6_s3_prv_finechar as S3      # noqa: E402

VALVE = "VALVE-173"
NOMINAL_PSI = S3.NOMINAL_PSI[VALVE]           # 70.0 (Phase-5 distributed setpoint)
LOW_PSI, HIGH_PSI = 50.0, 60.0                # the single unmeasured coarse bracket
ACTIVE_FLOOR = 0.05                           # frac_time_active below this == inactive
MAJORITY = 0.5                                # frac_time_active at/above this == regulating
REFINE_PSI = 0.25                             # resolution to which each crossing is refined
MAX_RUNS = 60                                 # hard cap (never approached; ~15 expected)

def _prefix(s: float) -> str:
    return f"p6s6b_173_{('%g' % s).replace('.', 'p')}"


def _compact(row: dict) -> dict:
    """One transparent per-setpoint record: actuator state + safety references."""
    sv = row.get("swept_valve") or {}
    return {
        "setting_psi": row["setting_psi"],
        "frac_time_closed": sv.get("frac_time_closed"),
        "frac_time_active": sv.get("frac_time_active"),
        "frac_time_open": sv.get("frac_time_open"),
        "ever_active": sv.get("ever_active"),
        "valve_flow_mean_gpm": sv.get("flow_mean_gpm"),
        "max_abs_realisation_error_when_active_psi": sv.get(
            "max_abs_realisation_error_when_active_psi"),
        "mean_service_pressure_psi": row["mean_service_pressure_psi"],
        "min_service_pressure_psi": row["min_service_pressure_psi"],
        "argmin_service_node": row["argmin_service_node"],
        "n_node_timesteps_below_20psi": row["n_node_timesteps_below_20psi"],
        "n_node_timesteps_negative": row["n_node_timesteps_negative"],
        "leakage_mean_gpm": row["leakage_mean_gpm"],
        "continuity_residual_rel_max": row["continuity_residual_rel_max"],
    }


def main() -> dict:
    C.build_working_copy(verbose=False)
    wn0 = S3.build(None, None)
    svc, conn = S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5, (len(svc), len(conn))

    # Leakage instrument recomputed by the identical Phase-5 closed form (same
    # target = 10% of leak-free mean inflow). Validation instrument only.
    base_p, base_inflow, weights = L.baseline_pressures("p6s6b_size")
    sizing = L.leak_coefficients(weights, base_p,
                                 L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    # Reference reproduction (all PRVs at nominal). The STEP 6 / Phase-5 reference
    # is 386 node-timesteps <20 psi, 0 negative, leak 84.730 gpm, mean 94.787 psi.
    ref = S3.run_case("reference: all PRVs at nominal, leakage on, PDA",
                      "p6s6b_ref", None, None, coeff_us, svc, conn)
    ref_below20 = int(ref["n_node_timesteps_below_20psi"])
    ref_neg = int(ref["n_node_timesteps_negative"])
    assert ref_neg == 0, ref_neg
    reference_reproduced = (ref_below20 == 386 and ref_neg == 0)

    rows: dict[float, dict] = {}
    truncated = False

    def ensure(s: float):
        nonlocal truncated
        key = round(float(s), 3)
        if key in rows:
            return rows[key]
        if len(rows) >= MAX_RUNS:
            truncated = True
            return None
        label = (f"{VALVE} setting {key:g} psi, other four RL PRVs and both "
                 "pumps at nominal")
        rows[key] = S3.run_case(label, _prefix(key), VALVE, key,
                                coeff_us, svc, conn)
        return rows[key]

    # Integer grid across the single unmeasured coarse bracket, inclusive of the
    # two coarse anchors 50 and 60 (re-measured here for continuity of evidence).
    for s in range(int(LOW_PSI), int(HIGH_PSI) + 1):
        ensure(float(s))

    def fa(s: float) -> float:
        sv = rows[round(float(s), 3)].get("swept_valve") or {}
        return float(sv.get("frac_time_active") or 0.0)

    # Refine each activation crossing to REFINE_PSI. Two crossings are resolved:
    # (i) inactive -> any activation (frac_active crosses ACTIVE_FLOOR), and
    # (ii) minority -> majority regulation (frac_active crosses MAJORITY).
    def refine(threshold: float):
        while len(rows) < MAX_RUNS:
            settings = sorted(rows)
            flag = {s: fa(s) >= threshold for s in settings}
            bracket = next(((a, b) for a, b in zip(settings, settings[1:])
                            if flag[a] != flag[b] and (b - a) > REFINE_PSI + 1e-9),
                           None)
            if bracket is None:
                break
            added = False
            x = round(bracket[0] + REFINE_PSI, 3)
            while x < bracket[1] - 1e-9:
                if x not in rows and ensure(x) is not None:
                    added = True
                x = round(x + REFINE_PSI, 3)
            if not added:
                break

    refine(ACTIVE_FLOOR)
    refine(MAJORITY)

    settings = sorted(rows)
    fully_closed = [s for s in settings if fa(s) <= 1e-9]
    any_active = [s for s in settings if fa(s) >= ACTIVE_FLOOR]
    majority_active = [s for s in settings if fa(s) >= MAJORITY]

    last_closed = max(fully_closed) if fully_closed else None
    first_any = min(any_active) if any_active else None
    first_majority = min(majority_active) if majority_active else None

    derived = {
        "last_setpoint_fully_closed_psi": last_closed,
        "first_setpoint_any_activation_psi": first_any,
        "first_setpoint_majority_active_psi": first_majority,
        "activation_bracket_psi": (
            [last_closed, first_any] if last_closed is not None
            and first_any is not None else None),
        "activation_bracket_width_psi": (
            None if last_closed is None or first_any is None
            else round(first_any - last_closed, 3)),
        "practical_regulating_lower_edge_psi": first_majority,
        "note": (
            "Practical regulating LOWER edge = first setpoint at which VALVE-173 "
            "is Active for a majority of the 96 h EPS. Below the fully-closed "
            "setpoint the valve passes no flow (0 gpm) and is not a control "
            "actuator. The regulating UPPER edge and the Active->Open saturation "
            "(observed at 100->110 psi) are already in p6_s6_active_prv_bounds.json "
            "and are NOT re-measured here. Leakage is flat while the valve is "
            "closed (the leak instrument responds to network pressure, which this "
            "nearly-inert valve barely moves) - a measured weak-actuator caveat, "
            "not used to alter any bound."),
    }

    payload = {
        "phase": 6,
        "step": "6b",
        "title": ("Focused low-side refinement of VALVE-173 closed->active "
                  "transition in the (50,60] psi coarse-grid gap"),
        "env": C.env_info(),
        "decision_ref": "D-P6-003",
        "decision_status": "PROPOSED - PENDING RESEARCHER APPROVAL (unchanged by this refinement)",
        "supersedes": None,
        "does_not_overwrite": "results/phase6/p6_s6_active_prv_bounds.json",
        "scope_statement": (
            "Single-bracket refinement only. Resolves the closed->active "
            "transition of VALVE-173 between 50 and 60 psi, which the STEP 6 "
            "coarse grid left unmeasured. No optimisation, no RL, no reward. Other "
            "PRVs and pumps held at nominal. STEP 6 evidence is preserved."),
        "solver_policy": {
            "accuracy": S3.SOLVER_ACCURACY, "trials": S3.SOLVER_TRIALS,
            "rule_timestep_s": S3.RULE_TIMESTEP_S,
            "report_timestep_s": S3.REPORT_TIMESTEP_S,
            "demand_model": "PDA",
            "required_pressure_psi": S3.PDA_REQUIRED_PSI,
            "minimum_pressure_psi": S3.PDA_MINIMUM_PSI,
            "pressure_exponent": S3.PDA_EXPONENT,
            "asserted_after_every_load": True,
        },
        "valve": VALVE,
        "nominal_setpoint_psi": NOMINAL_PSI,
        "activity_definitions": {
            "fully_closed": "frac_time_active == 0 (valve never regulates; 0 gpm)",
            "any_activation": f"frac_time_active >= {ACTIVE_FLOOR}",
            "majority_active": f"frac_time_active >= {MAJORITY}",
            "rationale": ("EPANET valve status per timestep: 0 Closed, 1 Open, "
                          "2 Active. A PRV is only a control actuator while Active; "
                          "the fractions are measured over all 96 h report steps."),
        },
        "reference_nominal_case": {
            "n_node_timesteps_below_20psi": ref_below20,
            "n_node_timesteps_negative": ref_neg,
            "mean_service_pressure_psi": ref["mean_service_pressure_psi"],
            "min_service_pressure_psi": ref["min_service_pressure_psi"],
            "argmin_service_node": ref["argmin_service_node"],
            "leakage_mean_gpm": ref["leakage_mean_gpm"],
            "reproduced_step6_reference": reference_reproduced,
        },
        "n_setpoints_evaluated": len(settings),
        "grid_truncated_at_cap": truncated,
        "derived": derived,
        "sweep": [_compact(rows[s]) for s in settings],
        "cases": {f"{VALVE}@{s:g}psi": rows[s] for s in settings},
    }

    out = (HERE.parent.parent / "results" / "phase6"
           / "p6_s6b_v173_lowside_refine.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"reference_reproduced={reference_reproduced} "
          f"ref_below20={ref_below20} ref_neg={ref_neg} "
          f"ref_leak={float(ref['leakage_mean_gpm']):.3f}")
    print(f"n_setpoints={len(settings)} truncated={truncated}")
    print(f"last_fully_closed={last_closed} first_any_active={first_any} "
          f"first_majority_active={first_majority}")
    for s in settings:
        c = _compact(rows[s])
        print(f"  {s:6.2f} psi  active={c['frac_time_active']:.3f} "
              f"closed={c['frac_time_closed']:.3f} open={c['frac_time_open']:.3f} "
              f"flow={c['valve_flow_mean_gpm']:.3f} gpm  minP={c['min_service_pressure_psi']:.3f} "
              f"n<20={c['n_node_timesteps_below_20psi']} neg={c['n_node_timesteps_negative']} "
              f"leak={c['leakage_mean_gpm']:.3f}")
    print(f"wrote {out}")
    return payload


if __name__ == "__main__":
    main()
