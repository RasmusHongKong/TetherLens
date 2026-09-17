# Tool anatomy and attachment-selection semantics

## Status

Normative design guidance for Tool / ToolAttachment recommendation semantics.

This document records the semantics validated against the current tool sample and representative ToolAttachments. Where it conflicts with older exploratory wording or the v0.1 `interface_type_code` examples in `technical-schema.md`, this document describes the intended migration direction.

`compatibility-evidence-and-inference.md` governs the complementary case where accepted manufacturer evidence establishes a known installation relationship but does not establish enough physical geometry to compile a reusable eligibility rule. In that case TetherLens must preserve the known relationship without inventing a more specific feature kind, captive state or dimensions.

## Design objective

TetherLens should minimize product-specific compatibility rules.

The preferred reasoning path, where the evidence supports it, is:

```text
resolved tool facts
  + tool anatomy / dimensions
  + operational mass
  + ToolAttachment facts / dimensions / capacity
  + tether interface facts
  + reusable compatibility rules
  -> technical suitability
```

Manufacturer endorsement, manufacturer instructions, evidence confidence, and site policy remain first-class. When lower-level physical facts are incomplete, a narrowly scoped manufacturer-documented installation may establish one known-valid route without becoming a generic technical rule or an exclusion of other independently supported routes.

The governing principle is:

> **Store the strongest low-level physical and declared facts the source actually establishes; derive reusable suitability where justified, and preserve narrower evidence-bound relationships where it is not.**

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

A `ToolInterfaceFeature` describes one physical feature that an attachment or tether connector can interact with.

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

These are deliberately geometry-led, but `other` is important when the source establishes a real installation location or role without enough evidence to classify its physical form more specifically.

Do not use manufacturer application terms such as `captive_hole`, `closed_handle`, `grip`, `neck`, or `waist` as mutually exclusive geometry primitives when the same meaning can be expressed through a feature kind plus qualifiers. Equally, do not force a manufacturer term into a known geometry primitive when the source does not establish that geometry.

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

Hilti accessory-installation openings
  feature_kind = other
  feature_role = accessory_mount
  captive_state = unknown
```

The Klein evidence establishes the physical form. The current Hilti evidence establishes the named accessory-installation location and its role, but not `through_opening`, captive state, exact dimensions, or ring/eye form.

This distinction prevents a generic physical feature from being silently promoted to a manufacturer-designed tether point and prevents a manufacturer-named location from being silently promoted to geometry the source never stated.

### Feature qualifiers

Feature state should remain orthogonal to feature kind.

Existing `captive_state` remains useful:

```text
captive
non_captive
unknown
not_applicable
```

`unknown` is a real evidence state, not an invitation to select the value that makes a candidate rule convenient.

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

Every tool-feature dimension is scoped to one `ToolInterfaceFeature`. A dimension predicate must therefore be evaluated against the same feature instance as the geometry, role, location, and state predicates that define the relevant installation path.

Existing connector dimensions such as gate opening and internal connector geometry remain separate connector facts.

Overall product dimensions must not be mistaken for attachment-interface dimensions. A compatibility list or documented pairing must not be reverse-engineered into an invented feature dimension merely because a dimension would explain the relationship.

## 3. Native tether status and physical geometry are separate

`native_tether_point_status` remains a useful summary of what is documented or observed, but it does not replace explicit feature records.

A tool may have:

- a documented native tether feature;
- a physical feature that is not manufacturer-designated for tethering;
- no observed native tether feature but usable retrofit geometry;
- a manufacturer-defined installation location whose exact geometry is not established; or
- insufficient information.

A manufacturer statement such as `Tether Capable: No` should be preserved as a manufacturer assessment from that issuing manufacturer. It must not automatically be translated into `prohibits_tethering = true` unless the source actually establishes a prohibition.

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

A documented manufacturer installation is one possible ToolAttachment path. It does not suppress other ToolAttachment paths that qualify through reusable technical eligibility or their own accepted installation evidence.

## 5. Attachment selection needs bounded OR semantics with feature binding

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
- prohibitions can invalidate an otherwise matching path; and
- all feature-local predicates within one path must resolve against the same bound `ToolInterfaceFeature` unless the path explicitly declares more than one named feature binding.

### Feature-scoped path binding

A path should bind a feature variable before evaluating feature-local predicates.

Example: an attachment for a captive handle **or** captive through-opening:

```text
paths:
  - bind feature = one ToolInterfaceFeature
    where:
      feature.feature_kind = handle
      feature.captive_state = captive

  - bind feature = one ToolInterfaceFeature
    where:
      feature.feature_kind = through_opening
      feature.captive_state = captive
