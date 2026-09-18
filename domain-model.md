# TetherLens Domain Model

## Purpose

This document defines the main concepts in TetherLens and how they relate.

It is a conceptual domain model, not a final database schema.

## Domain model overview

TetherLens contains three broad groups of entities:

1. **Product entities** — the physical tools, supporting configuration products, and tethering components.
2. **Knowledge entities** — what TetherLens knows about those products, their documented relationships, and why.
3. **Recommendation entities** — the current work context and the reasoning output.

## Product entities

### Tool

A physical tool or object that may need to be tethered.

Typical attributes may include:

- `id`
- `manufacturer`
- `model`
- `sku`
- `category`
- `body_mass`, where the tool has a separable installed battery or other configuration component
- power-source/configuration information where relevant
- native tether-point status
- relevant physical/interface features
- known materials where relevant
- manufacturer-declared limits
- catalogue status

For load reasoning, TetherLens must use the mass of the tool **as configured for use**, not automatically a bare-tool value. A non-battery tool may use its accepted physical mass directly. A cordless tool with an interchangeable installed battery should instead use an `OperationalMassProfile` that combines the accepted tool-body mass with the mass of a specific compatible battery.

Physical tool-body mass should be established from trustworthy evidence bound to the exact tool identity. Manufacturer evidence is preferred; a reputable exact-SKU secondary source may be used where manufacturer data is unavailable or incomplete, with the evidence method and provenance retained.

A tool does **not** need to have a manufacturer-documented tether point in order to be tetherable. A recommendation may use:

- a native tether point;
- another suitable physical feature or geometry on the tool;
- a loop, cinch, wrap or other controlled attachment method around an appropriate part of the tool;
- a separate ToolAttachment that creates a tethering interface through reusable technical eligibility; or
- an exact manufacturer-documented ToolAttachment installation at a resolved feature/location when the relationship is established but complete geometry is not.

The model should therefore distinguish between:

- a documented or observed absence of a native tether point;
- absence of information about whether a tether point exists; and
- a manufacturer-defined installation feature/location whose exact physical form is not fully established.

Suggested native tether-point states include:

- `documented_present`
- `observed_present`
- `observed_absent`
- `not_documented`
- `unknown`

#### ToolInterfaceFeature

A `ToolInterfaceFeature` represents one physical or manufacturer-defined feature/location that may participate in a tethering method, whether or not the manufacturer describes it as a tether point and whether or not complete geometry is known.

Typical attributes may include:

- `feature_kind` — normalized physical form where established;
- `feature_role` — manufacturer/functional purpose where established;
- location description on the tool;
- `captive_state`;
- relevant geometry and dimensions where established;
- feature-local attributes/constraints;
- evidence method; and
- source or observation reference.

Initial normalized feature kinds include:

```text
through_opening
ring
handle
narrowed_section
external_section
surface
other
```

Initial feature roles include:

```text
tether_interface
accessory_mount
grip
working_part
other
unknown
```

Feature kind, role and state are orthogonal. For example:

```text
Klein screwdriver tether hole
  feature_kind = through_opening
  feature_role = tether_interface
  captive_state = captive

Hilti accessory-installation openings
  feature_kind = other
  feature_role = accessory_mount
  captive_state = unknown
```

The Hilti example is intentionally conservative: current evidence establishes the named accessory-installation location and role, but not `through_opening`, captive state, dimensions, ring/eye form, or the number of independently usable openings.

The feature vocabulary should remain small and geometry-led where geometry is known. `other` is a valid evidence state when a real resolved feature/location exists but the source does not justify a more specific physical classification.

Every feature-local predicate used by one eligibility path must bind to the same concrete `ToolInterfaceFeature`; TetherLens must not combine geometry, captive state, dimensions, location or prohibitions from unrelated feature records.

See `tool-anatomy-selection-semantics.md` and `compatibility-evidence-and-inference.md` for the executable normalization and sparse-evidence rules.

### Battery

A `Battery` is a supporting catalogue product used to represent the installed configuration of a cordless Tool. It is not itself a tethering component and does not appear in the tether load path as a separate tethered item.

Typical attributes may include:

- `id`
- `manufacturer`
- `model`
- `sku`
- battery platform/family where published
- `mass`
- catalogue status

