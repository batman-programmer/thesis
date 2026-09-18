# Phase 4 — Network Selection Evidence Log

Date: 2026-09-01. Status: evidence collection (no decision locked).
Rule: **FACT** = directly observable in a model file / paper / official database.
**INFERENCE** = derived by me from facts.

---

## A. Primary evidence source for the benchmark landscape

**FACT.** `WaterFutures/WaterBenchmarkHub` (GitHub, `main` branch) is a curated
benchmark registry maintained by the WaterFutures consortium (KIOS CoE Cyprus,
TU Delft, Technion, Bielefeld). It contains 95 benchmark description files,
of which ~70 are individual WDN descriptions (`docs/_benchmarks/network-*.md`),
each with element counts and a literature reference.
Python package: `water-benchmark-hub` (PyPI). `.inp` files are distributed via
`https://filedn.com/lumBFq2P9S74PNoLPWtzxG4/EPyT-Flow/Networks/<file>.inp`
with GitHub backup mirrors (`KIOS-Research/EPANET-Benchmarks`,
`OpenWaterAnalytics/EPyT/epyt/networks/asce-tf-wdst`).

**FACT.** I downloaded and parsed the actual `.inp` files for the candidates
below. Counts marked "(.inp)" are my own direct section counts from the model
file, not quoted from a paper.

**FACT — discrepancy to record.** WaterBenchmarkHub's prose counts do not always
match the distributed `.inp`:
- Net3: WBH says "91 junctions, 121 pipes"; the `.inp` has 92 junctions, 117 pipes.
- BWSN-1: WBH says "154 pipes"; the `.inp` has 168 pipes.
- L-Town: WBH says "923 pipes"; the Zenodo `L-TOWN.inp` has 905 pipes
  (905 also matches the official BattLeDIM slide deck).
**INFERENCE.** Prose counts in secondary sources must not be cited as exact.
The `.inp` is the only citable authority for element counts. Any number quoted
in the thesis must be regenerated from the model file actually used.

---

## B. Verified `.inp` profiles (direct section counts)

| Network | Junc | Res | Tanks | Pipes | Pumps | Valves | Valve types | Pump spec | Duration | Hyd. step | Emitters |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Net3** | 92 | 2 | 3 | 117 | 2 | **0** | — | HEAD curve | 24:00 | 1:00 | 0 |
| **BWSN-1** | 126 | 1 | 2 | 168 | 2 | **8** | **8 PRV** | HEAD curve | 96:00 | 0:30 | 0 |
| **L-Town** | 782 | 2 | 1 | 905 | 1 | **3** | **3 PRV** | HEAD curve | 168:00 | 0:05 | 0 |
| **C-Town** | 388 | 1 | 7 | 429 | 11 | 4 | 3 PRV + 1 FCV | HEAD curve | 168:00 | 0:15 | 0 |
| **D-Town** | 399 | 1 | 7 | 443 | 11 | 5 | 4 PRV + 1 TCV | HEAD curve | 168:00 | 0:15 | 0 |
| **Richmond** | 865 | 1 | 6 | 949 | 7 | 1 | 1 PRV | HEAD curve | 24:00 | 1:00 | 0 |
| **Anytown** | 19 | 3 | 0 | 40 | 1 | 0 | — | HEAD curve | 24:00 | 3:00 | 0 |
| **KY6** | 543 | 2 | 3 | 644 | 2 | 1 | 1 PRV | **POWER** | **0** | 1:00 | 0 |
| **KY9** | 1242 | 4 | 15 | 1270 | 17 | 56 | 56 PRV | **POWER** | **0** | 1:00 | 0 |
| **KY10** | 920 | 2 | 13 | 1043 | 13 | 5 | 5 PRV | **POWER** | **0** | 1:00 | 0 |
| **KY11** | 802 | 1 | 28 | 846 | 21 | 15 | 15 PRV | **POWER** | **0** | 1:00 | 0 |
| **KY13** | 778 | 2 | 5 | 940 | 4 | 0 | — | **POWER** | **0** | 1:00 | 0 |
| **KY15** | 659 | 2 | 8 | 662 | 13 | 28 | 25 PRV + 3 PSV | **POWER** | **0** | 0:01 | 0 |

### Decision-relevant facts extracted from these files

