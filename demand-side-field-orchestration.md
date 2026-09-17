# Demand-Side Field Recommendation Orchestration

## Purpose

This document defines the first executable worker-facing vertical above the existing recommendation engine.

The layer does **not** add another compatibility, generation, hard-evaluation, ranking or fallback model. Its responsibility is narrower:

```text
recognition/search candidate refs
        ↓
explicit worker confirmation
        ↓
exact operational profile resolution
        ↓
existing complete recommendation run
        ↓
structured field-facing projection of the selected path
```

The executable entry point is:

```python
run_field_recommendation(
    observation,
    catalogue,
    *,
    product_runtime_state=None,
    connection_contexts=None,
    policy_contexts=None,
    ranking_context=None,
)
```

Once Tool/profile resolution succeeds, the function calls the existing `run_recommendation()` boundary with the supplied normalized alternatives unchanged.

## Why this is the first demand-side slice

The reusable core model is already able to:

- construct direct and ToolAttachment-mediated candidates;
- preserve selected feature, endpoint, component and anchor-path identity;
- evaluate hard compatibility, capacity, installation constraints and policy;
- rank complete viable candidate sets under explicit context;
- retain pending runtime verification and pre-use actions; and
- resolve those pending conditions downstream through the existing recommendation-session layer.

The missing MVP seam was therefore not another compatibility primitive. It was the worker-side coordination required to establish which Tool/configuration the engine is evaluating and to expose the selected result without bypassing those completed layers.

This slice deliberately stops short of image recognition itself. Recognition is treated as an upstream producer of candidate Tool refs so computer-vision implementation can evolve independently of recommendation semantics.

## Tool observation and confirmation

`FieldToolObservation` accepts:

```text
candidate_tool_refs
confirmed_tool_ref
selected_operational_profile_ref
generic_profile
```

Recognition/search candidates are advisory only.

A candidate ref never becomes the resolved Tool merely because it is the only recognition result. If no `confirmed_tool_ref` is supplied, the coordinator returns a `tool_confirmation` input requirement containing the recognized catalogue candidates.

If there are no recognition/search candidates, the result instead requests `tool_identification`. The demand layer does not invent an identity from incomplete observation data.

A recognized or confirmed ref that is absent from the supplied normalized catalogue produces an explicit `not_ready` result rather than being silently discarded or widened to a similar Tool.

## Advisory catalogue text search

The first real producer of `candidate_tool_refs` is deliberately small:

```python
candidate_tool_refs_from_text_search(
    query,
    catalogue,
    *,
    max_candidates=5,
)
```

It searches only the Tool identities already present in the supplied `FieldRecommendationCatalogue`. The searchable surface is the exact `tool_ref` plus worker-facing `display_name`.

Matching is deterministic lexical matching rather than identity inference:

- input is Unicode NFKC-normalized and case-folded;
- Unicode letters, numbers and their combining marks stay inside identity tokens, while punctuation and separators form boundaries;
- every query token must occur in the Tool's searchable identity text;
- partial identifier tokens, edit-distance matches and semantic expansion are not used;
- catalogue order is preserved rather than inventing a recognition-confidence score; and
- the returned shortlist is bounded by `max_candidates`.

The producer returns refs only. It cannot set `confirmed_tool_ref`, select an operational profile, or invoke recommendation logic.

This means a one-item search result still flows through:

```text
candidate_tool_refs=[...]
        ↓
tool_confirmation
        ↓
worker supplies confirmed_tool_ref
```

A zero-result search remains ordinary `tool_identification`; it is not widened to a similar SKU. Future image recognition can replace or complement this lexical producer while retaining the same advisory contract.

## Operational profile resolution

The recommendation engine consumes operational object mass through `ResolvedToolCandidate.object_mass_kg`.

The demand layer wraps those already-normalized Tool facts in `OperationalToolProfile`:

```text
profile_ref
profile display name
ResolvedToolCandidate
configuration_product_refs
```

`configuration_product_refs` retain supporting configuration identity such as an installed Battery. They are not load-bearing tethering components and do not enter candidate topology.

### Catalogue-backed profile materialization

Accepted operational-mass evidence can now be materialized into field profiles through:

```python
resolve_operational_tool_profiles(
    claims,
    *,
    tool_ref,
    descriptors,
    features=None,
    direct_interfaces=None,
)
```

Each `OperationalProfileDescriptor` supplies the exact normalized configuration identity already established by the catalogue layer:

```text
profile_ref
worker-facing display_name
configuration_product_refs
```

The descriptor is intentionally separate from Claim resolution. The resolver does not infer Battery/configuration identity by parsing a compound profile ref, matching arithmetic mass combinations, joining source URLs, using manufacturer/SKU conventions, or widening a platform label. Configuration identity and relationship validity must already have been established upstream.

The resolver binds only accepted `operational_mass_kg` Claims whose subject is the exact descriptor `profile_ref`. An operational-mass Claim without a corresponding descriptor fails closed, as do conflicting accepted masses for the same profile.

