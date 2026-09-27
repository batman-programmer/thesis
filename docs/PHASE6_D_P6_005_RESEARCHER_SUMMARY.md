# PHASE 6 — D-P6-005 Researcher Decision Summary (WU-12)

**Decision:** D-P6-005 (STEP 8 reward design — choose ONE formulation + parameters)
**Status:** `PROPOSED / DECISION PENDING RESEARCHER` — *not selected, not approved.*
**researcher_selection:** `null`
**Prepared:** 2026-09-27 · WU-12 · this file selects/scores/ranks/recommends **nothing**.

> This document is a **presentation** of already-persisted evidence. It measures
> nothing new (no EPANET, no PPO, no RNG). Every number is copied verbatim from
> the WU-11 decision brief. It exists only to let the researcher make an explicit
> D-P6-005 decision.

**Evidence chain:** WU-9 scale analysis
[`results/phase6/p6_s8_reward_scale_analysis.json`] → WU-10 formulation comparison
[`results/phase6/p6_s8_reward_formulation_comparison.json`] → WU-11 decision brief
[`results/phase6/p6_d_p6_005_decision_brief.json`] · spec `docs/PHASE6_REWARD_SPEC.md`
§8.1–§8.11 · machine mirror `results/phase6/p6_d_p6_005_researcher_summary.json`.

---

## A. Current state

- **STEP 5/6 action space** — D-P6-001/002/003 **APPROVED & FROZEN**. `action_dim=7`,
  absolute encoding `physical = lower + ((a+1)/2)*(upper-lower)`, box `[-1,1]^7`. Excluded
  valves {174, 179, 180} remain in the hydraulic model. **Unchanged by this task.**
- **STEP 7 observation** — D-P6-004 **APPROVED & FROZEN**. `observation_dim=139`, float32,
  reward must not modify state. **Unchanged by this task.**
- **STEP 8 reward** — measurement (WU-9), comparison (WU-10) and decision brief (WU-11)
  **COMPLETE**. Four PROVISIONAL candidate parameterizations exist as *evidence*.
  **No formulation is selected; no weights are chosen; researcher_selection is null.**
- **Frozen normalization constants** (measured once, no running statistics → no train/eval
  leakage): `leak_ref=84.72988433677985` GPM, `req_ref=906.3987348621764` GPM,
  `deficit_ref=28.671793365478514` psi·node-sum (= max(baseline mean, pooled p95)),
  `power_ref=88.10062475649187` kW, `movement_L2sq_max=28.0`.
- **Service mask:** 121 service junctions; 5 connector junctions excluded
  (JUNCTION-105/106/109/110/128), kept in model.
- **Next:** the researcher completes the decision form in §G. This task does **not**
  implement `reward.py`, does **not** add a STEP-9 clamp, and does **not** start PPO.

---

## B. Exact candidate definitions (verbatim from WU-11)

Sign convention (all): reward is a **negative cost**; higher (less negative) is better.
Time aggregation (all): per 1800 s report step; episode return = sum over 193 report steps
of a 96 h EPS; no discounting in the measurement. Terminal behavior (all): fixed-horizon
EPS; **a STEP-9 safety clamp/termination is NOT part of any candidate.**

### Formulation families (context)

- **F1 `normalized_weighted_sum`** —
  `r_t = -w_L*(leak_t/leak_ref) - w_U*(unserved_t^+/req_ref) - w_P*(deficit_t/deficit_ref) - w_A*(||da_t||^2/L2sq_max) - w_E*(power_t/power_ref)`;
  clipping: unserved clipped ≥0, da=0 for static holds; denominators fixed nonzero.
- **F2 `constrained_penalty_service_protected`** —
  `r_t = -(leak_t/leak_ref) - LAMBDA*(deficit_t/deficit_ref) - BIG*max(0, n_below20_t)`.
- **F3 `baseline_relative_improvement`** —
  `r_t = (leak_ref - leak_t)/leak_ref - w_U*max(0, unserved_t - unserved_ref)/req_ref - w_P_safety*(deficit_t/deficit_ref)`;
  F3 `baseline_constants.unserved_ref_gpm = 14.98483697365873` (accounting value).
- **F4 `safety_first_lexicographic`** —
  `if min_svc_p_t < 0: r_t = -c_hard - deficit_t/deficit_ref; elif min_svc_p_t < theta: r_t = -c_soft - deficit_t/deficit_ref; else: r_t = -(leak_t/leak_ref) - eps*(||da_t||^2/L2sq_max)`.

