# TetherLens Technical Schema v0.1

## Status

Draft implementation specification for the MVP supply-side knowledge model.

This document translates the conceptual entities in `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, and `recommendation-engine.md` into an implementation-ready logical relational schema.

It does **not** commit TetherLens to a specific database engine, ORM, backend language, or deployment platform.

## Goals

Schema v0.1 should make it possible to:

- store a small but structurally diverse catalogue of real tools, supporting configuration products, and tethering components;
- keep accepted operational product facts fast to query;
- trace mandatory facts back to claims, evidence, and sources;
- represent configuration-dependent operational mass without collapsing interchangeable battery options into one tool mass;
- represent reusable physical interfaces rather than a tool-to-tether compatibility matrix;
- represent multi-connection and multi-leg tether products;
- store explicit manufacturer constraints and product relationships without confusing them with generic compatibility;
- support deterministic recommendation rules in version-controlled code;
- derive recommendation-readiness rather than relying on a manually maintained boolean; and
- support the first two-stage supply-side scalability test without redesigning the data model.

## Non-goals

Schema v0.1 does not attempt to model:

- users, organisations, permissions, or SSO;
- worker sessions;
- computer-vision recognition results;
- persistent candidate configurations;
- persistent recommendations;
- feedback workflows;
- inventory, procurement, or stock;
- a full standards ontology;
- arbitrary engineering geometry;
- a database-executed rule language;
- arbitrary structural-anchor engineering assessment; or
- a complete automated ingestion pipeline.

These may be added later if validated by the MVP.

---

# 1. Design decisions

## 1.1 Relational core with product subtypes

All physical catalogue products share a base `product` record and then use one subtype table where subtype-specific fields are required:

- `tool`
- `battery`
- `tether`
- `tool_attachment`
- `anchor_attachment`
- `container`

`battery` is a supporting configuration product rather than a tethering component. It exists because the installed battery can change the mass of a cordless Tool used by load reasoning.

This avoids both:

- a single sparse product table containing many irrelevant nullable columns; and
- unrelated product tables that duplicate identity, manufacturer, lifecycle, and catalogue metadata.

## 1.2 Accepted operational values are stored directly

Values needed frequently by the recommendation engine are stored in typed operational columns, for example:

```text
tool.body_mass_kg
battery.mass_kg
operational_mass_profile.operational_mass_kg

tether.rated_capacity_kg

tether.min_length_mm
connector_spec.locking_mode
```

The recommendation engine should not reconstruct these values by traversing `Claim` and `Evidence` for each request.

The provenance layer exists alongside the operational catalogue and explains why those accepted values are trusted.

For configuration-dependent cordless tools, the engine consumes a specific `operational_mass_profile`; it must not substitute `tool.body_mass_kg` as the load-check mass when an installed battery is required.

Whether a Tool may use `body_mass_kg` directly or requires an operational profile is itself an accepted catalogue fact. The default state is unknown, and absence of a known Battery relationship or operational profile must never be treated as evidence that no installed configuration is required.

## 1.3 Provenance remains claim-level

`Claim` remains atomic and source-backed where it represents a directly sourced fact.

An accepted operational field is linked to the accepted Claim that currently supports it through `accepted_fact_link`.

Historical, disputed, rejected, and superseded Claims remain preserved even when they are no longer linked to the active operational value.

Derived Claims may additionally depend on other accepted Claims through `claim_dependency`. This makes the derivation machine-traceable rather than relying on a human-readable note.

For example:

```text
accepted tool-body mass Claim
          +
accepted battery-mass Claim
          ↓
