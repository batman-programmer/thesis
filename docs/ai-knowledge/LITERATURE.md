# LITERATURE.md — the project's research corpus and external citations

Two distinct bodies of literature exist in this project and they must not be
conflated:

1. **The local corpus** — `D:\Thesis\papers\`, **42 PDF files**, indexed in §2 by
   exact filename. `DIRECT_OBSERVATION`: the count and the filenames were read
   from the filesystem on 2026-09-07 (`ls -1 papers/ | wc -l` → 42; zero non-PDF
   files; no subdirectories). **The PDFs themselves are NOT in this backup** —
   they are copyrighted third-party material and were left in place.
2. **Externally verified citations** — §3. Every entry there was obtained during
   Phase 4 from Crossref / OpenAlex metadata or from a publisher abstract, and
   each is recorded in `docs/phase4_decision_report.md` or
   `docs/phase4_network_evidence.md` with its DOI.

**Rule that governed writing this file:** *"Never invent a citation."* Where a
bibliographic field was not recorded in the project's own documents, this file
says `NOT RECORDED` rather than filling it in. Several local PDFs are indexed by
filename only, because the filename is all that was ever captured — see §2.4.

---

## 1. How the corpus was used, and its two known defects

`DIRECT_OBSERVATION`. The 42 PDFs were read across Phases 1, 1.5, 1.5-B and 2.
Those phases produced **no report file in `docs/`** — their output survives only
in the session transcripts under `session-backup/`. Consequently this file can
index the corpus and record what Phase 4 quoted from it, but it **cannot**
reconstruct the per-paper reading notes from Phase 1.5. That gap is recorded in
`MISSING_OR_UNRECOVERABLE.md`.

### Defect 1 — the corpus is not a bibliography

`DIRECT_OBSERVATION`. The files are named by title only. Author, year, venue, DOI
and page numbers are **not** encoded in the filenames and were not extracted into
any machine-readable index. `docs/literature.md` — the file `CLAUDE.md` §18
nominates for exactly this purpose — is **0 bytes**.

`INFERENCE`. Before any thesis text cites these papers, each PDF must be opened
and its front matter transcribed. Do not construct a citation from a filename.

### Defect 2 — the OpenAlex sweep is a lower bound on the field, not coverage

`VERIFIED_FACT`, and this is the single most important methodological warning in
this file. From `phase4_network_evidence.md` §E, gap G-F, verbatim:

> search-power caveat that must travel with any novelty statement: OpenAlex
> `"pressure reducing valve" AND ("reinforcement learning" OR "deep
> reinforcement")` returns **2 results across all years**, yet Hu, Gao & Zhong
> (2023) — the most relevant paper in the field — is **not** among them, because
> its abstract says "valve".

`INFERENCE`, recorded verbatim in the same source: *"the count evidences
under-indexing of abstracts, **not** novelty, and must never be cited as proof of
novelty."*

The forward-citation sweep counts, for the record: **Hu 2023 → 15 citing works,
Negm 2023 → 4, Javed 2025 → 17, Pei 2025 → 17, Hajgató 2020 → 89.** The sweep
"surfaced no paper" doing joint continuous PRV + variable-speed-pump DRL control.
Because Hu 2023 is missing from the PRV query's counts, **that null result is
evidence of a gap in the index as much as a gap in the field.**

---

## 2. The local corpus — `D:\Thesis\papers\`

`DIRECT_OBSERVATION`. 42 files, all `.pdf`. Entries 1–36 are English-titled,
37–42 Persian-titled. Filenames are reproduced **exactly**, including the typos
and missing spaces that are present on disk (e.g. entry 12's
`WaterDistribution`), because the filename is the only identifier that can be
used to locate the file again.

### 2.1 English titles (36)

| # | Filename (exact) |
|---|---|
| 1 | `A Survey of Pressure Control Approaches in Water Supply Systems.pdf` |
| 2 | `Control of chaotic systems by Deep Reinforcement Learning.pdf` |
| 3 | `Deep Reinforcement Learning for Real-Time Optimization of Pumps in Water Distribution Systems.pdf` |
| 4 | `Deep reinforcement learning based valve scheduling for pollution isolation in water distribution network..pdf` |
| 5 | `Deep reinforcement learning challenges and opportunities for urban water systems.pdf` |
| 6 | `Improving Water Treatment Using Reinforcement Learning.pdf` |
| 7 | `Improving pressure monitoring and control in order to reduce water loss in water urban public systems.pdf` |
| 8 | `Integrated pressure control strategies for sustainable management of water distribution networks.pdf` |
| 9 | `Integrating the agent-based approach with hydraulic analysis of the water distribution network to a realistic micro-scale simulation of end-users in GAZ City, Iran.pdf` |
| 10 | `Investigation of water losses with real time pressure management as a case study in Sakarya.pdf` |
| 11 | `Leak Management in Water Distribution Networks Through Deep Reinforcement Learning A Review.pdf` |
| 12 | `Leveraging Deep Reinforcement Learning for WaterDistribution Systems with Large Action Spaces and Uncertainties DRL-EPANET for Pressure Control.pdf` |
| 13 | `Model-free pressure control in water distribution networks.pdf` |
| 14 | `Multi-agent reinforcement learning framework for real-time scheduling of pump and valve in water distribution networks.pdf` |
| 15 | `Noniterative Application of EPANET for Pressure Dependent Modelling Of Water Distribution Systems.pdf` |
| 16 | `Optimal Control for Water Distribution Networks with Unknown Dynamics.pdf` |
| 17 | `Optimal Pressure Management in Water Distribution Systems Using an Accurate Pressure Reducing Valve Model Based Complementarity Constraints.pdf` |
| 18 | `Optimal Pressure Regulation in Water Distribution Systems Based on an Extended Model for Pressure Reducing Valves.pdf` |
| 19 | `Optimal pressure management in water networks Increased efficiency and reduced energy costs.pdf` |
| 20 | `Optimal real-time control of a water distribution system undergoing cyber-attacks  a reinforcement learning.pdf` |
| 21 | `Optimization of water distribution of network systems using the Harris Hawks optimization algorithm Case study Homashahr city.pdf` |
| 22 | `Optimizing Smart City Water Distribution Systems Using Deep Reinforcement Learning.pdf` |
| 23 | `Pressure control for minimizing leakage in water distribution systems.pdf` |
| 24 | `Pressure management in water distribution systems in order to reduce energy consumption and background leakage.pdf` |
| 25 | `Pump Scheduling Optimization in Urban Water Supply Stations A Physics-Informed Multiagent Deep Reinforcement Learning Approach.pdf` |
| 26 | `QuantifyingTheGlobalNon-RevenueWaterProblem-Liemberger.pdf` |
| 27 | `Real-Time Scheduling of Pumps in Water Distribution Systems Based on Exploration-Enhanced Deep Reinforcement Learning.pdf` |
| 28 | `Real-time multi-objective optimization of pump scheduling in water distribution networks using neuro-evolution.pdf` |
| 29 | `Reinforcement learning applications in water resource management a systematic literature review.pdf` |
| 30 | `Rethinking Urban Water Network Design A Reinforcement Learning Framework for Long-Term Flexible Planning.pdf` |
| 31 | `Review of leakage detection in water distribution networks.pdf` |
| 32 | `Towards Model-Free Pressure Control in Water Distribution Networks.pdf` |
| 33 | `Water Age Control for Water Distribution Networks via Safe Reinforcement Learning.pdf` |
| 34 | `Water Pressure Optimisation for Leakage Management Using Q Learning.pdf` |
| 35 | `Water distribution networks optimization using GA, SMPSO, and SHGAPSO algorithms based on engineering approach a real case study.pdf` |
| 36 | `Water pressure optimisation for leakage management using deep reinforcement learning.pdf` |

### 2.2 Persian titles (6)

| # | Filename (exact) |
|---|---|
| 37 | `ارائه بسته نظارتی مرتبط با برنامه های کاهش میزان آب به حساب نیامده در شبکه توزیع آب (گزارش مجلس).pdf` |
| 38 | `امکان سنجی و بررسی نقش شیرهای فشار شکن بر کاهش تلفات آب در شبکه توزیع آب.pdf` |
| 39 | `بهینه سازی چندهدفه شیرهای فشارشکن در شبکه توزیع آب شهری با استفاده از الگوریتم NSGAمطالعه موردیپ شبکه توزیع آب شهری نجف آباد.pdf` |
| 40 | `بهینه‌سازی نشت در شبکه توزیع آب شهری با استفاده از مدیریت فشار.pdf` |
| 41 | `مدیریت فشار در شبکه های توزیع آب با استفاده از جانمایی و بهره‌برداری بهینه از تجهیزات کنترلی.pdf` |
| 42 | `مدیریت فشار در شبکه‌های توزیع آب با برنامه زمان‌بندی کنترل شیرآلات جهت کاهش میزان نشت.pdf` |

### 2.3 What the corpus covers, by topic

`INFERENCE` from the titles alone — this is a classification of the filenames,
not of the papers' contents, which were read in Phases 1–2 whose notes are lost.

| Cluster | Entries | Relevance to this thesis |
|---|---|---|
| DRL for pressure/leakage control | 11, 12, 13, 32, 34, 36 | **Core.** Directly the thesis topic |
| DRL for pump scheduling | 3, 25, 27, 28 | Core — the VSP half of the action space |
| DRL for other WDN objectives | 4 (pollution isolation), 20 (cyber-attack), 33 (water age), 30 (network design), 6 (treatment), 22 (smart city) | Adjacent — method transfer, not topic overlap |
| DRL surveys / reviews | 5, 11, 29 | Gap identification |
| Classical / optimisation pressure management | 1, 7, 8, 10, 17, 18, 19, 23, 24 | Baselines and PRV modelling |
| PRV modelling specifically | 17, 18 | **Load-bearing** for the action-mapping layer |
| PDA / hydraulic modelling | 15 | **Load-bearing** for the §17 PDA configuration |
| Metaheuristic optimisation on WDNs | 21, 35 | Baseline candidates |
| Leak detection (not control) | 31 | Peripheral |
| Non-revenue water context | 26 (Liemberger) | Motivation / introduction |
| Agent-based / Iranian case studies | 9, 21, 37–42 | Local context; Persian sources motivate the problem |
| Method-only, non-WDN | 2 (chaotic systems), 16 (unknown dynamics) | Method background |

`OPEN_QUESTION`. Entries 13 and 32 have near-identical titles ("Model-free
pressure control…" and "Towards Model-Free Pressure Control…"), as do 34 and 36
("…Using Q Learning" and "…using deep reinforcement learning"). Whether each pair
is two versions of one work or two distinct works is **not recorded anywhere in
the project**. Resolve by opening the PDFs before citing either.

### 2.4 What is missing from this index, and why

`DIRECT_OBSERVATION`. For 41 of the 42 files, **no author, year, venue, DOI or
page range is recorded anywhere in the project's documents.** The single exception
is entry 26, whose filename carries the author surname `Liemberger` — and even
there the year and venue are not recorded.

`INFERENCE`. The papers Phase 4 cites by DOI in §3 below **overlap** this corpus
but the mapping is not established. For example, entry 14
("Multi-agent reinforcement learning framework for real-time scheduling of pump
and valve in water distribution networks") is almost certainly Hu, Gao & Zhong
(2023) — but this file will not assert that, because the correspondence was never
verified by opening the PDF. Likewise entry 12 is plausibly the DRL-EPANET work
and entry 36 plausibly Negm's. **Verify by opening the file; do not assume.**

---

## 3. Externally verified citations

Every entry below has a DOI recorded in a project document. Confidence is stated
per entry. `NOT RECORDED` marks a field the project never captured.

### 3.1 The two most directly competing works

**Hu, Gao & Zhong (2023).** *Water Supply* **23(7):2833**.
DOI **`10.2166/ws.2023.163`**.
Method: **MADDPG**, multi-agent, joint pump and valve scheduling.
Source of the citation: `phase4_decision_report.md` line 35 and line 393;
`phase4_network_evidence.md` §F.
Why it matters: it is the closest prior work to this thesis's actuator set. Phase
4 recorded that Hu's four valves were **added** to the network — verbatim:
*"Four valves with the greatest impact on leakage were added to the network
through a pre-experiment using a GA"* — which is precisely the placement-bias
problem novelty claim **N11** targets.
How used: rejected novelty claims **N1, N2, N4** and grounds N13 (single-agent
PPO vs multi-agent MADDPG) and N11.
`VERIFIED_FACT` — venue and DOI confirmed from metadata.

> **DEBT — CORRECTION OWED TO THE PROPOSAL.** `VERIFIED_FACT`, from
> `phase4_network_evidence.md` §F: *"The proposal cites Hu's pump-and-valve MARL
> paper as JWRPM 148(8). The actual venue is **Water Supply 23(7):2833, DOI
> 10.2166/ws.2023.163**. Fix."* This correction has **not yet been applied to the
> proposal.** Do not let any thesis text inherit the wrong venue.

Also recorded, same authors, separate work: **Hu et al., "E-PPO", MDPI
*Systems*** — DOI `NOT RECORDED`. Cited in `phase4_decision_report.md` line 393
and in the N2 row. `INFERENCE`: this citation is incomplete and must be resolved
before use.

**Negm (2024).** Doctoral thesis, **University of Exeter**.
Exact title: `NOT RECORDED`. DOI / handle: `NOT RECORDED`.
Method: single-agent **PPO**, continuous Box action space, PRVs only, on the
Jowitt & Xu network.
Quoted verbatim in `phase4_decision_report.md`: *"The only available continuous
space in GYM is the Box space"*; action bounds *"0 to 70 for valves and unbounded
speeds for the pumps"*; on reward weighting *"a ratio of 3:1 favouring the leakage
objective produces the best trade-off"*; §7.3 names pumps as future work —
*"Incorporating other pressure influencing network elements such as pumps …
Adding pumps to the pressure management system will improve the agent performance
hydraulically"*.
Why it matters: this thesis's proposal builds on it. Its §7.3 sentence is what
**authorises novelty claim N6** (the VSP ablation) — Negm proposes it and does not
do it. Its existence **rejects N1**.
Recorded results: *"agents reaching roughly 73 % water saved"* (65.9 % / 73.4 %
figures appear in the §4 comparability discussion).
Also recorded on the same network: Negm's own statements *"Due to the extensive
work on choosing the correct valve location in previous research, we adopt three
valve locations presented in (Araujo et al., 2006)"*, installed *"on pipes P31,
P01, and P25 using invisible nodes Junc 16.5, Junc 13.5, and Junc 1.5 that don't
affect the hydraulic simulation"*, all modelled after *"the standard test network
(Araujo et al., 2006, p. 138,139)"*, and the self-reported bias *"the Jowitt & Xu
valve locations were based on optimised locations"*.

> **DEBT — CITATION NOT SAFE TO USE.** `VERIFIED_FACT`, from
> `phase4_network_evidence.md` §F: *"Negm's Table 5-4 as used in earlier phases
> was reconstructed here from a column-garbled `pdftotext -layout` extraction.
> Re-read the PDF page before quoting any number from it."* **No number from
> Negm's Table 5-4 may be cited until the PDF page has been read directly.** This
> debt is still open.
>
> Second recorded defect: *"Negm's thesis is internally inconsistent: §5.2 says
> '22 nodes, 37 pipes and 3 tanks' while Table 5-5 says 25 junctions. Resolved as
> 22 demand junctions + 3 source nodes = 25. Cite carefully."*

**Negm et al. (2023).** Q-learning. DOI **`10.1109/CAI54212.2023.00120`** (IEEE
CAI). Full title, authors and page range: `NOT RECORDED`. Forward citations: 4
(OpenAlex). Source: `phase4_decision_report.md` line 393.

### 3.2 The classical anchor

**Jowitt, Paul W. & Xu, Chengchao (1990).** "Optimal Valve Control in
Water-Distribution Networks." *Journal of Water Resources Planning and
Management* **116(4):455–472**.
DOI **`10.1061/(ASCE)0733-9496(1990)116:4(455)`**. **251 citations** (OpenAlex).
`VERIFIED_FACT` — confirmed from Crossref/OpenAlex metadata; this closed Phase 4
gap **G-A** on the citation.
`VERIFIED_FACT` — **no public `.inp` exists.** `grep -ril "jowitt"` over all 95
WaterBenchmarkHub benchmark description files returned **0 matches**.
`INFERENCE` recorded verbatim: *"'unmodified Jowitt & Xu' can only mean
reconstructed from the 1990 paper, which is weaker reproducibility than a
distributed model file."*
How used: this is why Jowitt & Xu was **rejected** as the primary network
(scored 16/35, last, and last or second-last in all five sensitivity scenarios) —
see `FAILED_APPROACHES.md` and `DECISIONS.md`.

**Araujo et al. (2006).** Cited only *through* Negm, as the source of the three
PRV locations and of pipe properties, nodal emitter coefficients and demand
patterns at *"p. 138,139"*. Full citation: `NOT RECORDED` — no title, venue, or
DOI was captured. `INFERENCE`: must be resolved independently before citing.

### 3.3 The 2025–2026 competitive frontier

These were found by the Phase 4 adversarial sweep. Each one removed or weakened a
candidate novelty claim, which is why they are load-bearing rather than
background.

| Citation | DOI | What it does | Effect on this thesis |
|---|---|---|---|
| **Pei, Hoang, Fu & Butler (2025)**, *JWRPM*, 17 citations, **Exeter** | `10.1061/JWRMD5.WRENG-6476` | PPO pump scheduling on **Anytown + D-Town**, explicit demand-uncertainty robustness, baselines GA / scenario-specific optimisation / MPC / robust optimisation | **Removes "PPO + demand uncertainty vs GA baselines" as a novelty claim.** Rejected N2. Is the reason **D-Town must not be primary** — same institution as Negm |
| **Locatelli et al. (2026)**, *Internet of Things* | `10.1016/j.iot.2026.101911` | "TwinAI" — graph RL, and **Dyn-WNTR**, verbatim *"an extension of the widely used WNTR simulator that supports dynamic interaction during runtime"* | **Removes "first RL environment on WNTR."** Downgraded N14 to Low–Moderate. `OPEN_QUESTION`: is Dyn-WNTR actually released? Full text not read |
| **Cyriac, Unni & Chacko (2026)**, *JWRPM*, published **2026-05-05**, Heriot-Watt University Malaysia, closed access, 0 citations | `10.1061/JWRMD5.WRENG-7303` | DRL for pressure optimisation with multiple pumping stations. Verbatim from the abstract: *"previous work focused on improving pump efficiency and have overlooked pressure control using RL with continuous action spaces"*; *"a case study on a WDN in **Abu Dhabi**"*; *"A custom training environment was developed using the Gym framework"*; agent *"dynamically adjust[s] the **pumping station pressure setpoints**"* | Grounds **N15** — their priority claim is *contradicted* by Negm (2024) and Hu et al. (2023), and a short sourced correction is legitimate. **Paywalled: abstract only. Do not characterise their method beyond the abstract.** |
| **Jeung et al. (2026)**, *Water Research X* | `10.1016/j.wroa.2026.100540` | Double-DQN, **discrete** actions, valve and hydrant flushing for contamination | Low threat — different objective, discrete action space |
| **Nanehkaran et al. (2026)**, *Frontiers in Earth Science* | `10.3389/feart.2026.1847899` | **Classical** NSDE + Shrimp algorithm, PRV placement, Khorramshahr network. Excess-pressure reduction **8.616 %** (1 PRV) → **55.262 %** (5) → **55.287 %** (6) → **55.456 %** (7) | `INFERENCE` recorded: marginal value **saturates by ~5 valves**. Relevant to the 5-PRV action space |
| **Jun, Yoo & Jung (2025)**, *JWRPM* | `10.1061/JWRMD5.WRENG-6868` | "Toward Transparent and Reproducible Machine Learning–Based Research in Urban Water Networks" | Prescribes exactly the multi-seed statistical reporting of **N12**. Low novelty, high defensibility. Also the external justification for this project's reproducibility discipline |
| **Logan, Inturri, Cui, Koeppl & Pelz (2025)**, *JWRPM* | `10.1061/JWRMD5.WRENG-7082` | Major-Minor Mean Field Control | Recorded as a competitor; not analysed in depth |
| **Ferrarese, Fathi & Malavasi (2026)**, *Water Resources Management* **40(9)** | `10.1007/s11269-026-04785-y` | Lab-scale **E-NET** replica of Jowitt & Xu, flow-scale factor **4.33**, GA optimising both PRV **locations and settings**, pressure-dependent leakage with minimum service pressure, **RMSE 0.38 m** for head loss | `INFERENCE`: *"GA-placed PRVs with pressure-dependent leakage on J&X is occupied ground as of 2026."* Another reason J&X was rejected |
| **Korviakov**, *World Journal of Civil Engineering and Architecture* | `10.31586/wjcea.2026.6596` | Single author, hierarchical RL | Recorded with the caveat **unverifiable venue** — treat with suspicion |
| **Javed et al. (2025)**, *Water* **17(13):1928** | `NOT RECORDED` | Review. Verbatim: *"Most DRL models are network-specific and require retraining"*; lists *"Recurring gaps … limited transferability across network topologies"* | Names the gap **N16** would answer, and the absence of benchmark environments that N14 addresses. 17 forward citations. **DOI not captured — resolve before citing** |
| **Hajgató, Paál & Gyires-Tóth (2020)** | `NOT RECORDED` | DDQN pump scheduling, on Anytown and D-Town. 89 forward citations | Establishes D-Town as the incumbent RL pump-scheduling benchmark. **DOI not captured — resolve before citing** |
| **Xu et al. (2021)**, KA-PPO | `NOT RECORDED` | Reward combining heads + water age + efficiency | Cited in the N4 rejection (multi-objective reward is not novel). **Incomplete citation** |
| **Mosetlhe et al. (2020)** | `NOT RECORDED` | Critical-node-driven PRV placement: 5 PRVs on pipes 1, 9, 10, 17, 21; 7 PRVs at 1, 3, 5, 20, 46, 99, 102 | Used in the PRV-placement-provenance taxonomy. **Incomplete citation** |
| **Liemberger** — `QuantifyingTheGlobalNon-RevenueWaterProblem` | `NOT RECORDED` | Global non-revenue water quantification | Motivation. Present as local PDF entry 26. Year and venue not recorded |

### 3.4 Benchmark and simulator sources

**BWSN benchmark paper (Battle of the Water Sensor Networks).**
DOI **`10.1061/(ASCE)WR.1943-5452.0001601`** (ASCE *JWRPM*).
`INFERENCE` — **caution.** In `phase4_network_evidence.md` this DOI appears in the
**L-Town / BattLeDIM** paragraph, immediately after the L-Town Zenodo files, and
is labelled *"Benchmark paper DOI"* there. In `phase4_decision_report.md` line
949–950, BWSN-1's provenance is given as *"BWSN 2008, 'Battle of the Water Sensor
Networks', Ostfeld et al."* with **no DOI attached**. These may be two different
papers. **Verify which benchmark this DOI belongs to before citing it.** Do not
assume it is BWSN's.

**BattLeDIM Problem Description and Rules v1.3.1.** Authors recorded:
**Vrachimis, Eliades, Taormina, Kapelan, Ostfeld, Liu, Kyriakou, Pavlou, Qiu,
Polycarpou.** Quoted verbatim in `phase4_network_evidence.md` for L-Town's native
pressure management, the *"pressure head of at least 20m"* service target, the
sensor set (1 tank level, 3 flow, 33 pressure at 5-minute intervals, 82 AMRs in
Area C), the ≤10 % model-parameter uncertainty statement, and the LeakDB lineage
*"based on benchmark networks and created using the WNTR tool, using
**pressure-driven demands** and realistic leakage modelling"*.
Files: `L-TOWN.inp`, `L-TOWN_Real.inp`, **Zenodo record 4017659** (412 KB, 905
pipes, 3 PRV, 1 pump; PRV settings 40 / 50 / 35 in CMH→m).
`INFERENCE`: this is the closest external precedent for a 20-unit service-pressure
threshold, which matters because — see below — **BWSN-1 declares no threshold at
all.**

**WNTR 1.5.0** and **EPANET (DLL 20200, i.e. 2.2)**. The simulators this project
runs. `DIRECT_OBSERVATION`: **no citation for either was recorded in any project
document.** `INFERENCE`: WNTR's own paper (Klise et al.) and Rossman's EPANET
manual are the standard citations and **will** be needed for the thesis's methods
chapter, but neither has been captured here and neither should be reconstructed
from memory. Resolve before writing methods.

**EPyT 2.3.5.2** wraps **EPANET 2.3.05** — a *different engine* from the one WNTR
drives. Citation: `NOT RECORDED`. The two engines have **never been
cross-validated in this project**; do not mix results.

---

## 4. Where each novelty claim's evidence lives

The full N1–N16 audit is §9 of `docs/phase4_decision_report.md`. This is the
citation-to-claim map only. Status is quoted from that audit.

| Claim | Status | Decided by which citation |
|---|---|---|
| N1 — first continuous action space for WDN pressure control | **REJECTED** | Negm 2024 (Box space, bounds "0 to 70 for valves") |
| N2 — first EPANET + PPO | **REJECTED** | Hu E-PPO; Pei 2025 `10.1061/JWRMD5.WRENG-6476`; Xu KA-PPO |
| N3 | **REJECTED** | see the audit |
| N4 — first multi-objective reward for pressure/leakage | **REJECTED** | Hu 2023 (energy + leakage + tank); Negm 2024 (3:1); Xu 2021 |
| **N6** — ablation isolating the marginal contribution of VSP operation under coordinated PRV control | **HIGH** | Negm §7.3 names it as future work — *"Negm's own text authorises it"* |
| **N7** | **HIGH** | see the audit |
| **N8** | **HIGH** | see the audit |
| N9 — PDA vs DDA under DRL pressure control | Moderate–High | Negm evaluates three hydraulic states but never contrasts PDA with DDA. **Caveat recorded: must search "pressure-driven demand" + reinforcement learning explicitly before claiming** |
| **N10** — Pareto / constraint-matched evaluation instead of a scalarised cost | **HIGH** | Hu reports aggregate \$/day; Negm reports scalar reward at fixed 3:1 — both scalarise |
| **N11** — quantifying how much of the reported RL benefit comes from optimised valve placement rather than control | **HIGH — "freshest claim in this list"** | Negm observes the mechanism qualitatively; Hu's GA-added valves are the exhibit; nobody quantifies it |
| N12 — multi-seed statistical reporting | Low novelty, high defensibility | Jun, Yoo & Jung 2025 `10.1061/JWRMD5.WRENG-6868` prescribes it; neither Hu nor Negm reports seed variance |
| N13 — single-agent PPO vs multi-agent MADDPG for joint PRV+VSP | Moderate | Hu 2023 (MADDPG) vs Negm 2024 (single-agent, PRV-only) |
| N14 — a reproducible open RL environment on a public benchmark | Low–Moderate | **Weakened** by Locatelli 2026 Dyn-WNTR |
| N15 — correcting the claim that continuous-action RL pressure control is unexplored | Low novelty, real value | Cyriac & Chacko 2026 `10.1061/JWRMD5.WRENG-7303` |
| N16 — transferability across topologies | Moderate | Javed et al. 2025 *Water* 17(13):1928. *"Only worth claiming if the transfer experiment is actually run"* |

`OPEN_QUESTION`, carried in `ROADMAP.md` §6: **are the surviving HIGH claims (N6,
N7, N8, N10, N11) still HIGH after the 2026 literature?** The sweep is a lower
bound (§1, Defect 2), so the honest answer is that they have not been disproved
rather than that they have been confirmed.

---

## 5. Two negative literature results that constrain the project

**`VERIFIED_FACT` — no DRL precedent exists on BWSN-1.** Phase 4 gap **G-C**,
recorded verbatim as *"CLOSED NEGATIVELY"*: OpenAlex
`("C-Town" OR "D-Town" OR "L-Town" OR "Anytown" OR "BWSN") AND "reinforcement
learning"` returned **6 results, none of them control studies on BWSN-1, C-Town or
L-Town**; a separate WebSearch on BWSN + RL *"returned nothing relevant"*.
`INFERENCE` recorded verbatim: *"novelty headroom, but also no prior result to
sanity-check against — which is why Net3 is retained as a secondary arm."*

**`VERIFIED_FACT` — no joint continuous PRV + VSP DRL control on a public
benchmark under demand uncertainty was found.** Phase 4 gap **G-F**. This is the
thesis's central novelty position. It rests on the sweep whose search-power
caveat is §1, Defect 2. State it as *"no such work was found"*, never as *"no such
work exists."*

**`VERIFIED_FACT` — a prior-phase conclusion was overturned by the literature.**
Recorded verbatim: prior gap **G10** — *"no standard benchmark carries both PRVs
and VSPs natively"* — is *"**false as stated**"*. BWSN-1 (2 pumps + 8 PRVs),
L-Town (1 pump + 3 PRVs), C-Town, D-Town, Richmond and CY-DBP all ship pumps *and*
PRVs. Only the weaker statement survives: **no public benchmark ships a pump
pre-configured as variable-speed.** The original claim *"conflated 'PRV present'
with 'VSP present'"*.

---

## 6. Open literature debts

Ranked by what blocks what.

| # | Debt | Blocks | Type |
|---|---|---|---|
| 1 | Correct the proposal's Hu citation from *JWRPM* 148(8) to ***Water Supply* 23(7):2833, doi 10.2166/ws.2023.163** | Any thesis text citing Hu | `VERIFIED_FACT`, fix known, not yet applied |
| 2 | Re-read Negm's **Table 5-4** directly from the PDF | Citing any number from it | `UNRESOLVED` |
| 3 | Resolve DOIs for **Javed et al. 2025**, **Hajgató et al. 2020**, **Xu et al. 2021 (KA-PPO)**, **Mosetlhe et al. 2020**, **Hu et al. E-PPO**, **Araujo et al. 2006**, **Liemberger** | Citing any of them | `UNRESOLVED` |
| 4 | Establish citations for **WNTR** and **EPANET 2.2** | The methods chapter | `UNRESOLVED` — never captured |
| 5 | Determine whether DOI `10.1061/(ASCE)WR.1943-5452.0001601` is BWSN's paper or L-Town/BattLeDIM's | Citing the benchmark | `OPEN_QUESTION` — the two project documents attach it differently |
| 6 | Build the filename → citation mapping for all 42 local PDFs | Any use of the corpus in writing | `UNRESOLVED` |
| 7 | Resolve the two suspected duplicate pairs in the corpus (13/32, 34/36) | Citing either | `OPEN_QUESTION` |
| 8 | Obtain the **BWSN-1 problem statement** | Two open scientific questions: is the baseline service deficit intentional, and **does BWSN-1 declare a service pressure threshold at all** | `OPEN_QUESTION`, recorded UNKNOWN in Phase 5. The 20 psi PDA threshold is **this project's choice, not the benchmark's declaration** |
| 9 | Check whether **Dyn-WNTR** is actually released | The strength of N14 | `OPEN_QUESTION` |
| 10 | Search *"pressure-driven demand"* + reinforcement learning explicitly | Claiming N9 | `PLANNED`, named in the audit itself |
| 11 | Obtain Cyriac & Chacko full text (paywalled) | Characterising their method beyond the abstract | `UNRESOLVED` — and until then, **do not** |

---

## 7. Instruction to the next agent

Three rules, in force:

1. **Never invent a citation.** Where this file says `NOT RECORDED`, the project
   genuinely does not hold that information. Fetch it from Crossref or the PDF;
   do not reconstruct it.
2. **Never cite a local PDF from its filename.** Open the file and read the front
   matter. §2.4 explains why: the filename→citation mapping was never built.
3. **Never cite the OpenAlex null results as proof of novelty.** §1 Defect 2 is
   the reason. The correct phrasing is always *"no such work was found in
   [named search]"*, with the search stated.

The full evidence, with the surrounding argument, is in
`docs/phase4_decision_report.md` §9 (the N1–N16 audit) and
`docs/phase4_network_evidence.md` §E–§F (the six verification gaps and the
corrections owed). This file is an index into those, not a replacement for them.