### C-A · `C-A_F1_balanced_dense` — base F1 · **PROVISIONAL CANDIDATE — NOT APPROVED**

- **Equation:** `r_t = - w_L*(leak_t/leak_ref) - w_U*(unserved_t^+/req_ref) - w_P*(deficit_t/deficit_ref) - w_A*(||da_t||^2/L2sq_max) - w_E*(power_t/power_ref)`
- **Constants:** leak_ref 84.72988433677985 · req_ref 906.3987348621764 · deficit_ref 28.671793365478514 · power_ref 88.10062475649187 · movement_L2sq_max 28.0
- **Provisional weights:** `w_L=1.0, w_U=1.0, w_P=1.0, w_A=0.1, w_E=0.0`
- **Actuator effort:** `w_A*(||da||^2/28)` on the **COMMANDED** normalised action (never realised pump speed); `w_A=0.1`.
- **Service/pressure:** dense normalised deficit (`deficit/deficit_ref`, `w_P=1`) + unserved⁺ (`w_U=1`); **no hard threshold term**.
- **Leakage:** normalised absolute `leak/leak_ref` (`w_L=1`).
- **Special cases:** unserved clipped ≥0; da=0 static holds; fixed nonzero denominators; energy off (`w_E=0`).
- **Scale derivation:** terms pre-normalised O(1) ⇒ unit weights neutral; `w_A=0.1` from WU-10 pathology C (leak dynamic range ~0.108 vs one max-move step = 1.0 at `w_A=1`); `w_E=0` avoids parameter proliferation.

### C-B · `C-B_F1_safety_leaning` — base F1 · **PROVISIONAL CANDIDATE — NOT APPROVED**

- **Equation:** *same functional form as C-A.*
- **Constants:** identical to C-A.
- **Provisional weights:** `w_L=1.0, w_U=1.0, w_P=2.0, w_A=0.1, w_E=0.0` (only `w_P` differs: 1 → 2).
- **Actuator effort:** identical to C-A (`w_A*(||da||^2/28)` on commanded action; `w_A=0.1`).
- **Service/pressure:** same dense deficit as C-A but heavier `w_P=2` (still O(1) after normalisation); unserved⁺ `w_U=1`; no hard threshold.
- **Leakage:** `leak/leak_ref` (`w_L=1`).
- **Special cases:** same as C-A. Motivated by measured deficit↔leak −0.7735; a *different emphasis*, **not a ranking versus C-A**.

### C-C · `C-C_F3_baseline_relative` — base F3 · **PROVISIONAL CANDIDATE — NOT APPROVED**

- **Equation:** `r_t = (leak_ref - leak_t)/leak_ref - w_U*max(0, unserved_t - unserved_ref)/req_ref - w_P_safety*(deficit_t/deficit_ref)`
- **Constants:** leak_ref 84.72988433677985 · req_ref 906.3987348621764 · deficit_ref 28.671793365478514 · **unserved_ref_gpm 15.103309701248634** (DSR-implied; the WU-9 *accounting* value is 14.98483697365873 — reported here exactly as the candidate stores it).
- **Provisional weights:** `w_U=1.0, w_P_safety=1.0`
- **Actuator effort:** **NOT SPECIFIED IN SOURCE** (F3 defines no actuator-movement/smoothness term).
- **Service/pressure:** excess-unserved penalty `w_U*max(0, unserved - unserved_ref)/req_ref` (only *above* baseline) + dense deficit `w_P_safety*(deficit/deficit_ref)`.
- **Leakage:** fractional reduction vs native baseline `(leak_ref - leak)/leak_ref`; intrinsically normalised, zero-centred at the native controller; no separate leak weight.
- **Special cases:** excess unserved clipped ≥0; no hard threshold term.

### C-D · `C-D_dense_deficit_no_hard_count` — base F2/F4 dense-safety variant · **PROVISIONAL CANDIDATE — NOT APPROVED**

