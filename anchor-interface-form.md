# Evidence-backed anchor interface form

## Purpose

This note defines the first production target-interface form enrichment used to bind an already-established manufacturer connector/interface declaration to a concrete ingested anchor target.

The initial case is the NLG Adjustable Wristband anchor D-ring.

The governing rule is:

> **A physical-interface form may be normalized only when accepted manufacturer wording directly binds that form to the concrete tether interface being represented. A generic ring, a product name, or an unresolved repeated interface set must not be upgraded to a D-ring.**

## Evidence boundary

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

## Why the form is an attribute

`ConnectionInterface` already retains arbitrary accepted `interface.attribute.*` claims in `attributes`.

The normalized runtime target is therefore:

```text
ConnectionInterface(
    role = anchor_attachment_tether_side,
    interface_type = ring,
    attributes = {"ring_form": "d_ring"},
)
```

No new domain field or D-ring-specific runtime class is required.

`interface.type = ring` remains the broader topology fact. `ring_form = d_ring` is a narrower accepted physical-form fact and must remain absent when the source establishes only a generic ring.

## Singular-interface boundary

V1 materializes only a singular D-ring target that is directly tied to lanyard attachment.

Explicit plural D-ring/lanyard wording is not collapsed into one anonymous interface. A repeated target set needs evidence that preserves its physical count and identity before its members can be materialized safely.

This boundary is important for products such as belts or harness systems where different D-rings may serve different functions or ratings.

## Polarity and clause binding

The D-ring and lanyard relationship must occur inside one rendered evidence clause.

The extractor fails closed for:

- product-name-only or bare D-ring references;
- generic `ring` wording;
- cross-block D-ring/lanyard co-occurrence;
- interrogative wording;
- direct negation or prohibition;
- permission/safety prohibitions such as `not permitted`, `not allowed` or `not safe`;
- trailing avoidance/prohibition wording; and
- D-rings whose stated purpose is another function such as brace mounting.

Unrelated negative wording does not suppress a later affirmative relation in the same clause.

## Relationship to Quick Clip compatibility

PR #44 already defines the reusable NLG Quick Clip -> D-ring anchor declaration with the target requirements:

```text
target role = anchor_attachment_tether_side
target interface type = ring
target attribute ring_form = d_ring
```

This slice does not modify that declaration or the connection evaluator.

Once the accepted anchor-interface claims resolve to a matching `ConnectionInterface`, the existing declaration binder can create the candidate-scoped manufacturer assessment and the ordinary evaluator can return:

```text
status = compatible
basis = manufacturer_declared
```

Runtime product identities continue to scope the candidate context only. They are not the compatibility rule.

## Container and ToolAttachment boundary

A D-ring on another structural role is not widened into the PR #44 anchor scope.

In particular:

- container D-rings remain `container_connection` targets;
- ToolAttachment-provided D-rings remain `tool_attachment_tether_side` targets; and
- neither role is rewritten as `anchor_attachment_tether_side` merely because the physical form is a D-ring.

Likewise, preserving D-ring form on those roles in a future slice would not by itself make the current Quick Clip declaration applicable to them.

## Benchmark boundary

The Batch 2 post-blind golden now expects the NLG 101365 anchor interface role, ring topology and `ring_form = d_ring` attribute.

The immutable Batch 2 blind artifact remains unchanged.

Focused executable coverage verifies:

- positive singular D-ring extraction without SKU/name dependence;
- generic-ring and product-name fail-closed behavior;
- cross-block and plural-interface fail-closed behavior;
- local polarity and prohibition handling;
- preservation of container structural role; and
- end-to-end binding through the existing manufacturer-declared Quick Clip compatibility path.

## Non-goals

This slice does not:

- upgrade generic rings to D-rings;
- infer D-ring form from a product name;
- infer plural D-ring count or identity;
- add D-ring geometry or dimensions;
- change Quick Clip connector semantics;
- change declaration matching or connection-evaluation precedence;
- widen compatibility to container or ToolAttachment roles;
- create SKU-pair compatibility; or
- resolve unrelated capacity/evidence conflicts on the anchor product.