A known descriptor whose operational mass is still missing is **not dropped**. It becomes an `OperationalToolProfile` with unknown mass so the worker can still select the actual configuration; selecting that profile then reaches the existing `operational_mass_not_established` readiness boundary before candidate generation. This prevents an incomplete multi-configuration Tool from silently collapsing into one apparently selectable profile merely because only one configuration currently has complete mass evidence.

The first catalogue-backed proof uses Hilti SF 4-22 `2253847` with the already-ingested B 22-55 and B 22-85 operational-mass Claims. Advisory text search still stops at explicit Tool confirmation; confirmation then exposes both real Battery profiles through the existing `operational_profile_selection` requirement, and the selected profile retains its exact configured mass and configuration-product identity.

This profile materialization step does not itself make the Hilti Tool recommendation-ready. The manufacturer-required retaining strap/tether installation path remains a separate supply-side normalization task; the field layer does not turn that exact pairing into SKU-based candidate logic.

### One profile

If a confirmed Tool has exactly one operational profile, it is selected automatically. No redundant worker question is introduced.

### Multiple profiles

If several profiles are available and none is selected, the coordinator returns one targeted `operational_profile_selection` requirement containing exactly those alternatives.

It never chooses one Battery/profile because it is first in a list, lighter, more common, or otherwise convenient.

### No profile

A confirmed Tool with no resolved operational profile returns `not_ready`.

### Missing operational mass

A selected profile whose `ResolvedToolCandidate.object_mass_kg` is unknown also returns `not_ready` **before candidate generation**.

This is intentional. The field layer must not enter load reasoning with an unknown operational mass and must not substitute bare-tool mass for a Tool/configuration that requires an installed profile.

The coordinator does not itself decide what catalogue evidence is acceptable for Tool or Battery mass. Evidence acceptance and configuration-relationship validation remain upstream catalogue responsibilities.

## Session-local generic fallback

The field workflow may receive an explicit `generic_profile` when the worker's Tool cannot be resolved to a catalogue identity.

This is a session-local fallback, not a new catalogue record and not a fuzzy match to a similar SKU.

It uses the same `OperationalToolProfile` shape so the recommendation engine receives normalized mass/features/interfaces through an ordinary `ResolvedToolCandidate`.

The result records:

```text
source = session_local_generic
```

rather than pretending that the Tool was catalogue-resolved.

A generic profile is still subject to the same operational-mass requirement. This slice does not invite the worker to enter an unverified guessed weight and does not promote session-local facts into catalogue evidence.

## Complete recommendation-run handoff

After Tool/profile resolution, `run_field_recommendation()` passes the catalogue slice to `run_recommendation()`:

```text
resolved operational Tool
all supplied Tether options
all supplied AnchorPath options
all supplied ToolAttachment assemblies
runtime product facts
connection contexts
policy contexts
ranking context
```

The field layer does not:

- pre-evaluate candidates;
- suppress a Tether because another looks better;
- hand-select one candidate for evaluation;
- reimplement attachment eligibility;
- reimplement connection compatibility;
- reimplement load capacity;
- reimplement contextual feasibility;
- rank alternatives itself; or
- convert orchestration errors into recommendation exhaustion.

The complete-set guarantee therefore remains the one already enforced by `RecommendationRunResult`.

The field result retains the exact originating `RecommendationRunResult` for audit and later session-condition resolution.

## Field result states

`FieldRecommendationState` contains five states:

```text
needs_input
not_ready
selected
no_generated_candidates
no_suitable_recommendation
```

The first two occur before the recommendation run.

The final three map exactly from `CandidateSelectionState` after a complete run:

```text
selected                   -> selected
no_generated_candidates    -> no_generated_candidates
no_suitable_recommendation -> no_suitable_recommendation
```

`no_generated_candidates` is intentionally not collapsed into `no_suitable_recommendation`.

Likewise, a missing Tool/profile/mass is not reported as either recommendation outcome because no complete recommendation run has occurred yet.

## Structured selected recommendation

For a selected run, `FieldRecommendationSummary` exposes:

- the exact operational profile ref and label;
- the exact operational mass used by load reasoning;
- supporting configuration-product refs, such as the selected Battery;
- the exact retained `CandidatePathSelection`;
- the exact retained `CandidateEvaluation`;
- the selected candidate's contextual evaluation when one exists;
- complete pending verification `CandidateCheck` objects; and
- complete pending pre-use-action `CandidateCheck` objects.

The path selection carries the selected:

- Tool ref;
- Tether ref;
- ToolAttachment assembly and installation feature where applicable;
- retained ToolAttachment installation method provenance where available;
- anchor path;
- primary-anchor installation binding where applicable;
- endpoint/target assignments;
- component/source-product identities; and
- retained eligibility/assignment proofs.

The field projection does not parse human-readable `reason` strings to infer new safety facts, installation actions or terminal outcomes.

Pending verification/action checks are selected only by the structured pending identifiers already emitted by the hard evaluator.

A result validator recomputes the field summary from the retained operational profile and retained selected run. A directly constructed/deserialized result therefore cannot silently swap the displayed path, evaluation or pending-condition projection.

## ToolAttachment installation-method provenance