- **Equation:** `r_t = -(leak_t/leak_ref) - LAMBDA*(deficit_t/deficit_ref) - BIG*max(0, n_negative_t)   # hard term on NEGATIVE nodes only`
- **Constants:** leak_ref 84.72988433677985 · deficit_ref 28.671793365478514
- **Provisional weights:** `LAMBDA_service=5.0, BIG_hard_negative=100.0`
- **Actuator effort:** **NOT SPECIFIED IN SOURCE** (this variant defines no actuator-movement term).
- **Service/pressure:** dense `LAMBDA*(deficit/deficit_ref)` (`LAMBDA=5`) + hard gate `BIG*max(0, n_negative)` firing **only** on negative-pressure nodes (baseline count 0).
- **Leakage:** normalised absolute `leak/leak_ref` (unit implicit weight).
- **Special cases:** **replaces** the ill-posed hard 20-psi count with dense deficit; the 20-psi level appears only *inside* the smooth deficit `= sum max(0, 20 - p_i)`, **not** as a hard gate; `LAMBDA=5` is central in [1,10], not fitted.

---

## C. توضیح ساده (فارسی) — هر candidate عملاً چه می‌کند؟

> این بخش فقط «تفسیر زبان‌ساده» است؛ هیچ عددی اضافه نمی‌کند و هیچ candidate را
> بهترین/برتر/بهینه/ترجیح‌داده‌شده نمی‌نامد. چهار پرسش برای هر کدام: (۱) چه چیزی را
> تشویق می‌کند؟ (۲) اگر فشار و نشت کم شوند ولی سرویس بدتر شود چه می‌شود؟
> (۳) اگر فشار بالا برود چه می‌شود؟ (۴) اگر agent زیاد action را تغییر دهد چه می‌شود؟

**C-A (F1، متعادل و چگال):**
1. کاهش همزمان نشت، تقاضای برآورده‌نشده (unserved) و کسری فشار (deficit)، به‌علاوه‌ی یک جریمه‌ی کوچک برای تغییرِ زیادِ عملگرها؛ همه‌ی ترم‌ها با ثابت‌های ثابت‌شده نرمال شده‌اند تا هم‌مقیاس باشند و وزن‌های ۱ نقطه‌ی شروعِ خنثی‌اند.
2. چون نشت و سرویس و فشار هر سه وزنِ ۱ دارند، بهبودِ نشت با بدترشدنِ سرویس و افزایش deficit خنثی یا حتی منفی می‌شود؛ پاداش لزوماً بهتر نمی‌شود.
3. طبق شواهد، بالا رفتنِ فشار نشت را زیاد می‌کند پس ترمِ نشت بدتر می‌شود، هرچند deficit و unserved بهتر می‌شوند؛ نتیجه‌ی خالص به تعادلِ وزن‌ها بستگی دارد.
4. ترمِ `w_A*(‖Δa‖²/28)` با `w_A=0.1` جریمه‌ی کوچکی می‌گیرد؛ یک حرکتِ کاملِ کران‌به‌کران تقریباً هم‌اندازه‌ی کلِ دامنه‌ی تغییرِ نشت (~۰٫۱۰۸) هزینه دارد، نه بیشتر.

**C-B (F1، تأکید بر ایمنی، `w_P=2`):**
1. همان C-A است ولی وزنِ فشار/deficit دو برابر است؛ یعنی محافظت از بدترین گرهِ فشار پررنگ‌تر می‌شود. این فقط «تأکیدِ متفاوت» است، نه رتبه‌بندی نسبت به C-A.
2. چون وزنِ deficit بزرگ‌تر است، بدترشدنِ سرویس شدیدتر جریمه می‌شود؛ پس بهبودِ نشت به‌قیمتِ سرویس، پاداش را بیشتر از C-A پایین می‌آورد.
3. مثل C-A نشت بالا می‌رود و ترمِ نشت بدتر می‌شود؛ اما چون deficit وزنِ ۲ دارد، بهبودِ فشار سهمِ مثبتِ بزرگ‌تری می‌گذارد.
4. دقیقاً مثل C-A: جریمه‌ی کوچکِ `w_A=0.1` روی `‖Δa‖²/28`.

**C-C (F3، نسبت به خطِ پایه):**
1. پاداش برابرِ «کسرِ کاهشِ نشت نسبت به کنترلرِ بومی» است، منهای جریمه برای unserved اضافه‌تر از خطِ پایه و جریمه‌ی deficit؛ یعنی مستقیماً «بهبود نسبت به baseline» را تشویق می‌کند و در نقطه‌ی کنترلرِ بومی صفر است.
2. اگر unserved از سطحِ baseline (~۱۵٫۱۰ GPM) بیشتر شود جریمه می‌گیرد و ترمِ deficit هم جریمه دارد؛ پس بدترشدنِ سرویس، سودِ کاهشِ نشت را جبران/خنثی می‌کند.
3. بالا رفتنِ فشار نشت را زیاد می‌کند، پس ترمِ بهبودِ نشت `((leak_ref-leak)/leak_ref)` کوچک یا منفی می‌شود.
4. **NOT SPECIFIED IN SOURCE** — خانواده‌ی F3 در منبع هیچ ترمِ حرکت/هموارسازیِ عملگر ندارد؛ تغییرِ زیادِ action مستقیماً جریمه نمی‌شود.

