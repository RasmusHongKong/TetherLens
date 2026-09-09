# Evidence-backed target interface form

## Purpose

This note defines production target-interface form enrichment used to bind already-established structural interfaces to narrower manufacturer-stated physical form without inventing topology.

The first slice was the singular NLG Adjustable Wristband anchor D-ring. The second slice is the six already-distinct internal D-ring interfaces on the NLG Tall Tool Bag.

The governing rule is:

> **A physical-interface form may be normalized only when accepted manufacturer wording can be bound unambiguously to the concrete tether interface or already-resolved repeated interface set being represented. A generic ring, a product name, or an unresolved repeated interface set must not be upgraded to a D-ring.**

## Shared representation

`ConnectionInterface` already retains arbitrary accepted `interface.attribute.*` claims in `attributes`.

The normalized runtime pattern is therefore:

```text
ConnectionInterface(
    role = <preserved structural role>,
    interface_type = ring,
    attributes = {"ring_form": "d_ring"},
)
```

No new domain field or D-ring-specific runtime class is required.

`interface.type = ring` remains the broader topology fact. `ring_form = d_ring` is a narrower accepted physical-form fact and must remain absent when the source establishes only a generic ring or when the form evidence cannot be bound to a concrete interface identity.

## Singular anchor slice

Current NLG first-party wording for the Adjustable Wristband states that the product creates an anchor point on the wrist and utilises a durable plastic D ring for quick and easy lanyard attachment.

That wording establishes one singular physical interface with the narrow primitives:

```text
subject_type = physical_interface
subject_ref = lanyard_anchor_d_ring
interface.role = anchor_attachment_tether_side
interface.type = ring
interface.attribute.ring_form = d_ring
```

The extraction is evidence-led rather than SKU-led. Product identity scopes the owning catalogue item, but the SKU or product name is not used to manufacture the D-ring form.

## Repeated container slice

The Tall Tool Bag evidence establishes two complementary facts:

```text
8 load-rated anchor points — 2 external, 6 internal
6 integrated D Rings for tool lanyard attachment
```

The existing container-topology resolver already materializes the count/location fact as eight concrete subjects and can bind the unlocated six-count D-ring observation to exactly one resolved set: the six internal anchors.

The form layer therefore enriches those existing subjects only:

```text
internal_anchor_1 ... internal_anchor_6
interface.role = container_connection
interface.location_description = internal
interface.type = ring
interface.attribute.ring_form = d_ring
```

The two external anchors remain separate `container_connection` interfaces with unknown form. The four external tool holders remain outside `ConnectionInterface`.

This is not plural collapse. Interface count and identity already exist before the form attribute is added. The form enrichment reuses each concrete subject and the D-ring evidence already bound to its `interface.type = ring` claim.

## Identity boundary

Repeated form may be normalized only after topology has preserved the individual interface subjects and the form evidence maps unambiguously to that exact set.

A repeated D-ring phrase does **not** by itself authorize new interface subjects.

For example:

- a `4 external / 4 internal` anchor split plus an unlocated `4 D-rings` phrase is ambiguous and remains form-unknown;
- generic `ring` wording is not a D-ring claim;
- unknown-form anchor points remain unknown even when imagery appears ring-like; and
- a product name containing `D Ring` cannot supply physical form to another subject.

The singular anchor extractor continues to fail closed on plural D-ring/lanyard wording because that path does not independently establish repeated interface identity.

## Polarity, function and clause binding

The D-ring form must remain attached to affirmative manufacturer evidence and an already-established tether function.

The singular anchor extractor fails closed for:

- product-name-only or bare D-ring references;
- generic `ring` wording;
- cross-block D-ring/lanyard co-occurrence;
- interrogative wording;
- direct negation or prohibition;
- permission/safety prohibitions such as `not permitted`, `not allowed` or `not safe`;
- trailing avoidance/prohibition wording; and
- D-rings whose stated purpose is another function such as brace mounting.

The container form path adds no separate topology or function inference. It only copies `d_ring` form from an already-produced `container_connection` subject whose own `interface.type = ring` evidence explicitly contains D-ring wording. Existing container guards therefore continue to reject mounting D-rings, tool holders and ambiguous repeated sets before form enrichment can occur.

## Structural role is preserved

D-ring form never rewrites structural role.

In particular:

- wrist/anchor-attachment D-rings remain `anchor_attachment_tether_side`;
- container D-rings remain `container_connection`;
- ToolAttachment-provided D-rings remain `tool_attachment_tether_side`; and
- a ring on any other function is not promoted into one of those roles merely because its form is a D-ring.

The Comfort Safety Belt remains an important control. Current first-party evidence distinguishes top D-rings used for braces from bottom D-rings used as tool anchors, but the current text does not establish a concrete per-set count/identity suitable for materializing those plural interfaces. The existing `bottom_d_ring` capacity fact is therefore not widened into fabricated connection-interface subjects in this slice.

## Relationship to Quick Clip compatibility

PR #44 defines the reusable NLG Quick Clip -> D-ring anchor declaration with the target requirements:

```text
target role = anchor_attachment_tether_side
target interface type = ring
target attribute ring_form = d_ring
```

This target role remains unchanged.

Container D-ring enrichment does **not** make `container_connection` targets satisfy that anchor declaration. No declaration matcher, compatibility evaluator or hard constraint is changed by this work.

Once an accepted interface of the correct declared structural role independently satisfies a supported declaration, the existing binder/evaluator may use its attributes in the normal way. Product identity continues to scope candidate context only; it is not the compatibility rule.

## Benchmark boundary

The Batch 2 post-blind golden expects:

- NLG 101365 to retain the singular `anchor_attachment_tether_side` ring with `ring_form = d_ring`;
- NLG 101492 to retain six distinct internal `container_connection` ring subjects and add `ring_form = d_ring` to each of those exact subjects;
- NLG 101492's two external anchors to remain form-unknown; and
- NLG 101520's generic internal anchor points to remain form-unknown.

The immutable Batch 2 blind artifact remains unchanged.

Focused executable coverage verifies:

- preservation of all six repeated container interface identities and structural role;
- D-ring attribute resolution through the existing generic `ConnectionInterface.attributes` path;
- generic-ring fail-closed behavior;
- ambiguous equal-count repeated-set fail-closed behavior;
- mounting D-ring rejection; and
- continued singular-anchor behavior through the existing tests.

## Non-goals

This slice does not:

- upgrade generic rings to D-rings;
- infer D-ring form from a product name or imagery;
- create repeated interface count or identity from a plural D-ring phrase;
- add D-ring geometry or dimensions;
- rewrite container interfaces as anchor-attachment interfaces;
- change Quick Clip connector semantics or declaration scope;
- change declaration matching, compatibility evaluation or hard constraints;
- create SKU-pair compatibility; or
- materialize the Comfort Safety Belt's plural D-ring sets without stronger identity/count evidence.
