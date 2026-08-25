# TetherLens Project Status

_Last updated: 2026-08-25_

This document is the short operational handoff for the current TetherLens ingestion and compatibility work. It records what has landed, what the latest benchmark says, and which workstreams should be tackled next.

For durable design principles, use the dedicated documents such as `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`. This file should not replace those documents or freeze semantic decisions before the evidence has been inspected.

## Current ingestion and compatibility state

The current development line through PR #27 includes the completed work from:

- PR #17 — Batch 2 blind NLG holdout and post-blind evaluation path;
- PR #18 — explicit tether endpoint topology;
- PR #19 — salvaged NLG catalogue discovery plus value-sensitive forbidden-claim scoring;
- PR #20 — reusable primitive ToolAttachment attachment-method semantics;
- PR #21 — ToolAttachment compatibility and installation constraints;
- PR #22 — NLG evidence-polarity and bond-time hardening;
- PR #23 — normalized tool-anatomy and attachment-selection semantics;
- PR #24 — executable feature-bound attachment eligibility core;
- PR #25 — accepted tool-feature resolution plus the first reusable captive-feature ToolAttachment vertical slice;
- PR #26 — comparison hardening and conservative dimensional evaluation; and
- PR #27 — ToolAttachment-provided tether interfaces, resolved tether endpoints, and topology-aware endpoint engagement.

PR #16, the earlier NLG catalogue-generalization branch, was closed unmerged after its still-useful catalogue-discovery and scorer changes were carried forward through PR #19. Its older endpoint and attachment-method semantics should not be revived.

The important current capabilities are:

- manufacturer-specific ingestion adapters with shared claim/evidence semantics;
- Hilti-style product/source graph traversal for cordless-tool operational mass;
- qualified exact-SKU cross-source physical facts where the evidence policy permits them;
- deterministic manufacturer-document acquisition for Hilti with revision gaps kept explicit;
- NLG catalogue discovery with Shopify variant-level SKU enumeration, manufacturer product/variant IDs, root-relative URL normalization, and duplicate identity suppression;
- immutable NLG Batch 2 blind-result preservation alongside a fresh post-blind evaluation path;
- explicit tether connection-point subjects, including endpoint interface type, role where stated, and connector-spec references;
- connector-specific action, swivel, and locking properties rather than treating those properties as generic tether attributes;
- a reusable primitive ToolAttachment attachment-method vocabulary that keeps mechanism separate from tool geometry, surface restrictions, companion products, and application/cure constraints;
- explicit ToolAttachment applicability and installation constraints, including preservation of scoped evidence tensions rather than silently collapsing them;
- normalized runtime `ToolInterfaceFeature` semantics with feature kind, role, captive state, feature-local dimensions, and attributes;
- bounded ToolAttachment eligibility with OR between paths, AND within a path, and strict same-feature binding;
- conservative accepted-claim resolution into runtime tool features, including fail-closed handling of conflicting accepted facts and dimensions;
- a reusable `captive_feature_attachment` selection class that can match equivalent captive handles or through-openings without encoding SKU pairs;
- hardened numeric comparison semantics where malformed, non-numeric, missing, or non-finite values remain unresolved instead of accidentally passing;
- runtime `ConnectionInterface` objects for ToolAttachment-provided tether-side interfaces and tether connection points;
- evidence-backed NLG extraction of provided tether-side D-rings only when manufacturer wording locally binds the D-ring to the tether point or lanyard relation;
- endpoint-side topology checks that can reject obviously wrong tool-side/anchor-side pairings; and
- conservative endpoint engagement that remains `UNRESOLVED` when topology is plausible but no validated geometry rule proves physical engagement.

The last point is now the main architectural boundary: TetherLens can represent the relevant connection participants and their roles, but it does not yet infer physical compatibility from interface names alone. In particular, `carabiner + ring` is not treated as sufficient evidence of engagement.

## Latest benchmark state

The latest green validation on the PR #27 head completed the full workflow:

- **162 unit tests passed**;
- Batch 1 live acquisition completed **12/12 products**;
- Batch 1 extraction scored **54 true positives, 0 false positives, and 0 false negatives**;
- Batch 1 micro precision and recall were both **1.0**;
- Batch 1 recommendation-data coverage is **27/29 requirements**, with **10/12 baseline products complete**;
- the two remaining Batch 1 missing requirements are existing `source_blocked` cases rather than extraction regressions;
- fresh Batch 2 post-blind evaluation acquired **8/8 products**;
- fresh Batch 2 extraction scored **47 true positives, 0 false positives, and 0 false negatives**;
- fresh Batch 2 micro precision and recall were both **1.0**;
- fresh Batch 2 recommendation-data coverage is **36/36 requirements** with **8/8 baseline products complete**; and
- the fresh Batch 2 run records **five known semantic/evidence gaps** rather than hiding them behind the complete baseline requirement count.

The immutable Batch 2 blind baseline must remain unchanged. Against the expanded current golden contract it records **14 TP / 1 FP / 33 FN**; that poorer result is expected because it preserves the genuinely blind pre-fix output rather than current adapter performance.

The five current Batch 2 known gaps are:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101520 | Ascent™ Pouch | `claim_vocabulary_gap` | internal anchor count/topology |
| NLG 101492 | Tall Tool Bag | `claim_vocabulary_gap` | internal/external anchor and holder topology |
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |

These gaps should remain explicit until the relevant workstream resolves them. Passing the current recommendation-data baseline is not a reason to manufacture certainty where the evidence or model is still incomplete.

## Next workstreams

### 1. Connector/interface geometry and dimensional engagement

