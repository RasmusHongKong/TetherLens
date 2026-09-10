# Non-captive ToolAttachment capture and fit

## Status

Reusable production boundary for ToolAttachments that can install onto a tool handle without requiring that handle to be an already-captive tether feature, when manufacturer evidence establishes the handle geometry but does not provide a complete numeric tool-feature fit envelope.

This document complements `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `single-feature-captive-eligibility.md`, `recommendation-session.md`, and the frozen V2 portability audit in `portability-benchmark.md`.

## Problem

PR #56 isolated the same architecture question in two independent V2 C-class products:

- GRIPPS H01150 SnapLock; and
- 3M DBI-SALA 1500028 Quick Spin Medium.

Both create a tether connection point by installing around/on handle-style tool geometry that does not need to be a pre-existing captive tether feature. The runtime feature model already represents `FeatureKind.HANDLE`, `FeatureKind.EXTERNAL_SECTION`, and all `CaptiveState` values, while `mechanical_capture` can remain the attachment-method family where the accepted retaining-action evidence supports it.

The missing production boundary was therefore not a new manufacturer-specific geometry type. It was the conservative separation between:

1. coarse executable installation geometry;
2. numeric dimensional fit when a complete manufacturer-backed fit envelope exists; and
3. an installed-fit confirmation when the manufacturer requires a secure/snug fit that catalogue dimensions alone do not establish.

A key distinction is that evidence saying an attachment installs on a `handle` does **not** establish `captive_state = non_captive` as a requirement. The architecture gap is the ability to support non-captive handles without requiring captivity; it is not evidence that captive/closed handles are prohibited. Captive state is therefore left unconstrained unless the manufacturer explicitly makes it part of eligibility.

## Evidence findings

### GRIPPS H01150 SnapLock

The current first-party GRIPPS product page identifies H01150 as a self-closing tool connector, states that it installs to a tool's handle or neck, and offers Small, Medium, Large and Extra Large variants. It does not publish a complete min/max tool-feature fit envelope on the reviewed product evidence.

Source:

- https://gripps.com/products/snaplock

The S/M/L/XL labels therefore remain product variant labels. They must not be converted into inferred tool-handle diameters, circumferences, or acceptance ranges.

The current implementation deliberately adds only the common executable subset justified by the recurring architecture question:

```text
attachment_selection_class = handle_attachment

-> bind handle
   where:
     feature_kind = handle
```

No `captive_state` predicate is compiled. This means an explicitly non-captive handle can participate, which closes the V2 gap, while a captive or captive-state-unknown handle is not rejected merely because the source did not impose that condition.

GRIPPS' separate `neck` wording does not automatically create an `EXTERNAL_SECTION` alternative in this slice. That additional composition should be added only when accepted evidence and a concrete vertical proof establish the correct normalized geometry and fit semantics.

### 3M DBI-SALA 1500028 Quick Spin Medium

The first-party 3M/Python Safety Quick Spin instructions state that Quick Spins slide onto a tool handle, should be used where they fit tightly, and must not be used if a snug fit cannot be secured. Installation instructs the user to select an adapter that properly fits the tool handle, push/twist it onto the tool with enough resistance to create a snug fit, and ensure it is firmly in place before use.

The same instructions list 1500028 as a 0.8 in / 2 cm diameter product with a 1 lb / 0.5 kg load rating. That nominal product diameter is not presented as a complete permitted tool-handle fit envelope.

Sources:

- https://multimedia.3m.com/mws/media/1300988O/ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf
- https://multimedia.3m.com/mws/media/1446232O/3m-dbi-sala-fall-protection-for-tools-pocket-guide-aunz-english.pdf

The correct runtime consequence is therefore a bounded installed-fit obligation rather than invented numeric eligibility:

```text
secure_attachment_fit_required = true