**C-D (deficit چگال + دروازه‌ی سختِ فقط-منفی):**
1. کاهشِ نشت و کاهشِ deficit، با یک «دروازه‌ی سختِ» جریمه فقط برای فشارِ منفی. عمداً ترمِ سختِ «۲۰ psi» حذف شده چون روی خطِ پایه هم فعال می‌شود (ill-posed).
2. ترمِ deficit با وزنِ `LAMBDA=5` جریمه می‌شود، پس بدترشدنِ سرویس پاداش را پایین می‌آورد؛ و اگر کنترلی گره‌ای را به فشارِ منفی ببرد جریمه‌ی بزرگِ `BIG=100` فعال می‌شود.
3. نشت بالا می‌رود پس ترمِ نشت `(leak/leak_ref)` بدتر می‌شود؛ ترمِ منفیِ سخت فعال نمی‌شود.
4. **NOT SPECIFIED IN SOURCE** — این نسخه هیچ ترمِ حرکت/هموارسازی ندارد؛ تغییرِ زیادِ action مستقیماً جریمه نمی‌شود.

---

## D. Evidence per candidate — OBSERVED / INFERRED / UNRESOLVED

The three categories are kept separate on purpose. **OBSERVED** = measured on BWSN-1.
**INFERRED** = a reasoned implication, not directly measured. **UNRESOLVED** = an open
uncertainty or a value judgement that only the researcher (or a later experiment) can close.

**Shared measured facts (OBSERVED, apply to all candidates):**
- Leakage and service genuinely **oppose**: leak↔dsr **+0.7497**, leak↔deficit **−0.7735**,
  leak↔n_below20 **−0.7419**, dsr↔deficit **−0.9653**.
- **Chronic baseline sub-20-psi:** `frac_ts_any_node_below_20psi = 1.0` (386 node-timesteps
  <20 psi), `frac_ts_any_node_negative = 0.0`, min service pressure over horizon **4.16452 psi**.
- **Boundary-seeking:** the leak-only optimum sits on the PRV lower corner
  (`prv_all_lower`: leak 84.73 → 81.38 GPM but DSR 0.98334 → 0.91940).
- **Movement-penalty scale:** leak-term dynamic range **~0.108** vs one full max-move step = 1.0
  (analytic `movement_L2sq_max=28`, static holds = 0 movement).
- **Scale imbalance** across raw penalties ≈ **7.15×** ⇒ fixed normalisation is mandatory.
- **Limited joint-action coverage:** only a single lower-corner joint test exists (19 static
  in-bounds configs); interior/mixed 5-D corners are a STEP-9/STEP-12 job.

**C-A** — *OBSERVED:* balanced leakage/service/safety/effort; unit-weight induced-incentive
argmax is `prv_176_upper` and the leak-only optimum is at the PRV lower corner ⇒ a STEP-9 clamp
is required, not optional. *INFERRED:* dense, differentiable, PPO-continuous friendly.
*UNRESOLVED:* `F1_vary_w_P` shows `w_P=0 → prv_175_lower`, `w_P≥0.5 → prv_176_upper` — `w_P` below
~0.5 lets the incentive drift toward the low-pressure corner; realised `||da||²` unknown (analytic
effort ceiling is a HYPOTHESIS until a policy trajectory exists).

**C-B** — *OBSERVED:* heavier `w_P=2` more strongly weights the dense worst-node/deficit signal.
*INFERRED:* a safety-leaning emphasis of C-A. *UNRESOLVED:* more weight on pressure safety may
reduce achievable leakage cuts (a *different emphasis*, not a ranking); over-weighting deficit
could flatten the leakage gradient (leak span ~±6%).

**C-C** — *OBSERVED:* interpretable as % leakage reduction vs the native controller, zero-centred
at baseline. *INFERRED:* directly answers the thesis objective (reduction vs baseline).
*UNRESOLVED:* leakage-improvement dynamic range is small (~±6%), so signal-to-noise / advantage
scaling at training time must be checked; the two `unserved_ref` values (accounting 14.985 vs
DSR-implied 15.103) reflect two accounting bases.