This is the recommended next workstream because PR #27 now exposes a clean stopping point: the system can resolve a tether endpoint and a target tether-side interface, enforce endpoint-side semantics, and identify a topologically plausible pair, but it intentionally returns `UNRESOLVED` until geometry proves or disproves engagement.

The goal is **not** to create a general CAD or arbitrary mechanical-geometry model. The technical schema already establishes the right principle: record only dimensions required by real compatibility rules.

Initial work should therefore:

1. inspect the current `ConnectionInterface`, `ConnectorSpec`, resolution code, endpoint evaluator, `dimension_type_code` vocabulary, claim model, and relevant benchmark expectations on `main`;
2. inspect representative first-party evidence for connector/interface geometry rather than beginning from an assumed rule;
3. identify the smallest reusable set of dimensions needed for one real engagement rule, for example gate opening plus the relevant closed-ring/eye section or opening geometry where evidence supports those measurements;
4. keep connector geometry separate from connector locking/action/swivel semantics;
5. resolve the required dimensions from evidence-backed claims into runtime connection objects without SKU-pair logic;
6. implement a rule that can return all three meaningful states: `COMPATIBLE` when measurements prove fit, `INCOMPATIBLE` when measurements prove non-fit, and `UNRESOLVED` when evidence is missing or insufficient; and
7. use representative real catalogue cases alongside adversarial synthetic tests so the first geometry rule is both evidence-backed and reusable.

Relevant existing geometry gaps include NLG tether/connector cases such as 101372, the NLG 101363 D-ring attachment path, and Hilti tether connector evidence such as 2261970. Which products form the first complete vertical slice should be chosen only after the available manufacturer evidence has been inspected.

A successful first geometry PR should move at least one real endpoint/interface path beyond topology-only `UNRESOLVED` without introducing a shortcut such as “carabiner connects to ring by type name.”

### 2. Container anchor topology

Primary benchmark cases:

- NLG 101520 — Ascent™ Pouch: integrated internal anchor count/topology is not yet normalized; and
- NLG 101492 — Tall Tool Bag: internal and external anchor/tool-holder topology is not yet structured.

This workstream should build on the shared connection/interface direction established by tether endpoint and ToolAttachment topology. Prefer explicit physical interfaces and repeated-interface relationships over a single overloaded aggregate field, while retaining counts where they are useful as derived or transitional facts.

Before implementation, inspect multiple container products so the model can distinguish concepts such as internal anchors, external anchors, daisy chains/tool holders, repeated interfaces, per-interface ratings, and interfaces that are storage/retention features rather than tether anchors.

### 3. Evidence conflicts, scope tensions, and ambiguity

Once the next structural topology/geometry gaps are addressed, return to evidence reconciliation rather than broadening extraction simply to force a value.

Initial cases:

- **NLG 101365 — Adjustable Wristband:** the product webpage and another first-party NLG source give conflicting attached-weight guidance. Preserve both claims and resolve the recommendation only if the evidence policy provides a defensible reconciliation basis; do not silently choose one first-party value.
- **NLG 101481 — Mini Adhesive D Ring:** descriptive copy supports curved-surface capability while current product instructions prescribe a flat installation surface. Preserve the scope distinction and let the prescriptive installation constraint govern eligibility unless stronger evidence resolves the tension.
- **NLG 101756 — Heavy Duty Retractable Lanyard:** current public copy establishes a locking carabiner but does not establish whether locking is manual or automatic. Keep the detailed locking mode unresolved unless a qualified source explicitly distinguishes it.

This workstream should improve the evidence model itself where required: source identity, scope, evidence priority, conflict representation, ambiguity states, and recommendation-readiness behavior when a critical fact is disputed or under-specified.

## Working principles for the next phase

The following constraints remain in force across all workstreams:

- do not add SKU-specific extraction or compatibility branches to make a benchmark product pass;
- inspect catalogue variation and manufacturer evidence before defining new normalized vocabularies or rules;
- model primitive physical facts and relationships rather than app-specific recommendation labels;
- preserve manufacturer wording and provenance per claim;
- keep topology, geometry, connector operation, manufacturer position, and site policy as separate reasoning axes;
- require same-subject / same-feature binding where facts must belong to one physical feature;
- distinguish source absence, acquisition failure, parser failure, semantic-vocabulary gaps, evidence-scope tension, public ambiguity, and true claim conflict;
- fail closed when required dimensions, polarity, subject binding, or evidence are uncertain;
- do not weaken evidence requirements to manufacture completeness;
- preserve the original Batch 2 blind artifact and cohort unchanged;
- use fresh post-blind evaluation against that same cohort for regression checking; and
- reserve paid/general search for genuinely difficult cases after deterministic manufacturer and qualified-source paths have been exhausted.

## Suggested fresh-chat starting point

Start the next chat with the **connector/interface geometry and dimensional-engagement** workstream. The first action should be inspection rather than implementation: review the current runtime connection model, connector specs, resolver/evaluator, technical schema, benchmark gaps, and available first-party geometry evidence before choosing the first rule.

A concise handoff prompt is:

> Continue TetherLens from `main` after PR #27. Start the connector/interface geometry and dimensional-compatibility workstream. First inspect the current `ConnectionInterface`, `ConnectorSpec`, resolver/evaluator, technical schema, benchmark gaps, and available manufacturer evidence for representative connector/ring cases before changing code. Define the smallest reusable geometry vocabulary and engagement rule needed to move endpoint evaluation from topology-only `UNRESOLVED` toward evidence-backed `COMPATIBLE` / `INCOMPATIBLE` results, without SKU-pair logic or type-name compatibility shortcuts.
