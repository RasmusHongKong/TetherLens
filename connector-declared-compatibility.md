# Manufacturer-declared connector/interface compatibility

## Purpose

This note defines the first reusable path for turning an accepted manufacturer statement about a connector/interface relationship into candidate-scoped connection evidence without creating a SKU-pair compatibility table.

The initial evidence case is NLG Quick Clip -> D-ring anchor compatibility.

The governing rule is:

> **A manufacturer declaration may establish a reusable connector/interface relationship when its connector identity, target interface primitives, role scope, issuer and provenance are explicit. Runtime product identities scope the matched candidate; they are not the compatibility rule.**

## Evidence boundary

NLG first-party material for the Retractable Quick Clip Attachment (product code 101456) states that the attachment is designed to anchor a Heavy Duty Retractable Tool Lanyard to a D Ring style anchor point. The same datasheet separately states that the Quick Clip can be attached to a D Ring.

Primary evidence:

- `https://go.neverletgo.com/hubfs/Product/Datasheet/101456.pdf`

This evidence is stronger than the earlier Quick Clip trigger wording because it establishes an intended connector-to-interface relationship rather than merely describing how the connector is operated.

The first slice deliberately normalizes only the narrow relationship supported by that wording:

```text
source connector spec = quick_clip
source interface type = clip
target role = anchor_attachment_tether_side
target interface type = ring
target attribute ring_form = d_ring
issuer = NLG
manufacturer position = explicitly_compatible
```

The broader phrase `similar anchor point` is not normalized. It does not define a sufficiently bounded reusable interface class.

## Claim representation

A manufacturer declaration is represented by a dedicated `connection_compatibility` claim subject rather than by a tether-product pair.

The initial declaration subject is:

```text
quick_clip_to_d_ring_anchor
```

Its accepted claims carry:

```text
connection_compatibility.connector_spec_ref
connection_compatibility.source_interface_type
connection_compatibility.target_interface_type
connection_compatibility.target_role
connection_compatibility.target_attribute.ring_form
connection_compatibility.issuer_manufacturer
connection_compatibility.scope
```

Each claim retains the manufacturer source URL and raw evidence. The extraction rule is evidence-led: the product SKU is not consulted to manufacture the declaration.

Because the declaration can become authoritative compatibility evidence, a positive relation substring is not sufficient on its own. Extraction also checks bounded surrounding grammar for epistemic negation before the relation and a contradictory use/connection prohibition after it. For example, `Do not assume the Quick Clip can be attached to a D Ring` and `The Quick Clip can be attached to a D Ring, but must not be used that way` both fail closed. This is deliberately narrower than a clause-wide negative-token blacklist, so unrelated wording such as `without removing gloves` does not erase an otherwise explicit positive relation.

The declaration issuer is taken from the adapter's canonical manufacturer identity (`NLG`), not from caller-provided product-identity spelling or a lowercase CLI key. This keeps provenance stable when evidence from catalogue-discovery and direct CLI ingestion paths is combined.

## Resolution and candidate binding

`resolve_connector_interface_compatibility_declarations()` compiles accepted declaration claims into `ConnectorInterfaceCompatibilityDeclaration` objects.

A declaration contains no tether SKU, anchor SKU or candidate ID. It retains only:

- declaration identity;
- connector specification reference;
- source interface type;
- target interface type;
- target structural role;
- required target attributes;
- issuer manufacturer;
- scope; and
- source URLs.

`connection_contexts_from_compatibility_declarations()` then matches those primitives against concrete runtime endpoint/target interfaces.

Only after a primitive match is established does it create the existing candidate-scoped `ConnectionEvaluationContext` key:

```text
(tether_ref, target_owner_ref, endpoint_id, target_interface_id)
```

Those runtime identities prevent evidence leakage between candidates. They are not persisted as a compatibility declaration and do not turn the rule into SKU-pair logic.

The resulting context supplies an existing `ConnectionManufacturerAssessment` with:

```text
position = explicitly_compatible
claim_or_evidence_ref = manufacturer source URL
```

The ordinary connection evaluator remains the authority for precedence, endpoint-side semantics, contradictions and the final technical status.

## Quick Clip v1 matching scope

A Quick Clip declaration matches only when all of the following are established:

1. the source is a `tether_connection` endpoint;
2. the endpoint references the declared connector specification;
3. the source interface type is `clip`;
4. the target role is `anchor_attachment_tether_side`;
5. the target interface type is `ring`; and
6. the target explicitly carries `ring_form = d_ring`.

A generic `ring` is not promoted to a D-ring merely because the manufacturer uses D-rings elsewhere.

Likewise, a D-ring on a ToolAttachment does not match the first declaration because the first-party scope is an anchor-side relationship.

## Relationship to existing Quick Clip mechanism semantics

PR #42 established:

```text
connection_point.interface_type = clip
connector.attribute.opening_mechanism = trigger_operated
```

That primitive remains unchanged.

The new manufacturer declaration does **not** establish:

- `connector.opening_action_count`;
- `connector.locking_mode`;
- gate geometry;
- automatic closure or automatic locking;
- `clip == carabiner`;
- `clip == snap_hook`; or
- eligibility for `gated_connector_to_closed_interface.v1`.

A Quick Clip connection outside the exact declaration scope remains `unresolved` unless another acceptable basis applies.

## Endpoint-role boundary

This slice does not solve endpoint direction or interchangeability.

In particular, two physically identical Quick Clip endpoints with unresolved `connection_point.role` remain `TetherSide.UNKNOWN`. Candidate generation must not promote them to `either` merely because their connector/interface facts are symmetric.

The compatibility declaration may establish that a Quick Clip can engage a D-ring anchor once that endpoint is selected for the anchor side. It does not establish that either end of a particular tether may be assigned to that side.

A later symmetric-tether slice should introduce a separate evidence-backed interchangeability/assignment primitive rather than mutating missing endpoint-role claims.

## Provenance and persistence

The accepted declaration retains its first-party source URL. The candidate-scoped manufacturer assessment carries that evidence reference into the connection evaluation.

A matched candidate context is runtime composition. It does not create a persistent tether-SKU/anchor-SKU compatibility fact.

A later runtime observation, candidate selection or successful session condition likewise must not be promoted into manufacturer evidence.

## Benchmark boundary

The existing Batch 1 and Batch 2 supply-side goldens do not contain product 101456, so this slice does not change their expected claim sets.

Focused executable tests cover:

- positive first-party declaration extraction;
- SKU-independent extraction;
- canonical issuer identity across CLI and catalogue ingestion paths;
- cross-block, interrogative and bounded surrounding-negation fail-closed cases;
- preservation of unrelated negative wording outside the compatibility assertion;
- declaration resolution;
- exact D-ring anchor matching;
- generic-ring and wrong-role non-matching;
- downstream use of the existing manufacturer-declared compatibility basis;
- candidate-generation consumption of the derived context; and
- preservation of the existing unknown symmetric-endpoint-role boundary.

A future recommendation benchmark should exercise resolved catalogue evidence through candidate generation/evaluation rather than treating supply-side claim coverage alone as proof of end-to-end recommendation readiness.

## Deliberate non-goals

This slice does not:

- introduce SKU-pair compatibility;
- infer a generic Quick Clip connector class;
- widen D-ring evidence to every ring or `similar anchor point`;
- infer endpoint side/interchangeability;
- introduce a Quick Clip runtime-verification family;
- infer geometry or locking semantics from the declaration;
- change hard candidate evaluation;
- change contextual ranking or selection; or
- change session fallback semantics.
