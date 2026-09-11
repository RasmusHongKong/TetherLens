# Non-captive ToolAttachment capture and fit

## Status

Reusable production boundary for ToolAttachments that can install onto a tool handle without requiring that handle to be an already-captive tether feature, when manufacturer evidence establishes the handle geometry but does not provide a complete numeric tool-feature fit envelope.

PR #57 introduced the neutral handle/secure-fit primitives. PR #58 vertically proves those primitives against GRIPPS H01150 SnapLock and 3M DBI-SALA 1500028 Quick Spin Medium, adds the separate hard tapered-surface prohibition required by 3M evidence, and keeps all fit/geometry claims feature-bound and evidence-limited.

This document complements `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `single-feature-captive-eligibility.md`, `recommendation-session.md`, and the frozen portability audits in `portability-benchmark.md`.

## Problem

PR #56 isolated the same architecture question in two independent V2 C-class products:

- GRIPPS H01150 SnapLock; and
- 3M DBI-SALA 1500028 Quick Spin Medium.

Both create a tether connection point by installing around/on handle-style tool geometry that does not need to be a pre-existing captive tether feature. The runtime feature model already represents `FeatureKind.HANDLE`, `FeatureKind.EXTERNAL_SECTION`, and all `CaptiveState` values, while `mechanical_capture` can remain the attachment-method family where the accepted retaining-action evidence supports it.

The missing production boundary was therefore not a new manufacturer-specific geometry type. It was the conservative separation between:

1. coarse executable installation geometry;
2. numeric dimensional fit when a complete manufacturer-backed fit envelope exists;
3. an installed-fit confirmation when the manufacturer requires a secure/snug fit that catalogue dimensions alone do not establish; and
4. a separate hard surface-profile prohibition when first-party evidence forbids installation on a known geometry profile.

A key distinction is that evidence saying an attachment installs on a `handle` does **not** establish `captive_state = non_captive` as a requirement. The architecture gap is the ability to support non-captive handles without requiring captivity; it is not evidence that captive/closed handles are prohibited. Captive state is therefore left unconstrained unless the manufacturer explicitly makes it part of eligibility.

## Evidence findings

### GRIPPS H01150 SnapLock

The current first-party GRIPPS product page identifies H01150 as a self-closing tool connector, states that it installs to a tool's handle or neck, and offers Small, Medium, Large and Extra Large variants. It does not publish a complete min/max tool-feature fit envelope on the reviewed product evidence.

Source:

- https://gripps.com/products/snaplock

The S/M/L/XL labels therefore remain product variant labels. They must not be converted into inferred tool-handle diameters, circumferences, or acceptance ranges.

The production implementation deliberately compiles only the common executable subset justified by the recurring architecture question:

```text
attachment_selection_class = handle_attachment

-> bind handle
   where:
     feature_kind = handle
```

No `captive_state` predicate is compiled. This means an explicitly non-captive handle can participate, while a captive or captive-state-unknown handle is not rejected merely because the source did not impose that condition.

PR #58 proves that behavior through the normal GRIPPS adapter and downstream eligibility path. The same vertical also preserves the evidence boundary around GRIPPS' separate `neck` wording: it does **not** automatically create an `EXTERNAL_SECTION` alternative. That additional composition should be added only when accepted evidence and a concrete vertical proof establish the correct normalized geometry and fit semantics.

The affirmative first-party tether-point wording may establish a ToolAttachment-provided tether-side interface role. It does not by itself establish a narrower interface type, so the vertically proven interface remains type-unknown unless separate evidence supports a concrete form.

### 3M DBI-SALA 1500028 Quick Spin Medium

The first-party 3M/Python Safety Quick Spin instructions state that Quick Spins slide onto a tool handle, should be used where they fit tightly, and must not be used if a snug fit cannot be secured. Installation instructs the user to select an adapter that properly fits the tool handle, push/twist it onto the tool with enough resistance to create a snug fit, and ensure it is firmly in place before use.

The same instructions list 1500028 as a 0.8 in / 2 cm diameter product with a 1 lb / 0.5 kg load rating. That nominal product diameter is not presented as a complete permitted tool-handle fit envelope.

Sources:

- https://multimedia.3m.com/mws/media/1300988O/ifu-5903829-python-quick-spins-a3-a3-size-instructions-manual.pdf
- https://multimedia.3m.com/mws/media/1446232O/3m-dbi-sala-fall-protection-for-tools-pocket-guide-aunz-english.pdf

The correct runtime consequence for fit is therefore a bounded installed-fit obligation rather than invented numeric eligibility:

```text
secure_attachment_fit_required = true

