# AnchorAttachment vertical proof and portability V4

## Scope

This note records the post-PR #60 vertical proof and the fresh V4 portability audit. It does not rewrite the historical semantic revisions of V1, V2 or V3.

Historical portability results remain frozen exactly as follows:

- V1 after PR #51: **0 A / 5 B / 3 C / 0 D**;
- V2 against post-PR #55 `main`: **0 A / 6 B / 2 C / 0 D**; and
- V3 at the PR #58 production-semantic freeze: **0 A / 5 B / 3 C / 0 D**.

PR #60 supplied the manufacturer-neutral AnchorAttachment installation/binding core: `PrimaryAnchorFeature` (`belt`, `beam`, `rail`), `wrap` / `cinch` / `thread_over`, same-feature predicates, exact `AnchorInstallationBinding` provenance, pre-generation binding retention through `AnchorPathOption`, and a separate hard anchor-installation eligibility check. It intentionally did not change tether-to-anchor connection compatibility, ranking, selection or exhaustion.

## Vertical proof through normal first-party ingestion

The follow-on vertical adds an ingestion-layer representation for accepted feature-local AnchorAttachment installation claims and a manufacturer-neutral compiler into the PR #60 runtime rule. The compiler groups all predicates for one installation path onto one concrete anchor feature and treats separate path subjects as alternatives. It has no manufacturer or SKU branches.

### Milwaukee 48-22-8855

First-party evidence establishes that the anchor-strap loop wraps around **beams and rails**, provides an oversized D-ring and has a 50 lb maximum working capacity.

The adapter therefore emits:

- `installation_method = wrap`;
- a `beam` path OR a `rail` path;
- an `anchor_attachment_tether_side` ring with `ring_form = d_ring`; and
- rated capacity.

No beam/rail dimensions are invented because the reviewed manufacturer wording does not publish them.

### FallTech 5424A10

First-party evidence establishes a **choke-on** installation, explicit fit to most full-body-harness belts, a steel D-ring tether point and a 5 lb maximum tool capacity.

The adapter therefore emits:

- `installation_method = cinch`;
- one explicit `belt` path;
- an `anchor_attachment_tether_side` D-ring; and
- rated capacity.

The separate phrase about “other small diameter anchorage locations” is not converted into a numeric envelope or an unsupported primary-anchor feature. Qualitative size wording remains qualitative evidence.

### Ergodyne Squids 3171 / item 19171

The verified first-party product page is joined to Ergodyne's first-party 3171/3172/3174/3176/3177 instruction document. Extraction is identity-scoped to the 3171 section and 3171 table row; sibling-model installation facts are not inherited.

The 3171 instructions establish that the enclosed loop must be threaded onto an open-ended primary anchor such as a belt, that the belt is undone for threading and then refastened/secured, and that the applicable 3171 row publishes a 3 in x 0.5 in primary-anchor size bound.

The adapter therefore emits:

- `installation_method = thread_over`;
- one `belt` path;
- `open_for_threading = true`;
- `can_be_resecured = true`;
- `section_height <= 3 in` and `section_thickness <= 0.5 in`, normalized to millimetres by the generic compiler; and
- the D-ring tether-side interface and rated capacity from first-party evidence.

The vertical tests prove that every predicate must pass on the same concrete belt feature. Facts split across two different belts cannot be stitched together into eligibility.

## Downstream boundary preserved

The vertical proof stops at the intended seam:

```text
first-party evidence
  -> accepted ingestion claims
  -> generic AnchorAttachment installation rule
  -> concrete PrimaryAnchorFeature evaluation
  -> exact AnchorInstallationBinding
  -> existing AnchorPathOption/candidate path
```

It does not add or relax tether-to-anchor connection compatibility, ranking, selection or exhaustion rules. It does not introduce SKU-pair compatibility logic. Legacy unbound candidate identity remains governed by the PR #60 behavior.

## Fresh portability V4

The V4 sample was fixed before classification so product selection could not be biased toward the desired result. It contains eight previously unaudited identities across five manufacturers and deliberately moves away from V3's tether-heavy sample toward worker-worn anchors, rigid aerial-bucket anchors, fresh tool-side attachments and one conventional tether control.

