# TetherLens Project Status

_Last updated: 2026-09-04_

This document is the operational handoff for the current TetherLens ingestion, compatibility, candidate-generation/evaluation/selection, recommendation-run, session-resolution, and contextual reasoning stack. It records the semantics that should be preserved and the highest-value remaining workstreams.

For durable design details, use the dedicated documents including `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `connector-mechanism-semantics.md`, `connector-declared-compatibility.md`, `cinch-loop-semantics.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `container-interface-topology.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `environmental-context.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`.

## Current development line

The current development line through PR #44 includes:

- PR #17 — Batch 2 blind NLG holdout and post-blind evaluation path;
- PR #18 — explicit tether endpoint topology;
- PR #19 — salvaged NLG catalogue discovery plus value-sensitive forbidden-claim scoring;
- PR #20 — reusable primitive ToolAttachment attachment-method semantics;
- PR #21 — ToolAttachment compatibility and installation constraints;
- PR #22 — NLG evidence-polarity and bond-time hardening;
- PR #23 — normalized tool-anatomy and attachment-selection semantics;
- PR #24 — executable feature-bound attachment eligibility core;
- PR #25 — accepted tool-feature resolution plus the first reusable captive-feature ToolAttachment slice;
- PR #26 — comparison hardening and conservative dimensional evaluation;
- PR #27 — ToolAttachment-provided tether interfaces, resolved tether endpoints, and topology-aware endpoint engagement;
- PR #28 — explicit connection-compatibility bases and controlled runtime-verification design;
- PR #29 — executable compatibility-basis runtime model, connector-spec resolution, manufacturer-assessment precedence, and the first bounded gated-connector/closed-interface verification family;
- PR #30 — repeated container tether interfaces with explicit location, evidence-bound form, per-interface rating, and fail-closed cross-source reconciliation;
- PR #31 — reusable `CandidateConfiguration` / `CandidateEvaluation` composition;
- PR #32 — normalized product/installation constraints with hard/pre-use/contextual separation and provenance retention;
- PR #33 — reusable candidate generation for direct and ToolAttachment paths;
- PR #34 — candidate-generation hardening for policy scoping, assemblies, connector-spec identity, and canonical candidate IDs;
- PR #35 — deterministic candidate ranking and bounded global selection;
- PR #36 — end-to-end recommendation-run orchestration over the complete generated/evaluated set;
- PR #37 — explicit snag-risk contextual ranking using minimum/retracted tether length only inside baseline-quality ties;
- PR #38 — required-reach contextual feasibility using maximum/extended tether length;
- PR #39 — session-local pending-condition resolution and deterministic fallback;
- PR #40 — evidence-backed session adapters for bounded connection verification and normalized pre-use actions;
- PR #41 — explicit environmental contextual feasibility using accepted `prohibited_exposure` constraints;
- PR #42 — evidence-backed Quick Clip mechanism semantics, preserving `clip` while recording `opening_mechanism = trigger_operated` without gated-family promotion;
- PR #43 — evidence-backed cinch-loop mechanism and bounded `cinch_loop_to_closed_interface.v1` runtime verification; and
- PR #44 — reusable manufacturer-declared connector/interface compatibility claims and candidate-context binding, with the first bounded NLG Quick Clip -> D-ring anchor declaration.

PR #16 remains closed unmerged; its useful catalogue-discovery/scoring work was carried forward through PR #19 and its older topology semantics should not be revived.

## Current recommendation architecture

The executable downstream stack deliberately separates responsibilities.

### Candidate generation

`candidate_generation.py` constructs structurally admissible physical paths and evaluator-ready `CandidateConfiguration`s. It owns candidate identity and physical binding, but does not decide hard viability, ranking, contextual feasibility, or global exhaustion.

Endpoint assignment remains evidence-sensitive:

```text
TOOL_SIDE / EITHER   -> may serve tool side
ANCHOR_SIDE / EITHER -> may serve anchor side
UNKNOWN              -> not assigned
```

`TetherSide.UNKNOWN` must not be promoted to `either` from connector symmetry or missing contrary evidence.

### Hard candidate evaluation

`recommendation.py` remains the sole hard-viability authority for one candidate:

```text
hard_viable <=> CandidateEvaluation.recommendation_state is not None
```

Hard capacity, installation, interface compatibility, policy applicability and validated pending obligations remain distinct from ranking/context.

`compatible`, `incompatible`, `requires_verification`, and `unresolved` remain separate connection states. `unresolved` is blocking; `requires_verification` is conditional but usable only when a validated bounded verification family exists.

### Contextual feasibility and ranking

`candidate_selection.py` consumes the complete generated/evaluated set, separates hard-blocked candidates first, applies explicit contextual feasibility, then ranks retained selectable candidates deterministically.

Current contextual families are:

- required reach, using known maximum/extended tether length;
- explicit environmental exposure against accepted selected-component `prohibited_exposure` constraints; and
- elevated snag preference, using minimum/retracted tether length only inside complete baseline-quality ties.

Unknown reach/environment facts remain explicit fallback uncertainty rather than being rewritten as pass/fail values.

Ranking remains lexicographic rather than weighted. It does not prefer brands, direct paths, fewer components, tether form, excess capacity headroom, or excess maximum reach merely because those facts exist.

### Recommendation-run orchestration

`recommendation_run.py` owns complete generation -> evaluation -> selection execution. It evaluates every generated candidate exactly once and passes that exact set to selection.

Global selector exhaustion therefore remains safe only at the complete run boundary.

### Session-local condition resolution

`recommendation_session.py` and `recommendation_session_adapter.py` resolve already-pending runtime verifications/pre-use actions without regenerating, re-evaluating, or re-ranking survivors.

Session outcomes remain candidate/configuration evidence. They never become persistent catalogue compatibility claims.

## Current connection-compatibility families

### Gated connector -> closed interface

`gated_connector_to_closed_interface.v1` remains scoped to established `carabiner` / `snap_hook` endpoints with accepted opening-action evidence. Type names alone do not activate the family.

Gate-admission geometry may prove hard physical impossibility when accepted dimensions are available, but passing/incomplete geometry does not by itself establish complete safe engagement.

### Cinch loop -> bounded closed interface

PR #43 preserves `connection_point.interface_type = loop` and records `connector.attribute.engagement_method = cinch` only from locally bound first-party wording.

`cinch_loop_to_closed_interface.v1` is deliberately narrow:

- direct tool target: `captive_hole` or `closed_handle`;
- anchor/container target: `ring`;
- catalogue result: `requires_verification` until structured observations establish capture and a tightened cinch.

A plain loop remains unresolved. ToolAttachment-provided rings and other unevidenced closed forms remain outside v1.

### Quick Clip mechanism

PR #42 preserves Quick Clip as:

```text
connection_point.interface_type = clip
connector.attribute.opening_mechanism = trigger_operated
```

That does not establish action count, locking mode, gate geometry, connector-family equivalence, or gated-family eligibility.

### Manufacturer-declared Quick Clip -> D-ring anchor

PR #44 adds a separate manufacturer-declared compatibility path rather than widening Quick Clip mechanism semantics.

First-party NLG evidence for the Retractable Quick Clip Attachment (101456) establishes the bounded relationship:

```text
connector spec = quick_clip
source interface type = clip
target role = anchor_attachment_tether_side
target interface type = ring
target ring_form = d_ring
issuer = NLG
```

The new `connection_compatibility` claim subject retains the declaration primitives and source provenance. `resolve_connector_interface_compatibility_declarations()` resolves them into reusable declarations, and `connection_contexts_from_compatibility_declarations()` binds them to concrete endpoint/target pairs only when the primitives match.

The resulting candidate context reuses the existing `ConnectionManufacturerAssessment(position = explicitly_compatible)` and normal `manufacturer_declared` precedence path. No new Quick Clip hard evaluator is introduced.

Important boundaries:

- generic `ring` is not D-ring evidence;
- `similar anchor point` is not normalized;
- ToolAttachment D-rings are outside the v1 declaration scope;
- Quick Clip remains outside `gated_connector_to_closed_interface.v1`;
- the declaration does not infer closure, locking, action count or geometry; and
- the declaration does not resolve tether endpoint direction/interchangeability.

See `connector-declared-compatibility.md` for the exact claim/binding model.

## Manufacturer-declared compatibility model

A `ConnectorInterfaceCompatibilityDeclaration` contains reusable interface facts rather than product pairs:

- declaration identity;
- connector-spec reference;
- source interface type;
- target interface type;
- target structural role;
- required target attributes;
- issuer manufacturer;
- scope; and
- source URLs.

Runtime product identity appears only in the derived `ConnectionEvaluationContext` key needed to prevent evidence leakage between concrete candidates:

```text
(tether_ref, target_owner_ref, endpoint_id, target_interface_id)
```

Those IDs scope the evaluation; they are not the persisted compatibility rule.

The ordinary connection evaluator remains authoritative for side semantics, technical prohibitions, manufacturer/source conflicts, hard physical contradictions and precedence.

## Provenance principles currently in force

- manufacturer wording and URLs stay attached to atomic claims;
- accepted declared compatibility retains issuer and scope;
- candidate generation retains selected component, feature, endpoint, target and owner identity;
- ranking retains the original `GeneratedCandidate` and `CandidateEvaluation` rather than reconstructing provenance from IDs;
- runtime verification remains session/configuration evidence;
- a successful field check never becomes universal SKU-pair compatibility; and
- source-count/URL-count heuristics are not evidence-strength scores.

## Exhaustion boundaries

Three outcomes remain distinct.

### `no_generated_candidates`

Generation successfully produced no structural alternatives. The system does not infer the cause from this state alone.

### Selector-level `no_suitable_recommendation`

Use only when the complete non-empty generated set has exact evaluation coverage and no candidate remains selectable after hard evaluation plus explicit contextual feasibility.

Unknown reach/environment facts remain selectable fallback uncertainty and therefore prevent false context-only exhaustion.

### Session-local `exhausted`

Possible only after an originating run already had a selected/ranked selectable stream. It means every candidate in that original stream later failed at least one session-local condition.

It must not rewrite the original global selector result.

## Benchmark state

The supply-side ingestion/readiness benchmark remains healthy after PRs #42 and #43:

- Batch 1 live acquisition: **12/12 products**;
- Batch 1 extraction: **54 TP / 0 FP / 0 FN**;
- Batch 1 micro precision/recall: **1.0 / 1.0**;
- Batch 1 recommendation-data coverage: **27/29 requirements**, with the two remaining requirements classified as existing `source_blocked` cases;
- fresh Batch 2 post-blind acquisition: **8/8 products**;
- fresh Batch 2 extraction: **87 TP / 0 FP / 0 FN**;
- fresh Batch 2 micro precision/recall: **1.0 / 1.0**;
- fresh Batch 2 recommendation-data coverage: **44/44 requirements**, **8/8 products complete**; and
- the immutable Batch 2 blind artifact remains unchanged as the historical pre-fix baseline.

PR #44 introduces focused executable coverage for product 101456 evidence but does not add that product to the existing Batch 1/Batch 2 goldens. The current supply-side goldens therefore do not change merely to exercise the new declaration model.

The catalogue benchmark remains primarily a supply-side ingestion/recommendation-readiness benchmark. Candidate generation/evaluation/selection/session/context behavior is still covered mainly by focused executable tests; there is not yet a separate end-to-end golden recommendation benchmark.

## Recorded evidence/semantic gaps

The existing Batch 2 evidence gaps remain explicit:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |
| NLG 101520 | Ascent™ Pouch | `public_fact_not_established` | external daisy-chain presence is established, but an individual loop/site count is not publicly established |

A separate downstream semantic gap now remains especially important: some symmetric tethers have two physically similar endpoints but no accepted evidence assigning `tool_side`, `anchor_side`, or `either`. That gap must not be hidden by treating symmetry as interchangeability.

## Next highest-value workstreams

### 1. Evidence-backed symmetric tether endpoint assignment

This is now the clearest reusable downstream gap.

Current candidate generation correctly excludes `TetherSide.UNKNOWN`; two identical connector forms/specs do not prove a non-directional tether. The next slice should inspect representative first-party instructions/datasheets for products such as dual-Quick-Clip and dual-carabiner tethers and determine whether manufacturers explicitly establish endpoint interchangeability, reversibility, or non-directional use.

If supported, introduce a separate product/endpoint-assignment primitive rather than rewriting missing `connection_point.role` claims to `either`.

The implementation should:

- keep endpoint physical facts unchanged;
- preserve declaration provenance;
- derive allowed endpoint assignments from explicit interchangeability evidence;
- generate both orientations only when that evidence permits them;
- keep candidate IDs/provenance deterministic; and
- leave ambiguous products fail-closed.

### 2. Target-interface form enrichment where it unlocks recurring paths

PR #44 requires an explicit target `ring_form = d_ring` before the Quick Clip declaration can bind. Existing generic `ring` evidence must not be silently upgraded.

Future ingestion work should add D-ring form claims only where first-party wording/geometry is directly bound to the concrete target interface. Prioritize this when it unlocks recurring real anchor paths rather than adding broad taxonomy for its own sake.

### 3. End-to-end recommendation benchmark coverage

The current supply-side goldens can mark a product recommendation-data complete even when downstream role/assignment semantics still prevent candidate generation.

A future benchmark layer should therefore exercise a small representative set from accepted claims/resolved facts through candidate generation, hard evaluation and selection. It should remain separate from the immutable Batch 2 blind artifact and should avoid golden SKU-pair recommendations.

### 4. Selective geometry/evidence work

Continue geometry, measurements and document-join work only when one primitive closes a recurring uncertainty, proves a reusable hard rule, or materially reduces runtime verification burden.

Do not build a general CAD model.

## Working principles for the next phase

- no SKU-specific extraction, compatibility, generation, ranking, session or recommendation branches;
- no inferred compatibility from interface names alone;
- no promotion of `UNKNOWN` endpoint role to `EITHER` without explicit evidence;
- keep manufacturer scope, technical fit, installation constraints, policy, context, ranking and session outcomes separate;
- hard candidate viability remains owned exclusively by `CandidateEvaluation`;
- contextual feasibility/ranking must never rescue a hard-blocked candidate;
- preserve candidate identity and provenance through every downstream layer;
- fail closed on identity/feature/component/endpoint binding ambiguity;
- hard physical contradiction and authoritative source conflict remain blocking;
- inconclusive geometry remains inconclusive;
- successful runtime verification remains session/configuration evidence only;
- generic absence of environmental/geometry/role evidence must not become suitability;
- do not infer evidence strength from source count;
- use the complete recommendation-run boundary for global exhaustion;
- preserve the immutable Batch 2 blind artifact and use fresh post-blind evaluation for regression checking; and
- prefer small reusable evidence primitives over broad vocabularies introduced without a concrete decision need.

## Suggested fresh-chat starting point after PR #44

> Continue TetherLens from merged `main` after PR #44. Inspect current endpoint-role extraction/resolution, `_endpoint_assignments()`, representative symmetric tether evidence for dual Quick Clip / dual carabiner products, and downstream candidate-identity expectations. Determine whether manufacturer evidence supports a reusable interchangeability/non-directionality primitive that permits symmetric endpoint assignment without rewriting unknown endpoint roles, inventing evidence, or introducing SKU-pair logic. Recommend the smallest evidence-backed slice before changing code.
