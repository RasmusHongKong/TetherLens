# TetherLens Project Status

_Last updated: 2026-09-18_

This is the operational handoff for the current TetherLens knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file stays focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `compatibility-evidence-and-inference.md`, `feature-bound-dimensional-eligibility.md`, `attachment-method-vocabulary.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `demand-side-field-orchestration.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `portability-v5-post-pr62.md`, `portability-v6-post-feature-dimensional.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Repository agent guidance

Root-level `AGENTS.md` now provides durable repository-wide guidance for AI coding agents: how to orient from `project-status.md`, preserve evidence/provenance and recommendation boundaries, distinguish vendor-specific parsing from reusable invariants, test changes, and keep documentation current. It deliberately points agents back to this file for the changing operational baseline rather than duplicating current PR/workstream state.

This is workflow/documentation guidance only. It does not change recommendation semantics, historical benchmark freezes, the current baseline, or the next recommended implementation slice.

## Current baseline

Merged `main` entering PR #74 is PR #73, `Prove GRIPPS H01067 + H01085 wrist recommendation path`.

PR #74 is the current ingestion-architecture follow-on. It does not widen recommendation authority or catalogue semantics. It centralizes the manufacturer-neutral question of whether a positive-looking local prose match is negated, excluded, prohibited or contradicted, while leaving each adapter responsible for the manufacturer-specific positive wording it recognizes.

Historical portability cohorts remain immutable at their original semantic revisions:

```text
V1  0 A / 5 B / 3 C / 0 D   after PR #51
V2  0 A / 6 B / 2 C / 0 D   against post-PR #55 main
V3  0 A / 5 B / 3 C / 0 D   PR #58 production-semantic freeze
V4  0 A / 4 B / 4 C / 0 D   PR #61 production-semantic freeze
V5  0 A / 6 B / 2 C / 0 D   post-PR #62 semantic freeze
V6  1 A / 7 B / 0 C / 0 D   PR #64 semantic freeze
```

Do not rewrite any historical answer key after later PRs close the gaps it exposed.

## Strategic direction

V6 remains the pivot signal: a materially different portability cohort produced one A case, seven B cases and no C/D pressure after the reusable feature-bound dimensional compiler landed.

Therefore:

- portability is now a periodic stress/regression audit, not the primary implementation loop;
- the primary workstreams are **catalogue throughput + demand-side MVP**;
- new ontology should be introduced only when a concrete recurring decision need proves it necessary; and
- incomplete manufacturer geometry is treated as a permanent catalogue condition, not a temporary cleanup problem.

Do not start another portability cohort merely to search for a new primitive.

## Current recommendation architecture

The recommendation core remains a reusable evidence-bound pipeline:

```text
normalized Tool / ToolAttachment / tether / anchor facts
  + accepted exact installation/connection evidence where needed
  + issuer-scoped manufacturer-position evidence where applicable
  -> candidate generation
  -> hard candidate evaluation
  -> contextual ranking/selection
  -> recommendation-session condition resolution where needed
```

Hard viability, manufacturer position and ranking remain separate axes. Ranking cannot override hard incompatibility or missing required evidence. Manufacturer support/prescription wording does not become technical incompatibility unless the source establishes a causal technical failure mode. Global exhaustion may be concluded only after the complete generated alternative set has been evaluated.

### Sparse-geometry evidence boundary

Exact geometry and dimensions remain preferred inputs when sources publish them, but they are not assumed to exist for every product family.

The governing progression is:

```text
exact geometry/dimensions where established
  -> reusable technical rule

functional/topological facts where established
  -> reusable technical rule

explicit documented relationship but insufficient reusable geometry
  -> exact evidence-bound path
