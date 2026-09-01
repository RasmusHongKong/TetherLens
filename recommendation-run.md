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
        + optional explicit ranking context
        ↓
return selected / no-suitable / no-generated outcome
```

It does not add recommendation semantics of its own.

## Layer ownership

### Candidate generation remains authoritative for alternatives and ranking facts

`generate_candidate_configurations()` owns physical candidate construction, identity, feature/endpoint/component binding, ranking-only candidate facts, and the complete set of alternatives produced from the normalized run inputs.

The first ranking-only fact is the tether's minimum/retracted/shortest working length. It is retained on `GeneratedCandidate.ranking_facts` and is separate from `CandidateConfiguration.tether_max_length_mm`, which retains its existing hard-constraint meaning.

The orchestration layer must not:

- construct additional candidates;
- remove generated alternatives before evaluation;
- rewrite candidate IDs;
- infer missing product/interface/ranking facts; or
- turn an empty generated set into `no_suitable_recommendation`.

### Candidate evaluation remains authoritative for hard viability

`evaluate_candidate_configuration()` is invoked once for every generated candidate configuration.

The orchestration layer must not duplicate or reinterpret attachment eligibility, load capacity, product constraints, connection compatibility, policy, pending runtime verification, or pre-use-action semantics.

A candidate is viable exactly when the existing evaluator gives it a non-null recommendation state.

Ranking context is not passed into the hard evaluator in this slice.

### Candidate selection remains authoritative for ranking and global exhaustion

`rank_and_select_candidates()` receives the exact generated list and the complete evaluation list produced during the run, plus optional `CandidateRankingContext`.

It remains responsible for:

- exact candidate/evaluation identity coverage;
- blocked-versus-viable partitioning;
- baseline-quality ordering among viable candidates;
- applying explicit contextual preferences only where their required facts are available;
- deterministic final tie-breaking;
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
    ranking_context=None,
)
```

The first contextual model is deliberately small:

```python
CandidateRankingContext(
    snag_risk="standard" | "elevated" | None,
)
```

Only explicit elevated snag risk currently changes ordering, and only among candidates tied on all existing baseline-quality factors. See `candidate-ranking-selection.md` for the rule and missing-fact behavior.

The run boundary still mirrors the normalized generator boundary rather than adding a redundant `RecommendationRunInput` wrapper. A future API/session layer may introduce its own serialized request model when it has additional responsibilities such as session identity, user-supplied observations, or catalogue resolution.

## Completeness invariant

The orchestration sequence remains deliberately fixed:

```text
generated_candidates = generate_candidate_configurations(...)

evaluations = [
    evaluate_candidate_configuration(candidate.configuration)
    for candidate in generated_candidates
]

selection = rank_and_select_candidates(
    generated_candidates,
    evaluations,
    ranking_context=ranking_context,
)
```

The same complete `generated_candidates` list returned by the generator is retained, fully evaluated, and passed to selection. Context does not pre-filter alternatives before hard evaluation.

This preserves the PR #36 completeness guarantee: an external caller cannot obtain a system-level no-suitable conclusion by passing only a hand-selected subset through the normal run boundary.

The selector remains reusable on its own, but a system-level global recommendation outcome should normally come from the recommendation-run boundary when generation is part of the same decision.

## Result model

`RecommendationRunResult` retains:

```text
generated_candidates
    all physical alternatives produced by generation,
    including ranking-only candidate facts

evaluations
    one hard evaluation for every generated candidate

ranking_context
    the explicit context used to order viable candidates,
    or null when baseline ordering was used

selection
    the existing CandidateSelectionResult
```

The result intentionally preserves the full stage outputs rather than returning only the selected candidate.

This supports:

- explanation/audit of why ordering changed under explicit context;
- inspection of blocked alternatives;
- deterministic future session fallback;
- tracing selected component, installation-feature, endpoint, anchor-path, source-product, and ranking-fact provenance; and
- adding later context families without reconstructing candidate identity.

The authoritative global outcome remains `selection.state`; the orchestration layer does not duplicate `CandidateSelectionState` with another enum.

## Failure semantics

An unsuccessful orchestration stage is not a recommendation outcome.

If generation, candidate evaluation, or selection raises because its inputs/invariants are invalid, the exception propagates.

The orchestration layer must not catch such failures and translate them into:

```text
no_suitable_recommendation
```

That state retains its narrow meaning:

```text
generation succeeded
AND generated set is non-empty
AND every generated candidate was evaluated
AND every generated candidate is blocked
```

Context cannot create `no_suitable_recommendation` because contextual ranking never changes hard viability.

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
- component-instance references;
- source-product references; and
- explicit ranking facts such as minimum tether working length.

The ranking context itself is also retained on the run result rather than inferred later from the selected product.

## Deliberate boundaries

The current contextual-ranking slice does not add:

- required-reach ranking;
- environmental ranking;
- capacity-headroom preferences;
- direct-versus-ToolAttachment preference;
- tether-form preference by itself;
- brand or SKU-pair rules;
- new compatibility/evidence semantics;
- runtime verification/action resolution;
- session fallback state;
- user-facing recommendation prose;
- catalogue/ingestion resolution; or
- persistence/retry machinery.

Those concerns should build on the complete run result rather than being folded into orchestration.

## Test expectations

Focused orchestration/context tests should cover at least:

- a complete multi-candidate run selecting the real viable alternative;
- explicit elevated snag context changing the ordering of otherwise baseline-equivalent viable candidates when minimum working lengths are known;
- the run retaining the explicit ranking context used for selection;
- a non-empty complete run where every candidate is blocked and global exhaustion is valid;
- empty generation remaining `no_generated_candidates`;
- every generated candidate being evaluated exactly once; and
- stage failure propagating instead of being converted into recommendation exhaustion.

The lower-layer selector tests remain responsible for detailed baseline precedence, missing-context/fact neutrality, deterministic contextual ordering, hard-viability separation, identity, and exact coverage semantics.

A separate recommendation-run golden benchmark is not required for this slice. The current ingestion benchmark remains a supply-side catalogue/readiness benchmark, while the single contextual family is more directly and reliably expressed by focused executable tests.

## Next architecture step

After this first contextual family is trusted, the next context expansion should be justified by a distinct low-level fact and real scenario expectation rather than by adding a generic weighted score.

Required reach is the natural next candidate because the existing maximum/extended tether length is already the correct primitive for that question. It should remain separate from snag ranking, which deliberately uses minimum/retracted/shortest working length.

Session verification/action resolution and deterministic fallback also remain separate follow-on work and should reuse the ranked run result rather than changing catalogue compatibility semantics.
