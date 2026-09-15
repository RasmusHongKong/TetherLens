# Feature-bound ToolAttachment dimensional eligibility

## Purpose

PR #64 closes the reusable compiler seam exposed independently by the frozen V5 FallTech 5401A1 Battery Boot and Ergodyne Squids 3745 / 19747 Tool Grip cases.

The runtime model did not need a new geometry system. `ToolInterfaceFeature` already carries feature-local dimensions and `FeaturePredicate` already evaluates `dimension:<code>` predicates against the exact bound feature. The missing layer was production claim resolution: accepted manufacturer-backed dimensional conditions could not be composed generically onto ordinary ToolAttachment eligibility paths.

The governing rule is:

> **An explicit accepted ToolAttachment fit dimension may become a runtime predicate only when its target feature kind, comparison direction, value/unit, evidence source and feature subject are explicit. Every predicate in the resulting path remains bound to one concrete `ToolInterfaceFeature`.**

## Claim shape

The generic production claim vocabulary is:

```text
attachment_selection_class
attachment_eligibility.feature_kind
attachment_eligibility.dimension.<dimension_code>
```

Dimensional claims are `declared_constraint` claims and must carry one of the ordered operators already understood by runtime predicates:

```text
eq
lt
lte
gt
gte
```

Examples:

```text
subject = tool_side_fit
attachment_eligibility.feature_kind = handle
attachment_eligibility.dimension.section_diameter >= 1.0 in
attachment_eligibility.dimension.section_diameter <= 1.28 in
attachment_eligibility.dimension.section_height <= 4.5 in
```

and:

```text
subject = tool_side_fit
attachment_eligibility.feature_kind = external_section
attachment_eligibility.dimension.section_length <= 3.5 in
attachment_eligibility.dimension.section_width <= 2.75 in
attachment_eligibility.dimension.section_height <= 2.5 in
```

The dimension code remains manufacturer-neutral. Product, manufacturer and SKU identity are not part of the compiled predicate.

## Compilation boundary

`resolve_attachment_eligibility()` still starts from an established attachment selection class. That selection class creates the bounded eligibility path or paths. Explicit feature-bound fit profiles are then composed onto the path whose `feature_kind` matches the fit profile.

The compiler does not create a new feature path merely because a dimension was published. A fit profile whose feature kind does not match an established attachment selection path fails closed.

This preserves the separation between:

- evidence that identifies the physical feature on which the attachment may be installed; and
- evidence that further constrains the dimensions of that same feature.

## Source and subject guardrails

A dimensional fit profile is one `physical_interface` subject.

For every evidence source that contributes dimensions to that subject:

1. the same source must state the normalized `attachment_eligibility.feature_kind`;
2. every dimensional condition must carry an explicit ordered comparison operator;
3. values are normalized to millimetres before equivalent profiles are compared; and
4. that source must independently establish the same complete normalized predicate set as any other accepted source on the subject.

This permits equivalent source representations such as inches versus millimetres. It does **not** permit TetherLens to manufacture an envelope by taking a lower bound from one source and an upper bound from another.

The compiler also rejects more than one accepted fit subject for the same feature kind. Facts from separate physical subjects must not be merged merely because both subjects happen to describe handles, external sections or another shared kind.

Contradictory exact values, inverted lower/upper bounds and exact values that conflict with strict/inclusive bounds fail closed.

## Same-feature runtime semantics

Compilation produces ordinary runtime predicates such as:

```text
feature_kind = handle
dimension:section_diameter >= 25.4 mm
dimension:section_diameter <= 32.512 mm
dimension:section_height <= 114.3 mm
```

They are appended to one `EligibilityPath` and evaluated by the existing runtime matcher.

Therefore all predicates must be true on one concrete feature instance. TetherLens may not satisfy diameter from one handle and height from another. This is the same feature-binding invariant used by non-dimensional eligibility.

No connection-compatibility, candidate-generation identity, hard-evaluation, ranking, selection or exhaustion semantics change in this slice.

## Existing external-section diameter guardrail

The pre-existing `external_section_attachment` path has a deliberately strict legacy evidence contract:

```text
interface.dimension.min_diameter
interface.dimension.max_diameter
```

Those claims must remain one complete source-local envelope on one physical-interface subject. Missing, split-source, multiply-scoped or conflicting envelopes fail closed.

PR #64 does not weaken that contract.

If **any** legacy external-section min/max-diameter claim is present, the existing diameter-envelope compiler runs first. A partial legacy envelope therefore still fails rather than being bypassed by a new generic dimensional claim.

A generic external-section fit profile is available only as an additional evidence shape when no legacy min/max-diameter claims are present. This is what permits the FallTech 5401A1 three-axis maximum geometry without turning its length/width/height statement into a fake diameter envelope.

## V5 vertical proofs

### FallTech 5401A1 Battery Boot

The exact first-party product page establishes a maximum battery geometry of:

```text
3.5 in length
2.75 in width
2.5 in height
```

The adapter emits one `external_section` fit subject with three `lte` dimensions. Resolution compiles those dimensions onto one external-section eligibility path. The vertical test proves both:

- a single feature inside all three limits is eligible; and
- two different external-section features cannot donate different passing dimensions to manufacture eligibility.

The product's steel D-ring remains a separate ToolAttachment-provided tether interface.

### Ergodyne Squids 3745 / item 19747 Tool Grip

The exact first-party product page establishes a handle envelope of:

```text
section diameter >= 1.0 in
section diameter <= 1.28 in
section height <= 4.5 in
```

Those conditions compile onto one handle path and remain bound to one selected handle.

A current family instruction document states a different maximum height, so the vertical deliberately uses the exact product-page evidence that supported the frozen V5 classification. The compiler does not join or silently reconcile the two sources.

## Regression coverage

Focused tests cover:

- equivalent source-local profiles expressed in different units;
- rejection of split-source bounds;
- rejection of dimensions without an explicit comparison direction;
- rejection of multiple fit subjects for one feature kind;
- rejection of contradictory/inverted dimensional conditions;
- preservation of the legacy external-section partial-envelope failure;
- full FallTech 5401A1 adapter -> claim -> resolution -> same-feature runtime evaluation; and
- full Ergodyne 19747 adapter -> claim -> resolution -> same-feature runtime evaluation.

The existing `tests/test_external_section_fit_envelope.py` suite remains the regression authority for the legacy diameter-specific contract.

## Deliberate non-goals

This slice does not:

- infer numeric geometry from S/M/L/XL or other nominal size labels;
- infer numeric limits from `small`, `adjustable`, `all sizes` or similar qualitative wording;
- create battery-, screwdriver-, FallTech- or Ergodyne-specific runtime rules;
- merge dimensions across different physical feature subjects;
- synthesize a fit envelope across incomplete evidence sources;
- redefine attachment selection classes;
- change tether-to-interface connection compatibility;
- change ranking or selection; or
- change recommendation exhaustion semantics.
