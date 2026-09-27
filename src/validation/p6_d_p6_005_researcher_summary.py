#!/usr/bin/env python3
"""WU-12 — researcher-facing decision presentation for D-P6-005.

PURE re-shaping of the WU-11 decision brief
(results/phase6/p6_d_p6_005_decision_brief.json) into a concise, decision-ready
researcher summary. This script:

  * measures NOTHING new (no EPANET, no PPO, no RNG, no re-run);
  * copies every numeric value verbatim from the decision brief, so the summary
    cannot drift from the evidence;
  * does NOT select, score, rank, recommend, or declare a winner among F1-F4 or
    among the candidates C-A/C-B/C-C/C-D;
  * keeps researcher_selection = null.

Deterministic: re-running byte-reproduces
results/phase6/p6_d_p6_005_researcher_summary.json.

The only AUTHORED content here is plain-language (Persian) interpretation and
short descriptive notes for the decision dimensions / central trade-off. That
prose is clearly separated from the numeric fields and adds no new numbers.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "phase6"
BRIEF = RESULTS / "p6_d_p6_005_decision_brief.json"
OUT = RESULTS / "p6_d_p6_005_researcher_summary.json"

# ---------------------------------------------------------------------------
# AUTHORED interpretation (NOT measured data). Keyed by exact candidate_id.
# Persian plain-language answers to the four researcher questions:
#   q1: what does this reward actually encourage?
#   q2: pressure down + leak down but service worsens -> what happens to reward?
#   q3: pressure up -> what happens?
#   q4: agent changes its action a lot -> what happens?
# roles: exact treatment of effort / service-pressure / leakage.
# "NOT SPECIFIED IN SOURCE" is used where the brief does not define a term.
# ---------------------------------------------------------------------------
AUTHORED = {
    "C-A_F1_balanced_dense": {
        "plain_language_fa": {
            "q1_encourages": "کاهش همزمان نشت، کاهش تقاضای برآورده‌نشده (unserved) و کاهش کسری فشار (deficit)، به‌علاوه‌ی یک جریمه‌ی کوچک برای تغییرِ زیادِ عملگرها. هر چهار ترم با ثابت‌های ثابت‌شده‌ی WU-9 نرمال شده‌اند تا هم‌مقیاس باشند و وزن‌های ۱ نقطه‌ی شروعِ خنثی‌اند.",
            "q2_leak_down_service_down": "چون نشت و سرویس و فشار هر سه وزنِ ۱ دارند، بهبودِ نشت با بدترشدنِ سرویس و افزایش deficit خنثی یا حتی منفی می‌شود؛ پاداش لزوماً بهتر نمی‌شود.",
            "q3_pressure_up": "طبق شواهد (leak↔pressure)، بالا رفتنِ فشار نشت را زیاد می‌کند پس ترمِ نشت بدتر می‌شود، هرچند deficit و unserved بهتر می‌شوند؛ نتیجه‌ی خالص به تعادلِ وزن‌ها بستگی دارد.",
            "q4_action_moves_a_lot": "ترمِ w_A*(‖Δa‖²/28) با w_A=0.1 یک جریمه‌ی کوچک می‌گیرد؛ یک حرکتِ کاملِ کران‌به‌کران تقریباً هم‌اندازه‌ی کلِ دامنه‌ی تغییرِ نشت (~0.108) هزینه دارد، نه بیشتر.",
        },
        "actuator_effort_role": "w_A*(||da||^2 / 28) on the COMMANDED normalised action (never realised pump speed); w_A=0.1.",
        "service_pressure_treatment": "dense normalised pressure_deficit term (deficit/deficit_ref) with w_P=1, plus unserved^+ term with w_U=1; NO hard threshold term.",
        "leakage_treatment": "normalised absolute leakage leak/leak_ref with w_L=1.",
        "special_cases": "unserved clipped at >=0; da=0 for static holds; all denominators are fixed nonzero constants; energy term off (w_E=0).",
    },
    "C-B_F1_safety_leaning": {
        "plain_language_fa": {
            "q1_encourages": "همان C-A است ولی وزنِ فشار/deficit دو برابر (w_P=2) است؛ یعنی محافظت از بدترین گرهِ فشار پررنگ‌تر می‌شود. این فقط «تأکیدِ متفاوت» است، نه رتبه‌بندی نسبت به C-A.",
            "q2_leak_down_service_down": "چون وزنِ deficit بزرگ‌تر است، بدترشدنِ سرویس شدیدتر جریمه می‌شود؛ پس بهبودِ نشت به‌قیمتِ سرویس، پاداش را بیشتر از C-A پایین می‌آورد.",
            "q3_pressure_up": "مثل C-A نشت بالا می‌رود و ترمِ نشت بدتر می‌شود؛ اما چون deficit وزنِ ۲ دارد، بهبودِ فشار سهمِ مثبتِ بزرگ‌تری می‌گذارد.",
            "q4_action_moves_a_lot": "دقیقاً مثل C-A: جریمه‌ی کوچکِ w_A=0.1 روی ‖Δa‖²/28.",
        },
        "actuator_effort_role": "identical to C-A: w_A*(||da||^2 / 28) on COMMANDED action; w_A=0.1.",
        "service_pressure_treatment": "same dense deficit term as C-A but with heavier weight w_P=2 (still O(1) after normalisation); unserved^+ with w_U=1; NO hard threshold.",
        "leakage_treatment": "normalised absolute leakage leak/leak_ref with w_L=1.",
        "special_cases": "same as C-A (unserved^+ clipped; da=0 static; fixed denominators; w_E=0). Only difference vs C-A is w_P: 1 -> 2.",
    },
    "C-C_F3_baseline_relative": {
        "plain_language_fa": {
            "q1_encourages": "پاداش برابرِ «کسرِ کاهشِ نشت نسبت به کنترلرِ بومی» است، منهای جریمه برای unserved اضافه‌تر از خطِ پایه و جریمه‌ی deficit. یعنی مستقیماً «بهبود نسبت به baseline» را تشویق می‌کند و در نقطه‌ی کنترلرِ بومی صفر است.",
            "q2_leak_down_service_down": "اگر unserved از سطحِ baseline (~15.10 GPM) بیشتر شود جریمه می‌گیرد و ترمِ deficit هم جریمه دارد؛ پس بدترشدنِ سرویس، سودِ کاهشِ نشت را جبران/خنثی می‌کند.",
            "q3_pressure_up": "بالا رفتنِ فشار نشت را زیاد می‌کند، پس ترمِ بهبودِ نشت ((leak_ref-leak)/leak_ref) کوچک یا منفی می‌شود.",
            "q4_action_moves_a_lot": "NOT SPECIFIED IN SOURCE — خانواده‌ی F3 در منبع هیچ ترمِ حرکت/هموارسازیِ عملگر ندارد؛ تغییرِ زیادِ action مستقیماً جریمه نمی‌شود.",
        },
        "actuator_effort_role": "NOT SPECIFIED IN SOURCE (F3 family defines no actuator-movement / smoothness term).",
        "service_pressure_treatment": "excess-unserved penalty w_U*max(0, unserved - unserved_ref)/req_ref (only ABOVE baseline) plus dense deficit term w_P_safety*(deficit/deficit_ref).",
        "leakage_treatment": "fractional improvement vs native baseline (leak_ref - leak)/leak_ref; intrinsically normalised, zero-centred at the native controller; no separate leak weight.",
        "special_cases": "excess unserved clipped at >=0; unserved_ref = 15.103309701248634 GPM (DSR-implied baseline; the WU-9 accounting value is 14.98483697365873 GPM); NO hard threshold term.",
    },
    "C-D_dense_deficit_no_hard_count": {
        "plain_language_fa": {
            "q1_encourages": "کاهشِ نشت و کاهشِ deficit (سرویس)، با یک «دروازه‌ی سختِ» جریمه فقط برای فشارِ منفی. عمداً ترمِ سختِ «۲۰ psi» حذف شده چون روی خطِ پایه هم فعال می‌شود (ill-posed).",
            "q2_leak_down_service_down": "ترمِ deficit با وزنِ LAMBDA=5 جریمه می‌شود، پس بدترشدنِ سرویس پاداش را پایین می‌آورد؛ و اگر کنترلی گره‌ای را به فشارِ منفی ببرد جریمه‌ی بزرگِ BIG=100 فعال می‌شود.",
            "q3_pressure_up": "نشت بالا می‌رود پس ترمِ نشت (leak/leak_ref) بدتر می‌شود؛ ترمِ منفیِ سخت فعال نمی‌شود.",
            "q4_action_moves_a_lot": "NOT SPECIFIED IN SOURCE — این نسخه هیچ ترمِ حرکت/هموارسازی ندارد؛ تغییرِ زیادِ action مستقیماً جریمه نمی‌شود.",
        },
        "actuator_effort_role": "NOT SPECIFIED IN SOURCE (this dense-safety variant defines no actuator-movement term).",
        "service_pressure_treatment": "dense normalised deficit term LAMBDA*(deficit/deficit_ref) (LAMBDA=5) PLUS a hard gate BIG*max(0, n_negative) firing ONLY on negative-pressure nodes (baseline count 0).",
        "leakage_treatment": "normalised absolute leakage leak/leak_ref (unit implicit weight).",
        "special_cases": "REPLACES the ill-posed hard 20-psi count with dense deficit; hard term keyed on NEGATIVE nodes only (well-posed, baseline frac_negative=0.0); the 20-psi level appears only inside the smooth deficit = sum max(0, 20 - p_i), NOT as a hard gate.",
    },
}

# Short DESCRIPTIVE notes per decision dimension (evidence-grounded, no scores/ranks).
DIMENSION_NOTES = {
    "leakage_management_signal": "All candidates carry a leakage term; F1 family (C-A/C-B) and C-D use absolute normalised leak, F3 (C-C) uses fractional reduction vs baseline. Measured in-bounds leak span is small (~+/-6%, dynamic range ~0.108 across tested commands).",
    "service_preservation": "C-A/C-B/C-D protect service via a dense deficit term; C-C penalises unserved above baseline. Measured leak<->dsr +0.7497 and leak<->deficit -0.7735 show service and leakage genuinely oppose.",
    "pressure_safety_signal_density": "Dense channels (deficit, min-service-pressure) are active every timestep; the <0 psi hard channel is inactive in-bounds (frac_negative 0.0) and the <20 psi count is active at 100% of timesteps INCLUDING the native baseline.",
    "signal_density_dense_vs_sparse": "C-A/C-B/C-C/C-D rely on dense terms. Any hard-count term is sparse or (at 20 psi) degenerate on this network.",
    "scale_stability_fixed_normalisation": "Every candidate divides by the FROZEN WU-9 constants (leak_ref, req_ref, deficit_ref, movement_L2sq_max), so terms are O(1); raw penalty magnitudes otherwise span a ~7.15x ratio.",
    "interpretability_thesis_explainability": "C-C is directly interpretable as % leakage reduction vs the native controller; C-A/C-B as a normalised weighted cost; C-D as leak+dense-service with a negative-pressure backstop.",
    "parameter_count_and_sensitivity": "C-A/C-B expose {w_L,w_U,w_P,w_A} (w_E=0); C-C exposes {w_U,w_P_safety}; C-D exposes {LAMBDA,BIG}. Sweeps show the incentive-argmax shifts with these parameters (e.g. F1 w_P 0 -> prv_175_lower, >=0.5 -> prv_176_upper).",
    "reward_hacking_resistance": "Effort/smoothness MUST use the COMMANDED action (realised pump speed is reset by native STATUS rules); a hard 20-psi term is ill-posed; an F4-style 0-psi threshold never fires yet reports 'safe'.",
    "ppo_continuous_action_compatibility": "All candidates are finite and (for the dense F1/F3 forms) smooth/differentiable; F2/F4-style large penalties give high-variance returns (F2 pooled reward std ~42 vs F1 ~0.17).",
    "step9_safety_layer_compatibility": "No candidate enforces a pressure bound; the leak optimum sits on the PRV lower corner, so a STEP-9 state-dependent clamp is required regardless of the reward chosen. C-D's negative-node gate is complementary to, not a substitute for, STEP-9.",
    "reproducibility_no_leakage": "All constants are fixed (measured once, frozen), not per-episode running statistics; reference reproduces the frozen baseline exactly (leak_ref abs diff 0.0, per-timestep vs accounting 0.0).",
    "baseline_relatability": "C-C is zero-centred at the native controller (baseline-relative); C-A/C-B/C-D are absolute-cost forms whose values are read relative to the measured reference.",
}

CENTRAL_TRADEOFF_FA = (
    "چرا یک reward که با موفقیت نشت را کم می‌کند می‌تواند از نظر علمی برای این تز غلط باشد؟ "
    "شواهدِ اندازه‌گیری‌شده‌ی BWSN-1 نشان می‌دهد نشت و سرویس واقعاً در تضادند: هم‌بستگیِ "
    "leak<->dsr برابر +0.7497 و leak<->deficit برابر -0.7735 است، و بهینه‌ی «فقط-نشت» دقیقاً "
    "روی کرانِ پایینِ PRV می‌نشیند (prv_all_lower: نشت 84.73->81.38 GPM ولی dsr 0.98334->0.91940). "
    "یعنی یک reward که فقط نشت را می‌بیند، agent را به سمتِ پایین‌آوردنِ فشار می‌راند و سرویس را "
    "خراب می‌کند در حالی‌که عددِ نشت بهتر به‌نظر می‌رسد. افزون بر این، شبکه به‌طور مزمن در هر گامِ "
    "زمانی حداقل یک گرهِ سرویس زیرِ ۲۰ psi دارد (frac_ts_any_node_below_20psi = 1.0؛ min svc 4.16452 psi) "
    "ولی هیچ گرهِ منفی ندارد؛ پس یک قیدِ سختِ مطلقِ ۲۰ psi روی خودِ خطِ پایه هم فعال می‌شود و بد-تعریف است."
)

SEPARATION_FA = (
    "به همین دلیل «طراحیِ reward» (D-P6-005) و «مکانیزمِ ایمنیِ وابسته به وضعیت» (STEP-9) دو "
    "لایه‌ی جدا هستند: reward فقط رفتار را شکل می‌دهد و هیچ کرانِ فشاری را تضمین نمی‌کند؛ تضمینِ "
    "اجراییِ ۲۰ psi کارِ کلمپِ سطحِ اجرا در STEP-9 است. هیچ‌کدام از این دو لایه در این وظیفه پیاده‌سازی نمی‌شود."
)

import math

FORBIDDEN_KEY_TOKENS = ("winner", "rank", "tier", "score", "best",
                        "superior", "optimal", "preferred", "recommend")


def _iter_keys(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _iter_keys(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _iter_keys(x)


def _all_finite(obj):
    if isinstance(obj, bool):
        return True
    if isinstance(obj, (int, float)):
        return math.isfinite(obj)
    if isinstance(obj, dict):
        return all(_all_finite(v) for v in obj.values())
    if isinstance(obj, list):
        return all(_all_finite(x) for x in obj)
    return True


def _load_brief():
    with BRIEF.open(encoding="utf-8") as fh:
        return json.load(fh)


def build_summary(brief):
    """Re-shape the WU-11 brief into the researcher summary. Copies all numbers."""
    families = []
    for f in brief["candidate_formulations"]:
        entry = {
            "id": f["id"],
            "name": f["name"],
            "sign_convention": f["sign_convention"],
            "expression": f["expression"],
            "components": f["components"],
            "clipping": f["clipping"],
            "epsilon_handling": f["epsilon_handling"],
        }
        for opt in ("provisional_weights", "provisional_parameters", "baseline_constants"):
            if opt in f:
                entry[opt] = f[opt]
        families.append(entry)
    candidates = []
    cand_params = {}
    for c in brief["candidate_parameterizations"]:
        cid = c["candidate_id"]
        auth = AUTHORED[cid]
        candidates.append({
            "candidate_id": cid,
            "status": c["status"],
            "base_formulation": c["base_formulation"],
            "equation": c["equation"],
            "normalization_constants": c["constants"],
            "provisional_weights": c["provisional_weights"],
            "scale_derivation": c["scale_derivation"],
            "plain_language_fa": auth["plain_language_fa"],
            "actuator_effort_role": auth["actuator_effort_role"],
            "service_pressure_treatment": auth["service_pressure_treatment"],
            "leakage_treatment": auth["leakage_treatment"],
            "special_cases": auth["special_cases"],
            "evidence": {
                "observed": c["tradeoff"],
                "inferred": c["plausibility"],
                "unresolved_risk": c["risk"],
                "validation_experiment": c["validation_experiment"],
            },
        })
        cand_params[cid] = {
            "normalization_constants": c["constants"],
            "provisional_weights": c["provisional_weights"],
        }
    tradeoffs = {
        "central_tradeoff_fa": CENTRAL_TRADEOFF_FA,
        "layer_separation_fa": SEPARATION_FA,
        "decision_dimensions": {d: DIMENSION_NOTES[d] for d in brief["decision_dimensions"]},
        "measured_grounding": {
            "leak_vs_dsr_corr": 0.7497,
            "leak_vs_deficit_corr": -0.7735,
            "leak_vs_n_below20_corr": -0.7419,
            "dsr_vs_deficit_corr": -0.9653,
            "chronic_baseline_metrics": brief["chronic_baseline_service_issue"]["baseline_metrics"],
            "leak_only_optimum": "prv_all_lower: leak 84.73->81.38 GPM, dsr 0.98334->0.91940 (boundary-seeking at PRV lower corner)",
            "scale_imbalance_ratio": 7.145793,
            "leak_term_dynamic_range": 0.10788834247085066,
        },
    }
    summary = {
        "decision_id": brief["decision_id"],
        "current_status": brief["status"],
        "purpose": ("Researcher-facing decision presentation (WU-12). PURE re-shaping of the "
                    "WU-11 decision brief; measures nothing new; selects/scores/ranks/recommends "
                    "no formulation; researcher_selection stays null."),
        "generated_by": "src/validation/p6_d_p6_005_researcher_summary.py",
        "measures_nothing_new": True,
        "no_epanet_no_ppo_no_selection": True,
        "source_artifacts": dict(
            brief["evidence_artifacts"],
            wu11_decision_brief="results/phase6/p6_d_p6_005_decision_brief.json",
        ),
        "frozen_constraints_snapshot": brief["frozen_constraints"],
        "normalization_constants_frozen": brief["normalization_constants_frozen"],
        "formulation_families": families,
        "candidate_formulations": candidates,
        "candidate_parameters": cand_params,
        "evidence_references": {
            "wu9_scale_analysis": brief["evidence_artifacts"]["wu9_scale_analysis"],
            "wu10_formulation_comparison": brief["evidence_artifacts"]["wu10_formulation_comparison"],
            "wu11_decision_brief": "results/phase6/p6_d_p6_005_decision_brief.json",
            "reward_spec_doc": brief["evidence_artifacts"]["reward_spec_doc"],
            "action_space_spec_doc": brief["evidence_artifacts"]["action_space_spec_doc"],
            "state_spec": brief["evidence_artifacts"]["state_spec"],
        },
        "tradeoffs": tradeoffs,
        "uncertainties": brief["uncertainties"],
        "reproducibility": brief["reproducibility_information"],
        "researcher_selection": None,
    }
    summary["self_checks"] = _self_checks(summary, brief)
    return summary
def _candidates_match(summary, brief):
    """Every copied candidate number/equation must equal the WU-11 brief (anti-drift)."""
    by_id = {c["candidate_id"]: c for c in brief["candidate_parameterizations"]}
    for c in summary["candidate_formulations"]:
        src = by_id[c["candidate_id"]]
        if c["equation"] != src["equation"]:
            return False
        if c["normalization_constants"] != src["constants"]:
            return False
        if c["provisional_weights"] != src["provisional_weights"]:
            return False
        if c["base_formulation"] != src["base_formulation"]:
            return False
    return True


def _self_checks(summary, brief):
    cands = summary["candidate_formulations"]
    fc = summary["frozen_constraints_snapshot"]
    forbidden = [k for k in _iter_keys(summary)
                 if any(tok in k.lower() for tok in FORBIDDEN_KEY_TOKENS)]
    return {
        "status_is_proposed": summary["current_status"].startswith("PROPOSED"),
        "researcher_selection_is_null": summary["researcher_selection"] is None,
        "n_candidates_is_4": len(cands) == 4,
        "all_candidates_not_approved": all(
            c["status"] == "PROVISIONAL CANDIDATE - NOT APPROVED" for c in cands),
        "candidate_numbers_match_brief": _candidates_match(summary, brief),
        "no_forbidden_key_tokens": not forbidden,
        "action_dim_7": fc["action_space"]["action_dim"] == 7,
        "observation_dim_139": fc["observation"]["observation_dim"] == 139,
        "service_mask_121_5": (fc["service_node_policy"]["n_service_junctions"] == 121
                               and fc["service_node_policy"]["n_connector_junctions_excluded"] == 5),
        "constants_match_brief": (summary["normalization_constants_frozen"]
                                  == brief["normalization_constants_frozen"]),
        "all_values_finite": _all_finite(summary),
        "n_formulation_families_4": len(summary["formulation_families"]) == 4,
    }


def main():
    brief = _load_brief()
    summary = build_summary(brief)
    failed = [k for k, v in summary["self_checks"].items() if not v]
    if failed:
        raise SystemExit(f"self-checks failed: {failed}")
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(text)} bytes); self_checks all pass")


if __name__ == "__main__":
    main()
