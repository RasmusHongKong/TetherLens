# Cross-vendor portability benchmark

## Purpose

This benchmark tests whether the TetherLens knowledge and recommendation model built through the NLG-heavy development phase is portable beyond that original cohort.

The first benchmark intentionally freezes the core at merged `main` commit `7e9785456e3f52511f017fdc0a3f19afc1c652c7` and inspects an unseen cross-vendor cohort before adding new production semantics for those products. The post-PR #55 V2 audit repeats the same classification exercise against the evolved current core without rewriting the historical V1 answer key. PR #58 adds a third fresh audit after vertically proving the handle/secure-fit boundary, again preserving both earlier historical cohorts unchanged.

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

The reviewed V1 architecture audit produces:

```text
A facts_only               0
B vendor_ingestion_only    5
C new_reusable_primitive   3
D sku_specific_exception   0
```

The absence of class A is expected in this first cross-vendor slice because none of these manufacturers yet has a normal production adapter in the current repository. Five products appear to fit the existing normalized core without a new compatibility, candidate-generation, ranking or SKU-pair rule.

The review also exposed a useful recurring class C gap that the initial audit missed. The runtime `AttachmentEligibility` model can represent arbitrary feature-bound paths, but the production `resolve_attachment_eligibility()` compiler at the V1 freeze supported only one `captive_feature_attachment` selection class, which always expanded to:

```text
captive handle
OR
captive through-opening
```

That was correct for NLG evidence that explicitly permits both alternatives, but it could not faithfully compile a manufacturer statement that authorizes only one of them.

This affected two different manufacturers in the frozen cohort:

- **GRIPPS H01055 Tool Hitch** establishes closed-handle use. Treating it as the combined class would unevidentially authorize through-openings.
- **FallTech 5318A10** establishes captive-eye attachment points. Treating it as the combined class would unevidentially authorize handles.

Both therefore remain C in the frozen V1 artifact. They exposed the same reusable need: feature-scoped attachment eligibility must be able to express a single captive handle path or a single captive through-opening path without automatically widening to the other alternative. PR #53 later closed this current-core gap while deliberately leaving the historical V1 result unchanged.

Representative V1 B-class reuse findings include:

- the GRIPPS H01079 directional heavy-duty tether maps to existing concrete endpoints plus `tool_side` / `anchor_side` roles rather than requiring symmetric-end inference;
- FallTech 5027B maps to the existing mixed carabiner/cinch-loop tether topology and bounded cinch-loop connection family;
- Ty-Flot CC2956WR14LRD fits existing mixed endpoint, swivel/mechanism, capacity and min/max length concepts, while its loop engagement must remain evidence-bound rather than assumed from the word `loop`;
- both Dropsafe tether examples fit the existing carabiner/loop, action-count, locking, geometry, capacity and length vocabulary. The twin-carabiner product must remain assignment-unknown unless accepted evidence separately proves direction or reversibility.

The third V1 class C case is Ty-Flot `COLDSH41X35`. Its diameter-fit, capacity and maximum-tether-length constraints fit existing concepts, but the cold-shrink retention mechanism was not cleanly represented at the V1 freeze. PR #55 later closed that current-core mechanism gap through manufacturer-neutral `contraction_capture` plus source-local external-section fit envelopes, while retaining the product's current evidence conflicts.

No class D case was identified in V1.

## What V1 does not prove

The V1 result is encouraging but deliberately limited.

It does not prove that:

- the four manufacturers can already be ingested automatically;
- every observed public fact has sufficient evidence quality for recommendation use;
- all connector/interface compatibility is resolved;
- all dual-ended tethers have established endpoint assignment;
- the current vocabulary covers the full catalogues of these manufacturers; or
- the 5B / 3C distribution will remain stable as more unusual products are sampled.

It proves a narrower architectural point: the core at the PR #51 freeze described a meaningful cross-section of non-NLG tethering products without SKU-pair logic while exposing concrete reusable gaps rather than hiding them behind permissive normalization.

## How to use the benchmark

Each cohort is frozen at its stated core revision. Historical classifications must not be rewritten after later PRs close the gaps they exposed.

For each newly sampled product, ask in order:

1. Can current accepted claim/domain primitives represent the manufacturer evidence without loss?
2. If yes, can a vendor adapter emit those primitives without changing downstream rules?
3. If not, is the missing concept reusable across products/manufacturers?
4. Only if no reusable representation exists, is a product-specific exception actually justified?

Changes should be judged by movement toward A/B support, not simply by making a particular SKU recommendation-ready.

A new reusable class C primitive should be introduced only when the product evidence establishes its semantics and the concept is expected to recur. A class D implementation should be treated as a design smell requiring explicit justification.

## Post-PR #55 V2 cohort

