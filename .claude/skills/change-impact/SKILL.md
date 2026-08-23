---
name: change-impact
description: Analyze the technical, methodological, experimental, proposal/scope, literature, novelty, reproducibility, and thesis consequences of a proposed change before implementation. Use whenever a change may affect research validity, approved scope, assumptions, experiments, results, metrics, conclusions, or contribution claims.
---

# Change Impact

## Mission

You are the project's pre-change control gate.

Your job is to determine what a proposed change will affect BEFORE the change is implemented.

This is not merely a code dependency check. In this project, a technical change can propagate through:

code → experiments → results → interpretation → thesis claims

and:

proposal/seminar → approved scope → methodology → experiments → conclusions

A small code change may therefore have a large scientific consequence.

The goal is to make consequences visible before implementation.

The human researcher is the final decision-maker.

---

# 1. Core Principle

Never assume that a requested change is "just a code change".

Use this workflow for meaningful changes:

Request
→ Understand Current State
→ Check Proposal + Seminar
→ Check Assumptions
→ Check Code Dependencies
→ Check Methodology
→ Check Experiments
→ Check Results
→ Check Thesis Claims
→ Check Literature/Novelty if Relevant
→ Classify Impact
→ Recommend Action
→ Approval if Required
→ Implementation
→ Validation

Do not jump directly from request → implementation when research validity may be affected.

---

# 2. Proposal and Seminar Are Mandatory Project Constraints

The approved proposal and seminar report define the baseline scope and intended direction of the project.

Use them to determine:

- research question
- objectives
- approved methodology
- algorithms
- system/environment
- major variables
- intended experiments
- expected outputs
- proposed contribution
- explicit boundaries

Do not silently move outside this scope.

## But They Are Not Infallible Scientific Truth

The proposal or seminar may contain:

- a misunderstanding
- an incorrect scientific statement
- an outdated claim
- imprecise terminology
- an invalid methodological assumption
- an internal inconsistency
- an implementation assumption that does not hold

If a change exposes such a problem:

1. identify the exact problematic statement or assumption
2. explain why it may be scientifically wrong or weak
3. compare it with reliable evidence and the project's research corpus
4. classify the issue as:
   - wording/interpretation
   - implementation detail
   - methodological issue
   - experimental issue
   - fundamental scientific issue
5. determine whether it can be corrected while preserving the approved research question and core direction
6. prefer the smallest scientifically valid correction
7. never silently rewrite the project's scope
8. escalate material changes for human/advisor approval

Protect both scientific validity and approved project scope.

---

# 3. Impact Levels

## Level 0 — No Meaningful Impact

Examples:

- formatting
- comments
- local variable rename
- harmless documentation change
- internal refactor with demonstrably unchanged behavior

May proceed normally.

## Level 1 — Engineering Impact

Examples:

- API refactor
- internal architecture change
- dependency update
- non-semantic restructuring

Inspect relevant tests and dependencies.

## Level 2 — Experimental Impact

Examples:

- changing seed handling
- modifying data handling
- changing training duration
- changing experiment configuration
- changing evaluation scripts

Determine which experiments/results need rerunning or revalidation.

## Level 3 — Methodological Impact

Examples:

- changing state/observation
- changing action space
- changing reward/objective
- changing constraints
- changing model architecture in a scientifically meaningful way
- changing algorithm
- changing baseline
- changing evaluation metrics
- changing environment assumptions

Requires methodology review and experiment-impact analysis.

## Level 4 — Research-Critical Impact

Examples:

- changing the research question
- changing the central hypothesis
- changing the core methodology
- changing approved scope
- changing the central contribution
- adding/removing a central research objective

Do not implement automatically. Produce an impact report and require explicit human approval.

---

# 4. Establish the Actual Baseline

Before analyzing the change, inspect the real project state.

Relevant sources include:

- source code
- tests
- configuration
- experiment scripts
- experiment metadata
- results
- figures/tables
- documentation
- assumptions
- decision logs
- proposal
- seminar report
- thesis drafts
- local research papers
- relevant external literature when necessary

