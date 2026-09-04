# Cinch-loop mechanism and compatibility semantics

## Purpose

This note defines the first reusable compatibility path for a soft tether endpoint whose manufacturer evidence explicitly establishes **cinching** as its engagement mechanism.

The model deliberately separates endpoint form from engagement mechanism:

- `connection_point.interface_type = loop` preserves the physical endpoint form.
- `connector.attribute.engagement_method = cinch` records the independently established mechanism.
- A `loop` label by itself is not evidence that the loop can or should be cinched.

The initial evidence target is the NLG Bungee Tool Lanyard family represented by 101372. Current first-party product copy states that its climbing-cord loop can attach to an anchor point or directly to a captive hole/handle on a tool, and separately states that the climbing-cord loop allows secure cinching. NLG's Tool Tether Guide also demonstrates the generic cinch sequence on loop/choke products: capture the captive feature, pass the tether through the loop, pull tight, and check the installation before use.

## Ingestion rule

The NLG adapter emits the reusable cinch primitive only when one evidence clause binds the **loop itself** to cinching, such as `cinching loop`, `loop allows ... cinching`, or `loop is cinched`.

Nearby but unrelated words are insufficient. For example, a loop mentioned in one block and a cinching storage strap in another must not establish a cinch-loop connector specification.

When exactly one tether loop endpoint is established and no connector-spec reference already exists, the adapter gives that endpoint a reusable `cinch_loop` connector-spec reference and emits:

`connector.attribute.engagement_method = cinch`

The adapter deliberately does not broadcast one cinching statement across multiple loop endpoints whose individual mechanism identity has not been established.

## Compatibility family

`cinch_loop_to_closed_interface.v1` is a **bounded runtime-verification family**, not a universal interface-class compatibility rule.

Admission requires all of the following:

1. source role is a tether connection;
2. source interface type is `loop`;
3. the referenced connector specification explicitly has `engagement_method = cinch`;
4. endpoint-side semantics permit the requested side; and
5. the target is inside the evidence-backed v1 scope.

The v1 target scope is intentionally narrow:

- direct tool target: `captive_hole` or `closed_handle`;
- anchor-attachment/container target: `ring`.

A ToolAttachment-provided ring is **not** admitted by this family. Neither are other closed forms such as a `dedicated_eye` merely because they look topologically similar. Those cases remain `unresolved` until separate evidence justifies widening the family.

## Runtime observations

Catalogue evidence is not sufficient to prove the actual field engagement. An admitted candidate therefore starts as `requires_verification` with basis `runtime_verification`.

The v1 verifier derives its terminal result only from two structured observations:

- `target_fully_captured`
- `cinch_drawn_tight`

Any explicit `False` fails the verification. Both must be explicitly `True` to pass. Missing observations remain pending.

The verifier accepts no generic caller-supplied pass/fail assertion.

## Session boundary

A successful field verification is session-local evidence for the selected candidate. It does not create a persistent SKU-pair compatibility fact, does not modify catalogue evidence, and does not allow a later recommendation to skip the bounded check.

## Non-goals

This slice does not:

- make every `loop + ring` pair compatible;
- infer cinching from `loop` alone;
- infer dimensions, knot behavior, material behavior, or soft-connector geometry;
- widen Quick Clip, carabiner, or snap-hook semantics;
- treat a runtime pass as manufacturer evidence;
- establish compatibility with ToolAttachment-provided rings or unevidenced closed-interface classes.

## Evidence required to widen v1

A future change should widen target classes only when first-party evidence explicitly establishes the additional interface relationship or when a separately validated reusable physical rule makes the relationship defensible without product-pair logic.
