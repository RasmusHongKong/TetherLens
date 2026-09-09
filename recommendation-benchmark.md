# End-to-End Recommendation Benchmark

## Purpose

The recommendation benchmark is a small downstream contract over the existing recommendation stack. It complements, rather than replaces, the supply-side ingestion goldens.

The supply-side benchmark asks whether trustworthy recommendation-critical facts can be acquired and resolved. This benchmark asks whether already-accepted/resolved recommendation primitives preserve the intended semantics through the complete executable run:

```text
accepted / resolved recommendation facts
        ↓
candidate generation
        ↓
hard candidate evaluation
        ↓
contextual feasibility + deterministic ranking/selection
        ↓
selected / no-suitable / no-generated outcome
```

The benchmark must reuse `run_recommendation()` and the normal declaration/interface resolvers. It must not introduce a second candidate generator, evaluator, selector, scorer, compatibility path, or exhaustion model.

## Boundary

The benchmark starts at the accepted-claim / resolved-fact seam rather than live acquisition.

This is intentional:

- Batch 1 and Batch 2 remain responsible for acquisition, extraction and recommendation-data readiness;
- focused adapter/resolver tests remain responsible for evidence-polarity and extraction boundaries;
- the downstream benchmark consumes accepted claims or normalized runtime primitives and proves that those semantics survive recommendation composition;
- golden output is never fed back into runtime construction.

A benchmark failure therefore localizes a downstream semantic regression without duplicating the live ingestion benchmark.

A normalized runtime primitive may be supplied directly where the durable downstream semantic already exists but there is no production claim compiler for that exact selection class. Benchmark expansion must not create production rules solely to make a fixture convenient.

## Golden-data rule

`benchmarks/recommendation_e2e_golden.json` is an answer key only.

It may contain expected semantic outcomes such as:

- generated/evaluated counts;
- selector state;
- recommendation state;
- pending-condition counts;
- connection status and compatibility basis;
- attachment mode, eligibility proof semantics and selected feature characteristics;
- product-constraint key/status expectations associated with semantic scenario roles; and
- retained evidence issuer where provenance itself is part of the contract.

It must not contain runtime product configuration such as:

- SKU pairs;
- expected tool/tether/anchor/attachment product references;
- canonical candidate IDs; or
- product-specific compatibility lookup rules.

The executable fixtures are constructed independently of the golden. A dedicated regression recursively inspects the parsed answer key and rejects identity-shaped keys such as `*_id`, `*_ref`, and `*_sku` forms so runtime product/candidate identity cannot drift into the golden contract.

Semantic scenario-role labels such as `under_capacity` or `installation_surface_mismatch` are allowed because they describe the expected reason an alternative is blocked without identifying a real product or runtime candidate.

## Current scenarios

### Manufacturer-declared ranked selection

The first positive scenario uses generic normalized product identities plus accepted manufacturer declaration primitives for the existing Quick Clip -> D-ring anchor relationship.

Two structurally valid candidates are generated against the same direct tool ring and evidence-backed anchor D-ring:

1. a tool-side gated carabiner plus an anchor-side Quick Clip whose D-ring engagement is established by the reusable manufacturer declaration; and
2. a gated-carabiner control path whose tool-side and anchor-side connections both require the existing bounded runtime verification family.

Both candidates remain hard-viable and `recommended_with_constraints`.

The manufacturer-declared candidate must rank first because it has one pending physical verification rather than two. This exercises the existing lexicographic ranking rule; the benchmark does not prefer Quick Clip, NLG, a particular product family, direct attachment, or any SKU pair merely because those identities exist.

The selected anchor connection must retain:

```text
status = compatible
basis = manufacturer_declared
issuer = NLG
```

This proves the reusable declaration survives accepted-claim resolution, concrete context binding, candidate generation, hard evaluation, ranking and selection without a new Quick Clip evaluator or SKU-pair rule.

### Complete hard exhaustion

The first negative scenario produces exactly two structurally valid candidates:

- one fails an existing hard load-capacity check; and
- one has adequate capacity but an unevidenced tool-side connection that remains `unresolved`.

Both candidates must survive generation and both must be evaluated.

Only then may the complete run conclude:

```text
selection.state = no_suitable_recommendation
```

The golden therefore records non-empty generation, exact evaluation count, zero ranked selectable candidates and two blocked candidates. It associates `load_capacity / failed` with the semantic `under_capacity` role and `connection_compatibility / unresolved` with the `unresolved_tool_connection` role.

