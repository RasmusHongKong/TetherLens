# TetherLens Project Status

_Last updated: 2026-08-28_

This document is the short operational handoff for the current TetherLens ingestion, compatibility, and recommendation-composition work. It records what has landed, what remains intentionally unresolved, and which workstreams should be tackled next.

For durable design principles, use the dedicated documents such as `product-vision.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `tool-attachment-compatibility.md`, `tool-anatomy-selection-semantics.md`, `container-interface-topology.md`, `benchmark-goals.md`, and `ingestion-benchmark.md`. This file should not replace those documents or freeze semantic decisions before the evidence has been inspected.

## Current development line

The current development line through PR #32 includes:

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
- PR #29 — executable compatibility-basis runtime model, connector-spec resolution, manufacturer-assessment precedence, and the first bounded gated-connector/closed-interface verification family;
- PR #30 — repeated container tether interfaces with explicit location, evidence-bound form, per-interface rating, and fail-closed cross-source reconciliation;
- PR #31 — reusable `CandidateConfiguration` / `CandidateEvaluation` composition across attachment eligibility, load capacity, lanyard limits, both required connection evaluations, policy applicability, and pending runtime verification; and
- PR #32 — normalized product/installation constraints, hard-vs-pre-use action semantics, same-feature installation binding across composition, constraint provenance retention, and product-namespaced constraint identifiers.

PR #16, the earlier NLG catalogue-generalization branch, was closed unmerged after its useful catalogue-discovery and scorer changes were carried forward through PR #19. Its older endpoint and attachment-method semantics should not be revived.

PR #32 is the current open PR at the time of this update. Its scope is deliberately bounded: it does not add candidate generation, contextual ranking, global selection/exhaustion, broad new extraction vocabulary, or generic evaluation of every declared constraint.

## Important current capabilities

TetherLens can now:

- ingest manufacturer evidence into typed candidate claims with claim-level provenance;
- resolve tool operational mass from qualified manufacturer/cross-source evidence;
- resolve accepted tool anatomy into feature-local `ToolInterfaceFeature[]` with captive state, role, dimensions, and attributes;
- evaluate reusable ToolAttachment eligibility with OR between paths, AND within a path, and strict same-feature binding;
- resolve ToolAttachment-provided tether-side interfaces, tether endpoints, connector specifications, and repeated container tether interfaces;
- keep topology, geometry, connector operation, manufacturer position, runtime verification, policy, and installation constraints as separate reasoning axes;
- evaluate endpoint compatibility using explicit bases such as manufacturer declaration, validated geometry, validated interface class, or bounded runtime verification;
- preserve `compatible`, `incompatible`, `requires_verification`, and `unresolved` rather than forcing binary fit decisions;
- compose already-resolved primitives into one candidate evaluation without SKU-pair recommendation logic;
- keep a blocked candidate distinct from a globally exhausted recommendation search;
- return `recommended_with_constraints` when all hard checks pass but a validated runtime verification or pre-use action remains pending;
- distinguish pending connection verification from non-connection pre-use obligations such as adhesive cure time or a required attachment test;
- resolve supported product constraints into a normalized runtime form while leaving unsupported declared constraints outside the generic evaluator until their technical/manufacturer/policy meaning is explicit;
- apply hard installation constraints such as required surface profile, required surface condition, prohibited removable parts, and maximum lanyard length;
- bind feature-scoped installation constraints to the same eligible ToolAttachment feature used by the candidate, preventing facts from separate installation locations from being combined;
- canonicalize equivalent numeric constraint evidence before coalescing it;
- preserve primary and supporting manufacturer evidence URLs through resolution, runtime constraint evaluation, and final `CandidateCheck` output; and
- namespace resolved constraint IDs by a stable source-product reference so constraints resolved separately for different catalogue products cannot collide when their local subject is `self`.

The source-product namespace is intentionally separate from evidence URLs. Callers of `resolve_product_constraints()` must provide a stable catalogue-product reference; the resolver does not manufacture product identity from whichever evidence URL happened to support a claim.

## Recommendation-composition state

PR #31 established the first runtime composition layer. It accepts already-resolved primitives and checks:

1. ToolAttachment eligibility where applicable;
2. load-bearing component capacity against operational object mass;
3. legacy/runtime lanyard-length limits;
4. normalized product constraints;
5. tool-side connection compatibility;
6. anchor/container-side connection compatibility; and
7. site/configuration policy when explicitly applicable.

PR #32 closes the main normalized installation-constraint gap in that composition layer. Hard failures or unresolved safety-critical facts block the candidate. Known pre-use obligations can remain `requires_action`, allowing a constrained recommendation without incorrectly claiming that a physical connection itself needs verification.

The composition layer still does **not** generate candidate assemblies. It evaluates one already-generated candidate at a time and must not emit a global "no suitable recommendation" merely because that one candidate is blocked.

## Compatibility and evidence principles currently in force

The major architecture now implemented is:

**Every required connection needs an acceptable compatibility basis, but complete engineering geometry is not a universal catalogue-completeness requirement.**

Geometry remains valuable where it establishes hard impossibility, provides a reusable validated rule, or materially simplifies a bounded field-verification procedure. A type-name pair such as `carabiner + ring` is not itself proof of compatibility.

Likewise, manufacturer scope, technical fit, installation requirements, and site policy are not interchangeable. Category/application wording should not silently become a universal hard technical exclusion unless its semantics have been explicitly modeled that way.

Unknown form, ambiguous public evidence, source gaps, contradictory manufacturer evidence, and missing runtime facts should remain explicit rather than being converted into complete-looking recommendations.

## Latest benchmark state

The current development line continues to preserve the benchmark state established through PR #30 and revalidated by PRs #31–#32:

- Batch 1 live acquisition: **12/12 products**;
- Batch 1 extraction: **54 TP / 0 FP / 0 FN**;
- Batch 1 micro precision and recall: **1.0 / 1.0**;
- Batch 1 recommendation-data coverage: **27/29 requirements**, with the remaining two requirements recorded as existing `source_blocked` cases;
- fresh Batch 2 post-blind acquisition: **8/8 products**;
- fresh Batch 2 extraction: **87 TP / 0 FP / 0 FN**;
- fresh Batch 2 micro precision and recall: **1.0 / 1.0**;
- fresh Batch 2 recommendation-data coverage: **44/44 requirements**, **8/8 products complete**; and
- the immutable Batch 2 blind artifact remains unchanged as the historical pre-fix baseline.

The immutable Batch 2 blind baseline is intentionally worse against the expanded contract because the contract now includes semantics added after the blind run. It is a historical control, not a current regression target.

The four current Batch 2 evidence/semantic gaps remain:

| SKU | Product | Gap category | Field / issue |
|---|---|---|---|
| NLG 101365 | Adjustable Wristband | `evidence_conflict` | conflicting first-party attached-weight recommendation |
| NLG 101481 | Mini Adhesive D Ring | `evidence_scope_tension` | descriptive curved-surface capability vs prescriptive flat-surface installation requirement |
| NLG 101756 | Heavy Duty Retractable Lanyard, Double Carabiner | `public_fact_ambiguous` | connector locking mode not established as manual vs automatic |
| NLG 101520 | Ascent™ Pouch | `public_fact_not_established` | external daisy-chain presence is established, but public evidence does not establish an individual loop/site count |

These should remain explicit until acceptable evidence or a reusable semantic rule actually resolves them.

## Next workstreams

### 1. Candidate generation

The next highest-value slice after PR #32 is candidate generation over the primitives that are now executable.

The generator should produce candidate paths rather than SKU-pair recommendations. At minimum it should support:

- direct tool-to-tether paths where a valid direct interface exists;
- ToolAttachment paths with explicit binding to the selected eligible tool feature;
- explicit tether endpoint side/role semantics;
- attachment-provided tether interfaces;
- anchor/container-side interfaces;
- required load-bearing components; and
- normalized product constraints attached to the correct source products.

Each candidate should carry enough explicit identity/binding information that the existing evaluator can check it without looking back into raw claims or guessing which installation feature, endpoint, or product a constraint belongs to.

Multi-component ToolAttachment assemblies remain an expected future case. Candidate generation should therefore avoid baking in the assumption that one ToolAttachment SKU always equals one complete physical attachment assembly.

### 2. Contextual ranking and global selection/exhaustion

Ranking should follow candidate generation, not precede it. Once candidate construction is trustworthy, add contextual suitability, ranking, fallback, and global exhaustion semantics.

Only the global selection layer should be allowed to conclude that no suitable recommendation exists, and only after all admissible candidate paths have been generated and evaluated.

### 3. Selective geometry and remaining evidence gaps

Continue geometry, measurement, document-join, and evidence work when it materially blocks recurring candidate paths or exposes a reusable evidence-model weakness.

Prioritize new measurements or vocabulary when:

- a connector specification is reused across many tether SKUs;
- one measurement resolves a high-frequency uncertainty;
- a hard geometric rule can conclusively reject unsafe engagement;
- a published dimension can replace recurring runtime verification with catalogue-established compatibility; or
- the fact materially strengthens a validated field-verification procedure.

Do not build a general CAD model and do not weaken evidence requirements merely to close a benchmark gap.

## Working principles for the next phase

- do not add SKU-specific extraction, compatibility, or recommendation branches to make one benchmark product pass;
- inspect catalogue variation and manufacturer evidence before defining new normalized vocabularies or rules;
- model primitive physical facts and relationships rather than app-specific recommendation labels;
- preserve manufacturer wording and provenance per claim and through downstream evaluation outputs;
- keep product identity separate from evidence provenance;
- namespace identifiers that may coexist across separately resolved catalogue products;
- require same-subject / same-feature binding where facts must belong to one physical feature;
- distinguish source absence, acquisition failure, parser failure, semantic-vocabulary gaps, evidence-scope tension, public ambiguity, true claim conflict, `requires_verification`, pending pre-use action, and genuinely unresolved compatibility;
- do not infer `compatible` from interface names alone;
- do not treat a successful session-level field verification as universal catalogue compatibility;
- let hard physical contradiction and authoritative manufacturer prohibition fail closed;
- let inconclusive geometry remain inconclusive;
- preserve explicit negative-use wording and do not invert it into capability;
- reconcile repeated topology across accepted artifacts before materializing physical interfaces;
- do not infer repeated interface counts from imagery;
- preserve the original Batch 2 blind artifact and cohort unchanged; and
- use fresh post-blind evaluation against that same cohort for regression checking.

## Suggested fresh-chat starting point

After PR #32, start with **candidate generation**, not ranking.

A concise handoff prompt is:

> Continue TetherLens from `main` after PR #32. Inspect the resolved tool features, attachment eligibility, connection interfaces, connector specs, normalized product constraints, and `CandidateConfiguration` evaluator, then implement the smallest reusable candidate-generation layer for direct and ToolAttachment paths. Preserve explicit installation-feature binding, endpoint side/role semantics, source-product constraint identity, and multi-component attachment extensibility. Do not add contextual ranking or global `no suitable recommendation` logic until candidate construction itself is correct.
