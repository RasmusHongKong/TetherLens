# Compatibility evidence and inference

## Status

Architectural guidance for recommendation reasoning when complete physical geometry is not available from manufacturers.

This document records a permanent design constraint for TetherLens rather than a temporary catalogue-cleanup task: exact dimensions and complete interface geometry will often be unavailable. The recommendation model must therefore support bounded technical reasoning from the strongest reusable evidence that actually exists, without inventing physical facts or collapsing back to SKU-pair matching.

Where older exploratory examples imply that a manufacturer-named feature may be promoted to a more specific geometry than the source establishes, this document governs. In particular, current Hilti SF 4-22 evidence establishes manufacturer-defined accessory-installation openings and their role, but does not establish `through_opening`, `captive`, exact dimensions, or a ring/eye form.

## 1. Evidence layers

TetherLens should distinguish three epistemic layers.

### Observed facts

Facts stated directly by an accepted source or established by a validated measurement/observation.

Examples:

- a ToolAttachment is rated to 6.8 kg;
- a manufacturer instructs the retaining strap to be installed at the Tool's accessory-installation openings;
- a ToolAttachment provides an attachment point for a tether;
- a connector is described as a double-action carabiner.

Observed facts should preserve source, subject scope and wording closely enough to remain auditable.

### Deterministically derived facts

Facts that follow mechanically from accepted inputs through an explicit rule.

Examples:

- selected operational mass = accepted tool-body mass + accepted selected-battery mass;
- a measured gate opening is insufficient for a measured target section;
- a normalized installation rule matches one resolved feature instance.

A derivation must retain the rule identity and the accepted inputs that caused it.

### Bounded inference

A hypothesis or generalized rule supported by repeated catalogue relationships or other indirect evidence, but not directly established as a physical fact.

Example: if one attachment is documented across many tools that share the same battery family, the evidence may support a hypothesis that installation depends on that battery envelope rather than on each Tool SKU independently.

Such an inference may help TetherLens discover or rank candidate explanations, but it must not silently manufacture exact dimensions, captive state, structural form, or a hard compatibility result that the evidence does not justify.

## 2. Exact geometry is strong evidence, not a prerequisite

Dimensional reasoning remains valuable when data exists:

```text
gate_opening_mm >= target_section_diameter_mm
```

But TetherLens must also support reusable functional and topological rules such as:

```text
installation_mode = wrap
target_kind = external_section
requires_closed_capture = true
```

or:

```text
source_kind = gated_connector
target_kind = closed_attachment_point
engagement = pass_through_and_close
```

These remain logic-based compatibility rules. They generalize beyond product pairs without requiring CAD-grade data that manufacturers may never publish.

When the available evidence does not support even that level of reusable physical abstraction, a narrowly scoped evidence-bound relationship may still establish one known installation or connection path. That relationship is evidence about the documented path, not a substitute for a generic geometry rule.

## 3. Do not reverse-engineer precise physical facts from compatibility lists

Catalogue relationships can provide evidence about what works without proving why it works.

If manufacturer evidence repeatedly documents attachment X on Tools A, B, C and D, TetherLens may retain those positive relationships and later infer a shared dependency. It must not invent a battery width, opening diameter, captive state or other exact physical property merely because such a property would explain the pattern.

The preferred progression is:

```text
known-valid relationship
-> identify shared functional/topological facts
-> form bounded reusable hypothesis
-> validate against additional products or measurements
-> promote to a technical rule only when justified
```

The original relationship evidence remains useful even after a reusable explanation exists.

## 4. Positive manufacturer evidence is not an exclusion rule

A statement that Tool A is documented with attachment X establishes positive evidence for that route. Even wording such as `use only X` is primarily an issuer-scoped manufacturer instruction unless the source also establishes a technical causal reason that makes alternatives physically unsuitable.

Therefore:

- documented pairings may establish a manufacturer installation binding;
- omitted products normally remain `unknown`, not `incompatible`;
- another attachment may still qualify through reusable technical eligibility or its own accepted installation evidence;
- a site policy may independently require OEM-approved combinations;
- an explicit technical prohibition or failed physical constraint may still create a hard negative result.

This prevents manufacturer catalogue scope from becoming an accidental law of physics.

## 5. Evidence-bound installation is a fallback, not a generic rule

The current Hilti increment introduces a narrow `ToolAttachmentInstallationBinding` for cases where accepted evidence establishes that one ToolAttachment is installed at one resolved Tool feature, but does not expose enough geometry to compile a reusable eligibility rule.

Conceptually:

```text
ToolAttachmentInstallationBinding
  tool_ref
  source_product_ref
  installation_feature_id
  issuer_manufacturer
  scope
  source_urls
```

This object means only:

> accepted manufacturer evidence establishes this installation path.

It does not mean:

- every Tool with the same feature role accepts the attachment;
- only this attachment may be used on the Tool;
- the feature has geometry that was never published;
- the manufacturer pairing itself is a technical compatibility rule.

