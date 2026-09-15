# TetherLens Project Status

_Last updated: 2026-09-15_

This is the operational handoff for the current TetherLens supply-side knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file should stay focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `anchor-installation-portability-v4.md`, `portability-v5-post-pr62.md`, `tool-attachment-compatibility.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Current baseline

Merged `main` is post-PR #62 at commit `87f3c277f108e38dc3ec7d070e38c94868d355a6`. PR #62, `Close V4 wrist and bucket-lip AnchorAttachment seams`, is merged.

Historical portability cohorts are immutable at their original semantic revisions:

```text
V1  0 A / 5 B / 3 C / 0 D   after PR #51
V2  0 A / 6 B / 2 C / 0 D   against post-PR #55 main
V3  0 A / 5 B / 3 C / 0 D   PR #58 production-semantic freeze
V4  0 A / 4 B / 4 C / 0 D   PR #61 production-semantic freeze
```

A fifth fresh sample is now frozen against merged post-PR #62 `main`. Its identities were committed before classification at `e7c03c942b3fb2456033f7d5d3e15ee3cfee09d7`, and its reviewed result is:

```text
V5  0 A / 6 B / 2 C / 0 D   post-PR #62 main
```

Do not rewrite any historical answer key after later PRs close the gaps it exposed.

## Recent architecture milestones

The current recommendation architecture is the result of reusable, evidence-bound layers rather than SKU-pair logic.

- PRs #23-#27 established normalized tool features, feature-bound ToolAttachment eligibility, ToolAttachment-provided tether interfaces and topology-aware endpoint engagement.
- PRs #28-#32 established controlled runtime verification, declared compatibility bases, normalized hard/pre-use/contextual constraints and provenance retention.
- PRs #33-#36 established candidate generation, hard evaluation, deterministic ranking/selection and complete recommendation-run orchestration.
- PRs #37-#41 added bounded contextual reasoning for snag risk, required reach, environmental constraints and session-local pending-condition resolution.
- PRs #42-#51 hardened connector/endpoint semantics, declared compatibility, reversible endpoint assignment and semantic end-to-end recommendation goldens without introducing product-pair recommendation rules.
- PRs #52-#58 introduced the cross-vendor portability programme and closed recurring reusable ToolAttachment gaps exposed by V1/V2 while keeping historical cohorts frozen.
- PR #59 restored the NLG live regression signal without rewriting historical goldens.
- PR #60 introduced the reusable AnchorAttachment installation/binding core.
- PR #61 vertically proved that core through normal first-party ingestion/resolution and froze V4 at **0 A / 4 B / 4 C / 0 D**.
- PR #62 closed V4's two recurring C seams with `wrist` + `fasten_around` and `bucket_lip` + `hook_on`, preserving exact feature binding, provenance and qualitative/nominal fit guardrails without changing tether-to-anchor compatibility, ranking, selection or exhaustion.
- Post-PR #62 V5 is frozen at **0 A / 6 B / 2 C / 0 D**. Its six B cases strengthen the catalogue-throughput signal; its two C cases independently expose one narrow reusable ToolAttachment compiler seam: generic feature-bound dimensional eligibility.

PR #16 remains closed unmerged; its useful work was carried forward elsewhere and its older topology semantics should not be revived.

## Current recommendation architecture

### Candidate generation and hard evaluation

Candidate generation constructs structurally admissible physical paths and evaluator-ready configurations. It owns candidate identity and physical binding, but it does not decide hard viability, contextual ranking or global exhaustion.

Hard viability remains the authority of candidate evaluation. Missing mandatory evidence blocks rather than being interpreted as suitability. `compatible`, `incompatible`, `requires_verification` and `unresolved` remain distinct states.

Ranking never overrides a hard failure. Selection operates only over the complete evaluated candidate set, and global exhaustion may be concluded only after all generated alternatives have been evaluated.

### ToolAttachment installation

ToolAttachment eligibility is feature-bound. A rule path must resolve against one concrete `ToolInterfaceFeature`; facts from different tool features cannot be stitched together.

The runtime model is already dimension-generic: `ToolInterfaceFeature.dimensions_mm` may carry feature-local dimensions and `FeaturePredicate` may evaluate `dimension:<code>` against the exact bound feature.

Production claim resolution remains intentionally narrower. `handle_attachment` currently compiles a geometry-only handle path, while `external_section_attachment` has a special complete source-local min/max diameter-fit compiler. V5 demonstrates that explicit manufacturer-backed dimensions now recur outside that one diameter-specific case.

Nominal size labels and qualitative fit wording still do not become numeric tool geometry unless accepted evidence establishes an actual dimensional condition.

### AnchorAttachment installation

PR #60 introduced the separate manufacturer-neutral anchor-side model:

```text
PrimaryAnchorFeature
  -> AnchorAttachment installation eligibility
  -> exact AnchorInstallationBinding
  -> installed AnchorAttachment tether-side interface
  -> ordinary tether-endpoint compatibility