```

An evidence-bound path is positive evidence for one documented relationship. It is not a generic SKU-pair compatibility rule and does not prove alternatives incompatible.

Do not reverse-engineer a `through_opening`, captive state, dimensions, ring/eye form or other physical fact merely because such a fact would explain a manufacturer's pairing.

PR #69 proves the exact evidence-bound installation fallback with Hilti SF 4-22 / retaining strap #2293133. PR #70 deliberately does **not** use that fallback for 3M 1500009 because 3M publishes enough functional topology for the ordinary reusable ToolAttachment model. PR #73 applies the same governing boundary to connection evidence: H01067/H01085 reuse every published physical/topological primitive first, then retain the exact product-scoped suitability statement only for the remaining sparse target-interface geometry.

## Demand-side baseline

PRs #65–#68 establish the catalogue-to-field boundary without adding recommendation authority to search/recognition. The field coordinator supports advisory recognition/search candidate Tool refs, mandatory explicit worker Tool confirmation, exact operational-profile selection, configuration identity such as Battery refs, fail-closed missing operational mass, session-local generic fallback, and exact handoff into the existing recommendation run.

PR #69 carries the first real Hilti SF 4-22 operational profile through the complete recommendation pipeline using an exact evidence-bound ToolAttachment installation while preserving exact binding provenance.

PR #70 adds a second real complete worker vertical using ordinary reusable ToolAttachment semantics rather than a new core exception.

## PR #70: 3M DBI-SALA 1500009 D-Ring Attachment with Cord

PR #70 closes the frozen V6 1500009 B case as catalogue/ingestion work rather than new recommendation ontology.

### Exact first-party evidence boundary

The 3M adapter now supports 1500009 as a separate family from Quick Spin while preserving exact product-detail verification. The D-Ring Cord installation manual is joined only after the exact 1500009 primary record is verified, and executable document extraction requires the official manual plus product-local `1500009` identity and D-Ring Cord section semantics.

Aggregate 3M pages and manuals without local product identity remain fail-closed.

### Existing generic ToolAttachment semantics

The accepted 3M evidence normalizes only facts the manufacturer actually establishes:

```text
attachment_selection_class = captive_feature_attachment
attachment_method_code = cinch
rated_capacity_kg = 2.3
provided interface role = tool_attachment_tether_side
provided interface type = ring
provided interface ring_form = d_ring
```

This reuses the existing captive-handle OR captive-through-opening eligibility compiler, existing `cinch` installation vocabulary, existing capacity reasoning, and existing provided-interface model.

PR #70 does not infer dimensions, add SKU-pair compatibility, or create an evidence-bound ToolAttachment installation where ordinary reusable topology is already supported.

### Manufacturer instruction remains a separate axis

The 3M manual also states that Python Safety attachment points require an appropriate Python Safety lanyard, tether or retractor for safe connection.

PR #70 preserves that statement rather than either discarding it or turning it into technical incompatibility.

The reusable split is:

```text
vendor-specific source interpretation
  -> required_tether_manufacturer = <manufacturer named by source>
  -> shared comparison against accepted selected-tether manufacturer identity
  -> mismatch: CONTRARY_TO_MANUFACTURER_INSTRUCTION
  -> match: no contrary assessment, but no automatic positive endorsement
```

For 1500009 the source-specific value is `Python Safety`. The shared resolver contains no Python-Safety-specific recommendation rule: it compares the selected manufacturer with the manufacturer required by the accepted instruction.

Important invariants:

- do not parse manufacturer identity from product refs;
- a known manufacturer mismatch may create an issuer-scoped `CONTRARY_TO_MANUFACTURER_INSTRUCTION` assessment;
- manufacturer-position evidence does not by itself change technical compatibility;
- matching the named manufacturer only removes the known mismatch and does not prove every same-brand tether is endorsed; and
- site policy may separately prohibit or warn on contrary-to-instruction configurations.

This is the concrete implementation of the existing `connection-compatibility.md` rule that manufacturer position and technical compatibility are independent.

### Complete mixed-manufacturer field vertical

PR #70 reuses the existing worker-path scaffold with:

```text
Milwaukee 48-22-7215 Tool
  -> 3M 1500009 D-Ring Cord ToolAttachment
  -> GRIPPS H01079 tether
  -> NLG 101366 belt-loop anchor
