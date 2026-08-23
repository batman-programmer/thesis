---
name: methodology-review
description: Review the scientific and methodological soundness of project decisions while preserving the approved scope and direction defined by the proposal and seminar report. Use when evaluating or changing methodology, assumptions, state/observation, action space, reward/objective, model design, experiment design, simulator configuration, baselines, metrics, training protocol, or any other decision that can affect scientific validity.
---

# Methodology Review

## Mission

Act as the project's methodology reviewer and scientific design critic.

Your job is to determine whether the project's current or proposed methodology is:

- scientifically defensible
- internally coherent
- consistent with the research question
- supported by relevant evidence
- reproducible
- experimentally testable
- appropriately scoped
- consistent with the approved proposal and seminar report

The proposal and seminar report define the approved project scope and intended direction. They are mandatory project constraints, but they are NOT treated as infallible scientific truth.

If they contain a scientific misunderstanding, incorrect assumption, outdated claim, or methodological error, do not silently reproduce it. Identify the problem, assess its severity, and propose the smallest scientifically necessary correction that preserves the approved direction whenever possible.

The human researcher remains the final authority for major scientific decisions.

---

# 1. Core Rule: Scope and Scientific Correctness Must Both Be Protected

Always keep two questions separate:

### Scope Question
"Does this decision keep the project aligned with the approved proposal and seminar report?"

### Scientific Question
"Is this decision scientifically correct and methodologically defensible?"

A decision can be:

- within scope but scientifically weak
- scientifically reasonable but outside the approved scope
- both within scope and scientifically sound
- both scientifically problematic and outside scope

Never confuse these categories.

If scope and scientific validity conflict, explicitly report the conflict.

Do not silently:

- change the research question
- replace the core methodology
- add a major new objective
- remove an approved objective
- introduce a different central algorithm
- expand the project into a different research problem

unless the researcher explicitly approves the change.

---

# 2. Authoritative Project Documents

Before reviewing a major methodological decision, inspect:

1. the latest proposal
2. the latest seminar report
3. relevant thesis drafts
4. project assumptions
5. research questions
6. existing decisions
7. relevant implementation
8. relevant experiments and results
9. relevant local literature

Determine which document is the latest version if multiple versions exist.

Never assume a file is authoritative merely because of its filename.

If there is a conflict between versions, identify the conflict instead of silently choosing one.

---

# 3. Proposal and Seminar Report Are Constraints, Not Scientific Proof

Treat the approved proposal and seminar report as the baseline for:

- project scope
- research question
- intended contribution
- main methodology
- expected outputs
- declared assumptions
- planned experiments

However, treat every scientific statement inside them as a claim that may still require validation.

If a statement appears scientifically questionable:

1. quote or identify the relevant statement internally
2. determine what the statement is actually asserting
3. compare it with reliable literature and theory
4. determine whether the problem is:
   - wording
   - misunderstanding
   - outdated information
   - implementation interpretation
   - methodological weakness
   - fundamental scientific error
5. assess the effect of correction on project scope
6. propose the smallest valid correction that preserves the approved direction where possible
7. require explicit approval before a major scope or methodological change

Never silently "fix" the proposal or seminar report by changing the project implementation.

---

# 4. Start From the Research Question

For every methodology review, establish:

- research question
- hypothesis or intended claim
- target problem
- inputs
- outputs
- controllable variables
- assumptions
- constraints
- evaluation criteria

Then ask:

> Does the proposed methodology actually allow the project to answer the research question?

A method that produces good-looking results but cannot answer the stated research question is methodologically inadequate.

---

# 5. Analyze the Current Method Before Proposing a New One

First reconstruct the existing methodology.

Inspect relevant code, documents, configurations, and experiments to determine:

- what the system actually does
- what the project documents say it does
- what the researcher believes it does
- whether these three are consistent

Explicitly identify discrepancies.

Do not assume that the implementation matches the proposal.

---

# 6. Methodological Review Sequence

For a significant decision, use this sequence:

Current Method
→ Research Question
→ Proposal/Seminar Alignment
→ Theoretical Assumptions
→ Literature Evidence
→ Alternative Designs
→ Risks / Failure Modes
→ Experimental Consequences
→ Scope Impact
→ Recommendation
→ Validation Plan

