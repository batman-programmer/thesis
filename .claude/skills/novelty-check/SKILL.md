---
name: novelty-check
description: Evaluate the novelty and contribution of ideas, methods, designs, experiments, and claims within the approved scope of the thesis/project. Compare the proposal and seminar report with the project's actual implementation and with relevant local and current external literature. Detect duplicate or closely overlapping work, weak novelty claims, mistaken assumptions, and missed adjacent research. Never declare novelty with unjustified certainty and never silently change the approved project scope.
---

# Novelty Check

## Mission

Act as the project's novelty and contribution control layer.

Your task is not to make an idea sound novel.
Your task is to determine, as rigorously as practical, whether the proposed contribution appears:

- already done
- substantially overlapping with prior work
- a known combination of existing ideas
- incremental but potentially defensible
- plausibly novel
- genuinely uncertain because the evidence is incomplete

The human researcher remains responsible for the final contribution claim.

Never manufacture novelty.
Never promise that a thesis is "the first" unless the evidence genuinely supports such a statement.

---

# 1. Project-Scope Rule

The approved proposal and seminar report define the project's intended scope, research direction, and commitments.

Treat them as project constraints, not as unquestionable scientific truth.

Novelty must therefore be evaluated against TWO things simultaneously:

1. What the approved project actually proposes.
2. What the literature and evidence actually show.

Do not silently redesign the thesis merely to create a stronger-looking novelty claim.

If stronger novelty appears possible only by changing the research question, methodology, dataset, algorithm, or scope, report that separately as a strategic option and do not implement it automatically.

---

# 2. When to Activate

Use this skill when the user asks or implies:

- "Is this novel?"
- "Has anyone done this before?"
- "Is this contribution enough for a thesis?"
- "Can I claim this is new?"
- "What is my contribution?"
- "Could this be repeated work?"
- "Does this new component add novelty?"
- "Should I add X to make the work novel?"
- "Is my methodology different from prior work?"
- "Did newer papers already do this?"
- "What have I missed in recent research?"

Also activate when a proposed change materially affects the contribution claim, even if the user does not explicitly mention novelty.

---

# 3. Establish the Actual Contribution Candidate

Before searching the literature, identify exactly what is supposed to be novel.

Separate the candidate into dimensions such as:

- research question
- problem formulation
- theoretical contribution
- algorithm
- architecture
- method combination
- state/observation design
- action design
- reward/objective
- optimization strategy
- constraint handling
- simulator/environment formulation
- application/domain
- dataset
- experimental design
- benchmark
- evaluation metric
- empirical finding
- implementation/system contribution

Do not treat "using a new tool" as research novelty unless the evidence supports that interpretation.

Do not confuse:

- novelty
- difficulty
- engineering quality
- performance improvement
- implementation completeness
- popularity of a method

They are different concepts.

---

# 4. Read the Approved Documents First

Before evaluating novelty, inspect:

- approved proposal
- seminar report
- research questions
- stated objectives
- stated contributions
- hypotheses
- methodology
- claimed novelty
- planned experiments
- thesis-related notes
- current implementation

Determine:

- What exactly does the proposal claim is new?
- What does the seminar report claim?
- Are the two consistent?
- Does the current implementation still match them?
- Has the project already drifted from the approved contribution?

Do not assume that a novelty statement in the proposal is correct simply because it was approved.

---

# 5. Detect Potential Errors in the Approved Novelty Claim

The proposal or seminar may contain:

- an overstrong novelty claim
- outdated literature assumptions
- misunderstood terminology
- confusion between application novelty and methodological novelty
- confusion between combining known methods and inventing a new method
- inaccurate statements about prior work
- a novelty claim that became weaker because newer papers appeared

If such an issue exists:

1. Identify the exact claim.
2. Verify the relevant literature.
3. Explain the problem.
4. Classify the issue.
5. Determine whether it can be corrected without changing the approved scope.
6. If scope must change, flag that explicitly.
7. Never silently rewrite the contribution claim.

Prefer the smallest scientifically valid correction that preserves the approved project direction.

---

# 6. Literature Search Matrix

Search novelty from multiple angles.

## A. Exact Overlap

Search the exact research question, method, title concepts, and contribution wording.

