"""Gates 6, 7 and 8 - leakage validation, PDA response, leakage/service separation.

The leakage model is the simplest defensible one: pressure-dependent orifice flow
q = C * p^alpha applied at every junction through EPANET's own [EMITTERS] section.
alpha is not invented - it is the value the distributed file already declares in
[OPTIONS] Emitter Exponent, so no file option has to be changed to justify it.

The coefficients are allocated deterministically in proportion to half the incident
pipe length at each junction, then scaled by ONE closed-form global factor computed
from the leak-free baseline pressures. There is no search, no iteration and no
tuning: the achieved leakage share is whatever that single step produces, and it is
reported as observed. This coefficient is a validation instrument only and must not
enter any thesis result.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_common as C  # noqa: E402

LEAK_EXPONENT = 0.5          # = [OPTIONS] Emitter Exponent in the distributed file
LEAK_TARGET_FRACTION = 0.10  # target share of mean system inflow, one closed-form step
PDA_REQUIRED_PSI = 20.0      # author's validation choice, see gate 7 notes
PDA_MINIMUM_PSI = 0.0
PDA_EXPONENT = 0.5
PRV_SCALES = [0.25, 0.50, 0.75, 1.00, 1.25]
VALVES = ["VALVE-173", "VALVE-174", "VALVE-175", "VALVE-176",
          "VALVE-177", "VALVE-178", "VALVE-179", "VALVE-180"]
NOMINAL_PSI = {"VALVE-173": 70.0, "VALVE-174": 80.0, "VALVE-175": 55.0,
               "VALVE-176": 29.762, "VALVE-177": 45.0, "VALVE-178": 37.0,
               "VALVE-179": 40.0, "VALVE-180": 16.45}

# Valves that actually regulate in the distributed 96 h baseline (G5 evidence).
# VALVE-173 is Active but carries 1.5 GPM; VALVE-174/-179/-180 carry identically
# zero flow. Scaling the whole set upward reopens VALVE-179 and therefore *lowers*
# network pressure, which contaminates a nominally "higher pressure" case. Family B
# scales only these four so that a monotone pressure ladder exists on the high side.
ACTIVE_VALVES = ["VALVE-175", "VALVE-176", "VALVE-177", "VALVE-178"]
ACTIVE_ONLY_SCALES = [1.10, 1.25, 1.50]

# Solver settings adopted for every gate that does leakage or mass-balance
# accounting. The distributed file declares ACCURACY 0.005 / TRIALS 40, which is
# five times looser than EPANET's own 0.001 default. Measured consequence with the
# 126-emitter leakage model over 96 h (probe recorded in the report, Gate 9):
#   ACCURACY  TRIALS  max|q_emitter_engine - C*p^a|  max|sum node demand|
#     0.005      40                    2.0135 GPM             9.9692 GPM
#     0.001      40                    0.2954 GPM             1.9942 GPM
#     1e-4      100                    0.0015 GPM             0.0444 GPM
#     1e-5      200                    0.0000 GPM             0.0004 GPM
# EPANET reports zero errors and zero warnings in every one of those runs, so the
# 9.97 GPM continuity violation at the file's own setting is entirely silent. At
# 1e-5 the emitter law is reproduced exactly, so leakage can be accounted for
# rather than estimated. TRIALS must be raised with it: at 1e-5 the leak-free run
# needs more than 1200 trials at one timestep and halts at 19:00 h with
# "System unbalanced" when only 200 are allowed. Runtime cost is 0.24 s vs 0.10 s
# for the full 96 h horizon. Change impact on the leak-free baseline: mean
# pressure 103.8258 -> 103.8221 psi, min 4.224 -> 4.225 psi, identical pump switch
# counts (7/7), one single timestep (62 h) where PUMP-172 differs.
SOLVER_ACCURACY = 1e-5
SOLVER_TRIALS = 2000


def half_length_weights(wn) -> dict[str, float]:
    """Half the incident pipe length at each junction, in ft.

    Deterministic and closed-form: every junction owns half of each pipe that
    touches it, which is the standard way to turn a pipe-length-proportional
    background-leakage assumption into nodal emitters. No random seed is involved.
    """
    w = {j: 0.0 for j in wn.junction_name_list}
    for p in wn.pipe_name_list:
        link = wn.get_link(p)
        for n in (link.start_node_name, link.end_node_name):
            if n in w:
                w[n] += 0.5 * float(C.m_to_ft(link.length))
    return w


def leak_coefficients(weights: dict[str, float], mean_p_psi: dict[str, float],
                      target_leak_gpm: float) -> dict:
    """One closed-form global scale factor. No search, no iteration.

    Solves k * sum_j w_j * p_j^alpha = target for k, using the leak-free baseline
    mean pressures. Because adding leakage lowers pressure, the achieved leakage
    will come out below the target; that difference is reported, not corrected.
    """
    s = sum(weights[j] * max(mean_p_psi[j], 0.0) ** LEAK_EXPONENT for j in weights)
    k = target_leak_gpm / s
    coeff = {j: k * weights[j] for j in weights}
    return {
        "global_scale_k_gpm_per_ft_per_psi_alpha": k,
        "sum_w_p_alpha": s,
        "target_leak_gpm": target_leak_gpm,
        "n_junctions_with_emitter": len(coeff),
        "coefficient_gpm_per_psi_alpha": coeff,
        "coefficient_min": min(coeff.values()),
        "coefficient_max": max(coeff.values()),
        "alpha": LEAK_EXPONENT,
        "closed_form": ("k = target / sum_j (w_j * p_baseline_j^alpha); single "
                        "evaluation, no optimisation of any kind."),
    }


def apply_leak(wn, coeff_us: dict[str, float]) -> None:
    """Write the emitter coefficients into the in-memory model.

    WNTR's EmitterCoeff unit conversion assumes an exponent of 0.5 (it multiplies
    by sqrt(0.4333/0.3048) to go from GPM/sqrt(psi) to SI). That is exactly the
    exponent this file declares, so the conversion is valid here; it would not be
    for any other alpha.
    """
    from wntr.epanet.util import FlowUnits, HydParam, to_si

    for j, c in coeff_us.items():
        wn.get_node(j).emitter_coefficient = to_si(FlowUnits.GPM, c, HydParam.EmitterCoeff)


def echo_check(wn, prefix: str) -> dict:
    """Write the model out and read it back, to prove what reaches the engine.

    Same discipline as gate 3: never assume an in-memory attribute became an
    EPANET input token. [EMITTERS] and the demand-model options are read back
    from the echoed file in the file's own GPM/psi units.
    """
    import wntr

    p = C.RESULTS / "_tmp" / f"{prefix}_echo.inp"
    wntr.network.io.write_inpfile(wn, str(p), units="GPM")
    sec = C.read_sections(p)
    emit = {}
    for ln in sec.get("EMITTERS", []):
        t = ln.split()
        emit[t[0]] = float(t[1])
    opts = {}
    for ln in sec.get("OPTIONS", []):
        t = ln.split()
        key = " ".join(t[:2]).upper()
        if key in ("DEMAND MODEL", "MINIMUM PRESSURE", "REQUIRED PRESSURE",
                   "PRESSURE EXPONENT", "EMITTER EXPONENT", "ACCURACY"):
            opts[key] = " ".join(t[2:])
    valves = {}
    for ln in sec.get("VALVES", []):
        t = ln.split()
        valves[t[0]] = float(t[5])
    return {
        "echo_file": str(p),
        "n_emitter_lines": len(emit),
        "emitter_total_coefficient_gpm_per_psi_alpha": sum(emit.values()) if emit else 0.0,
        "emitter_sample": dict(sorted(emit.items())[:3]),
        "options_relevant": opts,
        "valve_settings_psi": valves,
    }


def accounting(wn, res, coeff_us: dict[str, float] | None) -> dict:
    """Per-timestep water balance in GPM, plus the leak/service split.

    EPANET folds emitter discharge into the reported nodal demand, so leakage is
    recomputed from the reported pressure with the same law the engine applied and
    subtracted to obtain the demand actually served.

    Two details were established empirically before this function could be trusted,
    both by single-emitter isolation runs against the engine:

    1. The law must be SIGNED: q = sign(p) * C * |p|^alpha. EPANET's emitter is a
       virtual pipe to a virtual reservoir, so at a node with negative pressure it
       flows backwards. Measured at JUNCTION-126, p = -5.731 psi: engine emitter
       flow -0.6416 GPM, signed law -0.6416 GPM, clipped law 0.0000 GPM.
    2. The residual q_node - expected_demand only equals the emitter law when the
       hydraulic solution is actually converged. At the file's ACCURACY 0.005 the
       per-node error reaches 2.01 GPM and the network continuity residual 9.97 GPM
       with no EPANET warning; at ACCURACY 1e-5 the law is reproduced to 0.0000 GPM.
       See SOLVER_ACCURACY.

    Because of (2) the engine's own implied emitter flow is reported alongside the
    modelled one, so any future divergence is visible in the artefact rather than
    hidden inside a verdict.
    """
    import numpy as np
    import wntr

    junc = wn.junction_name_list
    p_psi = C.m_to_psi(res.node["pressure"][junc])
    q_node = C.m3s_to_gpm(res.node["demand"][junc])          # includes emitter flow
    req_node = C.m3s_to_gpm(wntr.metrics.expected_demand(wn)[junc])
    req_node.index = q_node.index
    if coeff_us:
        leak_node = (np.sign(p_psi) * p_psi.abs() ** LEAK_EXPONENT).mul(
            [coeff_us[j] for j in junc], axis=1)
    else:
        leak_node = p_psi * 0.0
    leak = leak_node.sum(axis=1)
    served = q_node.sum(axis=1) - leak
    req = req_node.sum(axis=1)
    dsr = served / req
    inflow = -C.m3s_to_gpm(res.node["demand"][wn.reservoir_name_list].sum(axis=1))
    storage = C.m3s_to_gpm(res.node["demand"][wn.tank_name_list].sum(axis=1))
    resid = C.m3s_to_gpm(res.node["demand"].sum(axis=1))
    # Total withdrawal is the physically meaningful normaliser. Reservoir inflow
    # passes through ~0 at some timesteps when the tanks carry the system, so
    # normalising by inflow manufactures huge relative errors out of tiny absolute
    # ones (an earlier version of this file reported 63.58 for exactly that reason).
    withdrawal = C.m3s_to_gpm(res.node["demand"].clip(lower=0.0).sum(axis=1))
    # Under DDA the engine's implied emitter flow is (reported demand - requested
    # demand) at every junction. Under PDA that difference also contains curtailment,
    # so the check is only meaningful for DDA and is reported as such.
    implied = q_node - req_node
    dda = str(wn.options.hydraulic.demand_model).upper().startswith("D")
    out = {
        "n_timesteps": int(len(served)),
        "report_timestep_h": float(wn.options.time.report_timestep) / 3600.0,
        "requested_demand_mean_gpm": float(req.mean()),
        "served_demand_mean_gpm": float(served.mean()),
        "leakage_mean_gpm": float(leak.mean()),
        "leakage_max_gpm": float(leak.max()),
        "system_inflow_mean_gpm": float(inflow.mean()),
        "net_tank_fill_mean_gpm": float(storage.mean()),
        "leakage_share_of_inflow_pct": float(leak.mean() / inflow.mean() * 100.0),
        "leakage_share_of_served_pct": float(leak.mean() / served.mean() * 100.0),
        "dsr_mean": float(dsr.mean()),
        "dsr_min": float(dsr.min()),
        "dsr_max": float(dsr.max()),
        "n_timesteps_dsr_below_0p999": int((dsr < 0.999).sum()),
        "unserved_demand_mean_gpm": float((req - served).mean()),
        "unserved_demand_max_gpm": float((req - served).max()),
        "mean_junction_pressure_psi": float(p_psi.stack().mean()),
        "min_junction_pressure_psi": float(p_psi.min().min()),
        "n_node_timesteps_below_20psi": int((p_psi < 20.0).sum().sum()),
        "n_node_timesteps_negative_pressure": int((p_psi < 0.0).sum().sum()),
        "continuity_residual_max_abs_gpm": float(resid.abs().max()),
        "continuity_residual_rel_max": float((resid.abs() / withdrawal).max()),
        "total_withdrawal_mean_gpm": float(withdrawal.mean()),
        "volume_in_Mgal": float(inflow.sum() * 60.0 * out_dt(wn) / 1e6),
        "volume_served_Mgal": float(served.sum() * 60.0 * out_dt(wn) / 1e6),
        "volume_leaked_Mgal": float(leak.sum() * 60.0 * out_dt(wn) / 1e6),
        "volume_into_tanks_Mgal": float(storage.sum() * 60.0 * out_dt(wn) / 1e6),
        "emitter_law": "q = sign(p) * C * |p|^alpha, alpha = %.3f" % LEAK_EXPONENT,
    }
    if coeff_us and dda:
        err = (implied - leak_node).abs()
        out["engine_vs_modelled_leak_max_abs_gpm"] = float(err.max().max())
        out["engine_vs_modelled_leak_max_node"] = str(err.max().idxmax())
        out["engine_implied_leak_mean_gpm"] = float(implied.sum(axis=1).mean())
    else:
        out["engine_vs_modelled_leak_max_abs_gpm"] = None
        out["engine_vs_modelled_leak_note"] = (
            "not applicable: no leakage, or PDA folds curtailment into the same "
            "difference so it cannot isolate emitter flow")
    return out


def out_dt(wn) -> float:
    """Reporting interval in hours - the interval each reported row represents."""
    return float(wn.options.time.report_timestep) / 3600.0


def _rpt_errors(prefix: str) -> dict:
    rpt = C.RESULTS / "_tmp" / f"{prefix}.rpt"
    if not rpt.exists():
        return {"rpt_found": False}
    txt = rpt.read_text(encoding="utf-8", errors="replace").splitlines()
    return {
        "rpt_found": True,
        "n_error_lines": sum(1 for ln in txt if "Error" in ln or "ERROR" in ln),
        "n_warning_lines": sum(1 for ln in txt if "WARNING" in ln),
        "flagged_lines": [ln.strip() for ln in txt
                          if "WARNING" in ln or "Error" in ln or "ERROR" in ln][:12],
    }


def _run_with_retry(wn, prefix: str, attempts: int = 4):
    """Run EPANET, tolerating the occasional truncated-binary read on Windows.

    A genuine EPANET halt is distinguished from a transient read failure by scanning
    the report file for "EXECUTION HALTED"; that case is raised, never retried away.
    """
    import time

    last = None
    for k in range(attempts):
        pfx = prefix if k == 0 else f"{prefix}_r{k}"
        try:
            res, msgs = C.run_epanet(wn, pfx)
            return res, msgs, pfx
        except Exception as exc:            # noqa: BLE001 - re-raised below
            last = exc
            scan = _rpt_errors(pfx)
            if any("HALTED" in ln.upper() for ln in scan.get("flagged_lines", [])):
                raise RuntimeError(
                    f"EPANET halted in case {prefix}: {scan['flagged_lines']}") from exc
            time.sleep(1.0)
    raise RuntimeError(f"could not read EPANET output for {prefix}") from last


def run_case(label: str, prefix: str, *, demand_model: str = "DDA",
             coeff_us: dict | None = None, prv_scale: float = 1.0,
             prv_subset: list | None = None,
             pump_speed: float | None = None, accuracy: float | None = None,
             trials: int | None = None) -> dict:
    """One 96 h EPS. Native controls and topology untouched in every case."""
    wn = C.load_wn(rule_timestep=180, report_timestep=1800)
    wn.options.hydraulic.accuracy = float(accuracy or SOLVER_ACCURACY)
    wn.options.hydraulic.trials = int(trials or SOLVER_TRIALS)
    if demand_model == "PDA":
        wn.options.hydraulic.demand_model = "PDA"
        wn.options.hydraulic.required_pressure = float(C.psi_to_m(PDA_REQUIRED_PSI))
        wn.options.hydraulic.minimum_pressure = float(C.psi_to_m(PDA_MINIMUM_PSI))
        wn.options.hydraulic.pressure_exponent = PDA_EXPONENT
    scaled = list(prv_subset) if prv_subset is not None else list(VALVES)
    if prv_scale != 1.0:
        for v in scaled:
            wn.get_link(v).initial_setting = C.psi_to_m(NOMINAL_PSI[v] * prv_scale)
    if pump_speed is not None:
        for p in wn.pump_name_list:
            wn.get_link(p).base_speed = float(pump_speed)
    if coeff_us:
        apply_leak(wn, coeff_us)
    echo = echo_check(wn, prefix)
    res, msgs, used_prefix = _run_with_retry(wn, prefix)
    out = {
        "label": label,
        "demand_model": demand_model,
        "prv_scale_of_nominal": prv_scale,
        "prv_scaled_valves": scaled if prv_scale != 1.0 else [],
        "pump_base_speed": pump_speed,
        "accuracy_option": float(wn.options.hydraulic.accuracy),
        "trials_option": int(wn.options.hydraulic.trials),
        "leak_applied": bool(coeff_us),
        "echo_check": echo,
        "wntr_warnings": msgs,
        "report_scan": _rpt_errors(used_prefix),
    }
    out.update(accounting(wn, res, coeff_us))
    junc = wn.junction_name_list
    p_psi = C.m_to_psi(res.node["pressure"][junc])
    out["mean_pressure_by_node_psi"] = {j: float(p_psi[j].mean()) for j in junc}
    out["min_pressure_by_node_psi"] = {j: float(p_psi[j].min()) for j in junc}
    low = sorted((j for j in junc if p_psi[j].mean() < 20.0),
                 key=lambda j: p_psi[j].mean())
    out["junctions_mean_pressure_below_20psi"] = {
        j: {"mean_psi": float(p_psi[j].mean()), "min_psi": float(p_psi[j].min()),
            "elevation_ft": float(C.m_to_ft(wn.get_node(j).elevation))}
        for j in low}
    from wntr.network.base import LinkStatus
    out["valve_states"] = {
        v: sorted({LinkStatus(int(x)).name for x in res.link["status"][v]})
        for v in wn.valve_name_list}
    out["valve_flow_mean_gpm"] = {
        v: float(C.m3s_to_gpm(res.link["flowrate"][v]).mean()) for v in wn.valve_name_list}
    out["tank_level_range_ft"] = {
        t: [float(C.m_to_ft((res.node["head"][t] - wn.get_node(t).elevation).min())),
            float(C.m_to_ft((res.node["head"][t] - wn.get_node(t).elevation).max()))]
        for t in wn.tank_name_list}
    return out


def baseline_pressures(prefix: str) -> tuple[dict, float, dict]:
    """Leak-free nominal run, used only to size the emitter coefficients."""
    wn = C.load_wn(rule_timestep=180, report_timestep=1800)
    wn.options.hydraulic.accuracy = SOLVER_ACCURACY
    wn.options.hydraulic.trials = SOLVER_TRIALS
    res, _, _ = _run_with_retry(wn, prefix)
    junc = wn.junction_name_list
    p = C.m_to_psi(res.node["pressure"][junc]).clip(lower=0.0)
    inflow = -C.m3s_to_gpm(res.node["demand"][wn.reservoir_name_list].sum(axis=1))
    return ({j: float(p[j].mean()) for j in junc}, float(inflow.mean()),
            half_length_weights(wn))


def main() -> dict:
    base_p, base_inflow, weights = baseline_pressures("g6_size")
    sizing = leak_coefficients(weights, base_p,
                               LEAK_TARGET_FRACTION * base_inflow)
    coeff = sizing["coefficient_gpm_per_psi_alpha"]

    cases = {}
    cases["DDA_noleak_nominal"] = run_case(
        "DDA, no leakage, nominal PRVs", "g6_dda_noleak")
    cases["PDA_noleak_nominal"] = run_case(
        "PDA, no leakage, nominal PRVs", "g7_pda_noleak", demand_model="PDA")
    # Family A: all eight PRV settings scaled together.
    for s in PRV_SCALES:
        tag = f"{int(round(s * 100)):03d}"
        cases[f"DDA_leak_prv{s:.2f}"] = run_case(
            f"DDA, leakage, all PRVs x{s:.2f}", f"g6_dda_leak_{tag}",
            coeff_us=coeff, prv_scale=s)
        cases[f"PDA_leak_prv{s:.2f}"] = run_case(
            f"PDA, leakage, all PRVs x{s:.2f}", f"g8_pda_leak_{tag}",
            demand_model="PDA", coeff_us=coeff, prv_scale=s)
    # Family B: only the four PRVs that regulate in the baseline are scaled, so the
    # high-pressure end of the ladder is not contaminated by VALVE-179 reopening.
    for s in ACTIVE_ONLY_SCALES:
        tag = f"{int(round(s * 100)):03d}"
        cases[f"DDA_leak_actv{s:.2f}"] = run_case(
            f"DDA, leakage, active PRVs x{s:.2f}", f"g6_dda_actv_{tag}",
            coeff_us=coeff, prv_scale=s, prv_subset=ACTIVE_VALVES)
        cases[f"PDA_leak_actv{s:.2f}"] = run_case(
            f"PDA, leakage, active PRVs x{s:.2f}", f"g8_pda_actv_{tag}",
            demand_model="PDA", coeff_us=coeff, prv_scale=s, prv_subset=ACTIVE_VALVES)

    def rows(model: str) -> list[dict]:
        out = []
        for fam, scales, key in (("A_all_prv", PRV_SCALES, "prv"),
                                 ("B_active_prv_only", ACTIVE_ONLY_SCALES, "actv")):
            for s in scales:
                c = cases[f"{model}_leak_{key}{s:.2f}"]
                out.append({
                    "family": fam,
                    "prv_scale": s,
                    "scaled_valves": c["prv_scaled_valves"] or VALVES,
                    "mean_junction_pressure_psi": c["mean_junction_pressure_psi"],
                    "min_junction_pressure_psi": c["min_junction_pressure_psi"],
                    "leakage_mean_gpm": c["leakage_mean_gpm"],
                    "leakage_share_of_inflow_pct": c["leakage_share_of_inflow_pct"],
                    "system_inflow_mean_gpm": c["system_inflow_mean_gpm"],
                    "requested_demand_mean_gpm": c["requested_demand_mean_gpm"],
                    "served_demand_mean_gpm": c["served_demand_mean_gpm"],
                    "unserved_demand_mean_gpm": c["unserved_demand_mean_gpm"],
                    "dsr_mean": c["dsr_mean"],
                    "dsr_min": c["dsr_min"],
                    "n_node_timesteps_below_20psi": c["n_node_timesteps_below_20psi"],
                    "n_node_timesteps_negative_pressure":
                        c["n_node_timesteps_negative_pressure"],
                    "valve179_mean_flow_gpm": c["valve_flow_mean_gpm"]["VALVE-179"],
                    "engine_vs_modelled_leak_max_abs_gpm":
                        c["engine_vs_modelled_leak_max_abs_gpm"],
                    "continuity_residual_max_abs_gpm": c["continuity_residual_max_abs_gpm"],
                    "continuity_residual_rel_max": c["continuity_residual_rel_max"],
                    "volume_in_Mgal": c["volume_in_Mgal"],
                    "volume_served_Mgal": c["volume_served_Mgal"],
                    "volume_leaked_Mgal": c["volume_leaked_Mgal"],
                    "volume_into_tanks_Mgal": c["volume_into_tanks_Mgal"],
                })
        return out

    def monotone_in_observed_pressure(rs: list[dict], field: str,
                                     tol: float = 0.0) -> dict:
        """Is `field` non-decreasing when the cases are ordered by observed pressure?

        Ordering by the observed pressure rather than by the commanded PRV scale is
        the only way to test the physical claim. A perturbation is not guaranteed to
        move pressure in the intended direction - scaling every PRV up by 1.25
        reopens VALVE-179 and lowers pressure - and testing against the commanded
        scale would then score correct physics as a failure.

        This test is reported but is NOT the decision criterion. The mean junction
        pressure is not a sufficient statistic for total leakage: leakage is
        sum_j C_j * p_j^alpha with alpha < 1, so two states with the same mean
        pressure but different spatial distributions leak different amounts. The
        decision criterion is the pressure-dominance test below.
        """
        srt = sorted(rs, key=lambda r: r["mean_junction_pressure_psi"])
        vals = [r[field] for r in srt]
        viol = [{"from": srt[i]["prv_scale"], "to": srt[i + 1]["prv_scale"],
                 "family_from": srt[i]["family"], "family_to": srt[i + 1]["family"],
                 "p_from": srt[i]["mean_junction_pressure_psi"],
                 "p_to": srt[i + 1]["mean_junction_pressure_psi"],
                 "v_from": vals[i], "v_to": vals[i + 1]}
                for i in range(len(vals) - 1) if vals[i + 1] < vals[i] - tol]
        return {
            "ordered_by": "observed mean junction pressure over 96 h",
            "pressure_ladder_psi": [r["mean_junction_pressure_psi"] for r in srt],
            "field_along_ladder": vals,
            "monotone_non_decreasing": not viol,
            "violations": viol,
            "caveat": ("Mean pressure is not a sufficient statistic for total "
                       "leakage; see the dominance test."),
        }

    def dominance_test(model: str, field: str, *, p_tol: float = 0.05,
                       v_tol: float = 0.01) -> dict:
        """Monotonicity under nodal pressure dominance - the decision criterion.

        Case X is dominated by case Y when the 96 h mean pressure at EVERY junction
        satisfies p_j(X) <= p_j(Y) + p_tol, with at least one junction strictly
        lower. That is a partial order, not a total one: two perturbations can each
        raise pressure at some nodes and lower it at others, in which case they are
        simply not comparable and no monotonicity claim applies to that pair.

        The physical claim under test - lower pressure everywhere gives less
        leakage, higher pressure everywhere gives more - is exactly a statement
        about comparable pairs. Testing it on a scalar summary instead would either
        pass or fail for reasons that have nothing to do with the leakage law.
        """
        keys = ([(f"{model}_leak_prv{s:.2f}", "A_all_prv", s) for s in PRV_SCALES]
                + [(f"{model}_leak_actv{s:.2f}", "B_active_prv_only", s)
                   for s in ACTIVE_ONLY_SCALES])
        pairs, viol, incomp = [], [], []
        for kx, fx, sx in keys:
            for ky, fy, sy in keys:
                if kx == ky:
                    continue
                px = cases[kx]["mean_pressure_by_node_psi"]
                py = cases[ky]["mean_pressure_by_node_psi"]
                le = all(px[j] <= py[j] + p_tol for j in px)
                strict = any(px[j] < py[j] - p_tol for j in px)
                if not (le and strict):
                    continue
                vx, vy = cases[kx][field], cases[ky][field]
                rec = {"lower": f"{fx} x{sx:.2f}", "higher": f"{fy} x{sy:.2f}",
                       "n_junctions": len(px),
                       "mean_p_lower": cases[kx]["mean_junction_pressure_psi"],
                       "mean_p_higher": cases[ky]["mean_junction_pressure_psi"],
                       f"{field}_lower": vx, f"{field}_higher": vy,
                       "ok": bool(vx <= vy + v_tol)}
                pairs.append(rec)
                if not rec["ok"]:
                    viol.append(rec)
        for kx, fx, sx in keys:
            comparable = any(f"{fx} x{sx:.2f}" in (p["lower"], p["higher"])
                             for p in pairs)
            if comparable:
                continue
            px = cases[kx]["mean_pressure_by_node_psi"]
            near = []
            for ky, fy, sy in keys:
                if kx == ky:
                    continue
                py = cases[ky]["mean_pressure_by_node_psi"]
                hi = [j for j in px if px[j] > py[j] + p_tol]
                lo = [j for j in px if px[j] < py[j] - p_tol]
                diff = {j: px[j] - py[j] for j in px}
                near.append({
                    "vs": f"{fy} x{sy:.2f}",
                    "n_junctions_higher_in_this_case": len(hi),
                    "n_junctions_lower_in_this_case": len(lo),
                    "example_higher": sorted(hi)[:3],
                    "example_lower": sorted(lo)[:3],
                    "max_rise_psi": max(diff.values()),
                    "max_drop_psi": min(diff.values()),
                    "junction_of_max_drop": min(diff, key=diff.get),
                })
            incomp.append({
                "case": f"{fx} x{sx:.2f}",
                "mean_pressure_psi": cases[kx]["mean_junction_pressure_psi"],
                "min_pressure_psi": min(
                    cases[kx]["min_pressure_by_node_psi"].values()),
                "reason": ("raises pressure at some junctions and lowers it at "
                           "others relative to every other case, so it is not "
                           "comparable under the partial order"),
                "pairwise_breakdown": near,
            })
        return {
            "field": field,
            "pressure_tolerance_psi": p_tol,
            "value_tolerance": v_tol,
            "n_comparable_ordered_pairs": len(pairs),
            "pairs": pairs,
            "violations": viol,
            "monotone_on_all_comparable_pairs": not viol,
            "cases_not_comparable_with_any_other": incomp,
        }

    def dominance_tolerance_sweep(model: str, field: str, v_tol: float) -> list[dict]:
        """Is the dominance verdict an artefact of the 0.05 psi tolerance?

        A larger tolerance admits more pairs as comparable and therefore gives the
        monotonicity claim more chances to fail. Reporting the whole sweep, rather
        than a single tolerance, is what makes the verdict falsifiable: if the claim
        only held at one tolerance it would be a tuned result, not a physical one.
        """
        out = []
        for p_tol in (0.05, 0.10, 0.25, 0.50, 1.00, 2.00):
            d = dominance_test(model, field, p_tol=p_tol, v_tol=v_tol)
            out.append({
                "pressure_tolerance_psi": p_tol,
                "n_comparable_ordered_pairs": d["n_comparable_ordered_pairs"],
                "n_violations": len(d["violations"]),
                "monotone_on_all_comparable_pairs":
                    d["monotone_on_all_comparable_pairs"],
                "violations": d["violations"],
            })
        return out

    dda_rows, pda_rows = rows("DDA"), rows("PDA")
    a_rows = [r for r in dda_rows if r["family"] == "A_all_prv"]
    press_a = [r["mean_junction_pressure_psi"] for r in a_rows]
    v179 = {f'x{r["prv_scale"]:.2f}': r["valve179_mean_flow_gpm"] for r in a_rows}
    g6 = {
        "sweep_dda_leak": dda_rows,
        "commanded_scale_raises_pressure_family_A": all(
            press_a[i] < press_a[i + 1] for i in range(len(press_a) - 1)),
        "leakage_monotone_in_observed_pressure":
            monotone_in_observed_pressure(dda_rows, "leakage_mean_gpm"),
        "leakage_monotone_under_pressure_dominance":
            dominance_test("DDA", "leakage_mean_gpm"),
        "leakage_dominance_tolerance_sweep":
            dominance_tolerance_sweep("DDA", "leakage_mean_gpm", 0.01),
        "leakage_at_nominal_gpm": next(
            r["leakage_mean_gpm"] for r in a_rows if r["prv_scale"] == 1.0),
        "leakage_share_at_nominal_pct": next(
            r["leakage_share_of_inflow_pct"] for r in a_rows if r["prv_scale"] == 1.0),
        "service_invariant_under_dda": all(abs(r["dsr_mean"] - 1.0) < 1e-4
                                          for r in dda_rows),
        "max_dsr_deviation_under_dda": max(abs(r["dsr_mean"] - 1.0) for r in dda_rows),
        "engine_vs_modelled_leak_max_abs_gpm": max(
            r["engine_vs_modelled_leak_max_abs_gpm"] or 0.0 for r in dda_rows),
        "valve179_mean_flow_by_scale_gpm": v179,
        "confound_disclosed": {
            "id": "X1-valve179-reopens-at-scale-1.25",
            "observation": ("Scaling all eight PRV settings to 1.25 of nominal raises "
                            "VALVE-179 from 40 to 50 psi, which is inside the 50-70 psi "
                            "band in which G4 found it regulates. It stops being shut by "
                            "the hydraulics and starts passing flow, which lowers mean "
                            "network pressure below the nominal case instead of raising "
                            "it."),
            "evidence": v179,
            "handling": ("The case is kept in the record in full. Monotonicity is "
                         "tested against the observed pressure, and family B scales "
                         "only the four baseline-regulating PRVs so that a clean "
                         "high-pressure ladder also exists. No case was deleted."),
        },
        "note": ("Under DDA the served demand is fixed by construction, so every "
                 "change in system inflow across this sweep is leakage and nothing "
                 "else. That is why the leakage law is validated under DDA first "
                 "and only then combined with PDA."),
        "decision_criterion": (
            "The gate is decided on leakage_monotone_under_pressure_dominance, not "
            "on the mean-pressure ordering. Total leakage is sum_j C_j*sign(p_j)*"
            "|p_j|^0.5, which is not a function of mean(p): a case that lowers "
            "pressure at some junctions while raising it at others can leak either "
            "more or less than a case with the same mean, so the mean-pressure "
            "ordering can fail while the leakage law is exactly right. The "
            "dominance test compares only cases whose 96 h mean pressure is "
            "ordered at EVERY junction, which is the pair set the physical claim "
            "actually covers. The mean-pressure result is retained above."),
    }

    dda_n, pda_n = cases["DDA_noleak_nominal"], cases["PDA_noleak_nominal"]
    g7 = {
        "pda_option_in_echoed_inp": pda_n["echo_check"]["options_relevant"],
        "dda_option_in_echoed_inp": dda_n["echo_check"]["options_relevant"],
        "required_pressure_psi": PDA_REQUIRED_PSI,
        "minimum_pressure_psi": PDA_MINIMUM_PSI,
        "pressure_exponent": PDA_EXPONENT,
        "threshold_provenance": (
            "20 psi required / 0 psi minimum / exponent 0.5 is the author's "
            "validation choice, not a value taken from BWSN documentation. "
            "Whether the BWSN-1 problem statement declares a service pressure "
            "threshold is UNKNOWN - not checked in this phase."),
        "dda_noleak_dsr_mean": dda_n["dsr_mean"],
        "pda_noleak_dsr_mean": pda_n["dsr_mean"],
        "pda_noleak_dsr_min": pda_n["dsr_min"],
        "pda_noleak_unserved_max_gpm": pda_n["unserved_demand_max_gpm"],
        "pda_noleak_timesteps_curtailed": pda_n["n_timesteps_dsr_below_0p999"],
        "dda_delivers_requested_exactly": abs(dda_n["dsr_mean"] - 1.0) < 1e-4,
        "pda_curtails_at_nominal": pda_n["dsr_min"] < 0.999,
        "sweep_pda_leak": pda_rows,
        "dsr_monotone_in_observed_pressure":
            monotone_in_observed_pressure(pda_rows, "dsr_mean"),
        "dsr_monotone_under_pressure_dominance":
            dominance_test("PDA", "dsr_mean", v_tol=1e-4),
        "dsr_dominance_tolerance_sweep":
            dominance_tolerance_sweep("PDA", "dsr_mean", 1e-4),
        "perturbation_test": ("PRV settings are scaled deterministically: family A "
                             "scales all eight to 0.25/0.50/0.75/1.00/1.25 of nominal, "
                             "family B scales only the four baseline-regulating valves "
                             "to 1.10/1.25/1.50. Both are controlled perturbations, "
                             "not optimisations, and no valve is added, removed or "
                             "relocated in either."),
        "decision_criterion": (
            "Decided on dsr_monotone_under_pressure_dominance for the same reason "
            "as G6: delivered demand under PDA is a per-node function of the local "
            "pressure, so only cases ordered at every junction are comparable. The "
            "mean-pressure result is retained above."),
        "junctions_permanently_below_20psi_at_nominal": {
            "case": "PDA, leakage, all PRVs x1.00",
            "junctions": cases["PDA_leak_prv1.00"]
                              ["junctions_mean_pressure_below_20psi"],
            "n_node_timesteps_below_20psi":
                cases["PDA_leak_prv1.00"]["n_node_timesteps_below_20psi"],
            "n_reported_timesteps": 193,
            "reading": ("The count is an exact multiple of the 193 reported "
                        "timesteps, so these junctions are below the 20 psi "
                        "required pressure at every single timestep of the "
                        "distributed model, not transiently."),
        },
        "dsr_above_one_is_numerical": {
            "observation": ("Family B reports dsr_mean slightly above 1 "
                            "(unserved demand of about -0.06 GPM against 906.40 GPM "
                            "requested, i.e. 6.6e-5 relative)."),
            "explanation": ("PDA cannot deliver more than the requested demand. The "
                            "excess is the solver's convergence residual at "
                            "ACCURACY 1e-5, of the same order as the continuity "
                            "residual reported in G8. It is not over-delivery and "
                            "must not be read as one."),
        },
        "pda_feedback_disclosed": {
            "id": "X2-curtailment-raises-pressure-elsewhere",
            "observation": ("Under DDA, scaling all eight PRVs down to 0.25 lowers "
                            "the 96 h mean pressure at every junction. Under PDA it "
                            "does not: relative to the 0.75 case, 84 junctions sit "
                            "HIGHER and only 33 lower."),
            "explanation": ("PDA curtails demand where pressure is short of the 20 "
                            "psi requirement. Less water is withdrawn, so friction "
                            "losses fall and pressure recovers in parts of the "
                            "network even though every PRV setting was reduced. The "
                            "same perturbation therefore produces a different "
                            "pressure field under PDA than under DDA."),
            "consequence": ("Under PDA, pressure and delivered demand are coupled "
                            "in both directions, so only 3 of the 8 leakage cases "
                            "remain nodally comparable. A reward or state variable "
                            "built on mean pressure would mix a control effect with "
                            "a curtailment artefact. This is evidence about the "
                            "environment, not a thesis conclusion."),
        },
    }

    ref = next(r for r in pda_rows
               if r["family"] == "A_all_prv" and r["prv_scale"] == 1.0)
    sep = []
    for r in pda_rows:
        d_in = r["volume_in_Mgal"] - ref["volume_in_Mgal"]
        d_leak = r["volume_leaked_Mgal"] - ref["volume_leaked_Mgal"]
        d_srv = r["volume_served_Mgal"] - ref["volume_served_Mgal"]
        d_tank = r["volume_into_tanks_Mgal"] - ref["volume_into_tanks_Mgal"]
        sep.append({
            "family": r["family"],
            "prv_scale": r["prv_scale"],
            "mean_pressure_psi": r["mean_junction_pressure_psi"],
            "d_volume_in_Mgal": d_in,
            "d_volume_leaked_Mgal": d_leak,
            "d_volume_served_Mgal": d_srv,
            "d_volume_into_tanks_Mgal": d_tank,
            "closure_residual_Mgal": d_in - (d_leak + d_srv + d_tank),
            "leakage_saving_Mgal": -d_leak,
            "service_loss_Mgal": -d_srv,
            "pct_of_inflow_change_from_leakage": (
                None if abs(d_in) < 1e-12 else d_leak / d_in * 100.0),
            "pct_of_inflow_change_from_unserved_demand": (
                None if abs(d_in) < 1e-12 else d_srv / d_in * 100.0),
            "dsr_mean": r["dsr_mean"],
        })
    low = next(s for s in sep
               if s["family"] == "A_all_prv" and s["prv_scale"] == 0.25)
    g8 = {
        "reference_case": "PDA, leakage, all PRVs x1.00",
        "decomposition_vs_reference": sep,
        "low_pressure_case_prv_x0p25": low,
        "separable": bool(low["leakage_saving_Mgal"] > 0.0
                          and low["service_loss_Mgal"] > 0.0),
        "both_components_quantified": True,
        "max_abs_closure_residual_Mgal": max(abs(s["closure_residual_Mgal"]) for s in sep),
        "interpretation": (
            "Every volume is split into served demand, leakage and storage before "
            "any comparison is made, so a fall in system inflow can never be read "
            "as a leakage saving on its own. In the deepest perturbation both "
            "components move together, which is exactly the confound the gate "
            "exists to expose."),
    }

    closure = []
    for name, c in cases.items():
        r = (c["volume_in_Mgal"] - c["volume_served_Mgal"]
             - c["volume_leaked_Mgal"] - c["volume_into_tanks_Mgal"])
        closure.append({"case": name, "residual_Mgal": r,
                        "relative": abs(r) / c["volume_in_Mgal"],
                        "continuity_residual_rel_max": c["continuity_residual_rel_max"]})
    g8["per_case_volume_closure"] = closure
    g8["max_relative_volume_closure_error"] = max(x["relative"] for x in closure)

    n_emit = cases["DDA_leak_prv1.00"]["echo_check"]["n_emitter_lines"]
    share = g6["leakage_share_at_nominal_pct"]
    dsr_all = [r["dsr_mean"] for r in pda_rows]
    leak_law_exact = g6["engine_vs_modelled_leak_max_abs_gpm"] < 0.01
    g6_verdict = ("PASS" if (g6["leakage_monotone_under_pressure_dominance"]
                             ["monotone_on_all_comparable_pairs"]
                             and g6["leakage_monotone_under_pressure_dominance"]
                             ["n_comparable_ordered_pairs"] > 0
                             and g6["service_invariant_under_dda"]
                             and leak_law_exact
                             and n_emit == len(coeff) and 1.0 < share < 40.0)
                  else "FAIL")
    g7_verdict = ("PASS" if (g7["pda_option_in_echoed_inp"].get("DEMAND MODEL",
                                                                "").upper() == "PDA"
                             and g7["dda_delivers_requested_exactly"]
                             and min(dsr_all) < 0.999
                             and g7["dsr_monotone_under_pressure_dominance"]
                             ["monotone_on_all_comparable_pairs"]
                             and g7["dsr_monotone_under_pressure_dominance"]
                             ["n_comparable_ordered_pairs"] > 0)
                  else "FAIL")
    g8_verdict = ("PASS" if (g8["separable"]
                             and g8["max_relative_volume_closure_error"] < 1e-3)
                  else "FAIL")

    payload = {
        "gate": "G6+G7+G8",
        "title": "Leakage validation, PDA response, leakage/service separation",
        "env": C.env_info(),
        "method": {
            "leak_law": "q_leak = sign(p) * C * |p|^alpha at every junction, via [EMITTERS]",
            "alpha": LEAK_EXPONENT,
            "alpha_provenance": ("Taken from the distributed file's own [OPTIONS] "
                                 "Emitter Exponent 0.5, not invented here."),
            "signed_law_evidence": (
                "EPANET's emitter is a virtual pipe to a virtual reservoir and flows "
                "backwards at negative pressure. Verified at JUNCTION-126, "
                "p = -5.731 psi: engine -0.6416 GPM, signed law -0.6416 GPM, "
                "pressure-clipped law 0.0000 GPM."),
            "allocation": ("C_j proportional to half the incident pipe length at "
                           "junction j; deterministic, no random seed."),
            "calibration": sizing["closed_form"],
            "target_fraction_of_inflow": LEAK_TARGET_FRACTION,
            "validation_only": ("This coefficient set is a validation instrument. "
                                "It must not enter any thesis result and was not "
                                "optimised for any outcome."),
            "pda": {"required_psi": PDA_REQUIRED_PSI, "minimum_psi": PDA_MINIMUM_PSI,
                    "exponent": PDA_EXPONENT},
            "prv_scales_family_A_all_valves": PRV_SCALES,
            "prv_scales_family_B_active_valves_only": ACTIVE_ONLY_SCALES,
            "family_B_valves": ACTIVE_VALVES,
            "solver_settings": {
                "accuracy": SOLVER_ACCURACY,
                "trials": SOLVER_TRIALS,
                "file_declares": {"accuracy": 0.005, "trials": 40},
                "why": ("At the file's own ACCURACY 0.005 the engine returns a state "
                        "whose per-node emitter flow differs from C*p^alpha by up to "
                        "2.01 GPM and whose network continuity residual reaches 9.97 "
                        "GPM, with zero EPANET errors and zero warnings. At 1e-5 the "
                        "emitter law is reproduced to 0.0000 GPM and the residual "
                        "falls to 0.0004 GPM. TRIALS must rise with it: at 1e-5 with "
                        "only 200 trials the leak-free run halts at 19:00 h with "
                        "'System unbalanced'. This is a solver-tolerance change, not "
                        "a hydraulic or topological one."),
                "change_impact_on_leak_free_baseline": (
                    "mean junction pressure 103.8258 -> 103.8221 psi, min 4.224 -> "
                    "4.225 psi, pump switch counts identical (7 and 7), one timestep "
                    "at 62 h where PUMP-172 status differs, tank levels within "
                    "0.045 ft. Gates 1, 3, 4, 5 and 11 were run at the file's native "
                    "setting and their conclusions are unaffected."),
            },
            "accounting": ("EPANET reports emitter discharge inside nodal demand, so "
                           "leakage is recomputed from reported pressure with the "
                           "signed law and subtracted to obtain served demand. "
                           "Requested demand comes from wntr.metrics.expected_demand. "
                           "Under DDA the engine's own implied emitter flow "
                           "(reported demand - requested demand) is compared node by "
                           "node against the modelled law and the worst disagreement "
                           "is reported."),
        },
        "leak_sizing": {k: v for k, v in sizing.items()
                        if k != "coefficient_gpm_per_psi_alpha"},
        "leak_coefficients_gpm_per_psi_alpha": sizing["coefficient_gpm_per_psi_alpha"],
        "cases": cases,
        "gate6": g6,
        "gate7": g7,
        "gate8": g8,
        "verdicts": {
            "g6": f"G6 LEAKAGE MODEL VALIDATION = {g6_verdict}",
            "g7": f"G7 PDA RESPONSE = {g7_verdict}",
            "g8": f"G8 LEAKAGE/SERVICE SEPARATION = {g8_verdict}",
        },
    }
    C.jdump("g6_g7_g8_leak_pda.json", payload)

    print("\n--- G6 leakage law under DDA (service fixed by construction) ----")
    print(f"{'fam':>4} {'PRVx':>5} {'meanP':>8} {'minP':>8} {'leak_gpm':>9} {'%inflow':>8} "
          f"{'inflow':>9} {'served':>9} {'DSR':>8} {'lawerr':>7}")
    for r in dda_rows:
        print(f"{r['family'][0]:>4} {r['prv_scale']:5.2f} "
              f"{r['mean_junction_pressure_psi']:8.3f} "
              f"{r['min_junction_pressure_psi']:8.3f} {r['leakage_mean_gpm']:9.2f} "
              f"{r['leakage_share_of_inflow_pct']:8.3f} {r['system_inflow_mean_gpm']:9.2f} "
              f"{r['served_demand_mean_gpm']:9.2f} {r['dsr_mean']:8.5f} "
              f"{(r['engine_vs_modelled_leak_max_abs_gpm'] or 0.0):7.4f}")
    print(f"  emitter lines written to the echoed .inp: {n_emit} of {len(coeff)} junctions")
    print(f"  engine vs modelled leak, worst node over all DDA cases: "
          f"{g6['engine_vs_modelled_leak_max_abs_gpm']:.6f} GPM")
    print(f"  leakage monotone in observed mean pressure (reported, not the "
          f"criterion): "
          f"{g6['leakage_monotone_in_observed_pressure']['monotone_non_decreasing']}")
    dom6 = g6["leakage_monotone_under_pressure_dominance"]
    print(f"  DECISION: leakage monotone on all nodal-dominance pairs: "
          f"{dom6['monotone_on_all_comparable_pairs']} "
          f"({dom6['n_comparable_ordered_pairs']} comparable ordered pairs)")
    for p in dom6["pairs"]:
        print(f"    {p['lower']:>22} <= {p['higher']:<22} "
              f"leak {p['leakage_mean_gpm_lower']:8.2f} -> "
              f"{p['leakage_mean_gpm_higher']:8.2f}  "
              f"{'ok' if p['ok'] else 'VIOLATION'}")
    for c in dom6["cases_not_comparable_with_any_other"]:
        print(f"    not comparable: {c['case']} (meanP {c['mean_pressure_psi']:.3f}, "
              f"minP {c['min_pressure_psi']:.3f} psi)")
        for n in c["pairwise_breakdown"]:
            print(f"        vs {n['vs']:<24} higher at {n['n_junctions_higher_in_this_case']:3d}"
                  f"  lower at {n['n_junctions_lower_in_this_case']:3d} junctions"
                  f"  (max rise {n['max_rise_psi']:+8.3f}, max drop "
                  f"{n['max_drop_psi']:+8.4f} psi at {n['junction_of_max_drop']})")

    print(f"  VALVE-179 mean flow by family-A scale (GPM): {g6['valve179_mean_flow_by_scale_gpm']}")
    print("  dominance tolerance sweep (leakage): " + ", ".join(
        f"{s['pressure_tolerance_psi']:.2f}psi->{s['n_comparable_ordered_pairs']}pairs/"
        f"{s['n_violations']}viol" for s in g6["leakage_dominance_tolerance_sweep"]))
    print(f"  global k = {sizing['global_scale_k_gpm_per_ft_per_psi_alpha']:.6e} "
          f"GPM/(ft*psi^0.5), C range "
          f"{sizing['coefficient_min']:.5f}-{sizing['coefficient_max']:.5f}")

    print("\n--- G7 PDA response ---------------------------------------------")
    print(f"  echoed options (PDA run): {g7['pda_option_in_echoed_inp']}")
    print(f"  echoed options (DDA run): {g7['dda_option_in_echoed_inp']}")
    print(f"  DDA no-leak DSR mean = {dda_n['dsr_mean']:.8f} (must be 1)")
    print(f"  PDA no-leak DSR mean = {pda_n['dsr_mean']:.8f}  min = {pda_n['dsr_min']:.8f}  "
          f"curtailed timesteps = {pda_n['n_timesteps_dsr_below_0p999']}")
    print(f"{'fam':>4} {'PRVx':>5} {'meanP':>8} {'minP':>8} {'DSRmean':>9} {'DSRmin':>9} "
          f"{'unserved':>9} {'leak_gpm':>9} {'<20psi':>7} {'negP':>6}")
    for r in pda_rows:
        print(f"{r['family'][0]:>4} {r['prv_scale']:5.2f} "
              f"{r['mean_junction_pressure_psi']:8.3f} "
              f"{r['min_junction_pressure_psi']:8.3f} {r['dsr_mean']:9.5f} "
              f"{r['dsr_min']:9.5f} {r['unserved_demand_mean_gpm']:9.2f} "
              f"{r['leakage_mean_gpm']:9.2f} {r['n_node_timesteps_below_20psi']:7d} "
              f"{r['n_node_timesteps_negative_pressure']:6d}")
    print("  DSR monotone in observed mean pressure (reported, not the criterion): "
          f"{g7['dsr_monotone_in_observed_pressure']['monotone_non_decreasing']}")
    for v in g7['dsr_monotone_in_observed_pressure']['violations']:
        print(f"    violation: p {v['p_from']:.3f} -> {v['p_to']:.3f} psi, "
              f"DSR {v['v_from']:.5f} -> {v['v_to']:.5f} "
              f"({v['family_from']} x{v['from']:.2f} -> {v['family_to']} x{v['to']:.2f})")
    dom7 = g7["dsr_monotone_under_pressure_dominance"]
    print(f"  DECISION: DSR monotone on all nodal-dominance pairs: "
          f"{dom7['monotone_on_all_comparable_pairs']} "
          f"({dom7['n_comparable_ordered_pairs']} comparable ordered pairs)")
    for p in dom7["pairs"]:
        print(f"    {p['lower']:>22} <= {p['higher']:<22} "
              f"DSR {p['dsr_mean_lower']:9.5f} -> {p['dsr_mean_higher']:9.5f}  "
              f"{'ok' if p['ok'] else 'VIOLATION'}")
    for c in dom7["cases_not_comparable_with_any_other"]:
        print(f"    not comparable: {c['case']} (meanP {c['mean_pressure_psi']:.3f}, "
              f"minP {c['min_pressure_psi']:.3f} psi)")
        for n in c["pairwise_breakdown"]:
            print(f"        vs {n['vs']:<24} higher at {n['n_junctions_higher_in_this_case']:3d}"
                  f"  lower at {n['n_junctions_lower_in_this_case']:3d} junctions"
                  f"  (max rise {n['max_rise_psi']:+8.3f}, max drop "
                  f"{n['max_drop_psi']:+8.4f} psi at {n['junction_of_max_drop']})")

    subs = g7["junctions_permanently_below_20psi_at_nominal"]["junctions"]
    print("  dominance tolerance sweep (DSR): " + ", ".join(
        f"{s['pressure_tolerance_psi']:.2f}psi->{s['n_comparable_ordered_pairs']}pairs/"
        f"{s['n_violations']}viol" for s in g7["dsr_dominance_tolerance_sweep"]))
    print(f"  junctions with 96 h mean pressure below the 20 psi service threshold "
          f"at nominal PRVs: {len(subs)}")
    for j, d in subs.items():
        print(f"    {j}: mean {d['mean_psi']:.3f} psi, min {d['min_psi']:.3f} psi, "
              f"elevation {d['elevation_ft']:.2f} ft")

    print("\n--- G8 leakage vs service, 96 h volumes vs all-PRV x1.00 --------")
    print(f"{'fam':>4} {'PRVx':>5} {'dVin':>9} {'dVleak':>9} {'dVserved':>9} {'dVtank':>9} "
          f"{'resid':>10} {'%fromLeak':>10} {'%fromUnserved':>14}")
    for s in sep:
        fl = "-" if s["pct_of_inflow_change_from_leakage"] is None else \
            f"{s['pct_of_inflow_change_from_leakage']:10.2f}"
        fu = "-" if s["pct_of_inflow_change_from_unserved_demand"] is None else \
            f"{s['pct_of_inflow_change_from_unserved_demand']:14.2f}"
        print(f"{s['family'][0]:>4} {s['prv_scale']:5.2f} {s['d_volume_in_Mgal']:9.4f} "
              f"{s['d_volume_leaked_Mgal']:9.4f} {s['d_volume_served_Mgal']:9.4f} "
              f"{s['d_volume_into_tanks_Mgal']:9.4f} {s['closure_residual_Mgal']:10.2e} "
              f"{fl} {fu}")
    print(f"  max relative per-case volume closure error = "
          f"{g8['max_relative_volume_closure_error']:.3e}")
    print(f"  max relative instantaneous continuity residual across cases = "
          f"{max(x['continuity_residual_rel_max'] for x in closure):.3e}")

    for k in ("g6", "g7", "g8"):
        print(payload["verdicts"][k])
    return payload


if __name__ == "__main__":
    main()
