# TetherLens Project Status

_Last updated: 2026-09-16_

This is the operational handoff for the current TetherLens knowledge/recommendation stack and the immediate MVP work sequence. Durable design detail lives in the dedicated documents; this file stays focused on the current semantic baseline, invariants that must not regress, and the next highest-value work.

For detailed design, see `product-vision.md`, `mvp.md`, `domain-model.md`, `evidence-model.md`, `architecture.md`, `ingestion.md`, `technical-schema.md`, `recommendation-engine.md`, `connection-compatibility.md`, `anchor-interface-form.md`, `anchor-installation-binding.md`, `tool-attachment-compatibility.md`, `feature-bound-dimensional-eligibility.md`, `attachment-method-vocabulary.md`, `candidate-ranking-selection.md`, `recommendation-run.md`, `recommendation-session.md`, `demand-side-field-orchestration.md`, `recommendation-benchmark.md`, `portability-benchmark.md`, `portability-v5-post-pr62.md`, `portability-v6-post-feature-dimensional.md`, `benchmark-goals.md`, and `adapter-review-guidance.md`.

## Current baseline

PR #66, `Retain ToolAttachment installation method through field selection`, is merged. Current `main` is:

```text
a0e062df317e2de8e89d80c8b11f2db9846ee088
```

PR #67, `Add advisory field Tool catalogue search`, is the current proposed demand-side slice on branch:

```text
feature/field-tool-candidate-search
```

PR #67 is intentionally a narrow recognition/search-boundary implementation. It does not rewrite historical portability semantics, Tool confirmation authority, candidate identity, attachment eligibility, connection compatibility, hard evaluation, operational-profile semantics, or ranking.

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

V6 remains the pivot signal: a materially different portability cohort produced one A case, seven B cases and no C/D pressure after the reusable feature-bound dimensional compiler landed.

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

The reusable path remains:

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

## PR #65: demand-side field coordinator

The field coordinator provides the typed worker-facing boundary above the existing recommendation engine.

It supports:

- advisory recognition/search candidate Tool refs;
- mandatory explicit worker Tool confirmation;
- exact operational-profile selection where several profiles exist;
- automatic selection when exactly one profile exists;
- installed configuration identity such as Battery refs;
- fail-closed missing operational mass;
- explicit session-local generic profile fallback; and
- exact handoff of the normalized Tool plus all supplied tether, ToolAttachment and anchor alternatives to `run_recommendation()`.

The coordinator adds no compatibility, installation, hard-evaluation, ranking or selection rules.

The field result preserves the existing distinction between:

```text
selected
no_generated_candidates
no_suitable_recommendation
```

and retains exact run/profile/configuration provenance, generation-time Tool-side bindings, exact hard/contextual evaluation, pending verification checks and pending pre-use actions.

## PR #66: ToolAttachment installation-method retention

PR #66 closes the next field-output provenance gap without turning method metadata into a new compatibility rule.

Accepted ToolAttachment `attachment_method_code` claims now resolve into:

```text
ToolAttachmentInstallationMethod
  source_product_ref
  attachment_method_code
  source_urls
```

Resolution is fail-closed:

- only accepted/reconciled method claims participate;
- values must be native non-empty strings;
- conflicting accepted method codes do not receive an invented precedence; and
- exact accepted source URLs are retained.

A `ToolAttachmentAssemblyOption` may carry this method only when its provenance belongs to a selected assembly component. Candidate generation deep-copies the exact method onto the corresponding `CandidatePathSelection`.

The method remains **descriptive retained installation provenance**. It does not change:

- ToolAttachment eligibility;
- direct or ToolAttachment-mediated connection compatibility;
- load/capacity evaluation;
- hard viability;
- contextual ranking;
- candidate identity; or
- legacy/runtime assembly validity when method provenance is absent.

The field-facing result can therefore expose a canonical physical installation action such as `cinch` or `wrap` from retained runtime provenance instead of reconstructing it from product names, selected feature IDs or human-readable reason strings.

## PR #66 catalogue-backed worker vertical

PR #66 also proves the field path with a real catalogue-backed scenario rather than a synthetic SKU-pair rule.

The vertical uses:

- Milwaukee `48-22-7215` as the Tool;
- NLG `101363` as the ToolAttachment;
- GRIPPS `H01079` as the Tether; and
- NLG `101366` as the anchor path.

