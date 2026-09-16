# TetherLens Project Status

_Last updated: 2026-09-16_

This is the operational handoff for the current TetherLens knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file stays focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `tool-attachment-compatibility.md`, `feature-bound-dimensional-eligibility.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `demand-side-field-orchestration.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `portability-v5-post-pr62.md`, `portability-v6-post-feature-dimensional.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Current baseline

PR #64, `Compile feature-bound ToolAttachment dimensional eligibility`, is merged. Post-PR64 `main` is:

```text
355a56229d2738c320f26627d06bb1dbbdd5f4e2
```

PR #65, `Add first demand-side field recommendation orchestration`, is the current semantic baseline on branch:

```text
feature/demand-side-field-orchestration
```

This handoff describes the state intended to become the new `main` baseline when PR #65 is merged. Use PR #65 itself as the unit of provenance rather than relying on a transient pre-merge head SHA.

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

## Strategic direction

V6 remains the pivot signal. A materially different portability cohort produced one A case, seven B cases and no C/D pressure after the reusable feature-bound dimensional compiler landed.

Therefore:

- portability is now a periodic stress/regression audit, not the primary implementation loop;
- the primary workstreams are **catalogue throughput + demand-side MVP**;
- new ontology should be introduced only when a concrete recurring decision need proves it necessary.

Do not start another portability cohort merely to search for a new primitive.

## Current recommendation architecture

The recommendation core remains a reusable evidence-bound pipeline:

```text
normalized Tool / ToolAttachment / tether / anchor facts
  -> candidate generation
  -> hard candidate evaluation
  -> contextual ranking/selection
  -> recommendation-session condition resolution where needed
```

Hard viability and ranking remain separate. Ranking cannot override hard incompatibility or missing required evidence. Global exhaustion may be concluded only after the complete generated alternative set has been evaluated.

### Tool-side installation

A ToolAttachment eligibility path binds one concrete `ToolInterfaceFeature`. Feature kind, captive state, dimensions, attributes and other feature-local predicates in that path must all be satisfied by the same feature instance.

PR #64 added manufacturer-neutral compilation of accepted feature-bound dimensional fit evidence through:

```text
attachment_eligibility.feature_kind
attachment_eligibility.dimension.<code>
```

with explicit ordered comparison direction. Split-source envelope synthesis, conflicting fit subjects and unsupported inference remain fail-closed.

### Anchor-side installation

The current reusable path remains:

```text
PrimaryAnchorFeature
  -> AnchorAttachment installation eligibility
  -> exact AnchorInstallationBinding
  -> installed AnchorAttachment tether-side interface
  -> ordinary tether-endpoint compatibility
