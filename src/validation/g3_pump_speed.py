"""Gate 3 - pump speed response.

Deterministic one-factor-at-a-time sweep. The primary test is a single-period
snapshot (Duration 0) so that tank dynamics and the native tank-level rules
cannot confound the speed effect; a secondary 96 h run records what the same
speed change does once the native rules are back in the loop.

No PPO, no SAC, no tuning: fixed speeds chosen from the pump curves themselves.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_common as C  # noqa: E402

PUMP_CURVE = {"PUMP-170": "CURVE-0", "PUMP-172": "CURVE-2"}
SPEEDS = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 1.00, 1.05, 1.10]


def curve_points_us(wn, curve_name: str) -> list[tuple[float, float]]:
    """Pump curve in the file's own units (GPM, ft)."""
    return [(float(C.m3s_to_gpm(q)), float(C.m_to_ft(h)))
            for q, h in wn.get_curve(curve_name).points]


def curve_power_fit(points_us: list[tuple[float, float]]) -> dict:
    """EPANET's own 3-point pump-curve model: H = h0 - r*Q^n.

    EPANET does not interpolate a 3-point pump curve piecewise-linearly; it fits
    this power function (EPANET 2.2 manual, section on pump curves). The first
    point must be the shutoff point (Q = 0).
    """
    import math

    (q0, h0), (q1, h1), (q2, h2) = points_us
    if q0 != 0.0:
        return {"fitted": False, "reason": "first curve point is not the shutoff point"}
    n = math.log((h0 - h1) / (h0 - h2)) / math.log(q1 / q2)
    r = (h0 - h1) / (q1 ** n)
    return {"fitted": True, "h0_ft": h0, "r": r, "n": n}


def curve_head_at(fit: dict, q_gpm: float, speed: float) -> float:
    """H(Q, n_speed) = n^2 * h0 - r * (Q / n)^n_exp * n^2, i.e. EPANET's scaling."""
    if not fit.get("fitted") or speed <= 0:
        return float("nan")
    if q_gpm <= 0:
        return (speed ** 2) * fit["h0_ft"]
    return (speed ** 2) * (fit["h0_ft"] - fit["r"] * (q_gpm / speed) ** fit["n"])


def min_feasible_speed(fit: dict, static_head_ft: float) -> float:
    """Speed below which shutoff head cannot overcome the static head."""
    if not fit.get("fitted") or static_head_ft <= 0:
        return 0.0
    return (static_head_ft / fit["h0_ft"]) ** 0.5

