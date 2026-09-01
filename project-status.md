# TetherLens Project Status

_Last updated: 2026-09-01_

This document is the short operational handoff for the current TetherLens ingestion, compatibility, candidate-composition, generation, selection, and recommendation-run work. It records what has landed, what remains intentionally unresolved, and which workstreams should be tackled next.

For durable design principles, use the dedicated documents such as `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `container-interface-topology.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`. This file should not replace those documents or freeze semantic decisions before the evidence has been inspected.

## Current development line

The current development line through PR #36 includes:

- PR #17 — Batch 2 blind NLG holdout and post-blind evaluation path;
- PR #18 — explicit tether endpoint topology;
- PR #19 — salvaged NLG catalogue discovery plus value-sensitive forbidden-claim scoring;
- PR #20 — reusable primitive ToolAttachment attachment-method semantics;
- PR #21 — ToolAttachment compatibility and installation constraints;
- PR #22 — NLG evidence-polarity and bond-time hardening;
- PR #23 — normalized tool-anatomy and attachment-selection semantics;
- PR #24 — executable feature-bound attachment eligibility core;
- PR #25 — accepted tool-feature resolution plus the first reusable captive-feature ToolAttachment vertical slice;
- PR #26 — comparison hardening and conservative dimensional evaluation;
- PR #27 — ToolAttachment-provided tether interfaces, resolved tether endpoints, and topology-aware endpoint engagement;
- PR #28 — explicit connection-compatibility bases and controlled runtime-verification design;
- PR #29 — executable compatibility-basis runtime model, connector-spec resolution, manufacturer-assessment precedence, and the first bounded gated-connector/closed-interface verification family;
- PR #30 — repeated container tether interfaces with explicit location, evidence-bound form, per-interface rating, and fail-closed cross-source reconciliation;
- PR #31 — reusable `CandidateConfiguration` / `CandidateEvaluation` composition across attachment eligibility, load capacity, lanyard limits, both required connection evaluations, policy applicability, and pending runtime verification;
- PR #32 — normalized product/installation constraints, hard-vs-pre-use action semantics, same-feature installation binding, constraint provenance retention, and product-namespaced constraint identifiers;
- PR #33 — reusable candidate generation for direct and ToolAttachment paths, retaining explicit endpoint/feature/component identity and producing evaluator-ready `CandidateConfiguration`s without ranking or global exhaustion;
- PR #34 — candidate-generation hardening: candidate-scoped policy context, load-bearing ToolAttachment assembly requirements, connector-spec identity validation, and collision-resistant canonical candidate IDs;
- PR #35 — deterministic candidate ranking and global selection over fully evaluated generated alternatives, with exact evaluation coverage, provenance retention, fail-closed viability separation, and a bounded `no_suitable_recommendation` conclusion; and
- PR #36 — thin end-to-end recommendation-run orchestration that owns complete generation, evaluates every generated candidate exactly once, passes that exact complete set to the existing selector, retains all stage outputs, and makes global exhaustion safe by construction.

PR #16, the earlier NLG catalogue-generalization branch, was closed unmerged after its useful catalogue-discovery and scorer changes were carried forward through PR #19. Its older endpoint and attachment-method semantics should not be revived.

## Important current capabilities

TetherLens can now:

- ingest manufacturer evidence into typed candidate claims with claim-level provenance;
- resolve tool operational mass from qualified manufacturer/cross-source evidence;
- resolve accepted tool anatomy into feature-local `ToolInterfaceFeature[]` with captive state, role, dimensions, and attributes;
- evaluate reusable ToolAttachment eligibility with OR between paths, AND within a path, and strict same-feature binding;
- resolve ToolAttachment-provided tether-side interfaces, tether endpoints, connector specifications, and repeated container tether interfaces;
- keep topology, geometry, connector operation, manufacturer position, runtime verification, policy, and installation constraints as separate reasoning axes;
- evaluate endpoint compatibility using explicit bases such as manufacturer declaration, validated geometry, validated interface class, or bounded runtime verification;
- preserve `compatible`, `incompatible`, `requires_verification`, and `unresolved` rather than forcing binary fit decisions;
- compose already-resolved primitives into one `CandidateEvaluation` without SKU-pair recommendation logic;
- distinguish hard candidate failure from validated pending pre-use verification/action obligations;
- resolve supported product constraints into normalized runtime form while leaving unsupported declared constraints outside the generic evaluator until their technical/manufacturer/policy meaning is explicit;
- bind feature-scoped installation constraints to the same eligible ToolAttachment feature used by the candidate;
- preserve primary/supporting manufacturer evidence URLs and source-product constraint identity through evaluation output;
- generate direct and ToolAttachment candidate paths from reusable facts rather than manually curated tool/tether pairs;
- preserve installation feature, tether endpoint side/role, selected component instance, source-product, anchor path, and attachment-assembly identity in each generated candidate;
- support multi-component ToolAttachment assemblies without assuming one ToolAttachment SKU always equals one complete physical assembly;
- evaluate every generated candidate independently, retaining blocked candidates for audit rather than allowing ranking to rescue them;
- rank viable candidates deterministically without a global weighted score or hidden SKU/brand preferences;
- prefer fully established recommendations over conditional ones, then lower pending-condition burden, lower physical-verification dependence, stronger connection evidence, and no review signal before using canonical candidate identity as the final tie-break;
- retain the original generated candidate object through ranking so provenance is not reconstructed from product IDs;
- distinguish an empty generated set from a fully evaluated non-empty set in which every candidate is blocked; and
- execute one complete recommendation run from normalized generation inputs through evaluation and deterministic selection while retaining the full generated set, evaluation set, and selection result.

## Candidate generation, evaluation, selection, and run state

The executable recommendation core is now split into four deliberately narrow layers.

### Candidate generation

`candidate_generation.py` constructs physical candidate paths and evaluator-ready configurations. It owns candidate identity and binding, but does not rank, select, or infer global exhaustion.

### Candidate evaluation

`recommendation.py` remains the sole hard-viability authority for one candidate. A candidate is viable for ranking only when `CandidateEvaluation.recommendation_state` is non-null. `recommended_with_constraints` remains viable when all hard checks pass but a validated runtime verification or pre-use action remains pending.

Ranking and orchestration must never reinterpret failed/unresolved checks, invent missing evidence, or rescue a blocked candidate.

### Candidate ranking and global selection

`candidate_selection.py` pairs each generated candidate with its evaluation, requires unique candidate IDs and exact generated/evaluated ID-set coverage, partitions blocked from viable candidates, ranks only viable alternatives, and selects rank 1.

The baseline ordering is deliberately lexicographic rather than weighted:

1. `recommended` before `recommended_with_constraints`;
2. fewer total pending verification/pre-use conditions;
3. for equal pending burden, fewer pending physical verifications;
4. catalogue-established connection bases before runtime-verification dependence, and runtime verification before no basis;
5. no review signal before `review_required`; and
6. canonical `candidate_id` as the deterministic final tie-break.

`manufacturer_declared`, `validated_geometry`, and `validated_interface_class` are intentionally not ordered against one another as stronger/weaker evidence. The current normalized evaluation output does not justify such a preference.

The selector does not prefer direct paths over ToolAttachment paths, one brand over another, fewer components, greater capacity headroom, shorter tethers, or specific product families. Those would require explicit reusable context/preference semantics rather than accidental ordering.

A selected result must contain the exact complete first ranked `EvaluatedCandidate`, not merely another object sharing its candidate ID.

### Recommendation-run orchestration

`recommendation_run.py` owns one complete generation -> evaluation -> selection execution.

It invokes the generator once, retains that full returned list, evaluates each generated `CandidateConfiguration` exactly once, and passes that exact generated list plus the complete evaluation list to `rank_and_select_candidates()`.

`RecommendationRunResult` retains:

- every `GeneratedCandidate`;
- every corresponding `CandidateEvaluation`; and
- the existing `CandidateSelectionResult`.

The run layer intentionally adds no second candidate model, hard-viability calculation, ranking algorithm, or outcome-state enum.

Failures from generation, evaluation, or selection propagate. An orchestration/invariant failure must not be converted into `no_suitable_recommendation`.

## Global `no suitable recommendation` boundary

A blocked candidate is not a global recommendation outcome.

The selector itself may return `no_suitable_recommendation` only when:

- the supplied generated candidate set is non-empty;
- every generated candidate has exactly one corresponding evaluation;
- no unexpected evaluation exists; and
- every candidate in that complete supplied set is blocked by the existing evaluator.

An empty generated set is represented separately as `no_generated_candidates` and must not be widened into a global no-suitable conclusion.

PR #36 closes the remaining system-level completeness caveat for normal end-to-end use. `run_recommendation()` owns the generator invocation and therefore passes the selector the generator's actual complete returned set rather than relying on an external caller to supply all alternatives.

The standalone selector remains reusable, so its narrower guarantee still matters when called directly: exact coverage proves completeness for the supplied set, not that an arbitrary caller supplied every alternative the generator could have produced.

## Compatibility and evidence principles currently in force

The major architecture remains:

**Every required connection needs an acceptable compatibility basis, but complete engineering geometry is not a universal catalogue-completeness requirement.**

Geometry is valuable where it establishes hard impossibility, provides a reusable validated rule, or materially simplifies a bounded field-verification procedure. A type-name pair such as `carabiner + ring` is not itself proof of compatibility.

Manufacturer scope, technical fit, installation requirements, site policy, recommendation ranking, and evidence confidence are not interchangeable. Category/application wording should not silently become a universal hard technical exclusion unless its semantics have been explicitly modeled that way.

Unknown form, ambiguous public evidence, source gaps, contradictory manufacturer evidence, and missing runtime facts should remain explicit rather than being converted into complete-looking recommendations.

## Latest benchmark state

The current ingestion/readiness benchmark state was established through PR #30 and revalidated through PR #35. PR #36 changes recommendation-run composition only and does not change ingestion/extraction behavior:

- Batch 1 live acquisition: **12/12 products**;
- Batch 1 extraction: **54 TP / 0 FP / 0 FN**;
- Batch 1 micro precision and recall: **1.0 / 1.0**;
- Batch 1 recommendation-data coverage: **27/29 requirements**, with the remaining two requirements recorded as existing `source_blocked` cases;
- fresh Batch 2 post-blind acquisition: **8/8 products**;
- fresh Batch 2 extraction: **87 TP / 0 FP / 0 FN**;
- fresh Batch 2 micro precision and recall: **1.0 / 1.0**;
- fresh Batch 2 recommendation-data coverage: **44/44 requirements**, **8/8 products complete**; and
- the immutable Batch 2 blind artifact remains unchanged as the historical pre-fix baseline.

The catalogue benchmark remains a supply-side ingestion/recommendation-readiness benchmark. PRs #33-#36 add runtime candidate construction/evaluation/selection/orchestration semantics and are covered primarily by focused unit tests; there is not yet a separate golden ranking or recommendation-run benchmark.

The four current Batch 2 evidence/semantic gaps remain:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |
| NLG 101520 | Ascent™ Pouch | `public_fact_not_established` | external daisy-chain presence is established, but public evidence does not establish an individual loop/site count |

These should remain explicit until acceptable evidence or a reusable semantic rule actually resolves them.

## Next workstreams

### 1. Explicit contextual ranking inputs and reusable preference rules

With the complete end-to-end recommendation-run boundary in place, the next highest-value recommendation slice is context-driven suitability without weakening hard viability.

The first slice should establish the smallest reusable context/ranking-fact model before adding many preferences. A likely initial family is snag risk / usable tether length because it is explicitly part of the MVP scenarios, but only if the required candidate fact can be represented cleanly and compared without inventing missing measurements.

Context rules must remain ranking preferences unless their semantics genuinely define a hard constraint. Missing context should not silently create a preference.

Contextual ordering should build on the complete run/evaluated candidate set and retain the current deterministic baseline ordering as a fallback when contextual rules do not distinguish candidates.

### 2. Session verification/action resolution and deterministic fallback

Once a selected candidate can be produced end to end, model what happens when its pending pre-use condition is resolved:

- verification/action passes -> retain the selected configuration with the condition satisfied for the current session/configuration;
- verification fails -> reject that candidate for the session and move deterministically to the next ranked viable alternative;
- runtime observations remain session/configuration evidence and do not become universal SKU-pair catalogue claims.

This should reuse the existing run result, ranking order, and candidate identity rather than regenerate an unrelated recommendation state.

### 3. Selective geometry and remaining evidence gaps

Continue geometry, measurement, document-join, and evidence work when it materially blocks recurring candidate paths or exposes a reusable evidence-model weakness.

Prioritize new measurements or vocabulary when:

- a connector specification is reused across many tether SKUs;
- one measurement resolves a high-frequency uncertainty;
- a hard geometric rule can conclusively reject unsafe engagement;
- a published dimension can replace recurring runtime verification with catalogue-established compatibility; or
- the fact materially strengthens a validated field-verification procedure.

Do not build a general CAD model and do not weaken evidence requirements merely to close a benchmark gap.

## Working principles for the next phase

- do not add SKU-specific extraction, compatibility, generation, ranking, orchestration, or recommendation branches to make one product pass;
- keep generation, hard evaluation, preference ranking, policy, orchestration, and session verification responsibilities explicit;
- do not add a second hard-viability calculation inside ranking or orchestration;
- use the recommendation-run boundary for system-level global exhaustion rather than passing hand-selected candidate subsets to the selector;
- do not infer candidate evidence strength from source-count or URL-count heuristics;
- preserve candidate identity and provenance through every downstream layer rather than reconstructing it;
- require complete candidate/evaluation coverage before a global exhaustion conclusion;
- distinguish `no_generated_candidates` from a fully evaluated non-empty exhausted set and from an orchestration failure;
- add contextual ranking only from explicit reusable context facts/rules;
- preserve manufacturer wording and provenance per claim and through downstream outputs;
- keep product identity separate from evidence provenance;
- require same-subject / same-feature binding where facts must belong to one physical feature;
- distinguish source absence, acquisition failure, parser failure, semantic-vocabulary gaps, evidence-scope tension, public ambiguity, true claim conflict, `requires_verification`, pending pre-use action, and genuinely unresolved compatibility;
- do not infer `compatible` from interface names alone;
- do not treat a successful session-level field verification as universal catalogue compatibility;
- let hard physical contradiction and authoritative manufacturer prohibition fail closed;
- let inconclusive geometry remain inconclusive;
- preserve explicit negative-use wording and do not invert it into capability;
- preserve the original Batch 2 blind artifact and cohort unchanged; and
- use fresh post-blind evaluation against that same cohort for regression checking.

## Suggested fresh-chat starting point

After PR #36, start with the **smallest explicit contextual ranking model**, not more orchestration plumbing.

A concise handoff prompt is:

> Continue TetherLens from merged `main` after PR #36. Inspect `recommendation_run.py`, `candidate_selection.py`, generated candidate facts, recommendation-engine/status docs, MVP scenario expectations, and current tests. Define the smallest reusable context/ranking-fact model that can change the ordering of already-viable candidates without weakening hard constraints or inventing missing measurements. Start with one high-value contextual family only if its facts are representable cleanly—likely snag risk / usable tether length—and preserve the existing deterministic baseline ordering when context is absent or does not distinguish candidates. Do not add session fallback, SKU-pair preferences, or new compatibility semantics in the same slice.
