# TetherLens Connection Compatibility

## Purpose

This document defines how TetherLens should establish whether one tether-side connection can be made correctly when complete engineering geometry is not publicly available.

The governing requirement is:

> **Every required connection must have an acceptable compatibility basis.**

TetherLens should not require every connection to be proven from catalogue dimensions alone. Published or internally measured geometry remains valuable, but it is one evidence path among several.

This avoids turning the catalogue into an exhaustive measurement programme while preserving conservative physical-connection reasoning.

---

## Why this model is needed

Many tether, ToolAttachment, AnchorAttachment, container and connector manufacturers publish:

- connector/interface type;
- load rating;
- locking/action characteristics;
- intended use; and
- sometimes explicit pairings or installation instructions;

but do not publish the detailed dimensions needed to derive every connector-to-interface fit from first principles.

Treating unpublished geometry as a mandatory catalogue requirement would therefore make otherwise useful products permanently recommendation-incomplete unless TetherLens purchased and measured them.

That is not scalable and is not required for every defensible field recommendation.

TetherLens should instead distinguish:

1. **catalogue-established compatibility** — enough accepted evidence exists before the worker begins the task; and
2. **controlled runtime verification** — the connection is topologically plausible and may be used only after the worker verifies a bounded set of physical fit conditions on the actual equipment.

A runtime verification must never be silently promoted into a universal persistent catalogue fact.

---

## Connection result states

Initial connection-evaluation states should be:

```text
compatible
incompatible
requires_verification
unresolved
```

### `compatible`

Use when an accepted compatibility basis establishes the connection without requiring a physical check by the worker for this specific configuration.

### `incompatible`

Use when accepted evidence or a validated rule establishes that the connection must not be used.

Examples include:

- wrong endpoint-side semantics;
- explicit manufacturer prohibition;
- a dimensional rule proving insufficient clearance; or
- another validated rule proving invalid engagement.

### `requires_verification`

Use when:

- topology and role semantics are plausible;
- no accepted evidence proves incompatibility;
- catalogue evidence is insufficient to establish complete physical engagement; and
- the connection type is covered by a validated bounded field-verification procedure.

This is a usable but conditional state, not a synonym for missing data.

### `unresolved`

Use when TetherLens lacks enough evidence to classify the connection as compatible, incompatible, or safely field-verifiable.

Examples include:

- interface type or role is ambiguous;
- the applicable field-verification procedure has not been validated;
- critical geometry or operating semantics are unknown in a way that cannot safely be checked in the field; or
- accepted evidence is conflicting.

---

## Compatibility bases

A connection evaluation should record **why** it reached its status.

Initial compatibility-basis codes:

```text
manufacturer_declared
validated_geometry
validated_interface_class
runtime_verification
none
```

Additional basis codes should be added only when a real evidence path requires them.

### `manufacturer_declared`

Use when the manufacturer explicitly establishes the relevant connection or interface compatibility.

Examples:

- explicit compatible products/interfaces;
- prescribed kit or system relationship;
- a manufacturer instruction that clearly establishes the permitted connection.

This should remain issuer- and scope-aware. A statement from one manufacturer does not automatically represent endorsement by another manufacturer in a mixed-brand configuration.

### `validated_geometry`

Use when accepted physical facts satisfy a reusable geometry rule.

Geometry rules should remain deliberately narrow. TetherLens does not need a general CAD or arbitrary mechanical-geometry model.

A dimensional rule must establish the condition it actually proves. For example, a gate-opening comparison may prove that a ring section can pass through an open gate, but it must not automatically be treated as proof of every aspect of safe connector orientation, closure or loading unless the validated rule covers those conditions.

### `validated_interface_class`

Use when accepted primitive facts place both connection participants into a validated reusable compatibility class without relying on SKU-to-SKU logic.

The class must be defined by physical/interface properties or another reusable technical basis, not by an application label such as "works with product X".

### `runtime_verification`