accepted operational-mass Claim
```

The validity of the tool/battery combination itself is represented separately by a manufacturer-backed `declared_relationship`.

## 1.4 Physical interfaces are shared across tethering product categories

The conceptual domain distinguishes:

- `ToolInterfaceFeature`;
- `TetherConnectionPoint`;
- tool-attachment interfaces;
- anchor-attachment interfaces; and
- container interfaces.

The technical schema implements these through one shared `physical_interface` table with role-specific validation.

A supporting Battery does not require a tethering `physical_interface` merely because it participates in an operational Tool configuration.

This gives the recommendation engine a common vocabulary for connection reasoning without changing the conceptual meaning of the entities.

## 1.5 Geometry is deliberately narrow

TetherLens does not need a general CAD or mechanical geometry model.

It records only dimensions needed by actual interface rules.

Geometry vocabularies should therefore remain small and expand only when a real product or rule requires a new dimension.

## 1.6 Rules execute in code for v0.1

The `rule` table stores identity, version, type, description, evidence, and the reference to the implementation.

Executable rule logic remains in version-controlled application code.

Schema v0.1 does not store arbitrary executable expressions in database rows and does not introduce a custom rules DSL.

## 1.7 Readiness is derived

There is no manually editable `recommendation_ready` boolean.

Recommendation-readiness is derived from:

- the mandatory operational facts available for the product role;
- accepted Claims supporting those facts;
- the required evidence quality;
- valid configuration relationships where applicable; and
- whether at least one supported interface path can be established for the use being evaluated.

For every catalogued Tool, the catalogue must first establish whether an operational profile is `required` or `not_required`. The default `unknown` state blocks load-based readiness. For a cordless Tool classified as `required`, readiness for load-based reasoning requires at least one valid `operational_mass_profile`. A bare-tool/body mass alone is insufficient.

Readiness may therefore be path-dependent rather than a permanent intrinsic property of a product.

---

# 2. Logical datatype conventions

The following logical types are used throughout this specification.

| Logical type | Meaning |
|---|---|
| `UUID` | Globally unique identifier |
| `TEXT` | UTF-8 text |
| `BOOLEAN` | `true` / `false` |
| `SMALLINT` | Small whole number |
| `INTEGER` | Whole number |
| `DECIMAL(p,s)` | Exact decimal; never floating point for safety-relevant quantities |
| `DATE` | Calendar date |
| `TIMESTAMP_TZ` | Timestamp with timezone |
| `ENUM` | Closed vocabulary implemented as a database enum, check constraint, or application-level validated string |

All timestamps should be stored in UTC internally.

## Canonical operational units

Operational catalogue values use canonical units so recommendation logic does not repeatedly convert values:

| Quantity | Canonical operational unit |
|---|---|
| mass / rated capacity | kilograms (`kg`) |
| physical length / opening / diameter / circumference | millimetres (`mm`) |
| temperature | degrees Celsius (`°C`) where a typed field exists |

Claims and evidence may preserve the source unit separately.

All safety-relevant numbers use exact decimal types rather than binary floating-point types.

---

# 3. Stable enums

These vocabularies represent states or structural roles that should change rarely.

Expandable technical vocabularies such as tool categories, material names, and detailed dimension types should normally remain validated string codes rather than hard database enums.

## `product_type`

```text
tool
battery
tether
tool_attachment
anchor_attachment
container
```

## `record_status`

```text
draft
active
archived
```

`record_status` describes the state of the TetherLens catalogue record, not whether the manufacturer's product is still sold.

## `product_lifecycle_status`

```text
active
discontinued
superseded
unknown
```

## `operational_profile_requirement`

```text
unknown
not_required
required
```

`unknown` is the default and means TetherLens has not yet established whether `tool.body_mass_kg` represents the complete in-use load or whether an installed configuration must be added. This state blocks load-based recommendation-readiness.

`not_required` and `required` are accepted catalogue classifications, not fallbacks inferred from missing data. Each requires an accepted Claim linked to the Tool's `operational_profile_requirement` property.

## `native_tether_point_status`

```text
documented_present
observed_present
observed_absent
not_documented
unknown
```

## `tether_form`

Initial values:

```text
fixed
elastic
coiled
retractable
multi_leg
other
unknown
```

This vocabulary should only describe objectively identifiable product form or behaviour.

## `interface_role`

```text
tool_feature
tether_connection
tool_attachment_tool_side
tool_attachment_tether_side
anchor_attachment_tether_side
anchor_attachment_anchor_side
container_connection
```

## `tether_side`

```text
tool_side
anchor_side
either
```

Only valid for `interface_role = tether_connection`.

## `captive_state`

```text
captive
non_captive
unknown
not_applicable
```

## `locking_mode`

```text
non_locking
manual_locking
auto_locking
unknown
not_applicable
```

## `source_type`

```text
manufacturer_datasheet
manufacturer_webpage
manufacturer_manual
manufacturer_declaration
manufacturer_compatibility_statement
standard_or_guidance
internal_measurement
internal_test
third_party_test
secondary_published
structured_field_evidence
```

## `source_status`

```text
active
superseded
unavailable
```

## `claim_value_status`

```text
known
not_published
not_established
not_applicable
```

## `claim_value_kind`

```text
number
text
boolean
```

Only applicable where `claim_value_status = known`.

## `claim_type`

```text
direct
measured
declared_constraint
derived
```

## `claim_status`

Schema v0.1 extends the conceptual evidence model with workflow states needed for ingestion:

```text
proposed
accepted
disputed
superseded
rejected
```

## `evidence_target_type`

```text
claim
rule
```

## `evidence_method`

Initial values:

```text
manufacturer_stated
manufacturer_pairing
manufacturer_certification_statement
certificate_reviewed
qualified_secondary_exact_sku
published_geometry
internally_measured
internally_tested
standard_requirement
engineering_judgement
third_party_tested
derived_from_claims
structured_field_observation
```

## `evidence_strength`

```text
authoritative
supported
provisional
```

Nullable for evidence where strength is not useful.

## `rule_type`

```text
hard_constraint
compatibility
context_preference
caution
policy
```

## `rule_status`

```text
draft
active
superseded
retired
```

## `declared_relationship_type`

```text
explicitly_endorsed
explicitly_restricted
required_pairing
kit_relationship
compatible_configuration
```

`compatible_configuration` is intended for manufacturer-backed configuration relationships such as a Tool being valid with a particular Battery. It should not be populated merely from a shared voltage/platform label.

## `constraint_operator`

```text
eq
neq
lt
lte
gt
gte
requires
prohibits
```

---

# 4. Expandable technical vocabularies

The following should initially be represented as version-controlled validated string codes rather than database enums, because the vocabulary is expected to evolve as real products are ingested.

## `tool_category_code`

Examples only:

```text
hammer
wrench
spanner
screwdriver
drill
impact_driver
radio
flashlight
other
```

The catalogue should not depend on a perfect taxonomy for recommendation reasoning.

## `interface_type_code`

Initial vocabulary:

```text
carabiner
snap_hook
hook
loop
ring
dedicated_eye
captive_hole
closed_handle
grip
neck
strap
clamp
other
```

This vocabulary describes physical interface form rather than application suitability.

## `connector_type_code`

Initial vocabulary:

```text
carabiner
snap_hook
hook
other
```

## `dimension_type_code`

Initial examples:

```text
gate_opening
internal_width
internal_height
hole_diameter
feature_section_diameter
throat_depth
engagement_depth
strap_width
min_circumference
max_circumference
min_diameter
max_diameter
```

Only add dimensions required by real compatibility rules or product constraints.

## `material_code`

Material should be stored at the resolution actually supported by evidence.

Examples:

```text
polymer
polyester
aramid
uhmwpe
nylon
steel
stainless_steel
aluminium
```

Do not infer a more specific constituent material than the evidence supports.

## `material_role_code`

Examples:

```text
lanyard_body
strap
body
housing
reinforcement
other
```

Discrete connector material belongs on `connector_spec`, not in tether-body material rows.

---

# 5. Catalogue tables

## 5.1 `manufacturer`

Canonical manufacturer identity.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `name` | TEXT | no | Human-readable canonical name |
| `website_url` | TEXT | yes | Manufacturer root website |
| `created_at` | TIMESTAMP_TZ | no | Default current time |
| `updated_at` | TIMESTAMP_TZ | no | Updated on change |

### Constraints

- `name` must be non-empty after trimming.
- Case-insensitive duplicate detection should run during ingestion, but hard uniqueness by name is not required because corporate naming can be ambiguous.

---

## 5.2 `product`

Shared identity and lifecycle data for all physical catalogue products.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `manufacturer_id` | UUID | no | FK -> `manufacturer.id` |
| `product_type` | ENUM | no | `product_type` |
| `name` | TEXT | no | Product name |
| `model` | TEXT | yes | Manufacturer model identifier |
| `sku` | TEXT | yes | Manufacturer SKU / product code |
| `lifecycle_status` | ENUM | no | Default `unknown` |
| `record_status` | ENUM | no | Default `draft` |
| `notes` | TEXT | yes | Internal notes only |
| `created_at` | TIMESTAMP_TZ | no | Default current time |
| `updated_at` | TIMESTAMP_TZ | no | Updated on change |

### Constraints

- Exactly one subtype row must exist matching `product.product_type` once `record_status = active` where that type has a subtype table in v0.1.
- A product may remain `draft` while incomplete.
- Prefer a case-sensitive or normalized uniqueness check on `(manufacturer_id, sku)` where SKU is populated, but allow an explicit ingestion override because manufacturer catalogues may contain regional or legacy SKU ambiguity.
- `name` must be non-empty.

### Important distinction

`record_status` is not recommendation-readiness.

An active catalogue product may still have mandatory data gaps for a particular recommendation path.

---

## 5.3 `tool`

Tool-specific operational fields.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `product_id` | UUID | no | PK + FK -> `product.id` |
| `tool_category_code` | TEXT | no | Expandable controlled vocabulary |
| `body_mass_kg` | DECIMAL(12,6) | yes | Current accepted physical mass excluding an interchangeable installed Battery where applicable |
| `operational_profile_requirement` | ENUM | no | Default `unknown`; `not_required` permits direct body-mass reasoning only after accepted classification, `required` requires a configured profile |
| `native_tether_point_status` | ENUM | no | Default `unknown` |

### Constraints

- Parent `product.product_type` must equal `tool`.
- `body_mass_kg > 0` when populated.
- `body_mass_kg` may be null while the catalogue record is being built.
- A non-null operational `body_mass_kg` must have a matching `accepted_fact_link` to an accepted Claim supported by evidence permitted for physical mass. Manufacturer evidence is preferred; a reputable verified exact-SKU secondary source may be accepted when manufacturer mass is unavailable or incomplete.
- `operational_profile_requirement = unknown` blocks load-based recommendation-readiness, even if `body_mass_kg` is known and no Battery relationship/profile has been discovered.
- `operational_profile_requirement = not_required` permits `body_mass_kg` to be used directly as the object mass for load reasoning only when the classification itself has a matching `accepted_fact_link` to an accepted Claim for `operational_profile_requirement`.
- `operational_profile_requirement = required` also requires a matching accepted classification Claim; `body_mass_kg` is not itself the load-check mass and at least one valid `operational_mass_profile` is required.
- The classification Claim may be direct or derived from source-backed product facts, but `not_required` must never be inferred solely from absence of a Battery relationship, Battery product, or operational profile.
- `native_tether_point_status = observed_absent` does not imply that the tool is untetherable.

---

## 5.3A `battery`

Supporting product fields for an interchangeable Battery used in a Tool operational configuration.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `product_id` | UUID | no | PK + FK -> `product.id` |
| `mass_kg` | DECIMAL(12,6) | yes | Current accepted physical battery mass |
| `platform_code` | TEXT | yes | Manufacturer platform/family identifier where published |

### Constraints

- Parent `product.product_type` must equal `battery`.
- `mass_kg > 0` when populated.
- Battery `mass_kg` used in an operational profile requires an `accepted_fact_link` to an accepted Claim supported by evidence permitted for physical mass.
- Manufacturer evidence is preferred; a reputable verified exact-SKU secondary source may be accepted when manufacturer battery mass is unavailable or incomplete.
- `platform_code` alone does not establish compatibility with a Tool.

---

## 5.3B `operational_mass_profile`

Represents one exact Tool configuration whose mass is used by load reasoning.

For the current cordless-tool use case:

```text
tool.body_mass_kg + battery.mass_kg = operational_mass_profile.operational_mass_kg
```

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `tool_product_id` | UUID | no | FK -> `tool.product_id` |
| `battery_product_id` | UUID | no | FK -> `battery.product_id` |
| `relationship_id` | UUID | no | FK -> `declared_relationship.id` establishing manufacturer-backed Tool/Battery validity |
| `operational_mass_kg` | DECIMAL(12,6) | no | Derived configured mass used by load checks |
| `active` | BOOLEAN | no | Default true |
| `notes` | TEXT | yes | Qualification |

### Constraints

- `operational_mass_kg > 0`.
- Prefer `UNIQUE(tool_product_id, battery_product_id)` for active profiles unless a future product has materially distinct installed configurations using the same battery identity.
- `relationship_id` must relate the same Tool and Battery and use a manufacturer-backed relationship type such as `compatible_configuration` or `kit_relationship`.
- The parent Tool must have `operational_profile_requirement = required` with a matching accepted classification Claim before the profile is recommendation-eligible.
- The profile must have an `accepted_fact_link` for `operational_mass_kg` pointing to an accepted Claim with `claim_type = derived`.
- That derived Claim must depend through `claim_dependency` on the current accepted Tool `body_mass_kg` Claim and current accepted Battery `mass_kg` Claim.
- The normalized derived value must equal the accepted input masses according to the version-controlled derivation rule.
- A profile becomes invalid for recommendation use if its Tool/Battery relationship is inactive/superseded, an input mass Claim is superseded without re-derivation, or the derived Claim becomes disputed/superseded.

A Tool may have several active operational profiles, one for each accepted compatible Battery configuration. No profile should be selected silently when the installed Battery is unresolved.

---

## 5.4 `tether`

Tether/lanyard-specific operational fields.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `product_id` | UUID | no | PK + FK -> `product.id` |
| `rated_capacity_kg` | DECIMAL(12,6) | yes | Current accepted manufacturer rating |
| `min_length_mm` | DECIMAL(12,3) | yes | Minimum / retracted / shortest working length where meaningful |
| `max_length_mm` | DECIMAL(12,3) | yes | Maximum / extended / longest working length where meaningful |
| `tether_form` | ENUM | no | Default `unknown` |

### Constraints

- Parent `product.product_type` must equal `tether`.
- `rated_capacity_kg > 0` when populated.
- Lengths must be `> 0` when populated.
- If both lengths are known: `min_length_mm <= max_length_mm`.
- A fixed-length tether may use the same value for minimum and maximum length.
- A non-null rating used by recommendation logic requires an accepted manufacturer-backed Claim.
- The schema does not hard-code exactly two connection points.

---

## 5.5 `tether_leg`

Represents a branch or leg where a tether has multi-leg / multi-lanyard structure.

Simple two-ended tethers do not require a `tether_leg` row.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `tether_product_id` | UUID | no | FK -> `tether.product_id` |
| `parent_leg_id` | UUID | yes | Self-FK -> `tether_leg.id` for future nested branching |
| `label` | TEXT | yes | Human/internal leg label, e.g. `A`, `B` |
| `sequence_no` | SMALLINT | yes | Stable ordering where useful |
| `rated_capacity_kg` | DECIMAL(12,6) | yes | Optional leg-specific manufacturer rating |
| `min_length_mm` | DECIMAL(12,3) | yes | Optional leg-specific minimum length |
| `max_length_mm` | DECIMAL(12,3) | yes | Optional leg-specific maximum length |
| `notes` | TEXT | yes | Internal notes |

### Constraints

- `rated_capacity_kg > 0` when populated.
- Lengths must be `> 0` when populated.
- If both lengths are present: `min_length_mm <= max_length_mm`.
- `parent_leg_id`, when present, must belong to the same `tether_product_id`.
- A leg-specific rating does not automatically replace the whole-product rating; the applicable capacity rule decides which rating governs the candidate configuration.

---

## 5.6 `tool_attachment`

Operational fields for components that create or provide a tool-side tethering interface.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `product_id` | UUID | no | PK + FK -> `product.id` |
| `rated_capacity_kg` | DECIMAL(12,6) | yes | Current accepted manufacturer rating |
| `attachment_method_code` | TEXT | yes | Controlled technical description such as cinch, adhesive, clamp, wrap |

### Constraints

- Parent product type must equal `tool_attachment`.
- `rated_capacity_kg > 0` when populated.
- Rating used by recommendation logic requires an accepted manufacturer-backed Claim.
- Recommendation-ready use requires at least one suitable tool-side interface and one tether-side interface.

---

## 5.7 `anchor_attachment`

Operational fields for components that create or provide an anchorage-side tethering interface.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `product_id` | UUID | no | PK + FK -> `product.id` |
| `rated_capacity_kg` | DECIMAL(12,6) | yes | Current accepted manufacturer rating |
| `attachment_method_code` | TEXT | yes | Technical method, e.g. structural_wrap, belt_attachment |

### Constraints

- Parent product type must equal `anchor_attachment`.
- `rated_capacity_kg > 0` when populated.
- Rating used by recommendation logic requires an accepted manufacturer-backed Claim.
- Person versus structural anchoring remains runtime context/policy and is not inferred solely from `attachment_method_code`.

---

## 5.8 `container`

Operational fields for containment products used in a recommendation.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `product_id` | UUID | no | PK + FK -> `product.id` |
| `rated_capacity_kg` | DECIMAL(12,6) | yes | Current accepted manufacturer rating |
| `closure_type_code` | TEXT | yes | Expandable technical vocabulary |

### Constraints

- Parent product type must equal `container`.
- `rated_capacity_kg > 0` when populated.
- Rating used by recommendation logic requires an accepted manufacturer-backed Claim.

---

# 6. Physical interface tables

## 6.1 `physical_interface`

Represents a physical feature or connection interface on a tethering catalogue product.

Conceptually this table implements:

- `ToolInterfaceFeature` for tools;
- `TetherConnectionPoint` for tethers; and
- corresponding side-specific interfaces for attachments and containers.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `product_id` | UUID | no | FK -> `product.id` |
| `interface_role` | ENUM | no | Structural role |
| `interface_type_code` | TEXT | no | Expandable physical-interface vocabulary |
| `location_description` | TEXT | yes | e.g. handle base, rear eye, tether end |
| `captive_state` | ENUM | no | Default `unknown` |
| `connector_spec_id` | UUID | yes | FK -> `connector_spec.id` |
| `tether_side` | ENUM | yes | Only for tether connection points |
| `tether_leg_id` | UUID | yes | FK -> `tether_leg.id` |
| `sequence_no` | SMALLINT | yes | Stable ordering within product |
| `notes` | TEXT | yes | Internal notes |

### Role / product-type invariants

| Parent product type | Allowed interface roles |
|---|---|
| `tool` | `tool_feature` |
| `battery` | none in v0.1 |
| `tether` | `tether_connection` |
| `tool_attachment` | `tool_attachment_tool_side`, `tool_attachment_tether_side` |
| `anchor_attachment` | `anchor_attachment_tether_side`, `anchor_attachment_anchor_side` |
| `container` | `container_connection` |

These should be enforced by a catalogue validator and, where practical, by database triggers or generated constraints in the final physical implementation.

### Additional constraints

- `tether_side` must be non-null only when `interface_role = tether_connection`.
- `tether_leg_id` may only be populated for a tether connection and must reference a leg belonging to the same tether product.
- `connector_spec_id` should only be populated when the interface is a discrete connector whose reusable specification is represented by `connector_spec`.
- A product may have multiple physical interfaces of the same type.
- No global assumption is made that a tether has exactly two interfaces.

---

## 6.2 `interface_dimension`

Accepted geometry associated with a `physical_interface`.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `interface_id` | UUID | no | FK -> `physical_interface.id` |
| `dimension_type_code` | TEXT | no | Expandable dimension vocabulary |
| `value_mm` | DECIMAL(12,3) | no | Canonical millimetres |
| `notes` | TEXT | yes | Clarification where required |

### Constraints

- `value_mm > 0`.
- Prefer `UNIQUE(interface_id, dimension_type_code)` unless a future dimension genuinely requires multiple values of the same type.
- Every dimension used by compatibility reasoning must be traceable to an accepted Claim and evidence route.

---

# 7. Connector specification tables

## 7.1 `connector_spec`

Reusable specification for a discrete connector, especially carabiners reused across multiple tether products.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `manufacturer_id` | UUID | yes | FK -> `manufacturer.id`; nullable for internally identified generic connector specifications |
| `name` | TEXT | no | Connector specification name / internal identifier |
| `connector_type_code` | TEXT | no | e.g. carabiner |
| `material_code` | TEXT | yes | Known connector material |
| `locking_mode` | ENUM | no | Default `unknown` |
| `opening_action_count` | SMALLINT | yes | Number of deliberate opening actions where known |
| `swivel` | BOOLEAN | yes | Null means not established |
| `captive_eye` | BOOLEAN | yes | Null means not established |
| `manufacturer_description` | TEXT | yes | Source-faithful terminology |
| `notes` | TEXT | yes | Internal notes |

### Constraints

- `name` must be non-empty.
- `opening_action_count` must be between `1` and `3` when populated in v0.1; expand only if real products require another value.
- `locking_mode` and `opening_action_count` remain separate because terminology is not reliably interchangeable.
- Null boolean values mean the property has not been established; they must not be interpreted as `false`.

---

## 7.2 `connector_dimension`

Accepted geometry belonging to a reusable connector specification.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `connector_spec_id` | UUID | no | FK -> `connector_spec.id` |
| `dimension_type_code` | TEXT | no | e.g. `gate_opening`, `internal_width` |
| `value_mm` | DECIMAL(12,3) | no | Canonical millimetres |
| `notes` | TEXT | yes | Clarification where required |

### Constraints

- `value_mm > 0`.
- Prefer `UNIQUE(connector_spec_id, dimension_type_code)`.
- Dimensions used by recommendation logic require accepted Claim provenance.

---

# 8. Material table

## 8.1 `product_material`

Stores known constituent materials at the resolution supported by evidence.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `product_id` | UUID | no | FK -> `product.id` |
| `material_role_code` | TEXT | no | e.g. `lanyard_body` |
| `material_code` | TEXT | no | e.g. `polyester` or broader `polymer` |
| `notes` | TEXT | yes | Clarification |

### Constraints

- Material precision must not exceed the available evidence.
- Prefer uniqueness on `(product_id, material_role_code, material_code)`.
- Discrete connector material is stored on `connector_spec`, not duplicated as tether body material.

---

# 9. Evidence and provenance tables

## 9.1 `source`

An artefact used to support a Claim or Rule.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `source_type` | ENUM | no | `source_type` |
| `title` | TEXT | no | Source title |
| `publisher` | TEXT | yes | Publisher / issuing organisation |
| `url` | TEXT | yes | Where applicable |
| `document_revision` | TEXT | yes | Where available |
| `publication_date` | DATE | yes | Where available |
| `retrieved_at` | TIMESTAMP_TZ | no | When TetherLens obtained / checked the source |
| `archived_reference` | TEXT | yes | Optional archived copy or storage reference |
| `status` | ENUM | no | Default `active` |
| `notes` | TEXT | yes | Internal notes |

### Constraints

- `title` must be non-empty.
- `retrieved_at` is mandatory for all Source records.
- `url` is expected for public web sources but not required for internal measurements/tests.
- Superseding a source must not delete Claims or Evidence historically supported by it.

---

## 9.2 `claim`

An atomic statement accepted, proposed, disputed, rejected, or superseded by TetherLens.

Schema v0.1 uses a polymorphic subject reference because Claims can describe different operational entities.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `subject_type` | TEXT | no | Validated subject class |
| `subject_id` | UUID | no | ID of subject record |
| `property_key` | TEXT | no | Stable machine-readable property name |
| `value_status` | ENUM | no | Known / missing-state semantics |
| `value_kind` | ENUM | yes | Required only when `value_status = known` |
| `value_number` | DECIMAL(20,8) | yes | Normalized numeric value |
| `value_text` | TEXT | yes | Text or controlled code value |
| `value_boolean` | BOOLEAN | yes | Boolean value |
| `unit_code` | TEXT | yes | Normalized unit where relevant |
| `claim_type` | ENUM | no | Direct, measured, declared constraint, derived |
| `status` | ENUM | no | Default `proposed` |
| `supersedes_claim_id` | UUID | yes | Self-FK -> `claim.id` |
| `created_at` | TIMESTAMP_TZ | no | Default current time |
| `reviewed_at` | TIMESTAMP_TZ | yes | Acceptance/dispute/rejection review timestamp |
| `reviewed_by` | TEXT | yes | Reviewer identity until a user system exists |
| `notes` | TEXT | yes | Internal notes |

### Initial allowed `subject_type` values

```text
product
operational_mass_profile
physical_interface
tether_leg
connector_spec
interface_dimension
connector_dimension
product_material
declared_constraint
declared_relationship
```

The application repository layer must verify that `subject_id` exists in the table corresponding to `subject_type`.

A future physical database implementation may replace this polymorphic reference with a common entity registry if stronger database-level referential integrity proves worthwhile.

### Value constraints

If `value_status = known`:

- `value_kind` is required; and
- exactly one of `value_number`, `value_text`, `value_boolean` must be populated in accordance with `value_kind`.

If `value_status != known`:

- `value_kind` must be null;
- all three value fields must be null; and
- `unit_code` must be null.

A missing value must never be represented as numeric zero, empty text, or boolean false.

### Claim lifecycle

- `proposed` Claims may exist without being reflected in the operational catalogue.
- only `accepted` Claims may support an active accepted operational value;
- `disputed`, `rejected`, and `superseded` Claims remain preserved;
- `supersedes_claim_id` should link a newly reviewed replacement Claim to the prior Claim where applicable.

---

## 9.3 `evidence`

Relationship between a Source and either a Claim or a Rule.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `target_type` | ENUM | no | `claim` or `rule` |
| `claim_id` | UUID | yes | FK -> `claim.id` |
| `rule_id` | UUID | yes | FK -> `rule.id` |
| `source_id` | UUID | no | FK -> `source.id` |
| `evidence_method` | ENUM | no | Method by which source supports target |
| `source_location` | TEXT | yes | Page, section, table, URL fragment, etc. |
| `extracted_value` | TEXT | yes | Optional source-faithful extracted value |
| `extracted_unit` | TEXT | yes | Optional source-faithful unit |
| `strength` | ENUM | yes | Especially useful for rule evidence |
| `recorded_by` | TEXT | no | Person/process recording evidence |
| `recorded_at` | TIMESTAMP_TZ | no | Default current time |
| `notes` | TEXT | yes | Qualification |

### Constraints

- Exactly one of `claim_id` and `rule_id` must be populated.
- `target_type` must agree with the populated target FK.
- One Source may support many Claims and Rules.
- One Claim or Rule may have multiple Evidence rows.
- Deleting a Source should be restricted while Evidence references it; normal lifecycle handling should mark the Source unavailable or superseded instead.

---

## 9.4 `accepted_fact_link`

Connects a current operational fact to the accepted Claim that currently supports it.

This table does not store the operational value itself.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `subject_type` | TEXT | no | Same subject vocabulary as Claims |
| `subject_id` | UUID | no | Operational entity containing the accepted fact |
| `property_key` | TEXT | no | Operational property being supported |
| `claim_id` | UUID | no | FK -> `claim.id` |
| `linked_by` | TEXT | no | Reviewer/process creating link |
| `linked_at` | TIMESTAMP_TZ | no | Default current time |

### Constraints

- `UNIQUE(subject_type, subject_id, property_key)`.
- Referenced Claim must have `status = accepted`.
- Claim subject and property must correspond to the linked operational subject/property.
- The operational value and the accepted Claim value must normalize to the same value.
- Replacing an accepted operational value should atomically:
  1. preserve or supersede the old Claim;
  2. write the new accepted operational value; and
  3. move the `accepted_fact_link` to the new accepted Claim.

### Examples

```text
tool.body_mass_kg = 1.360777

