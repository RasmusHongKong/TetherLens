# Connector Mechanism Semantics

## Purpose

This document records the first reusable connector-mechanism primitive introduced for endpoint forms whose manufacturer terminology does not establish that they belong to an existing validated connector family.

The initial case is NLG `Quick Clip`.

The governing principle is:

> **A connector label may identify its physical form, while a separate accepted primitive records how it opens. Neither fact may be widened into unsupported locking, geometry, or compatibility semantics.**

## Quick Clip boundary

NLG manufacturer material for representative Quick Clip products explicitly describes Quick Clips as supporting connection/disconnection through a built-in or ergonomic trigger.

The normalized primitive is therefore:

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

## What the primitive establishes

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

## Extraction boundary

The NLG adapter emits the primitive only when all of the following are true:

1. tether topology has already established a connector-spec reference of `quick_clip` for the product;
2. the same manufacturer artifact contains a locally bound Quick Clip assertion;
3. connection/disconnection wording is tied to the trigger mechanism in the same sentence-like clause; and
4. the trigger relationship is not explicitly negated.

A trigger on a nearby power tool, unrelated product feature, or another clause must not be attributed to the Quick Clip.

The adapter remains evidence-led rather than SKU-led. The product SKU is not used to manufacture the mechanism fact.

## Resolution

The existing connector resolver already retains `connector.attribute.*` claims in `ConnectorSpec.attributes`.

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

## Relationship to connection compatibility

The current validated gated-connector compatibility and geometry rules remain scoped to their existing connector family.

A Quick Clip with `opening_mechanism = trigger_operated` therefore remains `unresolved` against an otherwise plausible closed interface unless another acceptable compatibility basis applies.

This is deliberate. The existing bounded verification family contains gate- and lock-specific observations. Current first-party Quick Clip evidence establishes a trigger-operated mechanism but does not yet establish enough gate/locking semantics to reuse that family without inference.

Likewise, adding a hypothetical `gate_opening` dimension to a `clip` does not make the existing carabiner/snap-hook admission rule applicable merely because the dimension name is familiar.

## Why retain the primitive before it closes compatibility?

The primitive removes an important vocabulary ambiguity without weakening downstream evidence standards.

It gives future work an explicit fact on which to base one of several evidence-backed next steps:

- first-party evidence that establishes Quick Clip closure/locking semantics;
- a separately validated bounded Quick Clip field-verification family;
- accepted geometry sufficient for a Quick Clip-specific reusable rule; or
- a properly scoped manufacturer compatibility declaration for a reusable interface relationship.

Whichever path is justified should consume the retained mechanism fact rather than reinterpreting product names or raw marketing text.

## Deliberate non-goals

This slice does not introduce:

- SKU-pair compatibility logic;
- a generic `clip -> carabiner` alias;
- a generic trigger-clip compatibility class;
- a new field-verification procedure without validation;
- action-count inference from the number of triggers;
- locking inference from words such as `secure`;
- geometry inference from product images; or
- changes to hard viability, candidate ranking, contextual feasibility, or session fallback.

## Next evidence criterion

The next Quick Clip compatibility slice should proceed only when representative evidence establishes enough reusable mechanism/interface semantics to justify a bounded rule.

The highest-value evidence would be first-party operating instructions that explicitly establish closure/locking behavior, or a manufacturer statement whose scope establishes the relevant connector-to-interface relationship without relying on one SKU pair.
