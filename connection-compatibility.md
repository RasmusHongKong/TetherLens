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

Use when accepted technical evidence or a validated rule establishes that the physical connection must not be used.

Examples include:

- established endpoint-side or role semantics that make the proposed engagement technically invalid;
- a manufacturer prohibition whose wording and causal scope establish a genuine technical failure mode;
- a dimensional rule proving insufficient clearance where no contradictory authoritative compatibility evidence exists; or
- another validated rule proving invalid engagement.

A manufacturer support, warranty, ecosystem or prescribed-product restriction is not automatically a technical `incompatible` result. Manufacturer assessments are handled separately below.

### `requires_verification`

Use when:

- topology and role semantics are plausible;
- no conclusive technical incompatibility or unresolved hard contradiction exists;
- catalogue evidence is insufficient to establish complete physical engagement; and
- the connection type is covered by a validated bounded field-verification procedure.

This is a usable but conditional state, not a synonym for missing data.

### `unresolved`

Use when TetherLens lacks enough consistent evidence to classify the connection as compatible, incompatible, or safely field-verifiable.

Examples include:

- interface type or role is ambiguous;
- the applicable field-verification procedure has not been validated;
- critical geometry or operating semantics are unknown in a way that cannot safely be checked in the field;
- accepted authoritative manufacturer evidence is conflicting and cannot yet be reconciled; or
- an explicit manufacturer compatibility declaration conflicts with accepted primitive physical facts that, through a validated rule, establish a direct physical impossibility for the same correctly bound configuration.

A less direct disagreement between an explicit manufacturer compatibility declaration and a generic TetherLens derived rule is handled separately under **Manufacturer precedence and contradiction review** below; it does not automatically make the operative connection state `unresolved`.

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

Use when the manufacturer explicitly establishes the relevant connection or interface compatibility for the intended use.

Examples:

- an explicit statement that the relevant products/interfaces are compatible;
- a prescribed kit or system relationship that establishes the intended connection; or
- a manufacturer instruction that clearly establishes that the connection may be made.

This should remain issuer- and scope-aware. A statement from one manufacturer does not automatically represent endorsement by another manufacturer in a mixed-brand configuration.

A statement such as `use only product X` may establish a manufacturer assessment or instruction about alternatives without proving that product Y is physically incompatible. Do not convert such wording into a technical result unless the source also establishes a genuine technical reason or failure mode with sufficient scope.

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

## Manufacturer assessment is separate from technical compatibility

Manufacturer position and physical technical compatibility are separate reasoning axes.

A manufacturer may endorse, require, restrict or prohibit a product relationship because that is the system it has designed, tested, documented, warranted or chosen to support. TetherLens should preserve that issuer-scoped statement without automatically translating it into a physical compatibility result.

Conceptually, connection reasoning may therefore carry both:

```text
technical_status = compatible | incompatible | requires_verification | unresolved

manufacturer_assessments:
  - issuer = <manufacturer>
    scope = <connection/configuration scope>
    position = explicitly_required | explicitly_endorsed | explicitly_compatible |
               contrary_to_manufacturer_instruction | explicitly_prohibited
```

Examples:

```text
Use connector X.
```

This may establish endorsement.

```text
Use only connector X.
```

This establishes an instruction whose alternatives may be contrary to that manufacturer's supported scope, but does not by itself establish that connector Y is physically incapable of safe engagement.

```text
Do not use connector Y because its gate can be forced open by this ring.
```

This may support both an issuer-scoped manufacturer prohibition and a technical `incompatible` result, provided the identity, scope and causal statement are sufficiently clear.

Policy may separately require manufacturer approval or prohibit configurations that are contrary to manufacturer instruction. That policy decision must not be smuggled into `technical_status`.

---

## Manufacturer precedence and contradiction review

An explicit, correctly scoped manufacturer compatibility declaration is more authoritative for that declared product/interface relationship than generic or incomplete TetherLens compatibility reasoning. TetherLens should nevertheless preserve and review contradictory derived results rather than suppressing them.

Three contradiction classes are useful:

```text
derived_rule_disagreement
hard_physical_contradiction
authoritative_source_conflict
```

### `derived_rule_disagreement`

Use when an explicit manufacturer compatibility declaration conflicts with a reusable TetherLens rule, but the derived rule does not establish a direct physical impossibility from accepted primitive facts bound to the same exact configuration.

Examples may include:

- an interface-class rule whose abstraction is broader than the manufacturer's tested pairing;
- a geometry rule that proves one partial condition but not the complete engagement mechanism; or
- another reusable rule whose assumptions may not capture a manufacturer-specific design detail.

In this case TetherLens should:

1. retain `compatible` as the operative connection status with basis `manufacturer_declared`;
2. preserve the contradictory derived result and its inputs;
3. raise an internal review signal for possible data-binding, rule-scope, dimensional, revision or manufacturer-guidance issues; and
4. avoid silently rewriting either source of evidence.

Conceptually:

```text
operative_status = compatible
operative_basis = manufacturer_declared
contradiction_type = derived_rule_disagreement
review_status = needs_review
contradicting_rule = <rule id/version>
contradicting_result = incompatible
```

### `hard_physical_contradiction`

Use only when accepted primitive physical facts, correctly bound to the same revision/configuration, and a validated rule establish a direct physical impossibility or necessarily invalid engagement while an accepted manufacturer declaration says the connection is compatible.

For example:

```text
accepted maximum gate opening = 8 mm
accepted closed interface section that must pass through the gate = 15 mm
validated admission rule proves the section cannot pass through the gate
manufacturer declaration says the exact connection is compatible
```