```

This must not be evaluated as independent tool-level facts.

For example, a tool with:

```text
feature A:
  feature_kind = handle
  captive_state = non_captive

feature B:
  feature_kind = through_opening
  captive_state = captive
```

must **not** satisfy the captive-handle path by combining `feature_kind = handle` from feature A with `captive_state = captive` from feature B.

The same binding rule applies to all feature-local facts, including:

```text
feature_kind
feature_role
captive_state
location / part identity
feature dimensions
surface profile
structural state
feature-local installation requirements
feature-local prohibitions
```

A feature-local prohibition must invalidate only the path using the bound feature to which the prohibition applies, unless the source explicitly states a tool-wide prohibition.

### Multiple feature bindings

The initial rule set should assume one bound tool feature per eligibility path because that covers the representative cases.

If a future real product requires two distinct features simultaneously, the rule should introduce explicit named bindings, for example:

```text
bind primary_handle = one ToolInterfaceFeature
bind secondary_feature = another ToolInterfaceFeature

where:
  primary_handle.feature_kind = handle
  secondary_feature.feature_kind = through_opening
```

The implementation must never obtain multi-feature semantics accidentally by joining unrelated atomic facts.

This feature-binding requirement is narrower than a general rule DSL. It is a subject-scoping safeguard needed to preserve the meaning of atomic anatomy facts.

The scalar `CandidateClaim` / `declared_constraint` representation cannot express either the OR relationship or the feature binding on its own. Source claims should remain atomic while composition occurs at the rule/eligibility layer.

## 6. Evidence-bound installation is distinct from reusable eligibility

When accepted first-party evidence establishes that one concrete ToolAttachment installs at one concrete resolved Tool feature, but does not establish enough geometry to compile a reusable eligibility rule, TetherLens may retain an exact `ToolAttachmentInstallationBinding`.

This binding is positive evidence for one known route. It is not a claim that every Tool with the same feature role accepts the attachment, not a claim that the feature has missing geometry, and not a universal SKU-pair compatibility rule.

The ordinary geometry-backed path and the evidence-bound path therefore coexist:

```text
reusable feature/dimension eligibility
OR
exact evidence-bound Tool/product/feature installation
```

At recommendation-run time the evidence-bound route may be projected through the ordinary generator using the already-resolved exact feature. The original installation binding remains retained separately as provenance; the execution projection must never be persisted or reused as generic technical compatibility.

## 7. ToolAttachment selection class is orthogonal to attachment method

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

## 8. Technical suitability is separate from manufacturer assessments

Manufacturer statements must be preserved accurately, but brand should not become a compatibility rule by default.

Recommendation reasoning should maintain separate dimensions:

```text
technical_status
manufacturer_assessments[]
policy_status
```

There is intentionally no single authoritative `manufacturer_status` scalar for a mixed-manufacturer candidate.

### Technical status

Technical status is derived from reusable physical facts and rules, including as applicable:

- operational mass;
- rated capacities;
- tool geometry;
- dimensional fit;
- connector/interface fit;
- installation requirements;
- movement/clearance requirements; and
- genuine technical prohibitions.

An evidence-bound installation is not evidence that all generic technical predicates are known to pass. It establishes the documented installation path at the scope supported by the source. Other independent hard checks such as load capacity and downstream connection compatibility still run normally.

### Manufacturer assessments are issuer-scoped

Each manufacturer statement about a candidate configuration must retain the issuing party and the scope of the statement.

Conceptually:

```text
ManufacturerAssessment
  issuer_manufacturer_id
  scope
  position
  claim_or_evidence_ref
```

Possible `scope` examples include:

```text
tool_to_attachment
attachment_to_tool_class
attachment_to_tether
full_candidate_configuration
installation_method
```

A useful `position` range is:

```text
explicitly_required
explicitly_endorsed
explicitly_compatible
contrary_to_manufacturer_instruction
explicitly_prohibited
```

`no_statement` should normally be derived from the absence of an applicable assessment from the manufacturer being queried rather than stored as an evidence row.

A mixed-brand candidate may legitimately have simultaneous assessments such as:

```text
technical_status = compatible

manufacturer_assessments:
  - issuer = Hilti
    scope = tool_to_attachment
    position = contrary_to_manufacturer_instruction

  - issuer = attachment maker
    scope = attachment_to_tool_class
    position = explicitly_compatible