```

The current primary-anchor feature vocabulary after PR #62 is:

```text
belt
beam
rail
wrist
bucket_lip
```

The current anchor installation-method vocabulary is:

```text
wrap
cinch
thread_over
fasten_around
hook_on
```

Every eligibility path evaluates against one concrete `PrimaryAnchorFeature`. The exact selected feature, rule, source product and source provenance are retained through candidate generation and hard evaluation.

Installation eligibility is separate from tether-to-anchor interface compatibility. Neither layer may silently stand in for the other.

### Proven AnchorAttachment families

PR #61 vertically proves:

- Milwaukee 48-22-8855: `wrap` over explicit `beam` OR `rail`, without invented geometry;
- FallTech 5424A10: `cinch` over explicit `belt`, with qualitative small-anchor wording left qualitative; and
- Ergodyne Squids 3171 / 19171: `thread_over` on one open/refastenable `belt` with evidence-backed dimensional conditions.

PR #62 adds two recurring cross-vendor families:

- worker-worn / adjustable fastening: FallTech 5331A1 and GRIPPS H01086 prove `wrist` + `fasten_around`; GRIPPS also independently proves a separate `rail` path because its first-party evidence explicitly permits hand rails as well as the wrist; and
- aerial-bucket hooks: Ergodyne Squids 3178 and Klein 5144LG3 prove `bucket_lip` + `hook_on`, retaining published 2 in / 3 in lip labels as nominal feature attributes rather than inferred numeric fit envelopes.

### Provenance and identity boundaries

Manufacturer provenance and product identity are separate questions.

A manufacturer-controlled host or document namespace establishes source ownership; it does not by itself establish that the resolved page/document belongs to the requested SKU. Adapters must continue to fail closed on same-host redirects, sibling rows and multi-product documents.

PR #62 review hardening reinforces that boundary:

- FallTech BigCommerce documents are accepted only inside FallTech's store-specific `s-1wxw1202sk/content/product_documents/` namespace, not the shared `cdn11.bigcommerce.com` host generally;
- GRIPPS and Klein AnchorAttachment extraction verifies the resolved artifact against the requested product identity before emitting claims; and
- Ergodyne Squids 3178 family instruction data is selected by the requested identity-local SKU row before nominal bucket-lip class is parsed, so 19178 and 19179 remain distinct and package/sibling variants cannot inherit another row.

`adapter-review-guidance.md` remains the governing rule: generalize a manufacturer-independent safety/evidence invariant, while keeping source grammar and vendor-specific interpretation local.

## Frozen portability state

V4 exposed two recurring AnchorAttachment C seams across four products:

```text
wrist anchors:
  FallTech 5331A1
  GRIPPS H01086

bucket-lip hooks:
  Ergodyne Squids 3178 / 19178
  Klein 5144LG3
