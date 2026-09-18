# AnchorAttachment installation eligibility and primary-anchor binding

## Status

The manufacturer-neutral AnchorAttachment installation/binding boundary was introduced by PR #60, vertically proven through normal first-party ingestion/resolution by PR #61, and extended by PR #62 to close the two recurring V4 portability seams.

This document defines how TetherLens represents and evaluates installation of an `AnchorAttachment` onto one concrete primary-anchor feature before the resulting tether-side interface participates in ordinary tether-endpoint compatibility.

The boundary is intentionally narrow. It does not model arbitrary structural-anchor engineering suitability, does not introduce a general CAD model, and does not widen tether-to-anchor connection compatibility.

## Architectural boundary

The physical relationships remain separate:

```text
primary-anchor feature
        ↓
AnchorAttachment installation eligibility + concrete binding
        ↓
installed AnchorAttachment
        ↓
provided tether-side interface
        ↓
ordinary tether-endpoint compatibility
```

Installation eligibility must not be collapsed into tether-endpoint compatibility. Candidate generation also does not interpret manufacturer installation text; it consumes an already-resolved installation proof.

## PrimaryAnchorFeature

`PrimaryAnchorFeature` represents one concrete physical feature that may receive an AnchorAttachment. It is separate from `ToolInterfaceFeature`, because the accepted anchor-side evidence requires a different vocabulary.

The current `PrimaryAnchorFeatureKind` values are:

```text
belt
beam
rail
wrist
bucket_lip
```

The first three were introduced by PR #60. PR #62 adds `wrist` and `bucket_lip` only after the fresh V4 cohort exposed each as a recurring cross-vendor seam.

A feature retains:

- `feature_id`;
- feature kind;
- optional location description;
- feature-local canonical dimensions in millimetres; and
- feature-local normalized attributes.

`ResolvedPrimaryAnchor` owns one or more concrete features under one `primary_anchor_ref`. Feature IDs must be unique within that resolved anchor.

The vocabulary should expand only when accepted evidence and a recommendation decision require another reusable feature family. Do not add broad aliases such as `structure`, `anchorage`, `small_anchor`, `body_location` or generic `edge` merely because such words occur in source text.

## Installation method

`AnchorInstallationMethod` records the primary physical mechanism retaining the AnchorAttachment on the selected feature.

The current values are:

```text
wrap
cinch
thread_over
fasten_around
slip_on
hook_on
```

These are mechanism-led rather than manufacturer-led. `fasten_around` covers evidence-backed adjustable fastening around a concrete receiving feature such as a wrist or rail. `slip_on` covers an attachment that is retained by being slipped over a receiving feature such as a hand and onto the wrist, without inventing a fastening step that the source does not describe. `hook_on` covers a rigid hook-style installation onto a supported concrete feature such as an aerial-bucket lip.

The method is not a substitute for the receiving feature or for geometry. For example, `hook_on` does not mean that any edge is suitable, and `bucket_lip` does not prove that every hook product fits it. Both the method and the feature-local eligibility predicates remain explicit.

## Eligibility model

`AnchorAttachmentInstallationRule` contains:

- stable `rule_id`;
- owning AnchorAttachment `source_product_ref`;
- installation method;
- one or more eligibility paths; and
- source URLs.

Each `AnchorEligibilityPath` is an AND-set of requirements and prohibitions evaluated against exactly one `PrimaryAnchorFeature`. Multiple paths form bounded OR alternatives. Empty paths are invalid.

Supported predicate scopes remain feature-local:

```text
feature_kind
location_description
dimension:<code>
attribute:<code>
```

The evaluator preserves the conservative three-state boundary:

```text
at least one complete matching feature
  -> ELIGIBLE

no match, but a potentially applicable path lacks required facts
  -> UNRESOLVED

all complete paths contradict the available feature facts
  -> INELIGIBLE
```

Missing evidence never becomes suitability.

### Same-feature invariant

Every predicate in one path must be satisfied by the same concrete primary-anchor feature. Facts from separate features are never stitched together.

This invariant applies equally to topology, dimensions and normalized attributes. A feature that has the right kind but lacks a required attribute remains unresolved; a different feature carrying that attribute cannot satisfy the path on its behalf.

## Ingestion and rule compilation

Accepted installation evidence uses a feature-local `anchor_installation_path` claim subject. A product-level `anchor_installation.method` claim owns the installation mechanism, while every path subject contains the predicates that must apply to one concrete receiving feature.

The manufacturer-neutral compiler:

- requires one unambiguous installation method;
- requires an explicit feature kind on every path;
- fails closed on conflicting accepted feature kinds inside one path;
- normalizes evidence-backed dimensional predicates to millimetres;
- maps feature attributes and location to the runtime predicate vocabulary;
- preserves exact source provenance; and
- contains no manufacturer or SKU branches.

Vendor adapters may remain source-format specific, but downstream installation semantics must remain manufacturer-neutral.

## Concrete binding and candidate boundary

An eligible installation is materialized as `AnchorInstallationBinding` and retains:

```text
primary_anchor_ref
installation_feature_id
rule_id
source_product_ref
installation_method
eligibility_proofs[]
source_urls[]
```

When multiple paths prove the same concrete feature, they remain multiple audit proofs on one physical binding rather than multiplying candidate installations.