def snapshot(speeds: dict[str, float], prefix: str) -> dict:
    """Single-period run with the given pump speeds. Returns per-pump state."""
    import wntr

    wn = C.load_wn(rule_timestep=180)
    wn.options.time.duration = 0
    wn.options.time.report_timestep = 0
    for p, s in speeds.items():
        wn.get_link(p).base_speed = float(s)

    # Confirm the speed really reaches the engine: inspect the .inp WNTR writes.
    tmp = C.RESULTS / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    echo = tmp / f"{prefix}_echo.inp"
    wntr.network.io.write_inpfile(wn, str(echo), units="GPM")
    pump_lines = [ln.strip() for ln in echo.read_text(encoding="utf-8").splitlines()
                  if ln.strip().startswith(("PUMP-170", "PUMP-172"))]

    res, msgs = C.run_epanet(wn, prefix)
    out = {"speeds_commanded": speeds, "inp_pump_lines": pump_lines,
           "wntr_warnings": msgs, "pumps": {}}
    for p in wn.pump_name_list:
        link = wn.get_link(p)
        q_gpm = float(C.m3s_to_gpm(res.link["flowrate"][p].iloc[0]))
        h_in = res.node["head"][link.start_node_name].iloc[0]
        h_out = res.node["head"][link.end_node_name].iloc[0]
        dh_ft = float(C.m_to_ft(h_out - h_in))
        pts = curve_points_us(wn, PUMP_CURVE[p])
        fit = curve_power_fit(pts)
        n_sp = speeds.get(p, 1.0)
        q_max_at_speed = pts[-1][0] * n_sp
        status = float(res.link["status"][p].iloc[0])
        expected = curve_head_at(fit, q_gpm, n_sp) if status > 0 else None
        rho_g = 1000.0 * 9.81
        eta = wn.options.energy.global_efficiency / 100.0
        q_si = float(res.link["flowrate"][p].iloc[0])
        power_kW = rho_g * q_si * float(h_out - h_in) / eta / 1e3
        out["pumps"][p] = {
            "speed_commanded": n_sp,
            "speed_in_model": float(link.base_speed),
            "status": status,
            "status_label": "Open" if status > 0 else "Closed",
            "flow_gpm": q_gpm,
            "head_gain_ft": dh_ft,
            "head_gain_expected_from_curve_ft": expected,
            "head_residual_ft": (dh_ft - expected) if expected is not None else None,
            "shutoff_head_ft": fit["h0_ft"] * n_sp ** 2 if fit.get("fitted") else None,
            "static_head_when_shut_ft": dh_ft if status == 0 else None,
            "curve_qmax_at_speed_gpm": q_max_at_speed,
            "beyond_curve_qmax": bool(q_gpm > q_max_at_speed + 1e-6),
            "power_kW": power_kW,
            "inlet_head_ft": float(C.m_to_ft(h_in)),
            "outlet_head_ft": float(C.m_to_ft(h_out)),
        }
    pj = res.node["pressure"][[j for j in wn.junction_name_list]]
    out["pressure_vector_psi"] = {j: float(C.m_to_psi(pj.iloc[0][j])) for j in pj.columns}
    out["network"] = {
        "min_junction_pressure_psi": float(C.m_to_psi(pj.iloc[0].min())),
        "min_at_node": str(pj.iloc[0].idxmin()),
        "max_junction_pressure_psi": float(C.m_to_psi(pj.iloc[0].max())),
        "mean_junction_pressure_psi": float(C.m_to_psi(pj.iloc[0].mean())),
        "n_negative_pressure": int((pj.iloc[0] < 0).sum()),
        "report_scan_errors": _rpt_errors(prefix),
    }
    return out


def _rpt_errors(prefix: str) -> int | None:
    rpt = C.RESULTS / "_tmp" / f"{prefix}.rpt"
    if not rpt.exists():
        return None
    txt = rpt.read_text(encoding="utf-8", errors="replace")
    return sum(1 for ln in txt.splitlines() if "Error" in ln or "ERROR" in ln)


def eps_run(speeds: dict[str, float], prefix: str) -> dict:
    """96 h run at fixed speed, native rules active. Secondary evidence only."""
    import wntr

    wn = C.load_wn(rule_timestep=180, report_timestep=1800)
    for p, s in speeds.items():
        wn.get_link(p).base_speed = float(s)
    res, msgs = C.run_epanet(wn, prefix)
    pw = wntr.metrics.pump_power(res.link["flowrate"], res.node["head"], wn)
    en = wntr.metrics.pump_energy(res.link["flowrate"], res.node["head"], wn)
    out = {"speeds_commanded": speeds, "wntr_warnings": msgs, "pumps": {}}
    for p in wn.pump_name_list:
        st = res.link["status"][p]
        q = C.m3s_to_gpm(res.link["flowrate"][p])
        out["pumps"][p] = {
            "frac_time_open": float((st > 0).mean()),
            "n_status_changes": int((st.diff().fillna(0) != 0).sum()),
            "flow_mean_gpm_when_open": float(q[st > 0].mean()) if (st > 0).any() else 0.0,
            "flow_max_gpm": float(q.max()),
            "volume_pumped_Mgal": float(
                (res.link["flowrate"][p] * wn.options.time.report_timestep).sum()
                * 264.172052 / 1e6),
            "energy_total_kWh": float(en[p].sum()) / 3.6e6,
            "power_mean_when_open_kW": (float(pw[p][st > 0].mean()) / 1e3
                                       if (st > 0).any() else 0.0),
        }
    for t in wn.tank_name_list:
        lev = res.node["head"][t] - wn.get_node(t).elevation
        out.setdefault("tanks", {})[t] = {
            "level_min_ft": float(C.m_to_ft(lev.min())),
            "level_max_ft": float(C.m_to_ft(lev.max())),
            "net_change_ft": float(C.m_to_ft(lev.iloc[-1] - lev.iloc[0])),
            "hit_min_level": bool(lev.min() <= wn.get_node(t).min_level + 1e-9),
        }
    pj = res.node["pressure"][[j for j in wn.junction_name_list]]
    out["network"] = {
        "min_junction_pressure_psi": float(C.m_to_psi(pj.min().min())),
        "mean_junction_pressure_psi": float(C.m_to_psi(pj.stack().mean())),
        "n_negative_node_timesteps": int((pj < 0).sum().sum()),
        "report_scan_errors": _rpt_errors(prefix),
    }
    return out