`benchmarks/cross_vendor_portability_v2.json` freezes a second eight-product audit at merged `main` commit `29c01939c8e8774dcc553527255fc4281708480c`, after PR #55.

The V2 cohort is disjoint from V1 and also excludes the pre-PR #55 Ergodyne web ToolAttachment + required tape/wrap family that was already used as a design input in `tool-anatomy-selection-semantics.md`. It contains two products each from FallTech, GRIPPS, Ergodyne and 3M. The sample deliberately mixes manufacturers with narrow existing adapters and manufacturers with no adapter so the audit can distinguish core reuse from catalogue-onboarding breadth without counting a previously modelled architecture sample as fresh evidence.

The sample covers:

- a screwgate-carabiner + cinch-loop tether variant outside the current FallTech extractor wording;
- captive-eye-only ToolAttachment installation with a provided carabiner interface;
- a GRIPPS triple-action carabiner + tail-loop tether with a malformed storefront load field;
- a self-closing GRIPPS handle/neck ToolAttachment with size variants;
- an Ergodyne screwgate carabiner + cinch-loop tether;
- an Ergodyne retractable tether with explicit anchor-side manual-locking carabiner and tool-side choking-loop roles;
- a 3M D-ring attachment installed with a separately catalogued Quick-Wrap Tape product; and
- a 3M slide-on Quick Spin attachment with a nominal diameter.

The reviewed V2 result is:

```text
A facts_only               0
B vendor_ingestion_only    6
C new_reusable_primitive   2
D sku_specific_exception   0
```

This is a stronger portability signal than V1. Six of eight fresh products fit the post-#55 domain/recommendation core without a new compatibility, candidate-generation, hard-evaluation, ranking or SKU-pair rule. The lack of A-class results is now mostly a catalogue-throughput signal: the existing GRIPPS and FallTech adapters were intentionally narrow proofs, while Ergodyne and 3M had no normal adapters at that freeze.

### Required companion products remain existing-core reuse

The V2 cohort contains one 3M D-ring system whose installation requires separately catalogued Quick-Wrap Tape II. The same general tape/wrap assembly pattern had already been considered before PR #55 using an Ergodyne architecture sample, which is why that Ergodyne ToolAttachment family is now explicitly excluded from the fresh V2 cohort.

The 3M case still provides a useful cross-vendor reuse check: the technical schema already has a manufacturer-backed `required_pairing` relationship and candidate generation already accepts ToolAttachment assemblies with one or many component instances. The correct architecture remains:

```text
accepted manufacturer pairing
  -> retain both catalogue-product identities
  -> compose one multi-component ToolAttachment assembly
  -> preserve ordinary capacity / interface / constraint semantics
```

3M 1500007 is therefore B, not C. Vendor acquisition/composition must establish the relationship and component identities, but downstream recommendation semantics must not gain a product-pair exception. This is confirmation that an already-designed generic assembly model ports to another manufacturer, not a claim that V2 newly discovered the companion-product primitive.

### Frozen V2 C gap: non-captive capture fit

The two V2 C cases are **GRIPPS H01150 SnapLock** and **3M 1500028 Quick Spin Medium**.

They remain C in the frozen V2 artifact because it records the post-PR #55 core. Subsequent PRs deliberately close the shared current-core gap without rewriting that historical answer key.

PR #57 establishes the reusable common subset:

- `handle_attachment` compiles only `feature_kind = handle`, with captive state unconstrained;
- `secure_attachment_fit_required` is a distinct PRE_USE obligation rather than an invented numeric fit envelope or an alias for `pre_use_attachment_test_required`;
- S/M/L/XL and nominal attachment diameter do not become min/max tool-feature geometry; and
- GRIPPS `neck` is not widened to `external_section_attachment` without separate evidence-backed semantics.

PR #58 vertically proves that boundary against both manufacturers and adds Quick Spin's separate hard tapered-surface prohibition as `prohibited_surface_profile = tapered`. The prohibition remains distinct from secure fit and stays bound to the selected installation feature.

### Evidence gaps remain separate

V2 also reinforces the evidence/core distinction. The current GRIPPS H01074 storefront exposes a malformed `7 g / 15 g` summary field while the product title and detailed specifications state `7 kg / 15 lb`. That is an evidence/extraction-quality issue, not a new capacity concept.

Likewise, a B-class product may remain recommendation-blocked where endpoint direction, engagement method or another mandatory fact is not established. V2 classification records model fit, not a promise that every sampled SKU is already recommendation-ready.

## Post-PR #57 V3 cohort

`benchmarks/cross_vendor_portability_v3.json` is the third independent eight-product audit. It is disjoint from V1 and V2 and is evaluated after the SnapLock/Quick Spin production semantics are finalized on PR #58.