Do not analyze against an imagined architecture or an outdated description.

---

# 5. Classify the Change

Determine whether the request is primarily:

- cosmetic
- refactor
- bug fix
- implementation correction
- scientific correction
- methodology change
- experiment change
- evaluation change
- scope change
- novelty-driven change
- thesis-claim change

A single change may belong to multiple categories.

---

# 6. Code-Level Impact

Identify:

- affected files
- affected modules
- direct dependencies
- indirect dependencies
- interfaces
- configuration dependencies
- tests
- experiment pipelines
- data flow

Determine whether behavior changes or only structure changes.

Do not equate a small diff with a small scientific impact.

---

# 7. Scientific Impact

Ask:

- Does the change alter the meaning of the method?
- Does it change an assumption?
- Does it alter the optimization objective?
- Does it change what the experiment is actually testing?
- Does it make prior results incomparable?
- Does it create a confounding variable?
- Could it invalidate a claim?
- Does it require new validation?

When relevant to DRL, explicitly inspect:

- state/observation
- action
- action constraints
- reward
- reward scaling
- environment dynamics
- termination
- episode definition
- exploration
- training/evaluation protocol
- hyperparameters
- baseline design
- metrics
- random seeds
- reproducibility
- simulator behavior
- leakage
- reward hacking
- unintended incentives

---

# 8. Proposal/Seminar Compatibility

For every Level 2+ research-impacting change, compare it with the approved proposal and seminar report.

Classify it as:

### Compatible

Clearly within the approved direction.

### Clarifying

Clarifies an ambiguity without changing scope.

### Corrective

Fixes a likely scientific/technical error while preserving the intended project direction.

### Borderline

May stretch the approved scope.

### Incompatible

Materially changes the approved research question, objectives, methodology, or contribution.

Borderline and Incompatible changes must not be silently implemented.

---

# 9. Scientific Correction vs Scope Change

This distinction is mandatory.

If the proposal/seminar contains an incorrect scientific assumption:

Do NOT say:

> "The proposal says it, so we must preserve the error."

Also do NOT say:

> "The proposal is wrong, so redesign the thesis."

Instead ask:

> Can the scientific error be corrected while preserving the approved research question and core methodology?

If YES:

→ prefer the minimal scientifically valid correction.

If NO:

→ explain the scope impact and require human/advisor approval before proceeding.

Default objective:

**scientifically valid + as close as reasonably possible to the approved scope.**

---

# 10. Literature Review Trigger

Do not perform a full literature review for harmless refactoring.

Use `research-review` when the change affects:

- methodology
- scientific assumptions
- algorithm choice
- reward/objective
- state/action design
- evaluation
- current best practice
- interpretation
- contribution
- questions where recent research may materially change the decision

The need for literature review must be based on impact, not habit.

---

# 11. Novelty Review Trigger

Use `novelty-check` when the proposed change is motivated by or may affect:

- novelty
- contribution differentiation
- similarity to prior work
- adding a component mainly to create novelty
- changing the research question to avoid overlap

Never introduce complexity solely to make the thesis appear more novel.

---

# 12. Experiment Impact

Determine:

- which experiments become invalid
- which remain valid
- which must be rerun
- whether prior results remain comparable
- whether baselines must be rerun
- whether ablations are needed
- whether metrics change
- whether random seeds need control
- whether train/evaluation protocols change
- whether saved checkpoints/results remain meaningful

Never silently mix materially different configurations in one comparison.

If comparison is unfair after the change, say so explicitly.

---

# 13. Results and Thesis Impact

Determine whether the change affects:

- numerical results
- tables
- figures
- statistical analysis
- interpretation
- discussion
- limitations
- conclusions
- contribution claims
- thesis wording

If prior text or figures may become stale, identify them.

Do not leave outdated scientific claims in the thesis after a methodology-changing modification.

---

# 14. Reproducibility Impact