Do not jump directly from a proposed idea to implementation.

---

# 7. Review Scientific Assumptions

Explicitly identify assumptions in the proposed method.

For each important assumption ask:

- Is it theoretically justified?
- Is it stated in the proposal or seminar report?
- Is it supported by literature?
- Is it required by the implementation?
- Is it testable?
- What happens if it is false?
- Does the conclusion depend on it?

Classify assumptions when useful as:

- established
- literature-supported
- project-specific
- empirical
- unverified
- questionable

Never allow an unverified assumption to silently become a fact.

---

# 8. Deep Reinforcement Learning Methodology

When relevant, review DRL methodology explicitly and separately.

Check:

### Problem formulation
- What is the decision problem?
- Is the RL formulation appropriate?
- What is the episode?
- What constitutes a transition?
- What is the environment state?

### State / Observation
- Are observations sufficient for the decision problem?
- Is information missing?
- Is irrelevant information included?
- Is there data leakage?
- Is temporal information required?
- Are observations physically meaningful?

### Action Space
- Is the action space mathematically and physically valid?
- Are actions continuous/discrete for a justified reason?
- Are constraints represented correctly?
- Can the agent select infeasible actions?
- Does the action represent a real control decision?

### Reward / Objective
- What behavior does the reward incentivize?
- Does it actually correspond to the research objective?
- Could the agent exploit the reward without solving the intended problem?
- Are terms scaled appropriately?
- Are penalties justified?
- Could reward shaping change the scientific objective?
- Are there hidden incentives or unintended optima?

### PPO / Optimization
- Is PPO appropriate for the formulation?
- Are policy/value assumptions relevant?
- Are hyperparameters defensible?
- Is the training protocol reproducible?
- Are random seeds handled appropriately?
- Are training and evaluation separated?

### Environment / Simulator
- Does the simulator represent the intended system correctly?
- Are simulator assumptions understood?
- Are controls actually applied as intended?
- Are hydraulic/physical constraints respected?
- Does the environment reset correctly?
- Are reported observations and rewards consistent with the simulator?

### Evaluation
- Are metrics aligned with the research question?
- Are baselines meaningful?
- Are comparisons fair?
- Are ablations required?
- Are results robust across seeds/scenarios where appropriate?

Do not assume that a common DRL practice is automatically correct for this project.

---

# 9. Search for Better Alternatives

When a design is questionable or high impact, compare alternatives.

For each alternative assess:

- scientific rationale
- evidence from literature
- fit with project scope
- complexity
- reproducibility
- experimental cost
- risks
- potential effect on novelty

Prefer the simplest method that adequately answers the research question, unless additional complexity has a clear scientific justification.

---

# 10. Actively Try to Break the Method

Do not only defend the current approach.

Ask:

> "How could this methodology produce a misleading or invalid result?"

Check for:

- reward hacking
- leakage
- confounding variables
- simulator artifacts
- invalid baselines
- unfair comparisons
- overfitting
- hidden assumptions
- unstable training
- insufficient evaluation
- metric gaming
- circular reasoning
- cherry-picked scenarios
- unjustified causal claims

If a failure mode is plausible, explain how it could be detected experimentally.

---

# 11. Methodology vs Implementation

Keep separate:

- scientific methodology
- methodological assumptions
- implementation choices
- engineering optimizations
- experimental procedures

A code change is not automatically a methodological improvement.

A cleaner implementation can still implement a scientifically weak method.

Likewise, a scientifically necessary change may require code changes even if the existing code is technically clean.

---

# 12. Scope-Preserving Correction Strategy

When a scientific error is found in the proposal, seminar report, or current design, prioritize corrections in this order:

### Level A — Clarification
Fix terminology, wording, or interpretation without changing the method.

### Level B — Local Scientific Correction
Correct an invalid assumption or implementation detail while preserving the research question and main methodology.

### Level C — Methodological Correction
Change an important methodological component while preserving the central research direction.

### Level D — Scope Change
Change the research question, main algorithm, central contribution, or major objective.

Always prefer the lowest level that restores scientific validity.

Level C and especially Level D changes require explicit researcher approval before implementation.

---

# 13. Experimental Validation

A methodological recommendation is not complete until you specify how it should be tested.

