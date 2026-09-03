# Environmental Contextual Suitability

## Purpose

This document defines the first executable environmental-context slice for TetherLens.

The initial scope is deliberately narrow:

> **An explicit accepted manufacturer prohibition for a selected candidate component may establish that the otherwise hard-viable candidate is contextually infeasible for an explicitly stated work exposure.**

The model does not infer general environmental suitability from materials, product family, marketing labels, or absence of a prohibition.

## Layer ownership

Environmental exposure is work context. It is not an intrinsic hard candidate fact.

The existing layer boundaries remain:

```text
candidate generation
    -> retain normalized selected-component constraints
hard candidate evaluation
    -> evaluate intrinsic hard checks and pre-use obligations
    -> defer contextual constraints unchanged
candidate selection
    -> apply explicit work context
    -> retain contextual checks separately
```

`CandidateEvaluation` therefore remains the sole hard-viability result. A candidate excluded for the current environmental context retains its original non-null recommendation state.

## Normalized manufacturer primitive

The first supported environmental constraint is:

```text
constraint_key = prohibited_exposure
operator = prohibits
disposition = contextual
value = <exact normalized exposure code>
```

It must originate from an accepted/reconciled declared manufacturer constraint and retains:

- canonical `constraint_id`;
- `source_product_ref`;
- candidate-local `component_ref` after composition;
- exact normalized exposure code;
- source URLs; and
- the complete `ResolvedProductConstraint` primitive.

The normalization layer does not require current work context. It returns `deferred_context`, which means only that downstream context is required to decide whether this prohibition applies to the current task.

`deferred_context` is not a pass, failure, verification requirement, or pre-use action.

## Explicit work context

`CandidateRankingContext.environmental_exposures` is a deterministic list of exact normalized exposure codes.

Examples might eventually include codes such as:

```text
salt_spray
hydraulic_fluid
```

but a code must not receive broader semantics merely because its name sounds related to another exposure.

The current slice performs exact code equality only.

It does not implement:

- synonyms;
- chemical families;
- concentration ranges;
- temperature interaction;
- material inheritance;
- generic corrosion reasoning; or
- material-to-exposure compatibility inference.

Those require separate evidence-backed semantics before implementation.

## Context checks

Context evaluation is retained independently from the original hard evaluation.

The initial statuses are:

```text
established
infeasible
unknown
```

### Matching explicit prohibition

For one hard-viable candidate:

```text
IF work context contains exposure X
AND a selected candidate component retains an accepted prohibited_exposure = X
THEN candidate context status for X = infeasible
```

The contextual check retains the selected component, source product, manufacturer constraint identity, and source URLs.

The candidate moves to `contextually_infeasible_candidates` but its `CandidateEvaluation` is not modified.

### Missing or unrelated evidence

For one stated exposure:

```text
no matching accepted prohibition
    -> unknown
```

`unknown` remains selectable.

This deliberately means:

```text
no known prohibition != proven suitable
```

An unrelated prohibition also does not expand by analogy. For example, a prohibition for `salt_spray` does not establish anything about `hydraulic_fluid`.

## Candidate scoping and fail-closed provenance

Environmental constraints apply only to physical component instances in the generated candidate that actually carries them.

Selection validates that a deferred contextual constraint retains:

- a normalized contextual primitive;
- the same `constraint_id` as that primitive;
- a non-null candidate-local `component_ref`;
- a component that exists in the candidate's retained selection; and
- a `source_product_ref` matching that selected component.

Identity/provenance mismatches fail closed rather than allowing one product's prohibition to leak into another candidate.

## Relationship to required reach and snag risk

Environmental prohibition and required reach are contextual feasibility families.

A hard-viable candidate is contextually infeasible when any established contextual feasibility check is `infeasible`.

Required reach continues to use maximum/extended working length.

Environmental exposure uses only explicit accepted manufacturer `prohibited_exposure` constraints in this first slice.

Elevated snag risk remains a ranking preference among candidates that survive contextual feasibility. It does not trade against a proven environmental prohibition.

## Global exhaustion

Environmental context may contribute to selector-level `no_suitable_recommendation` only after the complete generated/evaluated set is supplied and no hard-viable candidate remains selectable.

Therefore:

```text
all hard-viable candidates carry matching accepted prohibitions
    -> environmental contextual exhaustion may be established
```

but:

```text
at least one hard-viable candidate has unknown environmental suitability
    -> candidate remains selectable
    -> environmental-only exhaustion is not established
```

This follows the same conservative principle already used for unknown required reach.

## Deliberate non-goals

This slice does not introduce:

- `suitable_for_environment` or `suitable_for_offshore` fields;
- generic chemical-resistance scores;
- material compatibility tables;
- a material hierarchy such as `polyester -> polymer`;
- weighted context scoring;
- preferences based on the number of environmental claims or sources;
- SKU-pair environmental rules;
- inferred capability from missing negative evidence; or
- session-local environmental observation semantics.

## Next expansion criterion

Environmental reasoning should expand only when real product evidence supports another reusable primitive that materially changes recommendations.

Likely candidates include explicit operating-temperature limits or explicit positive/negative chemical-resistance statements, but their semantics should be defined from representative manufacturer evidence before code is added.

Material-based reusable rules should wait until the project has enough evidence to justify the required material and exposure vocabularies without inventing unsupported inheritance.