accepted_fact_link
- subject_type = product
- subject_id = <tool product id>
- property_key = body_mass_kg
- claim_id = <accepted evidence-qualified tool-body mass claim>
```

```text
tool.operational_profile_requirement = required

accepted_fact_link
- subject_type = product
- subject_id = <tool product id>
- property_key = operational_profile_requirement
- claim_id = <accepted Tool operational-profile classification claim>
```

```text
operational_mass_profile.operational_mass_kg = 2.086525

accepted_fact_link
- subject_type = operational_mass_profile
- subject_id = <profile id>
- property_key = operational_mass_kg
- claim_id = <accepted derived operational-mass claim>
```

---

## 9.5 `claim_dependency`

Records the input Claims used by a derived Claim.

This table represents derivation dependencies, not source Evidence. The primitive input Claims retain their own Evidence records.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `derived_claim_id` | UUID | no | FK -> `claim.id` |
| `input_claim_id` | UUID | no | FK -> `claim.id` |
| `role_code` | TEXT | no | Stable role such as `tool_body_mass` or `battery_mass` |
| `sequence_no` | SMALLINT | yes | Optional deterministic input order |

### Constraints

- `derived_claim_id` must reference a Claim with `claim_type = derived`.
- `input_claim_id` must reference an accepted Claim when the derived Claim is accepted for operational use.
- A Claim must not depend directly or transitively on itself; cycle prevention belongs in the catalogue validator for v0.1.
- Prefer `UNIQUE(derived_claim_id, input_claim_id, role_code)`.
- For an accepted `operational_mass_kg` Claim, required roles are initially `tool_body_mass` and `battery_mass`.
- The validator must verify that those input Claims correspond to the Tool and Battery referenced by the parent `operational_mass_profile`.

This generic table can later support other persisted derivations without creating property-specific dependency columns.

---

# 10. Explicit manufacturer constraints and relationships

## 10.1 `declared_constraint`

Structured representation of an accepted, product-specific declared constraint.

Examples include:

- maximum operating temperature;
- explicit chemical restriction;
- requirement to use another named product;
- prohibition on a named use or relationship.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `product_id` | UUID | no | FK -> `product.id` |
| `interface_id` | UUID | yes | FK -> `physical_interface.id` when constraint is interface-specific |
| `constraint_key` | TEXT | no | Stable machine-readable constraint type |
| `operator` | ENUM | no | `constraint_operator` |
| `value_number` | DECIMAL(20,8) | yes | Numeric threshold where relevant |
| `value_text` | TEXT | yes | Text/code value where relevant |
| `value_boolean` | BOOLEAN | yes | Boolean value where relevant |
| `unit_code` | TEXT | yes | Unit for numeric values |
| `related_product_id` | UUID | yes | FK -> `product.id` for product-reference constraints |
| `claim_id` | UUID | no | FK -> accepted `claim.id` of type `declared_constraint` |
| `active` | BOOLEAN | no | Default true |
| `notes` | TEXT | yes | Qualification |

### Constraints

- `interface_id`, when populated, must belong to `product_id`.
- `claim_id` must reference an accepted Claim with `claim_type = declared_constraint`.
- The constraint's structured value must be consistent with the Claim.
- Exactly one relevant value representation should normally be populated for a constraint; the validator determines the expected value type from `constraint_key`.
- Inactive/superseded constraints remain preserved for traceability rather than deleted.

### Example constraint keys

```text
max_operating_temperature
min_operating_temperature
prohibited_exposure
requires_related_product
prohibits_related_product
```

New keys should be introduced only for source-backed reusable semantics, not vague application labels such as `suitable_for_offshore`.

---

## 10.2 `declared_relationship`

Stores explicit manufacturer-backed relationships between products and, where needed, specific interfaces.

This table is **not** a general compatibility matrix.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `subject_product_id` | UUID | no | FK -> `product.id` |
| `subject_interface_id` | UUID | yes | FK -> `physical_interface.id` |
| `object_product_id` | UUID | no | FK -> `product.id` |
| `object_interface_id` | UUID | yes | FK -> `physical_interface.id` |
| `relationship_type` | ENUM | no | `declared_relationship_type` |
| `claim_id` | UUID | no | FK -> accepted Claim |
| `active` | BOOLEAN | no | Default true |
| `notes` | TEXT | yes | Qualification |

### Constraints

- `subject_interface_id`, when populated, must belong to `subject_product_id`.
- `object_interface_id`, when populated, must belong to `object_product_id`.
- `claim_id` must reference an accepted Claim whose manufacturer Evidence supports the declared relationship.
- A `compatible_configuration` or `kit_relationship` used by an `operational_mass_profile` must relate a Tool to the exact Battery product used by that profile.
- A shared platform/voltage string alone is not sufficient to create a Tool/Battery compatibility relationship.
- No relationship row should be created merely because two tethering products happen to pass generic compatibility rules.

### Typical uses

```text
Manufacturer explicitly endorses Attachment A with Tether B
Manufacturer sells Tool Attachment C and Tether D as a kit
Manufacturer kit identifies Battery X as installed with Tool Y
Manufacturer explicitly identifies Battery X as compatible with Tool Y
Manufacturer explicitly restricts Product E from Product F
```

Absence of a row does not imply incompatibility, but a cordless operational profile requires a positive manufacturer-backed Tool/Battery relationship.

---

# 11. Rule table

## 11.1 `rule`

Metadata and provenance identity for deterministic recommendation logic.

| Field | Type | Null | Constraint / meaning |
|---|---|---:|---|
| `id` | UUID | no | PK |
| `rule_key` | TEXT | no | Stable semantic identifier |
| `version` | INTEGER | no | Positive version number |
| `name` | TEXT | no | Human-readable name |
| `rule_type` | ENUM | no | Hard constraint, compatibility, etc. |
| `description` | TEXT | no | What the rule does and why |
| `inputs_description` | TEXT | yes | Human-readable input contract |
| `outcome_description` | TEXT | yes | Human-readable outcome |
| `severity_code` | TEXT | yes | Optional controlled severity |
| `status` | ENUM | no | Default `draft` |
| `implementation_ref` | TEXT | no | Version-controlled code reference |
| `owner` | TEXT | yes | Responsible technical/domain owner |
| `notes` | TEXT | yes | Qualification |
| `created_at` | TIMESTAMP_TZ | no | Default current time |

### Constraints

- `version > 0`.
- `UNIQUE(rule_key, version)`.
- At most one active version of a `rule_key` should exist at a time.
- `implementation_ref` must resolve to a known code implementation during build/test validation.
- Rule evidence is attached through `evidence.rule_id`.

### Examples

```text
rule_key = mass.operational.tool_plus_battery
version = 1
rule_type = hard_constraint
implementation_ref = rules.mass.tool_plus_battery.v1
```

```text
rule_key = capacity.component_meets_object_mass
version = 1
rule_type = hard_constraint
implementation_ref = rules.capacity.component_meets_object_mass.v1
```

The database row does not contain executable comparison syntax.

---

# 12. Relationship summary

```text
Manufacturer
    │
    └── Product
          │
          ├── Tool ───────────────┐
          ├── Battery ────────────┤
          │                       ▼
          │             OperationalMassProfile
          │                       │
          ├── Tether ── TetherLeg│
          ├── ToolAttachment      │
          ├── AnchorAttachment    │
          └── Container           │
          │                       │
          ├── PhysicalInterface ── InterfaceDimension
          │          │
          │          └── ConnectorSpec ── ConnectorDimension
          │
          ├── ProductMaterial
          ├── DeclaredConstraint
          └── DeclaredRelationship ── Tool/Battery configuration basis