Those statements cannot all be simultaneously correct for the same correctly bound configuration. TetherLens should not decide that its own measurement/rule is necessarily more trustworthy than the manufacturer, but it also should not present the configuration as established compatible while its accepted catalogue facts prove the connection impossible.

The correct outcome is therefore:

```text
technical_status = unresolved
manufacturer_assessment = explicitly_compatible
contradiction_type = hard_physical_contradiction
review_status = needs_review
```

The connection remains blocked until identity, revision, scope, measurements, rule assumptions or manufacturer guidance are reconciled.

A `hard_physical_contradiction` must be narrow. Conservative margins, generic class assumptions, incomplete geometry, or a rule that proves only one partial fit condition are not sufficient to invoke it.

### `authoritative_source_conflict`

Use when accepted authoritative manufacturer evidence conflicts at the same applicable scope, for example:

- one accepted manufacturer document explicitly permits the connection while another accepted applicable document explicitly prohibits it;
- two applicable revisions provide incompatible instructions and recency/supersession has not been resolved; or
- the identity/scope binding of the manufacturer declaration is itself disputed.

These cases should remain `unresolved` until the authoritative conflict is reconciled.

---

## Evaluation order

Connection evaluation should remain conservative, keep manufacturer assessment separate from technical status, preserve authoritative manufacturer evidence, and continue past inconclusive generic bases.

Recommended order:

```text
resolve endpoint + target topology
        ↓
collect applicable manufacturer assessments / compatibility declarations
        ↓
conflicting authoritative manufacturer evidence?
        → unresolved + authoritative_source_conflict
        ↓
applicable manufacturer statement establishes a genuine technical prohibition
with sufficient causal scope?
        → incompatible
        ↓
nontechnical manufacturer restriction / supported-system instruction?
        → preserve ManufacturerAssessment; continue technical evaluation
        ↓
evaluate established topology / role rules
        → retain any conclusive technical result
        ↓
validated geometry rule applicable?
        → conclusive result? retain it
        → otherwise continue
        ↓
validated interface-class rule applicable?
        → conclusive result? retain it
        → otherwise continue
        ↓
explicit accepted manufacturer compatibility exists?
        ↓
    conclusive technical result establishes direct physical impossibility
    from correctly bound accepted primitive facts?
        → unresolved + hard_physical_contradiction
        ↓ otherwise
    contradictory generic derived result exists?
        → compatible / manufacturer_declared
        → attach derived_rule_disagreement review signal
        ↓ otherwise
    → compatible / manufacturer_declared
        ↓
no manufacturer compatibility declaration controls the result:
        ↓
conflicting conclusive generic technical results?
        → unresolved
        ↓
generic conclusive incompatible result exists?
        → incompatible
        ↓
generic conclusive compatible result exists?
        → compatible
        ↓
validated bounded field-verification path available?
        → requires_verification
        ↓
unresolved
```

An individual generic compatibility basis may be applicable yet unable to conclude because its required evidence is missing, incomplete or insufficient. That intermediate lack of conclusion must **not** terminate evaluation. For example, a geometry rule whose required measurements are unavailable should fall through to any applicable interface-class or runtime-verification basis.

The evaluator must not manufacture `incompatible` from manufacturer ecosystem wording alone. Only a technical prohibition with sufficient causal scope, or another conclusive technical rule, should produce technical incompatibility.

`unresolved` is the result when the evidence set itself is irreconcilably inconsistent for current use, or after all usable bases and validated field-verification paths have been exhausted without a defensible outcome.

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

Runtime verification does not replace other hard constraints. Rated capacity, ToolAttachment installation eligibility, genuine technical prohibitions, anchor suitability, manufacturer assessments and policy remain separate checks.

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

Manufacturer assessments should retain issuer, scope and source rather than being collapsed into technical status.

Contradictory generic derived results should remain traceable even when a manufacturer declaration controls the operative connection status. Hard physical contradictions should retain the exact accepted primitive facts and rule version that caused the connection to be blocked.

Runtime field observations are session-level context unless they later enter a separate reviewed evidence-ingestion process.

A worker's successful check of Product A connected to Product B must not silently create a universal accepted Claim that Product A and Product B are compatible.

---

## Recommendation implications

A candidate configuration may remain recommendable when one or more connections are `requires_verification`, provided:

- all other hard constraints pass;
- the required field-verification procedure is validated and available;
- the recommendation clearly presents the verification as a condition before use; and
- failure of the field check causes that candidate connection/configuration to be rejected.

`unresolved` remains blocking where no acceptable verification path exists or where a hard physical/source contradiction must first be reconciled.

A manufacturer-declared compatible connection may remain recommendable despite an ordinary contradictory generic derived rule, but the contradiction should create an internal review signal and remain explainable in provenance. It must not remain recommendable when the conflict qualifies as a `hard_physical_contradiction`.

A nontechnical manufacturer restriction may still affect explanation or policy without changing the connection's technical status.

This gives TetherLens a useful middle ground between:

- unsafe type-name assumptions; and
- an economically unrealistic requirement to prove every connection from complete engineering dimensions.

---

## Design principle

> **Use explicit manufacturer compatibility over weaker generic reasoning, but block irreconcilable hard physical contradictions; keep manufacturer position separate from technical compatibility.**

Geometry, declared compatibility, reusable interface classes, manufacturer assessments, controlled runtime verification and policy are complementary reasoning axes rather than competing architectures.
