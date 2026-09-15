# TetherLens Project Status

_Last updated: 2026-09-15_

This is the operational handoff for the current TetherLens supply-side knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file stays focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `anchor-installation-portability-v4.md`, `tool-attachment-compatibility.md`, `feature-bound-dimensional-eligibility.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `portability-v5-post-pr62.md`, `portability-v6-post-feature-dimensional.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Current baseline

Merged `main` is post-PR #63 at commit:

```text
a6b76be2639bf309554a1a331da90620ce86d2fc
```

PR #64, `Compile feature-bound ToolAttachment dimensional eligibility`, is currently open as a draft from branch:

```text
feature/toolattachment-dimensional-eligibility-v6
```

Its semantic implementation was frozen before V6 identity selection at:

```text
d5f1d67c4a1e36cd7b80edfb5423bf1f7cfca43a
```

The V6 identities were then frozen before classification at:

```text
f3901d9636d198090e243ed9f9e74d558a2937f9
```

Historical portability cohorts remain immutable at their original semantic revisions:

```text
V1  0 A / 5 B / 3 C / 0 D   after PR #51
V2  0 A / 6 B / 2 C / 0 D   against post-PR #55 main
V3  0 A / 5 B / 3 C / 0 D   PR #58 production-semantic freeze
V4  0 A / 4 B / 4 C / 0 D   PR #61 production-semantic freeze
V5  0 A / 6 B / 2 C / 0 D   post-PR #62 semantic freeze
V6  1 A / 7 B / 0 C / 0 D   PR #64 semantic freeze
```

Do not rewrite any historical answer key after later PRs close the gaps it exposed.

## Current architecture state

The recommendation core is now a reusable evidence-bound stack rather than a collection of SKU-pair rules.

### Tool-side installation

A ToolAttachment eligibility path binds one concrete `ToolInterfaceFeature`. Feature kind, captive state, dimensions, attributes and other feature-local conditions in that path must all be true on the same feature instance.

PR #64 generalizes production claim resolution so explicit accepted dimensional fit conditions can be composed onto ordinary same-feature eligibility paths through:

```text
attachment_eligibility.feature_kind
attachment_eligibility.dimension.<code>
```

with explicit `eq` / `lt` / `lte` / `gt` / `gte` comparison direction.

The compiler:

- normalizes dimensional values to millimetres;
- requires the feature kind and dimensions to remain source-local on one physical-interface subject;
- permits equivalent complete profiles expressed in different units;
- rejects split-source envelope synthesis, conflicting profiles and multiple fit subjects for the same feature kind; and
- emits ordinary runtime `FeaturePredicate("dimension:<code>")` conditions on the exact selected feature path.

The existing `external_section_attachment` min/max-diameter evidence contract remains intact. If any legacy diameter-envelope claim is present, the old complete source-local envelope compiler remains authoritative; a partial legacy envelope cannot be bypassed by a generic dimension claim.

See `feature-bound-dimensional-eligibility.md`.

### Anchor-side installation

The current manufacturer-neutral anchor path remains:

```text
PrimaryAnchorFeature
  -> AnchorAttachment installation eligibility
  -> exact AnchorInstallationBinding
  -> installed AnchorAttachment tether-side interface
  -> ordinary tether-endpoint compatibility
```

Current proven primary-anchor feature vocabulary:

```text
belt
beam
rail
wrist
bucket_lip
```

Current proven installation-method vocabulary:

```text
wrap
cinch
thread_over
fasten_around
hook_on
```

Every eligibility path evaluates against one concrete `PrimaryAnchorFeature`. Installation eligibility remains separate from tether-to-anchor interface compatibility.

### Connection, evaluation and selection boundaries

Connection compatibility remains unchanged by PR #64.

Candidate generation owns structurally admissible path construction and candidate identity. Hard candidate evaluation remains the authority on viability. Ranking never overrides a hard failure. Selection operates only over the evaluated candidate set, and global exhaustion may be concluded only after all generated alternatives have been evaluated.

PR #64 does not alter any of those layers.

## PR #64 vertical proof

The V5 C cases independently exposed the same compiler seam and are both covered vertically through ordinary manufacturer adapters, accepted claims, claim resolution and runtime eligibility.

### FallTech 5401A1 Battery Boot

The exact product page establishes a maximum external battery geometry of:

```text
3.5 in length
2.75 in width
2.5 in height
```

Those become three `lte` predicates on one selected `external_section` feature. The test proves that separate features cannot donate different passing dimensions to manufacture eligibility. The provided D-ring remains a separate tether-side interface.

### Ergodyne Squids 3745 / item 19747 Tool Grip

The exact product page establishes:

```text
handle diameter >= 1.0 in
handle diameter <= 1.28 in
handle height <= 4.5 in
```

Those predicates remain bound to one selected handle. Current family instructions state a different height limit, so the vertical deliberately stays source-local to the exact product-page evidence used by the frozen V5 classification instead of synthesizing the sources.

### Regression guardrails

Focused tests also prove:

- equivalent source-local profiles across unit representations;
- rejection of bounds split across sources;
- rejection of missing comparison direction;
- rejection of multiple same-kind fit subjects; and
- preservation of the legacy external-section incomplete-envelope failure.

The existing external-section diameter-fit suite remains the regression authority for that older evidence shape.

## Portability V6 and the pivot decision

V6 was deliberately selected from a materially different region after the PR #64 semantic implementation was frozen: three conventional tethers, two conventional ToolAttachments, one conventional AnchorAttachment and two composite/system-like commercial products across seven manufacturers.