def eps_no_rules(speed: float, prefix: str) -> dict:
    """Diagnostic: what pressure authority would speed have if the agent replaced
    the native on/off rules with a continuously running pump?

    The native rules force a duty cycle, so in the rule-driven EPS a speed change
    mostly changes run time rather than pressure. Removing the rules is not a
    topology edit and no PRV or element is added or deleted; it is a bounded
    what-if used only to bound the actuator's authority.
    """
    wn = C.load_wn(rule_timestep=180, report_timestep=1800)
    removed = []
    for name in list(wn.control_name_list):
        ctrl = wn.get_control(name)
        if any(p in str(ctrl) for p in ("PUMP-170", "PUMP-172")):
            wn.remove_control(name)
            removed.append(name)
    for p in wn.pump_name_list:
        wn.get_link(p).base_speed = float(speed)
        wn.get_link(p).initial_status = "Open"
    res, msgs = C.run_epanet(wn, prefix)
    pj = res.node["pressure"][[j for j in wn.junction_name_list]]
    out = {
        "speed": speed,
        "controls_removed": removed,
        "wntr_warnings": msgs,
        "report_scan_errors": _rpt_errors(prefix),
        "min_junction_pressure_psi": float(C.m_to_psi(pj.min().min())),
        "mean_junction_pressure_psi": float(C.m_to_psi(pj.stack().mean())),
        "max_junction_pressure_psi": float(C.m_to_psi(pj.max().max())),
        "n_negative_node_timesteps": int((pj < 0).sum().sum()),
        "pressure_vector_mean_psi": {j: float(C.m_to_psi(pj[j].mean())) for j in pj.columns},
    }
    for t in wn.tank_name_list:
        lev = res.node["head"][t] - wn.get_node(t).elevation
        out.setdefault("tanks", {})[t] = {
            "level_min_ft": float(C.m_to_ft(lev.min())),
            "level_max_ft": float(C.m_to_ft(lev.max())),
            "max_level_ft": float(C.m_to_ft(wn.get_node(t).max_level)),
            "overflowed": bool(lev.max() > wn.get_node(t).max_level + 1e-9),
            "emptied": bool(lev.min() <= wn.get_node(t).min_level + 1e-9),
        }
    return out