Battery mass should be established from trustworthy evidence bound to the exact battery identity. Manufacturer evidence is preferred; a reputable exact-SKU secondary source may be used where manufacturer data is unavailable or incomplete.

Tool-to-battery compatibility should not be inferred merely because two products share a voltage or marketing platform name. The relationship should be supported by manufacturer evidence such as:

- explicit compatibility/recommended-battery information;
- manufacturer kit composition; or
- another manufacturer-backed product relationship.

One Battery may be compatible with many Tools and one Tool may have several compatible Batteries.

### OperationalMassProfile

An `OperationalMassProfile` represents the mass of one specific tool configuration used for load reasoning.

For a cordless tool with an interchangeable battery:

```text
tool body mass + installed battery mass = operational mass
```

Typical attributes may include:

- `id`
- `tool_id`
- `battery_id`
- `operational_mass`
- relationship/evidence basis establishing that the battery is valid for the tool
- dependency references to the accepted tool-body and battery-mass Claims
- status

A Tool may therefore have several valid operational mass profiles. TetherLens should preserve those profiles explicitly rather than silently choosing an arbitrary battery.

The operational mass is a derived fact. Its provenance should identify the exact tool-body mass Claim, exact battery-mass Claim, and the manufacturer-backed relationship that permits that tool/battery configuration.

If a cordless tool requires an installed battery but no valid operational profile can be established, it is not recommendation-ready for load-based reasoning. A bare-tool mass must not be substituted silently.

### Tether

The tether or lanyard connecting the tool-side interface to an anchorage-side interface.

Typical attributes may include:

- `id`
- `manufacturer`
- `model`
- `sku`
- `rated_capacity`
- `minimum_length` / `maximum_length`, where relevant
- tether form or behaviour, where objectively defined
- `lanyard_materials`
- `connection_points[]`
- manufacturer-declared limits
- standards declarations
- catalogue status

Tether materials should distinguish the lanyard/body material from discrete connector materials.

A tether will normally have at least two connection points, but the model should not assume exactly two. Examples include:

- dual-carabiner tethers;
- carabiner-to-loop tethers;
- multi-leg / multi-lanyard products; and
- products with additional connection or branching points.

A tether is the only tethering component category expected to be present in every tethered-tool configuration.

#### TetherConnectionPoint

A `TetherConnectionPoint` represents one usable end, branch, or connection interface on a tether.

Typical attributes may include:

- `id`
- `tether_id`
- `role` — `tool_side`, `anchor_side`, `either`, or not established
- `interface_type` — e.g. carabiner, loop, ring, hook, other
- `connector_spec_id`, where a discrete connector is present
- `leg_id`, where required for branched or multi-leg tethers
- relevant interface dimensions

This allows TetherLens to represent products with two, three, or more connection points without hard-coding `connector_a` and `connector_b`.

`either` is an affirmative endpoint-role fact: it means accepted evidence establishes that the individual endpoint may serve either side. Missing role evidence is different and must remain not established/`unknown`; it must not be promoted to `either` merely because two endpoints look identical, reference the same connector specification, or lack a stated distinction.

#### TetherEndpointAssignmentDeclaration

A `TetherEndpointAssignmentDeclaration` represents accepted evidence about how a set of tether endpoints may be assigned within a candidate path when that relationship is not properly represented as an intrinsic role on either individual endpoint.

The first bounded semantic is `reversible_tool_anchor_pair`: accepted evidence establishes that exactly two named endpoints may occupy the tool-side and anchor-side positions in either orientation.

Typical attributes may include:

- `id`
- `tether_id`
- `endpoint_ids[]`
- assignment semantic
- issuer/manufacturer
- evidence scope
- source/evidence references

This relation is separate from `TetherConnectionPoint.role`. A reversible-pair declaration does not rewrite either endpoint to `either`; the individual roles may remain unknown. It is also separate from connection compatibility: proving that endpoint A or B may occupy the tool/anchor position does not prove that either endpoint can safely engage a selected target interface.

The relation must remain tether-owned because endpoint IDs are local and may repeat across products. Symmetric hardware, shared `ConnectorSpec`, `dual` / `double` naming, connectors at each end, or absence of contrary evidence are not sufficient by themselves to create this declaration. See `endpoint-assignment-semantics.md` for the executable v1 evidence and provenance rules.

#### ConnectorSpec