Source
  │
  └── Evidence ──> Claim
  │                  │
  │                  ├── AcceptedFactLink ──> current operational fact
  │                  └── ClaimDependency ───> input Claim(s)
  │
  └── Evidence ──> Rule ──> version-controlled implementation
```

---

# 13. Recommendation-readiness validation

Recommendation-readiness is evaluated by a catalogue validation service rather than stored as a mutable boolean.

The validator should return structured issues rather than only `true` / `false`.

Example logical result:

```text
product_id: ...
baseline_ready: false
issues:
  - code: OPERATIONAL_PROFILE_REQUIREMENT_UNKNOWN
    property: operational_profile_requirement
  - code: MISSING_OPERATIONAL_MASS_PROFILE
    property: operational_mass_kg
  - code: MISSING_MANUFACTURER_CAPACITY
    property: rated_capacity_kg
  - code: NO_SUPPORTED_INTERFACE_PATH
```

## 13.1 Tool baseline requirements

For a catalogued Tool to participate in load-based recommendations:

1. `tool.body_mass_kg` must be populated.
2. `body_mass_kg` must have an `accepted_fact_link` to an accepted Claim satisfying the physical-mass evidence policy.
3. `tool.operational_profile_requirement` must be explicitly classified as `not_required` or `required`; `unknown` is a hard readiness gap.
4. The non-`unknown` classification must have an `accepted_fact_link` to an accepted Claim for `operational_profile_requirement`. Missing Battery/profile data alone cannot establish `not_required`.
5. If `operational_profile_requirement = not_required`, `body_mass_kg` is the object's load-reasoning mass.
6. If `operational_profile_requirement = required`, the exact installed configuration must resolve to an active `operational_mass_profile` before load checks run.
7. Each accepted operational profile must reference an exact Battery product, an active manufacturer-backed Tool/Battery `declared_relationship`, and an accepted derived `operational_mass_kg` Claim.
8. The derived operational-mass Claim must depend on the current accepted Tool `body_mass_kg` Claim and Battery `mass_kg` Claim, and its value must match the deterministic derivation.
9. For a particular recommendation path, sufficient physical-interface information must exist to establish a valid tool-side connection directly or through a ToolAttachment.

A native tether point is not mandatory.

An incompletely classified Tool is not recommendation-ready merely because its body mass is known. The validator must not interpret absence of a Battery relationship or operational profile as evidence that the Tool is non-battery/non-configurable.

A Tool classified as requiring an installed Battery is likewise not recommendation-ready merely because its bare/body mass is known. If several valid Battery profiles exist and the installed Battery is unresolved, the engine must resolve the configuration or remain unable to perform the load check; it must not choose a profile arbitrarily.

## 13.2 Battery profile requirements

For a Battery to participate in an operational profile:

1. its exact Product identity/SKU must be established;
2. `battery.mass_kg` must be populated and linked to an accepted evidence-qualified Claim;
3. the Tool/Battery relationship used by the profile must be manufacturer-backed; and
4. the Battery mass Claim must be one of the explicit dependencies of the derived operational-mass Claim.

Battery recommendation-readiness is not evaluated independently as if the Battery were a tethering component; readiness is assessed through the Tool operational profile that uses it.

## 13.3 Load-bearing component baseline requirements

For Tethers, ToolAttachments, AnchorAttachments, and Containers where their rating is applicable:

1. `rated_capacity_kg` must be populated.
2. It must have an `accepted_fact_link`.
3. The linked accepted Claim must be supported by manufacturer information.
4. The product must expose the physical interfaces needed by the configuration path.

The introduction of Battery/operational-mass structures does **not** weaken the manufacturer-only evidence requirement for component rated capacity.

## 13.4 Interface readiness

A physical connection is recommendation-eligible only when compatibility can be established through at least one accepted route:

- published dimensions;
- internal measurement;
- explicit manufacturer relationship;
- manufacturer kit relationship;
- observed/confirmed tool geometry evaluated by a validated reusable rule; or
- another validated reusable interface rule.

The interface does not need every possible dimension populated.

It needs the facts required by the rule being applied.

## 13.5 Property-specific source validation

For physical tool-body or Battery mass, manufacturer evidence is preferred. Acceptable manufacturer Source types are initially:

```text
manufacturer_datasheet
manufacturer_webpage
manufacturer_manual
manufacturer_declaration
```

Where manufacturer mass is unavailable or incomplete, `secondary_published` may support an accepted physical-mass Claim when the resolved source is reputable, verified against the exact SKU/model, and recorded with `evidence_method = qualified_secondary_exact_sku`. Secondary mass must never be represented as manufacturer-stated evidence.

Physical Battery mass is eligible under this policy **only because the Battery is represented as an exact catalogue Product and is incorporated into a specific manufacturer-backed operational profile**. A mass value attached only to a battery family/platform label is insufficient.

The Tool's `operational_profile_requirement` classification must also be source-backed/reviewed. A classification Claim may be direct or derived from accepted product facts, but `not_required` may not be inferred from missing Battery/profile records or from ingestion simply failing to discover them.

For rated capacity of Tethers, ToolAttachments, AnchorAttachments, and Containers, manufacturer evidence remains mandatory. A manufacturer compatibility statement may support compatibility/relationship Claims but should not automatically be treated as the source of a rated load unless it actually states that rating and the review process accepts it as manufacturer technical information.

Internal measurement is acceptable for geometry but not as the normal source of catalogue tool/battery mass or manufacturer-rated component capacity.

---

# 14. Database-level invariants

The final physical implementation should enforce as many simple invariants in the database as practical.

## Required database constraints

- all PKs unique and non-null;
- all explicit FKs valid;
- `tool.operational_profile_requirement` is non-null and defaults to `unknown`;
- masses, capacities, and dimensions positive when populated;
- active operational profiles unique by Tool/Battery where applicable;
- tether and leg minimum length must not exceed maximum length;
- `opening_action_count` valid where populated;
- Evidence targets exactly one Claim or Rule;
- known Claims contain exactly one correctly typed value;
- unknown/not-published/not-established/not-applicable Claims contain no fake value;
- one current `accepted_fact_link` per operational property;
- Claim dependency rows unique and non-self-referential at the direct-row level;
- Rule key/version unique;
- physical-interface/tether-leg ownership consistent where enforceable.

## Application/catalogue-validator constraints

The following involve cross-table semantics and should initially be enforced in a validation/service layer, even if some later become database triggers:

- product subtype matches `product_type`;
- `operational_profile_requirement = unknown` blocks load-based Tool readiness;
- `not_required` and `required` operational-profile classifications each have a matching accepted classification Claim and accepted fact link;
- absence of Battery, relationship, or profile records does not establish `not_required`;
- Batteries used in profiles have exact catalogue identity and accepted mass Claims;
- Tool/Battery profile relationship references the same Tool/Battery and is manufacturer-backed;
- operational-mass derived Claim dependencies correspond to the current accepted Tool body-mass and Battery-mass Claims;
- operational-mass value equals the deterministic result of its input Claims;
- no cyclic Claim dependency graph;
- physical interface role is valid for its parent product type;
- accepted fact link subject/property matches its Claim;
- accepted operational value equals normalized accepted Claim value;
- mandatory tool/battery-mass Claims satisfy the physical-mass evidence policy, and rated-capacity Claims have acceptable manufacturer evidence;
- interface facts required by a compatibility rule have sufficient evidence;
- declared relationship interfaces belong to their declared products;
- constraint value shape matches `constraint_key`;
- active Rule implementation reference exists in code;
- recommendation-readiness requirements are met for the evaluated path.

---

# 15. Delete and supersession behaviour

TetherLens should favour historical preservation over destructive updates for evidence-bearing knowledge.

## Products

Products referenced by Claims, profiles, interfaces, or recommendations should normally be archived rather than deleted.

## Claims

Accepted, disputed, rejected, and superseded Claims should not be hard-deleted during normal catalogue maintenance.

## Sources

Unavailable or outdated Sources should change status rather than be deleted when Evidence references them.

## Evidence

Evidence should only be deleted to correct an ingestion mistake before acceptance or under an explicit administrative repair workflow.

## Accepted operational facts

When an accepted primitive physical value or operational-profile classification changes:

```text
old accepted Claim
        ↓
