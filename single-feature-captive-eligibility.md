# Single-feature captive ToolAttachment eligibility

## Status

Reusable production composition for ToolAttachment manufacturer evidence that authorizes exactly one captive tool-feature family, while preserving the existing captive-handle-OR-captive-through-opening behavior.

This document complements `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, and the frozen cross-vendor audit in `portability-benchmark.md`.

## Problem

The runtime `AttachmentEligibility` model already represents bounded OR-of-AND feature paths and binds every predicate in one path to the same concrete `ToolInterfaceFeature`.

Before PR #53, the production claim compiler exposed only:

```text
attachment_selection_class = captive_feature_attachment
```

which compiled to:

```text
captive handle
OR
captive through-opening
```

That is correct for existing NLG evidence such as the 101363-style combined scope, but it cannot faithfully represent manufacturer evidence that authorizes only one of those alternatives. Reusing the broader class for a handle-only or captive-eye-only product would widen eligibility beyond the accepted evidence.

The first frozen cross-vendor portability cohort exposed this same gap independently for a handle-only ToolAttachment family and a captive-eye-only ToolAttachment family. The reusable missing concept is therefore selection composition over existing anatomy primitives, not a manufacturer-specific feature type or product exception.

## Production selection classes

PR #53 keeps `attachment_selection_class` as the production compilation seam and adds two narrower manufacturer-neutral values:

```text
captive_handle_attachment
captive_through_opening_attachment
captive_feature_attachment
```

They compile as follows:

```text
captive_handle_attachment
  -> one path
     feature_kind = handle
     captive_state = captive

captive_through_opening_attachment
  -> one path
     feature_kind = through_opening
     captive_state = captive

captive_feature_attachment
  -> path A
     feature_kind = handle
     captive_state = captive

     OR

     path B
     feature_kind = through_opening
     captive_state = captive
```

All three use the same feature-local path builder. There is no separate compatibility or hard-evaluation implementation per class.

## Evidence boundary

The compiler consumes accepted/reconciled claims; it does not decide what manufacturer wording is sufficient to emit a selection class.

An adapter may emit only the narrowest class actually supported by its accepted evidence:

- explicit captive-handle-only evidence may authorize `captive_handle_attachment`;
- explicit captive-eye / captive-through-opening-only evidence may authorize `captive_through_opening_attachment`;
- evidence that genuinely establishes either a captive handle or a captive through-opening may authorize the existing `captive_feature_attachment` alternative.

Do not infer the missing alternative from product family, attachment method, geometry similarity, catalogue convention, or the existence of another compiler class.

In particular:

```text
handle-only evidence
!= handle OR opening

opening-only evidence
!= handle OR opening
```

The existing NLG combined evidence recognizer and `captive_feature_attachment` output are intentionally unchanged by PR #53.

## Feature-instance binding

Every compiled path still binds both predicates to one concrete tool feature:

```text
bind feature
where:
  feature.feature_kind = ...
  feature.captive_state = captive
```

A captive state from one feature cannot satisfy the geometry predicate of another feature. Unknown captive state remains unresolved rather than being treated as captive.

The narrower classes therefore change only which alternative paths are authorized; they do not change `AttachmentEligibility` evaluation semantics.

## Conflict handling

Accepted selection-class evidence must be reconciled before compilation.

If conflicting accepted values reach `resolve_attachment_eligibility()`, the existing single-claim conflict guard raises `ClaimResolutionError`. The resolver does not union two narrower claims into a broader runtime rule.

For example, simultaneously passing accepted:

```text
captive_handle_attachment
captive_through_opening_attachment
```

must not silently become:

```text
captive_feature_attachment
```

because logical union would manufacture an evidence relationship that was not itself reconciled or authorized.

Duplicate accepted evidence for the same selection-class value is harmless and compiles only once.

Unsupported selection classes continue to fail closed.

## Downstream invariants

PR #53 does not change:

- the `AttachmentEligibility`, `EligibilityPath`, `FeaturePredicate`, or `ToolInterfaceFeature` runtime models;
- feature-instance binding or unresolved/ineligible/eligible evaluation semantics;
- candidate generation;
- selected installation-feature identity/provenance;
- normalized product or installation constraints;
- ToolAttachment-provided tether-interface semantics;
- connection compatibility;
- hard candidate evaluation;
- contextual feasibility or ranking;
- global recommendation exhaustion; or
- session-local verification semantics.

No manufacturer, tool, attachment, or SKU identity participates in the compiler mapping.

## Portability significance

The frozen `cross_vendor_portability_v1` artifact remains a historical architecture audit of the core after PR #51. Its original classifications are not rewritten after the fact.

PR #53 resolves the recurring single-feature captive composition gap that caused two products in that frozen cohort to be class C. Future vendor adapters can now target the appropriate narrow selection class while reusing unchanged downstream semantics.

The next portability proof should therefore be vertical rather than another core change: ingest representative B-class cross-vendor products into the existing model and verify that no compatibility, candidate-generation, hard-evaluation or ranking rule needs to change.