A `ConnectorSpec` describes a discrete connector such as a carabiner. It should be reusable where the same connector is used across multiple products.

Typical attributes may include:

- `id`
- connector type
- material
- gate opening / throat geometry
- other relevant internal geometry
- locking mode — e.g. non-locking, manual-locking, auto-locking
- opening action count — e.g. one, two, three, unknown
- swivel — yes/no
- captive eye — yes/no
- manufacturer terminology / description

`locking_mode` and `opening_action_count` should be separate because manufacturer terminology is not always consistent.

Where a manufacturer reuses the same carabiner across several tether products, the connector specification and any internal measurement should be captured once and referenced by those products.

### ToolAttachment

A component used to create or provide a tethering interface on the tool.

Typical attributes may include:

- `id`
- `manufacturer`
- `model`
- `sku`
- `rated_capacity`
- attachment method
- provided tether-side interface
- reusable installation/eligibility facts where established
- materials
- applicable dimensional limits
- manufacturer-declared compatibility or restrictions
- catalogue status

A ToolAttachment is not required where the tool already has an appropriate tethering interface.

A ToolAttachment may participate in recommendation through reusable technical eligibility or through an exact accepted installation relationship when the manufacturer establishes the product/Tool/feature route but not enough physical detail for a generic rule.

A tool-side attachment solution may contain multiple physical products. Runtime `ToolAttachmentAssembly` composition should therefore preserve selected component identity and the product that owns each provided interface when product-scoped manufacturer evidence depends on that ownership.

#### ToolAttachmentInstallationBinding

A `ToolAttachmentInstallationBinding` represents accepted positive evidence for one exact ToolAttachment installation when reusable geometry is insufficient.

Conceptually:

```text
ToolAttachmentInstallationBinding
- id / binding_ref
- tool_ref
- source_product_ref
- installation_feature_id
- issuer_manufacturer
- scope
- source_urls
```

It means:

> accepted evidence establishes this attachment product at this resolved feature of this Tool.

It does **not** mean:

- every Tool with the same feature role accepts the attachment;
- the feature has geometry that was not published;
- only this attachment may be used; or
- the product pairing itself is a reusable technical compatibility rule.

Different documented product routes should have distinct relationship identity. Several sources documenting the same semantic route may support one binding while preserving all source provenance.

### AnchorAttachment

A component used to create or provide a tethering interface on the anchorage side.

Typical attributes may include:

- `id`
- `manufacturer`
- `model`
- `sku`
- `rated_capacity`
- attachment method
- interface geometry
- materials
- manufacturer-declared limits
- catalogue status

An AnchorAttachment may connect to:

- a person;
- a structural anchor;
- another permitted anchorage method.

Whether a person may be used as the anchorage can depend on operational tool mass, product capacity, site policy, and task context.

### Container

A bag, bucket, pouch, or other containment product intended to retain tools or objects.

Typical attributes may include:

- `id`
- `manufacturer`
- `model`
- `sku`
- `rated_capacity`
- closure type
- attachment / anchorage interface
- dimensions
- materials
- manufacturer-declared limits
- catalogue status

Containers are only relevant to recommendations where containment is part of the solution.

## Common product concepts

Although the product categories differ, they share common conceptual attributes:

- identity;
- manufacturer;
- model / SKU;
- rated or physical properties;
- physical geometry where established;
- functional/interface role where established;
- material information;
- declared constraints and relationships;
- source-backed claims;
- recommendation-readiness status where applicable.

Supporting products such as Batteries may exist primarily to define a Tool's valid operational configuration rather than to appear as independent recommendation components.

### Commercial kit / wrapper identity

A manufacturer may sell several independently identifiable recommendation components under one commercial kit SKU. The wrapper is retained as a catalogue-only `kit` product identity so it can own evidence-backed relationships, but it has no recommendation/load-path subtype and does not become another physical component.

Where the manufacturer identifies the contained products explicitly, TetherLens may preserve exact `kit_relationship` records and then normalize each contained Tether, ToolAttachment or AnchorAttachment from its own product evidence. Runtime candidate generation continues to compose those existing component types.

A kit row that conflicts with other first-party identity evidence must fail closed. The system should preserve the published relationship and the conflict rather than substitute the component that seems more plausible.