The worker must still explicitly confirm the Tool. The selected path retains the NLG ToolAttachment's canonical `cinch` method provenance while unresolved connection compatibility remains visible as verification work rather than being guessed.

This scenario demonstrates that the field coordinator can now preserve both **where/how the ToolAttachment binds** and **the accepted physical installation mechanism** through the selected recommendation path.

## PR #66 targeted Milwaukee throughput

Milwaukee ingestion now recognizes explicit first-party:

```text
tether-ready lanyard hole
tether-ready handle loop
```

as one manufacturer-neutral captive `through_opening` Tool tether interface.

Important boundaries:

- this extraction is Tool-only;
- generic handle language does not create tether-interface evidence;
- the exact-SKU Milwaukee product page must be verified;
- the tether-ready phrase is scoped to the selected product record rather than searched page-wide; and
- repeated occurrences of the selected SKU remain inside the same selected record while the first different recognized SKU terminates it.

The last rule is implemented in the shared `bounded_record_for_identifier()` invariant because repeated title/heading identifiers and cross-record evidence leakage are source-independent parsing concerns. Milwaukee's SKU grammar remains adapter-specific.

## PR #66 NLG method canonicalization hardening

NLG attachment-method extraction now treats explicit positive cinch/choke instructions as stronger evidence than incidental pass-through plus later `secure` wording. This is required for real instructions that pass a loop through a captive feature before creating the constricting cinch.

Negative wording remains non-evidence. Prohibitions such as:

```text
Do not create a cinch.
Do not use the loop to create a cinch.
Never use it to cinch around the handle.
```

must not emit or outrank `cinch`.

Negation handling is clause-local and bounded by punctuation/explicit contrast so a prohibition does not suppress a separate positive instruction. Retained cinch evidence uses the same positive-only view.

## Review-derived reusable ingestion invariants

PR #66 review reinforced two reusable rules:

1. **Page identity is not fact attribution.** Verifying that a page belongs to SKU A does not allow every phrase on the page to be assigned to SKU A; related-product content must remain out of the selected record.
2. **Repeated selected identifiers are not neighboring records.** A flattened page may repeat its selected SKU in title/heading content; the selected record ends at the first different recognized identifier, not the next occurrence of the same identifier.

These rules belong in shared ingestion behavior where safe; source-specific SKU grammars and wording stay in adapters.

## PR #67: advisory Tool catalogue search

PR #67 supplies the first real producer of `candidate_tool_refs` without changing who is allowed to confirm Tool identity.

The producer is:

```text
candidate_tool_refs_from_text_search(query, catalogue, max_candidates=5)
```

It searches only the normalized Tool entries already present in the supplied `FieldRecommendationCatalogue`.

Current semantics are deliberately modest:

- search surface = exact `tool_ref` + worker-facing `display_name`;
- matching = case-insensitive alphanumeric token containment;
- punctuation/separator variation is normalized;
- every query token must match;
- partial identifier tokens, edit-distance/fuzzy matching and semantic expansion are not used;
- catalogue order is retained rather than inventing a confidence ranking; and
- results are bounded to a short list.

The function returns refs only. It cannot set `confirmed_tool_ref`, choose an `OperationalToolProfile`, or invoke `run_recommendation()`.

Therefore even a single exact SKU result still produces:

```text
candidate_tool_refs
  -> TOOL_CONFIRMATION
  -> explicit confirmed_tool_ref
  -> operational-profile resolution
  -> recommendation run
```

The catalogue-backed Milwaukee/NLG/GRIPPS/NLG worker vertical now starts from this real search producer rather than a hand-injected Milwaukee candidate ref, while retaining the same mandatory confirmation boundary and downstream recommendation semantics.

## Current deliberate boundaries

The merged baseline plus PR #67 do **not** add:

- image recognition or computer-vision inference;
- fuzzy Tool identity acceptance;
- search-derived confidence scores as recommendation authority;
- persistent database/repository querying;
- automatic Battery recognition;
- free-form worker safety-fact inference;
- anchorage recognition;
- inventory optimization;
- user-facing natural-language recommendation generation;
- new attachment eligibility predicates;
- new connection compatibility rules;
- new contextual/ranking rules;
- SKU-pair recommendation logic; or
- a replacement for the existing recommendation-session condition resolver.

Those boundaries remain deliberate.

