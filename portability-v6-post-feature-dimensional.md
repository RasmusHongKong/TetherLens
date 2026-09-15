# Cross-vendor portability V6: post feature-dimensional compiler

## Purpose

V6 is the final fresh portability sample in the current architecture-discovery sequence. It asks whether, after closing the V5 generic feature-bound dimensional-eligibility seam, a materially different cross-vendor cohort still produces recurring missing recommendation primitives or whether the remaining work is primarily catalogue throughput.

Historical cohorts remain immutable at their original semantic revisions:

```text
V1  0 A / 5 B / 3 C / 0 D
V2  0 A / 6 B / 2 C / 0 D
V3  0 A / 5 B / 3 C / 0 D
V4  0 A / 4 B / 4 C / 0 D
V5  0 A / 6 B / 2 C / 0 D
```

V6 does not rewrite any of those answer keys.

## Freeze discipline

The semantic implementation under audit was frozen on branch `feature/toolattachment-dimensional-eligibility-v6` at:

```text
d5f1d67c4a1e36cd7b80edfb5423bf1f7cfca43a
```

The eight V6 identities were then committed **before classification** at:

```text
f3901d9636d198090e243ed9f9e74d558a2937f9
```

The frozen manifest is `benchmarks/cross_vendor_portability_v6.json`.

The sample is deliberately different from V5: three conventional tethers, two conventional ToolAttachments, one conventional AnchorAttachment and two system/kit-like commercial products across seven manufacturers. It avoids another dimensional ToolAttachment-heavy slice while retaining enough composition and proprietary-mechanism diversity to expose a real missing core semantic if one remains.

## Result

```text
V6  1 A / 7 B / 0 C / 0 D
```

This is the first portability cohort with an A case and the first with no C cases.

## Case review

### A — current production path already sufficient

**Hilti 2261970 — Tool tether 15lbs double carabiner**

The current registered Hilti adapter already extracts the relevant generic tether facts without a new family branch: rated capacity, double-carabiner endpoint topology and self-locking connector evidence. Unknown endpoint direction remains unknown. No adapter or recommendation-core change is required.

### B — catalogue / ingestion / evidence work only

**Dropsafe S017001101201 — Wire Tool Lanyard - Loop**

The mixed carabiner/loop topology, connector geometry, length and materials fit the current model. The first-party page currently contradicts itself on capacity: the title states 4.5 kg / 10 lb while application copy states 6.8 kg / 15 lb maximum dynamic load. That is an exact-product evidence conflict to preserve and reconcile through existing readiness policy, not a new capacity primitive.

**Guardian / Ty-Flot CC2072 — Coil Tool Tether**

Dual screw-gate carabiners, swivel attributes and relaxed/extended coil lengths fit current connector/tether semantics. The page similarly contains conflicting 5 lb and 10 lb load statements. The current Ty-Flot production adapter is scoped to Cold Shrink ToolAttachments, so the gap is Guardian tether ingestion plus ordinary evidence reconciliation.

**3M 1500009 — DBI-SALA D-Ring Attachment with Cord**

Manufacturer evidence describes a loop passed through a pre-drilled hole or closed handle and choked off, creating a D-ring attachment point with a 5 lb capacity. This is the already-established captive-through-opening OR captive-handle pattern plus a cinch/choke method and provided D-ring interface. The current 3M adapter is Quick-Spin-specific; broadening ingestion is sufficient.

**FallTech 5106A5 — choke-on cinch-loop Tool Attachment**

The product independently reuses captive-eye eligibility, cinch/choke installation, a provided carabiner interface and rated capacity. The current FallTech ToolAttachment path added for PR #64 is Battery-Boot-specific, so this is a second family branch in ingestion rather than a new eligibility primitive.

**Ergodyne Squids 3172 / 19172 — Hook & Loop Anchor Strap**

Existing post-PR #62 anchor semantics can conservatively compile its already-supported belt and rail installation subsets, feature-local published dimensions and D-ring tether interface. Broader `harness` / `other structure` wording must not be converted into invented feature kinds merely to maximize coverage. A safe supported subset is enough to show the recommendation core is not blocked; the remaining work is Ergodyne family ingestion/composition.

**GRIPPS H01088 — Adjustable Wrist Anchor With Tool Tether**

The manufacturer explicitly lists the kit contents as one H01067 Webbing Wrist Tether plus one H01085 Slip-On Wrist Anchor. The sellable SKU is therefore a commercial wrapper around separately catalogued load-path components, not evidence for a new runtime `Composite` component type. Supply-side ingestion should preserve/decompose the kit relationship and let ordinary tether + AnchorAttachment candidate composition reason over the contained products.

**Guardian / Ty-Flot QSS-R — Quick-Switch Link and Dock Pack**

The manufacturer describes one dock plus one tool-tether link, a Quick-Switch interface paired with a standard screw-gate end, a 6 lb limit and a transfer workflow that maintains 100% tie-off. The proprietary transfer behavior is important evidence but does not need a new baseline recommendation primitive to represent load-path interfaces or a declared link/dock relationship. Preserve it as product/connection behavior and defer stateful handoff reasoning until a demand-side requirement needs it.

## Why the composite/system cases are B rather than C

The portability programme is intended to discover missing reusable physical/evidence/reasoning primitives, not to force every catalogue marketing package or product behavior into the runtime ontology immediately.

Two boundaries matter:

1. A sellable kit made from separately identifiable recommendation components can be represented as catalogue composition/related-product evidence. The kit wrapper does not itself need to become a new load-path component.
2. A novel operational feature does not require a new reasoning primitive until it affects a decision the MVP must make. QSS-R's continuous-tie-off transfer claim should be retained faithfully, but baseline component viability does not currently ask the engine to simulate a handoff state machine.

If a later field workflow asks, for example, “which system permits a tool to be passed between workers without ever breaking tie-off?”, that demand-side requirement may justify a bounded transfer-state capability. V6 should not pre-build it speculatively.

## Decision

V6 supports a full development pivot.

The portability sequence has now moved from recurring C pressure to a materially different **1 A / 7 B / 0 C / 0 D** cohort after the V5 seam was closed. The remaining supply-side gaps are overwhelmingly:

- manufacturer/source acquisition;
- new product-family extraction;
- exact identity/variant binding;
- evidence conflict reconciliation;
- catalogue assembly/relationship decomposition; and
- breadth/throughput of recommendation-ready records.

These are important, but continuing to sample fresh products as the primary development loop is now likely to produce diminishing architectural returns.

Portability should therefore become a **periodic stress/regression audit**, run after meaningful core changes or after enough catalogue breadth has accumulated to justify another blind sample.

The primary MVP workstream should shift to:

```text
catalogue throughput
+
demand-side MVP
```

with emphasis on:

- tool recognition / resolution from field input;
- efficient acquisition of the tool/configuration facts required for recommendation;
- user confirmation when identity/configuration remains ambiguous;
- targeted capture of only the context needed by current hard/contextual rules;
- orchestration from resolved field tool -> candidate generation/evaluation -> selection;
- clear field-facing recommendation/explanation output; and
- graceful fallback when no catalogue-ready recommendation is possible.

The supply-side core should still be extended when demand-side work or a periodic portability audit exposes a **recurring** missing primitive. It should no longer be expanded merely because a new catalogue SKU has a novel marketing description or optional behavior.