unknown -> requires_action
confirmed secure fit -> passed
secure fit cannot be achieved -> failed
```

The installation instructions also state that tool lanyards or attachment points must never be attached to a tapered surface. PR #58 models that statement separately as the hard, reusable profile constraint:

```text
prohibited_surface_profile = tapered
```

That prohibition is not evidence about nominal diameter, captivity, part identity, or secure-fit confirmation. It remains bound to the exact selected installation feature.

PR #58 also hardens 3M source identity before this evidence is accepted. The resolved `/p/d/v…/` detail record must remain the requested product record, the primary page heading must identify Quick Spin and the exact requested SKU, and explicit 3M product-number labels must resolve only to that SKU. Aggregate/multi-product pages and redirects to a different detail product fail closed rather than contributing product-local claims.

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

The same component/installation binding is retained by `ProductConstraintRuntimeState`. If secure-fit evidence is carried into a later complete recommendation run, `secure_attachment_fit_confirmed = true` resolves the retained obligation as passed while `false` hard-blocks that regenerated candidate; the observation does not become a catalogue-wide compatibility fact or leak to another component or installation feature.

PR #58 closes a binding gap exposed by the real Quick Spin vertical: every secure-fit evaluation outcome now preserves the selected `installation_feature_id` when one is available. This does not change the constraint's PRE_USE disposition; it ensures unresolved, requires-action, passed and failed outcomes all remain tied to the exact selected feature.

### Hard prohibited surface profile

`prohibited_surface_profile` is a reusable HARD product constraint for evidence-backed installation-profile prohibitions.

For a selected installation feature:

```text
no bound feature
  -> unresolved

bound feature with no surface_profile fact
  -> unresolved

surface_profile == prohibited value
  -> failed

known different surface_profile
  -> passed
```

For Quick Spin, the prohibited value is `tapered`. The evaluation retains the exact `installation_feature_id` so a known cylindrical handle can pass while a separate tapered handle fails without leaking the result between tool features.

Unknown profile does not become suitability. The rule also does not infer that every non-tapered profile is dimensionally suitable; secure fit remains a separate pre-use obligation where required.

## Dimensional boundary

The existing `external_section_attachment` compiler remains the numeric-fit precedent: it requires a complete source-local min/max diameter-fit envelope before it can compile a dimensional eligibility path.

PRs #57-#58 do not weaken that rule. In particular:

```text
S / M / L / XL label
!= tool-feature fit envelope

nominal attachment diameter
!= tool-feature fit envelope
```

If later first-party evidence supplies explicit tool-feature minimum/maximum dimensions for SnapLock, Quick Spin, or another product family, those bounds may feed the existing feature-dimension/predicate model. Until then, installed secure fit remains a runtime/pre-use fact rather than a fabricated catalogue dimension.

## Guardrails

PRs #57-#58 do not:

- infer a fit range from product size labels or nominal attachment diameter;
- infer that `handle` evidence means `non_captive` or that non-captive capability means captive handles are forbidden;
- promote a non-captive feature to captive;
- broaden `handle_attachment` to external sections or necks without evidence-backed composition;
- reuse `pre_use_attachment_test_required` for a different physical observation;
- fold Quick Spin's tapered-surface prohibition into secure-fit confirmation or part-type semantics;
- treat unknown surface profile as a pass;
- add GRIPPS-, 3M-, or SKU-specific downstream compatibility logic;
- change connection compatibility, capacity evaluation, contextual feasibility, ranking, or global exhaustion semantics; or
- rewrite any frozen portability answer key.

## Vertical proof and follow-on

PR #58 provides the intended cross-manufacturer vertical proof. GRIPPS H01150 SnapLock and 3M 1500028 Quick Spin both flow through the same neutral handle composition without product-pair logic. Quick Spin additionally exercises the independent secure-fit PRE_USE obligation and the independent hard tapered-profile prohibition. Neither vendor path manufactures a dimensional fit envelope.

The fresh V3 portability audit performed alongside that proof is documented in `portability-benchmark.md` and `snaplock-quickspin-portability-v3.md`. Its **0 A / 5 B / 3 C / 0 D** result leaves one recurring architecture seam: evidence-backed installation eligibility and concrete selected-anchor-feature binding for `AnchorAttachment` products. That seam should be addressed conservatively before another materially different portability sample decides whether portability can become a periodic stress test rather than the default architecture driver.

Operationally, the known NLG live-source drift should be repaired in a separate focused maintenance PR after #58 rather than being mixed into this vertical semantic slice.