The final implementation may use separate tables, a shared Product/Component base entity, subtype tables, or another structure.

That decision is intentionally deferred.

## Knowledge entities

### Source

A document, webpage, measurement record, test record, standard, or other artefact used to support a Claim, relationship or Rule.

Examples:

- manufacturer datasheet;
- manufacturer product page;
- manufacturer operating instructions;
- declaration of conformity;
- reputable secondary product-detail source;
- internal measurement record;
- internal test record;
- standard or formal guidance;
- structured field study.

For combined manufacturer documents, source attribution may need model-local section scope. A model name appearing somewhere in a document is not enough to assign an unrelated installation section to that model.

### Claim

An atomic statement TetherLens accepts or considers about a subject.

Examples:

- Tool A body mass = 1.3 kg.
- Battery B mass = 0.6 kg.
- Operational profile A+B mass = 1.9 kg.
- Tether C rated capacity = 2.3 kg.
- Connector D gate opening = 14 mm.
- Product E material = polyester.
- Manufacturer F explicitly pairs Tether G with ToolAttachment H.
- Manufacturer F instructs ToolAttachment H to be secured at Tool A feature J.

Claims should be granular enough that one incorrect or superseded fact does not invalidate unrelated facts about the same product or relationship.

Equivalent claims may be supported by multiple sources, but the primary source URL and the raw wording/method metadata attributed to it must remain aligned. Additional equivalent artifacts should be retained as supporting provenance rather than causing wording from one source to be attributed to another.

### Evidence

A relationship between a Source and a Claim or Rule that records how the source supports it.

Evidence should capture:

- target claim/rule;
- source;
- method;
- source location where useful;
- exact model/product/interface scope where relevant;
- who or what recorded it;
- when it was recorded;
- any qualification.

Evidence scope should be as narrow as the source. Product-specific connection evidence must not apply to an unrelated same-shaped interface merely because the documented product appears elsewhere in the selected assembly.

### Rule

Reusable reasoning applied to product facts, context, and policy.

Rule types may include:

- hard constraint;
- compatibility rule;
- contextual preference;
- caution;
- policy rule.

Examples:

- object operational mass must not exceed rated component capacity;
- connector geometry must permit valid engagement;
- prefer reduced free tether length where snag risk is elevated;
- person anchoring is prohibited above a configured site threshold.

An exact documented installation/compatibility relationship is not automatically a Rule. It may remain a narrowly scoped evidence-backed relationship until repeated evidence or direct physical facts justify a reusable rule.

## Claim classes

### Primitive claim

A directly known product property.

Examples:

- `tool_body_mass = 1.3 kg`
- `battery_mass = 0.6 kg`
- `rated_capacity = 2.3 kg`
- `length = 1.0 m`
- `material = polyester`
- `gate_opening = 14 mm`

Primitive claims normally come from manufacturer data, qualified exact-product secondary evidence where the property policy permits it, or internal measurement.

### Declared constraint or relationship

A source explicitly states a product-specific limit, compatibility condition, pairing or installation relationship.

Examples:

- maximum operating temperature = 80°C;
- use only with attachment X;
- manufacturer pairs tether A with attachment B;
- manufacturer instructs attachment B to be installed at named Tool feature C;
- not intended for a particular exposure.

Declared constraints/relationships should be retained even where TetherLens cannot derive them from lower-level product facts.

A positive documented pairing does not automatically prove that omitted alternatives are technically incompatible. Likewise, a documented installation must not be reverse-engineered into exact geometry the source did not publish.

### Derived claim

A conclusion produced from claims and rules.

Examples:

- operational mass of Tool A with Battery B = accepted tool-body mass + accepted battery mass;
- connector A is geometrically compatible with attachment B;
- configuration C satisfies all rated-capacity requirements;
- configuration D is less suitable where snag risk is high.

Derived claims should retain enough dependency information to explain how they were reached. For a persisted operational-mass Claim, the dependency chain should explicitly identify the accepted tool-body and battery-mass Claims rather than relying only on a human-readable note.

Most derived recommendation conclusions may be computed at runtime. Operational mass profiles are a useful exception to persist because they are reusable configuration facts required by load checks and must retain their exact input provenance.

Cross-product patterns should remain bounded hypotheses until independently validated; they must not silently become derived exact physical facts.

## Recommendation-side entities

### ResolvedToolProfile

