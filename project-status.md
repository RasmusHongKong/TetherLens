# TetherLens Project Status

_Last updated: 2026-09-17_

This is the operational handoff for the current TetherLens knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file stays focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `compatibility-evidence-and-inference.md`, `feature-bound-dimensional-eligibility.md`, `attachment-method-vocabulary.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `demand-side-field-orchestration.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `portability-v5-post-pr62.md`, `portability-v6-post-feature-dimensional.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Current baseline

PR #69, `Carry evidence-bound ToolAttachment installations into field recommendations`, is merged into `main` at:

```text
ae0efac76ee0e42c4f9ddd0e1e01b376c06869ae
```

PR #69 carries one real Hilti SF 4-22 operational profile through the complete ordinary recommendation pipeline while preserving sparse-evidence boundaries. It does not rewrite historical portability semantics, hard compatibility/capacity rules, contextual ranking, recommendation-session semantics, or mixed-manufacturer alternatives.

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
  -> candidate generation
  -> hard candidate evaluation
  -> contextual ranking/selection
  -> recommendation-session condition resolution where needed
```

Hard viability and ranking remain separate. Ranking cannot override hard incompatibility or missing required evidence. Global exhaustion may be concluded only after the complete generated alternative set has been evaluated.

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

See `compatibility-evidence-and-inference.md` for the normative evidence/inference model.

### Tool-side installation

Reusable ToolAttachment eligibility binds one concrete `ToolInterfaceFeature`. Feature kind, captive state, dimensions, attributes and other feature-local predicates in that path must all be satisfied by the same feature instance.

PR #64 added manufacturer-neutral compilation of accepted feature-bound dimensional fit evidence through:

```text
attachment_eligibility.feature_kind
attachment_eligibility.dimension.<code>
```

with explicit ordered comparison direction. Split-source envelope synthesis, conflicting fit subjects and unsupported inference remain fail-closed.

PR #69 adds a separate exact evidence-bound installation path for accepted cases where the manufacturer establishes **what installs where** but does not publish enough geometry for a reusable eligibility rule.

### Anchor-side installation

The reusable path remains:

```text
PrimaryAnchorFeature
  -> AnchorAttachment installation eligibility
  -> exact AnchorInstallationBinding
  -> installed AnchorAttachment tether-side interface
  -> ordinary tether-endpoint compatibility
```

Current proven primary-anchor feature vocabulary includes:

```text
belt
beam
rail
wrist
bucket_lip
```

Current proven anchor installation methods include:

```text
wrap
cinch
thread_over
fasten_around
hook_on
```

Anchor installation eligibility remains distinct from tether-to-anchor connection compatibility.

## Demand-side baseline through PR #68

PRs #65–#68 establish the catalogue-to-field boundary without adding recommendation authority to search/recognition.

The field coordinator supports:

- advisory recognition/search candidate Tool refs;
- mandatory explicit worker Tool confirmation;
- exact operational-profile selection where several profiles exist;
- automatic selection when exactly one profile exists;
- installed configuration identity such as Battery refs;
- fail-closed missing operational mass;
- explicit session-local generic profile fallback; and
- exact handoff of the normalized Tool plus all supplied tether, ToolAttachment and anchor alternatives to `run_recommendation()`.

PR #67 supplies lexical catalogue Tool search as a real producer of `candidate_tool_refs`, but a search hit cannot confirm Tool identity.

PR #68 resolves accepted catalogue operational-profile mass claims against explicit `OperationalProfileDescriptor` configuration identity. It does not infer Battery identity from profile refs, URLs, SKU conventions or mass arithmetic.

The first real proof is Hilti SF 4-22 `2253847` with B 22-55 and B 22-85. Selecting B 22-85 retains the exact configured mass and configuration-product identity required by load reasoning.

## PR #69: evidence-bound ToolAttachment installation

PR #69 closes the remaining Hilti recommendation-readiness gap without inventing installation geometry.

### Exact installation evidence

`ToolAttachmentInstallationBinding` represents positive manufacturer evidence that one ToolAttachment product installs at one exact resolved Tool feature:

```text
ToolAttachmentInstallationBinding
  binding_id
  tool_ref
  source_product_ref
  installation_feature_id
  issuer_manufacturer
  scope
  source_urls
```

This object is intentionally separate from generic `AttachmentEligibility` rules.

`EvidenceBoundToolAttachmentAssemblyOption` remains separate from ordinary geometry-backed `ToolAttachmentAssemblyOption` so exact manufacturer evidence cannot silently become a reusable technical rule.

At `run_recommendation()` the exact accepted binding is composed against the already-resolved Tool feature through an execution-local projection into the ordinary generator. The original binding is retained separately in `CandidateToolBinding`; the projection is never persisted or reused as generic compatibility.

### Conservative Hilti normalization

The current SF 4-22 evidence establishes a manufacturer-defined location described as `installation openings for accessories`, but does not establish its exact physical form.