**FACT — zero networks ship with emitters.** `[EMITTERS]` is empty in every
candidate. Leakage must be added by the researcher in *all* cases (emitter
coefficients, or WNTR's leak model). Adding a leakage model is therefore **not**
a discriminator between candidate networks.

**FACT — zero networks ship a variable-speed pump.** Every pump row in every
candidate uses either `HEAD <curve>` or `POWER <value>`; no `SPEED` value and no
speed pattern appears in any `[PUMPS]` section. VSP capability must be added in
*all* cases. It is added by setting the pump's relative-speed property, which is
a native EPANET/WNTR pump attribute — not a topology edit.
**INFERENCE.** "Add a VSP" is a *parameterisation* change on any network that
already has a pump on a head curve. It is a *topology* change only on a network
with no pump at all. This distinction is the crux of the Jowitt & Xu question.

**FACT — Kentucky networks are single-period models.** ky6/9/10/11/13/15 all have
`Duration 0` (steady-state snapshot), `[CURVES]` empty (no pump curves at all),
pumps declared by `POWER`, and only 8–10 total demand-pattern rows.
**INFERENCE.** The KY series cannot support pump-speed control as distributed:
affinity-law speed scaling requires a pump head curve, which these files do not
contain. Using KY would require inventing pump curves, an EPS duration, and
diurnal demand patterns — strictly more fabrication than Net3 or BWSN-1 needs.
This disqualifies the whole KY series for a VSP thesis despite their large native
PRV counts.

**FACT — BWSN-1 control logic.** 4 `[RULES]`: `PUMP-170` switches on tank
`TANK-131` level (open ≤15.4, closed ≥18.4); `PUMP-172` switches on `TANK-130`
level (open ≤12.1, closed ≥16.0). One `[CONTROLS]` line closes `VALVE-180` at
time 0, so 7 of the 8 PRVs are active at start. Pump curves: `CURVE-0`
(PUMP-170), `CURVE-2` (PUMP-172), `CURVE-1` present but unused. `[ENERGY]`
Global Efficiency 75 %, Global Price 0. Units GPM (US), H-W head loss, so PRV
settings (70, 80, 55, 29.762, 45, 37, 40, 16.45) are in psi and elevations in ft.
Demand patterns: 4 patterns, 16 / 16 / 8 / 16 entries at a 0:30 pattern step,
i.e. an 8-hour cycle repeated over the 96 h horizon.
**INFERENCE.** BWSN-1's native demand patterns are unrealistically short-cycle.
Any credible study on it must impose its own diurnal + stochastic demand model.
That is however what this thesis intends to do on *any* network, so it is a
common cost, not a BWSN-1-specific penalty.

**FACT — Net3 control logic.** `[CONTROLS]`: `Link 10 OPEN AT TIME 1`,
`Link 10 CLOSED AT TIME 15` (Lake source pump runs part-day); `Link 335 OPEN IF
Node 1 BELOW 17.1`, `Link 335 CLOSED IF Node 1 ABOVE 19.1`; bypass pipe `330`
opens/closes inversely to pump 335. Pump `10` is listed `Closed` in `[STATUS]`.
Reservoirs: River (head 220), Lake (head 167). `[OPTIONS] Quality Trace Lake`.
**INFERENCE.** Net3's pumps are genuinely coupled to tank dynamics, which is the
property that makes tank-state observation meaningful in an RL formulation.

**FACT — L-Town native pressure management.** From the official BattLeDIM
Problem Description and Rules v1.3.1 (Vrachimis, Eliades, Taormina, Kapelan,
Ostfeld, Liu, Kyriakou, Pavlou, Qiu, Polycarpou), verbatim:
"A Pressure Reduction Valve (PRV) is installed in the lower part of the town
("Area B"), to help reducing background leakages. PRVs are also installed
downstream of the two main reservoirs, to help regulating the pressure. A pump
and a water tank have been installed in the higher part of the town ("Area C")
… The pump has been programmed so that the tank should be refilling during the
night and emptying to "Area C" during the day."
Service target, verbatim: "the water utility aims at providing water with a
pressure head of at least 20m to all of its consumers."
Sensors, verbatim: "one (1) tank water level sensor, three (3) flow sensors, and
33 pressure sensors … transmitting their measurements every 5 minutes";
"82 Automated Metered Readings (AMRs) … installed in "Area C"".
Pressure sensors "were placed using a methodology which maximizes the collective
sensitivity of the sensors to any possible leak."
Model uncertainty, verbatim: "the EPANET model parameters may be different from
the actual network parameters (e.g., diameters, roughness coefficients), and it
is assumed than in general this difference is no greater than 10% of the nominal
values"; "the utility was not able to confirm the status of all the valves".
Demand structure: 3 consumer types (residential/commercial/industrial), distinct
weekday vs weekend patterns, and stated Northern-hemisphere seasonality
(July/August high, December/January low).
Lineage, verbatim: LeakDB "based on benchmark networks and created using the
WNTR tool, using **pressure-driven demands** and realistic leakage modelling".
Public files: `L-TOWN.inp` and `L-TOWN_Real.inp` on Zenodo record 4017659;
`.inp` confirmed downloaded (412 KB, 905 pipes, 3 PRV, 1 pump).
Benchmark paper DOI: 10.1061/(ASCE)WR.1943-5452.0001601 (ASCE JWRPM).
PRV settings in the `.inp`: PRV-1 = 40, PRV-2 = 50, PRV-3 = 35 (CMH units → m).

**INFERENCE — this contradicts a prior-phase conclusion.** An earlier phase
recorded gap G10 as "closed negatively: no standard benchmark carries both PRVs
and VSPs natively". That is **false as stated**. Two public benchmarks carry
pumps *and* PRVs natively — BWSN-1 (2 pumps + 8 PRVs) and L-Town (1 pump +
3 PRVs) — plus C-Town, D-Town, Richmond, and the KY series. What is true is the
weaker statement: *no* benchmark ships a pump already configured as
variable-speed. The original claim conflated "PRV present" with "VSP present"
and led to the wrong conclusion that PRV addition is unavoidable everywhere.
On BWSN-1 and L-Town, **PRV addition is not required at all.**

---

## C. Networks with no pump (structurally excluded from a PRV+VSP thesis)

**FACT** (WaterBenchmarkHub prose counts, `.inp` not individually re-verified):
Hanoi 32 junc / 34 pipes / 1 reservoir, 0 pumps. Modena 268 / 317 / 4 reservoirs,
0 pumps. Balerma 447 / 454 / 4 reservoirs, 0 pumps. Fossolo 36 / 58 / 1 reservoir,
0 pumps. BAK 36 / 58 / 1 reservoir, 0 pumps. Jilin 27 / 34, 0 pumps.
Zhi-Jiang 113 / 164, 0 pumps. Marchi-Rural 379 / 476 / 2 reservoirs, 0 pumps.
KL 935 / 1274 / 1 reservoir, 0 pumps. EXN (EXNET) 1893 nodes / 3029 pipes /
2 reservoirs / 2 valves, 0 pumps. Pescara 89 / 99 / 3 reservoirs, 0 pumps.
CA1 111 / 126 / 1 tank, 0 pumps. PA1 337 / 399 / 2 tanks, 0 pumps.
Net2 35 / 40 / 1 tank, 0 pumps. Nineteen-Pipe, Fourteen-Pipe, TLN, TRN, NYC-Tunnel,
Modified-Nineteen-Pipe: all 0 pumps. KYV24 202 / 249 / 43 valves / 2 tanks, 0 pumps.
**INFERENCE.** All of the above are unusable as the primary network for a thesis
whose central claim is coordinated PRV + variable-speed-pump control. They remain
usable only as gravity-fed PRV-only secondary cases.

## D. Other pump-bearing networks recorded (prose counts, lower evidence grade)

**FACT** (WaterBenchmarkHub prose): Net1 9/12/1 res/1 tank/1 pump.
Net6 3322 junc / 3828 pipes / 60 pumps / 2 valves / 33 tanks / 1 reservoir.
Micropolis 1574 / 1823 / 2 res / 1 tank / 8 pumps / 0 valves.
E-Town 2859 / 3198 / 6 res / 4 tanks / 7 pumps / 15 valves.
BWSN-2 12523 / 14314 / 2 res / 2 tanks / 4 pumps / 5 valves.
WCR (Wolf-Cordera Ranch) 1786 nodes / 1984 pipes / 6 pumps / 4 res / 4 valves.
DMA 11063 / 13930 / 17 tanks / 3 pumps / 5 res.
NJ1 14991 / 16090 / 8 tanks / 12 pumps.
CY-DBP 284 junc / 357 pipes / 2 pumps / 4 valves / 2 res / 1 tank.
GOY 23 / 30 / 1 tank / 1 pump / 1 res.
PA2 262 / 290 / 1 pump / 1 res.
KY1 854/984/2 tanks/1 pump; KY2 809/1124/1 pump; KY3 270/366/5 pumps;
KY4 962/1156/2 pumps; KY5 402/496/9 pumps; KY7 479/603/1 pump;
KY8 1317/1614/4 pumps; KY12 2273/2426/22 valves/15 pumps; KY14 366/548/6 pumps;
KY16 777/907/7 pumps; KY17 6242/6567/5 pumps.
KYV8/18/21/22/23: 2439–2786 junctions with 96–488 valves (isolation-valve variants).
network-01-uk-style 136 nodes / 153 pipes / 1 valve / 1 res / 1 pump / 1 tank
(`.inp` public at `epanet-js/epanet-js/public/example-models/01-uk-style.inp`).
network-02-us-style 128 / 166 / 1 valve / 2 res / 1 tank, 0 pumps.

**INFERENCE.** CY-DBP (284 junc, 2 pumps, 4 valves, 1 tank) is the only
additional candidate in the size band that could compete with BWSN-1; its valve
types are not yet verified from the `.inp` and it is a chlorination/DBP
benchmark, so its RL and pressure-control precedent is likely nil.

---

## E. Verification gaps — status after the 2026-09-01/02 evidence sweep

All six are now closed. Full reasoning lives in `phase4_decision_report.md`.

- **G-A — CLOSED.** `FACT` Jowitt, Paul W. & Xu, Chengchao (1990), "Optimal Valve
  Control in Water-Distribution Networks", *JWRPM* 116(4):455–472,
  DOI `10.1061/(ASCE)0733-9496(1990)116:4(455)`, 251 citations (OpenAlex).
  `FACT` **No public `.inp` exists that I could find.** `grep -ril "jowitt"` over
  all 95 WaterBenchmarkHub benchmark files → **0 matches**. `INFERENCE` "unmodified
  Jowitt & Xu" can only mean *reconstructed from the 1990 paper*, which is weaker
  reproducibility than a distributed model file.
  `FACT` still active in 2026: Ferrarese, Fathi & Malavasi, *Water Resources
  Management* 40(9), DOI `10.1007/s11269-026-04785-y` — lab-scale E-NET replica,
  flow scale factor 4.33, GA-optimised PRV **locations and settings**,
  pressure-dependent leakage, RMSE 0.38 m. `INFERENCE` GA-placed PRVs with
  pressure-dependent leakage on J&X is occupied ground as of 2026.
- **G-B — CLOSED.** BWSN-1's 8 PRVs each sit on a dedicated valve link between a
  paired artificial node couple (`JUNCTION-111/112`, `113/114`, `115/116`,
  `117/118`, `119/120`, `121/122`, `123/124`, `125/126`), one incident pipe per
  side (e.g. `LINK-25 JUNCTION-15→111`, `VALVE-173 111→112`,
  `LINK-26 112→JUNCTION-14`). `LINK-0` (7,401 ft, 20.45 in) joins `JUNCTION-118`
  (downstream of `VALVE-176`) to `JUNCTION-126` (downstream of `VALVE-180`, closed
  at t=0). Settings 16.45–80 psi on 6–10 in valves. `INFERENCE` genuine
  parallel-feed / zone-boundary topology, not decorative in-series valves.
- **G-C — CLOSED NEGATIVELY.** No DRL precedent found on BWSN-1 or L-Town for
  pressure control. OpenAlex `("C-Town" OR "D-Town" OR "L-Town" OR "Anytown" OR
  "BWSN") AND "reinforcement learning"` → 6 results, none of them control studies
  on BWSN-1, C-Town or L-Town; a separate WebSearch on BWSN + RL returned nothing
  relevant. `INFERENCE` novelty headroom, but also no prior result to sanity-check
  against — which is why Net3 is retained as a secondary arm.
- **G-D — CLOSED.** CY-DBP `.inp`: 284 junctions, 2 reservoirs, 1 tank, 362 pipes,
  2 pumps (`HEAD QH_MU_33_3`, `HEAD QH_MU_34_4`), **4 valves = 2 PRV (25, 30) +
  2 FCV (661, 0)**, 42 curves, 7,392 pattern rows, 0 emitters,
  `Duration 167:50 @ 0:05` → 2,014 steps/episode. `INFERENCE` rejected: the 5-min
  step makes episodes ~10× BWSN-1 for no compensating benefit, and it is a
  disinfection-by-product benchmark with no pressure-control lineage.
- **G-E — CLOSED at abstract level.** Cyriac, Unni & Chacko, Sibi (2026), "Deep
  Reinforcement Learning for Pressure Optimization in Water Distribution Networks
  with Multiple Pumping Stations", *JWRPM*, published 2026-05-05,
  DOI `10.1061/JWRMD5.WRENG-7303`, Heriot-Watt University Malaysia, closed access,
  0 citations. Verbatim: "previous work focused on improving pump efficiency and
  have overlooked pressure control using RL with continuous action spaces";
  "a case study on a WDN in **Abu Dhabi**"; "A custom training environment was
  developed using the Gym framework"; agent "dynamically adjust[s] the **pumping
  station pressure setpoints**". `INFERENCE` different actuator (station setpoints,
  not PRV settings or pump speed), private non-reproducible network, no leakage
  objective or PRVs in the abstract; their priority claim is contradicted by Negm
  (2024) and Hu et al. (2023). Full text `UNKNOWN` — paywalled.