## Next highest-value demand-side seam

Once PR #67 is stable, candidate Tool discovery is no longer purely hand-injected. The next demand-side value should come from **another real field scenario that adds useful catalogue/profile coverage and forces only the smallest missing worker-context question**, rather than from broadening recognition authority.

Good next candidates should preserve:

- advisory-only discovery plus explicit Tool confirmation;
- exact Tool/variant identity;
- evidence-backed operational-profile mass/configuration;
- the unchanged complete recommendation pipeline; and
- context questions only where they can materially affect candidate feasibility, ranking or worker instructions.

Image recognition can later produce the same `candidate_tool_refs` contract when a curated pilot image set is ready. It should not bypass the confirmation boundary.

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

The Milwaukee `48-22-7215` page currently publishes `Weight 2.85 lb`, but the existing Milwaukee adapter intentionally accepts more specific Tool-mass labels on this path. Do not broaden generic `Weight` into `tool_body_mass_kg` merely to remove the vertical's accepted normalized mass fixture; that could weaken configuration-dependent mass semantics on other Tools. Treat this as a catalogue-readiness/evidence-modelling question, not a recognition concern.

V6 B cases are useful throughput candidates, but they should not drive new recommendation primitives unless implementation reveals a genuine reusable decision gap.

## Guardrails that must remain true

- Do not introduce manufacturer/SKU branches downstream of ingestion/resolution unless no reusable semantic representation exists and the exception is explicitly justified.
- Missing evidence fails closed; do not infer geometry, direction, compatibility, capacity or installation suitability from absence of contrary evidence.
- Do not convert qualitative marketing language into numeric fit envelopes.
- Compile numeric feature predicates only from accepted source evidence that explicitly establishes the dimension, declared-constraint semantics and comparison/bound.
- Keep every feature-bound predicate on one concrete feature instance.
- Do not synthesize fit envelopes by joining bounds from unrelated subjects or incomplete evidence sources.
- Keep manufacturer provenance separate from exact product/variant identity.
- Bound flattened multi-product evidence to the requested identity before parsing sibling-specific fields; repeated selected identifiers remain part of the same record until a different recognized identifier appears.
- Respect negative installation wording; prohibitions are not positive method evidence.
- Preserve candidate identity and exact provenance through generation/evaluation.
- Preserve generation-time Tool-side bindings independently of reconstructed Tool state.
- Preserve operational profile/configuration identity independently of the normalized Tool used by the recommendation core.
- Preserve ToolAttachment installation-method provenance independently of eligibility and candidate identity.
- Recognition/search candidates are advisory only; no search/recognition producer may silently populate authoritative Tool confirmation.
- Do not reconstruct safety-relevant facts or installation actions from human-readable reason text.
- Keep hard viability separate from ranking/context.
- Preserve V1-V6 historical portability cohorts and the immutable Batch 2 blind baseline.
- Prefer a small reusable primitive only when a concrete recurring decision need exists; do not pre-build ontology for optional product behavior.

## Suggested next-chat starting point

> Continue TetherLens from merged PR #67. Keep V1 **0 A / 5 B / 3 C / 0 D**, V2 **0 A / 6 B / 2 C / 0 D**, V3 **0 A / 5 B / 3 C / 0 D**, V4 **0 A / 4 B / 4 C / 0 D**, V5 **0 A / 6 B / 2 C / 0 D** and V6 **1 A / 7 B / 0 C / 0 D** frozen at their historical semantic revisions. Portability remains a periodic stress test rather than the primary implementation loop. PR #65 established explicit Tool confirmation, operational-profile/configuration provenance and the field recommendation coordinator. PR #66 retained accepted ToolAttachment installation-method provenance through `ToolAttachmentAssemblyOption` and the exact selected `CandidatePathSelection`, proved it in a catalogue-backed worker vertical, added scoped Milwaukee tether-ready Tool-feature ingestion, and hardened shared record scoping plus positive-only NLG cinch evidence. PR #67 adds deterministic lexical catalogue search as the first real producer of advisory `candidate_tool_refs`; even one exact result still requires explicit worker confirmation before Tool/profile resolution or recommendation. Continue targeted catalogue throughput and choose the next real field scenario that adds operational-profile coverage plus only the smallest context question needed to change feasibility/ranking/instructions, without broadening recognition authority or inventing new recommendation primitives prematurely.
