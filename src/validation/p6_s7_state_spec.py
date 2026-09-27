"""STEP 7 evidence generator: build the real observation config from the live
working INP, verify it against the frozen module constants, build one genuine
observation vector from a deterministic reference EPS, and record everything to
results/phase6/p6_s7_state_spec.json.

Reuses the EXACT service-node rule and mandated solver policy from
p6_s3_prv_finechar (no silent methodology change, brief §21). STATE ONLY — no
reward, no PPO, no demand model.

Run:  .venv/Scripts/python.exe src/validation/p6_s7_state_spec.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import phase5_common as C  # noqa: E402
import p6_s3_prv_finechar as S3  # noqa: E402
from env.state_builder import (  # noqa: E402
    PRV_BOUNDS_PSI, PUMP_BOUNDS, ObservationConfig, RawState,
    build_observation, observation_bounds,
)

SAMPLE_TIME_S = 43200.0  # 12:00 of day 1 — a mid-day, high-demand snapshot


def _tank_level_ft(res, wn, tank, t):
    head_m = float(res.node["head"].loc[t, tank])
    el_m = float(wn.get_node(tank).elevation)
    return float(C.m_to_ft(head_m - el_m))


def main() -> dict:
    wn = S3.build(None, None)  # working copy + mandated solver policy
    solver = S3.assert_solver(wn)
    svc, conn = S3.service_nodes(wn)
    tank_bounds = {
        t: (float(C.m_to_ft(wn.get_node(t).min_level)),
            float(C.m_to_ft(wn.get_node(t).max_level)))
        for t in wn.tank_name_list
    }

    cfg = ObservationConfig(
        service_nodes=tuple(svc), connector_nodes=tuple(conn),
        tank_ids=tuple(wn.tank_name_list), tank_level_bounds_ft=tank_bounds,
    )

    # --- drift guard: module constants must match the frozen spec / live INP ---
    consistency = {
        "n_service_is_121": len(svc) == 121,
        "connectors_match": conn == ["JUNCTION-105", "JUNCTION-106",
                                     "JUNCTION-109", "JUNCTION-110",
                                     "JUNCTION-128"],
        "prv_bounds_match_spec": PRV_BOUNDS_PSI == {
            "VALVE-173": (54.5, 100.0), "VALVE-175": (21.5, 110.0),
            "VALVE-176": (20.0, 59.524), "VALVE-177": (20.0, 90.0),
            "VALVE-178": (20.0, 74.0)},
        "pump_bounds_match_spec": PUMP_BOUNDS == {
            "PUMP-170": (0.82, 1.10), "PUMP-172": (0.77, 1.10)},
        "dim_is_139": cfg.dim == 139,
        "controlled_prvs_in_model": all(v in wn.valve_name_list
                                        for v in cfg.prv_ids),
        "excluded_prvs_still_in_model": all(
            v in wn.valve_name_list
            for v in ("VALVE-174", "VALVE-179", "VALVE-180")),
        "pumps_in_model": all(u in wn.pump_name_list for u in cfg.pump_ids),
    }
    assert all(consistency.values()), consistency

    # --- one genuine observation from a deterministic reference EPS -----------
    res, warns = C.run_epanet(wn, "p6s7_sample")
    P = res.node["pressure"]
    status = res.link["status"]
    setting = res.link["setting"]
    t = SAMPLE_TIME_S

    pressures = {n: float(C.m_to_psi(P.loc[t, n])) for n in wn.junction_name_list}
    tanks = {tk: _tank_level_ft(res, wn, tk, t) for tk in wn.tank_name_list}
    # PRV: current setting (psi) + Active flag (EPANET LinkStatus Active == 2)
    prv_status_codes = {v: float(status.loc[t, v]) for v in cfg.prv_ids}
    prv_setpoint = {v: float(C.m_to_psi(setting.loc[t, v])) for v in cfg.prv_ids}
    prv_active = {v: (prv_status_codes[v] == 2.0) for v in cfg.prv_ids}
    # Pump: current speed setting; realized = speed if running (status Open==1)
    pump_status_codes = {u: float(status.loc[t, u]) for u in cfg.pump_ids}
    pump_cmd = {u: float(setting.loc[t, u]) for u in cfg.pump_ids}
    pump_realized = {u: (float(setting.loc[t, u]) if pump_status_codes[u] >= 1.0
                         else 0.0) for u in cfg.pump_ids}

    raw = RawState(
        pressures_psi=pressures, tank_levels_ft=tanks,
        prev_cmd_prv_setpoint_psi=prv_setpoint, prv_is_active=prv_active,
        prev_cmd_pump_speed=pump_cmd, pump_realized_speed=pump_realized,
        sim_time_s=t,
    )
    obs = build_observation(cfg, raw)
    low, high = observation_bounds(cfg)

    checks = {
        "shape_139": obs.shape == (139,),
        "dtype_float32": str(obs.dtype) == "float32",
        "all_finite": bool(np.all(np.isfinite(obs))),
        "within_bounds": bool(np.all(obs >= low - 1e-6)
                              and np.all(obs <= high + 1e-6)),
        "connectors_absent_from_features": all(
            c not in cfg.service_nodes for c in cfg.connector_nodes),
    }
    assert all(checks.values()), checks
    return _assemble(cfg, solver, raw, obs, prv_status_codes, pump_status_codes,
                     consistency, checks, warns)


def _assemble(cfg, solver, raw, obs, prv_status_codes, pump_status_codes,
              consistency, checks, warns) -> dict:
    sl = cfg.slices()
    layout = {name: [s.start, s.stop] for name, s in sl.items()}
    payload = {
        "step": "STEP 7 - DRL observation / state design (evidence)",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "env": C.env_info(),
        "solver_policy_asserted": solver,
        "working_inp_sha256": C.sha256_file(C.WORKING_INP),
        "observation_dim": int(cfg.dim),
        "dtype": "float32",
        "block_layout_index_ranges": layout,
        "service_node_count": len(cfg.service_nodes),
        "service_nodes_sorted": list(cfg.service_nodes),
        "connector_nodes_excluded": list(cfg.connector_nodes),
        "tank_ids": list(cfg.tank_ids),
        "tank_level_bounds_ft": {k: list(v)
                                 for k, v in cfg.tank_level_bounds_ft.items()},
        "prv_ids": list(cfg.prv_ids),
        "prv_bounds_psi": {k: list(v) for k, v in cfg.prv_bounds_psi.items()},
        "pump_ids": list(cfg.pump_ids),
        "pump_bounds_rel_speed": {k: list(v)
                                  for k, v in cfg.pump_bounds.items()},
        "pressure_norm_band_psi": [cfg.p_min_psi, cfg.p_max_psi],
        "time_encoding": "cyclical sin/cos, 24 h (diurnal) period",
        "consistency_with_frozen_spec": consistency,
        "sample_observation": {
            "sim_time_s": raw.sim_time_s,
            "sim_time_h_of_day": (raw.sim_time_s % 86400.0) / 3600.0,
            "raw_prv_status_codes_epanet": prv_status_codes,
            "raw_pump_status_codes_epanet": pump_status_codes,
            "prv_is_active": {v: bool(a) for v, a in raw.prv_is_active.items()},
            "prv_setpoint_psi": raw.prev_cmd_prv_setpoint_psi,
            "pump_cmd_speed": raw.prev_cmd_pump_speed,
            "pump_realized_speed": raw.pump_realized_speed,
            "vector_min": float(np.min(obs)),
            "vector_max": float(np.max(obs)),
            "vector_mean": float(np.mean(obs)),
            "vector_first8_pressures": [float(x) for x in obs[:8]],
            "vector_tail_time_of_day": [float(x) for x in obs[-2:]],
        },
        "sample_checks": checks,
        "notes": [
            "LinkStatus codes: 0=Closed, 1=Open, 2=Active (EPANET/WNTR). The 5 "
            "controlled PRVs read Active(2) at the sampled mid-day step -> "
            "is_active=1; a valve that opens fully would read Open(1)->0.",
            "The sample runs the no-emitter hydraulic configuration; episode "
            "observations attach the (uncalibrated, validation-only) leak "
            "emitters, which lower pressures marginally. The fixed [-20,300] psi "
            "band brackets both cases; the recorded reference minimum "
            "(4.165 psi @ JUNCTION-29, leak-augmented) remains authoritative.",
            "State design only: no reward, no PPO, no demand model, no safety "
            "clamp (STEP 8/9/10/11).",
        ],
        "epanet_warnings": warns,
    }
    return payload


if __name__ == "__main__":
    out = main()
    dest = Path(C.REPO) / "results" / "phase6" / "p6_s7_state_spec.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"[written] {dest}")
    print("observation_dim =", out["observation_dim"],
          "| checks =", out["sample_checks"])
    print("consistency =", out["consistency_with_frozen_spec"])