The executable fixture binds those roles to the two generic candidates locally and asserts that each candidate's complete blocking-status set is exactly the expected singleton. A flattened union of blockers across the candidate set is not sufficient.

This case must remain distinct from `no_generated_candidates`.

### ToolAttachment selected-feature binding

The ToolAttachment scenario crosses the attachment composition boundary without adding a new production eligibility or hard-constraint rule.

Accepted physical-interface claims resolve into two separate tool features:

```text
feature A: surface, surface_profile = flat, surface_condition.clean = true
feature B: surface, surface_profile = curved, surface_condition.clean = true
```

Both features intentionally satisfy one already-normalized generic eligibility primitive:

```text
bind surface = one ToolInterfaceFeature
where feature_kind = surface
```

The benchmark supplies this `AttachmentEligibility` directly at the normalized-runtime seam. `resolve_attachment_eligibility()` currently compiles the established `captive_feature_attachment` selection class only; the benchmark does not invent a production `surface_bonded_attachment` compiler merely to construct this scenario.

Accepted ToolAttachment claims independently resolve the existing installation constraints:

```text
installation_surface_profile requires flat
required_surface_condition requires clean
```

Accepted physical-interface claims also resolve the ToolAttachment-provided tether target:

```text
role = tool_attachment_tether_side
interface_type = ring
```

The tool has no direct tether interface. Candidate generation therefore emits two ToolAttachment paths from the same generic assembly/tether/anchor choices, one bound to each eligible surface feature. The selected installation feature is retained on `CandidatePathSelection`, and the same feature is passed to product-constraint evaluation.

The flat/clean candidate passes both installation constraints and remains selectable. The separately bound curved/clean candidate fails only the existing hard `installation_surface_profile` product constraint. Selection must therefore choose the one hard-viable ToolAttachment path.

The golden records only reusable semantics: two generated/evaluated paths, one viable and one blocked, ToolAttachment mode, the surface eligibility proof, selected flat-surface semantics, the set of tool-attachment/tether/anchor component roles without depending on their serialization order, and the `installation_surface_mismatch` blocker. Runtime feature/component/assembly/product/candidate identities remain fixture-local.

This scenario catches regressions where feature identity is lost between resolution and generation, eligibility and installation constraints are accidentally evaluated against different features, ToolAttachment component provenance is discarded, the provided tether interface is bypassed, or a hard installation failure leaks into ranking as a preference.

## Completeness and provenance invariants

The benchmark asserts that:

- generated candidate IDs are unique;
- evaluation IDs are unique;
- generated and evaluated ID sets match exactly;
- the three selection partitions cover the exact generated set;
- each partitioned `EvaluatedCandidate` retains the corresponding original `GeneratedCandidate` and `CandidateEvaluation`;
- ToolAttachment paths retain their selected installation feature, eligibility proof and selected component-role set; and
- selected output equals rank 1 of the complete ranked selectable list.

These assertions intentionally exercise the same completeness/provenance boundary used for ordinary recommendation runs rather than reconstructing candidate identity from product references.

## Deliberate non-goals

The current benchmark does not add:

- a live recommendation benchmark runner;
- recommendation benchmark artifact upload;
- a new surface-bonded production attachment-selection compiler;
- session-condition resolution/fallback goldens;
- contextual reach/environment/snag goldens;
- golden user-facing recommendation prose;
- brand preferences;
- product-pair compatibility;
- new connection families; or
- new hard/contextual constraints.

Those should be added only when a stable reusable semantic is valuable enough that focused unit coverage alone no longer provides a clear system-level contract.

## CI role

The recommendation golden is exercised by `tests/test_recommendation_benchmark.py`, so it runs inside the normal unit-test step of the existing `Ingestion live smoke` workflow.

A separate report-producing runner or uploaded recommendation artifact is unnecessary while the cohort remains this small. If the cohort grows into a broader benchmark with scenario-level scoring, a dedicated runner can be introduced later without changing the underlying recommendation semantics.

## Next extension

With direct manufacturer-declared selection, complete hard exhaustion, and ToolAttachment selected-feature composition now represented, further golden expansion should remain selective.

Session-condition fallback or contextual feasibility would be reasonable future benchmark seams only when a concrete regression risk justifies a system-level contract. The next implementation work need not add another golden merely to increase scenario count.