policy_status = permitted
```

Neither assessment overwrites the other.

This is necessary because policies may query a specific issuing party, for example:

```text
require tool-manufacturer endorsement
require attachment-manufacturer approval
allow technically compatible mixed-brand systems
```

A default aggregate manufacturer status should **not** be derived. An aggregate may only be produced where a specific policy or user-facing rule defines how issuer-scoped assessments should be combined.

### Endorsement versus prohibition

The following statements are materially different:

```text
Use attachment X.
```

This may establish endorsement from the issuing manufacturer.

```text
Use only attachment X.
```

This establishes an instruction from the issuing manufacturer whose alternatives conflict with that manufacturer's instruction, but it does not by itself prove that attachment Y is physically incompatible.

```text
Do not use attachment Y because it can detach from this housing.
```

This establishes a manufacturer prohibition and may also support a technical hard constraint where the technical scope and causal basis are sufficiently clear.

TetherLens should not encode a speculative motive such as vendor lock-in. It should store who said what, about which scope, with source evidence, and let technical compatibility be assessed independently.

### Policy status

Site or organisation policy remains separate from both technical compatibility and manufacturer assessments.

## 9. Explicit category scope should be rare as a hard technical rule

A manufacturer category reference must not automatically become a hard whitelist.

Possible source meanings include:

- a closed technical restriction;
- a declared supported scope;
- illustrative examples; or
- marketing/category navigation.

A category should be a hard technical eligibility predicate only when:

1. the source clearly limits the product to that category **and** the limitation is established as a technical requirement; or
2. a validated reusable safety rule depends on functional behaviour that cannot be reduced to lower-level facts.

Otherwise category may contribute an issuer-scoped manufacturer assessment or ranking signal without excluding a geometry-compatible mixed-brand candidate.

## 10. Required companion components and attachment assemblies

A tool-side attachment solution may contain more than one physical product.

For example, a web ToolAttachment may require a separate manufacturer-specified tape/wrap product to create the rated installed assembly.

The recommendation model therefore supports runtime ToolAttachment assemblies rather than assuming exactly one ToolAttachment product.

For evidence-bound multi-product assemblies, each provided interface must be owned by an exact selected component product. Product-scoped manufacturer connection evidence is matched against the owner of the specific target interface, not merely against assembly-wide product membership. Single-product ownership may be inferred; multi-product ownership must be explicit and complete.

A required companion product should only be substituted cross-brand when TetherLens has sufficient evidence that the resulting installed assembly still satisfies the applicable retention, capacity, geometry, and installation requirements. Mere apparent physical fit is not enough.

## 11. Evidence source for tool facts

The source appropriate for a fact depends on the fact.

### Good computer-vision / observation targets

Potentially observable from an image, with confidence and user confirmation where needed:

- broad tool category;
- presence/location of handles, openings, narrowed sections, external sections, and surfaces;
- captive versus non-captive geometry where visually resolvable;
- flat versus curved surface profile; and
- gross structural state such as an obviously removable cover, where resolvable.

Computer-vision observations that describe one physical feature must remain grouped under the same feature instance. Confidence in `handle` and confidence in `captive` are not sufficient to create a captive handle unless both observations refer to the same resolved feature.

### Catalogue / manufacturer facts

Prefer catalogue or manufacturer evidence for:

- exact model/category identity;
- operational behaviour not reliably visible from a still image;
- manufacturer-declared feature purpose;
- manufacturer instructions and restrictions;
- rated capacities;
- manufacturer-supported pairings; and
- exact configuration relationships.

Manufacturer statements must retain issuing manufacturer identity and scope.

### User/runtime facts

Use targeted user confirmation for states that are session-specific or difficult to establish from the catalogue/image, for example:

- current surface cleanliness/grease condition;
- exact installed battery where unresolved;
- a measurement required for a generic tool; and
- confirmation of an ambiguous visible feature.

Runtime confirmation should identify the feature being confirmed where the answer is feature-local.

Computer vision should resolve physical facts; it should not directly decide that a particular SKU is suitable.

## 12. Candidate reasoning order

The intended tool-side reasoning sequence is:

```text
1. resolve tool/category/configuration
2. resolve operational mass
3. resolve distinct physical feature instances + known dimensions + behaviour
4. generate direct interface path(s)
5. generate reusable ToolAttachment eligibility path(s) with explicit feature binding
6. add accepted evidence-bound ToolAttachment installation path(s) where needed
7. compose required companion components where applicable
8. check load, interface, dimensional, installation, and movement constraints that apply
9. derive technical_status where reusable technical evidence permits it
10. retain issuer-scoped manufacturer assessments / known installation evidence
11. apply context/ranking
12. apply policy
13. present recommendation + evidence/manufacturer qualifications
```

Manufacturer-specific documented routes can be high-confidence candidate paths, but they must not prevent the engine from evaluating other candidates that independently satisfy technical rules or their own accepted evidence unless an actual technical prohibition or policy rule applies.

## 13. Current representative cases

### NLG 360 D Ring Loop

Expresses a true geometry alternative:

```text
one feature that is:
  captive handle