```

The selected path retains:

- Milwaukee's exact catalogued operational mass;
- installation feature `tether_ready_opening`;
- ordinary captive-feature eligibility;
- 3M assembly `3M:1500009:assembly`;
- `cinch` installation-method provenance from the 3M manual;
- GRIPPS H01079 and NLG 101366 component identity;
- unresolved connector engagement as ordinary field verification rather than invented compatibility; and
- the 3M-issued contrary-to-manufacturer-instruction assessment on the mixed-brand Tool-side connection.

The candidate remains technically usable with conditions. The manufacturer assessment is retained for policy/user transparency rather than smuggled into the hard technical result.

## PR #72: GRIPPS catalogue decomposition and wrist components

PR #72 tests the V6 H01088 case as a catalogue-decomposition problem rather than a new recommendation-core shape.

### Commercial kit relationships stay outside the load path

The technical schema already defined `declared_relationship_type = kit_relationship`; PR #72 adds the small executable resolver needed to bind accepted relationship claims to exact catalogue product refs.

The boundary is:

```text
sellable kit/wrapper identity
  -> accepted declared relationships
  -> exact contained-product refs
  -> contained products normalized independently
  -> ordinary Tether / ToolAttachment / AnchorAttachment runtime options
```

The sellable wrapper uses catalogue-only `ProductType.KIT` identity so its relationships have an exact owner. `KIT` has no candidate/load-path subtype. A kit relationship therefore does not create `ProductType.COMPOSITE`, a synthetic candidate component, or a generic compatibility rule.

Relationship resolution also fails closed on identity: accepted raw relationship claims may remain when the related product is not yet mapped, but executable catalogue composition requires an explicit identifier-to-product-ref mapping. Product identity is never reconstructed from SKU syntax, names or URLs.

### H01088 is deliberately not forced recommendation-ready

The current GRIPPS H01088 product page explicitly publishes Kit Contents rows naming H01067 Webbing Wrist Tether and H01085 Slip-On Wrist Anchor.

The same exact H01088 page describes the wrapper as an adjustable wrist anchor secured with hook-and-loop/Velcro semantics, while GRIPPS separately distinguishes H01085 as the Slip-On family. PR #72 therefore preserves the stated H01067/H01085 kit relationship evidence but emits `KIT_COMPONENT_IDENTITY_CONFLICT` and blocks recommendation-ready decomposition.

TetherLens does **not** silently replace H01085 with H01086 merely because H01086 appears more consistent with the wrapper description. Nor does the family-level H01085 row authorize choosing an arbitrary H01085-S/M/L variant; exact variant identity remains unresolved until supported by evidence.

Related-product cards remain non-evidence for kit membership; only an explicitly labelled Kit Contents table inside the exact product's bounded page region may emit `kit_relationship` claims. The same product-local boundary applies to the adjustable-versus-slip-on conflict check, so sibling/cross-sell copy cannot create either kit membership or a readiness conflict. The conflict check is GRIPPS kit-semantic rather than H01088-SKU-specific: any exact kit page with the same contradictory wrapper/component evidence fails closed.

### H01067 reuses existing tether and assignment semantics

The separately catalogued H01067 Webbing Wrist Tether normalizes through existing primitives:

```text
rated_capacity_kg = 2.5
connection_count = 2
endpoint 1 = carabiner
endpoint 2 = carabiner
shared connector = single-action + swivel
endpoint roles = unknown
```

When the same exact-product, product-local evidence also affirmatively establishes one same-construction carabiner pair plus undifferentiated hand-tool-to-glove/wrist-anchor use, the adapter emits the existing `derived_endpoint_equivalence` / `reversible_tool_anchor_pair` relation. Negated construction/use wording is not promoted into positive evidence, and any explicit dedicated/designated endpoint wording vetoes the derivation regardless of whether the directional phrase appears before or after the word `carabiner`. The endpoints remain `TetherSide.UNKNOWN`; the relation authorizes bounded assignments without mutating intrinsic roles.

That assignment evidence does not establish engagement with any particular anchor interface.

### H01085 adds only the missing physical installation mechanism

H01085 uses the existing `wrist` PrimaryAnchorFeature but requires a distinct mechanism: the product is slipped over the hand onto the wrist rather than fastened around it.

PR #72 therefore adds the manufacturer-neutral:

```text
AnchorInstallationMethod.SLIP_ON
```

The current H01085 path is:

```text
method = slip_on
feature_kind = wrist
rated_capacity_kg = 2.5
provided interface role = anchor_attachment_tether_side
provided interface type = unknown
```

Small/Medium/Large labels are not converted into numeric wrist-fit geometry. Slip-on installation and the H01067 suitability relationship require affirmative product-local evidence: a prohibition such as `do not ... slip it on` does not create an installation rule, and `not suitable for ... H01067` does not create an endorsement. A positive H01067 suitability statement is retained as an `explicitly_endorsed` catalogue relationship, not automatically promoted into a generic physical compatibility rule.

PR #73 additionally allows that same affirmative product-local statement to resolve as an exact product-scoped connection declaration only when H01067 and the concrete H01085 variant are explicitly mapped to stable product refs and the H01085 source provides unambiguous identity-bearing SKU evidence for that exact variant. The declaration carries the exact product relationship only; H01067 connector facts and H01085 interface facts remain on their independently sourced component records. The H01085 tether-side interface remains `unknown`; no ring, eye, opening, dimension or captive state is inferred.

## PR #73: GRIPPS H01067 + H01085 wrist recommendation path

PR #73 proves the component-local recommendation path directly rather than making a commercial kit the executable object.

The normalized path is:

```text
H01067 Tether
  -> existing two-carabiner connector facts
  -> existing reversible endpoint-assignment evidence

