"""Gate 0 - file integrity and conformance with the Phase 4 report.

Checks the distributed model file against the element counts, element types and
timing options recorded in docs/phase4_decision_report.md. Discrepancies are
reported, never silently corrected.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_common as C  # noqa: E402

# Claims made in docs/phase4_decision_report.md about BWSN_Network_1.inp.
PHASE4_CLAIMS = {
    "junctions": 126,
    "reservoirs": 1,
    "tanks": 2,
    "pipes": 168,
    "pumps": 2,
    "valves": 8,
    "valve_types_all_prv": True,
    "pump_spec_mode": "HEAD",
    "duration_s": 96 * 3600,
    "hydraulic_timestep_s": 1800,
    "n_rules": 4,
    "n_controls": 1,
    "flow_units": "GPM",
    "headloss": "H-W",
    "emitters_empty": True,
    "n_patterns": 4,
    "pattern_entry_counts": [16, 16, 8, 16],
    "pattern_cycle_hours": 8.0,
    "prv_settings_psi": [70.0, 80.0, 55.0, 29.762, 45.0, 37.0, 40.0, 16.45],
    "global_efficiency_pct": 75.0,
    "global_price": 0.0,
    "n_curves": 3,
    "unused_curve": "CURVE-1",
}
REQUIRED_SECTIONS = [
    "TITLE", "JUNCTIONS", "RESERVOIRS", "TANKS", "PIPES", "PUMPS", "VALVES",
    "PATTERNS", "CURVES", "CONTROLS", "RULES", "ENERGY", "EMITTERS", "STATUS",
    "TIMES", "OPTIONS", "REPORT", "COORDINATES",
]


def _hms_to_s(tok: str) -> int:
    """EPANET time token -> seconds. Accepts H, H:MM and H:MM:SS."""
    parts = tok.split(":")
    if len(parts) == 1:
        return int(round(float(parts[0]) * 3600))
    if len(parts) == 2:
        return int(round(float(parts[0]) * 3600 + float(parts[1]) * 60))
    return int(round(float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])))


def raw_profile() -> dict:
    """Direct section counts from the distributed file. No solver involved."""
    sec = C.read_sections(C.ORIGINAL_INP)
    prof: dict = {"sections_present": sorted(sec.keys())}
    prof["sections_missing"] = [s for s in REQUIRED_SECTIONS if s not in sec]

    for key, name in [
        ("junctions", "JUNCTIONS"), ("reservoirs", "RESERVOIRS"),
        ("tanks", "TANKS"), ("pipes", "PIPES"), ("pumps", "PUMPS"),
        ("valves", "VALVES"), ("emitters", "EMITTERS"), ("status", "STATUS"),
        ("controls", "CONTROLS"), ("demands", "DEMANDS"),
    ]:
        prof[f"n_{key}"] = len(sec.get(name, []))

    prof["n_rules"] = sum(1 for ln in sec.get("RULES", [])
                          if ln.split()[0].upper() == "RULE")
    prof["rule_ids"] = [ln.split()[1] for ln in sec.get("RULES", [])
                        if ln.split()[0].upper() == "RULE"]
    prof["control_lines"] = list(sec.get("CONTROLS", []))

    # Valves: ID node1 node2 diam type setting minorloss
    prof["valves"] = [
        {"id": t[0], "from": t[1], "to": t[2], "diameter_in": float(t[3]),
         "type": t[4].upper(), "setting": float(t[5]),
         "minor_loss": float(t[6]) if len(t) > 6 else None}
        for t in (ln.split() for ln in sec.get("VALVES", []))
    ]
    prof["valve_types"] = sorted({v["type"] for v in prof["valves"]})

    # Pumps: ID node1 node2 KEYWORD VALUE [KEYWORD VALUE ...]
    pumps = []
    for ln in sec.get("PUMPS", []):
        t = ln.split()
        kv = {t[i].upper(): t[i + 1] for i in range(3, len(t) - 1, 2)}
        pumps.append({"id": t[0], "from": t[1], "to": t[2], "params": kv})
    prof["pumps"] = pumps
    prof["pump_spec_modes"] = sorted({k for p in pumps for k in p["params"]})

    curves: dict[str, list] = {}
    for ln in sec.get("CURVES", []):
        t = ln.split()
        curves.setdefault(t[0], []).append((float(t[1]), float(t[2])))
    prof["curves"] = {k: v for k, v in curves.items()}
    prof["n_curves"] = len(curves)
    referenced = {p["params"].get("HEAD") for p in pumps if "HEAD" in p["params"]}
    prof["curves_referenced_by_pumps"] = sorted(x for x in referenced if x)
    prof["curves_unreferenced"] = sorted(set(curves) - referenced)

    pats: dict[str, list] = {}
    for ln in sec.get("PATTERNS", []):
        t = ln.split()
        pats.setdefault(t[0], []).extend(float(x) for x in t[1:])
    prof["n_patterns"] = len(pats)
    prof["pattern_line_counts"] = {
        k: sum(1 for ln in sec.get("PATTERNS", []) if ln.split()[0] == k) for k in pats
    }
    prof["pattern_multiplier_counts"] = {k: len(v) for k, v in pats.items()}
    prof["pattern_extremes"] = {k: [min(v), max(v)] for k, v in pats.items()}
    prof["patterns"] = pats
    return prof, sec
def options_and_times(sec: dict) -> dict:
    """[TIMES] and [OPTIONS] as declared in the file, plus derived seconds."""
    times_raw, opts_raw = {}, {}
    for ln in sec.get("TIMES", []):
        t = ln.split()
        if len(t) >= 2 and t[0].upper() in ("HYDRAULIC", "QUALITY", "PATTERN",
                                            "REPORT", "RULE"):
            times_raw[f"{t[0]} {t[1]}".upper()] = " ".join(t[2:])
        elif len(t) >= 2:
            times_raw[t[0].upper()] = " ".join(t[1:])
    for ln in sec.get("OPTIONS", []):
        t = ln.split()
        if len(t) >= 2 and t[0].upper() in ("DEMAND", "EMITTER"):
            opts_raw[f"{t[0]} {t[1]}".upper()] = " ".join(t[2:])
        elif len(t) >= 2:
            opts_raw[t[0].upper()] = " ".join(t[1:])

    out = {"times_raw": times_raw, "options_raw": opts_raw}
    out["duration_s"] = _hms_to_s(times_raw["DURATION"]) if "DURATION" in times_raw else None
    out["hydraulic_timestep_s"] = (
        _hms_to_s(times_raw["HYDRAULIC TIMESTEP"]) if "HYDRAULIC TIMESTEP" in times_raw else None
    )
    out["pattern_timestep_s"] = (
        _hms_to_s(times_raw["PATTERN TIMESTEP"]) if "PATTERN TIMESTEP" in times_raw else None
    )
    out["report_timestep_s"] = (
        _hms_to_s(times_raw["REPORT TIMESTEP"]) if "REPORT TIMESTEP" in times_raw else None
    )
    out["rule_timestep_declared"] = "RULE TIMESTEP" in times_raw
    out["flow_units"] = opts_raw.get("UNITS")
    out["headloss"] = opts_raw.get("HEADLOSS")
    out["demand_model_declared"] = opts_raw.get("DEMAND MODEL")
    out["emitter_exponent"] = (
        float(opts_raw["EMITTER EXPONENT"]) if "EMITTER EXPONENT" in opts_raw else None
    )
    energy = {}
    for ln in sec.get("ENERGY", []):
        t = ln.split()
        if len(t) >= 3 and t[0].upper() == "GLOBAL":
            energy[t[1].upper()] = t[2]
    out["energy_global"] = energy
    return out


def demand_profile(sec: dict, patterns: dict) -> dict:
    """Base demands and pattern usage. Establishes which patterns are live."""
    usage: dict[str, dict] = {}
    total = 0.0
    n_zero = 0
    for ln in sec.get("JUNCTIONS", []):
        t = ln.split()
        d = float(t[2]) if len(t) > 2 else 0.0
        pat = t[3] if len(t) > 3 else "<none>"
        total += d
        if d == 0.0:
            n_zero += 1
        u = usage.setdefault(pat, {"n_junctions": 0, "base_demand_gpm": 0.0})
        u["n_junctions"] += 1
        u["base_demand_gpm"] += d
    return {
        "total_base_demand_gpm": round(total, 6),
        "n_zero_demand_junctions": n_zero,
        "pattern_usage_junctions": usage,
        "n_demands_section_rows": len(sec.get("DEMANDS", [])),
        "patterns_never_used": sorted(set(patterns) - set(usage)),
    }


def parse_checks() -> dict:
    """Can each engine read the file? Native EPANET vs WNTR are both recorded."""
    out = {}
    try:
        import contextlib
        import io as _io

        from epyt import epanet

        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            d = epanet(str(C.ORIGINAL_INP))
            out["epanet_native_original"] = {
                "parsed": True,
                "engine_version": d.getVersion(),
                "n_nodes": int(d.getNodeCount()),
                "n_links": int(d.getLinkCount()),
                "rule_timestep_s": float(d.getTimeRuleControlStep()),
            }
            d.unload()
    except Exception as exc:
        out["epanet_native_original"] = {"parsed": False, "error": f"{type(exc).__name__}: {exc}"}

    for label, path in [("wntr_original", C.ORIGINAL_INP), ("wntr_working", C.WORKING_INP)]:
        try:
            import warnings as _w

            import wntr

            with _w.catch_warnings(record=True) as caught:
                _w.simplefilter("always")
                wn = wntr.network.WaterNetworkModel(str(path))
            out[label] = {
                "parsed": True,
                "n_junctions": len(wn.junction_name_list),
                "n_pipes": len(wn.pipe_name_list),
                "n_pumps": len(wn.pump_name_list),
                "n_valves": len(wn.valve_name_list),
                "n_tanks": len(wn.tank_name_list),
                "n_reservoirs": len(wn.reservoir_name_list),
                "rule_timestep_s_default": wn.options.time.rule_timestep,
                "warnings": sorted({f"{c.category.__name__}: {c.message}" for c in caught}),
            }
        except Exception as exc:
            out[label] = {"parsed": False, "error": f"{type(exc).__name__}: {exc}"}
    return out
def compare(prof: dict, ot: dict, dem: dict) -> tuple[list, list]:
    """Compare observed file content with the Phase 4 report's claims.

    Returns (structural_checks, documentation_discrepancies). A structural check
    failing means the file is not the revision Phase 4 described. A documentation
    discrepancy means the file is fine but the Phase 4 prose is wrong.
    """
    P = PHASE4_CLAIMS
    prv = [v for v in prof["valves"] if v["type"] == "PRV"]
    structural = [
        ("junction count", P["junctions"], prof["n_junctions"]),
        ("reservoir count", P["reservoirs"], prof["n_reservoirs"]),
        ("tank count", P["tanks"], prof["n_tanks"]),
        ("pipe count", P["pipes"], prof["n_pipes"]),
        ("pump count", P["pumps"], prof["n_pumps"]),
        ("valve count", P["valves"], prof["n_valves"]),
        ("all valves are PRV", True, prof["valve_types"] == ["PRV"] and len(prv) == 8),
        ("pump spec mode is HEAD", ["HEAD"], prof["pump_spec_modes"]),
        ("pump head curves present",
         sorted(prof["curves_referenced_by_pumps"]),
         sorted(c for c in prof["curves_referenced_by_pumps"] if c in prof["curves"])),
        ("curve count", P["n_curves"], prof["n_curves"]),
        ("unused curve", [P["unused_curve"]], prof["curves_unreferenced"]),
        ("[RULES] count", P["n_rules"], prof["n_rules"]),
        ("[CONTROLS] count", P["n_controls"], prof["n_controls"]),
        ("duration (s)", P["duration_s"], ot["duration_s"]),
        ("hydraulic timestep (s)", P["hydraulic_timestep_s"], ot["hydraulic_timestep_s"]),
        ("flow units", P["flow_units"], ot["flow_units"]),
        ("headloss formula", P["headloss"], ot["headloss"]),
        ("[EMITTERS] empty", True, prof["n_emitters"] == 0),
        ("pattern count", P["n_patterns"], prof["n_patterns"]),
        ("PRV settings (psi)", P["prv_settings_psi"], [v["setting"] for v in prv]),
        ("global efficiency (%)", P["global_efficiency_pct"],
         float(ot["energy_global"].get("EFFICIENCY", "nan"))),
        ("global price", P["global_price"], float(ot["energy_global"].get("PRICE", "nan"))),
    ]
    checks = [
        {"item": name, "phase4_claim": exp, "observed": obs, "match": exp == obs}
        for name, exp, obs in structural
    ]

    obs_mult = prof["pattern_multiplier_counts"]
    obs_lines = prof["pattern_line_counts"]
    pat_step_h = (ot["pattern_timestep_s"] or 0) / 3600.0
    disc = []
    if list(obs_mult.values()) != P["pattern_entry_counts"]:
        disc.append({
            "id": "D1-pattern-length",
            "phase4_text": ("'Demand patterns: 4 patterns, 16 / 16 / 8 / 16 entries at a "
                            "0:30 pattern step, i.e. an 8-hour cycle repeated over the 96 h "
                            "horizon.'"),
            "observed": {
                "lines_per_pattern": obs_lines,
                "multipliers_per_pattern": obs_mult,
                "pattern_timestep_h": pat_step_h,
                "cycle_hours_per_pattern": {k: v * pat_step_h for k, v in obs_mult.items()},
            },
            "explanation": ("Phase 4 counted [PATTERNS] *lines*, not multipliers. Each line "
                            "carries 6 multipliers, so the true lengths are 96/96/48/96 "
                            "multipliers = 48 h / 48 h / 24 h / 48 h cycles, not 8 h."),
            "consequence": ("The Phase 4 inference 'BWSN-1's native demand patterns are "
                            "unrealistically short-cycle' is not supported by the file and "
                            "must be retracted. No file change is required."),
            "silent_correction": False,
        })
    if dem["patterns_never_used"]:
        disc.append({
            "id": "D2-dead-patterns",
            "phase4_text": "Phase 4 reports 4 demand patterns without noting that some are unused.",
            "observed": {"patterns_never_referenced_by_any_junction": dem["patterns_never_used"],
                         "pattern_usage": dem["pattern_usage_junctions"]},
            "explanation": ("Only PATTERN-0 and PATTERN-1 are referenced in [JUNCTIONS]. "
                            "The remaining patterns are dead data, analogous to the unused "
                            "CURVE-1 that Phase 4 did record."),
            "consequence": ("The effective native demand model is one 96-multiplier profile "
                            "(PATTERN-0) driving nearly all demand. Relevant to how the "
                            "thesis demand model replaces it."),
            "silent_correction": False,
        })
    if not ot["rule_timestep_declared"]:
        disc.append({
            "id": "D3-rule-timestep-engine-divergence",
            "phase4_text": "Not mentioned in Phase 4.",
            "observed": {"rule_timestep_in_TIMES": None,
                         "epanet_native_default_s": (ot["hydraulic_timestep_s"] or 0) / 10,
                         "wntr_default_s": 360},
            "explanation": ("[TIMES] declares no rule timestep. Native EPANET defaults to "
                            "hydraulic/10 = 180 s; WNTR's WaterNetworkModel defaults to 360 s. "
                            "An unmodified WNTR run therefore evaluates the tank-level pump "
                            "rules at half the native frequency."),
            "consequence": ("Every Phase 5 run sets rule_timestep = 180 s explicitly so that "
                            "WNTR reproduces native EPANET rule behaviour."),
            "silent_correction": False,
        })
    if ot["report_timestep_s"] != ot["hydraulic_timestep_s"]:
        disc.append({
            "id": "D4-report-vs-hydraulic-timestep",
            "phase4_text": "Not mentioned in Phase 4.",
            "observed": {"hydraulic_timestep_s": ot["hydraulic_timestep_s"],
                         "report_timestep_s": ot["report_timestep_s"],
                         "reported_points_over_96h": int(
                             (ot["duration_s"] or 0) / (ot["report_timestep_s"] or 1)) + 1,
                         "solved_points_over_96h": int(
                             (ot["duration_s"] or 0) / (ot["hydraulic_timestep_s"] or 1)) + 1},
            "explanation": ("The file solves every 0:30 but reports every 1:00, so half the "
                            "solved states are never returned to the caller."),
            "consequence": ("Any RL environment reading results at the reporting resolution "
                            "would silently see a 1 h control interval. Belongs in 'Exact "
                            "Changes Required Before RL'."),
            "silent_correction": False,
        })
    return checks, disc
def main() -> dict:
    rec = C.build_working_copy(verbose=False)
    prof, sec = raw_profile()
    ot = options_and_times(sec)
    dem = demand_profile(sec, prof["patterns"])
    parses = parse_checks()
    checks, disc = compare(prof, ot, dem)

    parse_ok = (parses.get("epanet_native_original", {}).get("parsed") is True
                and parses.get("wntr_working", {}).get("parsed") is True)
    sections_ok = not prof["sections_missing"]
    counts_ok = all(c["match"] for c in checks)
    verdict = "PASS" if (parse_ok and sections_ok and counts_ok) else "FAIL"
    conformance = "FULL" if not disc else "PARTIAL - see documentation_discrepancies"

    payload = {
        "gate": "G0",
        "title": "File integrity and Phase 4 conformance",
        "env": C.env_info(),
        "provenance": rec["provenance"],
        "patches_applied": [p["id"] for p in rec["patches_applied"]],
        "original_sha256": rec["original_sha256"],
        "working_sha256": rec["working_sha256"],
        "raw_profile": prof,
        "options_and_times": ot,
        "demand_profile": dem,
        "parse_checks": parses,
        "phase4_structural_checks": checks,
        "documentation_discrepancies": disc,
        "sub_verdicts": {
            "parseable_native_epanet": parses.get("epanet_native_original", {}).get("parsed"),
            "parseable_wntr_original": parses.get("wntr_original", {}).get("parsed"),
            "parseable_wntr_working": parses.get("wntr_working", {}).get("parsed"),
            "all_required_sections_present": sections_ok,
            "all_phase4_structural_claims_match": counts_ok,
            "phase4_documentation_conformance": conformance,
        },
        "verdict": f"G0 FILE INTEGRITY = {verdict}",
    }
    C.jdump("g0_integrity.json", payload)

    print("\n--- structural checks vs Phase 4 -------------------------------")
    for c in checks:
        flag = "ok " if c["match"] else "MISMATCH"
        print(f"  [{flag}] {c['item']}: claim={c['phase4_claim']!r} observed={c['observed']!r}")
    print("\n--- documentation discrepancies (reported, not corrected) ------")
    for d in disc:
        print(f"  {d['id']}: {d['explanation']}")
    print(f"\nsections missing: {prof['sections_missing'] or 'none'}")
    print(f"parse native EPANET: {parses.get('epanet_native_original', {}).get('parsed')}")
    print(f"parse WNTR original: {parses.get('wntr_original', {}).get('parsed')}")
    print(f"parse WNTR working : {parses.get('wntr_working', {}).get('parsed')}")
    print(f"\n{payload['verdict']}")
    print(f"G0 PHASE4 DOCUMENTATION CONFORMANCE = {conformance}")
    return payload


if __name__ == "__main__":
    main()




