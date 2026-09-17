# TetherLens Project Status

_Last updated: 2026-09-17_

This is the operational handoff for the current TetherLens knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file stays focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `compatibility-evidence-and-inference.md`, `feature-bound-dimensional-eligibility.md`, `attachment-method-vocabulary.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `demand-side-field-orchestration.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `portability-v5-post-pr62.md`, `portability-v6-post-feature-dimensional.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Current baseline

Merged `main` before the current PR is PR #69, `Carry evidence-bound ToolAttachment installations into field recommendations`.

PR #70, `Broaden 3M ingestion for D-Ring Cord 1500009`, is the current completed slice and merge candidate. This file is written as the post-merge handoff: after PR #70 merges, the production baseline includes both PR #69's sparse-geometry evidence boundary and PR #70's first catalogue-throughput proof over a conventional reusable ToolAttachment path.

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

PR #69 proves the exact evidence-bound fallback with Hilti SF 4-22 / retaining strap #2293133. PR #70 deliberately does **not** use that fallback for 3M 1500009 because 3M publishes enough functional topology for the ordinary reusable ToolAttachment model.

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

## Review-derived reusable provenance invariants

The PR #69 and #70 reviews reinforce several reusable rules:

1. **Product-scoped evidence belongs to the exact owner/interface it describes.** Assembly-wide membership is insufficient when several products expose similar interfaces.
2. **Executable document evidence must be model-local.** A product appearing somewhere in a combined/related document does not authorize another model's section.
3. **Evidence identity follows the documented relationship.** Repeated sources for one relationship support one logical record; distinct routes remain distinct.
4. **Primary evidence provenance is atomic.** Source URL, raw wording, evidence method and extractor metadata must remain aligned.
5. **Vendor-specific wording may produce manufacturer-specific values, but downstream reasoning should remain manufacturer-neutral.** 3M parsing may extract `Python Safety`; shared logic compares selected vs required manufacturer without a Python-Safety branch.
6. **Manufacturer prescription and physical compatibility are independent unless causal technical scope is established.** A mixed-brand route can remain technically field-verifiable while carrying contrary manufacturer-position evidence.
7. **Matching a manufacturer family is not blanket endorsement.** `appropriate <manufacturer> tether` does not prove every tether sold by that manufacturer is approved.
8. **Historical portability classifications remain historical.** Closing the 1500009 B gap does not rewrite V6.

## Current deliberate boundaries

The post-PR #70 baseline does **not** add:

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
- automatic positive endorsement for same-manufacturer combinations; or
- a replacement for the existing recommendation-session condition resolver.

Those boundaries remain deliberate.

## Next recommended slice after PR #70

The next slice should continue proving catalogue throughput, but should exercise a **different supply-side shape** rather than immediately adding another conventional ToolAttachment family branch.

Recommended inspection target:

```text
GRIPPS H01088 — Adjustable Wrist Anchor With Tool Tether
```

The frozen V6 review classified H01088 as B because GRIPPS explicitly identifies the sellable kit as containing separately identifiable recommendation components:

```text
H01067 Webbing Wrist Tether
+
H01085 Slip-On Wrist Anchor
```

The likely reusable lesson is catalogue decomposition, not a runtime `Composite` load-path type. A commercial wrapper may describe/package components without itself becoming another physical component in candidate evaluation.

Start the next slice by inspecting current GRIPPS ingestion, any existing related-product/kit relationship semantics, the H01067 and H01085 first-party evidence, current wrist-anchor installation support, and how `FieldRecommendationCatalogue` should receive the decomposed components.

The target should be the smallest evidence-backed path that proves:

```text
sellable kit identity
  -> accepted contained-product relationships
  -> exact contained product identities
  -> ordinary tether + AnchorAttachment normalization
  -> ordinary candidate composition/evaluation
```

Do not create a new composite runtime primitive unless inspection finds a real load-path or decision semantic that cannot be represented by the contained products.

If H01088 evidence turns out not to support a clean decomposition without additional catalogue work, choose another remaining V6 B throughput case rather than forcing the abstraction. The next alternatives are the FallTech 5106A5 conventional ToolAttachment family, Ergodyne 3172/19172 AnchorAttachment family, or one of the exact-product capacity-conflict cases where existing reconciliation should fail closed.

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
Continue TetherLens from merged `main` after PR #70. Keep all historical portability cohorts frozen at their existing semantic revisions: V1 is 0 A / 5 B / 3 C / 0 D, V2 is 0 A / 6 B / 2 C / 0 D, V3 is 0 A / 5 B / 3 C / 0 D, V4 is 0 A / 4 B / 4 C / 0 D, V5 is 0 A / 6 B / 2 C / 0 D, and V6 is 1 A / 7 B / 0 C / 0 D.

PR #69 establishes the sparse-geometry evidence boundary: use reusable physical/topological rules where the source supports them, but retain exact evidence-bound installation/connection relationships when manufacturer evidence establishes what works without enough geometry to infer why.

PR #70 closes the frozen 3M 1500009 V6 B case using existing generic ToolAttachment semantics: captive handle OR captive through-opening eligibility, cinch installation, 2.3 kg rated capacity and a provided D-ring interface. It also preserves 3M's Python Safety tether-family requirement on the manufacturer-position axis. The shared resolver compares accepted selected-tether manufacturer identity against the manufacturer named by the source; a mismatch becomes CONTRARY_TO_MANUFACTURER_INSTRUCTION without becoming technical incompatibility, and a same-manufacturer match is not blanket endorsement.

For the next slice, inspect GRIPPS H01088 Adjustable Wrist Anchor With Tool Tether as a catalogue-decomposition case. Determine whether the sellable kit can be represented as accepted relationships to its separately identified H01067 Webbing Wrist Tether and H01085 Slip-On Wrist Anchor, then composed through the existing tether + AnchorAttachment recommendation path without inventing a runtime Composite component.

Before changing code, inspect current GRIPPS ingestion, related-product/kit semantics, first-party evidence for all three SKUs, and existing wrist-anchor support. Identify the smallest reusable implementation slice and recommend the approach before building it.
```