The recommendation engine should support two tool-resolution modes.

#### Catalogue tool

The preferred path is an exact or sufficiently specific match to a recommendation-ready Tool record. Verified catalogue facts can then be used directly, with provenance indicating whether an accepted physical property came from manufacturer evidence, qualified exact-SKU secondary evidence, or another permitted method.

For a cordless catalogue tool, the resolved profile should also identify the applicable `OperationalMassProfile`, including the installed Battery identity. The engine must not substitute bare-tool mass or silently choose among several compatible batteries.

The resolved Tool should retain its exact normalized feature instances even when some feature attributes remain unknown. Evidence-bound installation may require exact feature identity without requiring invented geometry.

#### Generic tool profile

Where an exact manufacturer/model match cannot be established, TetherLens may create a session-level `GenericToolProfile` containing only the facts needed to continue safely.

Typical attributes may include:

- broad tool type / category;
- user-provided or user-measured mass or mass range;
- mass-source type;
- relevant visible/confirmed geometry; and
- attachment/interface observations required by applicable rules.

A GenericToolProfile is runtime context, not an accepted catalogue Tool record. User-provided values should not silently become persistent Claims.

### Context

The current work situation relevant to the recommendation.

Examples include:

- restricted space;
- snag risk;
- contaminant exposure;
- required reach;
- available anchorage method;
- task-specific movement or access limitations.

Context is not evidence.

It is an input to rules.

### Policy

Rules imposed by an organisation, site, project, or programme.

Examples:

- person anchoring permitted up to a configured tool mass;
- specific components prohibited;
- manufacturer-only combinations required by local policy;
- additional site-specific restrictions.

Policy should be separable from technical suitability and manufacturer evidence. A manufacturer's documented route is not itself a site policy that all alternatives must be rejected.

### CandidateConfiguration

A possible tethering arrangement assembled from applicable product entities.

A candidate may include:

- resolved tool configuration, including an installed battery profile where applicable;
- ToolAttachment assembly, if required;
- exact bound Tool feature and installation provenance where applicable;
- tether;
- anchor attachment, if required;
- anchorage method;
- relevant configuration metadata, including selected endpoint identities and any operative endpoint-assignment declaration provenance.

A ToolAttachment-mediated candidate may originate from reusable feature eligibility or from an exact accepted `ToolAttachmentInstallationBinding`. Both routes enter the same ordinary downstream load/connection/context evaluation; the latter must retain its original evidence separately rather than pretending its execution projection is a generic technical rule.

CandidateConfiguration may be an ephemeral runtime object rather than a permanently curated database record.

### Recommendation

The evaluated output presented to the worker.

A Recommendation should include enough structured information to describe:

- resolved tool profile;
- selected configuration;
- viability result;
- context suitability;
- important cautions;
- evidence/installation provenance and limitations;
- manufacturer assessment where relevant;
- policy status;
- result state.

Possible result states are:

- Recommended;
- Recommended with constraints;
- Limited-confidence recommendation;
- No suitable recommendation.

## Mandatory recommendation facts

For baseline recommendations, TetherLens needs three classes of mandatory fact.

### 1. Object mass

For catalogued tools, the mass used for load reasoning must represent the tool as configured for use.

For a non-battery tool, the accepted physical tool mass may be used directly. For a cordless tool with an interchangeable installed battery, TetherLens should establish separately:

- exact tool identity and accepted tool-body mass;
- exact battery identity and accepted battery mass;
- a manufacturer-backed relationship establishing that the battery is valid for the tool; and
- the derived operational mass profile for that exact tool/battery combination.

Manufacturer evidence is preferred for physical tool-body and battery mass; a reputable exact-SKU secondary source may be accepted where manufacturer mass is unavailable or incomplete. TetherLens should not infer persistent catalogue mass from an image or a similar product.

If several compatible batteries exist, several valid operational mass profiles may exist. Load reasoning must use a specific resolved profile rather than an arbitrary battery or bare-tool mass.

### 2. Rated capacity of applicable load-bearing components

The rated capacity of every applicable component should come from manufacturer information.

Depending on the configuration, this may include:

- tether;
- tool attachment;
- anchor attachment;
- container.

Not all categories apply in every configuration.

### 3. Installation and interface viability

TetherLens needs sufficient information to establish every required step in a proposed configuration.