- **G-F — CLOSED.** Adversarial 2024–2026 sweep found **no** joint continuous
  PRV + variable-speed-pump DRL control on a public benchmark under demand
  uncertainty. New competitors recorded: **Pei, Hoang, Fu & Butler (2025)**,
  *JWRPM*, DOI `10.1061/JWRMD5.WRENG-6476`, 17 citations, Exeter — PPO pump
  scheduling on **Anytown + D-Town** vs GA / scenario-specific optimisation / MPC /
  robust optimisation, explicitly addressing demand-uncertainty robustness
  (`INFERENCE` this removes "PPO + demand uncertainty vs GA baselines" as a novelty
  claim and is why **D-Town must not be primary** — same institution as Negm);
  **Locatelli et al. (2026)**, *Internet of Things*, DOI
  `10.1016/j.iot.2026.101911` — TwinAI, graph RL + **Dyn-WNTR**, "an extension of
  the widely used WNTR simulator that supports dynamic interaction during runtime"
  (`INFERENCE` removes "first RL environment on WNTR"); **Jeung et al. (2026)**,
  *Water Research X*, DOI `10.1016/j.wroa.2026.100540` — DDQN, discrete, valve and
  hydrant flushing for contamination, low threat; **Nanehkaran et al. (2026)**,
  *Frontiers in Earth Science*, DOI `10.3389/feart.2026.1847899` — classical NSDE +
  Shrimp PRV placement, Khorramshahr network, excess-pressure reduction 8.616 %
  (1 PRV) → 55.262 % (5) → 55.287 % (6) → 55.456 % (7), `INFERENCE` marginal value
  saturates by ~5 valves; **Jun, Yoo & Jung (2025)**, *JWRPM*, DOI
  `10.1061/JWRMD5.WRENG-6868` — reproducibility standards for ML in urban water;
  **Logan, Inturri, Cui, Koeppl & Pelz (2025)**, *JWRPM*, DOI
  `10.1061/JWRMD5.WRENG-7082` — Major-Minor Mean Field Control.
  `FACT` search-power caveat that must travel with any novelty statement: OpenAlex
  `"pressure reducing valve" AND ("reinforcement learning" OR "deep
  reinforcement")` returns **2 results across all years**, yet Hu, Gao & Zhong
  (2023) — the most relevant paper in the field — is **not** among them, because
  its abstract says "valve". `INFERENCE` the count evidences under-indexing of
  abstracts, **not** novelty, and must never be cited as proof of novelty.

## F. Corrections owed to project documents

- `FACT` The proposal cites Hu's pump-and-valve MARL paper as *JWRPM* 148(8). The
  actual venue is ***Water Supply* 23(7):2833, DOI `10.2166/ws.2023.163`.** Fix.
- `FACT` Negm's Table 5-4 as used in earlier phases was reconstructed here from a
  column-garbled `pdftotext -layout` extraction. Re-read the PDF page before
  quoting any number from it.
- `FACT` Negm's thesis is internally inconsistent: §5.2 says "22 nodes, 37 pipes
  and 3 tanks" while Table 5-5 says 25 junctions. Resolved as 22 demand junctions
  + 3 source nodes = 25. Cite carefully.
- `FACT` Prior-phase gap **G10** ("no standard benchmark carries both PRVs and VSPs
  natively") is **false as stated** and is superseded. BWSN-1, C-Town, D-Town,
  L-Town, Richmond and CY-DBP all ship pumps *and* PRVs. Only the weaker statement
  survives: no public benchmark ships a pump *pre-configured* as variable-speed.