mark superseded
        ↓
new proposed Claim + Evidence
        ↓
review
        ↓
new Claim accepted
        ↓
update typed operational value/classification
        ↓
move AcceptedFactLink
        ↓
re-derive or revalidate any dependent operational profiles
```

A superseded Tool-body or Battery-mass Claim invalidates an operational profile until its derived Claim is recalculated/reviewed against the new accepted input.

A superseded `operational_profile_requirement` Claim makes the Tool non-ready for load reasoning until a replacement classification is accepted. Changing from `not_required` to `required` prevents further direct use of `body_mass_kg` and requires a valid operational profile.

The historical value, dependency chain, and source remain traceable.

---

# 16. Pressure-test configurations

The following examples test structure only unless explicitly tied to an established benchmark case. They are not tethering recommendations.

## 16.1 Configuration A: direct tool-to-tether interface

### Catalogue structure

```text
Tool A
- body_mass_kg = 1.40
- operational_profile_requirement = not_required
- operational_profile_requirement Claim = accepted
- native_tether_point_status = documented_present

PhysicalInterface A1
- product = Tool A
- role = tool_feature
- type = dedicated_eye
- captive_state = captive

InterfaceDimension
- interface = A1
- dimension_type = feature_section_diameter
- value_mm = 8

Tether B
- rated_capacity_kg = 2.30
- form = fixed

