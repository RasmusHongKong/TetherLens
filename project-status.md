# TetherLens Project Status

_Last updated: 2026-09-15_

This is the operational handoff for the current TetherLens supply-side knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file should stay focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `anchor-installation-portability-v4.md`, `tool-attachment-compatibility.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Current baseline

Merged `main` is post-PR #61. PR #62, `Close V4 wrist and bucket-lip AnchorAttachment seams`, is open and review-complete with green CI at the latest production-semantic head before this documentation pass.

Historical portability cohorts are immutable at their original semantic revisions:

```text
V1  0 A / 5 B / 3 C / 0 D   after PR #51
V2  0 A / 6 B / 2 C / 0 D   against post-PR #55 main
V3  0 A / 5 B / 3 C / 0 D   PR #58 production-semantic freeze
V4  0 A / 4 B / 4 C / 0 D   PR #61 production-semantic freeze
```

Do not rewrite those answer keys after later PRs close the gaps they exposed.

## Recent architecture milestones

The current recommendation architecture is the result of a sequence of reusable, evidence-bound layers rather than SKU-pair logic.

- PRs #23-#27 established normalized tool features, feature-bound ToolAttachment eligibility, ToolAttachment-provided tether interfaces and topology-aware endpoint engagement.
- PRs #28-#32 established controlled runtime verification, declared compatibility bases, normalized hard/pre-use/contextual constraints and provenance retention.
- PRs #33-#36 established candidate generation, hard evaluation, deterministic ranking/selection and complete recommendation-run orchestration.
- PRs #37-#41 added bounded contextual reasoning for snag risk, required reach, environmental constraints and session-local pending-condition resolution.
- PRs #42-#51 hardened connector/endpoint semantics, declared compatibility, reversible endpoint assignment and semantic end-to-end recommendation goldens without introducing product-pair recommendation rules.
- PRs #52-#58 introduced the cross-vendor portability programme and closed recurring reusable ToolAttachment gaps exposed by V1/V2 while keeping historical cohorts frozen.
- PR #59 restored the NLG live regression signal without rewriting historical goldens.
- PR #60 introduced the reusable AnchorAttachment installation/binding core.
- PR #61 vertically proved that core through normal first-party ingestion/resolution and froze V4 at **0 A / 4 B / 4 C / 0 D**.
- PR #62 closes the two recurring V4 C seams without changing tether-to-anchor compatibility, ranking, selection or exhaustion.

PR #16 remains closed unmerged; its useful work was carried forward elsewhere and its older topology semantics should not be revived.

## Current recommendation architecture

### Candidate generation and hard evaluation

Candidate generation constructs structurally admissible physical paths and evaluator-ready configurations. It owns candidate identity and physical binding, but it does not decide hard viability, contextual ranking or global exhaustion.

Hard viability remains the authority of candidate evaluation. Missing mandatory evidence blocks rather than being interpreted as suitability. `compatible`, `incompatible`, `requires_verification` and `unresolved` remain distinct states.

Ranking never overrides a hard failure. Selection operates only over the complete evaluated candidate set, and global exhaustion may be concluded only after all generated alternatives have been evaluated.

### ToolAttachment installation

ToolAttachment eligibility is feature-bound. A rule path must resolve against one concrete `ToolInterfaceFeature`; facts from different tool features cannot be stitched together.

The current core supports captive and non-captive reusable attachment families, explicit selected-feature binding, required companion products through manufacturer-backed relationships, secure-fit pre-use obligations, hard prohibited-surface constraints where evidenced, and ToolAttachment-provided tether-side interfaces.

Nominal size labels and qualitative fit wording do not become numeric tool geometry unless accepted evidence establishes an actual dimensional condition.

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

V4 exposed two recurring C seams across four products:

```text
wrist anchors:
  FallTech 5331A1
  GRIPPS H01086

bucket-lip hooks:
  Ergodyne Squids 3178 / 19178
  Klein 5144LG3
