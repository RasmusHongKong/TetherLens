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
structured candidate-local observation/fact
        ↓
existing primitive evaluator derives pending/pass/fail
        ↓
terminal pass/fail only -> candidate-scoped SessionConditionResolution
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

The generic session entry point is:

```python
resolve_recommendation_session(
    recommendation_run,
    resolutions=None,
)
```

Evidence-backed terminal resolutions for the currently supported primitive families are derived through:

```python
derive_connection_session_resolution(
    session,
    *,
    candidate_id,
    condition_id,
    observations,
)

derive_product_action_session_resolution(
    session,
    *,
    candidate_id,
    condition_id,
    runtime_state,
)
```

Neither adapter accepts an `outcome` argument. Incomplete primitive evidence returns no terminal resolution, leaving the original condition pending.

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

The session result reports condition state only. It does not make a broader readiness claim because other retained qualifications can remain unresolved even when no session condition is pending.

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

The evidence-backed adapters tighten this further: they target only the current active candidate and one condition still present in `active_pending_conditions`. Lower-ranked candidates, already-resolved conditions, wrong-kind identifiers, and rejected candidates therefore fail closed before primitive evaluation.

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

The result deliberately does **not** expose a generic `ready_for_use` flag.

A candidate can have no remaining pending session conditions while still carrying a retained contextual or evidence qualification. The clearest example is a required-reach fallback whose maximum working length remains unknown. Presentation/readiness decisions must therefore combine the session condition state with the unchanged originating run rather than infer readiness from `active_pending_conditions == []` alone.

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

## Primitive evaluators remain authoritative

Connection and product-constraint modules own family-specific semantics such as:

- which structured gated-connector observations produce pending/passed/failed verification;
- whether a bond-time requirement remains an action;
- whether a required pre-use attachment test passes or fails.

The session adapters do not duplicate those rules.

For the current bounded connection family, `ConnectionEvaluation` retains the exact `ConnectorSpec` required by the primitive verification rule. `evaluate_gated_connector_closed_interface_verification()` derives the runtime status from `GatedConnectorClosedInterfaceVerification`; the adapter maps only terminal `PASSED` / `FAILED` to `satisfied` / `failed`. `PENDING` produces no `SessionConditionResolution`.

For normalized product actions, `ProductConstraintEvaluation` retains the exact `ResolvedProductConstraint` that produced the original result. The adapter rebuilds only the runtime `ProductConstraintContext` from `ProductConstraintRuntimeState` and invokes `evaluate_product_constraints()` for that one original pre-use obligation. `REQUIRES_ACTION` remains pending, `PASSED` becomes satisfied, `FAILED` becomes failed, and `UNRESOLVED` fails closed rather than inventing a terminal outcome.

Component and installation-feature identity remain candidate-local. ToolAttachment runtime facts must use the exact selected component instance and the candidate's exact installation feature; tether/anchor-side component facts must not borrow that feature binding.

The generic fallback layer remains ignorant of connector geometry, adhesive semantics, manufacturer SKU pairs, and individual constraint keys.

A `SessionConditionResolution` is therefore a terminal internal result, not a substitute for the family-specific evidence/procedure that establishes that result. User-facing input must not be wired directly to `outcome="satisfied"` or `outcome="failed"`.

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

Evidence-backed adapters additionally reject:

- evidence for a candidate other than the active candidate;
- evidence for a condition that is no longer pending;
- pending connection conditions that do not retain the supported verification family/basis/specification;
- inconsistent pending-ID to primitive-result coverage;
- product actions missing their retained normalized constraint or physical component binding;
- component/source-product mismatches; and
- ToolAttachment runtime facts with a different installation-feature binding.

A directly constructed/deserialized `RecommendationSessionResult` also recomputes its deterministic projection from the retained run and resolutions and must match that projection exactly.

This prevents persisted session objects from silently replacing the active candidate, losing rejected-candidate provenance, or misreporting condition state.

## Deliberate boundaries

This slice does not add:

- session persistence storage;
- timestamps or event sourcing;
- retry/reopen semantics after a failed condition;
- automatic mapping for primitive families beyond the currently implemented gated-connector verification and normalized product pre-use obligations;
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
- reach-unknown qualification remaining unchanged after successful condition resolution;
- direct/deserialized session result self-consistency validation;
- incomplete bounded connection observations producing no terminal resolution;
- primitive connection pass/fail mapping without changing the original hard evaluation;
- unknown connector locking mode retaining the lock-observation requirement;
- insufficient bond time remaining pending until the normalized constraint passes;
- required attachment-test failure producing a candidate-local failed condition; and
- candidate/component/installation-feature identity mismatches failing closed.

A separate golden session benchmark is not required at this stage. The implemented behavior is small, deterministic and more directly specified by focused executable tests.