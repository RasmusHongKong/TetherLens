# Tool anatomy and attachment-selection semantics

## Status

Normative design proposal for the next Tool / ToolAttachment recommendation-model increment.

This document records the semantics validated against the current tool sample and representative ToolAttachments before changing the Python claim model, persistence schema, adapters, or recommendation implementation.

Where this document conflicts with the older exploratory wording in `tool-attachment-compatibility.md` or the current v0.1 `interface_type_code` examples in `technical-schema.md`, this document describes the intended migration direction. The migration should be implemented and tested explicitly rather than inferred from documentation alone.

## Design objective

TetherLens should minimize product-specific compatibility rules.

The preferred reasoning path is:

```text
resolved tool facts
  + tool anatomy / dimensions
  + operational mass
  + ToolAttachment facts / dimensions / capacity
  + tether interface facts
  + reusable compatibility rules
  -> technical suitability
```

Manufacturer endorsement, manufacturer instructions, evidence confidence, and site policy remain first-class, but they should not be substituted for physical compatibility reasoning unless the source establishes an actual technical requirement or prohibition.

The governing principle is:

> **Store low-level physical and declared facts once; derive attachment suitability through a small reusable rule set.**

## 1. Separate category, anatomy, role, and behaviour

Four concepts must not be collapsed into one vocabulary.

### Tool category

`tool_category_code` describes functional identity, not tetherability.

Examples:

```text
hammer
screwdriver
pliers
drill_driver
angle_grinder
```

A category may be hierarchical or have subtypes/capabilities, but recommendation logic should not depend on a perfect taxonomy.

Category becomes a technical eligibility predicate only when a product's function or behaviour matters in a way that cannot be reduced to lower-level physical facts, or when a validated technical restriction explicitly depends on the tool class.

### Tool anatomy / geometry

A `ToolInterfaceFeature` describes a physical feature that an attachment or tether connector can interact with.

Initial normalized feature kinds:

```text
through_opening
ring
handle
narrowed_section
external_section
surface
other
```

These are deliberately geometry-led.

Do not use manufacturer application terms such as `captive_hole`, `closed_handle`, `grip`, `neck`, or `waist` as mutually exclusive geometry primitives when the same meaning can be expressed through a feature kind plus qualifiers.

### Feature role / declared purpose

The physical shape of a feature is distinct from what it is intended to do.

Initial feature roles:

```text
tether_interface
accessory_mount
grip
working_part
other
unknown
```

Examples:

```text
Klein screwdriver tether hole
  feature_kind = through_opening
  feature_role = tether_interface
  captive_state = captive

Hilti accessory-installation opening
  feature_kind = through_opening
  feature_role = accessory_mount
  captive_state = captive
```

This prevents a generic through-opening from being silently promoted to a manufacturer-designed tether point.

### Feature qualifiers

Feature state should remain orthogonal to feature kind.

Existing `captive_state` remains useful:

```text
captive
non_captive
unknown
not_applicable
```

A later schema increment may add a structural-state qualifier where real rules require it, for example:

```text
fixed
removable
articulated
unknown
```

Do not add the qualifier until an implemented rule consumes it.

### Operational characteristics

Operational behaviour describes what moves during ordinary use. It is not tool category and not static geometry.

Initial attachment-relevant concepts justified by the current tool sample are:

```text
working_part_rotation
whole_tool_rotation
articulated_handles
```

Possible future characteristics such as impact or reciprocating motion should be added only when a real attachment-selection rule needs them.

A generic `rotating = true` flag is insufficient because a drill bit rotating while the tool body remains controlled is materially different from a manual screwdriver whose entire body is intentionally rotated.

## 2. Dimensions belong to the feature they describe

TetherLens does not need general CAD geometry.

Only dimensions consumed by an actual compatibility rule should be normalized.

Candidate tool-feature dimensions include:

```text
opening_clear_width
opening_clear_height
hole_diameter
section_diameter
section_width
section_height
section_circumference
available_attachment_length
ring_internal_width
ring_internal_height
surface_contact_width
surface_contact_height
```

Existing connector dimensions such as gate opening and internal connector geometry remain separate connector facts.

Overall product dimensions must not be mistaken for attachment-interface dimensions.

## 3. Native tether status and physical geometry are separate

`native_tether_point_status` remains a useful summary of what is documented or observed, but it does not replace explicit feature records.

A tool may have:

- a documented native tether feature;
- a physical feature that is not manufacturer-designated for tethering;
- no observed native tether feature but usable retrofit geometry; or
- insufficient information.

A manufacturer statement such as `Tether Capable: No` should be preserved as a manufacturer position. It must not automatically be translated into `prohibits_tethering = true` unless the source actually establishes a prohibition.

Likewise, absence of a native tether point must never imply that no ToolAttachment path exists.

## 4. Direct and retrofit paths coexist

Candidate generation should evaluate direct connection and retrofit ToolAttachment paths as alternatives.

Do not encode:

```text
native tether point present -> ToolAttachment candidates disabled
```

