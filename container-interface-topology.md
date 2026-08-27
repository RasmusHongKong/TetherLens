# Container Interface Topology

## Purpose

This document defines the first normalized container tether-interface slice for TetherLens.

It is intentionally narrow. The goal is to represent repeated container-provided tether interfaces without creating a separate container topology system, without treating every ring/loop/holder as an anchor, and without encoding SKU-specific rules.

The shared `physical_interface` / runtime `ConnectionInterface` model remains the canonical connection abstraction.

## Core distinction: function is not form

A container feature participates in tether connection reasoning only when accepted evidence establishes a tether-anchor function.

For the first slice:

```text
interface.role = container_connection
```

means that the container provides an interface intended to receive a tool tether/lanyard connection or otherwise secure a tethered item.

This role must not be inferred solely from physical form or load rating.

Examples that are **not automatically container connections** include:

- tool holders or staging holders;
- pockets and storage loops;
- bag-to-belt / bag-to-harness mounting D-rings;
- Quick Connect mounting hardware;
- lifting handles or lifting slings;
- rope-management loops;
- removable structural/top rings; and
- another ring, loop or attachment feature whose tether function has not been established.

A load-rated feature can therefore still be non-tethering. A D-ring can likewise be a tether anchor, mounting point or brace attachment depending on manufacturer-stated function.

## Small reusable vocabulary

The first container slice reuses the existing shared interface vocabulary rather than adding container-specific interface types.

| Concept | Representation |
|---|---|
| Tether-anchor function | `interface.role = container_connection` |
| Ring / D-ring form | `interface.type = ring` when established |
| Daisy-chain / closed webbing-loop form | `interface.type = loop` only when the individual loop interface is established |
| Form not established | no persisted `interface.type` claim; runtime resolves to `interface_type = unknown` |
| Internal / external topology | `interface.location_description = internal | external` when stated |
| Per-interface rating | interface-scoped `rated_capacity_kg` |
| Repetition | separate `physical_interface` subjects with stable ordinal refs |

`anchor` is a function and must not become an `interface.type` value.

`tool_holder` is not a tether-interface type. A holder remains outside `ConnectionInterface` unless separate evidence establishes that the holder itself is an intended load-bearing tether connection.

## Repeated interfaces

When manufacturer evidence states an explicit count, TetherLens materializes the repeated physical interfaces rather than storing only an aggregate count.

For example:

```text
4 internal anchor points
```

normalizes to:

```text
internal_anchor_1
internal_anchor_2
internal_anchor_3
internal_anchor_4
```

Each subject carries its own accepted interface claims.

A count can still be derived later from the set of accepted interfaces. It is not the canonical topology representation.

Where the manufacturer publishes a per-interface rating such as `5 kg each`, that rating may be bound to every repeated interface established by the same scope.

If accepted evidence conflicts on the repeated count for one location, the extractor fails closed for that location rather than choosing a count.

## Unknown form

Manufacturer evidence can establish that a physical anchor exists without establishing its load-bearing form in text.

That distinction is preserved:

```text
interface.role = container_connection
interface.location_description = internal
# no interface.type claim
```

The accepted-claim resolver materializes this as:

```text
ConnectionInterface(
    role = container_connection,
    interface_type = unknown,
    location_description = internal,
)
```

`unknown` here is a conservative runtime state. It is not an inferred persisted geometry claim.

An unknown-form anchor is useful topology, but it does not become compatible with a tether endpoint merely because both sides are plausible. Existing connection evaluation remains fail-closed unless a supported compatibility basis exists.

## Evidence-binding rules

Container extraction should remain clause-bound and evidence-led.

Positive examples include manufacturer wording such as:

- load-rated anchor points used to secure/attach tools;
- integrated anchor points for tool-lanyard attachment;
- counted load-rated anchor points explicitly split into internal/external locations; and
- counted D-rings locally tied to tool-lanyard/tether function.

Negative examples include:

- external D-rings used to mount the pouch to a belt, harness or rail;
- top D-rings used to attach braces;
- external tool holders, even where nearby marketing copy describes an overall tethering setup;
- load-rated lifting handles;
- rope-management loops; and
- removable top/structural rings.

Physical form may refine an already-established interface, but form alone must not create tether-anchor function.

## NLG evidence cases inspected

### 101520 — Ascent Pouch

Current NLG manufacturer evidence establishes:

- four internal load-rated anchor points;
- those internal points are used to attach tools / for multiple tool-lanyard attachment;
- a 5 kg per-site internal-anchor/daisy-chain rating; and
- a load-rated external daisy chain.

The first slice materializes the four internal anchors. Their physical form is not promoted from imagery into text-backed catalogue geometry.

The external daisy chain is retained as a known evidence limitation for repeated topology because the current public text does not publish the number of individual external loop/sites. TetherLens does not count them from imagery.

### 101492 — Tall Tool Bag

Current NLG manufacturer evidence establishes:

- eight load-rated anchor points in total;
- two external and six internal anchors;
- six integrated D-rings for tool-lanyard attachment;
- four external tool holders as a separate storage/staging feature; and
- a 5 kg per-site internal-anchor/daisy-chain rating.

The normalized topology is therefore:

- six internal `container_connection` interfaces of type `ring`; and
- two external `container_connection` interfaces whose form remains `unknown` unless stronger evidence establishes it.

The four external tool holders do not become `ConnectionInterface` objects.

### 101705 — Comfort Safety Belt control case

101705 is an `AnchorAttachment`, not a Container, but it demonstrates why form is insufficient.

NLG distinguishes bottom D-rings used as load-rated tool anchors from top D-rings used to attach braces. The container layer must not reclassify either simply because the feature is a D-ring.

### Nearby container controls

The Ascent Bucket and related Rope/Pro products combine genuine tool anchors with other strong or closed features such as:

- load-rated lifting handles/slings;
- rope-management loops;
- removable top rings; and
- external load-rated daisy chains.

These products are useful adversarial controls because they prove that neither `load-rated` nor `ring/loop` is sufficient to establish tether-anchor function.

## Connection-compatibility boundary

This workstream adds topology, not a new engagement shortcut.

In particular:

- `carabiner + unknown` does not become compatible;
- `carabiner + ring` still does not become compatible from type labels alone;
- the existing bounded gated-connector-to-closed-interface verification family remains subject to its connector-spec and observed-check requirements; and
- `loop` is not added to that validated closed-interface family merely because NLG daisy chains are represented as loops.

A future webbing-loop engagement rule should be justified independently from the topology model.

## SKU-independence requirement

No production extraction or compatibility branch may inspect NLG product codes such as `101520`, `101492` or `101705` to decide topology.

The target products are benchmark/evidence cases only. Production behavior must depend on reusable manufacturer wording, subject binding, counts, locations, physical form and stated function.
