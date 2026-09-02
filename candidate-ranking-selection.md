# Candidate Ranking and Selection

## Purpose

This document defines the executable model for comparing already-generated, already-evaluated recommendation candidates.

It covers the boundary between:

- candidate generation in `candidate_generation.py`;
- hard candidate evaluation in `recommendation.py`; and
- deterministic contextual feasibility, ranking, and global selection in `candidate_selection.py`.

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

Selection must preserve this object rather than reconstruct candidate provenance from product IDs or from the canonical `candidate_id` string.

`CandidateRankingFacts` contains normalized low-level facts used only for ranking. The currently implemented fact is:

```text
tether_min_length_mm
```

This is copied from `TetherOption.min_length_mm`, whose meaning matches the catalogue/schema primitive: minimum, retracted, or shortest working length where meaningful.

`TetherOption.max_length_mm` continues to populate `CandidateConfiguration.tether_max_length_mm`. Its meaning remains maximum, extended, or longest working length where meaningful. That value already participates in hard product/lanyard constraints and is also the correct primitive for explicit required-reach reasoning. It is deliberately not duplicated into `CandidateRankingFacts`.

Maximum/extended length must not be silently reinterpreted as free tether length for snag ranking.

### Candidate evaluation owns hard viability

`CandidateEvaluation` is the sole authority for intrinsic/hard viability of one candidate.

The selector uses exactly:

```text
hard_viable <=> CandidateEvaluation.recommendation_state is not None
```

A hard-blocked candidate can never be rescued by contextual suitability, better ranking facts, fewer components, a preferred brand, a stronger-looking source count, or any other preference.

Conversely, `recommended_with_constraints` is still hard-viable when all hard checks pass but a validated runtime verification or required pre-use action remains pending.

Task context is not passed back into `evaluate_candidate_configuration()` merely because it can make a hard-viable candidate unsuitable for one specific task.

### Candidate selection owns contextual feasibility, ordering, and global exhaustion

`rank_and_select_candidates()` accepts generated candidates and their evaluations plus optional `CandidateRankingContext`.

It:

1. validates exact generated/evaluated identity coverage;
2. separates evaluator-blocked candidates from hard-viable candidates;
3. applies explicit contextual feasibility rules to the hard-viable set;
4. ranks the remaining selectable candidates deterministically; and
5. selects rank 1 or concludes bounded exhaustion.

The first contextual feasibility family is explicit required reach. The first contextual preference family remains elevated snag risk.

## Input completeness and identity

Before selection, the selector requires:

- every generated candidate ID to be unique;
- every evaluation candidate ID to be unique; and
- the generated candidate ID set to exactly equal the evaluation candidate ID set.

Missing evaluations fail closed. Unexpected evaluations also fail closed.

The selector does not silently reason over a partially evaluated supplied set.

`EvaluatedCandidate` additionally validates that its retained `GeneratedCandidate.configuration.candidate_id` exactly matches its `CandidateEvaluation.candidate_id`.

This pairing keeps physical selection/provenance and contextual facts attached to the hard evaluation throughout downstream selection.

## Baseline-quality order

Baseline quality is lexicographic, not a weighted score. Lower tuple values are preferred in this order:

1. recommendation state;
2. total pending pre-use conditions;
3. pending physical-verification count;
4. connection-evidence weakness; and
5. review signal.

These factors remain unchanged by the required-reach slice.

### 1. Recommendation state

`recommended` ranks before `recommended_with_constraints`.

This is a preference among candidates that remain selectable after contextual feasibility is applied, not a new hard-viability test.

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

The selector treats catalogue-established bases as one tier:

```text
manufacturer_declared
validated_geometry
validated_interface_class
```

It does **not** claim that one of these is universally stronger than another.

`runtime_verification` is weaker for ranking because final fit depends on a session/configuration check.

`none` is weaker still. Under normal hard evaluation, a selectable connection should not depend on `none`; keeping it last is a conservative ordering rather than a new compatibility rule.

The selector does not use:

- number of supporting URLs;
- number of eligibility proofs;
- number of claims;
- source count; or
- arbitrary evidence-provider ordering

as evidence-strength proxies.

### 5. Review signal

When earlier baseline factors tie, a candidate without `review_required` ranks ahead of one carrying an internal review signal.

`review_required` is not itself a hard blocker in this layer. Any review condition that must block the candidate must already have been represented by the evaluator's hard result.

## Contextual preference: elevated snag risk

`CandidateRankingContext` contains the optional snag dimension:

```text
snag_risk = standard | elevated | absent
```

Only explicit `elevated` snag risk activates a snag preference.

For one baseline-quality tie group within the same required-reach knowledge tier:

```text
IF snag_risk = elevated
AND every candidate in the tied group has tether_min_length_mm
THEN prefer lower tether_min_length_mm
```

This implements the MVP principle of preferring reduced free tether length in congested/high-snag work without introducing an application-level `suitable_for_tight_spaces` flag.