PhysicalInterface B1
- product = Tether B
- role = tether_connection
- tether_side = tool_side
- type = carabiner
- connector_spec = Connector C

PhysicalInterface B2
- product = Tether B
- role = tether_connection
- tether_side = anchor_side
- type = loop

Connector C
- type = carabiner
- locking_mode = auto_locking
- opening_action_count = 2

ConnectorDimension
- connector = C
- dimension_type = gate_opening
- value_mm = 18
```

### Engine behaviour

Candidate generation can attempt:

```text
Tool A / A1
    ↓
Tether B / B1
```

A reusable connector-to-eye rule evaluates the dimensions and other required geometry.

Load rule evaluates:

```text
2.30 kg >= 1.40 kg
```

No exact Tool A -> Tether B compatibility row is required.

### Schema result

Pass.

The schema can represent direct connection and reusable geometric compatibility without a compatibility matrix, while requiring explicit confirmation that no additional operational mass profile is needed.

---

## 16.2 Configuration B: tool has no native tether point and requires a ToolAttachment

### Catalogue structure

```text
Tool D
- body_mass_kg = 2.00
- operational_profile_requirement = not_required
- operational_profile_requirement Claim = accepted
- native_tether_point_status = observed_absent

PhysicalInterface D1
- role = tool_feature
- type = neck
- captive_state = non_captive