Reusable feature/dimension rules remain the preferred route whenever the evidence actually supports them.

## 6. Conservative Hilti SF 4-22 normalization

The current first-party evidence supports a manufacturer-defined installation location described as `installation openings for accessories`. It supports the retaining strap being secured there and a tether carabiner being connected to the retaining strap.

The Tool feature is therefore normalized conservatively as:

```text
feature_id = accessory_installation_openings
feature_kind = other
feature_role = accessory_mount
captive_state = unknown
location_description = "installation openings for accessories"
```

The plural manufacturer wording is treated as one logical installation feature for this known installation path. TetherLens does not infer that there are two independently usable holes or that installation consumes only one of them.

The retaining strap provides only the functional interface established by the product evidence:

```text
interface_id = tether_attachment_point
role = tool_attachment_tether_side
interface_type = attachment_point
```

No ring, eye, captive-hole form or dimensions are inferred.

## 7. Configuration-level installation targets

Some future ToolAttachments will install on the selected operational configuration rather than the bare Tool—for example, a pouch or capture system around an installed battery.

The architecture should therefore remain capable of representing features owned by:

- the Tool itself;
- a selected configuration component such as a Battery; or
- the assembled operational configuration.

PR #68 already preserves exact configuration product identity. A later increment can extend feature ownership when a real catalogue case requires it; this PR does not invent that abstraction prematurely.

## 8. Future rule provenance

A later architectural increment should attach provenance/epistemic basis to reusable rules themselves. A possible starting vocabulary is:

```text
DIRECT_MEASUREMENT
EXPLICIT_TECHNICAL_DESCRIPTION
MANUFACTURER_INSTALLATION_EVIDENCE
CROSS_PRODUCT_PATTERN
FIELD_VALIDATED
```

The exact enum/schema should be chosen only after inspecting how it composes with existing claim provenance, connection-rule results and recommendation explanations.

The key requirement is that TetherLens must be able to distinguish, for example:

- compatibility established by measured geometry;
- compatibility established by a manufacturer-documented installation;
- compatibility suggested by a cross-product pattern but still requiring validation.

These should never be presented as equivalent evidence.

## 9. Scope of the current increment

The Hilti recommendation-readiness work intentionally implements only the smallest missing primitive: positive evidence-bound ToolAttachment installation when geometry is insufficient to compile a reusable technical rule.

It does not implement:

- cross-product inference;
- confidence scoring for inferred rules;
- configuration-component feature ownership;
- automatic promotion of repeated pairings to technical rules; or
- exclusion of mixed-manufacturer alternatives.

Those belong to a follow-up evidence/inference workstream. The immediate goal is to let one selected, evidence-backed Hilti operational profile enter the ordinary recommendation pipeline without SKU-pair compatibility logic or unsupported geometric inference.

## 10. Provenance must be scoped to the narrowest supported entity

PR #69 review reinforced several reusable provenance invariants.

### Product-scoped connection evidence belongs to the exact interface owner

A declaration that product A connects to product B must not become applicable to every interface in an assembly merely because B appears somewhere among the selected components.

For product-scoped manufacturer evidence, the runtime matcher must know which selected component product owns the specific target interface being evaluated and compare the declaration against that owner. Interface geometry itself remains manufacturer/product neutral.

Single-product assemblies may infer ownership unambiguously. Multi-product assemblies must carry complete interface-to-product ownership explicitly or fail closed.

### Model-specific executable evidence must be model-local in the source

A Tool model appearing somewhere in a combined operating-instruction document is not sufficient to bind every installation section in that document to the Tool.

Executable installation evidence must come from a section locally associated with the requested model. Where the same model has several scoped sections, incomplete contents/intro entries must not hide later complete evidence, and distinct complete routes may coexist.

### Evidence-record identity should follow the documented relationship

If two manuals document different attachment/tether pairings for the same Tool, they are independent evidence records and must not be forced into one conflicting subject merely because they share an adapter-defined label.

Conversely, two sources documenting the same semantic relationship should normally support one logical binding/declaration rather than manufacture duplicate runtime relationships.

For the current Hilti path, semantic identities therefore include the documented products, for example:

```text
retaining_strap_accessory_openings:<strap_identifier>
tool_tether_to_retaining_strap:<tether_identifier>:<strap_identifier>
```

This is evidence identity, not SKU-pair technical compatibility logic.

### A primary evidence tuple is atomic

When equivalent candidate claims from several artifacts are deduplicated, `source_url`, raw source wording, evidence method and extractor provenance must stay aligned.

The first accepted candidate claim may remain the primary evidence tuple while later equivalent source URLs are retained as supporting provenance. TetherLens must not select a different primary URL independently of the raw wording and thereby attribute text from source B to source A.

These rules generalize beyond Hilti: evidence may aggregate across sources, but subject scope and source attribution must never become broader than the evidence actually supports.
