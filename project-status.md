# TetherLens Project Status

_Last updated: 2026-09-18_

This is the operational handoff for the current TetherLens knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file stays focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `compatibility-evidence-and-inference.md`, `feature-bound-dimensional-eligibility.md`, `attachment-method-vocabulary.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `demand-side-field-orchestration.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `portability-v5-post-pr62.md`, `portability-v6-post-feature-dimensional.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Repository agent guidance

Root-level `AGENTS.md` now provides durable repository-wide guidance for AI coding agents: how to orient from `project-status.md`, preserve evidence/provenance and recommendation boundaries, distinguish vendor-specific parsing from reusable invariants, test changes, and keep documentation current. It deliberately points agents back to this file for the changing operational baseline rather than duplicating current PR/workstream state.

This is workflow/documentation guidance only. It does not change recommendation semantics, historical benchmark freezes, the current baseline, or the next recommended implementation slice.

## Current baseline

Merged `main` entering PR #73 is PR #72, `Decompose GRIPPS wrist kits into existing catalogue components`.

PR #73 is the current follow-on slice. It keeps kits outside the runtime load path and carries the separately catalogued GRIPPS H01067 tether + an exactly evidenced H01085 variant through the ordinary recommendation path. Reusable H01067 connector/assignment semantics and H01085 slip-on installation remain primary; the product-local H01067 suitability statement supplies only the exact product-scoped connection authority that cannot be generalized because H01085 tether-side geometry is unpublished. The current vertical uses H01085-S because the bounded component evidence explicitly identifies that SKU.

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
## Review-derived reusable provenance invariants

The PR #69, #70, #72 and #73 workstreams reinforce several reusable rules:

1. **Product-scoped evidence belongs to the exact owner/interface it describes.** Assembly-wide membership is insufficient when several products expose similar interfaces.
2. **Executable document evidence must be model-local.** A product appearing somewhere in a combined/related document does not authorize another model's section.
3. **Evidence identity follows the documented relationship.** Repeated sources for one relationship support one logical record; distinct routes remain distinct.
4. **Primary evidence provenance is atomic.** Source URL, raw wording, evidence method and extractor metadata must remain aligned.
5. **Vendor-specific wording may produce manufacturer-specific values, but downstream reasoning should remain manufacturer-neutral.** 3M parsing may extract `Python Safety`; shared logic compares selected vs required manufacturer without a Python-Safety branch.
6. **Manufacturer prescription and physical compatibility are independent unless causal technical scope is established.** A mixed-brand route can remain technically field-verifiable while carrying contrary manufacturer-position evidence.
7. **Matching a manufacturer family is not blanket endorsement.** `appropriate <manufacturer> tether` does not prove every tether sold by that manufacturer is approved.
8. **Product-detail URLs still need section-local evidence boundaries.** Exact URL/product verification does not authorize sibling cards, Related Products, later product fragments or their Kit Contents as evidence for the requested product.
9. **Positive-looking text with local contradictory grammar is contrary evidence, not positive evidence.** Prefix/in-match negation, adjacent prohibitions and adjacent negative relation assertions such as `not suitable`, `not compatible`, `unsuitable` or `incompatible` must fail closed rather than become installation, relationship or construction authority. The exact grammar is currently adapter-local and is the next consistency target.
10. **Directional semantics are not tied to one grammatical order.** Dedicated/designated endpoint wording vetoes reversible endpoint derivation whether the role phrase appears before or after the connector noun.
11. **Historical portability classifications remain historical.** Closing later catalogue gaps does not rewrite V6.

## Current deliberate boundaries

The post-PR #73 baseline does **not** add:

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

## Next recommended slice after PR #73

PR #73 closes the useful GRIPPS wrist-component proof without making a kit executable. H01088 remains unresolved until GRIPPS resolves its contradictory component identity, and no further kit-specific work is required merely to demonstrate runtime composition.

The review cycle exposed a higher-value ingestion-consistency gap before the next catalogue-throughput case: affirmative/negative local evidence grammar is currently implemented several times across GRIPPS and NLG. GRIPPS now has product-specific guards for prefix/in-match exclusions, adjacent prohibitions and declarative contradictions; `nlg_compat.py` has a separate `_match_is_negated()` helper; `nlg_declared_compatibility.py` independently implements prefix/post-relation guards; and connector-mechanism parsing has another local negation check.

The next highest-value slice is therefore a **manufacturer-neutral local evidence-context/contradiction layer**. Keep manufacturer-specific positive evidence patterns in their adapters, but centralize the reusable questions about the matched evidence context:

- clause/sentence/block boundaries around a positive match;
- prefix, in-match and immediate trailing negation;
- adjacent action prohibitions;
- adjacent negative relation assertions such as `not suitable`, `not compatible`, `unsuitable` and `incompatible`;
- contractions and rhetorical conjunctions; and
- harmless negative wording such as `without removing gloves` that must not veto otherwise positive evidence.

Start by migrating the GRIPPS H01085/H01067 relationship and NLG Quick Clip -> D-ring declared compatibility to the shared helper with one table-driven contradiction matrix. Then compare `nlg_compat._match_is_negated()` and connector-mechanism negation semantics and consolidate only where their evidence boundaries genuinely match. Do not attempt a wholesale rewrite of adapters that do not perform this kind of free-prose relationship extraction.

Historical portability cohorts remain frozen throughout this refactor. After the shared evidence-context layer is stable, return to FallTech 5106A5 / Ergodyne 3172/19172 catalogue throughput.

## Catalogue throughput in parallel

Continue increasing catalogue coverage specifically to unlock realistic field scenarios and reusable manufacturer/family ingestion, not for breadth alone.

High-value throughput work includes:

- reusable manufacturer-family source discovery/acquisition;
- exact Tool/product/variant identity binding;
- operational Tool/Battery profile construction;
- conflict/readiness handling for contradictory first-party facts;
- model/section-local manufacturer-document extraction;
- product-family adapter broadening;
- decomposition of sellable kits into recommendation components; and
- ingestion of the physical, functional and relationship facts actually required by demand-side sessions.

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
Continue TetherLens from PR #73 after it is merged to main. Keep all historical portability cohorts frozen at their existing semantic revisions: V1 is 0 A / 5 B / 3 C / 0 D, V2 is 0 A / 6 B / 2 C / 0 D, V3 is 0 A / 5 B / 3 C / 0 D, V4 is 0 A / 4 B / 4 C / 0 D, V5 is 0 A / 6 B / 2 C / 0 D, and V6 is 1 A / 7 B / 0 C / 0 D.

PR #73 proves the component-local GRIPPS H01067 + exact H01085-variant recommendation path while retaining sparse target geometry as exact product-scoped connection authority. Its review cycle also exposed a broader ingestion-consistency problem: local affirmative/negative evidence context is implemented separately in GRIPPS, nlg_compat.py, nlg_declared_compatibility.py and connector-mechanism parsing.

Before returning to catalogue throughput, inspect those ingestion paths and define the smallest manufacturer-neutral local evidence-context/contradiction helper. Manufacturer-specific adapters should continue to own the positive facts they are looking for; shared infrastructure should only decide whether a positive-looking match is locally negated, excluded or contradicted, while preserving evidence boundaries.

Cover the learned grammar with table-driven tests: prefix negation, in-match exclusions, entity-first negation, adjacent imperative prohibitions, not suitable/not compatible, unsuitable/incompatible, contractions, rhetorical conjunctions, clause/sentence/block boundaries, and harmless negative wording such as without removing gloves.

Migrate GRIPPS H01085/H01067 and NLG Quick Clip -> D-ring declared compatibility first. Then compare nlg_compat._match_is_negated() and connector-mechanism negation behavior and consolidate only where the semantics genuinely match. Do not turn this into a wholesale rewrite of adapters that do not perform free-prose relationship extraction, and do not change historical portability expectations.

Recommend the smallest reusable implementation slice after inspecting current main, project-status.md, the relevant adapters/tests and existing ingestion guidance.
```
