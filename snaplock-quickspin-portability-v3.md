# SnapLock / Quick Spin vertical and portability V3

## Scope

This slice follows PR #57. The historical portability cohorts remain immutable observations of the core at their original freeze points:

- V1 after PR #51: **0 A / 5 B / 3 C / 0 D**.
- V2 against post-PR #55 `main`: **0 A / 6 B / 2 C / 0 D**.

PR #57 resolved the recurring V2 handle/fit boundary with `handle_attachment`: installation requires `feature_kind = handle`, but it does not constrain `captive_state` and it does not infer dimensions. `secure_attachment_fit_required` is a distinct pre-use obligation and does not satisfy or replace `pre_use_attachment_test_required`.

This follow-on vertically checks that boundary against the two V2 C products and adds only evidence-backed semantics that were still missing.

## GRIPPS H01150 SnapLock

Accepted first-party wording establishes that SnapLock:

- is a self-closing tool connector;
- installs to a tool **handle or neck**;
- provides a tethering connection point;
- is offered in S/M/L/XL variants; and
- carries a stated 6.8 kg / 15 lb maximum load.

The executable subset is deliberately narrower than the prose:

- the explicit **handle** alternative compiles to `attachment_selection_class = handle_attachment`;
- self-closing retention maps to `attachment_method_code = mechanical_capture`;
- handle captivity remains unconstrained, so captive, non-captive and unknown-captivity handles are not excluded merely by this evidence;
- `neck` is **not** widened to `external_section_attachment`; no reviewed evidence yet establishes the normalized geometry/feature semantics needed to do that safely;
- S/M/L/XL labels do not become dimensions or a fit envelope; and
- the product's tethering connection point is retained as a ToolAttachment-provided interface without inventing a ring, carabiner or other interface form.

SnapLock therefore validates the PR #57 handle semantic without requiring another core primitive. Its current recommendation-readiness can still be limited by unresolved downstream interface-form evidence; that is an evidence gap, not permission to infer geometry.

## 3M DBI-SALA 1500028 Quick Spin

The first-party product page and Quick Spin family instructions establish separate facts:

- Quick Spin slides onto a tool handle;
- the 1500028 variant is described with a nominal 2 cm / 0.80 in size and 0.5 kg / 1 lb capacity;
- the installed Quick Spin must achieve a snug/firm fit before use; and
- tool lanyards or attachment points must never be attached to a **tapered surface**.

The normalized model keeps those facts separate:

- handle installation uses `handle_attachment` plus `mechanical_capture`;
- nominal attachment diameter is **not** promoted to minimum/maximum tool-handle geometry;
- snug/firm fit remains `secure_attachment_fit_required`, a pre-use obligation;
- the tapered-surface prohibition becomes the reusable hard constraint `prohibited_surface_profile = tapered` with operator `PROHIBITS`; and
- the hard profile check is bound to the same concrete installation feature selected by attachment eligibility.

Runtime behavior is intentionally fail-closed:

- a selected feature explicitly known to be tapered fails the hard constraint;
- a selected feature with a known different surface profile passes this constraint;
- a selected feature whose surface profile is unknown remains unresolved; and
- confirming secure fit cannot override a tapered-surface failure.

The first-party family manual is joined through the ordinary manufacturer source graph before constraint resolution. The `multimedia.3m.com` document remains inside the 3M first-party provenance boundary.

## Portability V3

After the SnapLock / Quick Spin vertical, a materially different eight-product cohort was frozen separately in `benchmarks/cross_vendor_portability_v3.json`. It deliberately shifts away from the previous handle-fit cluster toward unfamiliar tether constructions and anchor-side installation.

Result: **0 A / 5 B / 3 C / 0 D**.

The five B cases are tether products whose observed facts fit existing neutral endpoint, connector, length, capacity and tether-form semantics. They represent catalogue acquisition/extraction work rather than pressure for new recommendation rules.

The three C cases are independent AnchorAttachment products from Milwaukee, FallTech and Ergodyne. They converge on one downstream seam: the current core can represent an anchor component and the tether-side interface it provides, while candidate generation accepts an already-resolved `AnchorPathOption`; it does not yet provide an evidence-backed installation-eligibility and concrete anchor-feature binding layer analogous to ToolAttachment installation.

The recurrence matters more than the narrow 5/8 A/B majority. V3 therefore does **not** meet the stated condition for declaring semantic saturation and moving the development centre of gravity entirely to catalogue throughput and the demand-side MVP.

## Next implementation boundary

The next architecture slice should be one conservative, manufacturer-neutral AnchorAttachment installation/binding seam. It should prove that a selected primary anchor feature is eligible for a particular AnchorAttachment before constructing an `AnchorPathOption`, while preserving evidence-specific distinctions such as belt, beam/rail, open-ended/refastenable structure and any explicit dimensional bound.

It should not introduce vendor/SKU pair rules, infer generic anchor compatibility from marketing category names, or disturb the existing tether-to-anchor interface compatibility evaluator.

In parallel, the V3 B tether cases are appropriate catalogue-throughput work. If the anchor installation slice resolves the recurring C cluster and a later stress sample does not expose another comparable recurring C/D seam, portability can then become a periodic regression exercise and the main development focus can shift toward catalogue scale and the demand-side MVP.
