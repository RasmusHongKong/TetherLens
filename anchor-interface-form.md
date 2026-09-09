# Evidence-backed target interface form

## Purpose

This note defines production target-interface form enrichment used to bind an already-established structural interface to narrower manufacturer-stated physical form without inventing topology or compatibility.

The first slice was the singular NLG Adjustable Wristband anchor D-ring. The next justified slice is the concrete D-ring interface already provided by an NLG ToolAttachment and exercised by the ToolAttachment-mediated recommendation path.

The governing rule is:

> **A physical-interface form may be normalized only when accepted manufacturer wording directly and unambiguously binds that form to the concrete tether interface being represented. A generic ring, a product name, imagery, or an unresolved plural set must not be upgraded to a D-ring.**

## Shared representation

`ConnectionInterface` already retains arbitrary accepted `interface.attribute.*` claims in `attributes`.

The normalized runtime pattern remains:

```text
ConnectionInterface(
    role = <preserved structural role>,
    interface_type = ring,
    attributes = {"ring_form": "d_ring"},
)
```

No new domain field or D-ring-specific runtime class is required.

`interface.type = ring` is the broader topology fact. `ring_form = d_ring` is a narrower accepted physical-form fact. The latter must remain absent when the source establishes only a generic ring or when D-ring wording cannot be bound to the exact interface subject.

## Singular anchor slice

Current NLG first-party wording for the Adjustable Wristband states that the product creates an anchor point on the wrist and utilises a durable plastic D ring for quick and easy lanyard attachment.

That wording establishes one singular physical interface:

```text
subject_type = physical_interface
subject_ref = lanyard_anchor_d_ring
interface.role = anchor_attachment_tether_side
interface.type = ring
interface.attribute.ring_form = d_ring
```

The extraction is evidence-led rather than SKU-led. Product identity scopes the owning catalogue item, but the SKU or product name is not used to manufacture the D-ring form.

## ToolAttachment-provided interface slice

The existing NLG ToolAttachment interface extractor already has a stricter prerequisite than a generic ring detector. It creates the concrete `tether_side_ring` subject only when affirmative manufacturer evidence itself binds a **D-ring** to the tether point or tool-lanyard connection supplied by the attachment.

For example, the current NLG Mini Adhesive D Ring evidence identifies the D-ring and states that it creates a tether point for attaching a tool lanyard. The existing extraction path therefore already establishes:

```text
subject_type = physical_interface
subject_ref = tether_side_ring
interface.role = tool_attachment_tether_side
interface.type = ring
```

The target-form layer preserves the narrower form on that exact same subject:

```text
interface.attribute.ring_form = d_ring
```

This is an enrichment of an existing concrete interface, not a second interface extraction. Subject identity, structural role, raw evidence and source provenance are retained.

The form layer deliberately runs after the established ToolAttachment interface grammar. It does not independently search a product page for a D-ring phrase and cannot create `tether_side_ring` when the underlying interface extractor has failed closed.

## Why this path is justified now

PR #49 added a semantic end-to-end recommendation scenario in which a ToolAttachment-provided tether interface survives accepted evidence, selected installation-feature binding, normalized product/install constraints, candidate generation, hard evaluation and selection.

That makes `tool_attachment_tether_side` a recurring downstream recommendation seam rather than merely catalogue metadata. Preserving manufacturer-stated D-ring form on the already-resolved interface is therefore useful evidence fidelity without adding a new decision rule.

The recommendation golden itself does not need a new expected compatibility outcome for this enrichment. Form becomes available to future evidence-backed declarations or geometry rules only if those rules are independently justified.

## Evidence and polarity boundary

The underlying ToolAttachment interface extractor remains authoritative for whether a concrete tether-side interface exists. Its existing fail-closed controls include:

- product-name-only or bare `D Ring` references;
- generic `ring` wording;
- cross-block D-ring/tether-point co-occurrence;
- direct negation or prohibition;
- permission/safety prohibitions;
- subject switches in which another loop or component owns the lanyard relation; and
- unrelated D-rings that are not the supplied tether interface.