OR

one feature that is:
  captive through-opening
```

This validates both bounded OR-path semantics and feature-instance binding.

### Hilti SF 4-22 + retaining strap 2293133

The operating instructions identify `installation openings for accessories`, prescribe retaining strap `2293133`, and pair that installed strap with tether `2261970`.

Current evidence validates:

```text
feature_kind = other
feature_role = accessory_mount
captive_state = unknown
location_description = "installation openings for accessories"
```

It does **not** validate `through_opening` geometry, captive state, dimensions, or ring/eye form.

The documented Tool-to-strap relationship is therefore retained as an exact evidence-bound installation. The strap exposes only the functional tether-side `attachment_point` established by first-party evidence. The tether-to-strap manufacturer declaration is product-scoped and applies only to the interface owned by the documented strap product.

This case validates that incomplete geometry does not require either abstention or fabricated physical facts: TetherLens can carry one known manufacturer-documented route into the ordinary recommendation pipeline while leaving other independently supported alternatives available.

### Klein 6826INS screwdriver

The manufacturer provides a tether hole in the handle.

This validates:

- `through_opening` plus `feature_role = tether_interface` on one feature instance;
- direct and retrofit paths coexisting; and
- `whole_tool_rotation` as distinct from working-part rotation.

### Klein pliers contrast

One model has a manufacturer-provided tether ring while another similar pliers model does not.

This validates that category alone cannot select the attachment path.

### Ergodyne web ToolAttachment + required tape/wrap

This validates:

- multiple supported geometry paths;
- `narrowed_section` / non-captive external geometry normalization;
- feature-bound installation predicates; and
- multi-component tool-side attachment assemblies.

## 14. Current implementation and next increments

The reusable core now supports:

- normalized `ToolInterfaceFeature` records with feature-local facts;
- bounded eligibility paths and exact feature binding;
- feature-bound dimensional predicates;
- runtime multi-component ToolAttachment assemblies;
- retained ToolAttachment installation-method provenance;
- issuer-scoped connection/manufacturer evidence;
- exact evidence-bound Tool/product/feature installation paths where reusable geometry is insufficient; and
- interface-to-product ownership for product-scoped connection evidence in evidence-bound assemblies.

The next increments should not manufacture a generic Hilti rule from the one documented pairing. Higher-value follow-up work is:

- attach explicit epistemic/provenance basis to reusable rules when a real inference workflow needs it;
- test bounded cross-product pattern inference against additional catalogue evidence before promoting any hypothesis to a reusable rule;
- add configuration-component/assembled-configuration feature ownership only when a real attachment case requires it; and
- validate the evidence-bound pattern on another manufacturer/product family rather than broadening it through SKU-specific branches.

## 15. Migration and implementation guardrails

- Do not infer `tether_interface` role merely from a hole/ring being visible.
- Do not infer `through_opening`, captive state or dimensions from a manufacturer-named installation location unless the source establishes those physical facts.
- Do not infer technical incompatibility from different manufacturer names.
- Do not infer manufacturer endorsement from geometry compatibility.
- Do not convert category examples into closed whitelists without clear evidence.
- Do not encode OR alternatives as multiple independent `requires` constraints.
- Do not combine feature-local predicates from different `ToolInterfaceFeature` instances to satisfy one eligibility path.
- Do not apply a feature-local prohibition to another feature or to the whole tool unless the source scope supports that expansion.
- Do not collapse manufacturer positions from different issuers into one scalar status.
- Do not derive a default aggregate manufacturer status; aggregation requires explicit policy or presentation semantics.
- Do not collapse a required multi-product attachment assembly into one unexplained product claim.
- Do not apply product-scoped connection evidence to an interface owned by another selected assembly component.
- Do not promote one documented product relationship into a generic eligibility rule without independent support for the rule predicates.
- Do not add dimensions, feature kinds, or operational characteristics until a real rule consumes them.
- Preserve raw manufacturer terminology, issuing party, subject scope, model-local source context, product/interface ownership and evidence provenance even when normalized semantics differ.