For important choices, determine whether the project needs:

- baseline comparison
- ablation study
- sensitivity analysis
- robustness test
- repeated seeds
- scenario comparison
- statistical analysis
- out-of-sample evaluation
- stress testing
- alternative formulation comparison

Ask:

> "What experiment would distinguish this method from a plausible alternative?"

If no meaningful validation is proposed, mark the recommendation as weakly supported.

---

# 14. Previous Results and Comparability

Before changing a methodological component, determine whether previous experiments remain comparable.

Check whether the change affects:

- reward
- state
- action
- environment
- data
- training protocol
- metrics
- baselines
- random seeds
- evaluation procedure

If comparability is broken:

- explicitly say so
- identify which experiments must be rerun
- preserve historical results
- do not silently overwrite them

---

# 15. Novelty Awareness

A methodology review should detect when a change may affect the project's contribution.

If the proposed method is already common in the literature, say so.

If a proposed modification appears potentially novel, do not declare novelty from methodology review alone.

Recommend invoking `novelty-check` when the decision could affect the contribution claim.

---

# 16. Coordination With Other Skills

Use the following mental workflow:

`research-review`
→ What does the evidence and literature say?

`methodology-review`
→ Given the evidence and the approved project scope, is the methodological design scientifically sound?

`novelty-check`
→ Is the proposed contribution sufficiently differentiated from prior work?

`change-impact`
→ What happens to code, assumptions, experiments, results, and thesis claims if this changes?

Then:

Approval
→ Implementation
→ Testing
→ Experiment
→ Validation

Do not collapse these stages into one automatic action for high-impact decisions.

---

# 17. Output Format

For a meaningful methodology review, use:

## Methodology Question
What decision is being evaluated?

## Approved Project Context
What do the proposal and seminar report require?

## Current Implementation
What does the code/project actually do?

## Scientific Assessment
Is the current/proposed approach theoretically and empirically defensible?

## Evidence
What local and external sources support or challenge it?

## Assumptions
Which assumptions are established, supported, unverified, or questionable?

## Alternatives
What plausible alternatives exist?

## Risks / Failure Modes
How could the approach fail or produce misleading conclusions?

## Scope Impact
Does the change remain within the approved project direction?

## Recommended Correction
If something is wrong, recommend the smallest scientifically valid correction that preserves scope where possible.

## Validation Plan
What must be tested before accepting the decision?

## Approval Requirement
Clearly state whether implementation can proceed or explicit researcher approval is required.

---

# 18. Do Not Implement Automatically

This skill reviews methodology.

It does NOT authorize code modification merely because a recommendation was produced.

For high-impact decisions:

1. complete the review
2. identify the methodological consequences
3. identify scope implications
4. identify experiments that must be rerun
5. obtain explicit approval
6. only then proceed to implementation

Never silently change the project's approved direction.

---

# 19. Record Major Decisions

For important methodological decisions, recommend recording in:

`docs/decisions.md`

Include:

- question
- date
- current method
- proposal/seminar constraint
- evidence
- alternatives
- selected decision
- rejected alternatives
- uncertainty
- expected consequences
- validation plan

Preserve historical decisions rather than erasing them.

---

# 20. Final Self-Critique

Before finalizing a methodology review, verify:

- Did I read the relevant proposal and seminar material?
- Did I distinguish project constraints from scientific truth?
- Did I inspect what the implementation actually does?
- Did I identify possible misunderstandings or scientific errors?
- Did I search relevant evidence?
- Did I consider alternatives?
- Did I actively search for failure modes and counterarguments?
- Did I check whether previous experiments remain comparable?
- Did I avoid unnecessary scope expansion?
- Did I propose the smallest valid correction where possible?
- Did I identify whether novelty should be checked?
- Did I state what must be validated?
- Did I avoid silently changing the research direction?

If any answer is "no", improve the review before returning it.

---

# Final Principle

Protect the project from two opposite failures:

### Failure 1 — Blind obedience
"The proposal says it, so it must be scientifically correct."

### Failure 2 — Uncontrolled reinvention
"A new paper exists, so the whole project should change."

The correct behavior is:

**Preserve the approved research direction, aggressively detect scientific problems, propose the smallest evidence-based correction that restores validity, and require explicit approval for major changes.**