Use when the catalogue can establish a plausible connection path but final physical fit must be checked on the actual components using a validated procedure.

A successful runtime verification applies to the observed configuration/session. It must not automatically create a persistent claim that all specimens of the two catalogue products are universally compatible.

### `none`

Use when no acceptable compatibility basis is available.

---

## Evaluation order

Connection evaluation should remain conservative and short-circuit on established incompatibility.

Recommended order:

```text
resolve endpoint + target topology
        ↓
role / tether-side incompatibility?
        → incompatible
        ↓
explicit applicable prohibition?
        → incompatible
        ↓
explicit accepted compatibility?
        → compatible / manufacturer_declared
        ↓
validated geometry rule applicable?
        → compatible | incompatible | unresolved
        ↓
validated interface-class rule applicable?
        → compatible | incompatible | unresolved
        ↓
validated bounded field-verification path available?
        → requires_verification
        ↓
unresolved
```

A type-name pairing such as `carabiner + ring` is not by itself a compatibility basis.

---

## Controlled field verification

Field verification should be a structured technical check, not a vague user confirmation such as "looks okay".

The exact checklist belongs to the validated rule for the relevant connection family. For a gated connector engaging a closed tether point, observable criteria may include whether:

- the connector can be installed on the intended interface normally;
- the gate closes completely;
- the locking mechanism fully engages where applicable;
- the interface does not press against, capture or obstruct the gate;
- the connector can settle into an intended loaded orientation;
- the interface does not force obvious cross-loading or unstable seating; and
- adjacent hardware does not interfere with the gate or locking mechanism.

This list is illustrative until a specific field-verification rule is validated and versioned.

Runtime verification does not replace other hard constraints. Rated capacity, ToolAttachment installation eligibility, manufacturer prohibitions, anchor suitability and policy still apply independently.

---

## Relationship to computer vision

Computer vision may later assist a field-verification workflow by:

- identifying the intended connector/interface;
- prompting the worker to show the connection from useful angles;
- detecting obvious open-gate, wrong-feature or interference conditions; and
- recording structured observations.

Computer vision should not be treated as a compatibility authority merely because it can see the connection. Each machine-observed criterion must be separately validated before it can replace worker confirmation.

---

## Geometry remains valuable but optional

TetherLens should continue to ingest published dimensions and retain internal measurements where they are economically useful.

Measurements are especially valuable when:

- the same connector specification is reused across many products;
- one measurement resolves a high-frequency recurring uncertainty;
- a geometry rule can conclusively reject unsafe fit; or
- the measurement meaningfully reduces the number of field-verification steps.

The catalogue should not require a bespoke internal measurement for every tether SKU merely to reach recommendation readiness.

---

## Persistence and provenance

Compatibility evidence should preserve its basis and provenance.

Catalogue-level conclusions may depend on:

- accepted manufacturer Claims;
- accepted physical dimensions;
- validated Rules; and
- explicit product/interface relationships.

Runtime field observations are session-level context unless they later enter a separate reviewed evidence-ingestion process.

A worker's successful check of Product A connected to Product B must not silently create a universal accepted Claim that Product A and Product B are compatible.

---

## Recommendation implications

A candidate configuration may remain recommendable when one or more connections are `requires_verification`, provided:

- all other hard constraints pass;
- the required field-verification procedure is validated and available;
- the recommendation clearly presents the verification as a condition before use; and
- failure of the field check causes that candidate connection/configuration to be rejected.

`unresolved` remains blocking where no acceptable verification path exists.

This gives TetherLens a useful middle ground between:

- unsafe type-name assumptions; and
- an economically unrealistic requirement to prove every connection from complete engineering dimensions.

---

## Design principle

> **Model the strongest defensible compatibility basis available; do not manufacture geometric certainty where the market does not publish it.**

Geometry, declared compatibility, reusable interface classes and controlled runtime verification are complementary evidence paths rather than competing architectures.
