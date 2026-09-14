# AnchorAttachment installation eligibility and primary-anchor binding

## Status

Core manufacturer-neutral semantic boundary introduced by PR #60 for the recurring V3 AnchorAttachment portability seam and vertically proven through normal first-party ingestion/resolution by PR #61.

This document defines how TetherLens represents and evaluates the installation of an `AnchorAttachment` onto one concrete primary-anchor feature before the resulting tether-side interface participates in ordinary tether-endpoint compatibility.

The boundary is intentionally narrow. It does not attempt to model arbitrary structural-anchor engineering suitability, does not introduce a general CAD model, and does not widen tether-to-anchor connection compatibility.

## Problem

The V3 portability cohort identified the same missing upstream layer in three independent AnchorAttachment products:

- Milwaukee 48-22-8855 Anchor Strap: wraps around supported beam/rail geometry;
- FallTech 5424A10 Waist Belt Cinch Anchor Attachment: choke/cinch installation on supported belt-style anchorage and broader qualitative small-anchor wording; and
- Ergodyne Squids 3171 / SKU 19171: an enclosed loop threaded over an open-ended/refastenable primary anchor subject to explicit dimensional conditions.

Before PR #60, the runtime core could already represent:

```text
AnchorAttachment component
  -> provided anchor_attachment_tether_side interface
  -> AnchorPathOption
  -> tether endpoint engagement
```

But `AnchorPathOption` assumed the AnchorAttachment had already been validly installed. There was no generic evidence-backed mechanism to prove that the selected AnchorAttachment could install on one concrete primary-anchor feature and preserve that feature identity downstream.

The missing relation is therefore:

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

The first and second connection in that chain are different physical relationships. Installation eligibility must not be collapsed into tether-endpoint compatibility.

## PrimaryAnchorFeature

`PrimaryAnchorFeature` represents one concrete physical feature that may receive an AnchorAttachment.

It is deliberately separate from `ToolInterfaceFeature`. Tool features use a tool-anatomy vocabulary such as handle, through-opening, external section and surface. The reviewed anchor evidence instead requires a smaller anchorage-side vocabulary.

The initial `PrimaryAnchorFeatureKind` values are limited to:

```text
belt
beam
rail
```

A feature also retains:

- `feature_id`;
- optional location description;
- feature-local canonical dimensions in millimetres; and
- feature-local normalized attributes.

This vocabulary should expand only when real manufacturer evidence and a recommendation decision require another reusable feature family. Do not add generic aliases such as `structure`, `small_anchor`, `anchorage`, or product-specific terms merely because they appear in source wording.

`ResolvedPrimaryAnchor` owns one or more concrete `PrimaryAnchorFeature` values under one `primary_anchor_ref`. Feature IDs must be unique within that resolved anchor.

## Installation method

`AnchorInstallationMethod` records the primary physical mechanism retaining the AnchorAttachment on its selected primary-anchor feature.

The initial values are:

```text
wrap
cinch
thread_over
```

These are mechanism-led rather than manufacturer-led.

Although `wrap` and `cinch` have analogous meanings in the existing ToolAttachment attachment-method vocabulary, PR #60 does not silently reuse the ToolAttachment-scoped persisted field. The anchor-side semantic is explicit and may later be unified with a broader installation-method vocabulary only if that refactor preserves existing evidence boundaries.

The method is not a substitute for geometry. For example:

```text
method = wrap
```

does not establish which structural features may be wrapped, while:

```text
feature_kind = beam
```

does not establish that a particular AnchorAttachment uses wrapping rather than cinching or threading.

Both facts remain explicit.

## Eligibility model

`AnchorAttachmentInstallationRule` contains:

- stable `rule_id`;
- the owning AnchorAttachment `source_product_ref`;
- installation method;
- one or more eligibility paths; and
- source URLs.

Each `AnchorEligibilityPath` is an AND-set of requirements and prohibitions evaluated against exactly one `PrimaryAnchorFeature` instance. Multiple paths form bounded OR alternatives. Empty paths are invalid rather than vacuously matching every feature.

Supported predicate scopes are deliberately feature-local:

```text
feature_kind
location_description
dimension:<code>
attribute:<code>
```

`feature_kind` values must belong to the bounded `PrimaryAnchorFeatureKind` vocabulary. A misspelled kind must not become a universal match under a negative predicate.