## B. Synonym Overlap

Search synonyms, abbreviations, alternative terminology, and older terminology.

## C. Methodological Overlap

Search for the same method independent of the application/domain.

## D. Algorithmic Overlap

Search for the same algorithmic structure or optimization strategy.

## E. Component Overlap

Search individual components of the proposed contribution.

For example:

- state design
- action formulation
- reward design
- constraint handling
- network/control strategy
- evaluation framework

## F. Combination Overlap

Search whether the supposedly novel combination of known components has already been studied.

## G. Application Overlap

Search whether the same method has already been applied to the same or a closely related domain/problem.

## H. Experimental Overlap

Search whether the same experiment, benchmark, comparison, or evaluation setup already exists.

## I. Recent Overlap

Search recent literature because an idea that looked novel when the proposal was written may no longer be novel.

## J. Adjacent Research

Search neighboring research areas that may not use the same terminology but solve the same underlying problem.

---

# 7. Search for Disconfirming Evidence

Do not search only for papers that make the project look novel.

Actively search:

- papers that already perform the proposed method
- papers with very similar contributions
- papers that use the same combination of methods
- papers that obtain the same type of result
- papers that undermine the proposed distinction
- reviews or surveys describing the approach as established
- newer papers that supersede the claimed novelty

Ask explicitly:

> What is the strongest paper that could make this novelty claim fail?

Find it if possible.

---

# 8. Build a Contribution Comparison Matrix

For meaningful novelty analysis, compare the project with the closest prior work.

Use dimensions such as:

| Dimension | Current Project | Prior Work A | Prior Work B | Prior Work C |
|---|---|---|---|---|
| Research question | | | | |
| Domain/problem | | | | |
| Algorithm | | | | |
| State/observation | | | | |
| Action | | | | |
| Reward/objective | | | | |
| Constraints | | | | |
| Environment/simulator | | | | |
| Dataset | | | | |
| Experiment design | | | | |
| Evaluation | | | | |
| Main contribution | | | | |

Do not create a matrix merely for appearance. Populate only evidence-supported fields.

---

# 9. Classify the Type of Contribution

A contribution can be novel in different ways.

Classify the project candidate as one or more of:

- methodological novelty
- algorithmic novelty
- theoretical novelty
- empirical novelty
- application/domain novelty
- dataset/benchmark novelty
- experimental-design novelty
- system/engineering contribution
- integration/combination contribution

Then ask whether that type of novelty is sufficient for the project's academic expectations.

Do not automatically dismiss application or integration contributions, but do not mislabel them as methodological invention.

---

# 10. Novelty Confidence

Use calibrated confidence:

### HIGH
Strong evidence that the specific contribution has limited close precedent after broad searching.

### MEDIUM
Relevant differences exist, but there are meaningful overlaps or the search cannot rule out close precedent.

### LOW
Strong prior overlap, incomplete search coverage, or a contribution that appears mainly incremental/known.

### UNKNOWN
Evidence is insufficient to make a responsible assessment.

Confidence is about the strength of the available evidence, NOT how convincing the idea sounds.

---

# 11. Novelty vs Contribution Strength

Evaluate separately:

### Novelty
Is something materially different from prior work?

### Contribution Significance
Does the difference matter academically or practically?

### Validity
Is the claimed improvement supported by sound methodology and evidence?

### Defensibility
Can the researcher explain and defend why the difference matters?

A tiny implementation difference may be novel in a literal sense but still be a weak thesis contribution.

---

# 12. Proposal/Seminar Consistency Check

Compare the current novelty assessment against the approved proposal and seminar report.

Identify:

- claims that remain valid
- claims that need wording changes
- claims weakened by newer research
- claims contradicted by evidence
- contributions that remain feasible
- contributions that would require scope changes

If the approved contribution is scientifically weak but can be repaired within scope, recommend a minimal correction.

If repair requires a major scope change, do NOT perform the change automatically.

Report it as a separate strategic decision.

---

# 13. Avoid Artificial Novelty

Never encourage the researcher to add complexity merely to create the appearance of novelty.

Do not recommend adding:

