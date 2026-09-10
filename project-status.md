# TetherLens Project Status

_Last updated: 2026-09-10_

This document is the operational handoff for the current TetherLens ingestion, compatibility, candidate-generation/evaluation/selection, recommendation-run, session-resolution, contextual reasoning, recommendation-benchmark, and cross-vendor portability stack. It records the semantics that should be preserved and the highest-value remaining workstreams.

For durable design details, use the dedicated documents including `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `connector-mechanism-semantics.md`, `connector-declared-compatibility.md`, `anchor-interface-form.md`, `endpoint-assignment-semantics.md`, `cinch-loop-semantics.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `single-feature-captive-eligibility.md`, `mass-reconciliation.md`, `container-interface-topology.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `environmental-context.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`.

## Current development line

The current development line through PR #56 includes:

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
- PR #49 — ToolAttachment-mediated recommendation golden coverage, exercising accepted/resolved tool features, explicit selected-feature eligibility binding, normalized installation constraints, a ToolAttachment-provided tether interface, complete generation/hard evaluation and selection without production rule changes or golden product identity;
- PR #50 — evidence-backed ToolAttachment target-form enrichment, preserving `ring_form = d_ring` on an already-concrete `tool_attachment_tether_side` ring when the accepted local interface evidence itself identifies one singular D-ring, while keeping generic/plural rings fail-closed and leaving compatibility/hard constraints unchanged;
- PR #51 — decision-bound first-party NLG datasheet acquisition for a symmetric-looking dual-carabiner assignment gap plus a second bounded `derived_endpoint_equivalence` production family, with final-host and product-identity revalidation, affirmative/local construction and pair-use evidence, directional-endpoint vetoes, concrete endpoint identity, `TetherSide.UNKNOWN`, and compatibility separation preserved;
- PR #52 — the first frozen cross-vendor portability audit after the NLG-heavy development phase, covering eight unseen GRIPPS, FallTech, Ty-Flot and Dropsafe Tether/ToolAttachment products and classifying the smallest required change as facts-only, vendor-ingestion-only, new reusable primitive or SKU-specific exception without changing production recommendation semantics;
- PR #53 — reusable single-feature captive ToolAttachment eligibility composition, adding manufacturer-neutral handle-only and through-opening-only compiler classes over the existing `feature_kind` / `captive_state` primitives while preserving the existing combined OR class, exact feature-instance binding, fail-closed conflict handling and unchanged downstream recommendation rules;
- PR #54 — the first implemented B-class cross-vendor portability proof, adding GRIPPS and FallTech vendor extraction for H01079 and 5027B while keeping endpoint assignment, compatibility, candidate generation, hard evaluation and ranking unchanged, preserving GRIPPS fixed directionality and capacity conflict, and reusing the existing cinch-loop family for FallTech;
- PR #55 — the remaining provisional C-class Ty-Flot retention slice, adding manufacturer-neutral `contraction_capture`, bounded `external_section_attachment` eligibility from complete source-local diameter-fit envelopes, exact-product/final-host manufacturer provenance hardening, and shared source-precision-aware mass reconciliation reused by Ty-Flot and GRIPPS without changing downstream compatibility, hard evaluation, ranking or selection rules; and
- PR #56 — the first fresh post-PR #55 portability audit, freezing an eight-product FallTech/GRIPPS/Ergodyne/3M cohort at merged `main` commit `29c01939c8e8774dcc553527255fc4281708480c`, finding **0 A / 6 B / 2 C / 0 D**, confirming on a fresh 3M product that a manufacturer-required companion can reuse the existing `required_pairing` plus multi-component ToolAttachment assembly model, and isolating one recurring non-captive handle/neck capture-fit gap across GRIPPS SnapLock and 3M Quick Spin without changing production recommendation semantics.

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

`manufacturer_declared` means the manufacturer directly establishes reversibility/interchangeability. `derived_endpoint_equivalence` means TetherLens derives the same bounded assignment relation from a conjunction of accepted first-party facts. PR #46 supplies the first production derivation through the NLG Quick Clip evidence pattern where the same named Quick Clip construction is affirmatively established at each/both end, tool-to-anchor tether use is established, both endpoint roles remain unknown, and no directional/mixed-connector evidence exists.

PR #51 adds a second bounded production evidence family without widening the reusable relation. A first-party NLG datasheet may be followed only when the primary page already identifies a symmetric-looking dual/twin/double carabiner tether and does not expose an obvious directional or mixed named-connector split. The link must be explicitly labelled `Datasheet`; after fetch/redirect, the final artifact must still be an NLG-hosted product datasheet whose explicit Product Code/SKU matches the current product identity. Rejected documents are excluded before inherited NLG extraction. Assignment is then derived only when one trusted artifact itself establishes exactly two unresolved carabiner endpoints, an affirmative product-local collective construction equivalent to `dual/twin/two ... double-action carabiners`, an actual affirmative undifferentiated tool-to-anchor attachment/connection relationship, and no directional/mixed-end veto evidence. Negation or prohibition before or after the positive phrase, other-product/comparison wording, mere tool/anchor term co-occurrence, or separately distinguished carabiners assigned to opposite roles all fail closed. Directional identity checks remain sentence-local so repeated references to one undifferentiated plural pair do not create a false split. NLG 101519 is the first positive case; NLG 101756 remains the directional negative control.

The derived route does **not** make any single weak clue sufficient. `dual` / `double` / `twin` naming, shared normalized `ConnectorSpec`, connectors at both ends, one-to-tool/one-to-anchor wording, or absence of directional wording remain insufficient by themselves.

The relation does not mutate either endpoint role, does not override fixed or partially known role evidence, and does not establish connector/interface compatibility. Assignment declarations are tether-owned so repeated local endpoint IDs cannot leak authorization across products. Generated candidates retain declaration basis and provenance separately from canonical candidate identity; rehydration requires the retained selection proofs to match the operative declarations exactly.

Endpoint assignment is a **configuration-validity constraint rather than a product-ranking attribute**. For product selection, one manufacturer-permitted orientation that produces a viable tool-side connection and a viable anchor-side connection is sufficient. A reversible pair does not make a tether preferable merely because both orientations are allowed. Reversible orientations remain separate internally through endpoint-to-target evaluation and provenance checks, but equivalent orientations should not surface as duplicate user-facing product recommendations solely because the physical ends can be swapped.

See `endpoint-assignment-semantics.md` for the full v1 evidence threshold, production rules, selection significance and evidence findings.

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

### Cross-vendor portability benchmark

PR #52 adds the historical supply-side architecture audit in `benchmarks/cross_vendor_portability_v1.json`, guarded by `tests/test_portability_benchmark.py` and documented in `portability-benchmark.md`.

The V1 core is frozen at merged `main` after PR #51. The cohort deliberately excludes NLG and contains two products each from GRIPPS, FallTech, Ty-Flot and Dropsafe. Products are classified by the smallest change required for correct participation:

```text
A facts_only
B vendor_ingestion_only
C new_reusable_primitive
D sku_specific_exception
```

The reviewed V1 result remains **0 A / 5 B / 3 C / 0 D**. Later PRs do not rewrite those classifications; PRs #53-#55 implemented reusable gaps against the evolving current core while preserving the historical answer key.

At the PR #52 freeze, two C products revealed the same single-feature captive-eligibility gap. PR #53 closes that current-core gap with separate manufacturer-neutral `captive_handle_attachment`, `captive_through_opening_attachment`, and combined `captive_feature_attachment` compiler classes. GRIPPS H01079 and FallTech 5027B then supplied B-class vendor-ingestion proofs under PR #54 without downstream semantic changes. PR #55 closes the remaining provisional Ty-Flot retention-mechanism gap through manufacturer-neutral `contraction_capture` plus source-local external-section fit envelopes; Ty-Flot `COLDSH41X35` itself remains non-ready because current first-party dimensional/variant evidence conflicts.

PR #56 adds a separate fresh V2 audit in `benchmarks/cross_vendor_portability_v2.json`, guarded by `tests/test_portability_benchmark_v2.py`. It freezes the current core at merged `main` commit `29c01939c8e8774dcc553527255fc4281708480c`, after PR #55, and samples eight products disjoint from V1: two each from FallTech, GRIPPS, Ergodyne and 3M. The V2 guard also excludes the pre-PR #55 Ergodyne web ToolAttachment + required tape/wrap family that was already used as an architecture design input, so SKU disjointness alone cannot qualify that prior sample as fresh.

The reviewed V2 result is:

```text
A facts_only               0
B vendor_ingestion_only    6
C new_reusable_primitive   2
D sku_specific_exception   0
```

Six of eight fresh products fit the existing domain/recommendation core. The lack of A results is now primarily a catalogue-throughput signal: current GRIPPS/FallTech adapters are intentionally narrow development proofs, while Ergodyne and 3M do not yet have normal adapters.

The pre-PR #55 architecture had already considered an Ergodyne web ToolAttachment retained by required tape/wrap, including non-captive geometry and multi-component assembly semantics. That family is therefore explicitly excluded from the fresh V2 cohort rather than being counted as a B portability success. The replacement is Ergodyne Squids 3001, a retractable tether whose explicit anchor-side manual-locking carabiner, tool-side choking loop, working range and rated capacity fit existing neutral tether primitives and therefore remain B-class onboarding work.

V2 still includes a fresh cross-vendor confirmation of the already-designed required-companion model: 3M 1500007 requires Quick-Wrap Tape II, while the technical schema already supports manufacturer-backed `required_pairing` and `ToolAttachmentAssemblyOption` already accepts multiple component instances. The correct path is to retain both catalogue-product identities and compose one multi-component ToolAttachment assembly; no product-pair compatibility rule is needed. Its B result is reuse of an established generic model, not evidence that V2 newly discovered the companion-product primitive.

The two V2 C cases — GRIPPS H01150 SnapLock and 3M 1500028 Quick Spin Medium — expose one recurring unresolved boundary. Both intentionally install onto a **non-captive** handle/neck-style tool feature. The existing runtime feature/predicate model can describe non-captive features, and `mechanical_capture` is a plausible existing retention family, but the production eligibility compiler has no conservative manufacturer-neutral execution path for this installation family. Critically, neither branded S/M/L/XL sizing nor a nominal attachment diameter is enough to invent a tool-feature fit envelope.

The next slice therefore starts with installation evidence, not code. It must determine whether the smallest reusable model is a dimension-bounded eligibility path, a bounded pre-use/runtime fit verification, or a combination. It must not infer fit from nominal size, promote a non-captive handle to captive, or introduce GRIPPS/3M-specific downstream logic.

The V2 audit changes no production compatibility, candidate-generation, hard-evaluation, ranking or selection rule.

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

The vertical regression proves that the extracted/resolved anchor target binds through the existing PR #44 declaration and evaluates `COMPATIBLE / MANUFACTURER_DECLARED` without SKU-pair compatibility logic.

Important remaining scope boundaries:

- `similar anchor point` is not normalized to D-ring;
- ToolAttachment D-rings remain outside the PR #44 declaration target role;
- existing container D-rings remain `container_connection` rather than being widened to anchor-attachment role;
- Quick Clip remains outside `gated_connector_to_closed_interface.v1`;
- the declaration does not infer closure, locking, action count or geometry; and
- the declaration does not itself establish tether endpoint direction/interchangeability.

See `connector-declared-compatibility.md` for the declaration/binding model and `anchor-interface-form.md` for the PR #47 evidence boundary.

### ToolAttachment-provided D-ring form

PR #50 preserves narrower form on an existing ToolAttachment-provided tether interface only after the established ToolAttachment interface extractor has already created the topology subject from affirmative local D-ring/tether-point or tool-lanyard evidence.

The recurring normalized result is:

```text
role = tool_attachment_tether_side
interface_type = ring
attributes = { ring_form: d_ring }
```

The form layer does not create interface identity, rewrite structural role or independently scan product names for `D Ring`. Generic ring evidence remains generic. The supply-side benchmark proves the same singular evidence pattern on NLG 101363 and NLG 101481.

A review hardening guard also prevents plural D-ring wording from enriching the legacy singular `tether_side_ring` subject. The upstream topology behavior is deliberately unchanged in this slice; PR #50 simply refuses narrower form where the raw evidence does not establish one concrete D-ring identity.

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

PR #51 keeps that threshold intact while adding one more bounded evidence family. The NLG source graph follows an explicitly labelled first-party datasheet only for the specific symmetric-looking dual-carabiner assignment gap; it does not establish a general document-crawling policy. The fetched document must remain on an approved NLG host after redirects, retain the purpose-scoped datasheet relationship, and explicitly match the current product identity before it may participate in extraction. The complete assignment conjunction must then be affirmative and local on one trusted artifact: collective double-action construction, a genuine tool-to-anchor attachment/connection relationship rather than keyword co-occurrence, and no sentence-local evidence that separately distinguished carabiners have opposite roles. Rejected documents contribute no inherited NLG claims.

The relation is not a compatibility basis, ranking preference or SKU-pair rule.

### Representative endpoint-assignment evidence findings

- **NLG 101434:** first production positive for the bounded Quick Clip derived-equivalence rule. Current first-party copy establishes `360° Quick Clip™ connectors at each end` together with tool-to-anchor tether use.
- **NLG 101519:** second positive production case through decision-bound first-party datasheet evidence. The primary page establishes the symmetric-looking dual double-action carabiner pair; the identity-bound datasheet supplies tool-to-anchor pair use on the same affirmative collective double-action construction, allowing the existing derived relation without rewriting endpoint roles or introducing a SKU-specific assignment rule.
- **Hilti 2261970:** remains unknown. Double-carabiner topology and one/second-carabiner use wording do not independently establish the same connector construction at both ends.
- **StopDrop SDCOIL32:** remains unknown. `2 locking screwgate carabiner` establishes multiplicity/mechanism family but not the full equivalence-plus-pair-use conjunction.
- **NLG 101756:** strong negative control. First-party evidence explicitly distinguishes an integral anchor/belt carabiner from a tool-side Rotobiner; directional evidence wins, prevents decision-bound equivalence datasheet traversal, and prevents symmetry-derived widening.
- **GRIPPS H01079:** cross-vendor fixed-direction control. The first-party product wording distinguishes a large dedicated anchor-end carabiner from a small dedicated tool-end carabiner. PR #54 emits those roles directly and proves the unchanged side-semantics rule rejects reversed use; no reversible assignment relation is created.

PR #52 also retains Dropsafe twin-carabiner products as the opposite evidence control: shared/twin hardware fits the existing endpoint model, but public multiplicity/mechanism wording alone does not justify reversible assignment.

## Provenance and evidence-reconciliation principles currently in force

- manufacturer wording and URLs stay attached to atomic claims;
- a request labelled as manufacturer evidence is not sufficient provenance: manufacturer-labelled requests must stay within the declared first-party host boundary, and the final resolved artifact host is revalidated after redirects before it reaches manufacturer extraction;
- explicitly secondary external sources remain secondary and may be used only under the applicable property evidence policy; they are never upgraded to manufacturer evidence because a manufacturer page linked to them;
- accepted declared compatibility retains issuer and scope;
- accepted endpoint-assignment relations retain owner, assignment basis, issuer, scope and source URLs;
- derived endpoint assignment must remain visibly derived rather than being represented as a manufacturer declaration;
- decision-bound supporting-document traversal must remain first-party, purpose-scoped, identity-bound and revalidate the final fetched host after redirects; rejected documents must fail closed before inherited extraction rather than becoming generic evidence sources;
- target-interface form is evidence on a concrete physical interface, not a product-name or generic-type inference;
- canonical-unit normalization must precede semantic conflict checks for dimensional evidence; equivalent metric/customary representations are not conflicts;
- mass-valued source declarations use shared source-precision-aware reconciliation after identity/evidence policy has selected the claims to compare: each declaration defines a canonical kilogram rounding interval, overlapping intervals may corroborate, and missing raw precision fails closed to the exact normalized value;
- shared mass reconciliation does **not** choose evidence priority, average values, reconcile different product identities, or create a global rule that every mass source must agree; materially different same-priority mandatory facts remain blocking;
- candidate generation retains selected component, feature, endpoint, target and owner identity;
- selection-level endpoint-assignment proofs must exactly match the operative configuration declarations;
- ranking retains the original `GeneratedCandidate` and `CandidateEvaluation` rather than reconstructing provenance from IDs;
- runtime verification remains session/configuration evidence;
- a successful field check never becomes universal SKU-pair compatibility; and
- source-count/URL-count heuristics are not evidence-strength scores.

See `mass-reconciliation.md` for the shared rounded-mass semantic boundary.

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

PR #55 remains the latest code-bearing portability implementation before this audit. Its completed workflow is green across unit tests, the live manufacturer benchmark, Batch 1 scoring, the immutable Batch 2 blind baseline, and the fresh Batch 2 post-blind evaluation/scoring.

PR #56 is an **audit-only** benchmark/documentation change. It adds `cross_vendor_portability_v2.json` and focused regression guards but deliberately changes no production recommendation semantics. V1 remains frozen at **0 A / 5 B / 3 C / 0 D**; V2 freezes the post-#55 core at `29c01939c8e8774dcc553527255fc4281708480c` and records **0 A / 6 B / 2 C / 0 D**.

The V2 guards prove that:

- the cohort is disjoint from V1, excludes the pre-modelled Ergodyne tape/wrap ToolAttachment family, and contains two products each from FallTech, GRIPPS, Ergodyne and 3M;
- more than half of the fresh cohort is A/B reuse, concretely six B and two C;
- no D-class SKU-specific exception pressure is present;
- the two C products are from independent manufacturers and share the same non-captive capture/fit boundary; and
- the fresh 3M required-companion case remains B because `required_pairing` plus multi-component ToolAttachment assemblies already represent the architecture.

The recommendation golden itself remains the same three semantic scenarios:

- a manufacturer-declared connection path whose selected candidate is `recommended_with_constraints`, retains `COMPATIBLE / MANUFACTURER_DECLARED` on the anchor side and outranks a comparable alternative because it has one rather than two pending physical verifications;
- a non-empty two-candidate run in which the `under_capacity` semantic alternative is blocked by `load_capacity / failed` while the separate `unresolved_tool_connection` alternative is blocked by `connection_compatibility / unresolved`, allowing bounded `no_suitable_recommendation` only after complete evaluation; and
- a ToolAttachment-mediated two-feature run in which both surface features are explicitly eligible, the selected feature is retained through constraint evaluation, the flat/clean path remains selectable, and the separate curved/clean path is blocked specifically by the existing hard installation-surface-profile constraint.

The answer key intentionally omits SKU pairs, runtime product refs and canonical candidate IDs. Semantic scenario-role labels describe expected behavior without identifying a real product or runtime candidate. The catalogue benchmark remains the supply-side ingestion/recommendation-readiness benchmark; the recommendation golden is the downstream semantic contract; and portability cohorts test whether the core abstractions remain reusable before new manufacturer implementation work begins.

## Recorded evidence/semantic gaps

The existing Batch 2 evidence gaps remain explicit:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |
| NLG 101520 | Ascent™ Pouch | `public_fact_not_established` | external daisy-chain presence is established, but an individual loop/site count is not publicly established |

PR #47 closed the first singular anchor-side D-ring form gap. PR #50 closes the recurring ToolAttachment target-form preservation gap for already-concrete `tool_attachment_tether_side` D-ring interfaces. Neither change promotes generic rings, rewrites structural roles, supplies geometry or creates compatibility from form alone.

Repeated/plural target form remains evidence- and decision-bound. NLG 101492 already has concrete repeated internal `container_connection` ring identities but should gain narrower form only when that fact closes a recurring recommendation/evaluation uncertainty. NLG 101705 still lacks sufficiently explicit per-set count/identity for its functionally distinct D-ring groups. NLG 101520 generic internal anchors remain form-unknown. The review-added singular guard also prevents ambiguous plural ToolAttachment wording from receiving `ring_form = d_ring` on the legacy singular subject.

The reusable symmetric-endpoint model remains closed by PRs #45-#46, and PR #51 supplies the second bounded production evidence-derived assignment family. NLG 101519 is therefore no longer an outstanding source-graph gap. Broader symmetric-looking dual-ended products remain evidence problems rather than a reason to weaken endpoint roles globally: each future derivation must establish a new repeatable first-party evidence pattern strong enough to prove the same endpoint construction plus undifferentiated pair use.

PR #49 closes the ToolAttachment-mediated end-to-end benchmark gap without expanding production semantics. Further recommendation-golden growth should be driven by concrete regression risk rather than scenario count.

PR #53 closes the recurring **single-feature captive attachment eligibility composition** gap shared by GRIPPS H01055 and FallTech 5318A10. The existing runtime feature primitives were sufficient; the production compiler now has evidence-separate handle-only, through-opening-only and combined OR classes without introducing vendor/SKU branches or downstream hard-rule changes.

PR #54 closes the first implementation-level **B-class cross-vendor portability proof** for GRIPPS H01079 and FallTech 5027B. The result supports the PR #52 hypothesis that both products need vendor extraction rather than a core rule change. GRIPPS capacity remains an evidence-reconciliation gap, not an architecture gap; FallTech endpoint direction remains unknown unless stronger product-local evidence is found.

PR #55 closes the remaining provisional portability C-class **Ty-Flot contraction-retention architecture gap** in the current core. `COLDSH41X35` remains non-ready because current first-party Guardian evidence contains conflicting diameter/variant information; that unresolved state is evidence reconciliation, not a reason to widen `contraction_capture` or invent a SKU-specific rule. The frozen PR #52 classifications remain unchanged because they record the architecture state at their historical freeze point.

PR #56 identifies one new recurring architecture question: **non-captive ToolAttachment capture/fit**. GRIPPS SnapLock and 3M Quick Spin both install onto non-captive handle/neck-style geometry, but current production eligibility composition is bounded to captive feature families or a source-local diameter-envelope external-section path. The runtime feature model is already expressive enough to carry non-captive state and geometry, so the next work must first decide whether a new compiler composition is actually needed or whether existing predicates plus a bounded fit verification are sufficient.

Do not treat branded size labels or nominal attachment diameter as a complete fit envelope. Do not convert non-captive handles to captive state merely to reuse an existing class. Do not add manufacturer/SKU-specific downstream compatibility logic.

V2 also records a GRIPPS H01074 malformed storefront load field (`7 g / 15 g`) alongside detailed/title evidence for `7 kg / 15 lb`. This remains an evidence/extraction-quality issue rather than a capacity-model gap.

## Catalogue asymmetry and scaling philosophy

TetherLens should explicitly exploit the asymmetry between the two sides of the catalogue: there are very many tool types and individual tool models, but a much smaller set of commercially relevant tethering components and recurring attachment/connector mechanisms.

The intended scaling model is therefore not a tool-by-tether compatibility matrix. It is:

```text
many tools
  -> reusable tool/anatomy/configuration facts

