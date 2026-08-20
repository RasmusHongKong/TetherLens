# TetherLens Project Status

_Last updated: 2026-08-20_

This document is the short operational handoff for the current TetherLens ingestion work. It records what has landed, what the latest benchmark says, and which workstreams should be tackled next.

For durable design principles, use the dedicated documents such as `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`. This file should not replace those documents or freeze semantic decisions before the evidence has been inspected.

## Current ingestion state

The current `main` branch includes the completed work from:

- PR #17 — Batch 2 blind NLG holdout and post-blind evaluation path;
- PR #18 — explicit tether endpoint topology; and
- PR #19 — salvaged NLG catalogue discovery plus value-sensitive forbidden-claim scoring.

PR #16, the earlier NLG catalogue-generalization branch, was closed unmerged after its still-useful catalogue-discovery and scorer changes were carried forward through PR #19. Its older endpoint and attachment-method semantics should not be revived.

The important current capabilities are:

- manufacturer-specific ingestion adapters with shared claim/evidence semantics;
- Hilti-style product/source graph traversal for cordless-tool operational mass;
- qualified exact-SKU cross-source physical facts where the evidence policy permits them;
- deterministic manufacturer-document acquisition for Hilti with revision gaps kept explicit;
- NLG catalogue discovery with Shopify variant-level SKU enumeration, manufacturer product/variant IDs, root-relative URL normalization, and duplicate identity suppression;
- immutable NLG Batch 2 blind-result preservation alongside a fresh post-blind evaluation path;
- explicit tether connection-point subjects, including endpoint interface type, role where stated, and connector-spec references;
- connector-specific action, swivel, and locking properties rather than treating those properties as generic tether attributes; and
- benchmark forbidden-claim matching that is value-sensitive when a forbidden value is specified while retaining property-level wildcard behavior when no value is specified.

## Latest benchmark state

The latest green validation on the PR #19 head completed the full workflow:

- 57 unit tests passed;
- Batch 1 live acquisition completed 12/12 products;
- Batch 1 extraction scored 50 true positives, 0 false positives, and 0 false negatives;
- fresh Batch 2 post-blind evaluation acquired 8/8 products;
- fresh Batch 2 extraction scored 34 true positives, 0 false positives, and 0 false negatives;
- Batch 2 micro precision and recall were both 1.0;
- Batch 2 had 0 forbidden hits and 0 unexpected extracted claims; and
- all 24/24 current Batch 2 recommendation-data requirements were present.

The immutable Batch 2 blind baseline must remain unchanged. Its poorer score against the newer golden contract is expected because it represents the genuinely blind pre-fix output, not the current adapter performance.

The fresh Batch 2 evaluation still records **six known semantic/evidence gaps**. These are now the useful next development targets:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101691 | Angle Grinder Bracket | `claim_vocabulary_gap` | `attachment_method` |
| NLG 101481 | Mini Adhesive D Ring | `claim_vocabulary_gap` | `attachment_method` plus surface restrictions |
| NLG 101520 | Ascent™ Pouch | `claim_vocabulary_gap` | `internal_anchor_count` |
| NLG 101492 | Tall Tool Bag | `claim_vocabulary_gap` | `anchor_topology` |
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode |

These six gaps should remain explicit until the relevant workstream resolves them. Passing the current baseline requirements is not a reason to hide or collapse them.

## Next workstreams

### 1. Attachment-method semantics

Primary benchmark cases:

- NLG 101691 — Angle Grinder Bracket;
- NLG 101481 — Mini Adhesive D Ring.

The goal is **not** to add two SKU-specific values. Before changing the model or adapter, inspect a representative catalogue sample of ToolAttachment products and identify a small reusable vocabulary for the primitive attachment mechanism.

Expected method:

1. inspect the current ToolAttachment domain model, claim vocabulary, NLG adapter, and relevant benchmark contracts on `main`;
2. inspect several representative NLG ToolAttachment products covering materially different mechanisms;
3. define the smallest defensible normalized vocabulary for the attachment mechanism itself;
4. keep independent constraints separate from the mechanism, for example eligible surface/material, required tool geometry, dimensions, application/curing requirements, or other manufacturer-stated restrictions;
5. avoid compound application-specific values such as `adhesive_for_metal_tools` when the same information can be represented as primitive facts;
6. implement only semantics supported by manufacturer evidence and without SKU branches; and
7. strengthen tests and golden expectations, then rerun Batch 1 and the unchanged Batch 2 cohort.

No exact property names or enum values should be treated as frozen by this status document; they should be chosen after the catalogue survey.

### 2. Container anchor topology

Primary benchmark cases:

- NLG 101520 — Ascent™ Pouch: four integrated internal anchor points are not yet represented as explicit count/topology;
- NLG 101492 — Tall Tool Bag: internal and external anchor/tool-holder topology is not yet structured.

This workstream should follow the same modeling discipline as tether endpoint topology: prefer explicit physical interfaces/relationships over a single overloaded aggregate field, while retaining simple counts where they are useful as derived or transitional facts.

Before implementation, inspect multiple container products so the model can distinguish concepts such as internal anchors, external anchors, daisy chains/tool holders, repeated interfaces, and per-interface ratings without assuming every container has the same layout.

### 3. Evidence conflicts and ambiguity

Once the remaining structural vocabulary gaps are addressed, move to evidence reconciliation rather than broadening extraction regexes simply to force a value.

Initial cases:

- **NLG 101365 — Adjustable Wristband:** the product webpage and another first-party NLG source give conflicting attached-weight guidance. Preserve both claims and resolve the recommendation only if the evidence policy provides a defensible basis for reconciliation; do not silently choose one first-party value.
- **NLG 101756 — Heavy Duty Retractable Lanyard:** the public copy establishes a locking carabiner but does not currently establish whether the locking mode is manual or automatic. Keep the locking mode unresolved unless a qualified source explicitly distinguishes it.

This workstream should test and improve the evidence model itself: source identity, evidence priority, claim conflict representation, ambiguity states, and recommendation-readiness behavior when a critical fact is conflicting or under-specified.

## Working principles for the next phase

The following constraints remain in force across all three workstreams:

- do not add SKU-specific extraction branches to make a golden product pass;
- inspect catalogue variation before defining new normalized vocabularies;
- model primitive physical facts and relationships rather than app-specific recommendation labels;
- preserve manufacturer wording and provenance per claim;
- distinguish source absence, parser failure, semantic-vocabulary gaps, ambiguity, and evidence conflict;
- do not weaken evidence requirements to manufacture completeness;
- preserve the original Batch 2 blind artifact and cohort unchanged;
- use fresh post-blind evaluation against that same cohort for regression checking; and
- reserve paid/general search for genuinely difficult cases after deterministic manufacturer and qualified-source paths have been exhausted.

## Suggested fresh-chat starting point

Start the next chat with the **attachment-method semantics** workstream. The first action should be inspection rather than implementation: review the current ToolAttachment model/claims/tests on `main`, then survey representative NLG catalogue examples before proposing a normalized vocabulary.

A concise handoff prompt is:

> Continue TetherLens ingestion work from current `main`. Start the attachment-method semantics workstream by inspecting the current ToolAttachment model, NLG adapter/tests, Batch 1/2 contracts, and a representative sample of NLG ToolAttachment products before making changes. Define a reusable primitive attachment-method vocabulary rather than patching 101691 and 101481 individually.
