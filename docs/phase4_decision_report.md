# Phase 4 — Independent Adversarial Review: Network Selection, Experiment Design, Novelty

Date: 2026-09-02. Author: AI research partner (adversarial reviewer role).
Companion evidence log: [phase4_network_evidence.md](phase4_network_evidence.md).

**Evidence grades used throughout.**
`FACT` = directly readable in a model file, a paper, or an official database record.
`INFERENCE` = my derivation from stated facts.
`UNKNOWN` = not verified; do not cite.
No number in this report is a guess. Where a source could not be reached, it says so.

**Scope note.** No code was written, no dependency installed, no experiment run.
All hydraulic counts come from parsing distributed `.inp` files; all literature
claims come from OpenAlex/Crossref metadata, publisher abstracts, official
competition documents, or full texts already present in `D:\Thesis\papers\`.

---

# 1. Executive Decision

## Verdict on Net3 as the primary network: **NO**

Net3 should **not** be the primary network. Three findings drive this, in order
of force.

**1. Net3 contains zero valves.** `FACT` — the distributed `Net3.inp` has 92
junctions, 2 reservoirs, 3 tanks, 117 pipes, 2 pumps and an **empty `[VALVES]`
section**. Therefore every PRV in any Net3 pressure-management study is an
author-introduced design element. The thesis would have to choose its own valve
locations, and the examiner's strongest available attack — *"you placed the
valves that make your controller look good"* — has no external authority to
appeal to.

**2. The exact experiment is already published on Net3.** `FACT` — Hu, Gao &
Zhong (2023), *Water Supply* 23(7):2833, doi 10.2166/ws.2023.163, state:
"EPANET Net 3 was trained and tested in this study"; "Four valves with the
greatest impact on leakage were added to the network through a pre-experiment
using a GA"; "A background leakage was added to every node downstream of the
pumps as an emitter"; "The pump was modelled as a variable-speed pump with a
speed range of 0.7–1 … The action of the pressure reducing valve (PRV) agent was
to set the outlet pressure"; demand uncertainty multipliers "follow a truncated
normal distribution with a range from 0.7 to 1.3"; state = nodal demands + tank
levels; reward = pump energy cost + leakage cost + tank penalty; baselines GA,
PSO, DE. `INFERENCE` — a PPO study on Net3 with PRVs + VSP + emitter leakage +
demand uncertainty + a multi-objective reward is, at the level of the
environment, a re-implementation of Hu et al. (2023) with the learning algorithm
swapped. That is the weakest possible novelty position.

**3. A better-conditioned public benchmark exists and was missed in earlier
phases.** `FACT` — `BWSN_Network_1.inp` has 126 junctions, 1 reservoir, 2 tanks,
168 pipes, **2 pumps on HEAD curves**, and **8 PRVs already present in the
published benchmark**, with settings spanning 16.45–80 psi on 6–10 in valves, and
tank-level pump rules. `INFERENCE` — on BWSN-1 the PRV placement is fixed by the
benchmark's own authors, so it is *not* a degree of freedom the thesis can be
accused of tuning. This removes the placement-bias attack outright rather than
mitigating it.

## Recommendation: **OPTION 4**

**BWSN-1 (Battle of the Water Sensor Networks, Network 1) as the primary
network; Net3 retained as a mandatory secondary network purely for comparability
with Hu et al. (2023); Jowitt & Xu retained as an optional, strictly
*unmodified*, PRV-only tertiary case for comparability with Negm (2024).**

`INFERENCE` — this is the only configuration that simultaneously (a) removes
author-chosen PRV placement from the main result, (b) keeps a direct numerical
bridge to the two papers the thesis is positioned against, and (c) stays inside
a Master's compute budget. Full justification in §11, config in §12.

## What is genuinely novel after this review

`INFERENCE`, calibrated. Not the algorithm, not the action space, not the
coordination, not the multi-objective reward — all four have precedent (§9).
What survives: **out-of-distribution robustness** (Hu tested in-distribution
only), **model-parameter uncertainty**, **PDA/DDA separation**, **Pareto /
constraint-matched evaluation instead of a scalarised cost**, and **ablation that
isolates the pump's marginal contribution**. These are experiment-design
contributions, which is exactly where the brief already suspected the novelty
sat. That suspicion is confirmed by evidence.

## The one claim earlier phases got wrong

`FACT` — prior gap **G10** recorded "no standard benchmark carries both PRVs and
VSPs natively". This is false as stated. BWSN-1 (2 pumps + 8 PRVs), L-Town
(1 pump + 3 PRVs), C-Town (11 pumps + 3 PRV + 1 FCV), D-Town (11 pumps + 4 PRV +
1 TCV), Richmond (7 pumps + 1 PRV) and CY-DBP (2 pumps + 2 PRV + 2 FCV) all ship
pumps *and* PRVs. Only the weaker statement survives: **no public benchmark ships
a pump pre-configured as variable-speed** — and that is a parameterisation, not a
topology change, wherever a head-curve pump already exists.

---

# 2. Full Benchmark Landscape

Rows marked **`.inp` verified** were parsed by me from the distributed model
file. Rows marked *(prose)* come from the WaterBenchmarkHub description and are
one evidence grade lower — `FACT` in §A of the evidence log records three cases
where WBH prose disagrees with the `.inp`, so prose counts must never be cited as
exact.

Legend — *Leak. suit.* = suitability for a pressure-driven leakage study;
*P+V suit.* = suitability for joint pump + PRV control; *Compute* = relative
per-episode cost from the native `[TIMES]` block; *RL prec.* = published RL
control precedent found in this review.

| Network | Junc | Pipes | Pumps | Tanks | PRVs | Public? | EPANET `.inp`? | RL prec. | Leak. suit. | P+V suit. | Compute | Reprod. | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **BWSN-1** | 126 | 168 | 2 (HEAD) | 2 | **8** | Yes | **verified** | **none found** | High | **High** | 192 steps/ep | High | 96 h @ 0:30; tank-level pump rules; US units |
| **Net3** | 92 | 117 | 2 (HEAD) | 3 | **0** | Yes | **verified** | **Hu 2023 ×2** | High | Medium | 24 steps/ep | High | no valves at all; every PRV author-added |
| **L-Town** | 782 | 905 | 1 (HEAD) | 1 | **3** | Yes | **verified** | none found | **Very high** | Medium | **2,016 steps/ep** | **Very high** | BattLeDIM; ≥20 m target; ≤10 % param. error declared |
| **C-Town** | 388 | 429 | 11 (HEAD) | 7 | 3 (+1 FCV) | Yes | **verified** | BATADAL RL (cyber) | High | High | 672 steps/ep | High | BWCN 2010; 5 DMAs |
| **D-Town** | 399 | 443 | 11 (HEAD) | 7 | 4 (+1 TCV) | Yes | **verified** | **Hajgató 2020; Pei 2025** | Medium | High | 672 steps/ep | High | BWN-II 2012; pump-scheduling home turf |
| **Richmond** | 865 | 949 | 7 (HEAD) | 6 | 1 | Yes† | **verified** | none found | Medium | Medium | 24 steps/ep | Medium | †Yorkshire Water asks to be informed of use |
| **Anytown** | 19 | 40 | 1 (HEAD) | 0 | 0 | Yes | **verified** | **Hajgató 2020; Hu 2023; Pei 2025** | Low | Low | 8 steps/ep | High | no tanks in `.inp`; toy scale |
| **CY-DBP** | 284 | 362 | 2 (HEAD) | 1 | **2** (+2 FCV) | Yes | **verified** | none found | Medium | **High** | 2,014 steps/ep | High | 167:50 @ 0:05; DBP/water-quality benchmark |
| **Jowitt & Xu** | 22+3 src | 37 | **0** | 3 | 3 (added by users) | paper only | **no public `.inp` found** | **Negm 2024** | High | **Unusable** | ~24 steps/ep | **Low** | not in WBH (0/95); Ferrarese 2026 re-uses it |
| **KY6** | 543 | 644 | 2 (**POWER**) | 3 | 1 | Yes | **verified** | none | Medium | **Unusable** | `Duration 0` | High | steady-state; `[CURVES]` empty |
| **KY9** | 1242 | 1270 | 17 (**POWER**) | 15 | **56** | Yes | **verified** | none | Medium | **Unusable** | `Duration 0` | High | biggest native PRV count of any benchmark |
| **KY10** | 920 | 1043 | 13 (**POWER**) | 13 | 5 | Yes | **verified** | none | Medium | **Unusable** | `Duration 0` | High | same disqualifier |
| **KY11** | 802 | 846 | 21 (**POWER**) | 28 | 15 | Yes | **verified** | none | Medium | **Unusable** | `Duration 0` | High | same disqualifier |
| **KY13** | 778 | 940 | 4 (**POWER**) | 5 | 0 | Yes | **verified** | none | Medium | **Unusable** | `Duration 0` | High | same disqualifier |
| **KY15** | 659 | 662 | 13 (**POWER**) | 8 | 28 (25 PRV+3 PSV) | Yes | **verified** | none | Medium | **Unusable** | `Duration 0` | High | same disqualifier |
| Net6 *(prose)* | 3322 | 3828 | 60 | 33 | 2 valves | Yes | verified (unparsed) | none | Medium | High | very high | High | too large for a Master's RL budget |
| Micropolis *(prose)* | 1574 | 1823 | 8 | 1 | **0** | Yes | verified (unparsed) | none | Medium | Medium | high | High | no valves |
| E-Town *(prose)* | 2859 | 3198 | 7 | 4 | 15 valves | Yes | prose only | none | Medium | High | very high | Medium | valve types UNKNOWN |
| BWSN-2 *(prose)* | 12523 | 14314 | 4 | 2 | 5 valves | Yes | prose only | none | Medium | Medium | prohibitive | High | valve types UNKNOWN |
| WCR *(prose)* | 1786 n | 1984 | 6 | 4 res | 4 valves | Yes | prose only | none | Medium | Medium | high | Medium | valve types UNKNOWN |
| NJ1 *(prose)* | 14991 | 16090 | 12 | 8 | UNKNOWN | Yes | prose only | none | Medium | UNKNOWN | prohibitive | High | KY-library US system |
| Richmond-`van_zyl_2004` *(prose)* | UNKNOWN | UNKNOWN | ≥1 | ≥1 | UNKNOWN | Yes | prose only | none | Low | Low | low | Medium | small pump-scheduling test net |
| Hanoi / Modena / Balerma / Fossolo / BAK / Jilin / Zhi-Jiang / Marchi-Rural / KL / EXNET / Pescara / CA1 / PA1 / Net2 / WA1 / Blacksburg / TLN / TRN / NYC-Tunnel / Nineteen-Pipe / KYV24 *(prose)* | 27–1893 | 34–3029 | **0** | 0–2 | 0–43 | Yes | mixed | none | Low–Med | **Excluded** | low | High | **no pump ⇒ structurally cannot host a VSP** |

`FACT` — 21 catalogued benchmarks have zero pumps and are therefore structurally
incapable of hosting the thesis's central VSP claim; they remain usable only as
gravity-fed, PRV-only side cases.

`FACT` — `[EMITTERS]` is empty in **every** candidate parsed, and no candidate
sets `DEMAND MODEL PDA`. `INFERENCE` — leakage modelling and PDA are added by the
researcher in all cases and are therefore **not** discriminators between
networks. Earlier phases treated them as discriminators; that was an error.

`FACT` — no `[PUMPS]` row in any candidate carries a `SPEED` value or a speed
pattern; all use `HEAD <curve>` or `POWER <value>`. `INFERENCE` — "add a VSP" is a
parameterisation on any network with a head-curve pump, and a topology
fabrication only where no pump exists (Jowitt & Xu). This single distinction
decides the Jowitt & Xu question (§4).

---

# 3. Weighted Network Ranking

## 3.1 Criteria and weights

Weights sum to 100. They are my judgement, stated so they can be attacked and
re-run. Justification is given for every weight; §3.3 shows what happens when
they move.

| # | Criterion | W | Why this weight |
|---|---|---|---|
| 1 | Pump availability | 8 | Hard requirement. Effectively binary: no pump ⇒ the VSP half of the research question cannot exist. |
| 2 | PRV availability | 8 | Hard requirement, same logic. |
| 3 | **PRV-placement transparency** | **10** | Highest single weight. §7 shows placement is the one design choice that can invalidate the whole leakage result, because a placement optimised on leakage co-optimises the reward. Placement fixed by a third party is worth more than any other property. |
| 4 | Tank dynamics | 5 | Needed to make tank level a meaningful state variable and to couple pump action to storage. Present in most candidates ⇒ moderate discriminating power. |
| 5 | Leakage-model suitability | 4 | Low weight *because* `[EMITTERS]` is empty everywhere (`FACT`) — this must be added on any network, so it barely discriminates. Residual weight reflects node count and geometry convenience. |
| 6 | Demand-uncertainty compatibility | 4 | Same reasoning: a stochastic demand model is imposed by the thesis on any network. Residual weight rewards networks shipping documented consumer classes and seasonality. |
| 7 | Public availability | 7 | Gate. A non-public network makes the thesis unreproducible by definition. |
| 8 | Availability of an official `.inp` | 7 | Separate from (7): a paper can be public while its model file is not. This is precisely where Jowitt & Xu fails. |
| 9 | Reproducibility | 8 | Independent third-party mirrors, stable identifiers, versioned distribution. |
| 10 | RL computational feasibility | 9 | A real Master's constraint. Derived from `[TIMES]` × network size (§2). L-Town's 2,016 steps/episode × 782 junctions × multi-seed × OOD test sets is the binding limit. |
| 11 | Existing RL precedent (for *comparison*) | 4 | Scored as an **asset for comparability only**. The novelty *liability* of precedent is handled in §9 and deliberately not double-counted here. |
| 12 | Existing pump+PRV precedent (for comparison) | 3 | Same treatment, lower weight because such precedent is rarer. |
| 13 | Benchmark comparability | 6 | Can published numbers be placed beside mine on the same network? |
| 14 | Network realism | 4 | Derived-from-utility beats hand-built teaching example. |
| 15 | External validity | 3 | Does a result here plausibly transfer to a real utility? |
| 16 | Ability to isolate the pump's contribution | 5 | Directly serves the thesis's own ablation (§9 claim N6). Networks with many pumps confound it. |
| 17 | Ability to study PDA vs DDA | 2 | Low weight: technically possible on every candidate, so it hardly discriminates. |
| 18 | Size of existing user base | 3 | Proxy for reviewer familiarity and for the chance that someone can check the work. |

## 3.2 Scores (0–5) and baseline result

| Criterion | BWSN-1 | Net3 | L-Town | C-Town | D-Town | CY-DBP | J&X unmod. | J&X modified |
|---|---|---|---|---|---|---|---|---|
| 1 Pump avail. | 5 | 5 | 4 | 5 | 5 | 5 | **0** | 3 |
| 2 PRV avail. | 5 | **0** | 4 | 4 | 4 | 3 | 4 | 4 |
| 3 PRV-placement transparency | **5** | **0** | **5** | 5 | 5 | 5 | 2 | 2 |
| 4 Tank dynamics | 4 | 5 | 3 | 5 | 5 | 3 | 4 | 4 |
| 5 Leakage suitability | 4 | 4 | 5 | 4 | 4 | 3 | 5 | 5 |
| 6 Demand-uncertainty compat. | 3 | 3 | **5** | 3 | 3 | 3 | 3 | 5 |
| 7 Public | 5 | 5 | 5 | 5 | 5 | 5 | 3 | 3 |
| 8 Official `.inp` | 5 | 5 | 5 | 5 | 5 | 5 | **0** | **0** |
| 9 Reproducibility | 5 | 5 | 5 | 5 | 5 | 4 | 2 | 1 |
| 10 RL compute feasibility | **5** | **5** | **1** | 2 | 2 | 1 | 5 | 5 |
| 11 RL precedent (comparison) | 1 | **5** | 1 | 3 | **5** | 1 | 5 | 2 |
| 12 Pump+PRV precedent | 1 | **5** | 1 | 1 | 2 | 1 | 5 | 5 |
| 13 Benchmark comparability | 2 | **5** | 4 | 4 | **5** | 1 | 5 | **1** |
| 14 Realism | 4 | 4 | **5** | 4 | 4 | 4 | **0** | 1 |
| 15 External validity | 4 | 3 | **5** | 4 | 4 | 3 | 1 | 1 |
| 16 Isolate pump contribution | **5** | 4 | 3 | 3 | **2** | 4 | **0** | 4 |
| 17 PDA vs DDA | 5 | 5 | 5 | 5 | 5 | 3 | 4 | 5 |
| 18 User base | 3 | **5** | 4 | 4 | **5** | 1 | 3 | 1 |
| **Weighted total /500** | **424** | 383 | 391 | 407 | **422** | 331 | 271 | 279 |
| **Normalised** | **84.8 %** | 76.6 % | 78.2 % | 81.4 % | **84.4 %** | 66.2 % | 54.2 % | 55.8 % |

## 3.3 Weight-sensitivity analysis (this is the decision framework)

`INFERENCE` — a single weighting is not evidence. I re-ran the ranking under four
alternative weightings that a reasonable examiner might prefer.

| Weighting | 1st | 2nd | 3rd | Net3 rank | J&X rank |
|---|---|---|---|---|---|
| **S1 baseline** | **BWSN-1 84.8** | D-Town 84.4 | C-Town 81.4 | 5th | 7th/8th |
| **S2 novelty-first** (precedent weights →1/1/2; placement transparency →14) | **BWSN-1 90.7** | D-Town 84.8 | C-Town 84.2 | **6th** | 7th/8th |
| **S3 compute-rich** (compute 9→3; realism→7, ext. validity→6) | **D-Town 86.8** | C-Town 83.8 | BWSN-1 83.6 | 5th | 7th/8th |
| **S4 comparability-first** (comparability→12, RL prec.→8, P+V prec.→6) | **D-Town 84.6** | **Net3 79.3** | C-Town 78.9 | **2nd** | 7th/8th |
| **S5 reproducibility-absolutist** (`.inp` and reproducibility →14 each) | **BWSN-1 86.5** | D-Town 86.2 | C-Town 83.5 | 5th | 7th/8th |

Robust conclusions that survive every weighting:

- `INFERENCE` **Jowitt & Xu is last or second-to-last in all five weightings**, in
  both unmodified and modified form. No reasonable weighting rescues it as a
  primary network.
- `INFERENCE` **Net3 never ranks first.** It reaches 2nd only under
  "comparability-first", i.e. only if matching Hu et al. (2023) is valued above
  placement transparency, realism and reproducibility combined. That is the
  precise, narrow condition under which keeping Net3 as primary would be
  rational — and it is not this thesis's condition, because §9 shows matching Hu
  too closely is a novelty *liability*, not an asset.
- `INFERENCE` **BWSN-1 and D-Town are genuinely close** (0.4 pp apart at
  baseline; they trade places under compute-rich and comparability-first). The
  real contest is BWSN-1 vs D-Town, **not** Net3 vs Jowitt & Xu. Earlier phases
  framed the wrong question.
- `INFERENCE` **L-Town is never first and never last.** That is the signature of
  an ideal *secondary* network: maximum realism and uncertainty documentation,
  disqualified as primary only by compute.

## 3.4 Why BWSN-1 over D-Town — the tie-break lives outside the table

Three reasons, none of which is captured by criteria 1–18:

1. `FACT` — D-Town has **11 pumps**; BWSN-1 has 2. `INFERENCE` — with 11 pumps the
   marginal contribution of variable-speed operation cannot be cleanly
   attributed, which defeats the thesis's strongest available novelty claim
   (§9, N6).
2. `FACT` — D-Town is the established RL pump-scheduling benchmark: Hajgató,
   Paál & Gyires-Tóth (2020, DDQN) and **Pei, Hoang, Fu & Butler (2025),
   JWRPM, doi 10.1061/JWRMD5.WRENG-6476 — PPO, Anytown + D-Town, demand
   uncertainty, GA / MPC / robust-optimisation baselines** both use it.
   `INFERENCE` — a PPO thesis on D-Town with demand uncertainty and GA baselines
   is in direct head-to-head with Pei et al. (2025), from the same institution
   (Exeter) as Negm, whose thesis this proposal builds on. That is the second
   worst novelty position after Net3.
3. `FACT` — BWSN-1 has 8 PRVs vs D-Town's 4 PRVs + 1 TCV. `INFERENCE` — the PRV
   vector is the thesis's core actuator; 8 continuous dimensions with settings
   spanning 16.45–80 psi gives a substantially richer coordination problem.

`INFERENCE` — **D-Town is the designated fallback.** If BWSN-1 turns out to have a
practical defect (e.g. PRV convergence failure under WNTR's PDA solver, which is
`UNKNOWN` until tested), switch to D-Town rather than back to Net3.

---

# 4. Jowitt & Xu Modification Audit

## 4.0 Facts established about Jowitt & Xu in this phase

`FACT` — primary source confirmed from Crossref/OpenAlex metadata: **Jowitt, Paul
& Xu, Chengchao (1990). "Optimal Valve Control in Water-Distribution Networks."
*Journal of Water Resources Planning and Management* 116(4):455–472, doi
10.1061/(ASCE)0733-9496(1990)116:4(455), 251 citations.** This closes gap G-A on
the citation. It does **not** close it on the model file.

`FACT` — **no public `.inp` for Jowitt & Xu was located.** WaterBenchmarkHub
contains 95 benchmark description files; `grep -ril "jowitt"` across the entire
repository returns zero matches. The network is absent from the single largest
curated WDN benchmark registry.

`FACT` — element counts disagree across secondary sources. Negm §5.2: "The
network consists of 22 nodes, 37 pipes and 3 tanks." Negm Table 5-5: "Jowitt &
Xu | 25 | 37 | 3 | 0 | 3 | 1" (25 junctions, 37 pipes, 3 valves, 0 pumps,
3 tanks/reservoirs, 1 DMA). `INFERENCE` — reconcilable as 22 demand junctions +
3 source nodes = 25 nodes, but the fact that it needs reconciling is itself the
finding.

`FACT` — Negm did not take the valve locations from Jowitt & Xu: "Due to the
extensive work on choosing the correct valve location in previous research, we
adopt three valve locations presented in (Araujo et al., 2006)", installed "on
pipes P31, P01, and P25 using invisible nodes Junc 16.5, Junc 13.5, and Junc 1.5
that don't affect the hydraulic simulation". Pipe properties, nodal emitter
coefficients and demand patterns were "all modelled after the standard test
network (Araujo et al., 2006, p. 138,139)".

`FACT` — Negm records the placement-bias problem himself: "the Jowitt & Xu valve
locations were based on optimised locations".

`FACT` — the network is still live in 2026: **Ferrarese, Fathi & Malavasi (2026),
*Water Resources Management* 40(9), doi 10.1007/s11269-026-04785-y** scale Jowitt
& Xu to a laboratory model (E-NET, flow-scale factor 4.33) and "PRVs were
implemented using a genetic algorithm (GA) to optimise both valve locations and
pressure settings", under "a pressure-dependent leakage model with a minimum
service pressure constraint", reporting "RMSE values of 0.38 m for head loss".
`INFERENCE` — GA-placed PRVs + pressure-dependent leakage on Jowitt & Xu is
*actively occupied ground as of 2026*, not an empty niche.

## 4.1 The audit

**Level 0 — use exactly as published (no modification).**

| Test | Verdict |
|---|---|
| Scientific | Yes, for a gravity PRV-only study. |
| Reproducible | **No, not fully.** `INFERENCE` — with no official `.inp`, "unmodified" already means *reconstructed from published tables* (Negm Tables 5-1, 5-2 + Araujo et al. 2006 pp. 138–139). Two researchers reconstructing independently can disagree, and the 22-vs-25 node discrepancy proves the risk is real. |
| Comparable | Yes to Negm (2024) and the classical J&X literature, **provided** the reconstruction matches. |
| Defensible | Yes as a *secondary replication* case. |
| Artificiality risk | Low. |
| Novelty-inflation risk | Low. |
| Required assumptions | That the reconstruction reproduces Araujo et al. (2006) exactly; that Negm's emitter coefficients (Table 5-1) and hourly factors Fc = 0.61–1.23 with source heads 54.0–56.0 m (Table 5-2) are transcribed correctly. |
| **Still the Jowitt & Xu benchmark?** | **Yes.** |
| **Fatal problem for this thesis** | `FACT` — 0 pumps. The VSP half of the research question cannot be posed at all. |

**Level 1 — parameterisation only (no new elements).**
Changes permitted at this level: add/alter `[EMITTERS]`, replace demand patterns
with a diurnal + stochastic model, switch `DEMAND MODEL` to PDA, change PRV
settings, change simulation duration and hydraulic timestep, perturb roughness
and diameters for uncertainty analysis.

| Test | Verdict |
|---|---|
| Scientific | Yes. `INFERENCE` — all of these are *operational-condition* changes; none alters what the network *is*. Negm already did most of them. |
| Reproducible | Yes, **conditional on** publishing the exact modified `.inp` alongside the thesis. |
| Comparable | Yes to Negm, provided the leakage model and demand model are stated. Not comparable to the original 1990 results, which used a different (linearised) hydraulic treatment. |
| Defensible | Yes. |
| Artificiality risk | Low. |
| Novelty-inflation risk | Low–moderate: "we added PDA" is not a contribution by itself. |
| Required assumptions | Emitter exponent (0.5 is conventional; must be stated, not assumed silently); the chosen minimum service pressure; the demand-uncertainty distribution. |
| **Still the Jowitt & Xu benchmark?** | **Yes, with a stated modification list.** |
| **Fatal problem for this thesis** | Unchanged: still 0 pumps. Level 1 cannot create a VSP. |

**Level 2 — topology change (add a pump; and/or add a booster, tank, new PRV
locations, new source behaviour, new control rules).**

| Test | Verdict |
|---|---|
| Scientific | **Conditionally yes, but weakly.** `INFERENCE` — a pump added to a gravity network needs a *fabricated* head curve, a fabricated efficiency curve, a fabricated location, and a fabricated speed range. None of these has an external authority. Four fabricated design decisions in the network that produces the headline result. |
| Reproducible | **Only self-reproducible.** No third party can regenerate the network; they can only re-run the thesis's own file. |
| Comparable | **No.** `INFERENCE` — the Negm comparison, which is the *only* reason to use Jowitt & Xu, is destroyed by the topology change: a pumped network's leakage baseline is different, so the 65.9 %/73.4 % water-saved figures are no longer commensurable. |
| Defensible | **No.** See the red-team question in §10 (Q4). |
| Artificiality risk | **High.** |
| Novelty-inflation risk | **High.** `INFERENCE` — building the network that the method then succeeds on is the classic form of this failure, and an examiner will name it. |
| Required assumptions | Pump location, head curve shape and rated point, efficiency curve, speed bounds, whether a new tank or booster station is added, revised control rules, revised source heads. All `UNKNOWN` and all author-chosen. |
| **Still the Jowitt & Xu benchmark?** | **No.** `INFERENCE` — it is a new network that borrows Jowitt & Xu's pipe layout. It should be named as such (e.g. "JX-P, a pumped derivative of Jowitt & Xu") and never described as "the Jowitt & Xu benchmark". |

## 4.2 Direct answer to the question "can Negm's network be reused with a pump and PRV added, and is that defensible?"

`INFERENCE`, stated plainly:

- **Reused unmodified, as a PRV-only secondary case: yes, and it is useful** —
  it is the only network on which a direct numeric bridge to Negm (2024) exists.
- **Reused with PRV settings/leakage/demand/PDA changed (Level 1): yes**, with a
  published modification list.
- **Reused with a pump added (Level 2), as the primary network: no.** It is not
  scientifically indefensible in the sense of being *wrong* — it is
  indefensible in the sense of being *unnecessary*, because BWSN-1, L-Town,
  C-Town, D-Town, Richmond and CY-DBP all ship a head-curve pump **and** PRVs
  already (`FACT`, §2). `INFERENCE` — fabricating a pump when six public
  benchmarks already have one is a choice an examiner will ask you to justify,
  and there is no good answer.

`INFERENCE` — this is the cleanest resolution of the tension the brief raised.
The Jowitt & Xu question was framed as "is modification allowed?". The evidence
reframes it: **modification is allowed but pointless**, because the modification's
only purpose (getting a pump) is already satisfied for free elsewhere.

---

# 5. Jowitt & Xu versus Net3 — 20-dimension head-to-head

This is the pairwise contest the brief asked for. `INFERENCE` — note in advance
that **both lose to BWSN-1** (§3); this section settles which of the two is the
better *fallback*, not which is best overall.

| # | Dimension | Jowitt & Xu | Net3 | Winner |
|---|---|---|---|---|
| 1 | Official public `.inp` | `FACT` none found; absent from WBH (0/95) | `FACT` yes, verified, multiple mirrors | **Net3** |
| 2 | Counts verifiable from a model file | `FACT` no — only from papers, and they disagree (22 vs 25 nodes) | `FACT` yes — 92 / 2 / 3 / 117 / 2 / 0 parsed directly | **Net3** |
| 3 | Native pumps | `FACT` **0** | `FACT` **2, both `HEAD` curve** | **Net3, decisively** |
| 4 | Native PRVs | `FACT` 0 native; the 3 used by Negm come from Araujo et al. (2006) | `FACT` **0** (`[VALVES]` empty) | Tie (both zero) |
| 5 | Storage dynamics | `FACT` 3 tanks/sources at fixed hourly heads 54.0–56.0 m (Negm Table 5-2) | `FACT` 3 tanks + 2 reservoirs (River 220, Lake 167) with genuine level dynamics | **Net3** |
| 6 | Native extended-period simulation | `INFERENCE` 24 h implied by the 24 hourly load factors | `FACT` `Duration 24:00`, `Hydraulic Timestep 1:00` | **Net3** |
| 7 | Demand-pattern realism as shipped | `FACT` single 24-point factor series, Fc = 0.61–1.23 | `FACT` multiple 24 h patterns | Net3, marginally |
| 8 | Leakage model shipped | `FACT` none in the model; but Negm publishes per-node emitter coefficients (Table 5-1) | `FACT` none; `[EMITTERS]` empty | **J&X** (published coefficients are a real asset) |
| 9 | PDA needed from the researcher | Yes | Yes | Tie |
| 10 | PRV-placement authority | `FACT` Araujo et al. (2006), GA-optimised | `FACT` none — the thesis must invent it, or copy Hu's GA placement | **J&X** (at least there is a citable source) |
| 11 | Placement-bias exposure | **High** — `FACT` Negm: "based on optimised locations" | **High** — `INFERENCE` any placement is the thesis's own, or copies Hu's leakage-optimised GA placement | Tie (both bad) |
| 12 | RL precedent on the network | `FACT` Negm (2024) doctoral thesis + Negm et al. (2023) Q-learning, doi 10.1109/CAI54212.2023.00120 | `FACT` Hu, Gao & Zhong (2023) MADDPG, doi 10.2166/ws.2023.163; Hu et al. E-PPO (MDPI *Systems*) | **Net3** (peer-reviewed journal precedent) |
| 13 | Joint pump+PRV precedent on the network | `FACT` none (impossible — no pump) | `FACT` **yes, Hu 2023 — continuous VSP 0.7–1.0 + PRV outlet pressure** | J&X "wins" only in the sense of being unoccupied |
| 14 | Novelty headroom given (12)+(13) | Moderate: Negm's §7.3 explicitly leaves pumps as future work | **Low: the exact environment is published** | **J&X** |
| 15 | Comparability to Negm (2024) | **Direct** — same network, same PRV locations, same emitter coefficients | None | **J&X** |
| 16 | Comparability to Hu et al. (2023) | None | **Direct** | **Net3** |
| 17 | Compute per episode | `INFERENCE` ~24 steps, 25 nodes — cheapest possible | `FACT` 24 steps, 92 junctions — very cheap | Tie |
| 18 | Provenance / realism | `INFERENCE` 1990 synthetic UK test network, no utility attribution located | `FACT` EPA EPANET example network; real-system basis `UNKNOWN` | Net3, weakly |
| 19 | External validity | Low — 25 nodes, no pump, single DMA | Low–moderate — 92 junctions, 2 sources, 2 pump stations | **Net3** |
| 20 | Ability to isolate the pump's contribution | **None** — no pump to isolate | Possible — 2 pumps, and a PRV-only ablation is available | **Net3** |

**Score: Net3 wins 10 dimensions, Jowitt & Xu wins 5, 5 are ties.**

## Winner: **Net3** — but it is the winner of a contest neither should have entered

`INFERENCE` — Net3 beats Jowitt & Xu on every *structural* dimension (pumps,
storage, EPS, model-file availability, verifiability) and loses only on
*positioning* dimensions (novelty headroom, comparability to Negm). That is
exactly the trade the brief warned about: keeping Net3 buys hydraulic capability
and pays for it in novelty, because Hu et al. (2023) already published the
environment.

`INFERENCE` — the decisive observation is that **the two dimensions Jowitt & Xu
wins (14 and 15) are both satisfiable without using Jowitt & Xu as the primary
network**: novelty headroom is obtained by moving to a network with no RL
precedent at all (BWSN-1), and comparability to Negm is obtained by keeping
Jowitt & Xu as an unmodified tertiary case. There is no dimension on which
Jowitt & Xu must be primary.

---

# 6. Does Jowitt & Xu belong in the main experiment at all?

The brief specified three models. `INFERENCE` — the evidence forces a fourth, so
it is scored alongside them rather than smuggled in later.

- **Model A** — Net3 only.
- **Model B** — Net3 main + Jowitt & Xu secondary.
- **Model C** — modified (Level 2, pumped) Jowitt & Xu main + Net3 secondary.
- **Model D** — **BWSN-1 primary + Net3 secondary + unmodified Jowitt & Xu
  optional tertiary.**

Scores 0–5, unweighted, seven criteria as specified.

| Criterion | A | B | C | **D** |
|---|---|---|---|---|
| Scientific validity | 3 | 3 | **2** | **5** |
| Novelty | **1** | 2 | 2 | **4** |
| Fairness of comparison | 2 | 3 | **1** | **5** |
| Computation | 5 | 5 | 5 | 4 |
| Schedule feasibility | 5 | 4 | 4 | 4 |
| Reproducibility | 4 | 3 | **1** | **5** |
| Viva defensibility | 2 | 3 | **1** | **5** |
| **Total /35** | **22** | **23** | **16** | **32** |

Reasoning behind the low marks:

- **Model A scores 1 on novelty** because `FACT` Hu, Gao & Zhong (2023) published
  the environment on Net3 — GA-placed PRVs, emitter leakage on every node
  downstream of the pumps, VSP speed 0.7–1.0, PRV outlet-pressure actions,
  truncated-normal demand multipliers 0.7–1.3, tank-level state, energy+leakage
  reward, GA/PSO/DE baselines. `INFERENCE` — swapping MADDPG for PPO inside that
  environment is an algorithm study, not a thesis contribution.
- **Model C scores 1 on reproducibility and 1 on defensibility** because `FACT`
  no public Jowitt & Xu `.inp` exists and a Level 2 pump addition requires four
  fabricated design decisions (§4.1). `INFERENCE` — the headline result would be
  produced on a network built by the author, for the author's method.
- **Model D scores 4 rather than 5 on computation and schedule** because `FACT`
  BWSN-1's native `Duration 96:00` at `Hydraulic Timestep 0:30` is 192 steps per
  episode against Net3's 24. `INFERENCE` — roughly 8× the per-episode hydraulic
  cost of Net3 at 1.4× the node count. That is a real cost, and it is the only
  respect in which Model D is worse than Model A. Actual wall-clock is `UNKNOWN`
  until profiled.

## Answer

`INFERENCE` — **Jowitt & Xu does not belong in the main experiment.** It belongs
in the thesis as an *unmodified* tertiary replication case whose sole job is to
provide a direct numeric bridge to Negm (2024), and it should be dropped without
regret if the schedule tightens. Its `FACT`-level disqualifiers as a main network
are: zero pumps, no public model file, and absence from the largest benchmark
registry.

---

# 7. The PRV Placement Problem

## 7.1 The five placement paradigms

| Paradigm | What it optimises | Example evidence | Bias exposure |
|---|---|---|---|
| **GA / metaheuristic optimised** | an explicit objective, usually leakage or excess pressure | `FACT` Hu 2023: "Four valves with the greatest impact on leakage were added to the network through a pre-experiment using a GA"; `FACT` Araujo et al. (2006) locations adopted by Negm; `FACT` Ferrarese et al. (2026) "a genetic algorithm (GA) to optimise both valve locations and pressure settings"; `FACT` Nanehkaran et al. (2026) NSDE + Shrimp | **Highest** |
| **Operational / legacy** | historical utility objectives (DMA inflow, tank filling), *not* leakage | `FACT` Negm on SZ08: "SZ08's valves have been placed many years ago to control the inflow to DMAs and tanks amongst other objectives" | **Lowest** |
| **Pressure-zone boundary** | hydraulic separation of zones | `FACT` L-Town: "PRVs are also installed downstream of the two main reservoirs, to help regulating the pressure" (BattLeDIM v1.3.1) | Low |
| **Critical-node driven** | pressure at the worst-served node | `FACT` Mosetlhe et al. (2020) place 5 PRVs on pipes 1, 9, 10, 17, 21 and 7 PRVs at 1, 3, 5, 20, 46, 99, 102 | Moderate |
| **Leakage-based (direct)** | leakage volume alone | same as GA row; `FACT` Nanehkaran et al. (2026) report 1 PRV → 8.616 % excess-pressure reduction, 5 PRVs → 55.262 %, 6 → 55.287 %, 7 → 55.456 % | **Highest** |

`INFERENCE` from the Nanehkaran numbers — the marginal value of an additional PRV
collapses after roughly five valves (55.262 % → 55.456 % from 5 to 7). This is
useful for this thesis: BWSN-1's 8 PRVs sit past the saturation point, so the
result should not be knife-edge sensitive to which subset of them is controlled.

## 7.2 Does Hu's four-valve GA placement induce objective co-optimisation bias?

**Yes.** `FACT` — Hu's selection criterion was the valves "with the greatest
impact on **leakage**". `FACT` — Hu's reward contains a leakage cost term
`C_l · (b_k L_i / 2) · P_{i,t}^{a_k} · ΔT`. `INFERENCE` — the environment's
topology was therefore selected using the same quantity the agent is later
rewarded for reducing. Three consequences:

1. **Inflated absolute performance.** `INFERENCE` — the reported leakage
   reduction is conditioned on a near-best-case valve layout. It is an upper
   bound on what the same controller would achieve on a real network.
2. **Invalid cross-network comparison.** `FACT` — Negm states the mechanism
   directly: the Jowitt & Xu valve locations "were based on optimised locations
   … Hence, valve control is expected to be less effective in NWL's case study"
   (SZ08, legacy placement). `INFERENCE` — any claim of the form "our controller
   achieves X % on network 1 and only Y % on network 2" is confounded by
   placement provenance unless provenance is held constant or reported.
3. **Design-time objective leakage.** `INFERENCE` — structurally this is the same
   error as selecting features on the test set: information about the evaluation
   objective enters the experimental setup before learning begins. It is not
   fraud and it is common practice, but it must be disclosed, and it cannot
   support a claim about performance on real networks.

`FACT` (gap G-B, now closed) — **BWSN-1's own PRVs are also inserted rather than
organic.** Each of the 8 PRVs sits on a dedicated valve link between a paired
artificial node couple (`JUNCTION-111/112`, `113/114`, `115/116`, `117/118`,
`119/120`, `121/122`, `123/124`, `125/126`), with exactly one incident pipe on
each side — e.g. `LINK-25 JUNCTION-15→JUNCTION-111`, valve `VALVE-173
111→112`, `LINK-26 JUNCTION-112→JUNCTION-14`. The IDs run sequentially above the
main junction numbering, and the pumps occupy the adjacent block
(`JUNCTION-105/106`, `109/110`). `INFERENCE` — this is the same "invisible node"
insertion device Negm describes, so BWSN-1's valves were *designed into the
published benchmark by its authors*, not inherited from a real utility's asset
register.

`INFERENCE` — the honest claim is therefore narrower than "BWSN-1 has real
valves", and it is still sufficient: **BWSN-1's PRV placement was fixed by a
third party (the BWSN competition organisers), published in 2008, for a
competition about contamination-sensor placement — an objective unrelated to
leakage.** The placement is consequently *not* co-optimised with this thesis's
reward. That is exactly the property the thesis needs, and it is the property
Net3 cannot provide at all.

`FACT` — the layout carries genuine zone structure: `[CONTROLS]` closes
`VALVE-180` at time 0, and `LINK-0` (7,401 ft, 20.45 in) joins `JUNCTION-118`
(downstream of `VALVE-176`) to `JUNCTION-126` (downstream of `VALVE-180`), so
that transmission path is fed through `VALVE-176` alone in the shipped
configuration. PRV settings span 16.45–80 psi on 6–10 in valves.
`INFERENCE` — there are real, distinct pressure zones with real surplus, and PRV
coordination genuinely redistributes pressure between them rather than acting on
one isolated branch.

## 7.3 The three candidate designs

| Design | What it is | Strength | Fatal weakness |
|---|---|---|---|
| **D1 — Hu replication** | copy Hu's GA placement on Net3 and run PPO | Only design that yields a like-for-like comparison with Hu 2023 | `INFERENCE` inherits Hu's co-optimisation bias in full; cannot support any claim about real networks |
| **D2 — operational placement** | use placement fixed by a third party for an unrelated objective (BWSN-1's 8 PRVs; L-Town's 3) | `INFERENCE` no co-optimisation with the reward; placement attributable to a citable authority; removes the strongest examiner attack | No published RL numbers on the same network to compare against |
| **D3 — dual placement** | run **both** on the primary network: native placement as the headline, plus a GA-placed variant as a *sensitivity* study | `INFERENCE` strongest of the three: it reports the headline on unbiased placement **and quantifies how much of the literature's reported gain is attributable to placement optimisation rather than to control** | Costs one extra experimental arm |

## 7.4 Recommendation

`INFERENCE` — **D3, with D2 as the headline arm and D1 retained as the Net3
comparability arm.** Concretely:

- **Headline (BWSN-1, native 8 PRVs)** — all main results, ablations,
  uncertainty, Pareto analysis, seed statistics.
- **Sensitivity (BWSN-1, GA-selected subset of the 8)** — reported as a
  placement-sensitivity ablation only. `INFERENCE` — because it selects a *subset
  of existing* valves rather than inventing locations, it isolates the placement
  effect without changing the topology, which is a cleaner experiment than Hu's.
- **Comparability (Net3, Hu's placement replicated)** — the only arm where
  Hu-style bias is deliberately accepted, and it must be labelled as such in the
  thesis text.

`INFERENCE` — the sensitivity arm converts the placement-bias problem from a
threat into a *result*: "how much of the reported benefit of RL pressure control
in the literature comes from the controller, and how much from having optimised
the valve locations first?" No paper in the reviewed set answers this.

---

# 8. Joint decision: network × PRV placement

Cells: ✔ viable / ⚠ viable with a stated caveat / ✘ not viable.

| Network | Native placement (D2) | GA / leakage-optimised (D1) | Invented by author | Verdict |
|---|---|---|---|---|
| **BWSN-1** | ✔ **8 PRVs, BWSN 2008 authority, objective unrelated to leakage** | ⚠ only as a *subset-selection* sensitivity arm | not needed | **Primary** |
| Net3 | ✘ no valves exist | ⚠ acceptable **only** to replicate Hu 2023 | ⚠ unavoidable otherwise | **Secondary, comparability only** |
| L-Town | ✔ 3 PRVs, BattLeDIM authority | ⚠ possible | not needed | Generalisation case if compute allows |
| C-Town | ✔ 3 PRV + 1 FCV, BWCN authority | ⚠ possible | not needed | Alternative primary |
| D-Town | ✔ 4 PRV + 1 TCV, BWN-II authority | ⚠ possible | not needed | **Designated fallback primary** |
| CY-DBP | ✔ 2 PRVs | ⚠ possible | not needed | Rejected: 0:05 timestep, no pressure-control lineage |
| Jowitt & Xu (unmod.) | ⚠ Araujo et al. 2006, **GA-optimised** | already the case | — | Tertiary replication only |
| Jowitt & Xu (Level 2) | ✘ | ✘ | ✘ | **Rejected** (§4.1) |
| Kentucky series | ✔ up to 56 PRVs | — | — | ✘ `Duration 0`, empty `[CURVES]`, `POWER` pumps |

`INFERENCE` — exactly one cell is unconditionally clean: **BWSN-1 with its native
8 PRVs.** Every other viable configuration carries at least one caveat that must
be written into the thesis text.

---

# 9. Novelty Re-audit

`Conf.` = my confidence in the assessment, not in the claim being true.
`Search gap` = what would still have to be checked before the claim is asserted
in the thesis.

| # | Claim | Closest prior work | Year | Exact overlap | Remaining difference | Novelty | Conf. | Search gap |
|---|---|---|---|---|---|---|---|---|
| **N1** | First continuous action space for WDN pressure control | Negm, doctoral thesis, Exeter — "The only available continuous space in GYM is the Box space"; action bounds "0 to 70 for valves and unbounded speeds for the pumps" | 2024 | **Total** | none | **REJECTED — do not claim** | High | none |
| **N2** | First EPANET + PPO | Hu et al., E-PPO (MDPI *Systems*); **Pei, Hoang, Fu & Butler, JWRPM, doi 10.1061/JWRMD5.WRENG-6476 — PPO on Anytown + D-Town**; Xu et al., KA-PPO | 2021–2025 | **Total** | none | **REJECTED — do not claim** | High | none |
| **N3** | First coordinated PRV + pump control | Shao et al., *Energies* 12(15):2969 — GA co-optimising PRVs and variable-speed pumps for leakage + energy; Brentan et al. — near-real-time PSO of pumps and valves; Hu, Gao & Zhong — MADDPG | 2018–2023 | **Total** | RL vs metaheuristic only | **REJECTED — do not claim** | High | Shao 2019 full text not read |
| **N4** | First multi-objective reward for pressure/leakage | Hu 2023 — energy + leakage + tank penalty; Negm 2024 — leakage:pressure 3:1; Xu 2021 — heads + water age + efficiency | 2021–2024 | **Total** | none | **REJECTED — do not claim** | High | none |
| **N5** | First DRL pressure/leakage study on BWSN-1 | none found | — | none | whole study | **Moderate** (true but low-value on its own) | Medium | Abstract-level indexing only; a conference paper could exist |
| **N6** | **Ablation isolating the marginal contribution of variable-speed pump operation under coordinated PRV control** | Negm §7.3 names it as *future work*: "Incorporating other pressure influencing network elements such as pumps … Adding pumps to the pressure management system will improve the agent performance hydraulically" | 2024 | none — Negm proposes, does not do | the entire ablation (PRV-only vs VSP-only vs joint on one network) | **HIGH** | High | none — Negm's own text authorises it |
| **N7** | **Out-of-distribution robustness of a joint PRV+VSP controller** | Hu 2023 — `FACT` "We tested the MADDPG, GA, PSO, and DE models for five random test cases from **the same distribution of the training**"; Pei 2025 — robustness to demand uncertainty, **pumps only, no PRVs** | 2023–2025 | Pei covers OOD-ish demand robustness for pumps; Hu covers in-distribution only for pump+PRV | OOD **and** joint PRV+VSP **and** leakage objective, together | **HIGH** | Medium-High | Pei 2025 full text not read — must confirm whether their test demands are out-of-distribution or merely stochastic |
| **N8** | **Separating model-parameter uncertainty from demand uncertainty** | BattLeDIM declares "no greater than 10% of the nominal values" for diameters/roughness, but as a *detection* challenge; Hu varies demand only | 2020–2023 | none in a DRL control setting | roughness/diameter perturbation as a distinct uncertainty axis in training vs test | **HIGH** | Medium | 2024–2026 domain-randomisation-in-WDN sweep not exhaustive |
| **N9** | PDA vs DDA under DRL pressure control | Negm evaluates three hydraulic states (perfect / leaking / solved) but not PDA vs DDA; LeakDB lineage uses "pressure-driven demands" | 2018–2024 | partial — PDA is used, never *contrasted* with DDA | the contrast itself, and its effect on learned policy and reported leakage | **Moderate–High** | **Low–Medium** | **Real gap.** Must search "pressure-driven demand" + reinforcement learning explicitly before claiming |
| **N10** | **Pareto / constraint-matched evaluation instead of a scalarised cost** | Hu 2023 reports aggregate \$/day; Negm reports scalar reward at a fixed 3:1 weight and states "a ratio of 3:1 favouring the leakage objective produces the best trade-off" | 2023–2024 | none — both scalarise | reporting the trade-off surface and comparing methods at *matched* constraint-violation budgets | **HIGH** | High | none |
| **N11** | **Quantifying how much of the reported RL benefit comes from optimised valve placement rather than from control** | Negm observes the mechanism qualitatively ("valve control is expected to be less effective in NWL's case study"); nobody quantifies it | 2024 | qualitative observation only | the quantification | **HIGH — freshest claim in this list** | Medium-High | Placement-sensitivity literature outside DRL not exhaustively searched |
| **N12** | Multi-seed statistical reporting | Neither Hu 2023 nor Negm 2024 reports seed variance; **Jun, Yoo & Jung, JWRPM, doi 10.1061/JWRMD5.WRENG-6868, "Toward Transparent and Reproducible Machine Learning–Based Research in Urban Water Networks"** demands exactly this | 2025 | Jun et al. prescribe it; this thesis would apply it | application to DRL pressure control | **Low novelty, high defensibility** | High | none |
| **N13** | Single-agent PPO vs multi-agent MADDPG for joint PRV+VSP | Hu 2023 (MADDPG); Negm 2024 (single-agent PPO, PRVs only) | 2023–2024 | both halves exist separately | the controlled comparison on one network | **Moderate** | High | none |
| **N14** | A reproducible open RL environment on a public benchmark | **Locatelli et al., *Internet of Things*, doi 10.1016/j.iot.2026.101911 — "TwinAI", with "Dyn-WNTR, an extension of the widely used WNTR simulator that supports dynamic interaction during runtime"**; Javed et al. 2025 name the absence of benchmark environments as a recurring gap | 2025–2026 | **Substantial** — a runtime-interactive WNTR extension now exists | ours would be pressure/leakage-specific on a named benchmark with published configs | **Low–Moderate** | Medium | TwinAI full text not read; must check whether Dyn-WNTR is released |
| **N15** | Correcting the claim that continuous-action RL pressure control is unexplored | **Cyriac & Chacko, JWRPM, doi 10.1061/JWRMD5.WRENG-7303: "previous work focused on improving pump efficiency and have overlooked pressure control using RL with continuous action spaces"** | 2026 | — | `INFERENCE` this statement is contradicted by Negm (2024) and Hu et al. (2023); a short, sourced correction is a legitimate scholarly note | **Low novelty, real value** | High | Paywalled — abstract only. Do not characterise their method beyond the abstract |
| **N16** | Transferability across network topologies | Javed et al., *Water* 17(13):1928 — "Most DRL models are network-specific and require retraining"; listed among "Recurring gaps … limited transferability across network topologies" | 2025 | named as an open gap | a zero-shot / fine-tune transfer test BWSN-1 → Net3 → L-Town | **Moderate** | Medium | Only worth claiming if the transfer experiment is actually run |

## 9.1 Direct answer on Cyriac & Chacko 2026 (gap G-E, now closed at abstract level)

`FACT` — **Cyriac, Unni & Chacko, Sibi (2026). "Deep Reinforcement Learning for
Pressure Optimization in Water Distribution Networks with Multiple Pumping
Stations." *Journal of Water Resources Planning and Management*, published
2026-05-05, doi 10.1061/JWRMD5.WRENG-7303. Heriot-Watt University Malaysia.
Closed access; 0 citations at time of search.** From the publisher abstract,
verbatim: the study is "a case study on a WDN in **Abu Dhabi**"; "A custom
training environment was developed using the Gym framework, integrating a
calibrated hydraulic model of the network"; "The DRL agent was trained to
dynamically adjust the **pumping station pressure setpoints** to control the
maximum pressure across the network while maintaining the required minimum
pressure within all DMAs."

`INFERENCE` — three differences protect this thesis, and one warning follows:

1. **Their actuator is pumping-station pressure setpoints, not PRV settings and
   not pump speed.** Different action variable, different physics.
2. **Their network is a private Abu Dhabi utility model, not a public
   benchmark.** `INFERENCE` — their result cannot be reproduced or contested by
   anyone. This thesis's use of a public benchmark with a published `.inp` is a
   genuine, defensible differentiator, and it is exactly the gap Javed et al.
   (2025) and Jun et al. (2025) both name.
3. **No leakage objective, no PRVs and no demand-uncertainty treatment appear in
   the abstract.** `UNKNOWN` for the full text.
4. **Warning:** they publish the priority claim on "pressure control using RL
   with continuous action spaces" in a top journal. `INFERENCE` — this thesis must
   *not* make the same claim, must cite them, and may note in one sentence that
   their framing overlooks Negm (2024) and Hu et al. (2023).

## 9.2 What the adversarial search did and did not find (gap G-F)

`FACT` — OpenAlex title+abstract search, all years:
`"pressure reducing valve" AND ("reinforcement learning" OR "deep reinforcement")`
→ **2 results total**: Negm et al. (2023) Q-learning, and one 2021 *Water* paper
on pressure control's impact on leakage. `"variable speed pump" AND
"reinforcement learning"` → 2 results, both an arXiv preprint on pumped-storage
hydropower, not WDN. `("C-Town" OR "D-Town" OR "L-Town" OR "Anytown" OR "BWSN")
AND "reinforcement learning"` → 6 results, **none on BWSN-1, C-Town or L-Town for
pressure control**.

`INFERENCE`, with the caveat stated plainly: **these counts understate the field,
because OpenAlex indexes abstracts, not full texts.** Hu, Gao & Zhong (2023) — the
single most relevant paper — does **not** appear in the PRV query, because its
abstract says "valve" rather than "pressure reducing valve". `INFERENCE` — the
"2 results" figure must therefore **never** be quoted in the thesis as proof of
novelty. It may only be quoted as evidence that the intersection is
under-represented in indexed abstracts, alongside the counter-example.

`FACT` — a forward-citation sweep of Hu 2023 (15 citing works), Negm 2023
(4), Javed 2025 (17), Pei 2025 (17) and Hajgató 2020 (89) surfaced no paper
performing joint continuous PRV + variable-speed-pump DRL control on a public
benchmark under demand uncertainty. The nearest 2026 works are: Cyriac & Chacko
(pumping-station setpoints, private network); Jeung et al., *Water Research X*,
doi 10.1016/j.wroa.2026.100540 (double-DQN, **discrete**, valve/hydrant flushing
for **contamination**, not pressure); Locatelli et al. (graph RL, leak isolation
and flow rerouting, not pressure setting); and Nanehkaran et al., *Frontiers in
Earth Science*, doi 10.3389/feart.2026.1847899 (**classical** NSDE + Shrimp PRV
placement on the Khorramshahr network, no RL).

`FACT` — one 2026 item was found in a venue I cannot verify as peer-reviewed to a
normal standard (Korviakov, *World Journal of Civil Engineering and
Architecture*, doi 10.31586/wjcea.2026.6596, single author, hierarchical RL +
digital twin on a "2,400-node benchmark network"). `INFERENCE` — recorded for
completeness; not treated as evidence and not to be cited without independent
verification.

---

# 10. Red team: 18 examiner questions and defensive answers

Answers are written the way they should be said in a viva: short, sourced, no
hedging where evidence exists, explicit concession where it does not.

**Q1. Why not Net3? Everyone uses it.**
Because Net3's `[VALVES]` section is empty — 92 junctions, 117 pipes, 2 pumps,
**0 valves**. Every PRV would be mine. The thesis would then be reporting the
performance of my own valve-siting decisions as if it were a controller result.
BWSN-1 ships 8 PRVs placed by the BWSN organisers in 2008. I keep Net3 as a
secondary network purely so my numbers are comparable with Hu, Gao & Zhong (2023).

**Q2. So you chose BWSN-1 because it was convenient.**
No — because it is the only public benchmark whose PRVs were placed by a third
party for an objective unrelated to leakage. That makes the valve locations
exogenous to my reward function. That property is the whole point, and only
BWSN-1, C-Town, D-Town, L-Town and the Kentucky files have it at all; of those,
BWSN-1 is the only one in a size band that permits multi-seed PPO training.

**Q3. BWSN-1's PRVs were also inserted by its authors. How is that different from
inserting your own?**
It is different in one respect that matters and no others: the placement was not
chosen by me, and not chosen to make leakage control look good. BWSN-1 was built
for contamination sensor placement. I state this limitation explicitly rather
than claiming the valves are "real".

**Q4. Isn't 126 junctions too small to be realistic?**
Yes, for external validity. That is why the design includes L-Town (782
junctions, real-scale demand structure) as a generalisation case. But the primary
network must permit ≥5 seeds × 3 configurations of PPO training within a
Master's schedule. BWSN-1 is 192 hydraulic steps per episode; L-Town is 2,016.
`UNKNOWN` — the actual wall-clock ratio is untested, so this is a design margin,
not a measured claim.

**Q5. You are adding leakage to a network that has none. Isn't that fabrication?**
Every candidate network has an empty `[EMITTERS]` section — I verified this
directly in all 13 `.inp` files I parsed. Leakage must be added in every case, so
it is not a discriminator between networks. It is a modelling assumption I declare
and parameterise, following the same emitter-exponent convention used by LeakDB
and by Negm (2024).

**Q6. You are making a pump variable-speed. That is a topology change.**
It is not. Relative pump speed is a native EPANET pump property, and BWSN-1's two
pumps already run on head curves (`CURVE-0`, `CURVE-2`), which is what affinity-law
speed scaling requires. Nothing is added to the network; a property that exists is
made controllable. The contrast is with the Kentucky files, which declare pumps by
`POWER` with an empty `[CURVES]` section — there, VSP control would require
inventing a pump curve.

**Q7. Why not Jowitt & Xu, to compare directly with Negm?**
Three reasons. It has **0 pumps**, so the pump half of my research question is
unaskable on it. There is **no official `.inp`** — I searched WaterBenchmarkHub's
95 benchmark files and found zero mention of it — so "unmodified" would really mean
"reconstructed from a 1990 paper", which is less reproducible than a distributed
model file. And adding a pump makes it no longer Jowitt & Xu, at which point I
have a synthetic network with none of the comparability I was trying to buy.

**Q8. Then you cannot compare with Negm at all.**
I can compare *method against method* on a common network, which is the stronger
comparison. Negm's PPO formulation is reproducible on BWSN-1. What I lose is
comparison of *absolute* numbers on Negm's own network, which were never
transferable anyway — his network has different topology, different demands and
different valve placement.

**Q9. Negm already did PPO with continuous actions on PRVs. What is left?**
Not the algorithm. Negm reports agents reaching roughly 73 % water saved with
264–304 pressure violations, while his classical optimisers reached 64–66 % with
46–78 violations. `INFERENCE` — that is not a better controller, it is a different
point on a trade-off curve, produced by a 3:1 leakage weighting. My contribution
is to evaluate at *matched* violation budgets and report the trade-off surface,
plus the pump ablation his own §7.3 asks for.

**Q10. Hu et al. 2023 did pumps and valves with MADDPG. Isn't your work a subset?**
`FACT` — Hu tested "five random test cases from the same distribution of the
training". There is no out-of-distribution test, no model-parameter uncertainty,
no seed variance, and the valve locations were chosen by a GA on the same
objective the controller optimises. My contribution sits precisely in those four
holes, not in re-doing the controller.

**Q11. Cyriac & Chacko (2026) claim they were first to do continuous-action RL
pressure control. Are you scooped?**
No, and their claim is contestable. They control **pumping-station pressure
setpoints** on a **private Abu Dhabi network**, with no PRVs and no leakage
objective in the abstract. I cite them, I do not repeat their priority claim, and
I note in one sentence that continuous-action RL pressure control already existed
in Negm (2024) and Hu et al. (2023).

**Q12. Pei et al. (2025) already published PPO with demand-uncertainty robustness
against GA and MPC baselines on Anytown and D-Town.**
Correct, and that is why D-Town is not my primary network and why I do not claim
novelty on "PPO under demand uncertainty". Their actuator set is pumps only — no
PRVs, no pressure/leakage objective. My claim is narrower and survives: joint
PRV + variable-speed-pump control, evaluated out-of-distribution, with the pump's
marginal contribution isolated. `UNKNOWN` — I have not read their full text; no
green open-access copy exists. This is stated as a limitation.

**Q13. How do you know nobody has done this? You searched abstracts.**
I do not claim exhaustiveness, and I say so. `FACT` — the OpenAlex query for
"pressure reducing valve" AND reinforcement learning returns only 2 results in
all years, yet Hu et al. (2023) — the most relevant paper in the field — is not
among them, because its abstract says "valve". I found it by reading full texts.
I report the search counts as evidence of under-indexing, never as proof of
novelty, and I name the search gaps explicitly (§9, `Search gap` column).

**Q14. Your reward is multi-objective. How do you know the agent is not reward
hacking?**
That is the reason for constraint-matched evaluation rather than scalar reward
comparison. Negm's own results show the signature — large leakage gains bought
with 4–6× the pressure violations of a classical optimiser under a 3:1 weighting.
I report violations as a separate, non-negotiable axis and compare methods at
equal violation budgets.

**Q15. PDA or DDA? And does it change your conclusions?**
PDA (EPANET 2.2 `DEMAND MODEL PDA`), because under leakage and pressure reduction
DDA will silently deliver demand at physically impossible pressures and overstate
achievable savings. `UNKNOWN` — the size of that overstatement in my setting is
untested; measuring it is a planned result, not an assumption.

**Q16. If your valve locations are exogenous, aren't they also suboptimal?**
Yes, and deliberately. `FACT` — Nanehkaran et al. (2026) report excess-pressure
reduction of 8.6 % with 1 PRV rising to 55.3 % with 5 and only 55.5 % with 7 on
their case network: the marginal value of additional valves saturates by about
five. `INFERENCE` — with 8 native PRVs, BWSN-1 sits past that saturation point, so
results should not be knife-edge sensitive to which subset is controlled. The
sensitivity arm tests this directly instead of assuming it.

**Q17. What if BWSN-1 will not converge in WNTR with PRVs under PDA?**
Then the design falls back to D-Town, which ranked 422/500 against BWSN-1's
424/500 — a 0.4-point gap, i.e. the ranking does not depend on winning that
contest. `UNKNOWN` — convergence is untested; this is the single most important
thing to check in the first week of implementation, before any experiment is
designed around the network.

**Q18. What is the one-sentence contribution?**
A reproducible, out-of-distribution-tested PPO controller for coordinated PRV and
variable-speed-pump operation on a public benchmark with third-party valve
placement, which isolates the pump's marginal contribution and reports the
leakage/service trade-off surface instead of a single scalarised cost.

---

# 11. Final Recommendation

## Selected: **OPTION 4 — a network not previously on the shortlist**

> **BWSN-1** (`BWSN_Network_1.inp`) as the **primary** network.
> **Net3** as a **mandatory secondary** network, for one purpose only: numerical
> comparability with Hu, Gao & Zhong (2023).
> **Unmodified Jowitt & Xu** as an **optional tertiary** replication, for one
> purpose only: comparability with Negm (2024). Droppable without damaging the
> thesis if the schedule tightens.
> **PRV design D3 (dual placement):** native 8 PRVs as the headline configuration;
> a GA-selected subset *of those same 8* as a placement-sensitivity arm; Net3 with
> Hu's four GA-placed valves as the comparability arm.
> **Fallback primary if BWSN-1 proves hydraulically unworkable: D-Town** — not
> Net3.

`FACT` — BWSN-1 profile, counted directly from the distributed `.inp`: 126
junctions, 1 reservoir, 2 tanks, 168 pipes, 2 pumps on head curves, **8 PRVs**,
4 `[RULES]` linking both pumps to tank levels, `Duration 96:00` at a `0:30`
hydraulic step (192 steps per episode), GPM/H-W units, `[EMITTERS]` empty.

`FACT` — the 8 PRVs sit on dedicated valve links between paired artificial nodes
(`JUNCTION-111/112` … `125/126`), one incident pipe per side, with `LINK-0`
(7,401 ft, 20.45 in) joining the downstream sides of `VALVE-176` and `VALVE-180`
— a genuine parallel-feed / zone-boundary structure, not decorative valves in
series on a single main.

`INFERENCE` — this configuration is the only one in the entire landscape where
the valve locations are **exogenous to the reward function** while a
head-curve pump exists in the same model. That single property is what the
recommendation turns on.

## Why the other three options were rejected

| Option | Rejected because | What would have been gained | What would have been lost |
|---|---|---|---|
| **OPTION 1** — Net3 primary + J&X secondary | Net3 has **0 valves**; all PRVs would be author-placed and Hu (2023) already occupies that exact configuration. Scored 23/35 in §6 and **never ranked first in any of the five sensitivity scenarios** in §3. | Maximum comparability with Hu 2023; smallest compute; largest user base | Placement exogeneity; the strongest novelty claim (N11); the ability to answer "is this a controller result or a valve-siting result?" |
| **OPTION 2** — Net3 only | All of the above, plus no generalisation evidence at all, plus no route to answering the transferability gap Javed et al. (2025) name. Scored 22/35. | Simplest schedule | Everything OPTION 1 loses, and external validity as well |
| **OPTION 3** — modified Jowitt & Xu primary + Net3 secondary | Requires inventing a pump, a pump curve, an EPS duration and demand patterns on a network with **no official `.inp`**. §4 verdict: after a Level-2 modification it is **no longer the Jowitt & Xu benchmark** and would have to be renamed. Scored 16/35 — last. J&X ranked last or second-last in **all five** sensitivity scenarios. | Direct numerical comparability with Negm 2024; a clean novelty story on an under-used network | Reproducibility; benchmark identity; the ability to answer "why should anyone trust a network you built yourself?" |

`INFERENCE` — the decisive asymmetry: OPTION 3's *only* real prize is a pump, and
six public benchmarks supply a pump for free. Paying reproducibility and benchmark
identity for something available at zero cost is not a defensible trade. This is
the sense in which §4 concluded that modifying Jowitt & Xu is *permitted but
pointless*.

## What OPTION 4 gains

1. **Placement exogeneity.** The one property no other configuration provides.
2. **Both actuators native.** 2 head-curve pumps + 8 PRVs, so neither half of the
   research question requires a topology edit.
3. **A defensible novelty position.** Claims N6, N7, N8, N10 and N11 (§9) all
   survive the 2024–2026 sweep at HIGH level; none of them depends on the
   algorithm being new.
4. **Compute headroom for statistics.** 192 steps per episode makes ≥5 seeds ×
   3 configurations feasible, which is what N12 (seed variance) requires and what
   Jun et al. (2025) demand of reproducible ML in urban water.
5. **Comparability retained anyway,** via the Net3 secondary arm.
6. **Falsification of prior gap G10 recorded.** The earlier project conclusion
   that "no standard benchmark carries both PRVs and VSPs natively" is **false as
   stated**; the surviving true statement is only that no benchmark ships a pump
   *pre-configured* as variable-speed.

## What OPTION 4 costs

1. **No DRL precedent on BWSN-1.** `FACT` — the search found none. `INFERENCE` —
   this cuts both ways: novelty headroom, but no prior result to sanity-check
   against. The Net3 arm exists precisely to cover this.
2. **A three-network study is more work than a one-network study.** Mitigated by
   making the tertiary arm explicitly droppable.
3. **BWSN-1's native demand patterns are unrealistic** — 4 patterns of 16/16/8/16
   entries at a 0:30 step, i.e. an 8-hour cycle repeated over 96 hours. A diurnal
   + stochastic demand model must be imposed. `INFERENCE` — this is a cost the
   thesis pays on *any* network, so it is not a BWSN-1-specific penalty.
4. **US units.** GPM / psi / ft, H-W head loss. All reported pressures must be
   converted and the conversion stated. Net3 shares this; L-Town does not (CMH/m).
5. **One untested hydraulic risk.** `UNKNOWN` — whether 8 PRVs converge reliably
   in WNTR under PDA with emitters active. This is the gating check of §12.

---

# 12. Implementation Gate

## Gate: **YES — conditional on one pre-flight check.**

The network decision is closed and implementation may begin. One check must pass
before any experiment is *designed around* BWSN-1:

> **Pre-flight check P1.** Load `BWSN_Network_1.inp` in WNTR, switch the demand
> model to PDA, attach emitters at a representative node set, and run the full
> 96-hour extended-period simulation. Confirm: no solver failures, all 8 PRVs
> reach a defined status, and tank levels stay inside their bounds under the two
> tank-level pump rules. `UNKNOWN` — outcome untested. If P1 fails and cannot be
> resolved by standard means, switch the primary network to **D-Town** (§11
> fallback) and leave every other field below unchanged.

`INFERENCE` — P1 is a hydraulic feasibility test, not an experiment. It produces no
result that enters the thesis and costs one simulation run.

Two documentation corrections are also due before the thesis text is written, both
independent of P1:

- `FACT` — the proposal cites Hu's pump-and-valve MARL paper as *JWRPM* 148(8).
  The actual venue is ***Water Supply* 23(7):2833, doi 10.2166/ws.2023.163**. Fix
  the citation.
- `FACT` — Negm's Table 5-4 was reconstructed here from a column-garbled
  `pdftotext` extraction. Re-read that page in the PDF before quoting any number
  from it.

## Locked configuration

The block below is a **specification**, not code. Every field is either a decision
with its justification, or explicitly marked `TO TUNE` / `UNKNOWN`.

```text
NETWORK
  primary        BWSN_Network_1.inp  (BWSN 2008, "Battle of the Water Sensor
                 Networks", Ostfeld et al.)  — 126 junctions, 1 reservoir,
                 2 tanks, 168 pipes, 2 pumps (HEAD CURVE-0 / CURVE-2),
                 8 PRV, 4 RULES on tank levels, Duration 96:00 @ 0:30,
                 GPM / psi / ft, Hazen-Williams.  Counts verified from the .inp.
  secondary      Net3.inp (EPANET distribution) — comparability with
                 Hu, Gao & Zhong (2023) ONLY. 92 junctions, 117 pipes,
                 2 pumps, 0 valves; 4 PRVs inserted at Hu's locations.
  tertiary       Jowitt & Xu (1990), unmodified, reconstructed from the paper
                 (JWRPM 116(4):455-472).  OPTIONAL. Comparability with
                 Negm (2024) ONLY. No official .inp exists — record this.
  generalisation L-TOWN.inp (Zenodo 4017659) if and only if compute permits.
                 782 junctions, 905 pipes, 1 pump, 3 PRV, CMH/m.
  fallback       d-town.inp, if pre-flight check P1 fails.
  EXCLUDED       Kentucky KY1-KY17 / KYV series — Duration 0, [CURVES] empty,
                 pumps declared by POWER; affinity-law speed control impossible
                 without inventing pump curves.
  UNITS NOTE     BWSN-1 and Net3 are US units; L-Town is metric. All reported
                 pressures converted to metres of head; conversion stated in
                 the thesis.

LEAKAGE MODEL
  mechanism      EPANET [EMITTERS] / WNTR leak nodes.  Orifice form
                 q = C * p^alpha.
  exponent       alpha = 0.5 for discrete orifice leaks (theoretical orifice
                 exponent).  Background-leakage runs additionally reported at
                 alpha = 1.0 as a sensitivity, since field-reported exponents
                 for background leakage exceed 0.5.  Both values stated, neither
                 presented as the single truth.
  coefficients   C values NOT yet set.  TO TUNE: calibrate so that baseline
                 uncontrolled leakage is a stated fraction of total system
                 input, that fraction fixed in advance and reported.
  justification  FACT: [EMITTERS] is empty in all 13 candidate .inp files
                 parsed. Leakage must be added on every network, so this is a
                 common modelling cost, not a network-specific concession.
  DO NOT         change C or alpha between the RL agent and the baselines.
```
```text
DEMAND MODEL
  base           node base demands as distributed in the .inp — never edited.
  pattern        REPLACE BWSN-1's native patterns.  FACT: BWSN-1 ships 4
                 patterns of 16/16/8/16 entries at a 0:30 pattern step, i.e. an
                 8-hour cycle repeated over 96 h — not diurnal.  Imposed model:
                 24-hour diurnal multiplier profile + multiplicative stochastic
                 noise per node per step.
  stochasticity  noise distribution and magnitude TO TUNE.  Requirement: the
                 training distribution must be documented as a distribution, so
                 that "out of distribution" has a defined meaning for the test
                 protocol below.
  weekday/weekend  adopted only on L-Town, where BattLeDIM defines it.  Not
                 invented for BWSN-1.
  justification  Any credible uncertainty study needs its own demand model on
                 any of these networks. Documented as a modification.

PDA/DDA
  training       PDA (EPANET 2.2 DEMAND MODEL PDA / WNTR pressure-driven).
  reason         Under active pressure reduction and leakage, DDA delivers full
                 demand at physically impossible pressures and overstates
                 achievable savings.
  PDA parameters minimum and required pressure TO SET explicitly and reported.
                 For L-Town, BattLeDIM states the service target verbatim:
                 "a pressure head of at least 20m to all of its consumers" —
                 use 20 m there.  For BWSN-1 (psi units) the equivalent service
                 threshold must be set and justified separately; UNKNOWN
                 whether BWSN documentation states one.
  extra result   Run the FINAL trained policy under DDA as well, and report the
                 difference. This is claim N9 and it is a result, not a setting.

PRV PLACEMENT               (design D3 — dual placement, from section 7)
  headline arm   BWSN-1's native 8 PRVs, exactly as distributed. Locations fixed
                 by the BWSN organisers in 2008 for a contamination-sensor
                 objective, therefore exogenous to this thesis's reward.
                 Native settings: 70, 80, 55, 29.762, 45, 37, 40, 16.45 psi.
                 FACT: [CONTROLS] closes VALVE-180 at time 0, so 7 of 8 are
                 active at t=0. Preserve this unless deliberately changed.
  sensitivity    GA-selected SUBSET of those same 8 valves (k of 8, k stated).
                 Purpose: quantify how much benefit comes from placement vs
                 control (claim N11). The GA never invents new locations.
  comparability  Net3 with 4 PRVs at Hu, Gao & Zhong's (2023) locations.
  insertion      where a valve must be added, use the paired-node pattern BWSN-1
                 itself uses (valve link between two artificial nodes, one
                 incident pipe per side) so hydraulics are unchanged apart from
                 the valve.
  DO NOT         re-run placement optimisation against the thesis reward on the
                 primary network. That is the co-optimisation bias documented in
                 section 7 and it invalidates the headline claim.
```
```text
PUMP MODEL
  base           BWSN-1's 2 existing pumps, PUMP-170 (CURVE-0) and PUMP-172
                 (CURVE-2).  CURVE-1 is present but unused in the .inp.
  change         relative speed becomes a controlled variable. This is a native
                 EPANET pump property, NOT a topology edit — the head curves
                 required for affinity-law scaling already exist.
  speed bounds   TO SET, and must be stated. Requirement: bounds must keep the
                 operating point on the supplied curve's valid range; do not
                 allow speeds that extrapolate the curve into nonsense.
  native rules   FACT: 4 [RULES] tie the pumps to tank levels — PUMP-170 on
                 TANK-131 (open <= 15.4, closed >= 18.4), PUMP-172 on TANK-130
                 (open <= 12.1, closed >= 16.0).  DECISION: keep these rules as
                 the on/off envelope for the PRV-only baseline, and disable them
                 only in the arms where the agent controls the pump. State which
                 arms have them active — this is a comparability trap if left
                 implicit.
  energy         [ENERGY] Global Efficiency 75 %, Global Price 0 in the .inp.
                 A price must be set to report energy cost; the value chosen is
                 an assumption and must be reported, not buried.

STATE
  observation    tank levels (2 on BWSN-1); pressures at a defined sensor subset;
                 total inflow; current PRV settings; current pump speed(s);
                 time-of-day encoding.
  sensor subset  MUST be a realistic subset, NOT all 126 junctions.  Selection
                 rule TO DECIDE and to be stated.  Precedent for a principled
                 subset: BattLeDIM placed 33 sensors "using a methodology which
                 maximizes the collective sensitivity of the sensors to any
                 possible leak".  UNKNOWN whether BWSN-1 documentation defines a
                 sensor set; if not, the rule used here is an author decision and
                 must be declared.
  normalisation  fixed per-variable scaling, computed ONCE from the baseline
                 configuration and frozen across all arms, seeds and test sets.
  DO NOT         include the true leak flow, the true leak location, or any
                 quantity a real SCADA system could not measure. That is data
                 leakage and it is the first thing an examiner will look for.

ACTION
  space          continuous Box.
  components     8 PRV pressure setpoints + N pump relative speeds.
  bounds         PRV setpoints bounded per valve within a stated range tied to
                 that valve's own hydraulic context; pump speed bounded as
                 above.  Negm's precedent for reference: "0 to 70 for valves and
                 unbounded speeds for the pumps" — the unbounded pump speed is
                 NOT adopted here; unbounded speed invites physically invalid
                 operating points.
  rate limits    a per-step change limit on setpoints, to prevent policies that
                 are unimplementable on real actuators. Value TO SET.
  arms           PRV-only  |  VSP-only  |  joint PRV+VSP.  This triple IS the
                 ablation of claim N6 and is not optional.
```
```text
REWARD
  terms          (1) leakage volume  (2) pressure-service violation
                 (3) pump energy  (4) actuator-movement penalty.
  form           weighted sum for TRAINING only.
  weights        TO TUNE.  Negm's precedent, verbatim: "a ratio of 3:1 favouring
                 the leakage objective produces the best trade-off".  This thesis
                 does NOT inherit that ratio, because section 9 / Q14 argues the
                 3:1 setting is what produced his 264-304 violations against a
                 classical optimiser's 46-78.
  weight study   report results across a SET of weightings, not one. The output
                 is a trade-off surface (claim N10).
  EVALUATION     never by scalarised reward.  Violations are reported as a
                 separate, non-negotiable axis, and methods are compared at
                 MATCHED violation budgets.
  reward hacking explicit check: inspect whether the policy achieves leakage
                 reduction by starving nodes (PDA delivery shortfall) rather than
                 by managing pressure. Report delivered-vs-required demand.

UNCERTAINTY                 (two axes, deliberately separated — claims N7, N8)
  axis 1         DEMAND. Stochastic multipliers during training; test includes an
                 out-of-distribution regime (magnitude/shape outside the training
                 distribution).  Contrast with Hu, Gao & Zhong (2023), FACT,
                 verbatim: they tested "five random test cases from the same
                 distribution of the training".
  axis 2         MODEL PARAMETERS. Pipe roughness and diameter perturbation.
                 Precedent for the magnitude, BattLeDIM verbatim: "the EPANET
                 model parameters may be different from the actual network
                 parameters (e.g., diameters, roughness coefficients), and it is
                 assumed than in general this difference is no greater than 10%
                 of the nominal values".  Adopt 10 % as the declared bound and
                 cite that source.
  reporting      the two axes are reported SEPARATELY and then jointly. Merging
                 them destroys the contribution.

PPO
  library        Stable-Baselines3 PPO (single agent).  Version to be pinned in
                 the thesis; UNKNOWN until the environment is built.
  hyperparams    START from the library defaults and tune from there. The default
                 set (learning rate 3e-4, n_steps 2048, batch 64, 10 epochs,
                 gamma 0.99, GAE lambda 0.95, clip 0.2, vf coef 0.5, max grad
                 norm 0.5) is recorded here as a STARTING POINT, to be verified
                 against the installed version rather than quoted from memory.
                 Every value actually used must be logged per run.
  episode        one 96-hour EPS = 192 control steps on BWSN-1 (0:30 hydraulic
                 step).  Control interval may be coarser than the hydraulic
                 step; if so, state the ratio.
  budget         total timesteps TO SET.  Constraint: the budget must be
                 identical across all arms and all networks being compared.
  MADDPG arm     optional: single-agent PPO vs multi-agent baseline (claim N13).
                 Drop before dropping the ablation or the OOD test.
```
```text
BASELINES                   (all on the identical environment, leak model,
                             demand realisations and PDA settings)
  B0  no control            native PRV settings + native pump rules. The floor.
  B1  fixed optimised       one static PRV setting vector + one pump schedule,
                            optimised offline on the MEAN demand profile.
  B2  classical online      a metaheuristic re-optimising per timestep with full
                            knowledge of the current state.  Precedent set:
                            Negm uses Nelder-Mead, PSO and DE; Hu uses GA, PSO
                            and DE.  Choose at least two, and say which.
  B3  rule-based            a time-of-day PRV modulation rule of the kind
                            utilities actually deploy.
  UPPER BOUND               optional oracle: the same optimiser as B2 given
                            PERFECT foresight of future demand. Bounds how much
                            of the gap is attributable to uncertainty itself.
  fairness rule             baselines get the same actuators, the same bounds and
                            the same rate limits as the agent. A baseline denied
                            an actuator the agent has is not a baseline.
  compute note              report the wall-clock cost of B2 per decision. Online
                            metaheuristics are frequently infeasible in real time;
                            that is a legitimate advantage of a trained policy and
                            it should be measured, not asserted.

TEST PROTOCOL
  separation     demand realisations used for training are never reused for
                 testing. Fixed, saved test sets.
  T1 in-dist.    held-out realisations from the training distribution.
  T2 OOD demand  realisations outside the training distribution (claim N7).
  T3 param.      roughness/diameter perturbed to the declared 10 % bound
                 (claim N8), with demand held in-distribution so the axes stay
                 separable.
  T4 joint       T2 and T3 together. The hardest case; report it even if it fails.
  T5 PDA vs DDA  the final policy re-evaluated under DDA (claim N9).
  T6 transfer    optional: BWSN-1-trained policy applied zero-shot to Net3 and
                 L-Town (claim N16). Only claim transferability if T6 is run.
  metrics        leakage volume; number and magnitude of service violations;
                 delivered/required demand ratio; pump energy; actuator movement;
                 constraint-matched comparison against every baseline.
  reporting      mean AND spread across seeds for every number. No single-run
                 results in the thesis.

SEEDS
  training       >= 5 independent seeds per arm per network. Non-negotiable —
                 FACT: neither Hu, Gao & Zhong (2023) nor Negm (2024) reports
                 seed variance, and Jun, Yoo & Jung (2025, JWRPM,
                 doi 10.1061/JWRMD5.WRENG-6868, "Toward Transparent and
                 Reproducible Machine Learning-Based Research in Urban Water
                 Networks") argues directly for this reporting standard.
  evaluation     test-set generation seeded separately from training and fixed
                 once, so every arm and every baseline sees identical scenarios.
  logging        every seed, every config, every library version recorded per
                 run. Results reported as distributions, never as best-of-n.
```

---

## Closing statement

`FACT` — the four numbered claims that opened this review are answered as follows.
Net3 is **not** the best network for this thesis: its `[VALVES]` section is empty,
and Hu, Gao & Zhong (2023) already occupy the exact configuration Net3 would force.
Negm's Jowitt & Xu network **can** be reused, but only unmodified and only as a
replication arm; adding a pump to it produces a network that is no longer the
Jowitt & Xu benchmark and should be renamed if it is used at all. **BWSN-1** is the
network a researcher starting from zero today would choose, for one reason that no
alternative supplies: its valve locations were fixed by a third party for an
objective unrelated to leakage, while its pumps already run on head curves.

`INFERENCE` — the thesis's defensible contribution is not the algorithm. It is the
evaluation: an out-of-distribution and model-uncertainty test protocol, an ablation
that isolates what the variable-speed pump actually contributes, a trade-off
surface in place of a scalarised cost, and a quantification of how much of the
benefit reported in this literature comes from the controller rather than from
having optimised the valve locations first. Those four claims survived the
2024–2026 adversarial sweep. The algorithm claims did not, and must not be made.

**Prior conclusion overturned by this review:** gap G10, recorded earlier as "no
standard benchmark carries both PRVs and VSPs natively", is **false as stated**.
BWSN-1, C-Town, D-Town, L-Town, Richmond and CY-DBP all ship pumps *and* PRVs. The
only surviving true statement is that no public benchmark ships a pump
*pre-configured* as variable-speed — which is a parameterisation gap, not a
topology gap, and it was the source of the incorrect inference that PRVs must be
inserted by hand on every network.