def main() -> dict:
    wn0 = C.load_wn()
    curves = {p: curve_points_us(wn0, c) for p, c in PUMP_CURVE.items()}
    fits = {p: curve_power_fit(pts) for p, pts in curves.items()}

    ref = snapshot({}, "g3_snap_ref")
    sweep: dict[str, list] = {"PUMP-170": [], "PUMP-172": []}
    for pump in ("PUMP-170", "PUMP-172"):
        for s in SPEEDS:
            tag = f"g3_{pump.split('-')[1]}_{int(s*100):03d}"
            r = snapshot({pump: s}, tag)
            row = r["pumps"][pump]
            other = [p for p in sweep if p != pump][0]
            row["other_pump_flow_gpm"] = r["pumps"][other]["flow_gpm"]
            row["network"] = r["network"]
            row["inp_pump_lines"] = r["inp_pump_lines"]
            # Actuator authority: how far does the pressure field move?
            base = ref["pressure_vector_psi"]
            dp = {j: r["pressure_vector_psi"][j] - base[j] for j in base}
            worst = max(dp, key=lambda j: abs(dp[j]))
            row["pressure_influence_vs_speed1"] = {
                "max_abs_dP_psi": abs(dp[worst]),
                "max_abs_dP_node": worst,
                "n_junctions_moved_gt_0p5psi": sum(1 for v in dp.values() if abs(v) > 0.5),
                "n_junctions_moved_gt_2psi": sum(1 for v in dp.values() if abs(v) > 2.0),
                "mean_abs_dP_psi": sum(abs(v) for v in dp.values()) / len(dp),
            }
            sweep[pump].append(row)

    # Minimum feasible speed, from the static head each pump must overcome.
    feasible = {}
    for pump, rows in sweep.items():
        shut = [r for r in rows if r["status"] == 0]
        static = shut[0]["static_head_when_shut_ft"] if shut else None
        feasible[pump] = {
            "static_head_across_shut_pump_ft": static,
            "shutoff_head_at_speed1_ft": fits[pump]["h0_ft"],
            "min_feasible_speed_snapshot": (
                min_feasible_speed(fits[pump], static) if static else None),
            "highest_speed_that_shut_the_pump": max((r["speed_commanded"] for r in shut),
                                                    default=None),
            "lowest_speed_that_ran": min((r["speed_commanded"] for r in rows
                                          if r["status"] > 0), default=None),
            "note": ("The pump shuts when n^2 * h0 falls below the static head it must "
                     "lift. The static head depends on tank level, so this bound moves "
                     "during an EPS and is not a fixed constant."),
        }

    affinity = {}
    for pump, rows in sweep.items():
        running = [r for r in rows if r["status"] > 0]
        affinity[pump] = {
            "epanet_3point_fit_h0_r_n": fits[pump],
            "shutoff_scales_as_speed_squared": [
                {"speed": r["speed_commanded"], "shutoff_ft": r["shutoff_head_ft"],
                 "ratio_to_speed1": r["shutoff_head_ft"] / fits[pump]["h0_ft"],
                 "speed_squared": r["speed_commanded"] ** 2,
                 "match": abs(r["shutoff_head_ft"] / fits[pump]["h0_ft"]
                              - r["speed_commanded"] ** 2) < 1e-9}
                for r in rows],
            "operating_point_on_fitted_curve": [
                {"speed": r["speed_commanded"], "flow_gpm": r["flow_gpm"],
                 "head_observed_ft": r["head_gain_ft"],
                 "head_from_fit_ft": r["head_gain_expected_from_curve_ft"],
                 "residual_ft": r["head_residual_ft"]}
                for r in running],
            "max_abs_residual_running_ft": max(abs(r["head_residual_ft"]) for r in running),
        }

    eps = {f"speed_{int(s*100)}": eps_run({"PUMP-170": s, "PUMP-172": s}, f"g3_eps_{int(s*100)}")
           for s in (0.85, 1.00)}
    nr = {f"speed_{int(s*100)}": eps_no_rules(s, f"g3_norule_{int(s*100)}")
          for s in (0.85, 1.00)}
    a, b = nr["speed_85"]["pressure_vector_mean_psi"], nr["speed_100"]["pressure_vector_mean_psi"]
    nr_auth = {
        "max_abs_mean_dP_psi": max(abs(a[j] - b[j]) for j in a),
        "max_abs_mean_dP_node": max(a, key=lambda j: abs(a[j] - b[j])),
        "n_junctions_mean_moved_gt_1psi": sum(1 for j in a if abs(a[j] - b[j]) > 1.0),
        "n_junctions_mean_moved_gt_5psi": sum(1 for j in a if abs(a[j] - b[j]) > 5.0),
    }
    eps_auth = {
        "rule_driven_mean_dP_psi_0p85_vs_1p00": abs(
            eps["speed_85"]["network"]["mean_junction_pressure_psi"]
            - eps["speed_100"]["network"]["mean_junction_pressure_psi"]),
        "rule_driven_min_dP_psi_0p85_vs_1p00": abs(
            eps["speed_85"]["network"]["min_junction_pressure_psi"]
            - eps["speed_100"]["network"]["min_junction_pressure_psi"]),
        "rule_driven_energy_change_pct": {
            p: (eps["speed_85"]["pumps"][p]["energy_total_kWh"]
                / eps["speed_100"]["pumps"][p]["energy_total_kWh"] - 1.0) * 100.0
            for p in eps["speed_100"]["pumps"]},
        "interpretation": ("Under the native rules a speed change mainly redistributes pump "
                           "run time and energy; the pressure field is anchored by the two "
                           "tanks, whose level the rules confine to a narrow band. This is an "
                           "observation about actuator authority, not a verdict on the thesis."),
    }

    applied = all(
        abs(r["speed_in_model"] - r["speed_commanded"]) < 1e-12 and
        any("SPEED" in ln.upper() for ln in r["inp_pump_lines"]) == (r["speed_commanded"] != 1.0)
        for rows in sweep.values() for r in rows)
    monotone = {}
    for pump, rows in sweep.items():
        ok = [r for r in rows if r["status"] > 0]
        qs = [r["flow_gpm"] for r in ok]
        hs = [r["head_gain_ft"] for r in ok]
        monotone[pump] = {
            "flow_monotone_increasing_in_speed": all(a <= b + 1e-9 for a, b in zip(qs, qs[1:])),
            "flow_range_gpm": [min(qs), max(qs)],
            "head_range_ft": [min(hs), max(hs)],
            "flow_span_gpm": max(qs) - min(qs),
            "head_span_ft": max(hs) - min(hs),
            "n_speeds_with_pump_shut": sum(1 for r in rows if r["status"] == 0),
            "n_speeds_beyond_curve_qmax": sum(1 for r in rows if r["beyond_curve_qmax"]),
            "speeds_beyond_curve_qmax": [r["speed_commanded"] for r in rows
                                         if r["beyond_curve_qmax"]],
        }
    residual_ok = all(v["max_abs_residual_running_ft"] < 0.5 for v in affinity.values())
    responds = all(v["flow_span_gpm"] > 1.0 for v in monotone.values())
    errs = [r["network"]["report_scan_errors"] for rows in sweep.values() for r in rows]
    verdict = "PASS" if (applied and residual_ok and responds
                         and all(e == 0 for e in errs if e is not None)) else "FAIL"

    payload = {
        "gate": "G3",
        "title": "Pump speed response",
        "env": C.env_info(),
        "method": {
            "primary": ("Single-period snapshot, Duration = 0, so tanks act as fixed-head "
                        "boundaries at their initial levels and the tank-level rules cannot "
                        "fire. One pump varied at a time; the other held at speed 1.0."),
            "secondary": ("96 h EPS at a uniform fixed speed with the native rules active, "
                          "to record the rule/speed feedback that the snapshot removes."),
            "speeds_tested": SPEEDS,
            "curve_model": ("EPANET fits a 3-point pump curve with H = h0 - r*Q^n and scales "
                            "it as H(Q,s) = s^2 * (h0 - r*(Q/s)^n). The fitted coefficients "
                            "are reported so the residual check is auditable."),
            "speed_range_justification": (
                "Both pumps carry real 3-point head curves, so EPANET admits any speed s > 0. "
                "The sweep spans 0.50-1.10 and each row records (a) whether the operating "
                "flow exceeds s * Qmax of the curve, and (b) whether the engine shut the pump "
                "because s^2 * h0 fell below the static head."),
            "no_optimisation": "Speeds are a fixed deterministic list. No PPO, SAC or search.",
        },
        "pump_curves_gpm_ft": curves,
        "pump_curve_fits": fits,
        "reference_snapshot_speed_1": {k: v for k, v in ref.items()
                                      if k != "pressure_vector_psi"},
        "sweep": sweep,
        "feasible_speed_bounds": feasible,
        "affinity_law_check": affinity,
        "response_summary": monotone,
        "eps_fixed_speed": eps,
        "eps_rules_disabled_diagnostic": {"runs": nr, "authority": nr_auth},
        "pump_pressure_authority": eps_auth,
        "speed_really_applied": applied,
        "verdict": f"G3 PUMP SPEED RESPONSE = {verdict}",
    }
    C.jdump("g3_pump_speed.json", payload)

    for pump, rows in sweep.items():
        f = fits[pump]
        print(f"\n--- {pump} ({PUMP_CURVE[pump]}) single-period OFAT ---------------")
        print(f"  EPANET 3-point fit: H = {f['h0_ft']:.1f} - {f['r']:.6g} * Q^{f['n']:.5f} (ft, GPM)")
        print(f"{'speed':>6} {'stat':>6} {'flow_gpm':>10} {'head_ft':>9} {'fit_ft':>9} "
              f"{'resid':>8} {'power_kW':>9} {'shutoff':>8} {'maxdP':>7} {'>0.5psi':>8} {'minP':>7}")
        for r in rows:
            fit_s = f"{r['head_gain_expected_from_curve_ft']:9.3f}" if r["head_residual_ft"] is not None else "        -"
            res_s = f"{r['head_residual_ft']:8.4f}" if r["head_residual_ft"] is not None else "       -"
            infl = r["pressure_influence_vs_speed1"]
            print(f"{r['speed_commanded']:6.2f} {r['status_label']:>6} {r['flow_gpm']:10.3f} "
                  f"{r['head_gain_ft']:9.3f} {fit_s} {res_s} {r['power_kW']:9.2f} "
                  f"{r['shutoff_head_ft']:8.2f} {infl['max_abs_dP_psi']:7.3f} "
                  f"{infl['n_junctions_moved_gt_0p5psi']:8d} "
                  f"{r['network']['min_junction_pressure_psi']:7.3f}")
        print(f"  max |residual| on running rows = "
              f"{affinity[pump]['max_abs_residual_running_ft']:.5f} ft")
        fb = feasible[pump]
        print(f"  static head across shut pump = {fb['static_head_across_shut_pump_ft']} ft, "
              f"shutoff@s=1 = {fb['shutoff_head_at_speed1_ft']} ft, "
              f"min feasible speed = {fb['min_feasible_speed_snapshot']}")
        print(f"  shut at speeds <= {fb['highest_speed_that_shut_the_pump']}, "
              f"ran from {fb['lowest_speed_that_ran']}")
        m = monotone[pump]
        print(f"  flow {m['flow_range_gpm'][0]:.1f}-{m['flow_range_gpm'][1]:.1f} GPM, "
              f"head {m['head_range_ft'][0]:.1f}-{m['head_range_ft'][1]:.1f} ft, "
              f"monotone={m['flow_monotone_increasing_in_speed']}, "
              f"extrapolated_rows={m['n_speeds_beyond_curve_qmax']}")
    print("\n--- 96 h EPS at fixed uniform speed ----------------------------")
    for k, v in eps.items():
        print(f"  {k}: " + ", ".join(
            f"{p} open={d['frac_time_open']:.3f} sw={d['n_status_changes']} "
            f"kWh={d['energy_total_kWh']:.0f} vol={d['volume_pumped_Mgal']:.3f}Mgal"
            for p, d in v["pumps"].items()))
        print(f"      tanks={ {t: (round(d['level_min_ft'],2), round(d['level_max_ft'],2), d['hit_min_level']) for t, d in v['tanks'].items()} }")
        print(f"      minP={v['network']['min_junction_pressure_psi']:.3f} psi, "
              f"errors={v['network']['report_scan_errors']}")
    print(f"\nspeed really applied by the engine: {applied}")
    print("\n--- pump pressure authority -------------------------------------")
    print(f"  rule-driven EPS 0.85 vs 1.00: mean dP = "
          f"{eps_auth['rule_driven_mean_dP_psi_0p85_vs_1p00']:.4f} psi, min dP = "
          f"{eps_auth['rule_driven_min_dP_psi_0p85_vs_1p00']:.4f} psi, energy change = "
          + ", ".join(f"{p} {v:+.2f}%" for p, v in eps_auth['rule_driven_energy_change_pct'].items()))
    print("\n--- diagnostic: native pump rules disabled, pump always on ------")
    for k, v in nr.items():
        print(f"  {k}: controls_removed={v['controls_removed']} errors={v['report_scan_errors']} "
              f"minP={v['min_junction_pressure_psi']:.3f} meanP={v['mean_junction_pressure_psi']:.3f} "
              f"maxP={v['max_junction_pressure_psi']:.3f} psi")
        print(f"      tanks={ {t: (round(d['level_min_ft'],2), round(d['level_max_ft'],2), 'overflow' if d['overflowed'] else ('empty' if d['emptied'] else 'in-band')) for t, d in v['tanks'].items()} }")
    print(f"  authority without rules: {nr_auth}")
    print(f"\n{payload['verdict']}")
    return payload


if __name__ == "__main__":
    main()