The rule deliberately operates on minimum/retracted/shortest working length rather than maximum/extended length. This matters for elastic, coiled, and retractable products: a tether with long available reach may still keep routine slack controlled.

### Snag context cannot trade against baseline quality

A shorter tether does **not** outrank a candidate merely because it is shorter if that would require accepting:

- a weaker recommendation state;
- more pending conditions;
- greater physical-verification dependence;
- weaker connection evidence; or
- a review signal that the competing candidate does not carry.

Those cross-dimension tradeoffs would require explicit semantics and evidence rather than an arbitrary weighted score.

### Missing snag context or facts are neutral

If `ranking_context` is absent, baseline ordering is unchanged.

An explicit `snag_risk = standard` is also neutral; it does not create a preference for longer tethers.

If any candidate in one baseline-quality tie group lacks `tether_min_length_mm`, the snag rule does not reorder that group.

The selector must not treat unknown minimum length as zero, infinity, or an implicit penalty. If all relevant minimum lengths are known but equal, context likewise does not distinguish the candidates.

## Contextual feasibility: required reach

`CandidateRankingContext` also accepts:

```text
required_reach_mm
```

This means the task requires at least that much maximum working reach.

It is a task requirement, not a general preference for longer tethers.

The candidate fact is the existing:

```text
GeneratedCandidate.configuration.tether_max_length_mm
```

whose source primitive is `TetherOption.max_length_mm` = maximum / extended / longest working length where meaningful.

### Known inadequate reach is contextually infeasible

For a hard-viable candidate:

```text
IF required_reach_mm is stated
AND tether_max_length_mm is established
AND tether_max_length_mm < required_reach_mm
THEN the candidate is contextually infeasible for this task
```

The candidate remains hard-viable in its original `CandidateEvaluation`. It is not rewritten as a technical incompatibility, load failure, policy failure, or product-constraint failure.

It is retained in `contextually_infeasible_candidates` with its complete generated candidate and hard evaluation.

### Equality passes

A candidate whose maximum working length equals the stated requirement satisfies the reach threshold.

```text
tether_max_length_mm >= required_reach_mm
```

is established reach feasibility.

### Excess reach is not rewarded

Once a candidate satisfies the required minimum, additional maximum length creates no ranking advantage by itself.

For example, with `required_reach_mm = 1000`, candidates at 1000 mm and 2000 mm remain ordered by the normal baseline/context rules. The selector does not infer that 2000 mm is better merely because it is longer.

This avoids conflating reach feasibility with a generic long-tether preference.

### Missing maximum length remains unknown, not failed

If a candidate is hard-viable but `tether_max_length_mm` is absent, the required-reach rule cannot prove either adequate or inadequate reach.

The selector does not convert unknown into zero, infinity, pass, or fail.

Instead:

1. candidates with established adequate reach rank ahead of reach-unknown candidates; and
2. reach-unknown candidates remain deterministic fallbacks.

If every selectable candidate has unknown maximum length, their relative ordering is exactly the normal baseline plus applicable snag ordering.

A reach-unknown candidate therefore prevents the selector from claiming complete reach-based exhaustion. If selected as the best available fallback, downstream explanation must retain the fact that required reach was not established rather than claiming the threshold was proven.

### Required reach may outrank baseline quality because it is feasibility, not preference

An established-adequate candidate ranks ahead of a reach-unknown fallback even if the unknown candidate would otherwise have a better baseline-quality tuple.

That is intentionally different from snag ranking. Required reach represents whether the task requirement is established; snag risk remains a preference among otherwise comparable selectable candidates.

### Reach and snag remain separate dimensions

Required reach uses maximum/extended working length.

Elevated snag risk uses minimum/retracted/shortest working length.

For example, two candidates may both satisfy a 1500 mm reach requirement while one retracts to 300 mm and the other to 700 mm. Elevated snag risk may prefer the 300 mm candidate when the baseline factors tie, without treating either candidate's maximum length as a snag proxy.

## Deterministic final tie-break

Within the applicable reach-knowledge tier, after baseline quality and any applicable snag preference, a remaining tie is broken by canonical `candidate_id` lexical order.

Input list order is never a ranking signal.

Contextually infeasible candidates are also retained in deterministic canonical-ID order.

This preserves deterministic behavior across equivalent caller ordering.

## Result invariants

`CandidateSelectionResult` partitions the complete paired set into three mutually exclusive groups:

- `ranked_viable_candidates` — hard-viable candidates still selectable after contextual feasibility;
- `contextually_infeasible_candidates` — hard-viable candidates proven unable to satisfy an explicit contextual feasibility requirement; and
- `blocked_candidates` — candidates blocked by the existing hard evaluator.

IDs must remain unique inside every partition and no candidate may appear in more than one partition.

`contextually_infeasible_candidates` must remain hard-viable. A hard-blocked candidate is never relabelled as contextually infeasible merely because it also happens to be too short for the current reach requirement.

For `state = selected`:

- a selected candidate must exist;
- the selectable ranking must be non-empty;
- `selected` must itself be hard-viable; and
- `selected` must equal the complete first `EvaluatedCandidate` object in `ranked_viable_candidates`.

The last invariant is deliberately stronger than matching only `candidate_id`: a reconstructed object with the same ID but different evaluation/provenance must not contradict the ranked winner.

## Global outcome states

### `selected`

Use when at least one supplied candidate remains selectable after exact hard evaluation coverage and applicable contextual feasibility have been established.

The selected candidate is rank 1 of the deterministic selectable ordering.

### `no_suitable_recommendation`

Use only when:

- the supplied generated candidate set is non-empty;
- exact one-to-one evaluation coverage has been established; and
- no candidate remains selectable after hard evaluation and explicit contextual feasibility.

This may happen because:

- every generated candidate is blocked by the hard evaluator;
- every hard-viable candidate is proven contextually infeasible; or
- the complete set contains a mixture of those two cases.

A hard-viable candidate with unknown maximum reach is still selectable as an unknown fallback and therefore prevents a required-reach-only `no_suitable_recommendation` conclusion.

This is the first layer allowed to widen complete candidate exhaustion into a global recommendation outcome. The selector does not mutate the underlying hard evaluations to reach that conclusion.

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

`run_recommendation()` closes that caveat for normal end-to-end recommendation runs. The run boundary owns the generator invocation, evaluates every candidate in the generator's actual returned list exactly once, and passes that exact complete generated/evaluated set into the selector.

`RecommendationRunResult` validates complete coverage across all three selection partitions and retains the exact `CandidateRankingContext` used for the run.

The selector remains reusable on its own, so callers that invoke it directly must still respect the narrower completeness guarantee above. System-level global exhaustion should normally come from the end-to-end recommendation-run boundary when generation is part of the same decision.

## Deliberate non-preferences

The selector does not prefer candidates based on:

- brand or manufacturer;
- exact SKU pairing;
- direct attachment versus ToolAttachment path;
- fewer physical components;
- capacity headroom beyond passing the hard requirement;
- tether product family;
- longer maximum tether length beyond an explicit reach threshold;
- shorter maximum tether length as a snag proxy;
- tether form by itself (`coiled`, `retractable`, etc.);
- installation method aesthetics; or
- catalogue source/provider identity.

Minimum working length affects ordering only through the explicit elevated-snag rule.

Maximum working length affects selection only through existing hard product/lanyard constraints and the explicit required-reach feasibility rule.

Future contextual families such as environmental suitability must likewise be justified by explicit reusable context and candidate facts rather than hidden weighted scoring.

## Session verification and fallback

The ranked selectable list is intended to support later session behavior.

If the selected candidate carries pending runtime verification or pre-use actions, TetherLens should emit that candidate as a conditional recommendation before asking the worker to satisfy the condition.

If a required runtime verification later fails for the actual session/configuration, the candidate should be rejected for that session and the system should move deterministically to the next ranked selectable alternative.

A successful runtime check is session/configuration evidence. It must not silently become a universal catalogue claim that two SKUs are compatible.

Required-reach feasibility is separate from this later session verification/action-resolution model.

## Test expectations

The ranking/selection layer should continue to have focused unit coverage for at least:

- blocked candidates never being ranked or selected;
- fully recommended candidates ranking ahead of conditional candidates within one reach-knowledge tier;
- fewer pending conditions ranking ahead of greater burden;
- known pre-use action versus pending physical verification at equal burden;
- established connection evidence ranking ahead of runtime dependence;
- review signal acting only as a late baseline preference;
- absent/standard snag context preserving the baseline order;
- elevated snag risk preferring lower known minimum working length inside a complete baseline tie;
- missing minimum length making the snag rule neutral for the tied group;
- equal minimum lengths falling through to canonical identity;
- required reach accepting exact-threshold equality;
- known inadequate maximum reach producing contextual infeasibility without changing the hard evaluation;
- no preference for excess maximum reach after the threshold is met;
- known adequate reach ranking ahead of a reach-unknown fallback;
- all-unknown reach preserving the normal baseline/sn ag fallback ordering;
- reach-unknown fallback preventing a false reach-based exhaustion conclusion;
- complete known reach inadequacy producing bounded `no_suitable_recommendation`;
- hard-blocked and contextually infeasible candidates remaining separate;
- reach and snag using maximum and minimum lengths respectively;
- input-order-independent deterministic contextual and non-contextual ties;
- original candidate selection/component provenance retention;
- exact evaluation coverage;
- duplicate identity rejection;
- empty generation remaining distinct from exhausted evaluated alternatives; and
- selected-result structural equality with the first ranked candidate.

The existing ingestion benchmark remains a supply-side catalogue/readiness benchmark. A separate ranking golden benchmark should only be introduced when TetherLens has several stable scenario/context families whose expected cross-candidate outcomes are no longer expressed cleanly by focused unit tests.