Current normalized Tool feature:

```text
feature_id = accessory_installation_openings
feature_kind = other
feature_role = accessory_mount
captive_state = unknown
location_description = "installation openings for accessories"
```

Do **not** normalize this evidence to `through_opening`, `captive`, ring/eye form or invented dimensions.

The retaining strap #2293133 provides only the functional tether-side interface established by its product evidence:

```text
interface_id = tether_attachment_point
role = tool_attachment_tether_side
interface_type = attachment_point
```

Hilti's #2261970 tether-to-#2293133 retaining-strap instruction is retained as manufacturer-declared connection evidence scoped to those exact products. Product scope limits the positive manufacturer evidence; it is not a generic technical exclusion of other tethers/attachments.

### Complete field vertical

The PR proves:

```text
catalogue search
  -> explicit SF 4-22 confirmation
  -> B 22-55 / B 22-85 profile selection
  -> exact evidence-bound retaining-strap installation
  -> ordinary load + connection evaluation
  -> deterministic selection
  -> RECOMMENDED_WITH_CONSTRAINTS
```

For the B 22-85 route the selected recommendation retains:

- exact Tool and Battery profile/configuration identity;
- exact operational mass;
- attachment assembly `Hilti:2293133:assembly`;
- exact installation feature `accessory_installation_openings`;
- exact installation binding provenance;
- tether `Hilti:2261970`;
- manufacturer-declared Tool-side tether/strap connection;
- runtime verification on the unresolved anchor-side connection; and
- ordinary component capacity checks.

The documented Hilti route does not suppress a separately geometry-eligible ToolAttachment competitor.

## Review-derived reusable provenance invariants

PR #69 review reinforced reusable evidence rules that apply beyond Hilti.

1. **Product-scoped connection evidence belongs to the exact target interface owner.** Assembly-wide product membership is insufficient when several selected components expose similar interfaces.
2. **Multi-product evidence-bound assemblies require complete interface ownership.** Single-product ownership may be inferred; ambiguous multi-product ownership fails closed.
3. **Executable document evidence must be model-local.** A model appearing somewhere in a combined manual does not authorize another model's installation section.
4. **Enumerate all safely scoped model sections.** An incomplete contents/intro entry must not hide a later complete section, and distinct complete routes may coexist.
5. **Evidence-record identity follows the documented relationship.** Different product routes use different semantic subjects; repeated sources for the same route support one logical relationship.
6. **Primary evidence provenance is atomic.** `source_url`, raw wording, evidence method and extractor metadata must remain aligned. Later equivalent artifacts may become supporting sources but must not steal the primary URL while leaving another source's wording attached.
7. **Duplicate evidence-bound assembly identities are invalid.** Do not let candidate-ID deduplication hide catalogue ambiguity.

## Current deliberate boundaries

The PR #69 baseline does **not** add:

- image recognition or computer-vision inference;
- fuzzy Tool identity acceptance;
- search-derived confidence scores as recommendation authority;
- persistent database/repository querying;
- automatic Battery recognition;
- configuration-relationship inference from profile IDs, source URLs or mass arithmetic;
- free-form worker safety-fact inference;
- anchorage recognition;
- inventory optimization;
- user-facing natural-language recommendation generation;
- cross-product compatibility inference;
- confidence scoring for inferred compatibility rules;
- automatic promotion of repeated manufacturer pairings into technical rules;
- configuration-component/assembled-configuration feature ownership beyond current exact selected-component interface ownership;
- global mixed-manufacturer exclusion; or
- a replacement for the existing recommendation-session condition resolver.

Those boundaries remain deliberate.

## Next recommended slice after PR #69

The next slice should prove that the mature reusable semantics now buy us **faster catalogue expansion**, rather than immediately adding another abstraction.

The recommended target is:

```text
3M DBI-SALA 1500009 — D-Ring Attachment with Cord
```

V6 already classified this product as a catalogue/ingestion gap rather than a missing recommendation primitive. Manufacturer evidence describes a loop passed through a pre-drilled hole or closed handle and choked off, creating a D-ring attachment point with a 5 lb capacity. Those semantics map onto capabilities already established in the current model:

```text
captive through-opening OR captive handle eligibility
  + cinch/choke installation
  + rated capacity
  + provided D-ring tether interface
```

The implementation goal should therefore be:

```text
real 3M manufacturer evidence
  -> broadened 3M family ingestion for 1500009
  -> existing generic ToolAttachment normalization
  -> existing feature-bound eligibility
  -> existing cinch/choke installation semantics
  -> provided D-ring interface
  -> ordinary candidate generation/evaluation
  -> one complete worker-facing recommendation
```

Prefer a mixed-manufacturer complete vertical if the existing catalogue contains a Tool/tether/anchor combination whose accepted facts genuinely support it. Do not manufacture a mixed-brand case merely to demonstrate one.