unknown -> requires_action
confirmed secure fit -> passed
secure fit cannot be achieved -> failed
```

## Production model

### Handle eligibility without a captive-state requirement

`handle_attachment` is a manufacturer-neutral production selection class. It compiles to one feature-bound path requiring only:

```text
feature_kind = handle
```

It deliberately does **not** require either `captive` or `non_captive`. The source evidence reviewed for SnapLock and Quick Spin establishes handle installation, not a closed-world restriction on handle topology.

This differs from `captive_handle_attachment`, which remains the correct class when accepted manufacturer evidence explicitly requires a captive handle. The two classes therefore express different evidence scopes:

```text
handle_attachment
  -> handle; captive state unconstrained

captive_handle_attachment
  -> handle AND captive_state = captive
```

`handle_attachment` also contains no dimension predicate and does not widen to `EXTERNAL_SECTION`. A handle with any captive-state value may satisfy the geometry path; an external section does not satisfy it merely because it is handle-like or non-captive.

### Secure installed-fit obligation

`secure_attachment_fit_required = true` is a distinct `PRE_USE_OBLIGATION` product constraint.

It is not an alias for `pre_use_attachment_test_required`:

```text
secure_attachment_fit_required
  -> confirm that the selected installed attachment has achieved the manufacturer-required secure/snug fit

pre_use_attachment_test_required
  -> perform the separate manufacturer-required attachment test
```

A product may require either or both. Satisfying one must never satisfy the other.

The secure-fit condition remains bound through the existing candidate/session identity chain to the exact ToolAttachment component instance and selected installation feature. Candidate generation may therefore retain a structurally eligible ToolAttachment path while hard evaluation returns `recommended_with_constraints` until the pre-use fit condition is resolved. A failed fit confirmation rejects that active candidate through the existing session fallback semantics.

## Dimensional boundary

The existing `external_section_attachment` compiler remains the numeric-fit precedent: it requires a complete source-local min/max diameter-fit envelope before it can compile a dimensional eligibility path.

This slice does not weaken that rule. In particular:

```text
S / M / L / XL label
!= tool-feature fit envelope

nominal attachment diameter
!= tool-feature fit envelope
```

If later first-party evidence supplies explicit tool-feature minimum/maximum dimensions for SnapLock, Quick Spin, or another product family, those bounds may feed the existing feature-dimension/predicate model. Until then, installed secure fit remains a runtime/pre-use fact rather than a fabricated catalogue dimension.

## Deferred 3M tapered-surface prohibition

The reviewed Quick Spin installation instructions also contain a separate warning:

> Never attach tool lanyards or attachment points to a tapered surface.

This is materially different from the snug/secure-fit requirement. It is a geometry/location prohibition and should eventually participate as a hard installation constraint for applicable 3M attachment-point candidates.

PR #57 deliberately **does not** implement that prohibition. The current `prohibited_tool_part_type` primitive describes part identity rather than section profile, and this slice should not overload it or introduce a one-product predicate merely to make 1500028 complete. Before the 3M Quick Spin vertical is declared recommendation-ready, model this warning using the smallest reusable geometry/profile fact and hard prohibition justified by the evidence, with the prohibition bound to the exact selected installation feature.

The deferred item must not be lost when the vendor vertical is implemented.

## Guardrails

PR #57 does not:

- infer a fit range from product size labels or nominal attachment diameter;
- infer that `handle` evidence means `non_captive` or that non-captive capability means captive handles are forbidden;
- promote a non-captive feature to captive;
- broaden `handle_attachment` to external sections or necks without evidence-backed composition;
- reuse `pre_use_attachment_test_required` for a different physical observation;
- add GRIPPS-, 3M-, or SKU-specific downstream compatibility logic;
- change connection compatibility, capacity evaluation, contextual feasibility, ranking, or global exhaustion semantics; or
- rewrite either frozen portability answer key.

## Follow-on proof

The next vertical proof should ingest representative first-party evidence for the two independent manufacturers where practical and demonstrate that both can flow through the same neutral handle/secure-fit primitives without downstream product-pair logic.

The 3M proof must also address the deferred tapered-surface prohibition before treating Quick Spin as fully recommendation-ready. After the reusable boundary is vertically proven, run one materially different portability sample; if it remains predominantly A/B with no comparable recurring C or D pressure, portability should cease to be the default development driver.