Instead:

```text
direct path
OR
one or more ToolAttachment paths
```

A direct path will often be simpler and may rank higher where connector fit, capacity, context, and policy are otherwise equal, but an attachment may still provide a useful interface transformation such as a larger ring or swivel.

## 5. Attachment selection needs bounded OR semantics

Atomic claims remain atomic. They should not be overloaded to represent Boolean expressions.

Compatibility composition should support a deliberately small structure:

```text
AttachmentEligibility
  shared_requirements: AND
  paths:
    - path A: AND
    - path B: AND
  prohibitions: AND NOT
```

Semantics:

- all predicates within one path are required;
- satisfying any one path is sufficient for the path portion of eligibility;
- shared requirements apply to every path;
- prohibitions can invalidate an otherwise matching path.

This is intentionally narrower than a general rules DSL.

Example: an attachment for a captive handle **or** captive hole:

```text
paths:
  - feature_kind = handle
    captive_state = captive

  - feature_kind = through_opening
    captive_state = captive
```

The current scalar `CandidateClaim` / `declared_constraint` representation cannot express this OR relationship on its own. Persistence and executable rule changes should therefore preserve atomic source claims and add composition at the rule/eligibility layer.

## 6. ToolAttachment selection class is orthogonal to attachment method

`attachment_method_code` describes how the ToolAttachment is retained on the tool.

Examples already established include:

```text
adhesive
mechanical_capture
cinch
wrap
through_feature
```

A separate small selection-class vocabulary describes what kind of tool-anatomy problem the solution addresses.

Initial classes justified by the current sample:

```text
captive_feature_attachment
narrowed_section_attachment
external_section_attachment
surface_bonded_attachment
surface_wrapped_attachment
rigid_feature_capture
```

These names are recommendation abstractions, not manufacturer product categories.

Examples:

```text
NLG 360 D Ring Loop
  selection_class = captive_feature_attachment
  attachment_method_code = cinch

NLG Mini Adhesive D Ring
  selection_class = surface_bonded_attachment
  attachment_method_code = adhesive

NLG Angle Grinder Bracket
  selection_class = rigid_feature_capture
  attachment_method_code = mechanical_capture
```

Do not make `direct` a ToolAttachment class. Direct connection is a separate attachment path with `tool_attachment_required = false`.

## 7. Technical suitability is separate from manufacturer position

Manufacturer statements must be preserved accurately, but brand should not become a compatibility rule by default.

Recommendation reasoning should maintain at least three independent dimensions:

```text
technical_status
manufacturer_status
policy_status
```

### Technical status

Derived from reusable physical facts and rules, including as applicable:

- operational mass;
- rated capacities;
- tool geometry;
- dimensional fit;
- connector/interface fit;
- installation requirements;
- movement/clearance requirements; and
- genuine technical prohibitions.

### Manufacturer status

Records what the relevant manufacturer actually states about the combination.

A useful semantic range is:

```text
explicitly_required
explicitly_endorsed
explicitly_compatible
contrary_to_manufacturer_instruction
explicitly_prohibited
no_statement
```

The exact persisted enum should be chosen during schema implementation after checking how it interacts with existing `declared_relationship_type` and `declared_constraint` records.

Important distinctions:

- `Use attachment X` can establish endorsement.
- `Use only attachment X` establishes a manufacturer instruction whose alternatives conflict with that instruction.
- Neither statement by itself proves that attachment Y is physically incompatible.
- `Do not use Y because it can detach from this housing` is evidence of a technical prohibition and may become a hard constraint if the scope is clear.

TetherLens should not encode a speculative motive such as vendor lock-in. It should store the manufacturer's statement and let technical compatibility be assessed independently.

### Policy status

Site or organisation policy remains separate from both technical compatibility and manufacturer position.

For example:

```text
technical_status = compatible
manufacturer_status = contrary_to_manufacturer_instruction
policy_status = prohibited
```

can be a valid result where site policy requires strict manufacturer-endorsed combinations.

## 8. Explicit category scope should be rare as a hard technical rule

A manufacturer category reference must not automatically become a hard whitelist.

Possible source meanings include:

- a closed technical restriction;
- a declared supported scope;
- illustrative examples; or
- marketing/category navigation.

A category should be a hard technical eligibility predicate only when:

1. the source clearly limits the product to that category **and** the limitation is treated as a technical requirement; or
2. a validated reusable safety rule depends on functional behaviour that cannot be reduced to lower-level facts.

Otherwise category may contribute manufacturer-support status or ranking without excluding a geometry-compatible mixed-brand candidate.

This distinction is especially important for manufacturer statements that specify their own ecosystem. TetherLens should surface the statement prominently without silently converting it into a claim that other brands are physically incompatible.

## 9. Required companion components and attachment assemblies

A tool-side attachment solution may contain more than one physical product.

For example, a web ToolAttachment may require a separate manufacturer-specified tape/wrap product to create the rated installed assembly.

