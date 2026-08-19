# TetherLens Domain Model

## Purpose

This document defines the main concepts in TetherLens and how they relate.

It is a conceptual domain model, not a final database schema.

## Domain model overview

TetherLens contains three broad groups of entities:

1. **Product entities** — the physical tools, supporting configuration products, and tethering components.
2. **Knowledge entities** — what TetherLens knows about those products and why.
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
- another suitable captive feature or geometry on the tool;
- a loop or cinch arrangement around an appropriate part of the tool; or
- a separate ToolAttachment that creates a tethering interface.

The model should therefore distinguish between:

- a documented or observed absence of a native tether point; and
- absence of information about whether a tether point exists.

Suggested native tether-point states include:

- `documented_present`
- `observed_present`
- `observed_absent`
- `not_documented`
- `unknown`

#### ToolInterfaceFeature

A `ToolInterfaceFeature` represents a physical feature that may participate in a tethering method, whether or not the manufacturer describes it as a tether point.

Typical attributes may include:

- `feature_type`
- location on the tool
- relevant geometry and dimensions
- whether the feature is captive/closed
- evidence method
- source or observation reference

Possible feature types may include:

- dedicated tether eye;
- captive hole;
- closed or captive handle;
- grip;
- neck / waist / narrowing suitable for a controlled attachment method; or
- other geometry defined by a reusable rule.

The feature vocabulary should remain small and geometry-led rather than becoming an application-specific classification system.

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
- `role` — `tool_side`, `anchor_side`, or `either`
- `interface_type` — e.g. carabiner, loop, ring, hook, other
- `connector_spec_id`, where a discrete connector is present
- `leg_id`, where required for branched or multi-leg tethers
- relevant interface dimensions

This allows TetherLens to represent products with two, three, or more connection points without hard-coding `connector_a` and `connector_b`.

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
- interface geometry
- materials
- applicable dimensional limits
- manufacturer-declared compatibility or restrictions
- catalogue status

A ToolAttachment is not required where the tool already has an appropriate tethering interface.

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
- physical geometry;
- material information;
- declared constraints;
- source-backed claims;
- recommendation-readiness status where applicable.

Supporting products such as Batteries may exist primarily to define a Tool's valid operational configuration rather than to appear as independent recommendation components.

The final implementation may use separate tables, a shared Product/Component base entity, subtype tables, or another structure.

That decision is intentionally deferred.

## Knowledge entities

### Source

A document, webpage, measurement record, test record, standard, or other artefact used to support a Claim or Rule.

Examples:

- manufacturer datasheet;
- manufacturer product page;
- declaration of conformity;
- reputable secondary product-detail source;
- internal measurement record;
- internal test record;
- standard or formal guidance;
- structured field study.

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

Claims should be granular enough that one incorrect or superseded fact does not invalidate unrelated facts about the same product.

### Evidence

A relationship between a Source and a Claim or Rule that records how the source supports it.

Evidence should capture:

- target claim/rule;
- source;
- method;
- source location where useful;
- who or what recorded it;
- when it was recorded;
- any qualification.

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

### Declared constraint

A source explicitly states a product-specific limit or compatibility condition.

Examples:

- maximum operating temperature = 80°C;
- use only with attachment X;
- manufacturer pairs tether A with attachment B;
- not intended for a particular exposure.

Declared constraints should be retained even where TetherLens cannot derive them from lower-level product facts.

### Derived claim

A conclusion produced from claims and rules.

Examples:

- operational mass of Tool A with Battery B = accepted tool-body mass + accepted battery mass;
- connector A is compatible with attachment B;
- configuration C satisfies all rated-capacity requirements;
- configuration D is less suitable where snag risk is high.

Derived claims should retain enough dependency information to explain how they were reached. For a persisted operational-mass Claim, the dependency chain should explicitly identify the accepted tool-body and battery-mass Claims rather than relying only on a human-readable note.

Most derived recommendation conclusions may be computed at runtime. Operational mass profiles are a useful exception to persist because they are reusable configuration facts required by load checks and must retain their exact input provenance.

## Recommendation-side entities

### ResolvedToolProfile

The recommendation engine should support two tool-resolution modes.

#### Catalogue tool

The preferred path is an exact or sufficiently specific match to a recommendation-ready Tool record. Verified catalogue facts can then be used directly, with provenance indicating whether an accepted physical property came from manufacturer evidence, qualified exact-SKU secondary evidence, or another permitted method.

For a cordless catalogue tool, the resolved profile should also identify the applicable `OperationalMassProfile`, including the installed Battery identity. The engine must not substitute bare-tool mass or silently choose among several compatible batteries.

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

Policy should be separable from technical suitability.

### CandidateConfiguration

A possible tethering arrangement assembled from applicable product entities.

A candidate may include:

- resolved tool configuration, including an installed battery profile where applicable;
- tool attachment, if required;
- tether;
- anchor attachment, if required;
- anchorage method;
- relevant configuration metadata.

CandidateConfiguration may be an ephemeral runtime object rather than a permanently curated database record.

### Recommendation

The evaluated output presented to the worker.

A Recommendation should include enough structured information to describe:

- resolved tool profile;
- selected configuration;
- viability result;
- context suitability;
- important cautions;
- evidence limitations;
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

### 3. Interface compatibility

TetherLens needs sufficient information to establish that every required physical connection in a proposed configuration can be made correctly.

For tools, this does **not** require a manufacturer-documented tether point. Compatibility may instead be established from native tether features, observed geometry, controlled loop/cinch rules, or the geometry requirements of a ToolAttachment.

This may come from:

- published dimensions;
- internal measurement;
- explicit manufacturer compatibility;
- manufacturer-supplied kit relationships;
- observed/confirmed tool geometry evaluated by a validated rule; or
- another validated reusable interface rule.

The model must distinguish `no native tether point` from `no information available`.

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

A missing value should not silently mean "safe", "compatible", or "not relevant".

## Product readiness

A product may progress through internal readiness states such as:

### Identified

Basic product identity exists.

### Sourced

At least one relevant product source is recorded.

### Recommendation-ready

Mandatory recommendation facts are available for the relevant product role.

For a battery-powered Tool, this includes at least one valid operational mass profile for any configuration intended to participate in load-based recommendations.

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

Source
  │
  └── Evidence ──> Claim ──> Product / OperationalMassProfile
  │                    │
  │                    └── dependency ──> input Claim(s)
  │
  └── Evidence ──> Rule

Product facts + Context + Rules + Policy
                │
                ▼
      CandidateConfigurations
                │
                ▼
          Recommendation
```

## Domain modelling principle

> **Store low-level truths once. Derive application conclusions many times.**

This is the main scalability principle for the TetherLens knowledge model.
