"""Phase 6 / STEP 3c - is the VALVE-179 safe bound valid under JOINT action?

STEP 3b established that the VALVE-179 cliff is not a property of VALVE-179 in
isolation. The four service nodes that go to negative pressure are the four
highest-elevation nodes in the network (JUNCTION-102 at 1094.1 ft, -103 at
1031.7 ft, -121 and -122 at 957.0 ft), and JUNCTION-121 / JUNCTION-122 are
exactly the upstream and downstream nodes of VALVE-178. The failure is an
elevation-driven loss of available head in the upper pressure zone that
VALVE-179 and VALVE-178 share: widening VALVE-179 diverts flow into the zone,
the head at JUNCTION-123 collapses from 120.9 psi to 44.8 psi, VALVE-179 ceases
to regulate, and the high nodes can no longer be lifted.

That has a direct consequence for the action space. A per-valve safe bound
measured with all other valves held at nominal is only sound if it survives the
other valves moving too. A DRL agent emits all PRV settings simultaneously, so
this module tests the bound under joint perturbation instead of assuming
separability.

Design (fixed before execution):
  1. A 2-D grid over (VALVE-179, VALVE-178), the two valves that share the
     failing zone, spanning the STEP 3b boundary on the 179 axis and the
     plausible operating range on the 178 axis.
  2. A joint test in which all five PRVs that Phase 5 found responsive
     (173, 175, 176, 177, 178) sit at the low end of their range while
     VALVE-179 sits at its per-valve safe bound - the worst case for available
     head in the upper zone.

The question answered is binary and stated before the runs: does any combination
in which VALVE-179 is at or below its per-valve safe bound (44.7 psi) still
produce negative service pressure? If yes, a per-valve box constraint is not a
sufficient safety layer and the safety design must account for coupling.

No optimisation. No search for a best setting. Characterisation only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import phase5_common as C  # noqa: E402
import g6_g7_g8_leak_pda as L  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402

# Per-valve boundary measured in STEP 3b.
V179_LAST_CLEAN_PSI = 44.7   # highest setting with no service metric departure
V179_LAST_NONNEG_PSI = 44.8  # highest setting with no negative pressure
V179_FIRST_NEG_PSI = 44.9    # lowest setting producing negative pressure

# 2-D grid. The 178 axis spans 0.75x to 1.25x of its 37 psi nominal; the 179
# axis spans the safe region, the boundary, and one clearly unsafe point.
GRID_179 = [40.0, 44.0, 44.7, 44.8, 45.0]
GRID_178 = [27.75, 32.0, 37.0, 42.0, 46.25]

# Worst-case-for-head joint test: every responsive PRV at the low end while
# VALVE-179 sits at its per-valve safe bound.
RESPONSIVE = ["VALVE-173", "VALVE-175", "VALVE-176", "VALVE-177", "VALVE-178"]
JOINT_SCALES = [0.75, 0.90, 1.00]


def build_multi(settings_psi: dict[str, float]):
    """Same solver/PDA configuration as STEP 3, several PRVs overridden."""
    wn = S3.build(None, None)
    for v, s in settings_psi.items():
        wn.get_link(v).initial_setting = C.psi_to_m(s)
    return wn


def run_multi(label: str, prefix: str, settings_psi: dict[str, float],
              coeff_us, svc, conn) -> dict:
    wn = build_multi(settings_psi)
    L.apply_leak(wn, coeff_us)
    solver = S3.assert_solver(wn)
    echo = L.echo_check(wn, prefix)
    res, msgs, used = L._run_with_retry(wn, prefix)
    row = {
        "label": label,
        "settings_psi": settings_psi,
        "solver": solver,
        "echo_check": echo,
        "wntr_warnings": msgs,
        "report_scan": L._rpt_errors(used),
        "leak_applied": True,
    }
    row.update(S3.measure(wn, res, coeff_us, svc, conn, None))
    # Which service nodes ever go negative, so a failure is localisable.
    p = C.m_to_psi(res.node["pressure"][svc])
    row["service_nodes_ever_negative"] = {
        j: {"min_psi": float(p[j].min()),
            "n_timesteps_negative": int((p[j] < 0.0).sum()),
            "elevation_ft": float(C.m_to_ft(wn.get_node(j).elevation))}
        for j in svc if bool((p[j] < 0.0).any())}
    return row


def main() -> dict:
    C.build_working_copy(verbose=False)
    wn0 = S3.build(None, None)
    svc, conn = S3.service_nodes(wn0)
    assert len(svc) == 121 and len(conn) == 5

    base_p, base_inflow, weights = L.baseline_pressures("p6s3c_size")
    sizing = L.leak_coefficients(weights, base_p,
                                 L.LEAK_TARGET_FRACTION * base_inflow)
    coeff_us = sizing["coefficient_gpm_per_psi_alpha"]

    cases: dict[str, dict] = {}

    # --- 1. the 2-D (179, 178) grid ---------------------------------------
    for s179 in GRID_179:
        for s178 in GRID_178:
            key = f"179@{s179:g}_178@{s178:g}"
            cases[key] = run_multi(
                f"VALVE-179 {s179:g} psi with VALVE-178 {s178:g} psi "
                f"({s178 / S3.NOMINAL_PSI['VALVE-178']:.2f} x nominal), "
                "other PRVs nominal",
                f"p6s3c_g_{s179:g}_{s178:g}".replace(".", "p"),
                {"VALVE-179": s179, "VALVE-178": s178},
                coeff_us, svc, conn)

    # --- 2. worst-case-for-head joint perturbation ------------------------
    for sc in JOINT_SCALES:
        settings = {v: S3.NOMINAL_PSI[v] * sc for v in RESPONSIVE}
        settings["VALVE-179"] = V179_LAST_CLEAN_PSI
        key = f"joint_responsive_x{sc:g}_179@{V179_LAST_CLEAN_PSI:g}"
        cases[key] = run_multi(
            f"all five responsive PRVs at {sc:g} x nominal while VALVE-179 "
            f"sits at its per-valve safe bound {V179_LAST_CLEAN_PSI:g} psi",
            f"p6s3c_j_{sc:g}".replace(".", "p"),
            settings, coeff_us, svc, conn)

    # --- verdict on separability, computed from the runs -------------------
    at_or_below = {k: v for k, v in cases.items()
                   if v["settings_psi"].get("VALVE-179", 0.0)
                   <= V179_LAST_CLEAN_PSI}
    violators = {k: v["service_nodes_ever_negative"]
                 for k, v in at_or_below.items()
                 if v["n_node_timesteps_negative"] > 0}

    payload = {
        "phase": 6,
        "step": "3c",
        "title": ("Is the per-valve VALVE-179 safe bound valid under joint PRV "
                  "action?"),
        "env": C.env_info(),
        "scope_statement": (
            "Characterisation only. Grids fixed before execution. No "
            "optimisation, no search, no reward, no RL. Native controls, rules "
            "and topology untouched in every run."),
        "solver_policy": {"accuracy": S3.SOLVER_ACCURACY,
                          "trials": S3.SOLVER_TRIALS,
                          "rule_timestep_s": S3.RULE_TIMESTEP_S,
                          "report_timestep_s": S3.REPORT_TIMESTEP_S},
        "question": (
            "Does any tested combination in which VALVE-179 is at or below its "
            "per-valve safe bound of "
            f"{V179_LAST_CLEAN_PSI} psi still produce negative service "
            "pressure? If yes, a per-valve box constraint is not by itself a "
            "sufficient safety layer."),
        "per_valve_boundary_from_step3b_psi": {
            "last_clean": V179_LAST_CLEAN_PSI,
            "last_non_negative": V179_LAST_NONNEG_PSI,
            "first_negative": V179_FIRST_NEG_PSI,
        },
        "grid_179_psi": GRID_179,
        "grid_178_psi": GRID_178,
        "joint_responsive_valves": RESPONSIVE,
        "joint_scales": JOINT_SCALES,
        "n_cases_with_179_at_or_below_bound": len(at_or_below),
        "cases_violating_bound": violators,
        "box_constraint_sufficient_on_tested_set": len(violators) == 0,
        "cases": cases,
    }
    out = C.REPO / "results" / "phase6"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "p6_s3c_zone_interaction.json"
    path.write_text(json.dumps(payload, indent=2, default=str),
                    encoding="utf-8")
    print(f"[written] {path}")
    return payload


if __name__ == "__main__":
    main()