Scalar equality also preserves semantic type. In particular, boolean topology facts are distinct from numeric values: `true` does not equal `1`, and `false` does not equal `0`. Ordinary integer/float numeric equality remains valid.

Source provenance is normalized at the rule, evaluation and binding boundaries. Source URL entries are trimmed and blank/whitespace-only entries are rejected; a list containing an empty string does not count as evidence provenance.

The evaluation has the same conservative three-state boundary used elsewhere:

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

Every predicate in one eligibility path must be satisfied by the same concrete primary-anchor feature.

For example, this must fail:

```text
feature A: open for threading, but oversized
feature B: within dimensions, but cannot be opened
```

The system must not combine the topology from feature A with the dimensions from feature B.

This mirrors the established ToolAttachment feature-binding invariant but uses a distinct anchor-side feature model.

## Ingestion and rule compilation

PR #61 adds the normal evidence-to-runtime path without making candidate generation interpret manufacturer text.

Accepted installation evidence uses a feature-local `anchor_installation_path` claim subject. A product-level `anchor_installation.method` claim owns the installation mechanism, while every path subject contains the feature-local predicates that must apply to one concrete primary-anchor feature. Separate path subjects are OR alternatives; predicates within one path remain an AND-set.

The manufacturer-neutral compiler:

- requires one unambiguous installation method;
- requires an explicit feature kind on every path;
- fails closed on conflicting accepted feature kinds within one path;
- normalizes dimensional predicates to millimetres;
- maps feature attributes and location to the existing runtime predicate keys;
- maps `REQUIRES` to a required equality predicate and `PROHIBITS` to an equality prohibition;
- preserves exact source URLs; and
- contains no manufacturer or SKU branches.

This lets vendor adapters remain evidence-specific while the downstream installation rule stays reusable.

The PR #61 vertical proves the compiler through normal first-party ingestion for Milwaukee 48-22-8855, FallTech 5424A10 and Ergodyne Squids 3171 / 19171. Ergodyne's first-party family instruction document is identity-scoped to the 3171 row/section; sibling-model facts are not inherited. FallTech's qualitative `small diameter` wording is not converted into numeric geometry, and Milwaukee does not invent beam/rail dimensions.

## Concrete binding

An eligible installation is materialized as `AnchorInstallationBinding`.

The binding retains:

```text
primary_anchor_ref
installation_feature_id
rule_id
source_product_ref
installation_method
eligibility_proofs[]
source_urls[]
```

When several eligibility paths prove the same concrete feature, they remain multiple audit proofs on one physical binding rather than multiplying otherwise identical candidate installations.

`bound_anchor_installation_evaluation()` projects the binding into the exact eligible evaluation retained by the downstream candidate. Rule identity, source product, selected primary anchor, installation method and source URLs remain attached; they are not reconstructed later from candidate IDs or human-readable reason text.

## AnchorPathOption boundary

Candidate generation does not interpret manufacturer installation claims.

A bound `AnchorPathOption` may carry:

```text
installation_binding
installation_eligibility
```

The option validates that:

- an eligibility result cannot exist without a selected binding;
- a selected binding must carry an `ELIGIBLE` result;
- every retained match refers only to the selected feature;
- proof path/binding-name pairs exactly match the binding;
- evaluation provenance exactly matches the binding;
- the binding's `source_product_ref` belongs to a selected anchor component; and
- every target on a bound path is an `anchor_attachment_tether_side` interface, never a container connection.

Legacy direct/container anchor paths may continue to omit these fields. PR #60 does not retroactively assert that every historical anchor path is an installed AnchorAttachment path.

## Candidate identity and provenance

A bound anchor installation is part of physical candidate identity.

For bound paths, the canonical candidate ID additionally contains:

```text
primary_anchor_ref
anchor_installation_feature_id
anchor_installation_rule_id
```

This prevents two otherwise-identical candidates installed on different primary-anchor features from collapsing into one identity.

Unbound legacy paths retain their pre-PR #60 candidate ID byte-for-byte; anchor-binding keys are added only when a binding exists.

