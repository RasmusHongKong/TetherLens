# TetherLens Project Status

_Last updated: 2026-08-27_

This document is the short operational handoff for the current TetherLens ingestion and compatibility work. It records what has landed, what the latest benchmark says, and which workstreams should be tackled next.

For durable design principles, use the dedicated documents such as `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `container-interface-topology.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`. This file should not replace those documents or freeze semantic decisions before the evidence has been inspected.

## Current ingestion and compatibility state

The current development line through PR #30 includes the completed work from:

- PR #17 — Batch 2 blind NLG holdout and post-blind evaluation path;
- PR #18 — explicit tether endpoint topology;
- PR #19 — salvaged NLG catalogue discovery plus value-sensitive forbidden-claim scoring;
- PR #20 — reusable primitive ToolAttachment attachment-method semantics;
- PR #21 — ToolAttachment compatibility and installation constraints;
- PR #22 — NLG evidence-polarity and bond-time hardening;
- PR #23 — normalized tool-anatomy and attachment-selection semantics;
- PR #24 — executable feature-bound attachment eligibility core;
- PR #25 — accepted tool-feature resolution plus the first reusable captive-feature ToolAttachment vertical slice;
- PR #26 — comparison hardening and conservative dimensional evaluation;
- PR #27 — ToolAttachment-provided tether interfaces, resolved tether endpoints, and topology-aware endpoint engagement;
- PR #28 — explicit connection-compatibility bases and controlled runtime-verification design;
- PR #29 — executable compatibility-basis runtime model, connector-spec resolution, manufacturer-assessment precedence, and the first bounded gated-connector/closed-interface verification family; and
- PR #30 — repeated container tether interfaces with explicit location, evidence-bound form, per-interface rating, and fail-closed cross-source reconciliation.

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
- runtime `ConnectionInterface` objects for ToolAttachment-provided tether-side interfaces, tether connection points, and container-provided tether interfaces;
- evidence-backed ToolAttachment-provided tether-side rings only when manufacturer wording locally binds physical form to tether function;
- repeated container connection sites represented as distinct physical-interface subjects, with explicit `internal` / `external` location when stated and per-interface ratings when evidence establishes an each-site rating;
- conservative container form resolution: a stated D-ring can resolve to `ring`, while a functional anchor with unstated geometry remains unknown rather than being inferred from imagery or naming;
- separation of container tether anchors from tool holders, bag-mounting hardware, lifting handles, rope-management loops, structural rings, and other non-tether functions;
- cross-artifact topology reconciliation before materialization, with conflicting or unbindable observations kept from manufacturing extra interfaces;
- polarity-aware container extraction so explicit manufacturer prohibitions cannot be inverted into positive tether capability;
- endpoint-side topology checks that reject obviously wrong tool-side/anchor-side pairings;
- explicit technical connection states of `compatible`, `incompatible`, `requires_verification`, and `unresolved`;
- explicit compatibility bases of `manufacturer_declared`, `validated_geometry`, `validated_interface_class`, `runtime_verification`, and `none`;
- runtime verification status kept separate from catalogue facts, so a bounded field check can move a particular configuration from `requires_verification` without creating universal catalogue compatibility;
- manufacturer compatibility assessments preserved as a separate reasoning axis from technical fit, with authoritative manufacturer conflicts and hard physical contradictions able to block a recommendation;
- inconclusive geometry remaining inconclusive rather than being converted into false incompatibility; and
- the first reusable `gated_connector_to_closed_interface.v1` verification family, which can move an evidence-backed connection path beyond topology-only `unresolved` without using SKU-pair logic or treating type names alone as proof of compatibility.

The major architectural shift from PRs #27–#29 is now implemented rather than merely proposed: **every required connection needs an acceptable compatibility basis, but complete engineering geometry is not a universal catalogue-completeness requirement.** Geometry remains valuable where it can establish hard impossibility, provide a reusable validated rule, or materially simplify a bounded field-verification procedure.

PR #30 extends the same evidence discipline to containers. Function, topology, physical form, location, rating, manufacturer position, and runtime verification remain separate facts. Unknown form is allowed to remain unknown, and contradictory or prohibited-use evidence fails closed instead of being coerced into a complete-looking topology.

## Latest benchmark state

The latest green validation on the PR #30 head completed the full workflow:

- **197 unit tests passed**;
- Batch 1 live acquisition completed **12/12 products**;
- Batch 1 extraction scored **54 true positives, 0 false positives, and 0 false negatives**;
- Batch 1 micro precision and recall were both **1.0**;
- Batch 1 recommendation-data coverage is **27/29 requirements**, with **10/12 baseline products complete**;
- the two remaining Batch 1 missing requirements are existing `source_blocked` cases rather than extraction regressions;
- fresh Batch 2 post-blind evaluation acquired **8/8 products**;
- fresh Batch 2 extraction scored **87 true positives, 0 false positives, and 0 false negatives**;
- fresh Batch 2 micro precision and recall were both **1.0**;
- fresh Batch 2 recommendation-data coverage is **44/44 requirements** with **8/8 baseline products complete**; and
- the fresh Batch 2 run records **four known semantic/evidence gaps** rather than manufacturing certainty to make the dataset appear complete.

The immutable Batch 2 blind baseline must remain unchanged. Against the expanded v0.9 golden contract it records **12 TP / 3 FP / 75 FN** with two forbidden hits. That poorer score is expected: the artifact preserves the genuinely blind pre-fix output while the contract has subsequently expanded to include endpoint, ToolAttachment-interface, installation-constraint, and repeated-container-topology semantics. It is a historical baseline, not a regression signal.

The four current Batch 2 known gaps are:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |
| NLG 101520 | Ascent™ Pouch | `public_fact_not_established` | external daisy-chain presence is established, but the public source does not establish an individual loop/site count |

NLG 101492 is no longer a structured-topology gap: the Tall Tool Bag now resolves eight evidence-backed container connection sites as six internal rings plus two external anchors whose physical form remains unknown.

Batch 1 still records legitimate non-parser gaps including manufacturer-document joins/revisions, internal measurements, and source-blocked facts. Those should remain visible rather than being weakened into permissive defaults.

## Next workstreams

### 1. Compose the existing primitives into an end-to-end recommendation path

The highest-value next milestone is no longer another isolated vocabulary or resolver. TetherLens now has enough reusable pieces to prove a complete recommendation path while preserving uncertainty at each boundary.

A representative end-to-end evaluation should be able to:

1. resolve the tool's operational mass and accepted physical features;
2. evaluate reusable ToolAttachment eligibility against those features;
3. resolve the ToolAttachment-provided tether-side interface when an attachment is required;
4. resolve the relevant tether endpoint and connector specification;
5. evaluate tether endpoint ↔ tool/ToolAttachment interface compatibility using the available compatibility basis;
6. evaluate the opposite tether endpoint ↔ anchor/container connection in the same way;
7. apply relevant rated capacities, lanyard-length limits, installation constraints, manufacturer assessments, and other already-modeled restrictions;
8. propagate `requires_verification`, evidence conflicts, public ambiguity, source gaps, and genuinely unresolved steps rather than collapsing them into a binary recommendation; and
9. produce a recommendation only when every required link in the path is adequately established.

The first implementation should use one or two realistic, evidence-backed vertical slices chosen for semantic reuse, not because they form convenient SKU pairs. The evaluator should consume normalized product facts and interfaces; production code should not contain product-specific recommendation branches.

A useful success criterion is that one complete tool → ToolAttachment (where required) → tether → anchor/container path can be evaluated with an auditable explanation of which compatibility basis closed each connection and which checks remain runtime verification rather than catalogue truth.

### 2. Selective connector/interface geometry and dimensional compatibility

Geometry remains an important supporting workstream, but it should be driven by real connection cases rather than by a goal of fully measuring the catalogue.

Prioritize measurements or new geometry vocabulary when:

- a connector specification is reused across many tether SKUs;
- one measurement resolves a high-frequency recurring uncertainty;
- a hard geometric rule can conclusively reject unsafe engagement;
- a published dimension can upgrade a recurring path from runtime verification to catalogue-established compatibility; or
- the dimension materially simplifies or strengthens a validated field-verification procedure.

The technical-schema principle still applies: add only dimensions required by real validated rules. Do not build a general CAD model, and do not infer compatibility from names such as `carabiner`, `ring`, or `loop` alone.

### 3. Remaining evidence, document, and measurement gaps

Continue addressing gaps when they materially block a recommendation path or reveal a reusable evidence-model weakness.

Current examples include:

- the two Batch 1 `source_blocked` recommendation requirements;
- manufacturer-document joins and revision handling still recorded by Batch 1;
- internal measurements that may become worthwhile once a recurring geometric rule has been identified;
- the NLG 101365 first-party recommendation conflict;
- the NLG 101481 descriptive-vs-prescriptive surface-profile tension;
- the NLG 101756 locking-mode ambiguity; and
- the NLG 101520 external daisy-chain site count, which should remain unknown unless an acceptable source actually establishes it.

Do not turn imagery, catalogue convenience, or a likely interpretation into a structured fact merely to close one of these gaps.

## Working principles for the next phase

The following constraints remain in force across all workstreams:

- do not add SKU-specific extraction or compatibility branches to make a benchmark product pass;
- inspect catalogue variation and manufacturer evidence before defining new normalized vocabularies or rules;
- model primitive physical facts and relationships rather than app-specific recommendation labels;
- preserve manufacturer wording and provenance per claim;
- keep topology, geometry, connector operation, manufacturer position, runtime verification and site policy as separate reasoning axes;
- require same-subject / same-feature binding where facts must belong to one physical feature;
- distinguish source absence, acquisition failure, parser failure, semantic-vocabulary gaps, evidence-scope tension, public ambiguity, true claim conflict, `requires_verification`, and genuinely unresolved compatibility;
- do not infer `compatible` from interface names alone;
- do not treat a successful session-level field verification as universal catalogue compatibility;
- let hard physical contradiction and authoritative manufacturer prohibition fail closed;
- let inconclusive geometry remain inconclusive;
- preserve explicit negative-use wording and do not invert it into capability;
- reconcile repeated topology across accepted artifacts before materializing physical interfaces;
- do not infer repeated interface counts from imagery;
- do not weaken evidence requirements to manufacture completeness;
- preserve the original Batch 2 blind artifact and cohort unchanged;
- use fresh post-blind evaluation against that same cohort for regression checking; and
- reserve paid/general search for genuinely difficult cases after deterministic manufacturer and qualified-source paths have been exhausted.

## Suggested fresh-chat starting point

After PR #30, start with **end-to-end recommendation path composition** rather than another isolated extraction rule.

A concise handoff prompt is:

> Continue TetherLens from `main` after PR #30. Inspect the current recommendation/evaluation path and compose the existing operational-mass, tool-feature eligibility, ToolAttachment-provided interface, tether endpoint/ConnectorSpec, compatibility-basis, container/anchor interface, rating, lanyard-length, manufacturer-assessment, and runtime-verification primitives into the smallest reusable end-to-end recommendation evaluation. Prove it with one or two evidence-backed vertical slices without SKU-pair logic, and keep any unsupported connection or policy step explicitly `requires_verification` or `unresolved` rather than manufacturing compatibility.