The benchmark manifest freezes that semantic point at production commit `dba4174a4d504663f6aa66269630e62da4b160f8` on `vertical/quickspin-snaplock-portability-v3`, against base `main` commit `94722224944d8d2c8afc38fc2d069c12f608a9ad` through PR #57, with PR #58 still pending merge at the time of the audit. Later review hardening and documentation commits do not rewrite that semantic freeze.

The reviewed V3 result is:

```text
A facts_only               0
B vendor_ingestion_only    5
C new_reusable_primitive   3
D sku_specific_exception   0
```

The five B-class products are:

- Safewaze SW431 35 lb Medium Duty Elasticated Tool Tether;
- Safewaze SW411 5 lb Coil Tool Tether;
- Milwaukee 48-22-8825 5 lb 50 in Retractable Tool Lanyard;
- Guardian RET552RP-R 5 lb Retractable Tool Tether; and
- FallTech 5031A dual aluminum twist-lock tether.

Their smallest required change remains vendor/catalogue ingestion. The normalized recommendation core does not need a new compatibility, hard-evaluation, ranking or SKU-pair rule for those products based on the reviewed evidence.

The three C-class products are:

- Milwaukee 48-22-8855 50 lb Anchor Strap;
- FallTech 5424A10 Waist Belt Cinch Anchor Attachment; and
- Ergodyne Squids 3171 / SKU 19171 Anchor Strap Belt Loop Attachment.

### Recurring V3 C seam: AnchorAttachment installation eligibility and selected anchor-feature binding

These products expose one reusable boundary rather than three product-specific exceptions.

The current core can represent an `AnchorAttachment` component and the tether-side interface that it provides. Candidate generation can also consume a pre-resolved `AnchorPathOption`. What is missing is the anchor-side analogue of the ToolAttachment eligibility/binding layer: a generic way to compile manufacturer evidence about **where/how the AnchorAttachment may install**, bind that rule to one concrete selected primary-anchor feature, and carry that exact binding into candidate generation/evaluation.

The reviewed manufacturer evidence demonstrates materially different but related installation conditions:

- Milwaukee's anchor strap wraps around supported primary-anchor geometry such as beams/rails;
- FallTech's waist-belt cinch attachment is installed by choking/cinching on supported belt or small-anchor geometry; and
- Ergodyne's enclosed belt-loop attachment must be threaded over an open-ended/refastenable primary anchor, with an explicit maximum dimension in the reviewed instructions.

Those facts should not be flattened into a generic “anchor attachment exists” assertion, nor should candidate generation be handed an unevidenced pre-resolved `AnchorPathOption`. The next reusable model should establish the smallest manufacturer-neutral primary-anchor feature vocabulary and evidence-backed installation eligibility needed to select one concrete anchor feature without creating vendor/SKU branches.

V3 does **not** justify changing tether-to-anchor connection compatibility rules. The gap is upstream installation eligibility/binding for the AnchorAttachment itself.

### V3 interpretation

V3 remains encouraging but does not satisfy the portability exit condition yet. Five of eight products are B-class and D remains zero, but three independent vendors expose a comparable recurring C seam. Calling the architecture fully saturated at this point would hide a real reusable boundary.

The correct signal is therefore:

```text
catalogue-throughput pressure is now substantial
AND
one more recurring anchor-side installation abstraction remains
```

Catalogue onboarding can proceed in parallel, but the next semantic slice should be the conservative AnchorAttachment installation eligibility + selected-anchor-feature binding seam. After that slice is proven, one more materially different portability stress sample should decide whether portability becomes periodic rather than the default development driver.

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

Progress should be judged by trends rather than by forcing a numerical threshold from one cohort. Useful signals include:

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

## Follow-on strategy after V3

V3 is a narrow A/B majority (**5/8 B**) with **0 D**, but its three C cases independently identify one recurring AnchorAttachment installation/binding seam. The condition for a full portability-to-throughput pivot is therefore not yet met.

The immediate sequence after PR #58 should be:

1. repair the known live NLG source drift in a separate focused maintenance PR so the historical ingestion benchmark becomes a trustworthy regression signal again;
2. inspect the three V3 AnchorAttachment C cases and implement the smallest reusable manufacturer-neutral installation-eligibility plus concrete selected-anchor-feature binding layer, without changing tether-to-anchor compatibility unless evidence independently requires it;
3. continue high-leverage B-class catalogue onboarding in parallel where it does not force new downstream semantics; and
4. run one more materially different portability stress sample after the anchor-side seam is proven.

If that next sample is predominantly A/B with no comparable recurring C/D pressure, shift the development centre of gravity toward catalogue throughput and the demand-side MVP. Continue portability thereafter as a periodic stress/regression test rather than a continuous ontology-expansion loop.

Historical V1 and V2 results remain immutable throughout that sequence.