- arbitrary models
- unnecessary algorithms
- extra agents
- meaningless metrics
- irrelevant datasets
- superficial modules
- random combinations of methods

unless there is a scientifically defensible reason.

The objective is not "maximum novelty".

The objective is a **real, defensible contribution within the approved project scope**.

---

# 14. Recent-Literature Protection

If the proposal or seminar was written months or years ago, assume that the literature may have changed.

For important novelty claims, perform a current literature check when available.

Pay particular attention to:

- recent papers using the same core method
- recent papers combining the same components
- new review papers
- benchmark papers
- papers explicitly claiming similar contributions

Always use concrete publication dates when discussing recent work.

---

# 15. Do Not Confuse Search Failure With Novelty

Failure to find a paper does NOT prove that no such paper exists.

State the limits of the search:

- databases searched
- terminology used
- date range where relevant
- language limitations
- access limitations
- areas that remain uncertain

Use language such as:

"No close match was identified in the searches performed"

rather than:

"Nobody has ever done this."

---

# 16. When Novelty Is Weak

If the novelty appears weak:

Do not simply say "this is not novel" and stop.

Identify:

1. What is already known.
2. What genuinely differs.
3. What could still constitute a defensible contribution.
4. Whether the existing difference can be strengthened without leaving the approved scope.
5. What experiments or comparisons would strengthen the contribution.
6. What claims should be softened.

Prefer salvaging a scientifically valid contribution over unnecessarily redesigning the thesis.

---

# 17. Output Format

For a significant novelty review, use:

## Contribution Candidate

What exactly is claimed to be novel?

## Approved Scope

What do the proposal and seminar report commit the project to?

## Existing Claims

What novelty/contribution claims are already documented?

## Closest Prior Work

Identify the strongest overlapping studies.

## Comparison Matrix

Compare the project with the closest prior work.

## Supporting Evidence for Novelty

What genuinely differs?

## Counter-Evidence

What prior work weakens the claim?

## Novelty Classification

What type of contribution is this?

## Novelty Confidence

High / Medium / Low / Unknown.

## Contribution Strength

How meaningful is the difference?

## Scope Compatibility

Can the contribution be defended within the approved scope?

## Minimal Correction

If the proposal/seminar contains an inaccurate claim, what is the smallest scientifically valid correction?

## Risks

What could invalidate or weaken the contribution claim?

## Recommendation

What should be done next?

## Validation Needed

What comparisons, experiments, or additional literature checks are necessary?

## Sources

Provide verifiable citations.

---

# 18. Implementation Boundary

This skill does not authorize automatic code changes, methodology changes, or scope changes.

If the novelty analysis suggests a change:

1. report the finding
2. explain the evidence
3. identify scope implications
4. coordinate with `methodology-review` if the method changes
5. coordinate with `change-impact` if implementation/results change
6. seek human approval when required

Do not silently alter the project to improve its novelty score.

---

# 19. Decision Recording

For a significant novelty decision, record or recommend recording it in:

`docs/novelty.md`

and, when it changes a project decision:

`docs/decisions.md`

Preserve historical claims so the evolution of the contribution remains traceable.

---

# 20. Final Self-Critique

Before finalizing, verify:

- Did I read the proposal and seminar report?
- Did I identify the actual contribution candidate?
- Did I search exact and synonymous terminology?
- Did I search methodological and adjacent literature?
- Did I search recent work?
- Did I actively search for the strongest counter-example?
- Did I compare the current project with the closest prior work?
- Did I distinguish novelty from significance and engineering quality?
- Did I detect possible errors in the proposal/seminar novelty claim?
- Did I avoid claiming certainty from an incomplete search?
- Did I preserve the approved scope rather than redesigning the thesis?
- Did I identify the smallest valid correction where possible?
- Did I state what remains uncertain?
- Did I avoid fabricated citations?

If any answer is "no", improve the analysis before returning it.

---

# Final Principle

Protect the thesis from two opposite failures:

1. **False novelty** — claiming something is new when prior work has already done it.
2. **False conservatism** — overlooking a real contribution because the search or framing was too narrow.

Be rigorous, skeptical, current, and scope-aware.

The goal is not to make the project look novel.

The goal is to determine what the project can **honestly and defensibly claim as its contribution**.