```

Current proven primary-anchor feature vocabulary includes:

```text
belt
beam
rail
wrist
bucket_lip
```

Current proven anchor installation methods include:

```text
wrap
cinch
thread_over
fasten_around
hook_on
```

Anchor installation eligibility remains distinct from tether-to-anchor connection compatibility.

## PR #65: first demand-side orchestration slice

PR #65 adds the first typed field-workflow boundary above the existing recommendation engine without weakening or duplicating downstream recommendation logic.

### Tool and operational-profile resolution

`field_recommendation.py` now supports:

- advisory recognition/search candidate Tool refs;
- mandatory explicit worker confirmation before catalogue identity is accepted;
- exact operational-profile selection when more than one profile remains;
- automatic use of the only profile when exactly one exists;
- explicit installed-configuration identity such as Battery refs;
- fail-closed handling when operational mass is not established; and
- an explicit session-local generic profile fallback when catalogue identity is unavailable.

No bare-tool mass fallback is allowed when a selected operational profile is required for load reasoning.

### Existing recommendation pipeline remains authoritative

Once Tool/profile resolution succeeds, the field coordinator passes the exact normalized Tool plus the complete supplied tether, ToolAttachment and anchor alternative sets into `run_recommendation()`.

It does not add new compatibility, installation, hard-evaluation, ranking or selection rules.

The field result preserves the existing distinction between:

```text
selected
no_generated_candidates
no_suitable_recommendation
```

An empty generated set is not rewritten as global exhaustion.

### Structured field result

For a selected candidate, the field projection retains:

- operational profile ref and label;
- operational mass;
- supporting configuration-product refs such as installed Battery identity;
- exact `CandidatePathSelection`;
- exact hard `CandidateEvaluation`;
- selected contextual evaluation where present;
- complete pending verification checks; and
- complete pending pre-use-action checks.

Safety-relevant facts are retained as structured objects. They are not reconstructed by parsing human-readable reason strings.

## PR #65 provenance hardening

Review of PR #65 exposed several reconstruction/deserialization invariants that are now explicit.

### Run Tool provenance

`run_recommendation()` retains the exact normalized `ResolvedToolCandidate` used for generation together with a canonical whole-Tool fingerprint.

Recommendation-run validation binds generated candidates to that retained Tool, including tool identity and operational mass.

### Generation-time Tool-side bindings

The run also retains independent generation-time Tool-side binding snapshots for every generated candidate:

- direct candidates retain the exact normalized Tool `ConnectionInterface` targeted during generation;
- ToolAttachment candidates retain the exact `ToolInterfaceFeature` that satisfied eligibility.

These snapshots are deep-copied generation artifacts, not aliases to the retained Tool object. Replacing a retained Tool with a same-ref/same-mass Tool whose interface geometry or feature dimensions changed therefore cannot preserve an old candidate merely by recomputing the run-level fingerprint.

### Operational-profile/configuration provenance

The field result separately retains the generation-time operational-profile binding because the recommendation core intentionally consumes only the normalized Tool.

That field binding includes:

- resolution source (`catalogue` or `session_local_generic`);
- field Tool display identity;
- operational profile ref;
- operational profile display label; and
- supporting configuration-product refs such as Battery identity.

This closes the case where two operational profiles normalize to identical `ResolvedToolCandidate` values: a reconstructed result cannot relabel a run from one Battery/profile identity to another simply by changing the resolved profile and field summary.

These provenance checks apply to selected, no-suitable and no-generated run states.

## Deliberate non-goals of PR #65

PR #65 does **not** add:

- image recognition or computer-vision inference;
- fuzzy Tool identity acceptance;
- database/repository querying;
- raw-claim evidence acceptance at the field boundary;
- automatic Battery recognition;
- free-form worker safety-fact inference;
- anchorage recognition;
- inventory optimization;
- user-facing natural-language recommendation generation;
- new compatibility/context/ranking rules;
- SKU-pair logic; or
- a replacement for the existing recommendation-session condition resolver.

Those boundaries remain deliberate.

## Next highest-value demand-side seam

The next small reusable gap exposed by the field workflow is **ToolAttachment installation method retention**.

Accepted ToolAttachment evidence already carries canonical `attachment_method_code` values such as:

```text
adhesive
mechanical_capture
cinch
wrap
through_feature
contraction_capture
```

but that accepted method does not yet flow into `ToolAttachmentAssemblyOption` / `CandidatePathSelection`.

As a result, the field result can currently identify the selected ToolAttachment and exact bound Tool feature but cannot reliably state the canonical physical installation action (for example `cinch` or `wrap`) from retained runtime provenance. Do not infer that action from binding names or reason strings.

The next implementation slice should therefore bridge already-accepted/resolved ToolAttachment installation method evidence into the selected runtime path without changing compatibility or eligibility semantics.

Desired constraints for that slice:

- manufacturer-neutral representation;
- exact retained provenance where available;
- no SKU-pair branches;
- no reason-text parsing;
- no widening of current attachment eligibility;
- preserve existing candidate identity unless the method is genuinely part of physical-path identity; and
- prove the result with a direct selected ToolAttachment scenario.

## Next concrete MVP vertical after the method bridge

After installation method is retained end to end, exercise the field coordinator with a real catalogue-backed worker scenario rather than another synthetic portability cohort.

That vertical should bind:

1. one real catalogue Tool;
2. its real operational configuration/Battery profile where relevant;
3. the minimum missing physical/interface facts actually required by current rules;
4. only the task/anchorage context needed for the candidate set;
5. the existing generation -> hard evaluation -> ranking/selection pipeline; and
6. a field-usable structured result with installation action, verification/cautions and evidence limitations.

Recognition/search adaptation should follow once the catalogue-backed profile/context path is real enough to exercise. The field coordinator already treats recognition candidates as advisory and requires confirmation, so recognition can be added without becoming recommendation authority.

## Catalogue throughput in parallel

Continue increasing catalogue coverage specifically to unlock realistic field scenarios and reusable manufacturer/family ingestion, not for breadth alone.

High-value throughput work includes:

- reusable manufacturer-family source discovery/acquisition;
- exact Tool/product/variant identity binding;
- operational Tool/Battery profile construction;
- conflict/readiness handling for contradictory first-party facts;
- product-family adapter broadening;
- decomposition of sellable kits into recommendation components; and
- ingestion of the physical/interface facts actually required by demand-side sessions.

V6 B cases are useful throughput candidates, but they should not drive new recommendation primitives unless implementation reveals a genuine reusable decision gap.

## Guardrails that must remain true

- Do not introduce manufacturer/SKU branches downstream of ingestion/resolution unless no reusable semantic representation exists and the exception is explicitly justified.
- Missing evidence fails closed; do not infer geometry, direction, compatibility, capacity or installation suitability from absence of contrary evidence.
- Do not convert qualitative marketing language into numeric fit envelopes.
- Compile numeric feature predicates only from accepted source evidence that explicitly establishes the dimension, declared-constraint semantics and comparison/bound.
- Keep every feature-bound predicate on one concrete feature instance.
- Do not synthesize fit envelopes by joining bounds from unrelated subjects or incomplete evidence sources.
- Keep manufacturer provenance separate from exact product/variant identity.
- Bound flattened multi-product evidence to the requested identity before parsing sibling-specific fields.
- Preserve candidate identity and exact provenance through generation/evaluation.
- Preserve generation-time Tool-side bindings independently of reconstructed Tool state.
- Preserve operational profile/configuration identity independently of the normalized Tool used by the recommendation core.
- Do not reconstruct safety-relevant facts from human-readable reason text.
- Keep hard viability separate from ranking/context.
- Preserve V1-V6 historical portability cohorts and the immutable Batch 2 blind baseline.
- Prefer a small reusable primitive only when a concrete recurring decision need exists; do not pre-build ontology for optional product behavior.

## Suggested next-chat starting point

> Continue TetherLens from merged PR #65. Keep V1 **0 A / 5 B / 3 C / 0 D**, V2 **0 A / 6 B / 2 C / 0 D**, V3 **0 A / 5 B / 3 C / 0 D**, V4 **0 A / 4 B / 4 C / 0 D**, V5 **0 A / 6 B / 2 C / 0 D** and V6 **1 A / 7 B / 0 C / 0 D** frozen at their historical semantic revisions. Portability is now a periodic stress test rather than the primary implementation loop. PR #65 adds the first demand-side field coordinator with explicit Tool confirmation, operational-profile/Battery identity, fail-closed operational mass, exact recommendation-run retention, generation-time Tool-side provenance and independent field profile/configuration provenance. Inspect the accepted ToolAttachment `attachment_method_code` flow and bridge that canonical installation method into the runtime ToolAttachment assembly/selected path without changing eligibility or compatibility semantics; then use the resulting path in a real catalogue-backed worker scenario while continuing targeted catalogue throughput.