**C-D** — *OBSERVED:* the hard 20-psi count fires on the native baseline itself
(`frac_ts_any_node_below_20psi=1.0`), so it is replaced by dense deficit; the negative-node hard
gate is well-posed (baseline count 0). *INFERRED:* service protected by construction with a
well-posed hard backstop. *UNRESOLVED:* `LAMBDA` is unmeasured and sets the leakage↔service
exchange rate; the F2 λ/BIG sweep argmax is stable at `prv_176_upper` (direction robust) but the
reward *magnitude* is untuned — a very large `LAMBDA` suppresses the leakage gradient.

---

## E. The four families against the 12 thesis decision dimensions

> **Descriptive only.** No scores, ranks, tiers, winners, or recommendations. Each row states
> what the evidence says about that dimension; it does not order the candidates.

1. **Leakage management signal** — all candidates carry a leakage term; F1 (C-A/C-B) and C-D use
   absolute normalised `leak/leak_ref`, F3 (C-C) uses fractional reduction vs baseline. Measured
   in-bounds leak span is small (~±6%, dynamic range ~0.108).
2. **Service preservation** — C-A/C-B/C-D protect service via a dense deficit term; C-C penalises
   unserved above baseline. Measured leak↔dsr +0.7497 and leak↔deficit −0.7735 confirm service and
   leakage oppose.
3. **Pressure safety signal density** — dense channels (deficit, min-service-pressure) are active
   every step; the <0 psi hard channel is inactive in-bounds (`frac_negative 0.0`); the <20 psi
   count is active at 100% of steps **including the native baseline**.
4. **Signal density (dense vs sparse)** — all four rely on dense terms; any hard-count term is
   sparse or (at 20 psi) degenerate on this network.
5. **Scale stability (fixed normalisation)** — every candidate divides by the FROZEN WU-9 constants,
   so terms are O(1); raw penalties otherwise span a ~7.15× ratio.
6. **Interpretability / thesis explainability** — C-C reads directly as % leakage reduction vs the
   native controller; C-A/C-B as a normalised weighted cost; C-D as leak + dense-service with a
   negative-pressure backstop.
7. **Parameter count & sensitivity** — C-A/C-B expose {w_L,w_U,w_P,w_A} (w_E=0); C-C exposes
   {w_U,w_P_safety}; C-D exposes {LAMBDA,BIG}. Sweeps show the incentive-argmax shifts with these
   (e.g. F1 `w_P 0 → prv_175_lower`, `≥0.5 → prv_176_upper`).
8. **Reward-hacking resistance** — effort/smoothness MUST use the COMMANDED action (realised pump
   speed is reset by native STATUS rules); a hard 20-psi term is ill-posed; an F4-style 0-psi
   threshold never fires yet reports "safe".
9. **PPO continuous-action compatibility** — all candidates finite; dense F1/F3 forms are
   smooth/differentiable; F2/F4-style large penalties give high-variance returns (F2 pooled reward
   std ~42 vs F1 ~0.17).
10. **STEP-9 safety-layer compatibility** — no candidate enforces a pressure bound; the leak optimum
    sits on the PRV lower corner, so a STEP-9 state-dependent clamp is required **regardless** of the
    reward chosen. C-D's negative-node gate is complementary to, not a substitute for, STEP-9.
11. **Reproducibility / no leakage** — all constants are fixed (measured once, frozen), not
    per-episode running statistics; the reference reproduces the frozen baseline exactly
    (`leak_ref` abs diff 0.0; per-timestep vs accounting 0.0).
12. **Baseline relatability** — C-C is zero-centred at the native controller; C-A/C-B/C-D are
    absolute-cost forms read relative to the measured reference.

---

## F. The central scientific trade-off

**Why can a reward that successfully reduces leakage still be scientifically wrong for this
thesis?** Because on measured BWSN-1 evidence, leakage and service **genuinely oppose**
(leak↔dsr **+0.7497**, leak↔deficit **−0.7735**) and the leak-only optimum lands exactly on the
PRV **lower** corner (`prv_all_lower`: leak 84.73 → 81.38 GPM while DSR drops 0.98334 → 0.91940).
A reward that "sees" only leakage therefore drives the agent to lower pressure and degrade
service **while the leakage number looks better**. Additionally, the network is chronically below
20 psi at every timestep (`frac_ts_any_node_below_20psi = 1.0`; min service pressure 4.16452 psi)
yet never negative — so an **absolute hard 20-psi reward constraint fires on the native baseline
itself and is ill-posed.** A reward that reports "safe" while sitting on a low-pressure boundary is
a reward-hacking / mis-specification hazard, not a success.

