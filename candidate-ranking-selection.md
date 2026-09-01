# Candidate Ranking and Selection

## Purpose

This document defines the executable baseline for comparing already-generated, already-evaluated recommendation candidates.

It covers the boundary introduced by PR #35 between:

- candidate generation in `candidate_generation.py`;
- hard candidate evaluation in `recommendation.py`; and
- deterministic ranking/global selection in `candidate_selection.py`.

The selector is intentionally a thin layer. It does not create physical candidate paths, re-run compatibility reasoning, reinterpret hard constraints, invent missing evidence, or encode SKU-pair preferences.

## Layer ownership

### Candidate generation owns physical path identity

`GeneratedCandidate` retains the original `CandidatePathSelection` and evaluator-ready `CandidateConfiguration`.

Candidate identity includes the physical choices needed to distinguish one path from another, including where applicable:

- tool reference;
- ToolAttachment assembly reference;
- selected installation feature;
- tether reference;
- tool-side and anchor-side endpoint/target bindings;
- anchor path; and
- selected component instance references.

Ranking must preserve this object rather than reconstruct candidate provenance from product IDs or from the canonical `candidate_id` string.

### Candidate evaluation owns hard viability

`CandidateEvaluation` is the sole authority for whether one candidate may remain in consideration.

The ranking layer uses exactly:

```text
viable <=> CandidateEvaluation.recommendation_state is not None
```

A blocked candidate can never be rescued by a better ranking score, fewer components, a preferred brand, a stronger-looking source count, or any other preference.

Conversely, `recommended_with_constraints` is still viable when all hard checks pass but a validated runtime verification or required pre-use action remains pending.

### Candidate selection owns ordering and global exhaustion over a complete evaluated set

`rank_and_select_candidates()` accepts generated candidates and their evaluations, validates exact identity coverage, partitions viable from blocked candidates, ranks the viable partition, and selects rank 1.

It may conclude global exhaustion only under the bounded conditions described below.

## Input completeness and identity

Before ranking, the selector requires:

- every generated candidate ID to be unique;
- every evaluation candidate ID to be unique; and
- the generated candidate ID set to exactly equal the evaluation candidate ID set.

Missing evaluations fail closed. Unexpected evaluations also fail closed.

The selector does not silently rank a partially evaluated subset.

`EvaluatedCandidate` additionally validates that its retained `GeneratedCandidate.configuration.candidate_id` exactly matches its `CandidateEvaluation.candidate_id`.

This pairing keeps physical selection/provenance attached to the evaluation throughout ranking.

## Baseline ranking order

The baseline is lexicographic, not a weighted score. Lower tuple values are preferred in this order:

1. recommendation state;
2. total pending pre-use conditions;
3. pending physical-verification count;
4. connection-evidence weakness;
5. review signal; and
6. canonical candidate ID.

### 1. Recommendation state

`recommended` ranks before `recommended_with_constraints`.

This is a preference among already viable candidates, not a new viability test.

### 2. Total pending conditions

Among candidates in the same recommendation-state tier, prefer fewer combined:

- pending runtime connection verifications; and
- pending non-connection pre-use actions.

This favors a candidate that requires less work or uncertainty before use.

### 3. Pending physical verification

When total pending burden is equal, prefer fewer pending physical verifications.

For example, one known pre-use action may rank ahead of one unresolved physical fit that must be verified at runtime, because the former is a known procedure while the latter reflects weaker pre-use evidence about the actual connection.

This ordering does not make pre-use actions optional. The selected candidate remains `recommended_with_constraints` until its required actions are satisfied.

### 4. Connection evidence

Connection evidence is intentionally coarse.

The current selector treats catalogue-established bases as one tier:

```text
manufacturer_declared
validated_geometry
validated_interface_class
```

It does **not** claim that one of these is universally stronger than another.

`runtime_verification` is a weaker ranking basis because final fit depends on a session/configuration check.

`none` is weaker still. Under normal hard evaluation, a viable connection should not depend on `none`; keeping it last is a conservative ordering rather than a new compatibility rule.

The selector does not use:

- number of supporting URLs;
- number of eligibility proofs;
- number of claims;
- source count; or
- arbitrary evidence-provider ordering

as evidence-strength proxies.

### 5. Review signal

When earlier ranking factors tie, a candidate without `review_required` ranks ahead of one carrying an internal review signal.

`review_required` is not itself a hard blocker in this layer. Any review condition that must block the candidate must already have been represented by the evaluator's hard result.

### 6. Deterministic final tie-break

A complete tie is broken by canonical `candidate_id` lexical order.

Input list order is never a ranking signal.

This makes selection deterministic across equivalent caller ordering.

## Result invariants