Check whether the change affects:

- dependency versions
- configuration
- random seeds
- data
- preprocessing
- experiment scripts
- checkpoints
- result storage
- hardware/software assumptions

A change that improves a result but damages reproducibility must be flagged.

---

# 15. History, Rollback, and Traceability

For meaningful changes:

- use a Git branch
- preserve the previous baseline
- preserve prior experiment results
- keep the change traceable
- record why it was made

Never delete evidence just because a newer version is preferred.

The project history should allow reconstruction of:

question/decision
→ implementation
→ experiment
→ result
→ interpretation

---

# 16. Approval Gate

Explicit approval is required for Level 4 changes.

For Level 3 changes, request approval when:

- previous experiments may become invalid
- approved methodology is altered
- scope may change
- thesis claims may change
- novelty assumptions may change
- scientific uncertainty is substantial

Do not create unnecessary approval friction for harmless engineering work.

---

# 17. Recommended Output Format

For meaningful changes, produce:

## Requested Change

What the researcher wants to change.

## Current Baseline

What the project currently does.

## Why It Matters

Why the change was proposed.

## Proposal/Seminar Compatibility

Compatible / Clarifying / Corrective / Borderline / Incompatible

Explain why.

## Scientific Assessment

Whether the change improves, weakens, or leaves scientific validity unchanged.

## Code Impact

Files/modules/tests affected.

## Methodology Impact

What scientific assumptions or design choices change.

## Experiment Impact

Experiments/results that must be rerun or reconsidered.

## Thesis Impact

Sections, figures, claims, or conclusions potentially affected.

## Literature / Novelty Impact

Only when relevant.

## Risks

Scientific, technical, experimental, scope, novelty, and reproducibility risks.

## Minimal Safe Change

The smallest change that achieves the intended goal while preserving scientific validity and approved scope.

## Alternatives

Other defensible options.

## Recommendation

What should be done and why.

## Approval Required

Yes / No

Explain why.

## Validation Plan

What must be tested after implementation.

---

# 18. Prevent Scope Creep

A change request is not permission to add:

- another algorithm
- another dataset
- another research question
- unnecessary metrics
- unnecessary architectures
- unrelated experiments
- unrelated features

Before expanding scope, determine:

- Is it necessary?
- Is it required to correct a scientific issue?
- Is it supported by evidence?
- Does it materially improve the research question?
- Can the goal be achieved with a smaller change?
- Is the added scope justified by the project's constraints?

Prefer the minimum necessary scope change.

---

# 19. Special Rule for "Simple" Requests

The researcher may describe a change as simple:

- "Let's just change the reward."
- "Let's move this valve."
- "Let's add this variable."
- "Let's use another metric."
- "Let's switch the model."

Do not assume the impact is simple.

Quickly determine whether the request crosses a research-impact boundary.

If it does, switch to the appropriate deeper review.

---

# 20. Final Self-Check

Before approving a change for implementation, verify:

- Did I inspect the actual current code?
- Did I inspect the proposal and seminar report?
- Did I check the current project assumptions?
- Did I distinguish scientific correction from scope change?
- Did I assess methodology impact?
- Did I assess experiment impact?
- Did I assess result and thesis impact?
- Did I check reproducibility?
- Did I trigger literature review when needed?
- Did I trigger novelty review when needed?
- Did I identify the minimum safe change?
- Did I preserve prior evidence?
- Did I request approval when required?

If any critical answer is "no", do not treat the change as fully assessed.

---

# Final Principle

Protect the project from TWO opposite failures:

## Scientific Drift

Blindly following an incorrect assumption in the proposal, seminar, existing code, or previous decision.

## Scope Drift

Abandoning the approved project whenever a new paper, idea, algorithm, or implementation opportunity appears.

The preferred path is:

**detect the problem → verify it → determine impact → find the smallest scientifically valid correction → preserve the approved direction whenever possible → obtain approval for material changes → implement → validate → update experiments, documentation, and thesis claims.**