Its reviewed result is:

```text
V6  1 A / 7 B / 0 C / 0 D
```

This is the first portability cohort with an A case and the first with no C pressure.

The A case is Hilti 2261970, which already fits the registered production adapter unchanged.

The seven B cases require catalogue acquisition/extraction, evidence reconciliation or assembly/relationship composition, but no new recommendation primitive:

```text
Dropsafe S017001101201
Guardian / Ty-Flot CC2072
3M 1500009
FallTech 5106A5
Ergodyne Squids 3172 / 19172
GRIPPS H01088
Guardian / Ty-Flot QSS-R
```

Two points are important:

- GRIPPS H01088 is explicitly a sellable kit containing a separately identified tether and wrist anchor. The kit wrapper is catalogue composition evidence, not a new load-path component type.
- Guardian QSS-R has real proprietary continuous-tie-off transfer behavior, but baseline recommendation viability does not yet need a handoff state machine. Preserve that behavior as evidence and introduce stateful transfer reasoning only if a demand-side requirement actually needs it.

See `portability-v6-post-feature-dimensional.md` and `benchmarks/cross_vendor_portability_v6.json` for the full frozen audit.

## Development-centre decision

After PR #64, **do not immediately run another fresh portability cohort as the primary workstream**.

The architecture-discovery sequence has produced the signal we were waiting for: after closing the recurring V5 seam, a materially different sample contains no C or D cases. Continuing to hunt catalogue breadth for another missing primitive is now likely to have lower MVP value than exercising the system from the field/user side.

Portability should become a **periodic stress/regression audit** after meaningful core changes or after enough new catalogue breadth has accumulated to make another blind sample informative.

The primary workstream should now be:

```text
catalogue throughput
+
demand-side MVP
```

These two streams should advance together rather than as separate phases.

## Next highest-value workstream

Start from the worker's problem and drive the existing recommendation engine through a real demand-side orchestration path.

The first demand-side slice should establish the smallest field workflow that can:

1. accept a tool observation/input;
2. resolve it to an exact or sufficiently specific catalogue `Tool`, or fall back explicitly to a session-local generic tool profile;
3. determine the operational configuration needed for load reasoning, including installed battery where applicable;
4. obtain only the missing physical/interface facts and task context required by the current rules;
5. call the existing candidate generation -> hard evaluation -> ranking/selection pipeline without bypasses;
6. present a field-usable recommendation with the selected attachment/tether/anchor path, required installation action, important verification/cautions and evidence limitations; and
7. fail gracefully when the catalogue/evidence is not ready rather than inventing a recommendation.

In parallel, increase catalogue throughput specifically in support of that demand-side path. Prioritize records that unlock realistic field scenarios and improve manufacturer/family coverage; do not broaden the core merely because a new SKU uses unfamiliar marketing language.

High-value throughput work now includes:

- reusable source discovery/acquisition for manufacturer families;
- exact identity and variant binding;
- conflict/readiness handling for contradictory first-party facts;
- product-family adapter broadening;
- decomposition of sellable kits into recommendation components; and
- efficient ingestion of the tool/configuration facts required by real recommendation sessions.

## Guardrails that must remain true

- Do not introduce manufacturer/SKU branches downstream of ingestion/resolution unless no reusable semantic representation exists and the exception is explicitly justified.
- Missing evidence fails closed; do not infer geometry, direction, compatibility, capacity or installation suitability from absence of contrary evidence.
- Do not convert qualitative words such as `small`, `adjustable`, `all sizes`, `UniFit` or nominal product labels into numeric fit envelopes.
- Compile numeric feature predicates only from accepted source evidence that explicitly establishes the dimension and comparison/bound.
- Keep every feature-bound predicate on one concrete feature instance.
- Do not synthesize fit envelopes by joining bounds from unrelated subjects or incomplete evidence sources.
- Keep manufacturer provenance separate from exact product/variant identity.
- Bound flattened multi-product evidence to the requested identity before parsing sibling-specific fields.
- Preserve candidate identity and exact provenance through generation/evaluation; do not reconstruct safety-relevant facts from human-readable reason text.
- Keep hard viability separate from ranking/context.
- Preserve V1-V6 historical portability cohorts and the immutable Batch 2 blind baseline.
- Prefer a small reusable primitive only when a concrete recurring decision need exists; do not pre-build ontology for optional product behavior.

## Suggested next-chat starting point

> Continue TetherLens from PR #64 after the generic feature-bound ToolAttachment dimensional-eligibility compiler and V6 portability audit. Keep V1 **0 A / 5 B / 3 C / 0 D**, V2 **0 A / 6 B / 2 C / 0 D**, V3 **0 A / 5 B / 3 C / 0 D**, V4 **0 A / 4 B / 4 C / 0 D**, V5 **0 A / 6 B / 2 C / 0 D** and V6 **1 A / 7 B / 0 C / 0 D** frozen at their historical semantic revisions. V6 is the pivot signal: portability is now a periodic stress test, not the primary implementation loop. Start the demand-side MVP from the worker's field workflow while increasing catalogue throughput in support of concrete end-to-end recommendation scenarios. First inspect the existing recommendation-session/run orchestration, tool-resolution model, current catalogue/ingestion entry points and MVP docs, then define the smallest vertical from field tool input -> resolved tool/configuration -> targeted missing-fact/context capture -> existing candidate generation/evaluation/selection -> field-usable recommendation, with explicit graceful fallback when evidence is insufficient.