The target-form layer adds no broader grammar. It simply requires that an already-produced `tool_attachment_tether_side` `interface.type = ring` claim retain explicit D-ring wording in its own raw evidence before copying `ring_form = d_ring` to that subject.

A product name such as `Mini Adhesive D Ring` is therefore still insufficient by itself. A generic ring is still a generic ring.

## Structural role is preserved

D-ring form never rewrites structural role.

In particular:

- the Adjustable Wristband D-ring remains `anchor_attachment_tether_side`;
- a ToolAttachment-provided D-ring remains `tool_attachment_tether_side`;
- container interfaces remain `container_connection`; and
- another D-ring function is not promoted into one of these roles merely because the physical form is a D-ring.

This distinction is important because form and function answer different questions. `d_ring` describes physical form; it does not mean `anchor`.

## Relationship to Quick Clip compatibility

PR #44 defines the reusable NLG Quick Clip -> D-ring **anchor** declaration with the target requirements:

```text
target role = anchor_attachment_tether_side
target interface type = ring
target attribute ring_form = d_ring
```

The role requirement remains unchanged.

A ToolAttachment target with:

```text
role = tool_attachment_tether_side
interface_type = ring
ring_form = d_ring
```

therefore does **not** satisfy the PR #44 declaration. This slice does not modify declaration matching, the connection evaluator, compatibility precedence, candidate hard constraints, or runtime-verification families.

Focused regression coverage confirms that an ordinary carabiner endpoint engaging the enriched ToolAttachment D-ring remains `UNRESOLVED` when no acceptable compatibility basis is established. Form evidence alone is not compatibility evidence.

## Container and plural-interface boundary

This slice does not extend D-ring form to repeated container or belt interfaces.

NLG 101492 remains an important future candidate because the existing topology layer already preserves six distinct internal `container_connection` ring subjects. Current evidence also uses D-ring wording for those internal tethering points. However, the narrower form does not currently close a recurring recommendation, compatibility or hard-evaluation gap, so this PR deliberately leaves those container interfaces unchanged.

NLG 101705 remains a stronger fail-closed control. Current first-party evidence distinguishes top D-rings used for brace mounting from bottom D-rings used as tool anchors, but does not establish a concrete per-set count/identity suitable for materializing the plural interface sets. The existing `bottom_d_ring` capacity fact is not widened into fabricated connection-interface subjects.

NLG 101520 generic internal anchor points also remain form-unknown unless stronger first-party form evidence becomes available.

Repeated form should be added only when both conditions are true:

1. concrete interface count/identity and structural role are already evidence-backed; and
2. preserving the narrower form closes a recurring recommendation/evaluation uncertainty rather than merely expanding taxonomy.

## Benchmark boundary

The Batch 2 post-blind golden now expects:

- NLG 101365 to retain its singular `anchor_attachment_tether_side` ring with `ring_form = d_ring`;
- NLG 101481 to retain its concrete `tool_attachment_tether_side` `tether_side_ring` and add `ring_form = d_ring` on that exact subject;
- NLG 101492 to remain unchanged as repeated `container_connection` ring topology without D-ring form enrichment in this slice; and
- NLG 101520 generic internal anchors to remain form-unknown.

The immutable Batch 2 blind artifact remains unchanged.

Focused executable coverage verifies:

- preservation of ToolAttachment interface identity and `tool_attachment_tether_side` role;
- D-ring attribute resolution through the existing generic `ConnectionInterface.attributes` path;
- product-name/generic-ring fail-closed behavior; and
- no compatibility widening from the newly preserved form.

## Non-goals

This slice does not:

- upgrade generic rings to D-rings;
- infer D-ring form from a product name or imagery;
- create a ToolAttachment interface from form evidence alone;
- materialize repeated interface count or identity;
- enrich container D-rings merely because evidence exists;
- add D-ring geometry or dimensions;
- rewrite ToolAttachment or container interfaces as anchor-attachment interfaces;
- change Quick Clip connector semantics or declaration scope;
- change declaration matching, compatibility evaluation, runtime verification or hard constraints;
- create SKU-pair compatibility; or
- materialize the Comfort Safety Belt's plural D-ring sets without stronger identity/count evidence.