InterfaceDimensions
- min/max geometry required by applicable attachment rule

ToolAttachment E
- rated_capacity_kg = 4.00
- attachment_method_code = cinch

PhysicalInterface E1
- role = tool_attachment_tool_side
- type = loop

PhysicalInterface E2
- role = tool_attachment_tether_side
- type = ring

Tether F
- rated_capacity_kg = 3.00

PhysicalInterface F1
- role = tether_connection
- tether_side = tool_side
- type = carabiner
```

### Engine behaviour

Candidate path:

```text
Tool D feature D1
      ↓
ToolAttachment E tool-side interface E1
      ↓
ToolAttachment E tether-side interface E2
      ↓
Tether F tool-side connector F1
```

The engine applies:

1. reusable tool-feature/attachment geometry rule;
2. attachment capacity rule;
3. connector/ring compatibility rule; and
4. tether capacity rule.

`observed_absent` native tether point does not create a hard stop because another validated attachment path exists.

### Schema result

Pass.

The schema does not equate `no native tether point` with `not tetherable`.

---

## 16.3 Configuration C: branched / multi-leg tether

### Catalogue structure

```text
Tether G
- rated_capacity_kg = 5.00
- tether_form = multi_leg

TetherLeg G-A
- label = A

TetherLeg G-B
- label = B

PhysicalInterface G1
- role = tether_connection
- tether_side = anchor_side
- type = carabiner
- tether_leg_id = null

PhysicalInterface G2
- role = tether_connection
- tether_side = tool_side
- type = carabiner
- tether_leg_id = G-A

PhysicalInterface G3
- role = tether_connection
- tether_side = tool_side
- type = carabiner
- tether_leg_id = G-B
```

If the manufacturer publishes leg-specific properties, they may be stored on `tether_leg`:

```text
G-A.max_length_mm
G-A.rated_capacity_kg
G-B.max_length_mm
G-B.rated_capacity_kg
```

Otherwise the relevant whole-product Tether values remain authoritative.

### Engine behaviour

Candidate-generation code can reason about the individual connection points and legs without assuming `connector_a` and `connector_b`.

The applicable capacity rule determines whether the whole-product rating, a leg-specific rating, or another declared manufacturer limit governs the candidate.

### Schema result

Pass.

The model supports two, three, or more tether interfaces and does not require a schema change for branched products.

---

## 16.4 Configuration D: cordless Tool with interchangeable Batteries

This pressure test mirrors the structure already exercised by the Milwaukee ingestion benchmark.

### Catalogue structure

```text
Tool H
- sku = 2607-20
- body_mass_kg = 1.360777
- operational_profile_requirement = required
- operational_profile_requirement Claim = accepted

Battery J
- sku = 48-11-1828
- mass_kg = 0.725748

DeclaredRelationship H-J
- relationship_type = kit_relationship
- manufacturer-backed Claim establishes H + J configuration

OperationalMassProfile H+J
- tool_product_id = H
- battery_product_id = J
- relationship_id = H-J
- operational_mass_kg = 2.086525

Derived Claim P
- subject = OperationalMassProfile H+J
- property = operational_mass_kg
- value = 2.086525 kg

ClaimDependency P <- Tool H body-mass Claim
- role_code = tool_body_mass

