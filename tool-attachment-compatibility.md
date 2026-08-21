# ToolAttachment compatibility semantics

## Status

Initial reusable claim semantics for ToolAttachment applicability, required tool geometry, and installation constraints.

This document complements `attachment-method-vocabulary.md`. `attachment_method_code` continues to describe only the primary physical retention mechanism. Compatibility and installation requirements are represented independently.

## Compatibility axes

A ToolAttachment may depend on several independent facts:

1. **Declared tool-class scope** — the manufacturer may limit the product to a class such as angle grinders.
2. **Required tool geometry** — the attachment may require a handle, captive hole, neck, waist, or another reusable physical feature.
3. **Dimensional fit** — a compatible feature may still need to fall inside published or measured dimensional limits.
4. **Operational behaviour** — rotating or moving tool parts may affect which attachment methods are viable.
5. **Installation constraints** — surface condition, prohibited attachment locations, cure time, pre-use checks, or related requirements.
6. **Rated capacity and paired-product limits** — ordinary load and lanyard constraints remain separate mandatory checks.

These axes are complementary. Geometry must not silently broaden a manufacturer's declared application scope.

Example:

```text
NLG 101691 Angle Grinder Bracket
- attachment_method_code = mechanical_capture
- applicable_tool_category_code = angle_grinder
- required_tool_feature_type = handle
```

A non-angle-grinder tool with a handle does not satisfy the product's declared scope merely because its geometry resembles the required feature.

## Candidate-claim semantics

Structured manufacturer restrictions use the existing persisted `declared_constraint` concept. The ingestion candidate model now supports optional:

```text
claim_type = declared_constraint
constraint_operator = requires | prohibits | gte | ...
```

The fields remain optional during migration so existing adapters are not incorrectly reclassified without a dedicated pass.

Initial reusable property keys introduced by the NLG examples are:

```text
applicable_tool_category_code
required_tool_feature_type
supported_surface_profile
installation_surface_profile
required_surface_condition
prohibited_tool_part_type
minimum_bond_time_h
pre_use_attachment_test_required
```

These are product-level candidate claims for now. Persistence may later scope a constraint to the ToolAttachment's tool-side `physical_interface` using the existing `declared_constraint.interface_id` relationship.

## NLG 101691

The Angle Grinder Bracket is a specialist product. Its reusable semantics therefore combine tool class and geometry rather than reducing compatibility to the generic existence of a handle.

```text
applicable_tool_category_code = angle_grinder
  claim_type = declared_constraint
  operator = requires

required_tool_feature_type = handle
  claim_type = declared_constraint
  operator = requires
```

`handle` describes the required physical feature. `angle_grinder` preserves the manufacturer's declared application scope.

## NLG 101481

The Mini Adhesive D Ring uses adhesive retention, but correct installation also depends on atomic manufacturer constraints. Current instructions support structured requirements including:

```text
installation_surface_profile = flat
required_surface_condition = clean
required_surface_condition = grease_free
prohibited_tool_part_type = removable_cover_or_door
minimum_bond_time_h >= 24
pre_use_attachment_test_required = true
```

These are independent constraints and should not be collapsed into one free-text `attachment_constraints` value.

### Flat versus curved manufacturer wording

Current NLG descriptive product copy states that the adhesive D Ring can work on curved surfaces, while current product instructions prescribe installation on a flat surface.

TetherLens preserves these as different predicates:

```text
supported_surface_profile = curved        # descriptive capability claim
installation_surface_profile = flat      # prescriptive installation constraint
```

The prescriptive installation constraint governs current recommendation eligibility. The broader curved-surface capability remains retained as manufacturer evidence but must not expand eligibility until the scope tension is reconciled.

This follows a general conflict policy:

1. determine whether two statements address the same predicate and scope;
2. prefer the source authoritative for that predicate (for example, installation instructions for installation procedure);
3. then consider exact product identity, revision/recency, and specificity;
4. preserve unresolved same-priority contradictions rather than silently selecting the more permissive or more conservative wording; and
5. do not use disputed evidence to expand a safety-relevant eligibility envelope.

## Wider tool-selection design evidence

Industry guidance reviewed during this workstream consistently treats tool geometry as one input alongside tool type, weight, attachment-point form, connection method, length/reach, and task/environment constraints. The following sources are useful design references for a later dedicated tool-anatomy and attachment-selection vocabulary pass:

- Leading Edge Safety — *What Is Tool Tethering? A Complete Safety Guide for Construction*
- FallTech — *Dropped Object Prevention*
- Ergodyne — *How to Create Tool Attachment Points for Tool Tethering*
- Ergodyne — *Four Factors for Determining Tool Tethers*
- Enfield Safety — *Tool Tethering Matching*
- CMT — *NLG Tool Tethering / Dropped Object Prevention Guide*

The first dedicated implementation should remain narrower than a full rule-engine redesign. Future work can expand the reusable vocabulary only when representative products require it.
