# Candidate Ranking and Selection

## Purpose

This document defines the executable model for comparing already-generated, already-evaluated recommendation candidates.

It covers the boundary between:

- candidate generation in `candidate_generation.py`;
- hard candidate evaluation in `recommendation.py`; and
- deterministic baseline/contextual ranking and global selection in `candidate_selection.py`.

The selector is intentionally a thin layer. It does not create physical candidate paths, re-run compatibility reasoning, reinterpret hard constraints, invent missing evidence, or encode SKU-pair preferences.

## Layer ownership

### Candidate generation owns physical path identity and ranking facts

`GeneratedCandidate` retains the original `CandidatePathSelection`, evaluator-ready `CandidateConfiguration`, and `CandidateRankingFacts`.

Candidate identity includes the physical choices needed to distinguish one path from another, including where applicable:

- tool reference;
- ToolAttachment assembly reference;
- selected installation feature;
- tether reference;
- tool-side and anchor-side endpoint/target bindings;
- anchor path; and
- selected component instance references.

Ranking must preserve this object rather than reconstruct candidate provenance from product IDs or from the canonical `candidate_id` string.

`CandidateRankingFacts` contains normalized low-level facts that may affect suitability but are not hard candidate checks. The first implemented fact is:

```text
tether_min_length_mm
```

This is copied from `TetherOption.min_length_mm`, whose meaning matches the catalogue/schema primitive: minimum, retracted, or shortest working length where meaningful.

The existing `TetherOption.max_length_mm` continues to populate `CandidateConfiguration.tether_max_length_mm` for existing hard product/lanyard constraints. Maximum/extended reach must not be silently reinterpreted as free tether length for snag ranking.

### Candidate evaluation owns hard viability

`CandidateEvaluation` is the sole authority for whether one candidate may remain in consideration.

The ranking layer uses exactly:

```text
viable <=> CandidateEvaluation.recommendation_state is not None
```

A blocked candidate can never be rescued by a contextual preference, better ranking fact, fewer components, a preferred brand, a stronger-looking source count, or any other preference.

Conversely, `recommended_with_constraints` is still viable when all hard checks pass but a validated runtime verification or required pre-use action remains pending.

### Candidate selection owns ordering and global exhaustion over a complete evaluated set

`rank_and_select_candidates()` accepts generated candidates and their evaluations, plus optional `CandidateRankingContext`, validates exact identity coverage, partitions viable from blocked candidates, ranks the viable partition, and selects rank 1.

It may conclude global exhaustion only under the bounded conditions described below.

## Input completeness and identity

Before ranking, the selector requires:

- every generated candidate ID to be unique;
- every evaluation candidate ID to be unique; and
- the generated candidate ID set to exactly equal the evaluation candidate ID set.

Missing evaluations fail closed. Unexpected evaluations also fail closed.

The selector does not silently rank a partially evaluated subset.

`EvaluatedCandidate` additionally validates that its retained `GeneratedCandidate.configuration.candidate_id` exactly matches its `CandidateEvaluation.candidate_id`.

This pairing keeps physical selection/provenance and ranking facts attached to the evaluation throughout ranking.

## Baseline-quality order

Baseline quality is lexicographic, not a weighted score. Lower tuple values are preferred in this order:

1. recommendation state;
2. total pending pre-use conditions;
3. pending physical-verification count;
4. connection-evidence weakness; and
5. review signal.

These factors form the baseline-quality group. Context may reorder candidates only inside a complete tie on all five factors.

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

## First contextual family: elevated snag risk

`CandidateRankingContext` currently contains one optional contextual dimension:

```text
snag_risk = standard | elevated | absent
```

Only explicit `elevated` snag risk activates a contextual preference.

For one baseline-quality tie group:

```text
IF snag_risk = elevated
AND every candidate in the tied group has tether_min_length_mm
THEN prefer lower tether_min_length_mm
```

This implements the MVP principle of preferring reduced free tether length in congested/high-snag work without introducing an application-level `suitable_for_tight_spaces` flag.

The rule deliberately operates on minimum/retracted/shortest working length rather than maximum/extended length. This matters for elastic, coiled, and retractable products: a tether with long available reach may still keep routine slack controlled.

### Context cannot trade against baseline quality in this slice

The first contextual rule is deliberately bounded.

A shorter tether does **not** outrank a candidate merely because it is shorter if that would require accepting:

- a weaker recommendation state;
- more pending conditions;
- greater physical-verification dependence;
- weaker connection evidence; or
- a review signal that the competing candidate does not carry.

Those cross-dimension tradeoffs would require explicit semantics and evidence rather than an arbitrary weighted score.

### Missing context is neutral

If `ranking_context` is absent, baseline ordering is unchanged.

An explicit `snag_risk = standard` is also neutral in this slice; it does not create a preference for longer tethers.

### Missing ranking facts are neutral

If any candidate in a baseline-quality tie group lacks `tether_min_length_mm`, the snag rule does not reorder that group.

The selector must not treat unknown length as zero, infinity, or an implicit penalty. It falls back to the deterministic baseline order instead.

If all relevant lengths are known but equal, context likewise does not distinguish the candidates.

## Deterministic final tie-break

After baseline quality and any applicable contextual preference, a remaining tie is broken by canonical `candidate_id` lexical order.

Input list order is never a ranking signal.

This makes selection deterministic across equivalent caller ordering. It also preserves the PR #35 baseline ordering exactly when context is absent or neutral.

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

The selected candidate is rank 1 of the deterministic viable ordering after any applicable context preference.

### `no_suitable_recommendation`

Use only when:

- the supplied generated candidate set is non-empty;
- exact one-to-one evaluation coverage has been established; and
- every supplied candidate is blocked by the existing evaluator.

Context cannot create this state because contextual ranking never changes viability.

This remains the first layer allowed to widen individual candidate failure into a global recommendation outcome.

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

The contextual-ranking slice threads optional `CandidateRankingContext` through the same run boundary and retains it on `RecommendationRunResult`. It does not introduce a second orchestration or outcome model.

The selector remains reusable on its own, so callers that invoke it directly must still respect the narrower completeness guarantee above. System-level global exhaustion should normally come from the end-to-end recommendation-run boundary when generation is part of the same decision. See `recommendation-run.md` for the orchestration invariant and failure semantics.

## Deliberate non-preferences

The selector does not prefer candidates based on:

- brand or manufacturer;
- exact SKU pairing;
- direct attachment versus ToolAttachment path;
- fewer physical components;
- capacity headroom beyond passing the hard requirement;
- tether product family;
- shorter/longer maximum tether length by default;
- tether form by itself (`coiled`, `retractable`, etc.);
- installation method aesthetics; or
- catalogue source/provider identity.

Minimum working length affects ordering only through the explicit elevated-snag rule above.

Future preferences such as required reach or environmental suitability must be justified by explicit reusable context and candidate facts and must not silently become hard constraints.

## Session verification and fallback

The ranked viable list is intended to support later session behavior.

If the selected candidate carries pending runtime verification or pre-use actions, TetherLens should emit that candidate as a conditional recommendation before asking the worker to satisfy the condition.

If a required runtime verification later fails for the actual session/configuration, the candidate should be rejected for that session and the system should move deterministically to the next ranked viable alternative.

A successful runtime check is session/configuration evidence. It must not silently become a universal catalogue claim that two SKUs are compatible.

The session-state/fallback model is not implemented by the contextual selector itself.

## Test expectations

The ranking/selection layer should continue to have focused unit coverage for at least:

- blocked candidates never being ranked or selected;
- fully recommended candidates ranking ahead of conditional candidates;
- fewer pending conditions ranking ahead of greater burden;
- known pre-use action versus pending physical verification at equal burden;
- established connection evidence ranking ahead of runtime dependence;
- review signal acting only as a late baseline preference;
- absent/standard snag context preserving the baseline order;
- elevated snag risk preferring lower known minimum working length inside a complete baseline tie;
- missing minimum length making the contextual rule neutral for the tied group;
- equal minimum lengths falling through to canonical identity;
- context never overriding baseline-quality tiers or rescuing blocked candidates;
- input-order-independent deterministic contextual and non-contextual ties;
- original candidate selection/component provenance retention;
- exact evaluation coverage;
- duplicate identity rejection;
- empty generation remaining distinct from exhausted evaluated alternatives; and
- selected-result structural equality with the first ranked candidate.

The existing ingestion benchmark remains a supply-side catalogue/readiness benchmark. A separate ranking golden benchmark should only be introduced when TetherLens has several stable scenario/context families whose expected cross-candidate outcomes are no longer expressed cleanly by focused unit tests.