`CandidateSelectionResult` partitions the complete paired set into:

- `ranked_viable_candidates`; and
- `blocked_candidates`.

A candidate cannot appear in both partitions, and IDs must remain unique inside each partition.

For `state = selected`:

- a selected candidate must exist;
- the viable ranking must be non-empty;
- `selected` must itself be viable; and
- `selected` must equal the complete first `EvaluatedCandidate` object in the ranked viable list.

The last invariant is deliberately stronger than matching only `candidate_id`: a reconstructed object with the same ID but different evaluation/provenance must not contradict the ranked winner.

## Global outcome states

### `selected`

Use when at least one supplied candidate is viable after exact evaluation coverage has been established.

The selected candidate is rank 1 of the deterministic viable ordering.

### `no_suitable_recommendation`

Use only when:

- the supplied generated candidate set is non-empty;
- exact one-to-one evaluation coverage has been established; and
- every supplied candidate is blocked by the existing evaluator.

This is the first layer allowed to widen individual candidate failure into a global recommendation outcome.

### `no_generated_candidates`

An empty generated candidate set remains a distinct outcome.

The selector does not infer why generation produced no candidates and therefore does not call that state `no_suitable_recommendation`.

Possible upstream meanings include catalogue incompleteness, unavailable applicable paths, generation-scope decisions, or other conditions that require their own explanation.

## Standalone completeness boundary and end-to-end closure

Exact selector coverage proves:

```text
every supplied generated candidate was evaluated
```

It does **not** by itself prove:

```text
the caller supplied the generator's complete output
```

A caller could incorrectly pass only a subset of generated alternatives and still satisfy the selector's internal coverage check for that subset.

PR #36 closes that caveat for normal end-to-end recommendation runs through `run_recommendation()`. The recommendation-run boundary owns the generator invocation, evaluates every candidate in the generator's actual returned list exactly once, and passes that exact complete generated/evaluated set into this selector.

The selector remains reusable on its own, so callers that invoke it directly must still respect the narrower completeness guarantee above. System-level global exhaustion should normally come from the end-to-end recommendation-run boundary when generation is part of the same decision. See `recommendation-run.md` for the orchestration invariant and failure semantics.

## Deliberate non-preferences

The baseline selector does not prefer candidates based on:

- brand or manufacturer;
- exact SKU pairing;
- direct attachment versus ToolAttachment path;
- fewer physical components;
- capacity headroom beyond passing the hard requirement;
- tether product family;
- shorter/longer tether by default;
- installation method aesthetics; or
- catalogue source/provider identity.

Any future preference must be justified by an explicit reusable context or policy rule and must not silently become a hard constraint.

## Contextual ranking is intentionally separate

The baseline ordering handles evidence/condition burden and determinism without pretending work context exists when it does not.

Future context rules may change the ordering of viable candidates when explicit scenario facts are available, for example:

- elevated snag risk;
- required reach;
- environmental exposure; or
- anchorage constraints that are preferences rather than hard policy/technical exclusions.

A future contextual layer should:

- receive explicit normalized context;
- receive explicit candidate facts needed by the applicable rule;
- leave missing context neutral rather than inventing a preference;
- preserve the evaluator's hard-viability decision; and
- retain deterministic fallback ordering.

## Session verification and fallback

The ranked viable list is intended to support later session behavior.

If the selected candidate carries pending runtime verification or pre-use actions, TetherLens should emit that candidate as a conditional recommendation before asking the worker to satisfy the condition.

If a required runtime verification later fails for the actual session/configuration, the candidate should be rejected for that session and the system should move deterministically to the next ranked viable alternative.

A successful runtime check is session/configuration evidence. It must not silently become a universal catalogue claim that two SKUs are compatible.

The session-state/fallback model is not implemented by the baseline selector itself.

## Test expectations

The ranking/selection layer should continue to have focused unit coverage for at least:

- blocked candidates never being ranked or selected;
- fully recommended candidates ranking ahead of conditional candidates;
- fewer pending conditions ranking ahead of greater burden;
- known pre-use action versus pending physical verification at equal burden;
- established connection evidence ranking ahead of runtime dependence;
- review signal acting only as a late preference;
- input-order-independent deterministic ties;
- original candidate selection/component provenance retention;
- exact evaluation coverage;
- duplicate identity rejection;
- empty generation remaining distinct from exhausted evaluated alternatives; and
- selected-result structural equality with the first ranked candidate.

The existing ingestion benchmark remains a supply-side catalogue/readiness benchmark. A separate ranking golden benchmark should only be introduced when TetherLens has explicit scenario/context inputs and stable expected cross-candidate outcomes that cannot be expressed cleanly as focused unit tests.
