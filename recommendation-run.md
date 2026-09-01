# Recommendation Run Orchestration

## Purpose

This document defines the thin executable boundary introduced after candidate generation, hard evaluation, and deterministic ranking/selection were separated into reusable layers.

The orchestration layer exists to make one global recommendation run complete by construction:

```text
complete candidate generation
        ↓
evaluate every generated candidate
        ↓
rank/select that exact complete evaluated set
        ↓
return selected / no-suitable / no-generated outcome
```

It does not add recommendation semantics of its own.

## Layer ownership

### Candidate generation remains authoritative for alternatives

`generate_candidate_configurations()` owns physical candidate construction, identity, feature/endpoint/component binding, and the complete set of alternatives produced from the normalized run inputs.

The orchestration layer must not:

- construct additional candidates;
- remove generated alternatives before evaluation;
- rewrite candidate IDs;
- infer missing product/interface evidence; or
- turn an empty generated set into `no_suitable_recommendation`.

### Candidate evaluation remains authoritative for hard viability

`evaluate_candidate_configuration()` is invoked once for every generated candidate configuration.

The orchestration layer must not duplicate or reinterpret attachment eligibility, load capacity, product constraints, connection compatibility, policy, pending runtime verification, or pre-use-action semantics.

A candidate is viable exactly when the existing evaluator gives it a non-null recommendation state.

### Candidate selection remains authoritative for ranking and global exhaustion

`rank_and_select_candidates()` receives the exact generated list and the complete evaluation list produced during the run.

It remains responsible for:

- exact candidate/evaluation identity coverage;
- blocked-versus-viable partitioning;
- deterministic ranking among viable candidates;
- selecting rank 1;
- distinguishing `no_generated_candidates`; and
- concluding `no_suitable_recommendation` only for a non-empty, fully evaluated exhausted set.

The orchestration layer does not introduce a second ranking or outcome-state model.

## Executable boundary

The reusable entry point is:

```python
run_recommendation(
    tool,
    tethers,
    anchor_paths,
    *,
    tool_attachment_assemblies=None,
    product_runtime_state=None,
    connection_contexts=None,
    policy_contexts=None,
)
```

These inputs intentionally mirror the existing normalized generator boundary. PR #36 does not add a redundant `RecommendationRunInput` wrapper merely to restate the generator schema.

A future API/session layer may introduce its own serialized request model when it has additional responsibilities such as explicit work context, session identity, user-supplied observations, or catalogue resolution.

## Completeness invariant

The orchestration sequence is deliberately fixed:

```text
generated_candidates = generate_candidate_configurations(...)

evaluations = [
    evaluate_candidate_configuration(candidate.configuration)
    for candidate in generated_candidates
]

selection = rank_and_select_candidates(
    generated_candidates,
    evaluations,
)
```

The same complete `generated_candidates` list returned by the generator is retained, fully evaluated, and passed to selection.

This closes the standalone-selector limitation where an external caller could previously supply only a subset of the generator's output and still satisfy exact coverage for that subset.

The selector remains reusable on its own, but a system-level global recommendation outcome should normally come from the recommendation-run boundary when generation is part of the same decision.

## Result model

`RecommendationRunResult` retains:

```text
generated_candidates
    all physical alternatives produced by generation

evaluations
    one hard evaluation for every generated candidate

selection
    the existing CandidateSelectionResult
```

The result intentionally preserves the full stage outputs rather than returning only the selected candidate.

This supports later:

- explanation/audit;
- inspection of blocked alternatives;
- deterministic session fallback;
- tracing selected component, installation-feature, endpoint, anchor-path, and source-product provenance; and
- future contextual ranking without reconstructing candidate identity.

The authoritative global outcome remains `selection.state`; the orchestration layer does not duplicate `CandidateSelectionState` with another enum.

## Failure semantics

An unsuccessful orchestration stage is not a recommendation outcome.

If generation, candidate evaluation, or selection raises because its inputs/invariants are invalid, the exception propagates.

The orchestration layer must not catch such failures and translate them into:

```text
no_suitable_recommendation
```

That state has a narrower meaning:

```text
generation succeeded
AND generated set is non-empty
AND every generated candidate was evaluated
AND every generated candidate is blocked
```

Similarly, successful generation of no alternatives remains:

```text
no_generated_candidates
```

The run boundary does not infer why no candidates were generated.

## Provenance and identity

The run retains the original `GeneratedCandidate` objects throughout evaluation and selection.

Candidate identity is therefore not reconstructed from SKU pairs, product names, or the canonical candidate ID string. The selected and ranked candidates continue to carry their original:

- tool reference;
- tether reference;
- ToolAttachment assembly and installation feature where applicable;
- tool-side and anchor-side endpoint/target bindings;
- anchor path;
- component-instance references; and
- source-product references.

## Deliberate boundaries

PR #36 does not add:

- contextual snag/reach/environment ranking;
- capacity-headroom preferences;
- direct-versus-ToolAttachment preference;
- brand or SKU-pair rules;
- new compatibility/evidence semantics;
- runtime verification/action resolution;
- session fallback state;
- user-facing recommendation prose;
- catalogue/ingestion resolution; or
- persistence/retry machinery.

Those concerns should build on the complete run result rather than being folded into orchestration.

## Test expectations

Focused orchestration tests should cover at least:

- a complete multi-candidate run selecting the real viable alternative;
- a non-empty complete run where every candidate is blocked and global exhaustion is valid;
- empty generation remaining `no_generated_candidates`;
- every generated candidate being evaluated exactly once; and
- stage failure propagating instead of being converted into recommendation exhaustion.

The existing lower-layer tests remain responsible for detailed generation, hard-evaluation, compatibility, constraint, ranking, identity, and deterministic tie-breaking semantics.

A separate recommendation-run golden benchmark is not required for this slice. The current ingestion benchmark remains a supply-side catalogue/readiness benchmark, while the orchestration completeness invariant is more directly and reliably expressed by focused executable tests.

## Next architecture step

Once the complete recommendation-run boundary is trusted, the next highest-value recommendation capability is explicit contextual ranking.

That work should add normalized context/ranking facts and reusable preference rules while preserving:

- the evaluator as the sole hard-viability authority;
- the complete generated/evaluated run record;
- missing context as neutral rather than invented preference; and
- the existing deterministic baseline ordering as the fallback when contextual rules do not distinguish candidates.
