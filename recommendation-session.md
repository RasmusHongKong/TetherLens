# Recommendation Session Resolution and Fallback

## Purpose

This document defines the session-local layer that sits after one complete `RecommendationRunResult`.

The recommendation run remains the authority for:

- the complete generated candidate set;
- every hard `CandidateEvaluation`;
- contextual infeasibility;
- deterministic ranking of selectable candidates; and
- the global selector outcome.

The session layer does not repeat any of those decisions. It records only what happens when a ranked selectable candidate has one or more conditions that were already pending in its original hard evaluation.

The intended flow is:

```text
complete RecommendationRunResult
        ↓
original ranked selectable candidates
        ↓
current candidate has pending runtime/pre-use conditions?
        ↓
record terminal session outcome for one original pending condition
        ↓
condition satisfied -> retain candidate
condition failed    -> reject candidate for this session/configuration only
        ↓
if rejected, advance to next candidate in ORIGINAL ranking
        ↓
if all ranked selectable candidates are rejected
        -> session-local exhaustion
```

This closes the runtime fallback gap without mutating catalogue evidence, creating SKU-pair compatibility, regenerating candidates, or introducing a second ranking model.

## Executable boundary

The reusable entry point is:

```python
resolve_recommendation_session(
    recommendation_run,
    resolutions=None,
)
```

The input run must have:

```text
recommendation_run.selection.state == selected
```

A run that already ended as `no_generated_candidates` or `no_suitable_recommendation` has no ranked selectable recommendation to resolve and therefore does not create a session fallback workflow.

## Immutable upstream authority

`RecommendationRunResult` is retained directly on `RecommendationSessionResult`.

The session layer must not:

- modify `GeneratedCandidate`;
- modify `CandidateEvaluation`;
- change `CandidateEvaluation.recommendation_state`;
- rewrite pending verification/action identifiers;
- re-run `evaluate_candidate_configuration()`;
- re-run `rank_and_select_candidates()` to remove a failed session candidate;
- move a contextually infeasible or hard-blocked candidate into the fallback stream;
- infer new connection compatibility;
- persist a successful field observation as a universal catalogue claim; or
- generate new alternatives.

In particular, a candidate that originally had:

```text
recommendation_state = recommended_with_constraints
```

continues to retain that hard evaluation even after all of its session conditions have been satisfied.

The session result may expose that the active candidate has no remaining pending conditions and is therefore ready for use in the current session/configuration, but it does not pretend the catalogue evaluation was originally unconditional.

## Condition identity

The hard evaluator currently exposes two pending-condition namespaces:

```text
pending_verification_connection_ids
pending_action_constraint_ids
```

Session resolution wraps those identifiers in explicit candidate scope:

```text
(candidate_id, condition_kind, condition_id)
```

with:

```text
condition_kind = runtime_verification | pre_use_action
```

This candidate scope is mandatory.

Local connection/interface identifiers and product-constraint identifiers can repeat across alternative candidate paths. A condition result for one candidate must therefore never be applied to another candidate merely because the local condition identifier looks the same.

## Condition outcomes

The session layer records only terminal outcomes:

```text
satisfied
failed
```

There is no stored `pending` resolution.

Pending is represented by the absence of a terminal resolution for an originally pending condition.

This keeps the overlay small and avoids copying the original evaluation state into a second mutable condition model.

### Satisfied

A satisfied condition means that one original pending requirement has been completed successfully for the actual session/configuration.

Examples include:

- a bounded physical connection verification passing all required observations;
- a manufacturer-required pre-use attachment test passing; or
- a required pre-use waiting/action condition having been completed.

A satisfied condition does not create new catalogue compatibility or erase the original conditional evaluation.

### Failed

A failed condition rejects that candidate for the current session/configuration.

Any failed condition is sufficient to reject the candidate even when other candidate conditions have already been satisfied or remain pending.

Failure does not rewrite the original candidate as globally or catalogue-intrinsically incompatible.

## Candidate fallback

Fallback traverses exactly:

```text
recommendation_run.selection.ranked_viable_candidates
```

and no other partition.

For each candidate:

```text
session_rejected(candidate)
    <=> at least one candidate-scoped original pending condition has outcome failed
```

The active candidate is:

```text
first candidate in original ranked_viable_candidates
whose session_rejected(candidate) is false
```

No survivor is re-ranked.

For example, if the original selector produced:

```text
A
B
C
D
```

then:

```text
A fails -> B becomes active
B fails -> C becomes active
```

The session layer cannot decide that D should now outrank C because of a new heuristic or because one of D's conditions looks easier. Ranking responsibility remains entirely upstream.

## Lazy resolution invariant

Lower-ranked candidate conditions must not be resolved before every higher-ranked candidate before them has failed.

Valid progression:

```text
A failed
B failed
C active: some conditions satisfied, some pending
D no session resolutions
```

Invalid progression:

```text
A still active
B already verified
C already verified
```

This preserves the recommendation-engine workflow of presenting and checking one preferred configuration at a time rather than requiring workers to obtain and assemble lower-ranked alternatives unnecessarily.

It also gives deterministic progression without requiring timestamps or a separate mutable event-order model in this slice.

