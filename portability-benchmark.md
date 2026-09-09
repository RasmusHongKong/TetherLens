# Cross-vendor portability benchmark

## Purpose

This benchmark tests whether the TetherLens knowledge and recommendation model built through PR #51 is portable beyond the NLG-heavy development cohort.

The benchmark intentionally freezes the core at merged `main` commit `7e9785456e3f52511f017fdc0a3f19afc1c652c7` and inspects an unseen cross-vendor cohort before adding new production semantics for those products.

The question is not whether every manufacturer can be ingested without manufacturer-specific code. Different catalogues will continue to require different acquisition and extraction adapters. The more important question is:

> Once trustworthy product facts have been normalized, how often can an unfamiliar product participate through the existing domain model, compatibility primitives, candidate generation, hard evaluation and selection rules without changing the core?

That distinction matters because vendor-specific parsing is expected; vendor- or SKU-specific recommendation semantics should remain exceptional.

## Catalogue asymmetry and leverage

TetherLens operates in an asymmetric product universe. The number of individual tools and tool models is very large, while the number of commercially relevant tethering components and recurring tethering mechanisms is much smaller.

That asymmetry should influence the scaling strategy.

The system should not try to maintain a matrix of every tool model against every tether SKU. Instead, it should invest deeply enough in the smaller tethering-product universe to describe reusable physical and evidence primitives, then allow a much larger tool catalogue to participate by exposing the tool features those primitives require.

Conceptually:

```text
large tool catalogue
  -> reusable tool features / operational mass / configuration facts

smaller tethering-product catalogue
  -> reusable attachment, connector, capacity, length and constraint primitives

existing rules
  -> candidate configurations and recommendations
```

This means detailed tether-product modelling can have high leverage when one normalized mechanism applies to many tools. The goal is not to avoid depth; it is to avoid spending disproportionate effort on narrow manufacturer wording or branded mechanisms unless they reveal a reusable physical/evidence concept or close a recurring decision gap.

A useful rule of thumb is:

> Prefer work whose value scales with the number of tools or configurations it can unlock, not merely with the number of catalogue fields it can extract from one tether SKU.

## Classification model

Each cohort product is assigned one portability class based on the smallest change required for correct participation in the current architecture.

| Class | Name | Meaning |
|---|---|---|
| A | `facts_only` | Existing acquisition/normalization paths and existing core semantics are sufficient; the product mainly requires adding facts/configuration. |
| B | `vendor_ingestion_only` | The current domain/recommendation core is sufficient, but a new manufacturer-specific acquisition or extraction path is required. |
| C | `new_reusable_primitive` | The product exposes a physical, evidence or reasoning concept that the current core cannot faithfully represent and that appears reusable beyond one SKU. |
| D | `sku_specific_exception` | Correct support appears to require product-specific compatibility/recommendation logic rather than a reusable primitive. |

Class B is not considered an architectural failure. A manufacturer adapter that emits vendor-neutral facts is expected supply-side work. Class D is the main warning signal.

Evidence availability and evidence reconciliation are also kept separate from portability. A product can fit the current core while remaining recommendation-blocked because the public source does not establish endpoint assignment, loop engagement method, geometry or another mandatory fact, or because first-party evidence conflicts internally. Missing or conflicting evidence must not be turned into a new rule merely to make the cohort pass.

Two V1 products make that distinction concrete. The current GRIPPS H01079 page uses both `36.3 kg / 80 lb` and `36.9 kg / 81 lb` load wording, while the current Ty-Flot CC2956WR14LRD page describes a `5 lb` rating but also lists `Max Tool Weight 2 lb`. Both remain B-class because the current core already represents rated capacity; neither disputed value should be considered recommendation-ready until the evidence is reconciled.

## V1 cohort

`benchmarks/cross_vendor_portability_v1.json` contains eight products: two each from GRIPPS, FallTech, Ty-Flot and Dropsafe. NLG is deliberately absent.