H01085 exact variant AnchorAttachment
  -> slip_on wrist installation
  -> exact selected wrist feature binding
  -> tether-side role retained with interface type = unknown

product-local H01085 suitability statement
  -> exact H01067 + exact H01085-variant connection declaration
  -> existing manufacturer-declared connection context

ordinary TetherOption + AnchorPathOption
  -> candidate generation
  -> hard evaluation
  -> deterministic selection
```

The exact declaration is intentionally narrower than a generic compatibility rule. It becomes executable only when the source product identifier `H01067` and a concrete H01085 variant identifier both resolve to stable catalogue refs **and** the bounded component evidence contains unambiguous identity-bearing SKU evidence for that target variant. A bare sibling mention such as `also available as H01085-M`, a page region containing several identity-bearing H01085 variants, family-only `H01085`, missing mappings, cross-sell copy, negated suitability, in-match exclusions such as `not H01067`, contradictory nearby prohibitions, and nearby declarative conflicts such as `H01067 is incompatible/unsuitable` all fail closed. At runtime, whatever target predicates an exact product-scoped declaration retains must collectively select exactly one interface owned by that target product; product-only and partially constrained declarations both fail closed when more than one owned interface remains possible.

The end-to-end regression uses the explicitly identified H01085-S component and proves that runtime candidate components are exactly H01067 + H01085-S. No `KIT`, wrapper or synthetic `Composite` identity participates in the load path. H01067's reversible assignment and connector/interface facts remain sourced from H01067 itself; H01085's anchor-installation binding and tether-side interface remain sourced from H01085. The product-scoped declaration contributes only the documented pair authority used by the existing `MANUFACTURER_DECLARED` basis. A kit row naming H01085-M remains catalogue evidence; it does not itself authorize the H01085-M connection path.

This does not claim that GRIPPS kit membership explains compatibility. Kit evidence remains catalogue/system-architecture context; component-local evidence and reusable primitives determine recommendation behavior.

## PR #74: shared local evidence context

PR #74 turns the repeated contradiction hardening exposed by PR #73 into a bounded shared ingestion invariant rather than copying another set of vendor regexes.

The new shared evidence-context layer owns:

- HTML block/clause rendering that preserves inline text without joining separate semantic blocks;
- punctuation-bounded sentence context around a positive match;
- prefix and immediate trailing negation;
- caller-bound in-match exclusions;
- same-sentence or immediately adjacent action prohibitions;
- nearby negative relation assertions such as `not suitable`, `not compatible`, `unsuitable` and `incompatible`;
- common contractions and rhetorical conjunctions; and
- negative-looking but non-contradictory wording such as `without removing gloves` and additive `not only`.

The adapter still owns the positive source grammar and supplies the relationship referents that a contradiction must concern. Shared code therefore contains no GRIPPS SKU, NLG product name, D-ring compatibility rule or manufacturer-specific recommendation branch.

The first migrations are deliberately narrow:

```text
GRIPPS H01085 page
  -> adapter-specific H01067 suitability pattern
  -> shared local contradiction check
  -> existing exact relationship / connection claims