A bound `AnchorPathOption` may carry the exact binding plus its exact eligible evaluation. Candidate generation only preserves that already-resolved proof; it does not reinterpret manufacturer evidence.

For bound paths, the selected primary anchor, concrete feature and installation rule participate in canonical candidate identity. Legacy unbound/direct-container paths retain their historical identity behavior.

Anchor installation remains a hard viability check with distinct identity `anchor_installation_eligibility`. It does not create a ranking preference, compatibility basis, selection rule or exhaustion state.

## Proven vertical families

### Beam / rail wrap

Milwaukee-shaped evidence compiles as:

```text
method = wrap
paths:
  - feature_kind = beam
  - feature_kind = rail
```

No beam or rail dimensions are invented when the accepted evidence does not establish them.

### Belt cinch

FallTech-shaped evidence compiles the explicit belt subset as:

```text
method = cinch
path:
  feature_kind = belt
```

Qualitative wording such as `small diameter` is not converted into synthetic geometry.

### Thread-over belt

Ergodyne Squids 3171-shaped evidence compiles as one same-feature path with explicit open/refastenable topology and published dimensional bounds:

```text
method = thread_over
feature_kind = belt
AND attribute:open_for_threading = true
AND attribute:can_be_resecured = true
AND dimension:section_height <= 76.2 mm
AND dimension:section_thickness <= 12.7 mm
```

### Worker-worn / rail adjustable fastening

PR #62 closes the recurring V4 wrist-anchor seam with the concrete `wrist` feature and `fasten_around` mechanism.

FallTech 5331A1 proves a wrist path without turning `UniFit` wording into numeric wrist geometry. GRIPPS H01086 independently proves the same wrist family and, because its first-party wording explicitly permits hand rails as well as the wrist, also emits a separate `rail` path under the same `fasten_around` mechanism.

The two paths remain alternatives over concrete features; no wrist fact is stitched onto a rail or vice versa. GRIPPS `all sizes` / adjustable wording remains qualitative and does not become a numeric envelope.

### Worker-worn slip-on wrist anchor

PR #72 adds `slip_on` only for the distinct physical mechanism exposed by GRIPPS H01085: the anchor is slipped over the hand onto the wrist rather than tightened, wrapped or fastened around it.

The current production shape is deliberately narrow:

```text
method = slip_on
path:
  feature_kind = wrist
```

Small/Medium/Large catalogue labels remain product variants, not numeric wrist-fit geometry. The provided tether-anchor point remains type-unknown when the source establishes its role but not its physical form.

### Aerial-bucket lip hook

PR #62 closes the recurring V4 aerial-bucket seam with `bucket_lip` plus `hook_on`.

Ergodyne Squids 3178 and Klein 5144LG3 retain the manufacturers' published 2 in / 3 in bucket-lip labels as normalized nominal feature attributes. Those labels are not promoted into generic numeric fit envelopes.

For the Ergodyne family document, row-local identity is mandatory: the instruction selection-grid record matching the requested SKU is selected before its nominal lip class is parsed. The 19178 and 19179 rows therefore remain distinct, and sibling/package variants cannot silently inherit another row's fit class.

## Provenance and identity guardrails

Manufacturer provenance and product identity are separate checks.

A manufacturer-controlled host or document namespace answers whether a source is first party; it does not by itself prove that the source belongs to the requested product. Product-page extraction therefore remains identity-scoped.

PR #62 reinforces this boundary in three places:

- FallTech manuals served through BigCommerce are trusted only inside FallTech's store-specific `s-1wxw1202sk/content/product_documents/` namespace, not the shared `cdn11.bigcommerce.com` host generally;
- GRIPPS and Klein AnchorAttachment extraction verifies the resolved artifact against the requested product identity so same-host redirects cannot leak another product's claims; and
- Ergodyne multi-product instruction evidence is bounded to the requested identity-local row before sibling-specific facts are parsed.

These are ingestion/evidence boundaries, not downstream SKU exceptions.

## Guardrails

The current AnchorAttachment installation model does not:

- change tether-to-anchor interface compatibility;
- add SKU-pair recommendation logic;
- infer a primary-anchor feature from a product name alone;
- infer numeric fit from qualitative size wording or nominal product labels;
- combine predicates from different primary-anchor features;
- treat missing topology, attributes or dimensions as a pass;
- widen `bucket_lip` into generic `rail` or `edge` semantics;
- widen `wrist` into a generic body-location hierarchy;
- attach anchor-installation proof to a container connection;
- create a structural-engineering/load-rated anchorage assessment;
- change endpoint assignment, capacity, ranking, contextual selection, session behavior or global exhaustion; or
- rewrite historical V1/V2/V3/V4 portability classifications.

## Portability follow-on

Historical portability cohorts remain frozen at their original semantic revisions:

- V1: **0 A / 5 B / 3 C / 0 D**;
- V2: **0 A / 6 B / 2 C / 0 D**;
- V3: **0 A / 5 B / 3 C / 0 D**; and
- V4: **0 A / 4 B / 4 C / 0 D**.

PR #62 closes the two recurring V4 C seams; it does not rewrite V4. The next portability step should be a materially different fresh cohort frozen against merged post-PR #62 semantics. If that sample is predominantly A/B and shows no comparable recurring C/D pressure, development should shift its centre of gravity toward catalogue throughput and the demand-side MVP, while portability continues as a periodic regression/stress test.
