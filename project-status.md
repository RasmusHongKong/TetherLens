# TetherLens Project Status

_Last updated: 2026-08-25_

This document is the short operational handoff for the current TetherLens ingestion and compatibility work. It records what has landed, what the latest benchmark says, and which workstreams should be tackled next.

For durable design principles, use the dedicated documents such as `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`. This file should not replace those documents or freeze semantic decisions before the evidence has been inspected.

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
- conservative endpoint engagement that remains `UNRESOLVED` when topology is plausible but no accepted compatibility basis has yet established the connection.

PR #27 therefore exposed an important scalability boundary. Detailed connector/interface dimensions are often not publicly available, and requiring complete engineering geometry for every connection would make catalogue readiness depend on purchasing and manually measuring a large share of the market.

The compatibility requirement has consequently been revised: **every required connection needs an acceptable compatibility basis, but dimensional proof is only one possible basis.** The durable model is documented in `connection-compatibility.md`.

Initial connection states are intended to become:

```text
compatible
incompatible
requires_verification
unresolved
```

and initial compatibility bases are:

```text
manufacturer_declared
validated_geometry
validated_interface_class
runtime_verification
none
```

`requires_verification` is deliberately distinct from `unresolved`: it means the catalogue can establish a plausible connection path and a validated bounded field check can close the remaining physical-fit uncertainty on the actual equipment.

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

### 1. Connection compatibility bases and controlled field verification

This replaces the earlier plan to make detailed dimensional engagement the universal next requirement.

The first implementation goal should be to extend connection evaluation so a topologically plausible endpoint/interface pair can distinguish:

- catalogue-established `COMPATIBLE`;
- established `INCOMPATIBLE`;
- `REQUIRES_VERIFICATION` when a validated bounded field check can close the remaining physical-fit uncertainty; and
- genuinely `UNRESOLVED` cases where no acceptable basis or verification path exists.

Initial work should:

1. read `connection-compatibility.md` alongside the current `ConnectionInterface`, resolver and evaluator;
2. add a compatibility-basis concept without collapsing manufacturer position, technical compatibility and site policy;
3. preserve existing topology/side incompatibility checks as early hard failures;
4. define the first bounded field-verification rule for a representative gated-connector-to-closed-interface family using observable physical conditions rather than a vague user confirmation;
5. ensure a successful field check remains session/configuration evidence rather than becoming a universal catalogue pairing;
6. keep type-name shortcuts prohibited — `carabiner + ring` alone must not become `COMPATIBLE`;
7. retain dimensional rules as an optional stronger basis where published or economically useful internally measured dimensions exist; and
8. use real NLG/Hilti cases plus adversarial synthetic tests to distinguish `REQUIRES_VERIFICATION` from `UNRESOLVED` and `INCOMPATIBLE`.

NLG 101372 and NLG 101363 remain useful development cases because their topology is known while the detailed engagement geometry is not publicly established. Instead of requiring those dimensions before any useful recommendation can exist, the first question is whether their connection family can be covered by a validated field-verification procedure.

A successful first PR should move at least one real endpoint/interface path beyond topology-only `UNRESOLVED` without pretending that missing catalogue geometry has been solved.

### 2. Selective connector/interface geometry

Geometry remains useful, but it is no longer a universal catalogue-completeness requirement.

Prioritize measurements only when they have good leverage, for example:

- a connector specification is reused across many tether SKUs;
- one measurement resolves a high-frequency recurring uncertainty;
- a geometry rule can conclusively reject unsafe fit; or
- the measurement can materially simplify a field-verification procedure.

The technical-schema principle still applies: add only dimensions required by real validated rules. Do not build a general CAD model.

Relevant potential cases still include NLG 101372, NLG 101363 and Hilti 2261970, but purchasing/measuring every market product is explicitly not the intended scaling strategy.

### 3. Container anchor topology

Primary benchmark cases:

- NLG 101520 — Ascent™ Pouch: integrated internal anchor count/topology is not yet normalized; and
- NLG 101492 — Tall Tool Bag: internal and external anchor/tool-holder topology is not yet structured.

This workstream should build on the shared connection/interface direction established by tether endpoint and ToolAttachment topology. Prefer explicit physical interfaces and repeated-interface relationships over a single overloaded aggregate field, while retaining counts where they are useful as derived or transitional facts.

Before implementation, inspect multiple container products so the model can distinguish concepts such as internal anchors, external anchors, daisy chains/tool holders, repeated interfaces, per-interface ratings, and interfaces that are storage/retention features rather than tether anchors.

### 4. Evidence conflicts, scope tensions, and ambiguity

Initial cases:

- **NLG 101365 — Adjustable Wristband:** preserve conflicting first-party attached-weight guidance and resolve only if the evidence policy provides a defensible reconciliation basis.
- **NLG 101481 — Mini Adhesive D Ring:** preserve the distinction between descriptive curved-surface capability and prescriptive flat-surface installation requirements.
- **NLG 101756 — Heavy Duty Retractable Lanyard:** keep detailed locking mode unresolved unless a qualified source explicitly distinguishes manual from automatic locking.

This workstream should improve source identity, scope, evidence priority, conflict representation, ambiguity states, and recommendation-readiness behavior where required.

## Working principles for the next phase

The following constraints remain in force across all workstreams:

- do not add SKU-specific extraction or compatibility branches to make a benchmark product pass;
- inspect catalogue variation and manufacturer evidence before defining new normalized vocabularies or rules;
- model primitive physical facts and relationships rather than app-specific recommendation labels;
- preserve manufacturer wording and provenance per claim;
- keep topology, geometry, connector operation, manufacturer position, runtime verification and site policy as separate reasoning axes;
- require same-subject / same-feature binding where facts must belong to one physical feature;
- distinguish source absence, acquisition failure, parser failure, semantic-vocabulary gaps, evidence-scope tension, public ambiguity, true claim conflict, `requires_verification`, and genuinely unresolved compatibility;
- do not infer `COMPATIBLE` from interface names alone;
- do not persist session-level field verification as universal catalogue compatibility;
- fail closed when a connection is neither established nor covered by a validated verification procedure;
- do not weaken evidence requirements to manufacture completeness;
- preserve the original Batch 2 blind artifact and cohort unchanged;
- use fresh post-blind evaluation against that same cohort for regression checking; and
- reserve paid/general search for genuinely difficult cases after deterministic manufacturer and qualified-source paths have been exhausted.

## Suggested fresh-chat starting point

Continue with the **connection compatibility basis and controlled field-verification** workstream before implementing detailed dimensional engagement.

A concise handoff prompt is:

> Continue TetherLens from `main` after the connection-compatibility documentation change. Implement the compatibility-basis model described in `connection-compatibility.md`: distinguish `COMPATIBLE`, `INCOMPATIBLE`, `REQUIRES_VERIFICATION`, and `UNRESOLVED`, keep geometry as one optional evidence path, and define the first bounded runtime verification rule for a representative gated-connector/closed-interface connection without SKU-pair logic or type-name compatibility shortcuts.
