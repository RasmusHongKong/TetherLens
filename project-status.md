# TetherLens Project Status

_Last updated: 2026-09-02_

This document is the operational handoff for the current TetherLens ingestion, compatibility, candidate-composition, generation, evaluation, contextual selection, recommendation-run, and session-resolution work. It records the semantics that should be preserved and the highest-value next workstreams.

For durable design details, use the dedicated documents such as `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `container-interface-topology.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`.

For implemented downstream recommendation semantics, `candidate-ranking-selection.md`, `recommendation-run.md`, and `recommendation-session.md` are the authoritative design references.

## Current development line

The current development line through PR #39 includes:

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
- PR #37 — explicit contextual ranking inputs plus elevated-snag preference using lower known minimum/retracted tether length only inside complete baseline-quality ties;
- PR #38 — explicit required-reach contextual feasibility using maximum/extended tether length, separate contextual-infeasible provenance, deterministic unknown-reach fallback, bounded reach-driven global exhaustion, and run-result self-consistency validation; and
- PR #39 — session-local resolution of already-pending runtime verification/pre-use actions, candidate-scoped terminal outcomes, immutable run/evaluation preservation, deterministic fallback through the original ranked selectable list, and session-local exhaustion distinct from global selector exhaustion.

PR #16, the earlier NLG catalogue-generalization branch, was closed unmerged after its useful catalogue-discovery and scorer changes were carried forward through PR #19. Its older endpoint and attachment-method semantics should not be revived.

## Important current capabilities

TetherLens can now:

- ingest manufacturer evidence into typed candidate claims with claim-level provenance;
- resolve tool operational mass from qualified manufacturer/cross-source evidence;
- resolve accepted tool anatomy into feature-local `ToolInterfaceFeature[]` with captive state, role, dimensions, and attributes;
- evaluate reusable ToolAttachment eligibility with OR between paths, AND within a path, and strict same-feature binding;
- resolve ToolAttachment-provided tether-side interfaces, tether endpoints, connector specifications, and repeated container tether interfaces;
- keep topology, geometry, connector operation, manufacturer position, runtime verification, policy, installation constraints, contextual feasibility, ranking preferences, and session outcomes as separate reasoning axes;
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
- apply elevated snag context only among candidates tied on all baseline-quality factors within the same reach-knowledge tier;
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
- conclude selector-level `no_suitable_recommendation` only after the complete supplied set has no selectable candidate because of hard blocking and/or proven contextual infeasibility;
- execute one complete recommendation run from normalized generation inputs through evaluation and deterministic contextual selection while retaining the full generated set, evaluation set, ranking context, and exact selection result;
- create a session overlay only for a run that actually has a selected/ranked selectable stream;
- represent pending-condition identity as `(candidate_id, condition_kind, condition_id)` so local connection/constraint identifiers cannot leak across alternatives;
- record only terminal session outcomes (`satisfied` / `failed`), with absence meaning the original condition remains pending;
- retain the same active candidate when conditions are satisfied, without rewriting its original `CandidateEvaluation` or `RecommendationState`;
- reject only the affected candidate for the current session/configuration when any of its conditions fails;
- advance to the first unrejected candidate in the original `ranked_viable_candidates` order without regenerating, re-evaluating, or re-ranking survivors;
- prevent lower-ranked candidate conditions from being resolved before all higher-ranked alternatives before them have failed;
- preserve contextually infeasible and hard-blocked partitions outside session fallback; and
- represent complete runtime fallback failure as session-local `exhausted` while the immutable originating run may still retain `selection.state == selected`.

## Executable recommendation layers

The executable downstream core is now split into five deliberately narrow layers.

### 1. Candidate generation

`candidate_generation.py` constructs physical candidate paths and evaluator-ready configurations. It owns candidate identity and binding, but does not rank, select, or infer global exhaustion.

`TetherOption` carries:

```text
min_length_mm = minimum / retracted / shortest working length
max_length_mm = maximum / extended / longest working length
```

Generation copies `min_length_mm` into `CandidateRankingFacts.tether_min_length_mm` and `max_length_mm` into `CandidateConfiguration.tether_max_length_mm`.

Do not duplicate maximum length into ranking facts merely because required reach uses it.

### 2. Candidate evaluation

`recommendation.py` remains the sole hard-viability authority for one candidate:

```text
hard_viable <=> CandidateEvaluation.recommendation_state is not None
```

`recommended_with_constraints` remains hard-viable when all hard checks pass but a validated runtime verification or required pre-use action remains pending.

Context and later session outcomes do not mutate this hard evaluation.

### 3. Contextual feasibility, ranking, and global selection

`candidate_selection.py` requires unique candidate IDs plus exact generated/evaluated ID-set coverage.

Hard-blocked candidates are separated first. For explicit required reach, hard-viable candidates are classified as:

```text
known max < required reach  -> contextually infeasible
known max >= required reach -> reach established
max unknown                 -> reach unknown fallback
```

Known-inadequate candidates remain hard-viable in their retained `CandidateEvaluation`; they are not rewritten as technical failures.

Within one reach-knowledge tier, baseline quality remains lexicographic:

1. `recommended` before `recommended_with_constraints`;
2. fewer total pending verification/pre-use conditions;
3. for equal pending burden, fewer pending physical verifications;
4. catalogue-established connection bases before runtime-verification dependence, and runtime verification before no basis; and
5. no review signal before `review_required`.

Elevated snag risk operates only inside complete baseline ties when all relevant minimum-length facts are known.

The selector does not prefer direct paths, brands, fewer components, excess capacity headroom, tether family/form, or excess maximum reach beyond a stated requirement.

### 4. Recommendation-run orchestration

`recommendation_run.py` owns one complete generation -> evaluation -> selection execution.

It invokes the generator once, retains the complete returned list, evaluates each generated configuration exactly once, and passes that exact generated/evaluated set plus optional ranking context to the selector.

`RecommendationRunResult` retains all generated candidates, all hard evaluations, the ranking context, and the exact selection result.

Its validator enforces exact coverage and recomputes deterministic selection from the retained inputs/context so a manually constructed/deserialized run cannot carry stale or contradictory partitions/winners.

Failures from generation, evaluation, selection, or run-result invariants propagate and are not converted into recommendation exhaustion.

### 5. Session-local condition resolution and fallback

`recommendation_session.py` consumes an immutable `RecommendationRunResult` whose selector state is `selected`.

It never traverses `contextually_infeasible_candidates` or `blocked_candidates`; fallback uses only the original `ranked_viable_candidates` list.

Pending condition identity is candidate-scoped:

```text
(candidate_id, runtime_verification, connection_id)
(candidate_id, pre_use_action, constraint_id)
```

Terminal outcomes are:

```text
satisfied
failed
```

No stored session resolution means the original condition remains pending.

A failed condition rejects the candidate only for the current session/configuration. The next active candidate is the first unrejected item in the original ranking. Survivors are not re-ranked.

The original generated candidate, hard evaluation, ranking context, compatibility evidence, and selector result remain unchanged.

See `recommendation-session.md` for full invariants and deliberate boundaries.

## Exhaustion boundaries

Three distinct outcomes must remain separate.

### `no_generated_candidates`

Generation successfully produced no alternatives. The system does not infer why from this state alone.

### Selector-level `no_suitable_recommendation`

Use only when:

- the supplied generated set is non-empty;
- every generated candidate has exactly one corresponding evaluation;
- no unexpected evaluation exists; and
- no candidate remains selectable after hard evaluation plus explicit contextual feasibility.

A hard-viable candidate with unknown maximum reach remains selectable and therefore prevents a false required-reach-only exhaustion conclusion.

For normal end-to-end use, this global outcome should come from `run_recommendation()` so the selector receives the generator's actual complete returned set.

### Session-local `exhausted`

This is possible only after an originating run already had a selected/ranked selectable stream.

It means every candidate in that original ranked selectable list has subsequently acquired at least one failed session-local condition.

Therefore this is valid:

```text
RecommendationRunResult.selection.state == selected
RecommendationSessionResult.state == exhausted
```

Session exhaustion must not rewrite the original selector result as `no_suitable_recommendation`.

## Compatibility and evidence principles currently in force

The major architecture remains:

**Every required connection needs an acceptable compatibility basis, but complete engineering geometry is not a universal catalogue-completeness requirement.**

Geometry is valuable where it establishes hard impossibility, provides a reusable validated rule, or materially simplifies a bounded field-verification procedure. A type-name pair such as `carabiner + ring` is not itself proof of compatibility.

Manufacturer scope, technical fit, installation requirements, site policy, contextual feasibility, recommendation preference, runtime condition outcome, and evidence confidence are not interchangeable.

A successful session-level runtime verification remains evidence about the actual session/configuration. It must not silently become a universal catalogue claim or SKU-pair compatibility rule.

The generic session overlay consumes terminal condition outcomes; the family-specific connection/product evaluators remain responsible for deciding whether actual structured observations/facts constitute pending, satisfied/passed, or failed conditions.

## Latest benchmark state

PR #39 changes downstream session behavior only and does not change ingestion/extraction behavior. The PR workflow is green, including the full unit suite and live manufacturer benchmark.

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

The catalogue benchmark remains a supply-side ingestion/recommendation-readiness benchmark. Candidate generation/evaluation/selection/orchestration/context/session behavior is covered primarily by focused executable tests; there is not yet a separate golden ranking/session benchmark.

The four recorded Batch 2 evidence/semantic gaps remain:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |
| NLG 101520 | Ascent™ Pouch | `public_fact_not_established` | external daisy-chain presence is established, but public evidence does not establish an individual loop/site count |

These should remain explicit until acceptable evidence or a reusable semantic rule resolves them.

## Next workstreams

### 1. Family-specific runtime/action resolution adapters

The generic session overlay intentionally accepts only a terminal candidate-scoped condition resolution; it does not duplicate the rules that prove a physical verification or product action has actually passed/failed.

The cleanest next downstream slice is to connect existing structured primitive evaluators into that overlay so session results are produced from validated evidence rather than arbitrary UI assertions.

For runtime connection verification, preserve the existing family-specific structured observation model and derive pass/fail through `evaluate_endpoint_engagement()` / the relevant bounded rule. Do not add a generic `user_says_fit=true` shortcut.

For product pre-use actions, reuse normalized product-constraint semantics so conditions that merely remain incomplete (for example insufficient elapsed bond time) stay pending while genuinely failed procedures (for example a required attachment test returning false) reject the candidate.

The adapter must bind the produced resolution to the exact original `(candidate_id, condition_kind, condition_id)` and must not promote runtime observations into catalogue claims.

### 2. Environmental contextual suitability

Environmental exposure remains the next plausible context family only after low-level material/exposure semantics are explicit enough to distinguish:

- genuine contextual infeasibility;
- preference/caution; and
- unknown evidence.

Do not add generic `suitable_for_environment` flags or a weighted context score.

### 3. Selective geometry and remaining evidence gaps

Continue geometry, measurement, document-join, and evidence work when it materially blocks recurring candidate paths or exposes a reusable evidence-model weakness.

Prioritize new measurements/vocabulary when one primitive resolves a high-frequency uncertainty, establishes a reusable hard rule, or replaces recurring runtime verification with catalogue-established compatibility.

Do not build a general CAD model and do not weaken evidence requirements merely to close a benchmark gap.

## Working principles for the next phase

- do not add SKU-specific extraction, compatibility, generation, ranking, orchestration, session, or recommendation branches to make one product pass;
- keep generation, hard evaluation, contextual feasibility, preference ranking, policy, orchestration, primitive runtime evaluation, and session fallback responsibilities explicit;
- do not add a second hard-viability calculation inside selection, orchestration, or session logic;
- do not duplicate normalized candidate facts across ranking/context models when an existing primitive already has the correct meaning;
- use minimum/retracted length for snag preference and maximum/extended length for reach feasibility;
- keep missing context/facts explicit rather than inventing sentinel values, implicit penalties, passes, or failures;
- use the recommendation-run boundary for system-level global exhaustion rather than passing hand-selected candidate subsets to the selector;
- keep persisted/manually constructed run results self-consistent with retained inputs/context by reusing the selector as the source of truth;
- keep persisted/manually constructed session results self-consistent with the retained run and canonical candidate-scoped condition resolutions;
- preserve candidate identity and provenance through every downstream layer rather than reconstructing it;
- never let a session failure alter the original hard `CandidateEvaluation` or selector partitions;
- never re-rank survivors during session fallback; use the original ranked selectable order;
- do not resolve lower-ranked candidate conditions before higher-ranked alternatives have failed;
- distinguish `no_generated_candidates`, selector-level `no_suitable_recommendation`, orchestration failure, and session-local exhaustion;
- do not infer candidate evidence strength from source-count or URL-count heuristics;
- preserve manufacturer wording and provenance per claim and through downstream outputs;
- require same-subject / same-feature binding where facts must belong to one physical feature;
- distinguish source absence, acquisition failure, parser failure, semantic-vocabulary gaps, evidence-scope tension, public ambiguity, true claim conflict, `requires_verification`, pending pre-use action, contextual unknown, contextual infeasibility, failed session condition, and genuinely unresolved compatibility;
- do not infer `compatible` from interface names alone;
- do not treat a successful session-level field verification as universal catalogue compatibility;
- let hard physical contradiction and authoritative manufacturer prohibition fail closed;
- let inconclusive geometry remain inconclusive;
- preserve explicit negative-use wording and do not invert it into capability;
- preserve the original Batch 2 blind artifact and cohort unchanged; and
- use fresh post-blind evaluation against that same cohort for regression checking.

## Documentation note

Implemented contextual selection/run semantics are defined in `candidate-ranking-selection.md` and `recommendation-run.md`.

Implemented session-local condition/fallback semantics are defined in `recommendation-session.md`.

`recommendation-engine.md` and `mvp.md` still contain broader conceptual wording in places. Where that wording is less precise, it must not override the executable semantics above: hard evaluation remains immutable; explicit numeric required reach is contextual feasibility; reach unknown remains a qualified fallback; and runtime condition success/failure remains session/configuration evidence rather than universal catalogue compatibility.

## Suggested fresh-chat starting point

After PR #39 is merged, the recommended next slice is the family-specific bridge from validated runtime observations/actions into session resolutions.

A concise starting prompt is:

> Continue TetherLens from merged `main` after PR #39. Inspect `recommendation_session.py`, the existing gated-connector runtime-verification observations/evaluator, normalized product pre-use constraint runtime state, and the original candidate-scoped pending condition identifiers. Define the smallest evidence-backed adapter boundary that can derive `SessionConditionResolution` from validated connection observations or product-action facts without accepting generic user assertions, mutating the original `CandidateEvaluation`, or promoting session evidence into catalogue/SKU-pair compatibility. Preserve deterministic fallback through the original ranked selectable list.