## Deterministic resolution ordering

Callers may supply terminal condition resolutions in any list order.

The session result canonicalizes them by:

1. original candidate ranking; then
2. original condition order inside that candidate evaluation.

Within one candidate, pending physical verification identifiers are ordered before pending pre-use-action identifiers because that is the retained hard-evaluation structure.

Input list order is never a semantic signal.

## Session result

`RecommendationSessionResult` retains:

```text
recommendation_run
    exact immutable originating RecommendationRunResult

resolutions
    canonical candidate-scoped terminal session resolutions

state
    active | exhausted

active_candidate
    exact original EvaluatedCandidate currently in use,
    or null when the ranked selectable stream is exhausted

active_pending_conditions
    original pending conditions on the active candidate
    that have no terminal session resolution

active_satisfied_conditions
    satisfied terminal resolutions belonging to the active candidate

rejected_candidates
    original EvaluatedCandidate objects rejected by failed session conditions,
    retained in original ranking order
```

The convenience property:

```text
ready_for_use
```

is true only when an active candidate exists and has no remaining pending session conditions.

This does not mutate the hard recommendation state.

## Session-local exhaustion

Session exhaustion is distinct from selector-level `no_suitable_recommendation`.

Selector-level exhaustion means:

```text
complete generated/evaluated set
AND no selectable candidate remains after hard evaluation + contextual feasibility
```

Session exhaustion means:

```text
the original run DID have ranked selectable candidates
AND each one has subsequently been rejected by at least one failed session condition
```

Therefore a session may have:

```text
recommendation_run.selection.state == selected
RecommendationSessionResult.state == exhausted
```

without contradiction.

The global run remains an immutable record that a defensible ranked recommendation set originally existed. The session overlay records that none of those candidates survived actual runtime/pre-use resolution for this particular session/configuration.

## Reach/context preservation

Session resolution does not reclassify contextual knowledge.

For example, a selected candidate may be a required-reach fallback whose:

```text
tether_max_length_mm = unknown
```

Passing its physical runtime verification does not prove that it meets the requested reach.

The retained `RecommendationRunResult.ranking_context`, generated candidate facts, and reach-unknown qualification remain unchanged.

Likewise, a candidate already placed in `contextually_infeasible_candidates` cannot become a session fallback merely because a runtime action succeeds.

## Primitive evaluators remain upstream of the generic session overlay

Connection and product-constraint modules already own family-specific semantics such as:

- which structured gated-connector observations produce pending/passed/failed verification;
- whether a bond-time requirement remains an action;
- whether a required pre-use attachment test passes or fails.

This session slice does not duplicate those rules.

A future adapter may take a family-specific structured observation/result and produce the corresponding candidate-scoped `SessionConditionResolution`.

That adapter must still respect the original pending condition identifier and candidate identity. The generic fallback layer should remain ignorant of connector geometry, adhesive semantics, manufacturer SKU pairs, and individual constraint keys.

## Validation and fail-closed behavior

Session resolution rejects:

- candidate IDs outside `ranked_viable_candidates`;
- contextually infeasible candidates;
- hard-blocked candidates;
- unknown condition identifiers;
- the correct identifier under the wrong condition kind;
- duplicate terminal results for one candidate-scoped condition;
- duplicate pending identifiers within one candidate/kind scope; and
- resolutions for a lower-ranked candidate before the current candidate has failed.

A directly constructed/deserialized `RecommendationSessionResult` also recomputes its deterministic projection from the retained run and resolutions and must match that projection exactly.

This prevents persisted session objects from silently replacing the active candidate, losing rejected-candidate provenance, or misreporting condition state.

## Deliberate boundaries

This slice does not add:

- session persistence storage;
- timestamps or event sourcing;
- retry/reopen semantics after a failed condition;
- automatic mapping from all primitive observation objects into session resolutions;
- user-facing recommendation prose;
- environmental contextual rules;
- new compatibility rules;
- SKU-pair compatibility;
- cross-candidate shared-condition inference;
- catalogue promotion of runtime evidence; or
- candidate regeneration after failure.

If a failed candidate is materially reconfigured such that its physical candidate identity changes, that belongs to a new candidate/run or a new session/configuration boundary rather than silently reopening the failed condition in this model.

## Test expectations

Focused session tests cover at least:

- pending conditions exposed without mutating the hard evaluation;
- satisfied conditions retaining the current candidate;
- partial satisfaction leaving other original conditions pending;
- one failed condition rejecting only the current candidate;
- repeated failure advancing strictly through original ranking order;
- complete session-local exhaustion without rewriting the global run outcome;
- canonical resolution ordering independent of input list order;
- candidate-scoped condition identity preventing cross-candidate leakage;
- wrong-kind/unknown condition resolution failing closed;
- duplicate terminal resolution failing closed;
- lazy lower-ranked resolution failing closed;
- hard-blocked/contextually-infeasible candidates never entering session fallback;
- reach-unknown qualification remaining unchanged after successful condition resolution; and
- direct/deserialized session result self-consistency validation.

A separate golden session benchmark is not required at this stage. The implemented behavior is small, deterministic and more directly specified by focused executable tests.
