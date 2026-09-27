# PHASE6_ACTION_SPACE_SPEC.md — Approved DRL Action Space (FROZEN)

**Status:** APPROVED & FROZEN, 2026-09-27 (researcher approval).
**Decisions:** D-P6-001 (encoding), D-P6-002 (pump bounds), D-P6-003 (PRV set + bounds).
**Provenance:** PROPOSED → REVIEWED → APPROVED. See
`docs/PHASE6_DECISION_REGISTER.md` (APPROVAL section) for full history; earlier
proposed values are preserved there and are NOT erased.
**Decision class:** ENGINEERING DECISION (bounds/encoding) on VALIDATED FACT
(measured characterization). Researcher-approved (constitution priority level 3).

This document is the single source of truth for *what the agent may command*. The
STEP 9 safety layer and the STEP 11 environment MUST clamp to exactly these bounds.
Do not silently change any value here without a new, evidence-backed research
decision registered in the decision register.

---

## 9.1 Controlled actuators (the DRL action space)

Seven actuators, all continuous:

| # | Actuator  | Kind          | Physical quantity          |
|---|-----------|---------------|----------------------------|
| 0 | VALVE-173 | PRV           | pressure setting (psi)     |
| 1 | VALVE-175 | PRV           | pressure setting (psi)     |
| 2 | VALVE-176 | PRV           | pressure setting (psi)     |
| 3 | VALVE-177 | PRV           | pressure setting (psi)     |
| 4 | VALVE-178 | PRV           | pressure setting (psi)     |
| 5 | PUMP-170  | variable-speed| relative speed (unitless)  |
| 6 | PUMP-172  | variable-speed| relative speed (unitless)  |

The agent commands **PRV pressure setpoints** and **pump relative speed** only.

## 9.2 Excluded actuators (in the model, not in the action space)

| Actuator  | Why excluded                                                        |
|-----------|---------------------------------------------------------------------|
| VALVE-174 | Adverse reopen 95→96 psi; not safely regulating (VALIDATED FACT).   |
| VALVE-179 | Safety-critical negative-pressure transition ~44.8–44.9 psi.        |
| VALVE-180 | Commanded shut by benchmark `[CONTROLS]`; native-shut valve.        |

These three valves **remain in the hydraulic model** (their benchmark
settings/controls are preserved). They are excluded only from the *agent's* action
vector. Removing any of them from the model, or admitting VALVE-179, is a
**separate explicit research decision** — not part of this approval.

## 9.3 Physical bounds (approved, exact)

PRV setpoints (psi):

```text
VALVE-173 : [54.5, 100.0]
VALVE-175 : [21.5, 110.0]
VALVE-176 : [20.0, 59.524]
VALVE-177 : [20.0, 90.0]
VALVE-178 : [20.0, 74.0]
```

Pump relative speed (unitless):

```text
PUMP-170  : [0.82, 1.10]
PUMP-172  : [0.77, 1.10]
```

## 9.4 Normalized bounds

Every actuator is exposed to the policy on the same symmetric interval:

```text
a_i ∈ [-1.0, +1.0]   for all i in 0..6
```

`a_i = -1` maps to `lower_i`; `a_i = +1` maps to `upper_i`; `a_i = 0` maps to the
midpoint of the physical range. This uniform normalized box (Gaussian-friendly,
tanh-friendly) is the standard SB3/PPO continuous-action convention and keeps every
dimension on a comparable scale for the policy network.

## 9.5 Exact mapping formula (normalized → physical)

For actuator `i` with approved physical bounds `[lower_i, upper_i]` and normalized
action `a_i ∈ [-1, 1]`:

```text
physical_i = lower_i + ((a_i + 1) / 2) * (upper_i - lower_i)
```

- **Encoding = ABSOLUTE (D-P6-001, APPROVED).** The mapped value is the setpoint /
  speed itself, NOT an increment relative to the previous command.
- Inverse (physical → normalized), for logging/tests:
  `a_i = 2 * (physical_i - lower_i) / (upper_i - lower_i) - 1`.
- A delta / incremental encoding is explicitly deferred to a **separate future
  ablation** and must not silently replace this absolute formulation.

## 9.6 Pump rule interaction (STATUS vs SPEED)

- The benchmark's native pump **STATUS** rules (`[RULES]`/`[CONTROLS]`) are kept
  **unchanged**. They decide when a pump is OPEN or CLOSED (tank-refill logic).
- The agent controls pump **SPEED** only.
- **Mechanism (G12 = Option C on Option A, VALIDATED FACT + ENGINEERING DECISION):**
  each control step, map the action to a physical speed, issue the speed command,
  let the native STATUS rules run, and **re-issue the speed command every control
  step**. Measured: re-issue holds the commanded speed 98.62% of the time; commanding
  once holds it 1.72% (`results/phase6/p6_s4_pump_strategy.json`). The native
  `STATUS IS OPEN` rule action resets pump speed to 1.0, which is exactly why the
  speed must be re-asserted every step (and why the encoding is absolute).