It excludes every V1-V3 identity and the three products used for the vertical proof.

The frozen V4 result is:

```text
A facts_only               0
B vendor_ingestion_only    4
C new_reusable_primitive   4
D sku_specific_exception   0
```

The B-class products are:

- Milwaukee 48-22-8870 2 lb D-Ring Web Attachment;
- Ergodyne Squids 3708 / item 19713 Wire Tool Attachment;
- FallTech 5027F Speed-clip Tool Attachment; and
- Klein TT1 Tool Tether.

All four fit existing manufacturer-neutral ToolAttachment/tether, captive-feature, wrap/required-pairing, connector/declaration, endpoint, capacity and length semantics. Their remaining work is catalogue acquisition/extraction and evidence normalization.

The C-class products are:

- FallTech 5331A1 Wrist Attachment Anchor;
- GRIPPS H01086 Adjustable Wrist Anchor;
- Ergodyne Squids 3178 / item 19178 Locking Aerial Bucket Hook; and
- Klein 5144LG3 3-Inch Gated Bucket Hook.

They expose **two recurring cross-vendor seams**, not four product exceptions.

### Recurring seam 1: worker-worn wrist anchors

FallTech and GRIPPS independently publish load-rated AnchorAttachment products that install directly around the worker's wrist. The post-PR #60 primary-anchor vocabulary cannot represent that target truthfully as `belt`, `beam` or `rail`.

The next model investigation should establish the smallest reusable worker-worn primary-anchor feature abstraction needed by the evidence, likely beginning with a concrete wrist feature rather than prematurely creating a broad body-location hierarchy. Adjustable or “all sizes” wording must not be converted into numeric wrist dimensions unless the manufacturer publishes such dimensions.

The existing exact `AnchorInstallationBinding` path should then be reused unchanged so the selected worker-worn feature and evidence provenance reach candidate generation.

### Recurring seam 2: aerial-bucket lip hooks

Ergodyne and Klein independently publish rigid hook-style AnchorAttachments that install on an aerial-bucket lip. The products do not wrap, cinch or thread over a belt/beam/rail. Both manufacturers publish explicit lip-target evidence, and Klein publishes a 3 in lip requirement.

The next model investigation should establish:

- the smallest reusable primary-anchor lip/edge feature needed for this family; and
- an evidence-backed hook-on/clip-on installation method that evaluates one concrete lip/edge feature and uses dimensional bounds only where published.

A bucket lip should not be silently widened into `rail`, and product nominal size must not become a complete fit envelope without evidence.

## Decision after V4

The condition for shifting the development centre of gravity to catalogue throughput and the demand-side MVP is **not met yet**.

V4 is exactly split between B and C (**4 B / 4 C**), so it is not predominantly A/B. More importantly, the C pressure is comparable and recurring: two independent manufacturers expose the wrist-anchor seam and two others expose the bucket-lip/hook seam. D remains zero, which continues to support a manufacturer-neutral architecture, and the four B cases confirm that catalogue-throughput work is increasingly substantial.

The next semantic work should therefore remain narrow:

1. resolve and prove the smallest reusable worker-worn/wrist primary-anchor feature and installation semantics across the FallTech and GRIPPS cases;
2. resolve and prove the smallest reusable bucket-lip/edge feature plus hook-on/clip-on installation semantics across the Ergodyne and Klein cases;
3. keep tether-to-anchor compatibility, ranking, selection and exhaustion unchanged unless independent evidence exposes a separate gap; and
4. run another materially different fresh portability sample after those two recurring seams are closed.

Catalogue onboarding can continue in parallel, especially for B-class products, but V4 does not justify making throughput or the demand-side MVP the primary development centre yet.

## Regression status

The PR #61 branch passed the full `Ingestion live smoke` workflow after the vertical proof and V4 freeze were added: unit tests, live manufacturer benchmark, Batch 1 scoring, immutable Batch 2 blind-baseline scoring, post-blind NLG evaluation/scoring and artifact upload were all green.