ClaimDependency P <- Battery J mass Claim
- role_code = battery_mass
```

A second compatible Battery would create a second Battery Product and a second operational profile rather than overwriting `Tool H` with a different mass.

### Engine behaviour

The load rule receives the resolved profile mass:

```text
object_mass_used_for_reasoning = 2.086525 kg
```

It does not receive `1.360777 kg` merely because that is the Tool body's mass.

If the worker's installed Battery cannot be resolved among several profiles, the engine must resolve that configuration before applying load-capacity rules or return insufficient mass information for that candidate.

### Schema result

Pass.

The schema can bind physical Battery evidence to an exact SKU, represent manufacturer-backed Tool/Battery validity, retain the primitive Claim dependencies of the derived mass, and preserve multiple operational mass profiles.

---

## 16.5 Configuration E: incomplete operational-mass classification

This pressure test exists specifically to ensure that missing ingestion cannot silently authorize a bare-tool mass.

### Catalogue structure

```text
Tool K
- body_mass_kg = 1.50
- operational_profile_requirement = unknown
- no accepted operational_profile_requirement Claim
- no Battery relationship/profile discovered yet
```

### Engine behaviour

The load rule does **not** receive `1.50 kg`.

The catalogue validator returns:

```text
OPERATIONAL_PROFILE_REQUIREMENT_UNKNOWN
```

The Tool remains incomplete for load-based recommendations until the catalogue explicitly accepts either `not_required` or `required`.

### Schema result

Pass.

The absence of Battery evidence cannot be mistaken for evidence that no installed configuration contributes mass.

---

# 17. Recommended first rule implementations

Schema v0.1 should initially support a deliberately small deterministic rule set.

## Hard constraints / deterministic mass derivation

```text
mass.operational.tool_plus_battery
capacity.tether_meets_object_mass
capacity.tool_attachment_meets_object_mass
capacity.anchor_attachment_meets_object_mass
capacity.container_meets_contents_mass
constraint.explicit_manufacturer_limit
anchorage.method_viable
```

`mass.operational.tool_plus_battery` derives the reusable operational profile value; capacity rules consume that resolved value rather than recreating the derivation independently.

## Compatibility

Initial compatibility rules should be introduced only when required by the first real Batch 1 products, for example:

```text
compat.carabiner_to_eye
compat.carabiner_to_ring
compat.loop_or_cinch_to_tool_feature
compat.explicit_declared_relationship
```

Tool/Battery validity for an operational profile is not inferred through these generic interface rules; it must be manufacturer-backed through `declared_relationship`.

The exact geometry requirements must be determined from real products and validated domain reasoning rather than invented abstractly.

## Context preferences

```text
context.prefer_reduced_free_length_when_snag_risk_high
context.prefer_sufficient_reach
```

## Policy

Policy remains separate from technical suitability and may initially be represented as version-controlled configuration referencing rule keys.

---

# 18. Runtime objects intentionally outside the database

The following should initially be application/runtime structures.

## `GenericToolProfile`

Session-level only.

Typical fields:

```text
tool_category_code
mass_lower_kg
mass_upper_kg
mass_source_type
confirmed_interface_observations
```

Runtime user-provided values must not silently become persistent Claims.

## `Context`

Examples:

```text
snag_risk
required_reach
available_anchorage_method
environmental_exposure
```

## `Policy`

Initially static/version-controlled configuration.

## `CandidateConfiguration`

Ephemeral assembled path through a resolved Tool operational profile and tethering catalogue components/interfaces.

## `Recommendation`

Initially returned as structured engine output rather than persisted.

A later MVP phase may persist recommendation traces for testing and audit if required.

---

# 19. Suggested engine-facing read model

The recommendation engine should consume a simplified read model rather than raw persistence tables.

Example conceptual shape:

```text
ResolvedCatalogueTool
- product identity
- body_mass_kg
- operational_profile_requirement    # unknown | not_required | required
- operational_mass_profiles[]
    - profile_id
    - battery identity / SKU
    - operational_mass_kg
    - relationship basis
- physical interfaces[]
- accepted declared constraints[]

AvailableTether
- identity
- rated_capacity_kg
- length range
- form
- connection points[]
- connector specifications[]
- declared constraints[]

AvailableToolAttachment
AvailableAnchorAttachment
AvailableContainer
```

The runtime object must preserve `unknown` explicitly. It must not coerce missing/unknown classification to `not_required`.

For a resolved cordless configuration, the runtime object should carry one selected profile (or an explicit unresolved-profile state) so load rules cannot accidentally read `body_mass_kg` in place of configured mass.

The repository/data-access layer resolves provenance-backed operational values into this read model.

Evidence/dependencies are fetched when:

- validating the catalogue;
- explaining a recommendation;
- reviewing ingestion; or
- auditing a fact.

This maintains the architecture's separation between fast operational product data and detailed provenance.

---

# 20. Seed-data implications

The first machine-readable seed format should map closely to this schema but should not expose database implementation noise.

A seed set should be able to express:

```text
product identities, including supporting Batteries
subtype operational facts
explicit Tool operational-profile requirement classification
Tool/Battery manufacturer relationships
operational mass profiles
interfaces
interface dimensions
connector specs or connector-spec references
materials
declared constraints / relationships
sources
claims + evidence
claim dependencies for persisted derived facts
```

The seed validator should perform the same semantic checks as the database catalogue validator, including rejecting load-readiness when the Tool's operational-profile requirement remains `unknown`.

This makes it possible to use YAML/JSON files for Batch 1 while retaining a clean migration path into a relational database.

---

# 21. Deferred decisions

The following decisions should remain open until Batch 1 provides evidence that they matter.

## Database technology

PostgreSQL and SQLite can both represent Schema v0.1 adequately for an initial implementation.

Do not select a graph database merely because the domain contains relationships.

## Polymorphic Claim subjects

Schema v0.1 uses `subject_type + subject_id` for simplicity.

If database-level referential integrity across Claim subjects becomes operationally important, introduce a shared entity registry later.

Do not add that abstraction pre-emptively.

## Material hierarchy

Do not introduce a material ontology until environmental/chemical rules genuinely require inheritance such as:

```text
polyester -> polymer
```

## Standards structure

Standards declarations can initially be represented through Claims, Sources, Evidence, and declared constraints where applicable.

A dedicated standards schema should only be introduced when worker-facing or policy requirements justify it.

## Other configuration-dependent Tool components

Schema v0.1 explicitly models Battery-backed operational profiles because the benchmark has demonstrated that requirement. If another removable component materially changes operational mass, extend the configuration model only when a real product requires it rather than generalizing prematurely to arbitrary assemblies.

## Persistent derived Claims

Most compatibility and recommendation conclusions should still be computed at runtime.

Operational mass is a deliberate persisted exception because the configured mass is reused by safety-critical load checks and must preserve exact primitive dependencies.

## Generic rule DSL

Do not create one for the MVP.

Version-controlled deterministic code is the default.

---

# 22. Schema v0.1 acceptance criteria

The schema is ready for implementation when all of the following are true:

1. A real Batch 1 can represent tools, supporting Batteries, tethers, attachments, and connectors without schema-specific exceptions.
2. Tool-body and Battery mass are queryable directly and traceable to accepted evidence-qualified Claims, while component capacity remains traceable to accepted manufacturer-backed Claims.
3. Every Tool's operational-profile requirement defaults to `unknown`, becomes `not_required` or `required` only through an accepted classification Claim, and blocks load reasoning while unknown.
4. A cordless Tool can have multiple exact manufacturer-backed Battery configurations without collapsing them into one mass.
5. Each persisted operational-mass profile is traceable to exact Tool/Battery identities, a valid manufacturer relationship, and explicit primitive Claim dependencies.
6. Tool features and component connection points can participate in the same interface reasoning model.
7. Connector specifications can be reused across multiple products.
8. Multi-leg tethers require data rows rather than schema changes.
9. Manufacturer pairings/restrictions can be stored without creating a general tethering compatibility matrix.
10. Missing, not-published, not-established, and unknown operational-profile classification cannot be confused with a safe/direct body-mass path.
11. Recommendation-readiness can be calculated from mandatory facts, explicit configuration classification, configuration profiles, and evidence.
12. Hard constraints can be implemented deterministically against the typed catalogue and use configured operational mass rather than bare-tool mass where required.
13. Adding a second product batch does not require redesigning core tables or manually adding pairwise tethering compatibility rows for most products.

---

# 23. Immediate next implementation step

After this specification is accepted, the next work item should continue validating the schema against the live ingestion benchmark and subsequent seed-data work rather than treating the original pre-benchmark seed plan as frozen.

Batch work should deliberately pressure-test:

- explicit operational-profile requirement classification, including unknown/incomplete cases;
- cordless tools with multiple Battery operational profiles;
- exact-SKU evidence binding for Tool and Battery physical mass;
- manufacturer-backed configuration relationships;
- direct native interfaces;
- non-native but usable tool geometry;
- ToolAttachments;
- different connector geometries and locking/action characteristics;
- reusable connector specifications;
- mixed-manufacturer tethering paths;
- internal geometry measurement;
- incomplete secondary information; and
- multi-interface or multi-leg tether structures.

Any schema change discovered during Batch work should be judged against the core scalability test:

> Does this change model a reusable low-level fact or structure, or are we beginning to encode one-off application-specific exceptions?