- Rewriting the rules to `SETTING IS` (Option B) halts the segmented simulator at
  t=79.5 h (both pumps latch Closed, tank empties) — **disqualified**.

## 9.7 Commanded vs realized semantics

The environment MUST track and log, per pump, per step:

- `commanded_speed` — the speed the agent asked for (post-mapping),
- `realized_speed` — the speed actually in effect after native rules ran,
- `pump_status` — OPEN / CLOSED as set by native rules.

Persistent speed is asserted ONLY when `realized_speed` confirms it. A closed pump
has no meaningful realized speed; do not report the commanded value as if realized.
For PRVs the analogous pair is `commanded_setting` vs the echoed/active setting plus
valve status (Active / Open / Closed).

## 9.8 Safety limitations (NOT closed by this approval)

- Per-actuator bounds are approved; the **full 5-D PRV box × 2 pump dims × uncertain
  demand is NOT exhaustively validated.** Only a single joint lower-corner test
  exists (service-clean at that one corner). **No claim of exhaustive joint
  action-space safety.**
- Mixed corners, the box interior, and pump + stochastic-demand combinations are
  UNTESTED (risk R1b) → STEP 9 (safety layer) and STEP 12 (automated joint tests).
- The chronic low node JUNCTION-29 (~4.16 psi at nominal) is not fixed by these
  PRVs; the safety references are the measured baseline (n<20psi = 386, n_negative
  = 0). The leak instrument is validation-only / uncalibrated (relative response
  only, risk R3).

## 9.9 Evidence references

| Approved item | Evidence file | Key |
|---|---|---|
| PRV set {173,175,176,177,178}; exclude 174/179/180 | `results/phase6/p6_s3_prv_finechar.json`, `p6_s3b_v179_refine.json`, `p6_s3c_zone_interaction.json` | fine char / 179 cliff / joint responsive |
| PRV bounds (175/176/177/178) | `results/phase6/p6_s6_active_prv_bounds.json` | per-valve sweeps, service-clean lowers, highest-tested-regulating uppers |
| VALVE-173 lower = 54.5 | `results/phase6/p6_s6b_v173_lowside_refine.json` | last-closed 54.25 / first-active 54.5 |
| Pump lowers vs shut-off (0.8152 / 0.7655) | `results/phase5/g3_pump_speed.json` | feasible_speed_bounds |
| Pump upper 1.10 feasible | `results/phase5/g3_pump_speed.json` | response_summary (no overspeed infeasibility to 1.10) |
| Pump SPEED-only mechanism (G12) | `results/phase6/p6_s4_pump_strategy.json` | reopen_semantics, speed_hold_rate |

## 9.10 Explicit terminology limitations (do not overstate)

- For **VALVE-175/176/177/178**, the approved upper bounds are the **highest tested
  regulating setpoints** (the sweep's 2× nominal grid cap, where the valve was still
  Active). They are **NOT** the true physical maximum and **NOT** a demonstrated
  "regulation ceiling"; the true Active→Open onset above the cap is UNTESTED.
- For **VALVE-173**: 54.5 psi = first *measured* Active point (step6b, 0.25 psi
  bracket); 100 psi = highest tested Active/regulating setpoint; 110 psi is where
  173 was observed to transition to Open (wide-open, non-regulating). Only 173 has
  an OBSERVED Active→Open transition.
- Pump **1.10** = highest tested feasible speed, NOT the pump's absolute physical
  maximum. Pump lowers **0.82 / 0.77** carry margin above the measured shut-off
  speeds (0.8152 / 0.7655); they are practical operating floors, not the exact
  physical shut-off points.

---

## Exact ordered action vector (STABLE — do not reorder)

```text
action[0] -> VALVE-173   PRV   pressure setting  psi        bounds [54.5, 100.0]
action[1] -> VALVE-175   PRV   pressure setting  psi        bounds [21.5, 110.0]
action[2] -> VALVE-176   PRV   pressure setting  psi        bounds [20.0, 59.524]
action[3] -> VALVE-177   PRV   pressure setting  psi        bounds [20.0, 90.0]
action[4] -> VALVE-178   PRV   pressure setting  psi        bounds [20.0, 74.0]
action[5] -> PUMP-170    PUMP  relative speed    unitless   bounds [0.82, 1.10]
action[6] -> PUMP-172    PUMP  relative speed    unitless   bounds [0.77, 1.10]

action_dim = 7    normalized box = [-1, 1]^7    dtype = float32
```

This ordering is frozen. The environment, the safety layer, the logger, and every
test MUST use exactly this index → actuator mapping.