```

PR #62 closes both reusable seams. V4 itself remains frozen at **0 A / 4 B / 4 C / 0 D** because it records the state that exposed them.

PR #62 does **not** freeze V5. The next portability cohort should be selected only after the PR #62 semantics are merged, so the fresh sample has an unambiguous production baseline and is not biased by products already used to prove the new primitives.

## Guardrails that must remain true

- Do not introduce manufacturer/SKU branches downstream of ingestion/resolution unless no reusable semantic representation exists and the exception is explicitly justified.
- Missing evidence must fail closed; do not infer geometry, direction, compatibility, capacity or installation suitability from absence of contrary evidence.
- Do not convert qualitative words such as `small`, `adjustable`, `all sizes`, `UniFit` or nominal product labels into numeric fit envelopes.
- Keep feature-bound predicates on one concrete feature instance.
- Keep manufacturer provenance separate from exact product/variant identity.
- Bound flattened multi-product evidence to the requested identity before parsing sibling-specific fields.
- Preserve candidate identity and exact provenance through generation/evaluation; do not reconstruct safety-relevant facts from human-readable reason text.
- Keep hard viability separate from ranking/context.
- Preserve historical portability cohorts and the immutable Batch 2 blind baseline.
- Prefer a small reusable physical/evidence primitive over a broader ontology introduced without a concrete decision need.

## Next highest-value workstream after PR #62 merges

Run a materially different fresh portability sample against merged post-PR #62 `main`.

The cohort should be fixed before classification, disjoint from V1-V4 and from the products used to prove the PR #60/#61/#62 semantics, and should avoid simply sampling more wrist or bucket-lip AnchorAttachments. It should test whether unfamiliar products now mostly fit the existing normalized core rather than looking for another ontology seam by construction.

Classify each product by the smallest change required for correct participation:

```text
A  facts_only
B  vendor_ingestion_only
C  new_reusable_primitive
D  sku_specific_exception
```

Keep evidence availability/conflict separate from portability classification. A missing public fact is not a C-class architecture gap when the core can already represent the fact.

### Pivot decision

If the fresh sample is predominantly A/B and shows no comparable recurring C/D pressure, shift the development centre of gravity toward:

- catalogue throughput for the smaller tethering-component universe;
- efficient evidence acquisition/reconciliation;
- expanding the much larger tool catalogue through reusable features and operational configuration facts; and
- the demand-side MVP: tool recognition, targeted context capture and the field recommendation workflow.

Continue portability thereafter as a periodic stress/regression test rather than a continuous ontology-expansion loop.

If the fresh cohort instead exposes another recurring C seam, isolate the smallest reusable physical/evidence concept and prove it vertically before broadening the model. Any D result is a warning signal and should receive explicit design review before implementation.

## Suggested fresh-chat starting point after PR #62 is merged

> Continue TetherLens from merged `main` after PR #62. Keep all four historical portability cohorts frozen: V1 **0 A / 5 B / 3 C / 0 D**, V2 **0 A / 6 B / 2 C / 0 D**, V3 **0 A / 5 B / 3 C / 0 D**, V4 **0 A / 4 B / 4 C / 0 D**. PR #60 introduced the manufacturer-neutral AnchorAttachment installation/binding core, PR #61 vertically proved belt/beam/rail plus wrap/cinch/thread_over, and PR #62 closes V4's two recurring seams with `wrist` + `fasten_around` and `bucket_lip` + `hook_on`, preserving exact same-feature binding, evidence provenance, qualitative/nominal fit guardrails and unchanged tether-to-anchor compatibility/ranking/selection/exhaustion. First freeze a materially different fresh portability sample against merged post-PR #62 `main`, excluding all earlier cohort/proof identities. If the sample is predominantly A/B with no comparable recurring C/D pressure, shift the development centre toward catalogue throughput and the demand-side MVP; otherwise isolate only the next genuinely recurring reusable seam.