NLG Quick Clip evidence
  -> adapter-specific Quick Clip -> D-ring positive patterns
  -> shared block + sentence context
  -> shared local contradiction check
  -> existing generic connection declaration
```

GRIPPS-specific in-match exclusion, adjacent prohibition and negative-relation regexes are removed from that pairing path. NLG declared compatibility no longer maintains a separate assertion/prohibition grammar. The existing shared HTML clause renderer also moves out of the connector-mechanism implementation so other prose extractors can depend on an evidence-context module rather than a feature-specific parser.

A table-driven shared contradiction matrix covers prefix negation (including `no`), in-match exclusion, entity-first negation, adjacent direct and rhetorical prohibitions, negative relation adjectives, contractions, trailing predicate negation, hard block boundaries, `not only`, and harmless `without removing gloves`. Existing GRIPPS and NLG adapter regressions continue to prove end-to-end claim behavior.

Review hardening keeps the `without` distinction at the correct layer: harmless adjunct wording remains acceptable in shared context, while NLG's positive Quick Clip -> D-ring parser rejects relational forms such as `without attachment to a D Ring` because that grammar changes the relationship the adapter is asserting.

The same review cycle makes predicate ownership explicit in the shared layer. An introductory negative predicate such as `No special tools are required, ...` does not negate a later independent positive relationship, while an immediately following prohibition still fails closed when a short explicit subject intervenes, for example `but it must not be used that way`. Compound subjects preserve their governing negation, so `No gloves and wrist anchors are suitable ...` remains contrary evidence. Local contradiction handling therefore stays bounded by grammatical ownership as well as physical text distance.

NLG's positive declaration grammar is also kept sentence-local: the broad designed-to-anchor form may not borrow a D-ring from a following sentence. Its local relational-`without` guard covers qualified denial forms such as `without ever being attached to` and `without needing to connect it to`, while harmless wording about working without removing gloves remains admissible.

This is not a wholesale regex framework. `nlg_compat._match_is_negated()`, the Quick Clip trigger mechanism's trigger-specific negation, and the anchor D-ring parser's predicate-ownership rules remain local until their evidence boundaries are compared and shown to be genuinely equivalent.

## Review-derived reusable provenance invariants

The PR #69, #70, #72, #73 and #74 workstreams reinforce several reusable rules:

1. **Product-scoped evidence belongs to the exact owner/interface it describes.** Assembly-wide membership is insufficient when several products expose similar interfaces.
2. **Executable document evidence must be model-local.** A product appearing somewhere in a combined/related document does not authorize another model's section.
3. **Evidence identity follows the documented relationship.** Repeated sources for one relationship support one logical record; distinct routes remain distinct.
4. **Primary evidence provenance is atomic.** Source URL, raw wording, evidence method and extractor metadata must remain aligned.
5. **Vendor-specific wording may produce manufacturer-specific values, but downstream reasoning should remain manufacturer-neutral.** 3M parsing may extract `Python Safety`; shared logic compares selected vs required manufacturer without a Python-Safety branch.
6. **Manufacturer prescription and physical compatibility are independent unless causal technical scope is established.** A mixed-brand route can remain technically field-verifiable while carrying contrary manufacturer-position evidence.
7. **Matching a manufacturer family is not blanket endorsement.** `appropriate <manufacturer> tether` does not prove every tether sold by that manufacturer is approved.
8. **Product-detail URLs still need section-local evidence boundaries.** Exact URL/product verification does not authorize sibling cards, Related Products, later product fragments or their Kit Contents as evidence for the requested product.
9. **Positive-looking text with local contradictory grammar is contrary evidence, not positive evidence.** Prefix/in-match negation, adjacent prohibitions and adjacent negative relation assertions such as `not suitable`, `not compatible`, `unsuitable` or `incompatible` must fail closed rather than become installation, relationship or construction authority. PR #74 centralizes this invariant for the first two free-prose relationship paths while preserving specialized parser semantics where equivalence has not yet been established.
10. **Directional semantics are not tied to one grammatical order.** Dedicated/designated endpoint wording vetoes reversible endpoint derivation whether the role phrase appears before or after the connector noun.
11. **Historical portability classifications remain historical.** Closing later catalogue gaps does not rewrite V6.

## Current deliberate boundaries

The post-PR #74 baseline does **not** add:

- image recognition or computer-vision inference;
- fuzzy Tool identity acceptance;
- search-derived confidence scores as recommendation authority;
- persistent database/repository querying;
- automatic Battery recognition;
- free-form worker safety-fact inference;
- anchorage recognition;
- inventory optimization;
- user-facing natural-language recommendation generation;
- generic cross-product compatibility inference;
- confidence scoring for inferred compatibility rules;
- automatic promotion of repeated manufacturer pairings into technical rules;
- global mixed-manufacturer exclusion;
- manufacturer identity inference from SKU/product-ref naming conventions;
- automatic positive endorsement for same-manufacturer combinations;
- a replacement for the existing recommendation-session condition resolver;
- a runtime `Composite`/kit load-path component (catalogue-only `ProductType.KIT` is identity metadata, not a candidate component); or
- silent correction of contradictory manufacturer kit composition.

Those boundaries remain deliberate.

## Next recommended workstream after PR #74

PR #74 closes the current ingestion-refinement slice at a useful MVP boundary. The shared evidence-context layer now handles the reusable contradiction/predicate-ownership cases exposed by the migrated GRIPPS and NLG relationship paths, with full adapter regressions and frozen portability expectations still passing.

There are still nearby local parser guards that could be compared with the shared helper, but that work is now **deferred cleanup rather than the highest-value MVP slice**. Do not migrate `nlg_compat._match_is_negated()`, Quick Clip mechanism negation, anchor D-ring predicate ownership, or other local grammar merely for symmetry. Revisit them when:

- a concrete ingestion defect is observed in a real source;
- a second parser proves an identical reusable evidence boundary; or
- the local duplication materially blocks catalogue throughput or maintenance.

The next primary workstream is the **worker-facing MVP vertical**. The recommendation engine, recommendation-run/session layers and demand-side field coordinator already provide the structured decision path; the missing product-value layer is the field interaction that helps a worker get from a physical Tool to that path.

The smallest useful end-to-end target should be:

```text
camera/image input
    -> advisory Tool candidate refs
    -> explicit worker Tool confirmation
    -> operational profile selection where required
    -> smallest material context-question flow
    -> existing run_field_recommendation()
    -> structured selected/no-suitable result presentation
    -> lightweight worker feedback