The recommendation model should therefore move conceptually from:

```text
tool_attachment: optional single product
```

toward:

```text
tool_attachment_components[]
```

or an ephemeral:

```text
ToolAttachmentAssembly
  components[]
  provided_interface
```

A persisted assembly entity is not required yet. Existing manufacturer-backed product relationships may be sufficient to express required pairings while candidate generation composes the assembly at runtime.

A required companion product should only be substituted cross-brand when TetherLens has sufficient evidence that the resulting installed assembly still satisfies the applicable retention, capacity, geometry, and installation requirements. Mere apparent physical fit is not enough.

## 10. Evidence source for tool facts

The source appropriate for a fact depends on the fact.

### Good computer-vision / observation targets

Potentially observable from an image, with confidence and user confirmation where needed:

- broad tool category;
- presence/location of handles, openings, narrowed sections, external sections, and surfaces;
- captive versus non-captive geometry where visually resolvable;
- flat versus curved surface profile;
- gross structural state such as an obviously removable cover, where resolvable.

### Catalogue / manufacturer facts

Prefer catalogue or manufacturer evidence for:

- exact model/category identity;
- operational behaviour not reliably visible from a still image;
- manufacturer-declared feature purpose;
- manufacturer instructions and restrictions;
- rated capacities;
- manufacturer-supported pairings;
- exact configuration relationships.

### User/runtime facts

Use targeted user confirmation for states that are session-specific or difficult to establish from the catalogue/image, for example:

- current surface cleanliness/grease condition;
- exact installed battery where unresolved;
- a measurement required for a generic tool;
- confirmation of an ambiguous visible feature.

Computer vision should resolve physical facts; it should not directly decide that a particular SKU is suitable.

## 11. Candidate reasoning order

The intended tool-side reasoning sequence is:

```text
1. resolve tool/category/configuration
2. resolve operational mass
3. resolve relevant physical features + dimensions + behaviour
4. generate direct interface path(s)
5. generate ToolAttachment path(s) from reusable geometry rules
6. compose required companion components where applicable
7. check load, interface, dimensional, installation, and movement constraints
8. derive technical_status
9. assess manufacturer_status independently
10. apply context/ranking
11. apply policy
12. present recommendation + evidence/manufacturer qualifications
```

Manufacturer-specific pairings can still be generated as high-confidence candidates, but they should not prevent the engine from evaluating other candidates that independently satisfy technical rules unless an actual technical prohibition or policy rule applies.

## 12. Current representative cases

The design has been checked conceptually against the current tool sample plus representative ToolAttachments.

### NLG 360 D Ring Loop

Expresses a true geometry alternative:

```text
captive handle
OR
captive through-opening
```

This validates bounded OR-path semantics.

### Hilti SF 4-22 + retaining strap 2293133

The tool operating guidance gives a strong manufacturer-specified combination and identifies accessory-installation openings used by the retaining strap.

This validates:

- `through_opening` geometry;
- `feature_role = accessory_mount`;
- manufacturer position separate from geometry; and
- manufacturer-specific candidate generation without universal brand exclusion.

### Klein 6826INS screwdriver

The manufacturer provides a tether hole in the handle.

This validates:

- `through_opening` plus `feature_role = tether_interface`;
- direct and retrofit paths coexisting; and
- `whole_tool_rotation` as distinct from working-part rotation.

### Klein pliers contrast

One model has a manufacturer-provided tether ring while another similar pliers model does not.

This validates that category alone cannot select the attachment path.

### Ergodyne web ToolAttachment + required tape/wrap

This validates:

- multiple supported geometry paths;
- `narrowed_section` / non-captive external geometry normalization; and
- multi-component tool-side attachment assemblies.

## 13. Implementation sequence

The next implementation should remain narrow.

1. Migrate the tool-feature vocabulary in the domain/schema model from mixed anatomy labels toward `feature_kind` + qualifiers/role while preserving source wording.
2. Add the minimum claim/property vocabulary required to represent those facts.
3. Add bounded eligibility-path composition (`AND` inside a path, `OR` between paths) without a general DSL.
4. Separate technical compatibility results from manufacturer-position results.
5. Allow candidate configurations to contain multiple ToolAttachment components where a required pairing exists.
6. Add representative tests before extending manufacturer extraction broadly.
7. Keep existing atomic claims and provenance intact during the migration.

No adapter should gain SKU-specific branching merely to satisfy the representative cases.

## 14. Migration guardrails

- Do not infer `tether_interface` role merely from a hole/ring being visible.
- Do not infer technical incompatibility from different manufacturer names.
- Do not infer manufacturer endorsement from geometry compatibility.
- Do not convert category examples into closed whitelists without clear evidence.
- Do not encode OR alternatives as multiple independent `requires` constraints.
- Do not collapse a required multi-product attachment assembly into one unexplained product claim.
- Do not add dimensions, feature kinds, or operational characteristics until a real rule consumes them.
- Preserve raw manufacturer terminology and evidence even when normalized semantics differ.
