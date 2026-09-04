# Connector Mechanism Semantics

## Purpose

This document records reusable connector-mechanism primitives for endpoint forms whose manufacturer terminology does not establish membership in an existing validated connector family.

The initial case is NLG `Quick Clip`.

The governing principle is:

> **A connector label may identify its physical form, while separate accepted primitives record how it operates and any manufacturer-declared interface relationships. None of those facts may be widened into unsupported locking, geometry or connector-family semantics.**

## Quick Clip mechanism boundary

NLG manufacturer material for representative Quick Clip products explicitly describes Quick Clips as supporting connection/disconnection through a built-in or ergonomic trigger.

The normalized mechanism primitive is therefore:

```text
subject_type = connector_spec
property_key = connector.attribute.opening_mechanism
value = trigger_operated
```

The tether endpoint remains:

```text
connection_point.interface_type = clip
```

`clip` is not rewritten as `carabiner`, `snap_hook`, or another existing connector type.

## What `trigger_operated` establishes

`opening_mechanism = trigger_operated` establishes only that accepted manufacturer evidence identifies a trigger-operated connection/disconnection mechanism on the referenced connector specification.

It does not establish:

- `connector.opening_action_count = 1`;
- `locking_mode = non_locking`, `manual_locking`, or `auto_locking`;
- a gate-opening dimension;
- automatic closure or automatic locking;
- compatibility with every ring, eye, handle, hole, or anchor;
- membership in the existing validated `carabiner` / `snap_hook` geometry class; or
- eligibility for `gated_connector_to_closed_interface.v1` merely because a trigger exists.

Those conclusions require their own accepted evidence or validated reusable rule.

## Mechanism extraction boundary

The NLG adapter emits the primitive only when all of the following are true:

1. tether topology has already established a connector-spec reference of `quick_clip` for the product;
2. the same manufacturer artifact contains a locally bound Quick Clip assertion;
3. connection/disconnection wording is tied to the trigger mechanism in the same sentence-like clause; and
4. the trigger relationship is not explicitly negated.

A trigger on a nearby power tool, unrelated product feature, or another clause must not be attributed to the Quick Clip.

The adapter remains evidence-led rather than SKU-led. The product SKU is not used to manufacture the mechanism fact.

## Resolution

The existing connector resolver retains `connector.attribute.*` claims in `ConnectorSpec.attributes`.

A resolved Quick Clip may therefore carry:

```text
ConnectorSpec(
    connector_spec_id = "quick_clip",
    opening_action_count = None,
    locking_mode = unknown,
    attributes = {
        "opening_mechanism": "trigger_operated"
    }
)
```

Missing action-count or locking evidence remains missing. The resolver does not infer those values from the trigger primitive.

## Manufacturer-declared Quick Clip -> D-ring compatibility

PR #44 adds a separate evidence path rather than widening the mechanism primitive.

Current NLG first-party material for the Retractable Quick Clip Attachment (101456) states that the product is designed to anchor a Heavy Duty Retractable Tool Lanyard to a D Ring style anchor point and that the Quick Clip can be attached to a D Ring.

That evidence is represented as a dedicated `connection_compatibility` claim subject and resolved into a reusable `ConnectorInterfaceCompatibilityDeclaration` with the narrow v1 scope:

```text
source connector spec = quick_clip
source interface type = clip
target role = anchor_attachment_tether_side
target interface type = ring
target attribute ring_form = d_ring
issuer = NLG
```

The declaration is then bound to concrete endpoint/target pairs only when those retained primitives match. The resulting candidate-scoped context supplies the existing `ConnectionManufacturerAssessment(position = explicitly_compatible)` path.

This is **not** a Quick Clip interface-class rule and **not** a new runtime-verification family. It is accepted manufacturer-declared compatibility with an explicit issuer, scope and evidence reference.

See `connector-declared-compatibility.md` for the full binding and provenance rules.

## Relationship to connection compatibility

The validated gated-connector compatibility and geometry rules remain scoped to their existing `carabiner` / `snap_hook` family.

Therefore:

- a trigger-operated Quick Clip against a generic ring remains `unresolved`;
- a Quick Clip against a D-ring on the wrong structural role remains `unresolved`;
- a Quick Clip against a D-ring anchor may become `compatible / manufacturer_declared` only when the accepted declaration is supplied and exactly matches the target primitives;
- adding a hypothetical `gate_opening` dimension to a `clip` still does not make the carabiner/snap-hook admission rule applicable; and
- the declaration does not establish any gate, closure or locking fact.

The ordinary connection evaluator remains responsible for endpoint-side semantics, manufacturer/source conflicts, hard physical contradictions and precedence.

## Endpoint-role boundary

Quick Clip compatibility and tether endpoint assignment remain separate problems.

Two endpoints may both be `clip` and reference the same `quick_clip` connector specification while their `connection_point.role` remains unresolved. That structural symmetry does not itself prove that the tether is non-directional.

Candidate generation therefore continues to exclude `TetherSide.UNKNOWN`. A manufacturer compatibility declaration must not promote an unknown endpoint role to `either`.

A future symmetric-tether slice should model explicit interchangeability/assignment evidence separately from endpoint physical form and connector compatibility.

## Why keep the mechanism primitive separate from the declaration?

The two facts answer different questions:

```text
opening_mechanism = trigger_operated
    -> how the connector is operated

manufacturer compatibility declaration
    -> which narrowly scoped target interface the manufacturer states it may engage
```

Keeping them separate prevents a declaration from manufacturing missing physical semantics and prevents a mechanism label from becoming generic compatibility.

This separation also permits future Quick Clip evidence to add other facts independently, for example closure behavior, geometry, or another declared target class, without rewriting existing claims.

## Deliberate non-goals

The current Quick Clip work does not introduce:

- SKU-pair compatibility logic;
- a generic `clip -> carabiner` alias;
- a generic trigger-clip compatibility class;
- a Quick Clip field-verification procedure without separate validation;
- action-count inference from the number of triggers;
- locking inference from words such as `secure`;
- geometry inference from product images;
- endpoint-role/interchangeability inference from symmetric connectors; or
- changes to hard viability, candidate ranking, contextual feasibility, or session fallback.

## Next evidence criterion

The next Quick Clip-specific compatibility expansion should proceed only when additional representative evidence establishes another bounded target relationship, reusable geometry, or enough closure/locking semantics to justify a separately validated rule.

Separately, symmetric tether endpoint assignment should proceed only when manufacturer evidence establishes interchangeability/non-directionality rather than merely showing physically similar endpoint hardware.