The cohort was selected for physical diversity rather than statistical catalogue representation. It covers:

- symmetric-looking and explicitly directional dual-carabiner tethers;
- carabiner + loop tether topology;
- double/triple-action and automatic-locking connector facts;
- relaxed/extended tether lengths;
- choke/cinch ToolAttachments;
- captive-handle and captive-eye / through-opening eligibility;
- D-ring target interfaces;
- coil and bungee forms; and
- one deliberately unfamiliar retention mechanism: Ty-Flot Cold Shrink.

The primary first-party/current product sources are retained directly in the benchmark manifest. The audit records only public facts needed to judge model fit; it is not an ingestion golden and should not be fed into production extraction.

## Initial result

The reviewed architecture audit produces:

```text
A facts_only               0
B vendor_ingestion_only    5
C new_reusable_primitive   3
D sku_specific_exception   0
```

The absence of class A is expected in this first cross-vendor slice because none of these manufacturers yet has a normal production adapter in the current repository. Five products appear to fit the existing normalized core without a new compatibility, candidate-generation, ranking or SKU-pair rule.

The review also exposed a useful recurring class C gap that the initial audit missed. The runtime `AttachmentEligibility` model can represent arbitrary feature-bound paths, but the production `resolve_attachment_eligibility()` compiler currently supports only one `captive_feature_attachment` selection class, which always expands to:

```text
captive handle
OR
captive through-opening
```

That is correct for NLG evidence that explicitly permits both alternatives, but it cannot faithfully compile a manufacturer statement that authorizes only one of them.

This affects two different manufacturers in the frozen cohort:

- **GRIPPS H01055 Tool Hitch** establishes closed-handle use. Treating it as the current combined class would unevidentially authorize through-openings.
- **FallTech 5318A10** establishes captive-eye attachment points. Treating it as the current combined class would unevidentially authorize handles.

Both therefore move from B to C. They expose the same reusable need: feature-scoped attachment eligibility must be able to express a single captive handle path or a single captive through-opening path without automatically widening to the other alternative. The underlying feature vocabulary, `cinch` mechanism, capacity and provided tether-interface concepts already exist; the missing piece is executable eligibility composition.

Representative B-class reuse findings still include:

- the GRIPPS H01079 directional heavy-duty tether maps to existing concrete endpoints plus `tool_side` / `anchor_side` roles rather than requiring symmetric-end inference;
- FallTech 5027B maps to the existing mixed carabiner/cinch-loop tether topology and bounded cinch-loop connection family;
- Ty-Flot CC2956WR14LRD fits existing mixed endpoint, swivel/mechanism, capacity and min/max length concepts, while its loop engagement must remain evidence-bound rather than assumed from the word `loop`;
- both Dropsafe tether examples fit the existing carabiner/loop, action-count, locking, geometry, capacity and length vocabulary. The twin-carabiner product must remain assignment-unknown unless accepted evidence separately proves direction or reversibility.

The third class C case is Ty-Flot `COLDSH41X35`. Its diameter-fit, capacity and maximum-tether-length constraints fit existing concepts, but the cold-shrink retention mechanism is not cleanly represented by the current attachment-method vocabulary. Before adding a code, a later slice should confirm from the installation evidence that `mechanical_capture` would be semantically misleading and that cold-shrink/elastic-contraction is a reusable mechanism family rather than a product-name alias.

No class D case was identified in the initial cohort.

## What this benchmark does not prove

The V1 result is encouraging but deliberately limited.

It does not prove that:

- the four manufacturers can already be ingested automatically;
- every observed public fact has sufficient evidence quality for recommendation use;
- all connector/interface compatibility is resolved;
- all dual-ended tethers have established endpoint assignment;
- the current vocabulary covers the full catalogues of these manufacturers; or
- the 5B / 3C distribution will remain stable as more unusual products are sampled.

It proves a narrower architectural point: the current core appears to describe a meaningful cross-section of non-NLG tethering products without SKU-pair logic, while also identifying two concrete reusable gaps rather than hiding them behind permissive normalization.