For tools, this does **not** require a manufacturer-documented native tether point and does not always require complete published geometry. A Tool-side path may be established through:

- native tether features with ordinary reusable connection rules;
- observed/published geometry evaluated by a validated reusable ToolAttachment eligibility rule;
- controlled loop/cinch/wrap rules against a bound feature; or
- accepted exact manufacturer installation evidence binding one ToolAttachment product to one resolved Tool feature when reusable geometry is not established.

Downstream tether/interface compatibility may come from:

- published dimensions;
- internal measurement;
- explicit manufacturer compatibility;
- manufacturer-supplied kit relationships;
- observed/confirmed geometry evaluated by a validated rule; or
- another validated reusable interface rule.

Product-scoped manufacturer connection evidence must match the exact concrete products and, for multi-component target assemblies, the exact product that owns the target interface being evaluated.

The model must distinguish `no native tether point` from `no information available`, and must distinguish `known documented route with incomplete geometry` from `generic physical compatibility established`.

Endpoint assignment is a prerequisite to composing an oriented candidate path, but it is not itself interface compatibility. A role-backed or relation-backed assignment must still pass the ordinary connection-compatibility reasoning for the selected endpoint/target pair.

## Secondary enrichment facts

Examples include:

- materials;
- detailed dimensions;
- chemical resistance;
- standards declarations;
- tether behaviour;
- usability characteristics;
- field feedback.

Missing secondary facts should limit the conclusions TetherLens draws rather than automatically making the product unusable.

## Unknown states

The domain model should distinguish:

- known;
- not published;
- not established;
- not applicable;
- disputed;
- superseded.

A missing value should not silently mean "safe", "compatible", "incompatible", or "not relevant".

For endpoint roles specifically, missing/not-established must remain distinct from the affirmative `either` role. A separate accepted endpoint-assignment relation may authorize a candidate orientation without changing that unknown role state.

For Tool geometry, `unknown` captive state or a broad `other` feature kind must remain unknown/broad; a known manufacturer installation does not authorize TetherLens to fill those gaps with the values that would make a generic rule pass.

## Product readiness

A product may progress through internal readiness states such as:

### Identified

Basic product identity exists.

### Sourced

At least one relevant product source is recorded.

### Recommendation-ready

Mandatory recommendation facts are available for the relevant product role and at least one complete supported path can be established.

For a battery-powered Tool, this includes at least one valid operational mass profile for any configuration intended to participate in load-based recommendations.

A supported path may be geometry/rule-backed or, where the evidence boundary permits it, an exact evidence-bound installation plus ordinary downstream checks. Recommendation-readiness does not require TetherLens to invent a generic explanation for every documented valid relationship.

### Enriched

Additional material, dimensional, standards, or application-relevant facts are available.

### Field-enriched

Structured field experience or user feedback has been reviewed and incorporated into reusable knowledge.

These labels are primarily internal and may change as the implementation matures.

## Relationship summary

```text
Tool ──manufacturer-backed relationship──> Battery
  │                                         │
  └──────────────┬──────────────────────────┘
                 ▼
       OperationalMassProfile
                 │
                 ▼
        load reasoning mass

Tool
  │
  ├── ToolInterfaceFeature
  │       │
  │       ├── reusable eligibility predicates ──> ToolAttachmentAssembly
  │       │
  │       └── exact accepted installation binding ──> ToolAttachment product
  │
  └── selected configuration

ToolAttachmentAssembly
  │
  └── provided interface ──owned by exact selected component product

TetherConnectionPoint(s)
  │
  ├── individual role evidence ──> tool_side / anchor_side / either
  │
  └── optional accepted pair relation ──> reversible tool/anchor assignment

Source
  │
  └── Evidence ──> Claim / exact relationship ──> Product / feature / profile
  │                    │
  │                    └── dependency ──> input Claim(s)
  │
  └── Evidence ──> Rule

Product facts + exact accepted relationships + Context + Rules + Policy
                │
                ▼
      CandidateConfigurations
                │
                ▼
          Recommendation
```

## Domain modelling principle

> **Store the strongest low-level truths the evidence supports once. Derive reusable application conclusions many times, while retaining exact documented relationships when the evidence is narrower than a generic rule.**

This is the main scalability principle for the TetherLens knowledge model.