```

PR #62 closes both reusable seams. V4 itself remains frozen at **0 A / 4 B / 4 C / 0 D** because it records the state that exposed them.

V5 deliberately sampled a materially different region: four ToolAttachments and four tethers across seven manufacturers, with no AnchorAttachment products and no V1-V4 or recent proof identity. Its frozen result is **0 A / 6 B / 2 C / 0 D**.

The six B products are catalogue/onboarding work. They do not justify new endpoint, connector, ranking, selection or exhaustion semantics.

The two C products are:

```text
FallTech 5401A1 Battery Boot
Ergodyne Squids 3745 / 19747 Tool Grip
```

They expose the same compiler-level seam. Both publish explicit dimensional fit conditions that must remain bound to one selected `ToolInterfaceFeature`, but current production claim resolution only has a numeric-fit compiler for the special `external_section_attachment` min/max-diameter case. See `portability-v5-post-pr62.md` for the full audit rationale.

## Guardrails that must remain true

- Do not introduce manufacturer/SKU branches downstream of ingestion/resolution unless no reusable semantic representation exists and the exception is explicitly justified.
- Missing evidence must fail closed; do not infer geometry, direction, compatibility, capacity or installation suitability from absence of contrary evidence.
- Do not convert qualitative words such as `small`, `adjustable`, `all sizes`, `UniFit` or nominal product labels into numeric fit envelopes.
- Compile numeric feature predicates only from accepted source evidence that explicitly establishes the dimension and comparison/bound.
- Keep every feature-bound predicate, including every dimension, on one concrete feature instance.
- Do not synthesize a fit envelope by joining bounds from unrelated feature subjects or incompatible evidence sources.
- Keep manufacturer provenance separate from exact product/variant identity.
- Bound flattened multi-product evidence to the requested identity before parsing sibling-specific fields.
- Preserve candidate identity and exact provenance through generation/evaluation; do not reconstruct safety-relevant facts from human-readable reason text.
- Keep hard viability separate from ranking/context.
- Preserve V1-V5 historical portability cohorts and the immutable Batch 2 blind baseline.
- Prefer a small reusable physical/evidence primitive over a broader ontology introduced without a concrete decision need.

## Next highest-value workstream

Close only V5's recurring **generic feature-bound dimensional eligibility** seam.

The smallest reusable slice should generalize the production ToolAttachment eligibility compiler so explicit accepted dimensional predicates can be composed onto the exact selected feature for ordinary eligibility paths. It should reuse the existing runtime `FeaturePredicate` model rather than introduce battery-, screwdriver-, FallTech- or Ergodyne-specific rules.

The vertical proof should cover both V5 C manufacturers and preserve the existing diameter-fit behavior as a regression case:

```text
FallTech 5401A1
  -> one resolved external tool/configuration feature
  -> explicit source-backed length / width / height bounds
  -> same-feature eligibility

Ergodyne Squids 3745 / 19747
  -> one resolved handle
  -> explicit source-backed diameter / height bounds
  -> same-feature eligibility

existing external_section_attachment
  -> complete source-local min/max diameter envelope still behaves unchanged
```

Required guardrails:

- one selected feature per path unless a future rule explicitly declares multiple bindings;
- source-backed comparison direction only: min, max, bounded range or exact condition as actually stated;
- fail closed on incomplete/conflicting/cross-subject dimensional evidence;
- no numeric inference from nominal labels or qualitative fit wording;
- no change to tether-to-anchor compatibility, candidate ranking, selection or global exhaustion; and
- no SKU-specific compatibility branches.

After that vertical is proven, freeze another materially different fresh portability cohort. If it is predominantly A/B with no comparable recurring C/D pressure, portability should become a periodic stress/regression test and the development centre should shift to catalogue throughput plus the demand-side MVP: tool recognition, efficient tool/configuration fact acquisition, targeted context capture and the field recommendation workflow.

## Suggested fresh-chat starting point

> Continue TetherLens from the post-PR #62 V5 portability audit. Keep V1 **0 A / 5 B / 3 C / 0 D**, V2 **0 A / 6 B / 2 C / 0 D**, V3 **0 A / 5 B / 3 C / 0 D**, V4 **0 A / 4 B / 4 C / 0 D** and V5 **0 A / 6 B / 2 C / 0 D** frozen at their historical semantic revisions. V5 was frozen against merged post-PR #62 `main` before classification and deliberately sampled four ToolAttachments plus four tethers with no AnchorAttachment identities. Its six B cases are catalogue-throughput work; its two C cases, FallTech 5401A1 Battery Boot and Ergodyne Squids 3745 / 19747 Tool Grip, independently expose one narrow reusable seam: production ToolAttachment claim resolution cannot yet compose explicit accepted feature dimensions onto arbitrary same-feature eligibility paths, even though runtime `FeaturePredicate` already supports generic feature-local dimensions. Define the smallest manufacturer-neutral feature-bound dimensional-eligibility compiler, prove it vertically against both C cases while preserving the existing external-section diameter-fit guardrails, and do not change connection compatibility, ranking, selection or exhaustion. Then run one more materially different fresh portability sample to decide whether to pivot fully to catalogue throughput and the demand-side MVP.
