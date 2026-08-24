# ToolAttachment compatibility semantics

## Status

Reusable claim semantics for ToolAttachment applicability, required tool geometry, installation constraints, and manufacturer-position handling.

This document complements `attachment-method-vocabulary.md` and `tool-anatomy-selection-semantics.md`.

`attachment_method_code` continues to describe only the primary physical retention mechanism. Tool anatomy, dimensional fit, technical suitability, manufacturer position, and policy are represented independently.

Where older wording treated manufacturer-declared application scope as a universal technical exclusion, `tool-anatomy-selection-semantics.md` now governs: manufacturer instructions must be preserved, but brand/category declarations do not automatically prove physical incompatibility.

## Compatibility axes

A ToolAttachment may depend on several independent facts:

1. **Tool anatomy / geometry** — the attachment may require a handle, through-opening, narrowed section, external section, surface, or another reusable physical feature.
2. **Dimensional fit** — a geometrically relevant feature may still need to fall inside published or measured dimensional limits.
3. **Operational behaviour** — whole-tool rotation, working-part rotation, articulated handles, or other validated behaviours may affect viability.
4. **Installation constraints** — surface condition, prohibited attachment locations, cure time, companion products, pre-use checks, or related requirements.
5. **Rated capacity and paired-product limits** — ordinary load and lanyard constraints remain separate mandatory checks.
6. **Manufacturer position** — the manufacturer may require, endorse, support, discourage, or prohibit a particular configuration.
7. **Policy** — a site or organisation may impose stricter combination requirements than the technical compatibility rules.

These axes are complementary.

The recommendation engine should derive technical compatibility primarily from low-level physical facts. Manufacturer position should normally qualify the result rather than replace the physical analysis, unless the source establishes a genuine technical prohibition or requirement that cannot be represented by lower-level facts.

## Geometry-first reasoning

Prefer reusable predicates such as:

```text
feature_kind = through_opening
captive_state = captive
```

or:

```text
feature_kind = narrowed_section
section_diameter within published limits
```

rather than product-specific compatibility entries.

Tool category may still matter when function/behaviour cannot be reduced to geometry, but category references in manufacturer material must not automatically become closed hard whitelists.

## Candidate-claim semantics

Structured manufacturer restrictions continue to use the existing persisted `declared_constraint` concept where they are genuinely atomic.

The ingestion candidate model supports optional:

```text
claim_type = declared_constraint
constraint_operator = requires | prohibits | gte | ...
```

The fields remain optional during migration so existing adapters are not incorrectly reclassified without a dedicated pass.

Existing reusable property keys include:

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

These keys are transitional. The next schema increment should migrate geometry-bearing properties toward the normalized feature model in `tool-anatomy-selection-semantics.md` rather than expanding `required_tool_feature_type` into a second anatomy ontology.

## Alternative geometry paths

Atomic constraints cannot safely represent alternatives by emitting several independent `requires` claims.

For example:

```text
captive handle OR captive through-opening
```

must not become:

```text
requires handle
requires through-opening
```

because that incorrectly requires both.

Eligibility composition should therefore support bounded alternative paths:

```text
shared requirements: AND
paths:
  - path A: AND
  - path B: AND
prohibitions: AND NOT
```

The source claims remain atomic; the rule/eligibility layer composes their logical relationship.

## Manufacturer position is not technical compatibility

Brand should not be a compatibility predicate by default.

A manufacturer may specify its own product combination because that is the combination it has designed, tested, documented, or chosen to support. TetherLens should preserve that statement without silently inferring that every alternative brand is physically incompatible.

A candidate may therefore legitimately have:

```text
technical_status = compatible
manufacturer_status = contrary_to_manufacturer_instruction
policy_status = permitted
```

or:

```text
technical_status = compatible
manufacturer_status = explicitly_endorsed
policy_status = permitted
```

A site policy may separately disallow the first configuration.

The catalogue should record only what the source establishes. It should not record speculative motives such as vendor lock-in.

### Endorsement versus prohibition

The following statements are materially different:

```text
Use attachment X.
```

This may establish endorsement.

```text
Use only attachment X.
```

This establishes a manufacturer instruction whose alternatives conflict with that instruction, but it does not by itself prove that attachment Y is physically incompatible.

```text
Do not use attachment Y because it can detach from this housing.
```

This establishes a technical prohibition whose scope may justify a hard constraint.

The evidence model should preserve the source wording and scope so the recommendation layer can distinguish these cases.

## NLG 101691 Angle Grinder Bracket

The Angle Grinder Bracket remains a useful specialist case, but its manufacturer-declared angle-grinder scope should not be treated as proof that every non-angle-grinder tool is physically incompatible merely because the product name/application is category-specific.

Current extracted semantics are:

```text
attachment_method_code = mechanical_capture
applicable_tool_category_code = angle_grinder
required_tool_feature_type = handle
```

The next implementation pass should decide which part of the category statement is:

- a technical eligibility requirement that cannot be reduced further;
- manufacturer-supported scope; or
- descriptive/application wording.

Until that is established, the source-backed category statement should be preserved without allowing geometry alone to erase it or allowing the category alone to manufacture a physical incompatibility claim.

## NLG 101481 Mini Adhesive D Ring

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

## Representative geometry / relationship cases

The following cases now anchor the next implementation pass:

### NLG 101363 360 D Ring Loop

Manufacturer guidance supports a genuine alternative geometry expression:

```text
captive handle
OR
captive through-opening
```

This is the canonical test case for bounded OR-path semantics.

### Hilti SF 4-22 + retaining strap 2293133

Hilti provides a manufacturer-specified tool/attachment/tether configuration and identifies accessory-installation openings used by the retaining strap.

This case should preserve the Hilti instruction as manufacturer position while allowing technical evaluation of other candidates from geometry, dimensions, capacity, installation, and interface facts.

The physical feature should normalize toward:

```text
feature_kind = through_opening
feature_role = accessory_mount
```

rather than becoming a manufacturer-specific interface type.

### Ergodyne web ToolAttachment + companion tape/wrap

This case shows that a tool-side attachment solution can require multiple physical products.

Candidate configuration semantics should therefore support a runtime ToolAttachment assembly or `tool_attachment_components[]` rather than assuming exactly one ToolAttachment product.

Substituting another companion product requires sufficient evidence for the resulting installed assembly; apparent fit alone is insufficient.

## Wider tool-selection design evidence

Industry guidance reviewed during this workstream treats tool geometry as one input alongside tool type, weight, attachment-point form, connection method, length/reach, and task/environment constraints.

Useful design references include:

- Leading Edge Safety — *What Is Tool Tethering? A Complete Safety Guide for Construction*
- FallTech — *Dropped Object Prevention*
- Ergodyne — *How to Create Tool Attachment Points for Tool Tethering*
- Ergodyne — *Four Factors for Determining Tool Tethers*
- Enfield Safety — *Tool Tethering Matching*
- CMT — *NLG Tool Tethering / Dropped Object Prevention Guide*

The next implementation should remain narrower than a full rule-engine redesign. Expand the reusable vocabulary only when representative products require it.
