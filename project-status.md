# TetherLens Project Status

_Last updated: 2026-09-02_

This document is the short operational handoff for the current TetherLens ingestion, compatibility, candidate-composition, generation, evaluation, contextual selection, and recommendation-run work. It records what has landed or is under active review, the semantics that should be preserved, and the highest-value next workstreams.

For durable design details, use the dedicated documents such as `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `container-interface-topology.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`.

For implemented candidate-selection semantics, `candidate-ranking-selection.md` and `recommendation-run.md` are the authoritative design references.

## Current development line

The current development line through PR #38 includes:

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
- PR #35 — deterministic candidate ranking and global selection over fully evaluated generated alternatives, with exact evaluation coverage, provenance retention, hard-viability separation, and bounded global exhaustion;
- PR #36 — thin end-to-end recommendation-run orchestration that owns complete generation, evaluates every generated candidate exactly once, passes that exact complete set to the selector, retains all stage outputs, and makes system-level exhaustion safe by construction;
- PR #37 — explicit contextual ranking inputs plus the first reusable preference family: elevated snag risk may prefer lower known minimum/retracted tether length only inside complete baseline-quality ties, with missing context/facts remaining neutral; and
- PR #38 — explicit required-reach contextual feasibility using the existing maximum/extended tether-length primitive, separate contextual-infeasible provenance, deterministic unknown-reach fallback, bounded reach-driven global exhaustion, and run-result self-consistency validation against the retained inputs/context.

PR #16, the earlier NLG catalogue-generalization branch, was closed unmerged after its useful catalogue-discovery and scorer changes were carried forward through PR #19. Its older endpoint and attachment-method semantics should not be revived.

## Important current capabilities

TetherLens can now:

- ingest manufacturer evidence into typed candidate claims with claim-level provenance;
- resolve tool operational mass from qualified manufacturer/cross-source evidence;
- resolve accepted tool anatomy into feature-local `ToolInterfaceFeature[]` with captive state, role, dimensions, and attributes;
- evaluate reusable ToolAttachment eligibility with OR between paths, AND within a path, and strict same-feature binding;
- resolve ToolAttachment-provided tether-side interfaces, tether endpoints, connector specifications, and repeated container tether interfaces;
- keep topology, geometry, connector operation, manufacturer position, runtime verification, policy, installation constraints, contextual feasibility, and contextual preferences as separate reasoning axes;
- evaluate endpoint compatibility using explicit bases such as manufacturer declaration, validated geometry, validated interface class, or bounded runtime verification;
- preserve `compatible`, `incompatible`, `requires_verification`, and `unresolved` rather than forcing binary fit decisions;
- compose already-resolved primitives into one `CandidateEvaluation` without SKU-pair recommendation logic;
- distinguish hard candidate failure from validated pending pre-use verification/action obligations;
- resolve supported product constraints into normalized runtime form while leaving unsupported declared constraints outside the generic evaluator until their meaning is explicit;
- bind feature-scoped installation constraints to the same eligible ToolAttachment feature used by the candidate;
- preserve primary/supporting manufacturer evidence URLs and source-product constraint identity through evaluation output;
- generate direct and ToolAttachment candidate paths from reusable facts rather than manually curated tool/tether pairs;
- preserve installation feature, tether endpoint side/role, selected component instance, source-product, anchor path, and attachment-assembly identity in each generated candidate;
- support multi-component ToolAttachment assemblies without assuming one ToolAttachment SKU always equals one complete physical assembly;
- carry minimum/retracted/shortest tether working length as `CandidateRankingFacts.tether_min_length_mm` for snag ranking only;
- preserve maximum/extended/longest tether working length as `CandidateConfiguration.tether_max_length_mm` for existing hard product/lanyard constraints and explicit required-reach reasoning;
- evaluate every generated candidate independently, retaining hard-blocked candidates for audit rather than allowing selection to rescue them;
- rank selectable candidates deterministically without a global weighted score or hidden SKU/brand preferences;
- prefer fully established recommendations over conditional ones, then lower pending-condition burden, lower physical-verification dependence, stronger connection evidence, and no review signal;
- apply elevated snag context only among candidates tied on all existing baseline-quality factors within the same reach-knowledge tier;
- treat explicit `required_reach_mm` as contextual feasibility rather than a hard technical evaluator check;
- exclude a hard-viable candidate from the selectable stream only when its known `tether_max_length_mm` is below the stated required reach;
- treat `tether_max_length_mm == required_reach_mm` as satisfying the reach requirement;
- avoid rewarding excess maximum reach after the threshold is met;
- rank known reach-satisfying candidates ahead of reach-unknown fallback candidates when a required reach is stated;
- keep reach-unknown candidates selectable rather than inventing a pass/fail value, preventing false reach-based exhaustion;
- keep minimum/retracted length for snag preference separate from maximum/extended length for reach feasibility;
- use canonical `candidate_id` as the deterministic final tie-break within the applicable ranking tier;
- retain original generated/evaluated objects through all selection partitions so provenance is not reconstructed from product IDs;
- distinguish `ranked_viable_candidates`, `contextually_infeasible_candidates`, and hard `blocked_candidates`;
- distinguish an empty generated set from a fully evaluated non-empty exhausted set;
- conclude `no_suitable_recommendation` only after the complete supplied set has no selectable candidate because of hard blocking and/or proven contextual infeasibility; and
- execute one complete recommendation run from normalized generation inputs through evaluation and deterministic contextual selection while retaining the full generated set, evaluation set, ranking context, and exact selection result.

## Candidate generation, evaluation, selection, and run state

The executable recommendation core remains split into four deliberately narrow layers.

### Candidate generation

`candidate_generation.py` constructs physical candidate paths and evaluator-ready configurations. It owns candidate identity and binding, but does not rank, select, or infer global exhaustion.

`TetherOption` carries:

```text
min_length_mm = minimum / retracted / shortest working length
max_length_mm = maximum / extended / longest working length
```

with `min_length_mm <= max_length_mm` when both are known.

Generation copies `min_length_mm` into `CandidateRankingFacts.tether_min_length_mm`. It continues to copy `max_length_mm` into `CandidateConfiguration.tether_max_length_mm`.

Do not duplicate maximum length into ranking facts merely because required reach now uses it. One normalized primitive should remain the source of truth.

### Candidate evaluation

`recommendation.py` remains the sole hard-viability authority for one candidate.

```text
hard_viable <=> CandidateEvaluation.recommendation_state is not None
```

`recommended_with_constraints` remains hard-viable when all hard checks pass but a validated runtime verification or required pre-use action remains pending.

`CandidateRankingContext` is not passed to the hard evaluator. A candidate may therefore remain technically/hard viable while being unsuitable for one stated task context.

Selection/orchestration must never reinterpret failed/unresolved hard checks, invent missing evidence, or rescue a hard-blocked candidate.

### Candidate contextual feasibility, ranking, and global selection

`candidate_selection.py` pairs each generated candidate with its evaluation and requires unique candidate IDs plus exact generated/evaluated ID-set coverage.

Hard-blocked candidates are separated first.

For explicit required reach, hard-viable candidates are classified as:

```text
known max < required reach  -> contextually infeasible
known max >= required reach -> reach established
max unknown                 -> reach unknown fallback
```

Known-inadequate candidates remain hard-viable in their retained `CandidateEvaluation`; they are not rewritten as technical failures.

Known reach-satisfying candidates rank before reach-unknown fallbacks. If all selectable candidates have unknown maximum reach, their relative order remains the existing deterministic baseline plus applicable snag preference.

Within one reach-knowledge tier, baseline quality remains lexicographic:

1. `recommended` before `recommended_with_constraints`;
2. fewer total pending verification/pre-use conditions;
3. for equal pending burden, fewer pending physical verifications;
4. catalogue-established connection bases before runtime-verification dependence, and runtime verification before no basis; and
5. no review signal before `review_required`.

`manufacturer_declared`, `validated_geometry`, and `validated_interface_class` remain intentionally unordered against one another as stronger/weaker evidence.

Elevated snag risk acts only inside complete ties on the baseline-quality factors, and only when every candidate in the tied group has `tether_min_length_mm`:

```text
IF snag_risk = elevated
AND candidates tie on baseline quality
AND every candidate has tether_min_length_mm
THEN lower tether_min_length_mm ranks first
ELSE preserve deterministic baseline ordering
```

Required reach may outrank baseline quality because it represents whether an explicit task requirement is established. Snag risk remains a preference and cannot trade a small minimum-length advantage against stronger baseline quality.

The selector still does not prefer direct paths over ToolAttachment paths, one brand over another, fewer components, greater capacity headroom, product family, tether form by itself, or excess maximum reach beyond a stated threshold.

### Recommendation-run orchestration

`recommendation_run.py` owns one complete generation -> evaluation -> selection execution.

It invokes the generator once, retains that full returned list, evaluates each generated `CandidateConfiguration` exactly once, and passes that exact generated list plus the complete evaluation list and optional `CandidateRankingContext` to `rank_and_select_candidates()`.

`RecommendationRunResult` retains:

- every `GeneratedCandidate`;
- every corresponding `CandidateEvaluation`;
- the explicit `ranking_context` used for the run, or `None`; and
- the `CandidateSelectionResult`.

The result validator requires exact generated/evaluation coverage and exact coverage across all three selection partitions. It also recomputes the expected deterministic selection through `rank_and_select_candidates()` using the retained generated candidates, evaluations, and context, and rejects a manually constructed/deserialized result whose retained selection disagrees with those inputs.

This keeps selection semantics in one place and prevents persisted run results from carrying stale or contradictory reach partitions/winners.

The run layer adds no second hard-viability calculation, contextual rule implementation, or outcome-state enum.

Failures from generation, evaluation, selection, or result invariants propagate. An orchestration/invariant failure must not be converted into `no_suitable_recommendation`.

## Global `no suitable recommendation` boundary

A blocked or contextually infeasible candidate is not by itself a global recommendation outcome.

The selector may return `no_suitable_recommendation` only when:

- the supplied generated candidate set is non-empty;
- every generated candidate has exactly one corresponding evaluation;
- no unexpected evaluation exists; and
- no candidate remains selectable after hard evaluation plus explicit contextual feasibility.

A complete set may therefore be exhausted by:

- hard evaluator blocking alone;
- proven contextual infeasibility alone; or
- a mixture of both.

A hard-viable candidate with unknown maximum reach remains selectable as an unknown fallback and therefore prevents a required-reach-only global exhaustion conclusion.

An empty generated set remains `no_generated_candidates`.

For normal end-to-end use, `run_recommendation()` owns the generator invocation and therefore supplies the selector with the generator's actual complete returned set. The standalone selector remains reusable, but its exact-coverage guarantee applies only to the set a caller supplied.

## Compatibility and evidence principles currently in force

The major architecture remains:

**Every required connection needs an acceptable compatibility basis, but complete engineering geometry is not a universal catalogue-completeness requirement.**

Geometry is valuable where it establishes hard impossibility, provides a reusable validated rule, or materially simplifies a bounded field-verification procedure. A type-name pair such as `carabiner + ring` is not itself proof of compatibility.

Manufacturer scope, technical fit, installation requirements, site policy, contextual feasibility, recommendation preference, and evidence confidence are not interchangeable.

Unknown form, ambiguous public evidence, source gaps, contradictory manufacturer evidence, missing runtime facts, and missing contextual facts should remain explicit rather than being converted into complete-looking recommendations.

## Latest benchmark state

PR #38 changes contextual selection/orchestration only and does not change ingestion/extraction behavior. The full PR workflow, including unit tests and the live manufacturer benchmark, is green.

Current ingestion/readiness benchmark state remains:

- Batch 1 live acquisition: **12/12 products**;
- Batch 1 extraction: **54 TP / 0 FP / 0 FN**;
- Batch 1 micro precision and recall: **1.0 / 1.0**;
- Batch 1 recommendation-data coverage: **27/29 requirements**, with the remaining two requirements recorded as existing `source_blocked` cases;
- fresh Batch 2 post-blind acquisition: **8/8 products**;
- fresh Batch 2 extraction: **87 TP / 0 FP / 0 FN**;
- fresh Batch 2 micro precision and recall: **1.0 / 1.0**;
- fresh Batch 2 recommendation-data coverage: **44/44 requirements**, **8/8 products complete**; and
- the immutable Batch 2 blind artifact remains unchanged as the historical pre-fix baseline.

The catalogue benchmark remains a supply-side ingestion/recommendation-readiness benchmark. Candidate generation/evaluation/selection/orchestration/context behavior remains covered primarily by focused executable tests; there is not yet a separate golden ranking/recommendation-run benchmark.

The four recorded Batch 2 evidence/semantic gaps remain:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |
| NLG 101520 | Ascent™ Pouch | `public_fact_not_established` | external daisy-chain presence is established, but public evidence does not establish an individual loop/site count |

These should remain explicit until acceptable evidence or a reusable semantic rule resolves them.

## Next workstreams

### 1. Session verification/action resolution and deterministic fallback

This is now the cleanest next recommendation-engine slice.

Model what happens after the selected candidate carries one or more pending runtime verification/pre-use-action conditions:

- condition passes -> retain the selected configuration with that condition satisfied for the current session/configuration;
- condition fails -> reject that candidate for the session and move deterministically to the next ranked selectable alternative;
- a reach-unknown selected fallback should likewise retain its unresolved contextual qualification rather than being rewritten as proven adequate;
- runtime observations remain session/configuration evidence and do not become universal SKU-pair catalogue claims.

This work should reuse the existing complete `RecommendationRunResult`, ranking order, three selection partitions, pending condition identifiers, and candidate identity rather than regenerate unrelated recommendation state.

The main design question is how to represent session-local candidate disposition and condition resolution without mutating catalogue evidence or the original hard `CandidateEvaluation`.

### 2. Environmental contextual suitability

If continuing context instead of session state, environmental exposure is the next plausible family only after the required low-level material/exposure semantics are explicit enough to distinguish:

- genuine contextual infeasibility;
- preference/caution; and
- unknown evidence.

Do not add generic `suitable_for_environment` flags or a weighted context score.

### 3. Selective geometry and remaining evidence gaps

Continue geometry, measurement, document-join, and evidence work when it materially blocks recurring candidate paths or exposes a reusable evidence-model weakness.

Prioritize new measurements/vocabulary when one primitive resolves a high-frequency uncertainty, establishes a reusable hard rule, or replaces recurring runtime verification with catalogue-established compatibility.

Do not build a general CAD model and do not weaken evidence requirements merely to close a benchmark gap.

## Working principles for the next phase

- do not add SKU-specific extraction, compatibility, generation, ranking, orchestration, or recommendation branches to make one product pass;
- keep generation, hard evaluation, contextual feasibility, preference ranking, policy, orchestration, and session verification responsibilities explicit;
- do not add a second hard-viability calculation inside selection or orchestration;
- do not duplicate normalized candidate facts across ranking/context models when an existing primitive already has the correct meaning;
- use minimum/retracted length for snag preference and maximum/extended length for reach feasibility;
- treat explicit stated requirements differently from soft preferences only when the semantics justify that distinction;
- keep missing context/facts explicit rather than inventing sentinel values, implicit penalties, passes, or failures;
- use the recommendation-run boundary for system-level global exhaustion rather than passing hand-selected candidate subsets to the selector;
- keep persisted/manually constructed run results self-consistent with their retained inputs/context by reusing the selector as the source of truth;
- do not infer candidate evidence strength from source-count or URL-count heuristics;
- preserve candidate identity and provenance through every downstream layer rather than reconstructing it;
- require complete candidate/evaluation coverage before a global exhaustion conclusion;
- distinguish `no_generated_candidates` from a fully evaluated non-empty exhausted set and from an orchestration failure;
- preserve manufacturer wording and provenance per claim and through downstream outputs;
- require same-subject / same-feature binding where facts must belong to one physical feature;
- distinguish source absence, acquisition failure, parser failure, semantic-vocabulary gaps, evidence-scope tension, public ambiguity, true claim conflict, `requires_verification`, pending pre-use action, contextual unknown, contextual infeasibility, and genuinely unresolved compatibility;
- do not infer `compatible` from interface names alone;
- do not treat a successful session-level field verification as universal catalogue compatibility;
- let hard physical contradiction and authoritative manufacturer prohibition fail closed;
- let inconclusive geometry remain inconclusive;
- preserve explicit negative-use wording and do not invert it into capability;
- preserve the original Batch 2 blind artifact and cohort unchanged; and
- use fresh post-blind evaluation against that same cohort for regression checking.

## Documentation note

The implemented required-reach semantics are fully defined in `candidate-ranking-selection.md` and `recommendation-run.md`.

`recommendation-engine.md` and `mvp.md` still contain broader pre-implementation wording around reach/context and should be aligned in a later conceptual documentation cleanup. That wording must not be used to override the executable PR #38 semantics: an explicit numeric minimum required reach is contextual feasibility; a known-too-short candidate is not merely ranked lower, while an unknown maximum reach remains a qualified fallback rather than an invented failure.

## Suggested fresh-chat starting point

After PR #38 is merged, the recommended next slice is session verification/action resolution and deterministic fallback.

A concise starting prompt is:

> Continue TetherLens from merged `main` after PR #38. Inspect the complete `RecommendationRunResult`, ranked selectable candidates, contextual-infeasible and hard-blocked partitions, pending runtime verification/pre-use-action identifiers, and current recommendation-state/session expectations. Define the smallest reusable session-local condition-resolution and deterministic fallback model. Preserve the original hard `CandidateEvaluation`, candidate identity/provenance, and catalogue evidence; a failed runtime condition should reject only that candidate for the current session/configuration and advance to the next ranked selectable alternative without inventing SKU-pair compatibility or regenerating the candidate set.