relatively few tethering products
  -> deeply modelled reusable attachment/connector/capacity/constraint primitives

existing rules
  -> many candidate configurations
```

This makes careful modelling of tethering products high leverage when the resulting primitive can apply across many tools. It does not justify indefinite depth on rare branded wording. Prefer a tether-product enrichment when it unlocks many tool/configuration combinations, establishes a recurring evidence family or proves a reusable hard/verification rule. Defer narrow catalogue details whose only immediate effect is one manufacturer/SKU path.

`portability-benchmark.md` is the durable statement of this principle and the frozen cross-vendor tests.

## Portability phase objective

The current cross-vendor work is an **architecture-stabilization phase**, not the destination of the MVP. The aim is to use unfamiliar tethering products to discover the remaining recurring abstractions, while measuring whether the rate of core changes falls as the model matures.

The desired direction over successive representative cohorts is:

```text
more A/B outcomes
fewer but genuinely reusable C findings
D absent or exceptional
downstream recommendation semantics increasingly stable
```

Do not force this trend by widening evidence or hiding real C gaps. A recurring C primitive that unlocks several products or manufacturers is useful architectural learning. The important signal is that such findings become less frequent and more leveraged over time.

The V2 result — **6/8 B, 2/8 C, 0 D** — is a strong stabilization signal but not yet a reason to stop architecture work immediately because both C cases point to one recurring fit boundary across independent manufacturers.

The portability-led phase should be de-emphasized once that remaining high-leverage boundary has been resolved and a subsequent materially different sample is again predominantly A/B, new C findings are occasional and clearly reusable, D remains absent or exceptional, and new manufacturers mostly require acquisition/extraction/evidence work rather than changes to compatibility, generation, hard evaluation or ranking.

When that condition is reached, shift the centre of gravity toward catalogue throughput, scaling the much larger tool catalogue through reusable features/configuration facts, efficient evidence resolution, and the demand-side MVP: recognition, context capture and field recommendations. Continue portability sampling as a periodic stress/regression test rather than the default development driver.

See `portability-benchmark.md` and `benchmark-goals.md` for the durable metrics and exit criteria.

## Next highest-value workstreams

### 1. Establish the smallest reusable non-captive capture/fit model

Start from first-party **installation evidence** for the two independent V2 C cases: GRIPPS H01150 SnapLock and 3M 1500028 Quick Spin. The audit establishes recurrence, but it does not yet establish the exact rule.

Inspect whether existing primitives are sufficient when composed correctly:

- `attachment_method_code = mechanical_capture` where the retaining action supports it;
- `FeatureKind.HANDLE` and/or `FeatureKind.EXTERNAL_SECTION` with explicit `CaptiveState.NON_CAPTIVE`;
- existing feature dimensions and attributes where source-backed;
- existing product constraints; and
- a bounded pre-use/runtime verification if the manufacturer requires a snug/secure fit that catalogue geometry alone cannot establish.

Only add a new reusable selection/compiler primitive if the evidence shows that the current composition cannot faithfully execute the family. Do not infer a min/max tool fit from S/M/L/XL labels or nominal attachment diameter, and do not route non-captive geometry through the captive-handle compiler.

### 2. Prove the boundary with one implementation slice, then re-sample

If the evidence yields one bounded reusable primitive, implement the smallest manufacturer-neutral slice and prove it with both independent manufacturers where practical. Keep retention mechanism, eligibility, dimensional fit and runtime verification separate rather than collapsing them into one branded rule.

After that, run one more **materially different** small portability sample. If it remains predominantly A/B with no D pressure and no comparable recurring C discovery, portability should stop being the default development driver.

### 3. Begin shifting B-class work toward catalogue throughput

The V2 B cohort shows that several unfamiliar products already fit existing semantics. Future vendor work should increasingly be chosen for catalogue leverage and acquisition/evidence efficiency rather than simply to discover more ontology.

Required installation products should use manufacturer-backed `required_pairing` plus multi-component ToolAttachment assemblies where the evidence supports that structure; the mere existence of a separately sold tape/companion product is not a new core primitive.

Existing unresolved GRIPPS/Ty-Flot facts should remain evidence issues unless better evidence or a defensible generic reconciliation rule appears. External PDFs may be useful secondary evidence in future, but off-domain documents must not be represented as manufacturer-hosted evidence merely because they were linked from a manufacturer page.

The NLG line remains valuable, but additional target-form, endpoint-equivalence, geometry or supporting-document work should compete against cross-vendor leverage. Continue such work only when one primitive closes a recurring uncertainty, proves a reusable hard rule, materially reduces runtime verification burden, or is shown by portability work to recur across manufacturers.

Do not repurpose overall product dimensions as gate/section geometry, do not build a general CAD model, and do not broaden NLG-specific source traversal into generic crawling without a concrete decision need.

Further system-level recommendation goldens should still be added only for durable regression seams rather than broader SKU coverage. Use portability sampling, rather than the downstream recommendation golden, for cross-vendor architecture discovery.

## Documentation workflow

Documentation is part of the definition of done for every pull request.

**Every PR must include, at minimum, an update to `project-status.md` before merge.** The update should keep the operational handoff aligned with the code being merged — normally the date/current development line, benchmark state when relevant, any changed semantic boundary, and the next highest-value workstream.

PRs that materially change durable architecture, evidence semantics, compatibility, recommendation behavior or benchmark contracts should also update the relevant dedicated design document(s). The mandatory `project-status.md` update is a floor, not a substitute for those deeper updates.

## Working principles for the next phase

- every PR must update `project-status.md` before merge, with deeper design docs updated when their durable semantics change;
- exploit catalogue asymmetry deliberately: invest in reusable tethering-product primitives that can unlock many tools, rather than constructing or approximating a tool-by-tether SKU matrix;
- judge new cross-vendor products by A/B/C/D portability class, and treat class D SKU-specific recommendation logic as a design smell requiring explicit justification;
- manufacturer-specific acquisition/extraction is acceptable when it emits vendor-neutral facts; manufacturer-specific downstream compatibility/generation/ranking logic is not the default solution;
- keep PR #52's V1 and PR #56's V2 portability cohorts frozen at their stated core revisions; use fresh cohorts to measure an evolved core rather than rewriting historical classifications;
- a separately catalogued required installation product is not automatically a C-class gap: prefer existing manufacturer-backed `required_pairing` plus a multi-component ToolAttachment assembly when those semantics fit the evidence;
- do not infer non-captive attachment fit from branded size labels or nominal attachment diameter; fit geometry must be source-backed or remain a bounded verification question;
- never promote a non-captive handle/neck feature to captive merely to reuse an existing attachment-eligibility compiler;
- preserve fixed directional endpoint evidence directly; do not route explicitly different tool/anchor ends through derived endpoint-equivalence merely because both endpoints share a broad connector family;
- keep unresolved first-party evidence conflicts visible and recommendation-blocking until a defensible reconciliation rule exists; do not choose the more convenient value to make a product ready;
- reconcile mass declarations semantically through shared source-precision-aware canonical intervals, but only after identity/evidence policy determines which claims are comparable; do not turn the helper into a universal evidence-priority or conflict-resolution rule;
- never stitch independently sourced lower/upper dimensional bounds into a synthetic fit envelope; a constrained fit path requires a complete source-local envelope before cross-source reconciliation;
- never widen a single-feature attachment statement into an unevidenced alternative path merely because another compiler class bundles both features;
- emit a narrow single-feature selection class only when accepted evidence directly authorizes that feature family; do not union conflicting narrow claims into the broader OR class inside the resolver;
- no SKU-specific extraction, compatibility, generation, ranking, session or recommendation branches;
- recommendation golden answer keys must contain semantic expected outcomes, not runtime product configuration, SKU pairs or canonical candidate IDs;
- goldens validate outputs and must never be fed back into runtime construction;
- no inferred compatibility from interface names alone;
- no promotion of `UNKNOWN` endpoint role to `EITHER` without explicit role evidence;
- endpoint-pair assignment evidence must remain separate from individual endpoint role evidence;
- assignment provenance must distinguish manufacturer declaration from TetherLens derivation;
- no reversible assignment from `dual` / `double` / `twin`, a shared normalized connector spec, pair-use wording or manufacturer silence alone;
- decision-bound supporting-document traversal must stay first-party, purpose-scoped and identity-bound, must revalidate the final fetched host after redirects, and must fail closed before inherited extraction rather than becoming generic manufacturer-document crawling;
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

## Suggested fresh-chat starting point after PR #56

> Continue TetherLens from merged `main` after PR #56. Keep both portability cohorts frozen at their historical revisions: V1 is **0 A / 5 B / 3 C / 0 D** after PR #51, while V2 is **0 A / 6 B / 2 C / 0 D** against post-PR #55 `main`. V2 explicitly excludes the previously modelled Ergodyne tape/wrap ToolAttachment family; its replacement Ergodyne Squids 3001 is a fresh retractable-tether B case. The fresh 3M required-companion case confirms that `required_pairing` plus multi-component ToolAttachment assemblies already cover that architecture, while both remaining C cases — GRIPPS H01150 SnapLock and 3M 1500028 Quick Spin — expose the same non-captive handle/neck capture-fit boundary. Start by inspecting first-party installation evidence for those two products and define the smallest manufacturer-neutral fit/eligibility model before changing code. Test existing `mechanical_capture`, feature predicates/dimensions and bounded runtime verification first; do not infer fit from S/M/L/XL or nominal attachment diameter, promote non-captive features to captive, or add manufacturer/SKU-specific downstream compatibility rules.