> چرا یک reward که با موفقیت نشت را کم می‌کند می‌تواند از نظر علمی برای این تز غلط باشد؟ چون نشت و
> سرویس واقعاً در تضادند (leak↔dsr = +۰٫۷۴۹۷، leak↔deficit = −۰٫۷۷۳۵) و بهینه‌ی «فقط-نشت» روی کرانِ
> پایینِ PRV می‌نشیند؛ پس reward‌ای که فقط نشت را می‌بیند، فشار را پایین می‌آورد و سرویس را خراب
> می‌کند در حالی که عددِ نشت بهتر به‌نظر می‌رسد. افزون بر این، شبکه در هر گامِ زمانی حداقل یک گرهِ زیرِ
> ۲۰ psi دارد ولی هیچ گرهِ منفی ندارد؛ پس قیدِ سختِ مطلقِ ۲۰ psi روی خودِ خطِ پایه هم فعال می‌شود و
> بد-تعریف است.

**Two separate layers (do NOT conflate; neither is implemented here):**

| Layer | Decision | Role | Guarantees a pressure bound? |
|---|---|---|---|
| **Reward design** | **D-P6-005** (this decision) | *shapes* behavior via a per-step signal | **No** |
| **State-dependent safety** | **STEP-9** (separate, not started) | *enforces* bounds by clamping actions to the approved box | **Yes** (that is its job) |

The enforced 20-psi guarantee belongs to **STEP-9**, not to the reward. C-D's negative-node hard
gate is a *complement* to STEP-9, never a replacement. Choosing any candidate here does **not**
create a safety guarantee — the STEP-9 clamp is required regardless.

> «طراحیِ reward» (D-P6-005) و «مکانیزمِ ایمنیِ وابسته به وضعیت» (STEP-9) دو لایه‌ی جدا هستند:
> reward فقط رفتار را شکل می‌دهد و هیچ کرانِ فشاری را تضمین نمی‌کند؛ تضمینِ اجراییِ ۲۰ psi کارِ
> کلمپِ STEP-9 است. هیچ‌کدام از این دو لایه در این وظیفه پیاده‌سازی نمی‌شود.

---

## G. Researcher decision form (D-P6-005) — **BLANK, to be completed by the researcher**

```
D-P6-005 — REWARD FORMULATION SELECTION
========================================
Selected formulation (F1 / F2 / F3 / F4 or a candidate C-A/C-B/C-C/C-D): ______________________

Selected parameters / weights (list every weight, coefficient, threshold): ____________________
  ____________________________________________________________________________________________

Rationale (why this formulation + these parameters, on the measured evidence): ________________
  ____________________________________________________________________________________________

Any modification to the proposed candidate (equation, constant, weight, or none): ____________
  ____________________________________________________________________________________________

Approval status (APPROVED / REJECTED / NEEDS-REVISION): _______________________________________

Researcher: ______________________________       Date: ______________________________
```

*(No field above is filled. D-P6-005 remains PROPOSED until the researcher completes this form.)*

---

## H. Provenance & reproducibility

- **Machine mirror:** `results/phase6/p6_d_p6_005_researcher_summary.json`
  (`researcher_selection: null`; `self_checks` all true). Generated deterministically by
  `src/validation/p6_d_p6_005_researcher_summary.py` — a **pure re-shaping** of the WU-11 brief
  (no EPANET/PPO/RNG); re-running byte-reproduces the JSON. Tests:
  `tests/test_researcher_summary.py` (21).
- **Source of every number:** `results/phase6/p6_d_p6_005_decision_brief.json` (WU-11), itself
  built from WU-9 (`p6_s8_reward_scale_analysis.json`) and WU-10
  (`p6_s8_reward_formulation_comparison.json`). `working_inp_sha256` =
  `53015ba9212e46bec731d190971819996233996b498bc269e828f992830a20a9`.
- **Unchanged by this task:** action space (D-P6-001/002/003, dim 7), observation spec
  (D-P6-004, dim 139), network topology, native pump STATUS rules, leakage instrument, and all
  previously validated evidence.