Where accepted ToolAttachment evidence resolves an `attachment_method_code`, the normalized assembly may carry a `ToolAttachmentInstallationMethod` containing:

```text
source_product_ref
attachment_method_code
source_urls
```

Candidate generation copies that exact provenance onto the selected `CandidatePathSelection` for a ToolAttachment-mediated path.

This is a descriptive retained installation fact, not a new compatibility or eligibility rule. It therefore does not change whether a candidate is generated, hard-viable, ranked, or selected. Candidate identity also remains stable with or without method metadata.

The field layer consumes the retained path as-is. It must not infer `cinch`, `wrap`, `adhesive`, `mechanical_capture`, `through_feature`, or another method from product names, selected feature IDs or evaluator reason strings.

Missing method provenance remains explicit: legacy/runtime assemblies may still be usable under existing eligibility semantics even when no accepted installation-method claim is available.

## Relationship to recommendation sessions

This layer does not replace `recommendation_session.py`.

If the selected candidate contains pending runtime verification or pre-use actions, the field summary exposes those exact pending checks. The unchanged `RecommendationRunResult` can then become the input to the existing session resolver.

That resolver remains authoritative for:

- evidence-backed terminal condition resolution;
- candidate-local failure;
- lazy fallback to the next originally ranked candidate; and
- session-local exhaustion.

The field coordinator must not mark a pending check satisfied or failed directly.

## Current deliberate boundaries

The field layer does not add:

- image recognition or model inference;
- fuzzy Tool/SKU matching;
- a persistent catalogue/database repository;
- automatic Battery recognition;
- evidence acceptance or configuration-relationship inference from raw Claims/source URLs;
- free-form worker entry of safety-relevant mass/geometry facts;
- anchorage recognition;
- inventory/availability selection;
- user-facing prose generation;
- session persistence;
- new contextual preference families;
- new compatibility rules; or
- SKU-pair recommendation logic.

`FieldRecommendationCatalogue` is intentionally an in-memory normalized slice. Retrieval/persistence can be added later without changing the recommendation engine boundary.

## Test expectations

Focused tests cover at least:

- deterministic lexical Tool search producing only refs from the supplied catalogue;
- Unicode-safe tokenization retaining non-ASCII letters and combining marks while preserving distinct identities;
- punctuation/case normalization without fuzzy or prefix identity matching;
- bounded multi-match shortlists preserving catalogue order rather than invented confidence;
- a one-item search result still requiring explicit worker Tool confirmation;
- catalogue-backed operational-mass Claims materializing only against exact normalized profile descriptors;
- operational-mass evidence without configuration identity failing closed rather than having identity reconstructed from profile strings/URLs/mass arithmetic;
- known configurations with missing operational mass remaining visible and failing closed when selected;
- conflicting accepted operational masses not receiving an invented precedence;
- one operational profile being used without an unnecessary extra question;
- multiple operational profiles requiring explicit selection;
- selected Battery/profile mass actually driving load evaluation;
- no bare-tool/missing-mass fallback;
- session-local generic profile use remaining explicit;
- the complete supplied candidate set reaching `run_recommendation()`;
- exact selected path/evaluation retention in the field summary;
- retained ToolAttachment installation method on the exact selected path where accepted provenance exists;
- pending structured verification retention;
- `no_generated_candidates` remaining distinct from global `no_suitable_recommendation`; and
- pre-run not-ready states never masquerading as recommendation outcomes.

The catalogue-backed Milwaukee/NLG/GRIPPS/NLG worker vertical still proves the complete recommendation handoff. It begins from real text search, stops at explicit Tool confirmation, retains the exact `cinch` provenance of the selected NLG ToolAttachment and leaves unresolved connection checks visible rather than inventing compatibility evidence.

The Hilti SF 4-22 profile vertical separately proves that real catalogue-backed configuration choices can now reach the existing worker profile-selection boundary without weakening that recommendation pipeline or pretending the still-incomplete retaining-strap path is ready.

## Next demand-side steps

After this boundary is stable, the next useful demand-side work should continue from real field scenarios rather than another broad modelling pass. Likely extensions are:

1. normalize the smallest reusable Hilti retaining-strap/tool-interface path needed to carry the SF 4-22 selected profile into a complete recommendation run, without converting the manufacturer-required 2293133 + 2261970 pairing into SKU-pair recommendation logic;
2. apply the same profile materialization boundary to additional real configuration-dependent Tools as catalogue relationships become recommendation-ready;
3. add the smallest task/anchorage question flow needed by those scenarios;
4. pass pending checks into the existing recommendation-session evidence adapters;
5. introduce image-recognition candidates behind the same advisory `candidate_tool_refs` boundary when a curated pilot image set is ready; and
6. build a thin mobile result presentation over the structured field summary.

Catalogue-ingestion work should continue in parallel, especially where a real field scenario exposes missing normalized Tool/Tether/ToolAttachment/AnchorAttachment facts. Searchability and profile materialization are not substitutes for recommendation readiness: a Tool may be discoverable and its installed mass known before its required physical tethering path is complete, and the system must continue to fail closed at the existing readiness boundaries.