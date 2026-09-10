# Mass Claim Reconciliation

## Purpose

TetherLens normalizes mass-valued claims to kilograms for downstream reasoning, but source declarations are often rounded at different precision and may use different units. Exact equality between normalized floating-point values is therefore not a safe definition of evidentiary disagreement.

This document defines the reusable semantic-equivalence rule for mass declarations. It applies to mass-valued evidence across tools, batteries, tethers, ToolAttachments, AnchorAttachments, containers and other catalogue subjects. It does **not** decide which evidence sources are comparable or which disagreements are recommendation-blocking.

## Separation of responsibilities

Mass reconciliation has two layers:

1. **Semantic mass equivalence** — a shared unit/rounding calculation determines whether several source declarations could describe the same underlying physical value.
2. **Evidence policy** — the claim/property-specific caller determines which claims should be compared after product identity, evidence method and evidence priority have been established, and whether a material disagreement is blocking.

The shared calculation must not become a global rule that every mass claim from every source must agree. For example, manufacturer and qualified-secondary evidence may have different priority for a physical tool mass, while a manufacturer-rated load capacity has a different evidence requirement. Those policy decisions remain outside the generic rounding helper.

## Source-declared precision

For a declaration such as:

```text
10 lb
```

TetherLens interprets the displayed integer precision as a rounding interval of 9.5–10.5 lb before converting the interval to kilograms.

For:

```text
4.53 kg
```

the displayed precision implies 4.525–4.535 kg.

Two declarations semantically agree when their canonical kilogram intervals overlap. This allows differently rounded metric/customary statements such as `10 lb` and `4.53 kg` to corroborate rather than becoming a false evidence conflict.

The same rule explains why a rounded `36.3 kg` declaration can correspond to `80 lb`, while materially different declarations such as `36.3 kg` and `36.9 kg` remain conflicting. The existing GRIPPS H01079 first-party capacity conflict therefore remains unresolved.

## Fail-closed boundary

The interval is derived only from the source declaration retained in `CandidateClaim.raw_value`. If the original declaration/precision cannot be recovered, the normalized mass value is treated as exact rather than inventing an arbitrary tolerance.

The generic helper also does not:

- choose a preferred source;
- reconcile different product identities or variants;
- downgrade or upgrade evidence methods;
- override evidence-priority rules;
- average conflicting values;
- choose the more conservative value automatically; or
- relax a hard load-capacity threshold.

A material disagreement among the highest applicable accepted evidence remains an evidence conflict until a defensible property-specific reconciliation rule resolves it.

## Implementation

The reusable implementation lives in `src/tetherlens_ingest/reconciliation.py`:

- `mass_claim_rounding_interval_kg()` derives the canonical interval implied by one source declaration;
- `mass_claims_semantically_agree()` tests whether all supplied declarations have a common plausible value.

Adapters or future shared evidence-policy code may call this helper after selecting the exact claims whose evidence identity and priority make them comparable.

PR #55 migrates the existing GRIPPS capacity reconciliation and the new Ty-Flot capacity reconciliation to this shared primitive. This removes duplicated vendor-specific rounding logic without changing either product's evidence policy.