The key success criterion is **no new compatibility ontology unless inspection reveals a genuine missing reusable semantic**. In particular:

- do not turn the 3M product into a SKU-pair recommendation rule;
- do not add an evidence-bound installation path if published geometry already supports ordinary reusable eligibility;
- preserve exact manufacturer evidence and source scope;
- keep Tool feature predicates bound to one concrete feature instance; and
- let the existing generator/evaluator/selector do the downstream work wherever possible.

Start by inspecting the frozen V6 1500009 case, the current 3M adapter (currently Quick-Spin-specific), existing ToolAttachment eligibility/method/interface resolvers, current catalogue candidates for a complete field vertical, and available first-party 3M evidence. Recommend the smallest reusable slice before changing code.

Do not immediately generalize the Hilti relationship into a physical rule. One documented route remains insufficient evidence for `through_opening`, captive state, dimensions or a broader family rule.

After the 3M vertical, use what it teaches us to choose between:

- another catalogue-backed complete vertical;
- a genuinely recurring sparse-geometry/evidence-bound case;
- a demand-side context question such as required working reach once multiple real candidate sets make it decision-relevant; or
- a new inference/provenance abstraction only if a concrete case requires it.

Image recognition can later produce the same `candidate_tool_refs` contract when a curated pilot image set is ready. It should not bypass the confirmation boundary.

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

V6 B cases remain useful throughput candidates, but they should not drive new recommendation primitives unless implementation reveals a genuine reusable decision gap.

## Guardrails that must remain true

- Do not introduce manufacturer/SKU branches downstream of ingestion/resolution unless no reusable semantic representation exists and the exception is explicitly justified.
- Missing evidence fails closed; do not infer geometry, direction, compatibility, capacity or installation suitability from absence of contrary evidence.
- Exact manufacturer-documented relationships may be retained when geometry is incomplete, but they must stay narrowly scoped evidence rather than becoming generic rules by convenience.
- Do not convert qualitative marketing language into numeric fit envelopes.
- Compile numeric feature predicates only from accepted source evidence that explicitly establishes the dimension, declared-constraint semantics and comparison/bound.
- Keep every feature-bound predicate on one concrete feature instance.
- Do not synthesize fit envelopes by joining bounds from unrelated subjects or incomplete evidence sources.
- Keep manufacturer provenance separate from exact product/variant identity.
- Bind product-scoped manufacturer connection evidence to the exact product that owns the evaluated interface.
- Bound flattened multi-product or multi-model evidence to the requested identity before parsing sibling-specific fields.
- Preserve the primary source/evidence tuple atomically when merging equivalent claims from multiple sources.
- Treat manufacturer prescription as positive issuer-scoped evidence unless the source establishes a causal technical prohibition.
- Omission from a manufacturer compatibility list remains `unknown`, not `incompatible`.
- Keep operational mass configuration-specific when the Tool requires an installed configuration.
- Search/recognition remains advisory until the worker explicitly confirms Tool identity.
- Preserve exact candidate, component, feature, endpoint, installation-binding and source-product provenance through generation, evaluation, ranking and field output.
- Historical portability cohorts V1–V6 remain frozen at their original semantic revisions.

## Suggested opening prompt for the next chat

```text
Continue TetherLens from merged `main` after PR #69. Keep all historical portability cohorts frozen at their existing semantic revisions: V1 is 0 A / 5 B / 3 C / 0 D, V2 is 0 A / 6 B / 2 C / 0 D, V3 is 0 A / 5 B / 3 C / 0 D, V4 is 0 A / 4 B / 4 C / 0 D, V5 is 0 A / 6 B / 2 C / 0 D, and V6 is 1 A / 7 B / 0 C / 0 D.

PR #69 establishes the sparse-geometry evidence boundary: use reusable physical/topological rules where the source supports them, but retain exact evidence-bound installation/connection relationships when manufacturer evidence establishes what works without enough geometry to infer why. Do not reverse-engineer unsupported geometry from manufacturer pairings, and do not treat positive OEM evidence as a global mixed-manufacturer exclusion.

For the next slice, tackle 3M DBI-SALA 1500009 D-Ring Attachment with Cord. Start by inspecting the frozen V6 case, the current 3M ingestion path, existing ToolAttachment eligibility / attachment-method / provided-interface semantics, current catalogue candidates for a complete worker-facing vertical, and available first-party 3M evidence.

The target is to broaden 3M ingestion and carry 1500009 through one real complete recommendation using existing generic semantics wherever possible: captive through-opening OR captive-handle eligibility, cinch/choke installation, rated capacity, provided D-ring interface, ordinary candidate generation/evaluation/selection. Prefer a defensible mixed-manufacturer vertical if the current catalogue supports one, but do not force it.

Before changing code, identify the smallest reusable implementation slice and recommend the approach. Treat a need for new ontology as a finding to justify from the evidence, not as the default objective.
```