```

Image recognition remains advisory. It must never confirm Tool identity, select a Battery/profile, invent catalogue facts, or bypass the existing recommendation-readiness and fail-closed boundaries.

Prefer a thin worker-facing surface over a new recommendation abstraction. Reuse the existing `candidate_tool_refs`, confirmation/profile requirements, recommendation run, session resolution and field-summary models rather than duplicating them in UI/application code.

## Ingestion and catalogue work during the worker-facing phase

Ingestion should now be **scenario-driven rather than refinement-driven**.

Continue catalogue work when a worker-facing scenario exposes a real missing dependency, such as:

- a pilot Tool is not discoverable because exact identity is missing;
- an operational Tool/Battery profile is incomplete;
- a required ToolAttachment/Tether/AnchorAttachment path lacks recommendation-ready facts;
- a selected field scenario exposes a genuine parser defect; or
- another product is needed to exercise meaningful recommendation variation.

Do not broaden adapters, consolidate regexes, or add catalogue SKUs only to make ingestion look more complete. FallTech 5106A5 / Ergodyne 3172/19172 and similar throughput items remain useful backlog candidates, but they should be pulled by pilot-scenario value rather than precede the worker-facing MVP vertical by default.

Historical portability cohorts remain frozen throughout this work.

## Guardrails that must remain true

- Do not introduce manufacturer/SKU branches downstream of ingestion/resolution unless no reusable semantic representation exists and the exception is explicitly justified.
- Manufacturer-specific strings extracted from source evidence are data, not permission for manufacturer-specific recommendation logic.
- Missing evidence fails closed; do not infer geometry, direction, compatibility, capacity or installation suitability from absence of contrary evidence.
- Exact manufacturer-documented relationships may be retained when geometry is incomplete, but they must stay narrowly scoped evidence rather than becoming generic rules by convenience.
- Do not convert qualitative marketing language into numeric fit envelopes.
- Keep every feature-bound predicate on one concrete feature instance.
- Keep manufacturer provenance separate from exact product/variant identity.
- Bind product-scoped manufacturer connection evidence to the exact product that owns the evaluated interface.
- Bound flattened multi-product or multi-model evidence to the requested identity before parsing sibling-specific fields.
- Preserve the primary source/evidence tuple atomically when merging equivalent claims from multiple sources.
- Preserve manufacturer prescription on the manufacturer-assessment axis; promote it to technical incompatibility only when accepted evidence establishes causal technical scope.
- Omission from a manufacturer compatibility list remains `unknown`, not `incompatible`.
- Keep operational mass configuration-specific when the Tool requires an installed configuration.
- Search/recognition remains advisory until the worker explicitly confirms Tool identity.
- Preserve exact candidate, component, feature, endpoint, installation-binding and source-product provenance through generation, evaluation, ranking and field output.
- Historical portability cohorts V1–V6 remain frozen at their original semantic revisions.

## Suggested opening prompt for the next chat

```text
Continue TetherLens from merged main after PR #74. Keep all historical portability cohorts frozen at their existing semantic revisions: V1 is 0 A / 5 B / 3 C / 0 D, V2 is 0 A / 6 B / 2 C / 0 D, V3 is 0 A / 5 B / 3 C / 0 D, V4 is 0 A / 4 B / 4 C / 0 D, V5 is 0 A / 6 B / 2 C / 0 D, and V6 is 1 A / 7 B / 0 C / 0 D.

PR #74 establishes the manufacturer-neutral local evidence-context/contradiction layer and closes the current ingestion-refinement slice. Positive manufacturer grammar remains adapter-specific; shared code owns only bounded reusable evidence-context semantics. Remaining parser consolidation is deferred unless a concrete source defect or genuinely reusable second case justifies it.

The next highest-value MVP workstream is worker-facing identification and interaction. Start by inspecting demand-side-field-orchestration.md, recommendation-session.md, the existing run_field_recommendation() implementation/tests, and current repository structure. Define the smallest end-to-end mobile-first vertical that can accept a Tool image, produce advisory catalogue candidate refs, require explicit worker confirmation, resolve any required operational profile/context inputs, invoke the existing field recommendation boundary unchanged, and present the structured result plus lightweight feedback.

Do not redesign the recommendation engine or weaken catalogue evidence/readiness rules. Image recognition is only an upstream candidate-ref producer; it must not confirm identity or invent safety-critical facts. Pull additional ingestion/catalogue work only when the chosen field scenario exposes a real readiness gap.
```