## How to use the benchmark

The cohort should remain frozen while the next portability implementation slices are developed.

For each product, future work should ask in order:

1. Can current accepted claim/domain primitives represent the manufacturer evidence without loss?
2. If yes, can a vendor adapter emit those primitives without changing downstream rules?
3. If not, is the missing concept reusable across products/manufacturers?
4. Only if no reusable representation exists, is a product-specific exception actually justified?

Changes should be judged by movement toward A/B support, not simply by making a particular SKU recommendation-ready.

A new reusable class C primitive should be introduced only when the product evidence establishes its semantics and the concept is expected to recur. A class D implementation should be treated as a design smell requiring explicit justification.

## Portability phase objective and exit condition

Portability is an architecture-stabilization phase, not an end state for TetherLens. The purpose is to discover the remaining recurring abstractions while unfamiliar tethering products still have enough diversity to challenge an NLG-shaped core, then deliberately reduce the rate at which new products require core changes.

The intended loop is:

```text
sample unfamiliar cross-vendor products
  -> classify A / B / C / D against the current core
  -> implement only evidence-backed reusable C primitives
  -> prove B-class vendor ingestion into unchanged downstream semantics
  -> repeat with a materially different cohort
```

Progress should be judged by trends rather than by forcing a numerical threshold from the first cohort. Useful signals include:

- the share of new products landing in A or B;
- the number of new reusable C primitives required per cohort;
- whether one C primitive unlocks several products, manufacturers or tool-feature families;
- the rate of downstream compatibility/generation/evaluation/ranking changes caused by new catalogue products;
- the rate of D-class one-off exceptions; and
- human effort and evidence-resolution cost required to make products recommendation-ready.

The portability-led architecture phase should be considered mature enough to de-emphasize when successive representative cross-vendor additions are predominantly A/B, new C findings are occasional and clearly reusable, D remains absent or exceptional, and new manufacturers mostly require acquisition/extraction/evidence work rather than changes to recommendation semantics.

At that point the centre of gravity should shift deliberately toward:

- catalogue throughput and coverage across the major tethering manufacturers;
- scaling the much larger tool catalogue through reusable tool features and operational configuration facts rather than pairwise mappings;
- resolving evidence and measurement gaps efficiently; and
- returning attention to the demand-side MVP: tool recognition, targeted context capture and the field recommendation workflow.

Portability cohorts should continue after that transition as periodic stress/regression tests. They should no longer be the default reason to deepen the ontology.

## Follow-on strategy

The strongest next core slice is now the recurring **single-feature captive eligibility** gap, because one generic improvement would cover products from both GRIPPS and FallTech and likely many additional ToolAttachments. The implementation should extend the existing feature-bound eligibility composition without weakening the current NLG `captive handle OR captive through-opening` case.

The key semantic requirement is:

```text
manufacturer evidence: captive handle only
  -> executable captive-handle path only

manufacturer evidence: captive through-opening only
  -> executable captive-through-opening path only

manufacturer evidence: captive handle OR captive through-opening
  -> existing two-path OR composition
```

Do not infer alternatives the source did not authorize, and do not introduce product/SKU branches.

After that reusable C-class gap is closed, prove B-class portability with products from different manufacturers while keeping downstream recommendation rules unchanged. A strong pair is:

- **GRIPPS H01079**, exercising explicit directional dual-carabiner endpoints without relying on recent NLG-derived equivalence; and
- **FallTech 5027B**, exercising the existing carabiner + cinch-loop tether topology and connection semantics.

Ty-Flot Cold Shrink can then be revisited as the remaining class C candidate. Do not add a new retention code until the installation evidence has been reviewed against `mechanical_capture`, `cinch`, `wrap` and `through_feature`.

The benchmark should expand only when a new cohort materially tests a different mechanism or exposes a new architectural risk. Catalogue breadth is useful when it tests reuse; product count by itself is not the objective.