`CandidatePathSelection` retains the full `AnchorInstallationBinding`. `CandidateConfiguration` now retains that same binding alongside the exact `AnchorInstallationEligibilityEvaluation`, and `GeneratedCandidate` requires the configuration binding to equal the selection binding. The configuration validator also requires selected-feature, proof and provenance equality whenever a binding is present. This prevents an otherwise valid eligibility result from a different primary anchor or source product from being reused on another candidate.

Configuration-scoped policy identity also includes the selected primary anchor, feature and installation rule when a binding exists. A policy result for one concrete anchor installation must not leak to another installation that happens to use the same tether/product interfaces.

## Hard evaluation

Anchor installation eligibility is a hard candidate viability check.

The evaluator reuses the existing generic check category:

```text
check_type = attachment_eligibility
```

but uses the distinct check identity:

```text
check_id = anchor_installation_eligibility
```

A valid bound eligible result produces `PASSED`. An eligible evaluation without a concrete selected binding remains `UNRESOLVED`; it cannot establish a recommendation merely because one or more anchor features match. Ineligible or unresolved installation evidence blocks the candidate through the existing hard-evaluation semantics.

The hard check retains:

- source AnchorAttachment product;
- selected primary anchor;
- installation rule;
- selected feature; and
- source URLs.

No new ranking preference, compatibility basis, selection rule or exhaustion state is introduced.

## V3 evidence-shaped compositions

The core model is intentionally vendor-neutral. The following examples describe the semantic shapes that motivated it; they are not SKU branches.

### Beam/rail wrap

Milwaukee-shaped evidence compiles conservatively as:

```text
method = wrap

paths:
  - feature_kind = beam
  - feature_kind = rail
```

No width, diameter, profile or other fit geometry is inferred when the reviewed evidence does not establish it.

### Belt cinch

FallTech-shaped evidence compiles the explicit belt subset as:

```text
method = cinch

path:
  feature_kind = belt
```

Qualitative wording such as `small-diameter anchorage` must not be converted into a synthetic diameter threshold. A broader route remains uncompiled until evidence establishes reusable feature semantics or a complete dimensional condition.

### Thread-over belt with explicit topology/dimensions

Ergodyne-shaped evidence compiles as one same-feature path:

```text
method = thread_over

feature_kind = belt
AND attribute:open_for_threading = true
AND attribute:can_be_resecured = true
AND dimension:section_height <= 76.2 mm
AND dimension:section_thickness <= 12.7 mm
```

The dimensional values are evidence-backed installation bounds, not generic belt dimensions or inferred product fit.

## Guardrails

PRs #60-#61 do not:

- change tether-to-anchor interface compatibility;
- add `AnchorAttachment` SKU-pair compatibility rules;
- infer a primary-anchor feature from an AnchorAttachment product name;
- infer numeric fit from qualitative `small`, `small-diameter`, size labels or nominal product dimensions;
- combine predicates from different primary-anchor features;
- treat missing topology, attributes or dimensions as a pass;
- treat numeric `1`/`0` as boolean topology facts;
- accept blank source strings as evidence provenance;
- attach a primary-anchor installation proof to a container connection;
- convert a generic structural anchor into beam or rail without evidence;
- create a general structural-engineering or load-rated anchorage assessment;
- change tether endpoint roles, assignment semantics, capacity rules, ranking, contextual selection, session behavior or global exhaustion;
- rewrite frozen V1/V2/V3/V4 portability classifications; or
- require legacy unbound anchor/container paths to invent an AnchorAttachment installation binding.

## Portability V4 follow-on

PR #61 completed the V3 three-vendor vertical and then froze a materially different eight-product V4 portability sample at **0 A / 4 B / 4 C / 0 D**. The pivot condition toward catalogue-throughput-led development was therefore not met.

The four C products form two recurring cross-vendor seams:

- worker-worn wrist anchors (FallTech 5331A1 and GRIPPS H01086), which need the smallest reusable worker-worn/wrist primary-anchor feature plus evidence-backed adjustable fastening semantics; and
- aerial-bucket lip hooks (Ergodyne Squids 3178 / 19178 and Klein 5144LG3), which need a reusable bucket-lip/edge feature plus hook-on/clip-on installation semantics.

Those are the next architecture investigations. They should extend the same exact-feature binding model rather than changing tether-to-anchor compatibility, ranking, selection or exhaustion. Catalogue B-class onboarding can continue in parallel. See `anchor-installation-portability-v4.md` for the frozen V4 evidence and decision rationale.
