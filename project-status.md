# TetherLens Project Status

_Last updated: 2026-09-09_

This document is the operational handoff for the current TetherLens ingestion, compatibility, candidate-generation/evaluation/selection, recommendation-run, session-resolution, contextual reasoning, and recommendation-benchmark stack. It records the semantics that should be preserved and the highest-value remaining workstreams.

For durable design details, use the dedicated documents including `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `connector-mechanism-semantics.md`, `connector-declared-compatibility.md`, `anchor-interface-form.md`, `endpoint-assignment-semantics.md`, `cinch-loop-semantics.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `container-interface-topology.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `environmental-context.md`, `recommendation-benchmark.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`.

## Current development line

The current development line through PR #50 includes:

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
- PR #43 — evidence-backed cinch-loop mechanism and bounded `cinch_loop_to_closed_interface.v1` runtime verification;
- PR #44 — reusable manufacturer-declared connector/interface compatibility claims and candidate-context binding, with the first bounded NLG Quick Clip -> D-ring anchor declaration;
- PR #45 — evidence-backed reversible tether endpoint assignment using a separate tether-owned relation, preserving `TetherSide.UNKNOWN`, candidate identity and declaration provenance without inferring direction from symmetric hardware;
- PR #46 — explicit endpoint-assignment basis provenance plus the first bounded production `derived_endpoint_equivalence` extraction for an NLG dual-Quick-Clip tether when first-party endpoint-construction equivalence and undifferentiated tool-to-anchor use are both established;
- PR #47 — evidence-backed singular anchor-side D-ring form extraction for NLG AnchorAttachments, using `interface.attribute.ring_form = d_ring` on a concrete `anchor_attachment_tether_side` interface so the existing PR #44 Quick Clip declaration can bind without generic-ring promotion, geometry inference or SKU-pair logic;
- PR #48 — the first semantic end-to-end recommendation golden, exercising accepted/resolved evidence through complete recommendation-run selection for a manufacturer-declared connection path and a non-empty globally exhausted path without golden SKU-pair or candidate-ID expectations;
- PR #49 — ToolAttachment-mediated recommendation golden coverage, exercising accepted/resolved tool features, explicit selected-feature eligibility binding, normalized installation constraints, a ToolAttachment-provided tether interface, complete generation/hard evaluation and selection without production rule changes or golden product identity; and
- PR #50 — evidence-backed ToolAttachment target-form enrichment, preserving `ring_form = d_ring` on an already-concrete `tool_attachment_tether_side` ring when the accepted local interface evidence itself identifies a D-ring, while keeping generic rings generic and leaving compatibility/hard constraints unchanged.

PR #16 remains closed unmerged; its useful catalogue-discovery/scoring work was carried forward through PR #19 and its older topology semantics should not be revived.

## Current recommendation architecture

The executable downstream stack deliberately separates responsibilities.

### Candidate generation

`candidate_generation.py` constructs structurally admissible physical paths and evaluator-ready `CandidateConfiguration`s. It owns candidate identity and physical binding, but does not decide hard viability, ranking, contextual feasibility, or global exhaustion.

Endpoint assignment remains evidence-sensitive:

```text
TOOL_SIDE / EITHER   -> may serve tool side
ANCHOR_SIDE / EITHER -> may serve anchor side
UNKNOWN              -> not assigned from endpoint role alone
```

`TetherSide.UNKNOWN` must not be promoted to `either` from connector symmetry or missing contrary evidence.

PR #45 adds a separate assignment relation for the bounded case where accepted evidence establishes that exactly two named tether endpoints form a reversible tool/anchor pair. A valid `reversible_tool_anchor_pair` declaration may authorize both physical orientations only when both covered endpoints still have `TetherSide.UNKNOWN`.

PR #46 makes the provenance basis explicit:

```text
manufacturer_declared
derived_endpoint_equivalence
```

`manufacturer_declared` means the manufacturer directly establishes reversibility/interchangeability. `derived_endpoint_equivalence` means TetherLens derives the same bounded assignment relation from a conjunction of accepted first-party facts. The first production derivation is deliberately limited to the NLG Quick Clip evidence pattern where the same named Quick Clip construction is affirmatively established at each/both end, tool-to-anchor tether use is established, both endpoint roles remain unknown, and no directional/mixed-connector evidence exists.

The derived route does **not** make any single weak clue sufficient. `dual` / `double` / `twin` naming, shared normalized `ConnectorSpec`, connectors at both ends, one-to-tool/one-to-anchor wording, or absence of directional wording remain insufficient by themselves.

The relation does not mutate either endpoint role, does not override fixed or partially known role evidence, and does not establish connector/interface compatibility. Assignment declarations are tether-owned so repeated local endpoint IDs cannot leak authorization across products. Generated candidates retain declaration basis and provenance separately from canonical candidate identity; rehydration requires the retained selection proofs to match the operative declarations exactly.

Endpoint assignment is a **configuration-validity constraint rather than a product-ranking attribute**. For product selection, one manufacturer-permitted orientation that produces a viable tool-side connection and a viable anchor-side connection is sufficient. A reversible pair does not make a tether preferable merely because both orientations are allowed. Reversible orientations remain separate internally through endpoint-to-target evaluation and provenance checks, but equivalent orientations should not surface as duplicate user-facing product recommendations solely because the physical ends can be swapped.

See `endpoint-assignment-semantics.md` for the full v1 evidence threshold, production rule, selection significance and evidence findings.

### Hard candidate evaluation

`recommendation.py` remains the sole hard-viability authority for one candidate:

```text
hard_viable <=> CandidateEvaluation.recommendation_state is not None
```

Hard capacity, installation, interface compatibility, policy applicability and validated pending obligations remain distinct from ranking/context.

`compatible`, `incompatible`, `requires_verification`, and `unresolved` remain separate connection states. `unresolved` is blocking; `requires_verification` is conditional but usable only when a validated bounded verification family exists.

Endpoint-assignment evidence is structural authorization only. A relation-backed orientation may still be `compatible`, `incompatible`, `requires_verification`, or `unresolved` under the ordinary connection evaluator.

### Contextual feasibility and ranking

`candidate_selection.py` consumes the complete generated/evaluated set, separates hard-blocked candidates first, applies explicit contextual feasibility, then ranks retained selectable candidates deterministically.

Current contextual families are:

- required reach, using known maximum/extended tether length;
- explicit environmental exposure against accepted selected-component `prohibited_exposure` constraints; and
- elevated snag preference, using minimum/retracted tether length only inside complete baseline-quality ties.

Unknown reach/environment facts remain explicit fallback uncertainty rather than being rewritten as pass/fail values.

Ranking remains lexicographic rather than weighted. It does not prefer brands, direct paths, fewer components, tether form, excess capacity headroom, excess maximum reach, or endpoint interchangeability merely because those facts exist.

### Recommendation-run orchestration

`recommendation_run.py` owns complete generation -> evaluation -> selection execution. It evaluates every generated candidate exactly once and passes that exact set to selection.

Global selector exhaustion therefore remains safe only at the complete run boundary.

### End-to-end recommendation benchmark

`tests/test_recommendation_benchmark.py` and `benchmarks/recommendation_e2e_golden.json` provide the semantic golden over the complete recommendation run.

The benchmark starts at accepted claims / normalized resolved facts rather than live acquisition. It therefore complements the supply-side goldens rather than duplicating them.

The golden deliberately contains only semantic expected outcomes. It does not contain SKU pairs, tool/tether/anchor/attachment product refs, or canonical candidate IDs; a regression recursively rejects identity-shaped keys such as `*_id`, `*_ref`, and `*_sku` forms from the answer key.

The current three scenarios prove:

- a reusable manufacturer-declared Quick Clip -> evidence-backed D-ring anchor context survives declaration resolution, candidate binding, hard evaluation and ranking; the otherwise-equivalent path with fewer pending physical verifications is selected under the existing lexicographic ranking semantics;
- `no_suitable_recommendation` is reached only for a non-empty complete generated set after both alternatives have been evaluated, with the under-capacity alternative blocked by `load_capacity / failed` and the separate adequate-capacity alternative blocked by `connection_compatibility / unresolved`; and
- a ToolAttachment path preserves two accepted surface-feature subjects independently through explicit normalized eligibility, selected installation-feature binding, resolved ToolAttachment installation constraints, the ToolAttachment-provided tether interface, candidate generation and hard evaluation, so the flat/clean installation remains selectable while the separately bound curved/clean installation is blocked specifically by the existing `installation_surface_profile` hard product constraint.

The ToolAttachment scenario deliberately supplies its generic `feature_kind = surface` eligibility as a normalized runtime primitive at the benchmark seam. It does not add a production `surface_bonded_attachment` selection-class compiler merely for fixture convenience. Accepted feature, product-constraint and provided-interface claims still flow through their normal resolvers.

The benchmark does not add a new scorer, recommendation path, compatibility family, hard-constraint rule or exhaustion rule. See `recommendation-benchmark.md` for the durable contract.

### Session-local condition resolution

`recommendation_session.py` and `recommendation_session_adapter.py` resolve already-pending runtime verifications/pre-use actions without regenerating, re-evaluating, or re-ranking survivors.

Session outcomes remain candidate/configuration evidence. They never become persistent catalogue compatibility claims.

A worker is expected to have the Tool, but candidate tether products may not yet be physically present during recommendation. Runtime inspection of a candidate tether therefore must not be required to establish catalogue endpoint assignment needed for recommendation. Pre-use checks may validate installation/use conditions after selection, but they do not rescue missing catalogue assignment semantics.

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

The `connection_compatibility` claim subject retains the declaration primitives and source provenance. `resolve_connector_interface_compatibility_declarations()` resolves them into reusable declarations, and `connection_contexts_from_compatibility_declarations()` binds them to concrete endpoint/target pairs only when the primitives match.

The resulting candidate context reuses the existing `ConnectionManufacturerAssessment(position = explicitly_compatible)` and normal `manufacturer_declared` precedence path. No new Quick Clip hard evaluator is introduced.

PR #47 supplies the first real ingested anchor target that can satisfy that declaration. Current first-party NLG Adjustable Wristband (101365) wording directly binds a singular D-ring to lanyard attachment, so the accepted interface resolves as:

```text
role = anchor_attachment_tether_side
interface_type = ring
attributes = { ring_form: d_ring }
```

The target form remains an ordinary `interface.attribute.*` fact; the resolver, declaration matcher and connection evaluator did not require a new D-ring-specific domain field or Quick Clip-specific branch.

The extraction boundary is intentionally narrow:

- the product must be an `AnchorAttachment`;
- a singular D-ring must be directly bound to lanyard attachment/use;
- provision-style evidence requires an affirmative local provision/ownership predicate such as `utilises`, `includes`, `features`, `provides`, `has`, or `equipped with`;
- direct attachment wording counts as product-owned use evidence only for a referential target such as `the`, `this`, or `its D Ring`, not an indefinite external `a D Ring`;
- denied, prohibited, questioned or externally required D-ring relations fail closed;
- plural D-ring/lanyard sets fail closed rather than being collapsed into one anonymous physical interface;
- product names alone never establish form; and
- generic rings remain generic rings.

The vertical regression now proves that the extracted/resolved anchor target binds through the existing PR #44 declaration and evaluates `COMPATIBLE / MANUFACTURER_DECLARED` without SKU-pair compatibility logic.

Important remaining scope boundaries:

- `similar anchor point` is not normalized to D-ring;
- ToolAttachment D-rings remain outside the PR #44 declaration target role;
- existing container D-rings remain `container_connection` rather than being widened to anchor-attachment role;
- Quick Clip remains outside `gated_connector_to_closed_interface.v1`;
- the declaration does not infer closure, locking, action count or geometry; and
- the declaration does not itself establish tether endpoint direction/interchangeability.

See `connector-declared-compatibility.md` for the declaration/binding model and `anchor-interface-form.md` for the PR #47 evidence boundary.

### ToolAttachment-provided D-ring form

PR #50 preserves narrower form on an existing ToolAttachment-provided tether interface only after the established ToolAttachment interface extractor has already created the concrete subject from affirmative local D-ring/tether-point or tool-lanyard evidence.

The recurring normalized result is:

```text
role = tool_attachment_tether_side
interface_type = ring
attributes = { ring_form: d_ring }
```

The form layer does not create interface identity, rewrite structural role or independently scan product names for `D Ring`. Generic ring evidence remains generic. The supply-side benchmark now proves the same evidence pattern on NLG 101363 and NLG 101481.

This is deliberately not a compatibility rule. PR #44 still requires `anchor_attachment_tether_side`, so the enriched ToolAttachment target cannot satisfy that declaration. Focused coverage also proves that a carabiner engaging the enriched ToolAttachment D-ring remains `UNRESOLVED` without an independent compatibility basis. No declaration matcher, evaluator, runtime-verification family, candidate hard constraint or ranking rule changes.

Repeated container form remains deferred: NLG 101492 already has six concrete internal `container_connection` ring identities and promising D-ring evidence, but narrower form does not yet close a recurring recommendation/evaluation uncertainty. NLG 101705 remains fail-closed because its plural brace-mounting and tool-anchor D-ring sets do not yet have sufficiently concrete per-set identity/count evidence for safe materialization.

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

## Endpoint-assignment relation model

A `TetherEndpointAssignmentDeclaration` represents accepted evidence about the relationship between tether endpoints rather than an intrinsic side role on either endpoint.

The first supported semantic is:

```text
reversible_tool_anchor_pair
```

V1 requires exactly two distinct endpoint references owned by the same tether. It applies only when both individual endpoint roles remain `UNKNOWN`, and permits the two oriented candidate assignments without rewriting either endpoint to `EITHER`.

The declaration retains assignment basis, issuer, scope and source URLs. `CandidateConfiguration` retains the selected `tether_ref` so authorization cannot leak across tethers with repeated local endpoint IDs. `GeneratedCandidate` requires the selection-level `EndpointAssignmentProof` values — including basis — to be the exact deterministic projection of the operative declarations.

The derived-equivalence threshold is conjunctive: affirmative same-construction endpoint evidence plus undifferentiated tool-to-anchor pair use, with explicit directional/different-end evidence acting as a veto. A shared generic connector description or manufacturer silence is not positive proof. Negated pair-use wording cannot satisfy the positive-use requirement, and separately designated connectors assigned to opposite sides are directional evidence rather than reversible evidence.

The relation is not a compatibility basis, ranking preference or SKU-pair rule.

### Representative endpoint-assignment evidence findings

- **NLG 101434:** first production positive for the bounded Quick Clip derived-equivalence rule. Current first-party copy establishes `360° Quick Clip™ connectors at each end` together with tool-to-anchor tether use.
- **NLG 101519:** promising future evidence case; same-construction carabiner wording is available, while the strongest pair-use evidence reviewed is in a datasheet not yet part of ordinary NLG primary-page ingestion.
- **Hilti 2261970:** remains unknown. Double-carabiner topology and one/second-carabiner use wording do not independently establish the same connector construction at both ends.
- **StopDrop SDCOIL32:** remains unknown. `2 locking screwgate carabiner` establishes multiplicity/mechanism family but not the full equivalence-plus-pair-use conjunction.
- **NLG 101756:** strong negative control. First-party evidence explicitly distinguishes an integral anchor/belt carabiner from a tool-side Rotobiner; directional evidence wins and prevents symmetry-derived widening.

## Provenance principles currently in force

- manufacturer wording and URLs stay attached to atomic claims;
- accepted declared compatibility retains issuer and scope;
- accepted endpoint-assignment relations retain owner, assignment basis, issuer, scope and source URLs;
- derived endpoint assignment must remain visibly derived rather than being represented as a manufacturer declaration;
- target-interface form is evidence on a concrete physical interface, not a product-name or generic-type inference;
- candidate generation retains selected component, feature, endpoint, target and owner identity;
- selection-level endpoint-assignment proofs must exactly match the operative configuration declarations;
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

PR #48 adds the first golden regression over this global boundary: a non-empty two-candidate run may conclude `no_suitable_recommendation` only after both generated candidates are retained and exactly evaluated, with each expected hard blocker bound to the intended semantic alternative rather than merely appearing somewhere in the blocked set.

### Session-local `exhausted`

Possible only after an originating run already had a selected/ranked selectable stream. It means every candidate in that original stream later failed at least one session-local condition.

It must not rewrite the original global selector result.

## Benchmark state

The latest complete executable validation for PR #50 is workflow run **34301848210** on head `40f08e3443590d6f9c56a6fbca981e7338b280f0`. The complete `Ingestion live smoke` workflow passed:

- unit test suite: **421 passed**;
- Batch 1 live acquisition: **12/12 products**;
- Batch 1 extraction: **55 TP / 0 FP / 0 FN**;
- Batch 1 micro precision/recall: **1.0 / 1.0**;
- Batch 1 recommendation-data coverage: the new ToolAttachment D-ring-form requirement is satisfied and the two pre-existing `source_blocked` requirements remain unchanged;
- fresh Batch 2 post-blind acquisition: **8/8 products**;
- fresh Batch 2 extraction: **99 TP / 0 FP / 0 FN**;
- fresh Batch 2 micro precision/recall: **1.0 / 1.0**;
- fresh Batch 2 recommendation-data coverage: **51/51 requirements**, **8/8 products complete**;
- the immutable Batch 2 blind artifact remained unchanged as the historical pre-fix baseline; and
- benchmark artifact upload completed successfully.

This run validates the PR #50 form-enrichment boundary on top of the PR #49 ToolAttachment-mediated recommendation golden. The same generic enrichment is exercised by two independent supply-side ToolAttachment cases: NLG 101363 in Batch 1 and NLG 101481 in Batch 2. Both retain the existing concrete `tether_side_ring` subject and `tool_attachment_tether_side` role while adding only `interface.attribute.ring_form = d_ring` from explicit local D-ring interface evidence.

The recommendation golden itself remains the same three semantic scenarios. PR #50 does not add a compatibility outcome or a fourth system-level scenario because target form alone is not a compatibility basis and the existing ToolAttachment recommendation path already provides the downstream seam that justifies preserving the fact.

The answer key intentionally omits SKU pairs, runtime product refs and canonical candidate IDs. Semantic scenario-role labels describe expected behavior without identifying a real product or runtime candidate. The catalogue benchmark remains the supply-side ingestion/recommendation-readiness benchmark; the recommendation golden is the downstream semantic contract.

## Recorded evidence/semantic gaps

The existing Batch 2 evidence gaps remain explicit:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |
| NLG 101520 | Ascent™ Pouch | `public_fact_not_established` | external daisy-chain presence is established, but an individual loop/site count is not publicly established |

PR #47 closed the first singular anchor-side D-ring form gap. PR #50 now closes the recurring ToolAttachment target-form preservation gap for already-concrete `tool_attachment_tether_side` D-ring interfaces. Neither change promotes generic rings, rewrites structural roles, supplies geometry or creates compatibility from form alone.

Repeated/plural target form remains evidence- and decision-bound. NLG 101492 already has concrete repeated internal container interfaces but should gain narrower form only when that fact closes a recurring recommendation/evaluation uncertainty. NLG 101705 still lacks sufficiently explicit per-set count/identity for its functionally distinct D-ring groups. NLG 101520 generic internal anchors remain form-unknown.

The reusable symmetric-endpoint model gap is also closed, and PR #46 provides the first production evidence-derived assignment case. Broader symmetric-looking dual-ended products remain an evidence problem rather than a reason to weaken endpoint roles globally: each future derivation must clear an evidence pattern strong enough to establish the same endpoint construction plus undifferentiated pair use.

PR #49 closes the ToolAttachment-mediated end-to-end benchmark gap without expanding production semantics. Further benchmark growth should be driven by concrete regression risk rather than scenario count.

## Next highest-value workstreams

### 1. Extend target-interface form only when it closes a concrete downstream uncertainty

PRs #47 and #50 establish the reusable pattern: preserve narrower form on an already-evidence-backed concrete interface, keep structural role unchanged, and do not treat form itself as compatibility.

The next form slice should not be selected merely because a catalogue page contains richer D-ring wording. It should first identify a recurring recommendation, declaration-binding, geometry or hard-evaluation uncertainty that the narrower form would actually resolve. NLG 101492 remains a candidate only if its repeated `container_connection` D-ring form becomes decision-relevant; NLG 101705 remains blocked on plural identity/count; NLG 101520 remains generic.

Do not build a broad ring taxonomy for its own sake.

### 2. Extend derived endpoint equivalence only from recurring evidence patterns

NLG 101519 is a useful next evidence candidate if/when first-party datasheet acquisition becomes part of the normal NLG source graph. Generic dual-carabiner derivation should not be introduced merely because most products are expected to be symmetric.

Any additional production family should first establish a repeatable first-party pattern for same endpoint construction and tool-to-anchor pair use, with directional/mixed-end evidence as a hard veto.

### 3. Selective geometry/evidence work

Continue geometry, measurements and document-join work only when one primitive closes a recurring uncertainty, proves a reusable hard rule, or materially reduces runtime verification burden.

Do not build a general CAD model.

### 4. Further downstream goldens only for durable regression seams

Session fallback and contextual feasibility are already covered by focused executable tests. Add system-level golden scenarios there only when a concrete integration risk or regression demonstrates that the recommendation-run contract needs another durable semantic case.

Do not expand the golden solely for broader product or SKU coverage.

## Documentation workflow

Documentation is part of the definition of done for every pull request.

**Every PR must include, at minimum, an update to `project-status.md` before merge.** The update should keep the operational handoff aligned with the code being merged — normally the date/current development line, benchmark state when relevant, any changed semantic boundary, and the next highest-value workstream.

PRs that materially change durable architecture, evidence semantics, compatibility, recommendation behavior or benchmark contracts should also update the relevant dedicated design document(s). The mandatory `project-status.md` update is a floor, not a substitute for those deeper updates.

## Working principles for the next phase

- every PR must update `project-status.md` before merge, with deeper design docs updated when their durable semantics change;
- no SKU-specific extraction, compatibility, generation, ranking, session or recommendation branches;
- recommendation golden answer keys must contain semantic expected outcomes, not runtime product configuration, SKU pairs or canonical candidate IDs;
- goldens validate outputs and must never be fed back into runtime construction;
- no inferred compatibility from interface names alone;
- no promotion of `UNKNOWN` endpoint role to `EITHER` without explicit role evidence;
- endpoint-pair assignment evidence must remain separate from individual endpoint role evidence;
- assignment provenance must distinguish manufacturer declaration from TetherLens derivation;
- no reversible assignment from `dual` / `double` / `twin`, a shared normalized connector spec, pair-use wording or manufacturer silence alone;
- endpoint assignment is a configuration-validity constraint, not a ranking preference; one viable permitted orientation is sufficient for product selection, and equivalent reversible orientations should not become duplicate user-facing product recommendations solely because the physical ends can be swapped;
- catalogue assignment required for recommendation must not depend on physical inspection of a tether the worker may not possess;
- target-interface form must remain bound to concrete accepted evidence; generic `ring` must not silently become `d_ring`;
- keep manufacturer scope, technical fit, installation constraints, policy, context, ranking and session outcomes separate;
- hard candidate viability remains owned exclusively by `CandidateEvaluation`;
- contextual feasibility/ranking must never rescue a hard-blocked candidate;
- preserve candidate identity and provenance through every downstream layer;
- fail closed on identity/feature/component/endpoint/assignment/interface binding ambiguity;
- hard physical contradiction and authoritative source conflict remain blocking;
- inconclusive geometry remains inconclusive;
- successful runtime verification remains session/configuration evidence only;
- generic absence of environmental/geometry/role/assignment/form evidence must not become suitability;
- do not infer evidence strength from source count;
- use the complete recommendation-run boundary for global exhaustion;
- preserve the immutable Batch 2 blind artifact and use fresh post-blind evaluation for regression checking; and
- prefer small reusable evidence primitives over broad vocabularies introduced without a concrete decision need.

## Suggested fresh-chat starting point after PR #50

> Continue TetherLens from merged `main` after PR #50. Inspect the completed target-interface-form model and current recommendation/evidence gaps, then choose the next smallest reusable slice only where accepted evidence closes a recurring downstream uncertainty. Preserve concrete interface/endpoint identity and structural role, keep form separate from compatibility, and do not widen hard constraints or inference from generic catalogue wording.