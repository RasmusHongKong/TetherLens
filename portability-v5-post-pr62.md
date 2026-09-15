# Post-PR #62 portability V5

## Status

V5 is the fifth frozen cross-vendor portability audit. It is evaluated against merged `main` commit `87f3c277f108e38dc3ec7d070e38c94868d355a6` through PR #62.

The eight identities were committed before classification in sample-freeze commit `e7c03c942b3fb2456033f7d5d3e15ee3cfee09d7`. The completed answer key is retained in `benchmarks/cross_vendor_portability_v5.json` and must not be rewritten after later work closes any gap it exposes.

Historical cohorts remain immutable:

```text
V1  0 A / 5 B / 3 C / 0 D
V2  0 A / 6 B / 2 C / 0 D
V3  0 A / 5 B / 3 C / 0 D
V4  0 A / 4 B / 4 C / 0 D
```

## Sample design

V5 deliberately moves away from the AnchorAttachment region stressed by V3 and V4. It contains four fresh ToolAttachments and four fresh tethers across seven manufacturers, with no AnchorAttachment products and no wrist/bucket-lip cases.

It excludes every V1-V4 identity and the recent PR #58/#60/#61/#62 vertical-proof identities. The cohort therefore tests a materially different part of the catalogue rather than asking whether the just-added anchor vocabulary works on more close variants.

The frozen products are:

- FallTech 5401A1 Battery Boot Tool Attachment;
- Ergodyne Squids 3745 / item 19747 Tool Grip and Tether Attachment Point;
- Safewaze SW404 35 lb Medium Duty Cinch Tool Attachment;
- GRIPPS H01006-5 Tool Catch;
- Milwaukee 48-22-8815 15 lb Locking Tool Lanyard;
- GRIPPS H01072 Bungee Tether;
- 3M DBI-SALA 1500047 Hook2Loop Bungee Tool Tether; and
- Guardian 7100001 Arc Flash Tool Tether.

## Frozen result

```text
A facts_only               0
B vendor_ingestion_only    6
C new_reusable_primitive   2
D sku_specific_exception   0
```

V5 is strongly A/B-majority by count and again produces no D case. The six B products reinforce the catalogue-throughput signal: their relevant endpoint, connector, cinch/wrap, required-pairing, capacity, length and evidence concepts already fit the normalized recommendation core, while their current manufacturer adapters are absent or deliberately narrow.

V5 nevertheless does **not** justify a full pivot yet because the two C products independently expose the same small reusable compiler seam.

## Recurring C seam: generic feature-bound dimensional eligibility

The runtime ToolAttachment eligibility model is already dimension-generic:

```text
ToolInterfaceFeature
  dimensions_mm[dimension_code]

EligibilityPath
  -> FeaturePredicate("dimension:<dimension_code>", operator, value)
```

Those predicates remain scoped to the exact feature bound by the eligibility path, so the runtime model can evaluate several geometry constraints against one concrete handle or external section without stitching dimensions from unrelated features.

The production claim-resolution compiler is narrower. At the V5 freeze:

- `handle_attachment` compiles only `feature_kind = handle` and intentionally carries no inferred numeric fit; and
- `external_section_attachment` has one special numeric path requiring a complete source-local minimum/maximum **diameter** envelope.

That conservative boundary was correct for earlier evidence where nominal product size or qualitative snug-fit wording did not establish a real numeric tool-feature envelope. V5 now supplies explicit manufacturer dimensions that must not be discarded.

### FallTech 5401A1

The Battery Boot publishes an explicit maximum battery geometry in length, width and height. The existing runtime predicate model can represent those dimensions on one resolved external tool/configuration feature, but the production eligibility compiler cannot currently compose that three-axis envelope. Treating the product as geometry-only would authorize batteries outside the manufacturer's published bounds; forcing it through the diameter-only external-section compiler would misrepresent the evidence.

The reusable need is not a `battery_boot` compatibility rule. It is the ability to compile accepted source-backed dimensional bounds onto the exact feature selected by an ordinary ToolAttachment eligibility path.

### Ergodyne Squids 3745 / 19747

The Tool Grip publishes an explicit handle diameter range and handle height. The current `handle_attachment` path deliberately accepts a handle without inventing dimensions, but this product has real numeric evidence that should constrain the selected handle.

Again, the missing capability is not a screwdriver/nut-driver or Ergodyne rule. It is the same feature-bound dimensional composition needed by FallTech: accepted diameter/height predicates should remain attached to the one concrete handle used by the installation path.

## Smallest next semantic slice

Close only the generic feature-bound dimensional-eligibility seam.

The implementation should:

1. preserve the existing `ToolInterfaceFeature` and `FeaturePredicate` runtime model rather than introducing product-family geometry classes;
2. compile only explicit accepted dimensional conditions supported by source evidence;
3. keep every dimensional predicate bound to the exact selected feature and source scope;
4. support the comparison direction actually established by the manufacturer, including bounded ranges or one-sided maxima/minima where valid;
5. fail closed on incomplete, conflicting or cross-subject evidence rather than synthesizing an envelope;
6. leave nominal size labels and qualitative fit wording non-numeric unless the source states an actual dimensional condition; and
7. avoid any change to tether-to-anchor compatibility, candidate ranking, selection or global exhaustion.

The current diameter-specific `external_section_attachment` behavior should remain a regression case, not be weakened to obtain generality.

## What V5 does not justify

V5 does not justify:

- battery-, screwdriver-, FallTech- or Ergodyne-specific downstream branches;
- a general positive environmental-suitability model from the single Guardian arc-flash example;
- converting tool-category examples into hard eligibility whitelists;
- broadening endpoint or connector compatibility;
- changing ranking or exhaustion; or
- rewriting any earlier portability cohort.

The Guardian arc-flash product is intentionally B. Its positive ASTM F887 capability should be retained as manufacturer evidence, but the current absence of a positive environmental preference primitive does not block baseline participation. If future demand-side scenarios repeatedly need positive arc-flash suitability to distinguish otherwise viable candidates, that can be audited separately from this V5 seam.

## Development-centre decision

V5 is close to semantic saturation but does not cross the pivot threshold yet. Six of eight products are ordinary catalogue/onboarding work, while two products repeat one narrow reusable gap across different manufacturers and different tool geometries.

Therefore:

```text
next semantic work
  -> generic feature-bound dimensional eligibility only
  -> one cross-manufacturer vertical proof
  -> another materially different fresh portability audit
```

If that next audit is predominantly A/B with no comparable recurring C/D pressure, portability should become a periodic stress/regression programme rather than the default development driver. The development centre should then move to catalogue throughput and the demand-side MVP: tool recognition, efficient tool/configuration fact acquisition, targeted context capture and the field recommendation workflow.
