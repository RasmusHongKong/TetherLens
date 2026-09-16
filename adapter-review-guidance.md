# Vendor Adapter Review and Generalization Guidance

## Purpose

Manufacturer adapters are intentionally allowed to contain source-format-specific acquisition and extraction logic. A defect first discovered in one adapter, however, may expose a reusable ingestion or evidence invariant rather than a vendor-only problem.

This document defines the review heuristic for deciding when a vendor-specific fix should remain local and when the reusable part should move into shared code.

## Review rule

When a defect is found in manufacturer-specific ingestion code, inspect equivalent paths in the other active adapters before applying a purely local fix.

Ask first:

> Is the thing that failed a vendor/source-format fact, or a TetherLens system invariant?

Prefer a shared implementation when the failure concerns a manufacturer-independent invariant such as:

- source provenance and final-host validation;
- exact product/variant identity binding;
- unit normalization or semantic equivalence;
- evidence reconciliation semantics;
- source-local grouping or scope boundaries;
- prevention of cross-record evidence leakage;
- fail-closed handling of ambiguous or incomplete evidence.

Keep logic vendor-specific when the generic layer cannot safely infer the manufacturer's source structure or wording, for example:

- what URL pattern identifies a manufacturer's exact product page;
- what SKU grammar marks rows in a particular catalogue;
- how a manufacturer labels connector roles or attachment mechanisms;
- where a specific website stores related-product relationships.

The preferred split is therefore:

```text
vendor-specific source interpretation
        ↓
shared safety / normalization / provenance / reconciliation invariant
        ↓
manufacturer-neutral claims and downstream semantics
```

Do not generalize merely for symmetry. A shared abstraction should correspond to a real semantic or safety invariant that can be stated independently of one manufacturer. If only the source grammar is shared superficially, keep the implementation local until another concrete case establishes a reusable boundary.

## Review procedure

For a vendor-adapter bug or review comment:

1. reproduce and fix the concrete failure conservatively;
2. inspect the equivalent code paths in other current adapters;
3. identify the smallest manufacturer-independent invariant, if one exists;
4. move only that invariant into shared code and keep source grammar/vendor interpretation local;
5. add a generic regression for the shared invariant when practical, plus a vendor regression for the concrete failure;
6. confirm that existing adapters retain their prior evidence priority and downstream semantics.

If no equivalent risk exists elsewhere and no safe generic invariant can be stated, a vendor-local fix is correct.

## Flattened multi-record evidence

When a source page or guide contains several product records, fields used for physical or recommendation-relevant claims must be scoped to the selected product record before parsing.

The shared `bounded_record_for_identifier()` helper expresses the generic boundary while the caller supplies the source-specific identifier grammar.

Its intended semantics are:

- the requested identifier must itself be recognized as a record marker;
- the selected record starts at the first occurrence of that identifier;
- repeated occurrences of the **same** selected identifier remain inside the selected record, because flattened pages commonly repeat a SKU in metadata, titles and headings; and
- the record ends at the first **different** recognized record marker.

Do not treat every later marker as a new record if it merely repeats the selected product identity. Conversely, do not search the whole page after exact-page identity verification: proving that the page is for SKU A does not prove that every phrase on the page belongs to SKU A rather than a related-product card.

## Current examples

PR #55 provides several examples of this boundary:

- Guardian/Ty-Flot final-host provenance exposed a system invariant, so manufacturer-source host validation moved into shared ingestion behavior.
- Ty-Flot rounded `lb` / `kg` capacity comparison exposed the same semantic issue previously handled in GRIPPS, so source-precision-aware mass equivalence moved into shared reconciliation while property-specific conflict policy remained with the caller.
- Ty-Flot flattened product-guide row bleed exposed a universal rule that one product's fields must not cross into the next record. The record-bounding helper is shared, while the `COLDSH...` row-marker grammar remains Ty-Flot-specific.
- Ty-Flot contraction wording itself remains vendor extraction evidence, while the resulting `contraction_capture` value is a manufacturer-neutral attachment-method primitive.

PR #66 reinforces the same split for Milwaukee product pages:

- the Milwaukee SKU grammar and explicit `tether-ready handle loop` / `tether-ready lanyard hole` wording remain adapter-specific;
- selected-product scoping uses the shared record-bounding invariant;
- repeated selected-SKU markers are tolerated generically; and
- a related-product SKU still terminates the selected record so tether-ready evidence cannot leak across products.

These examples should be used as review precedents, not as a requirement to refactor every adapter whenever one vendor needs a fix.
