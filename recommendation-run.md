# Recommendation Run Orchestration

## Purpose

This document defines the thin executable boundary after candidate generation, hard evaluation, and deterministic contextual selection were separated into reusable layers.

The orchestration layer exists to make one global recommendation run complete by construction:

```text
complete candidate generation
        ↓
evaluate every generated candidate
        ↓
apply contextual feasibility and rank/select that exact complete evaluated set
        + optional explicit ranking context
        ↓
return selected / no-suitable / no-generated outcome
```

It does not add new technical compatibility semantics of its own.

PR #69 adds one deliberate composition responsibility at this boundary: an accepted evidence-bound ToolAttachment installation may be projected through the ordinary generator when the manufacturer establishes the exact Tool/product/feature installation but does not publish enough geometry for a reusable eligibility rule. The original evidence binding remains retained separately; the projection is execution-local and is never promoted to generic compatibility.

## Layer ownership

### Candidate generation remains authoritative for ordinary alternatives and candidate facts

`generate_candidate_configurations()` owns physical candidate construction, identity, feature/endpoint/component binding, ranking-only candidate facts, and the complete set of alternatives produced from normalized technical inputs.

Minimum/retracted/shortest tether working length is retained on `GeneratedCandidate.ranking_facts` for contextual snag ranking.

Maximum/extended/longest tether working length remains on `CandidateConfiguration.tether_max_length_mm`. It retains its existing hard product/lanyard-constraint role and is also the normalized primitive consumed by explicit required-reach contextual feasibility. It is not duplicated into `CandidateRankingFacts`.

For ordinary geometry-backed inputs, the orchestration layer must not:

- construct additional technical eligibility rules;
- remove generated alternatives before evaluation;
- rewrite candidate IDs;
- infer missing product/interface/context facts; or
- turn an empty generated set into `no_suitable_recommendation`.

### Evidence-bound ToolAttachment composition is narrow and explicit

`EvidenceBoundToolAttachmentAssemblyOption` is separate from ordinary `ToolAttachmentAssemblyOption`.

An evidence-bound assembly contains accepted installation evidence tying:

```text
exact Tool
+ exact ToolAttachment product
+ exact resolved Tool feature
```

without claiming enough geometry for a reusable `AttachmentEligibility` rule.

When such an assembly is supplied, `run_recommendation()`:

1. requires the exact installation feature to exist on the selected resolved Tool;
2. creates an execution-local one-feature Tool/eligibility projection only to reuse the ordinary generator;
3. generates the candidate through the same existing candidate generator;
4. retains the original `ToolAttachmentInstallationBinding` separately in `CandidateToolBinding`; and
5. sends the generated candidate through the same ordinary hard evaluator and selector.

This projection does **not** become persisted product knowledge, a generic eligibility rule, or a technical claim that another Tool with similar broad feature shape accepts the attachment.

Evidence-bound assembly refs must be unique, and they must not collide with ordinary geometry-backed assembly refs. Invalid identity ambiguity raises rather than being hidden by downstream candidate-ID deduplication.

Where product-scoped connection evidence applies to an evidence-bound multi-component assembly, interface-to-product ownership must already be explicit enough for the connection matcher to determine which selected component owns the exact target interface. The run boundary does not infer that ownership from generic interface shape.

### Candidate evaluation remains authoritative for hard viability

`evaluate_candidate_configuration()` is invoked once for every generated candidate configuration, whether the ToolAttachment route came from reusable technical eligibility or accepted evidence-bound installation.

The orchestration layer must not duplicate or reinterpret load capacity, product constraints, connection compatibility, policy, pending runtime verification, or pre-use-action semantics.

A candidate is hard-viable exactly when the existing evaluator gives it a non-null recommendation state.

`CandidateRankingContext` is not passed into the hard evaluator. A candidate can therefore remain technically/hard viable while being contextually infeasible for one stated task requirement.

### Candidate selection remains authoritative for contextual feasibility, ranking, and global exhaustion

`rank_and_select_candidates()` receives the exact generated list and complete evaluation list produced during the run, plus optional `CandidateRankingContext`.

It is responsible for:

- exact candidate/evaluation identity coverage;
- hard-blocked versus hard-viable separation;
- explicit contextual feasibility over the hard-viable set;
- retaining proven contextual exclusions separately from hard-blocked candidates;
- baseline-quality ordering among selectable candidates;
- applying contextual preferences only under their defined semantics;
- deterministic final tie-breaking;
- selecting rank 1;
- distinguishing `no_generated_candidates`; and
- concluding `no_suitable_recommendation` only for a non-empty, fully evaluated set with no remaining selectable candidate.

The orchestration layer does not introduce a second ranking, feasibility, or outcome-state model.

## Executable boundary

The reusable entry point is:

```python
run_recommendation(
    tool,
    tethers,
    anchor_paths,
    *,
    tool_attachment_assemblies=None,
    evidence_bound_tool_attachment_assemblies=None,
    product_runtime_state=None,
    connection_contexts=None,
    policy_contexts=None,
    ranking_context=None,
)
```

The two ToolAttachment inputs deliberately mean different things:

```text
tool_attachment_assemblies
    reusable technical eligibility backed by normalized feature/constraint facts

evidence_bound_tool_attachment_assemblies
    exact accepted Tool/product/feature installation evidence used only when
    reusable geometry is not established
```

Supplying an evidence-bound route does not make it technically exclusive. Ordinary ToolAttachment alternatives remain in the generated set when their own technical eligibility succeeds.

The current contextual model remains deliberately small:

```python
CandidateRankingContext(
    snag_risk="standard" | "elevated" | None,
    required_reach_mm=float | None,
)
```

The two implemented context dimensions have different semantics:

- explicit `required_reach_mm` is a contextual feasibility requirement using maximum/extended working length;
- explicit elevated snag risk is a contextual preference using minimum/retracted working length and acts only inside complete baseline-quality ties within the same reach-knowledge tier.

See `candidate-ranking-selection.md` for detailed threshold, missing-fact, partition, and ordering rules.

## Completeness invariant

Conceptually, the orchestration sequence remains:

```text
complete generated candidate set
  -> evaluate every generated candidate
  -> rank/select the exact complete evaluated set
```

When no evidence-bound assemblies are supplied, generation is exactly the historical single `generate_candidate_configurations()` invocation.

When evidence-bound assemblies are supplied, `_generate_with_evidence_bound_installations()` composes:

- all ordinary geometry-backed ToolAttachment alternatives through the existing generator; and
- each applicable exact evidence-bound route through the same generator under its execution-local feature projection.

Only after that complete generated set exists does evaluation begin.

Context does not pre-filter alternatives before hard evaluation.

This preserves the PR #36 completeness guarantee: an external caller cannot obtain a system-level no-suitable conclusion by passing only a hand-selected subset through the normal run boundary.

The selector remains reusable on its own, but a system-level global recommendation outcome should normally come from the recommendation-run boundary when generation is part of the same decision.

## Result model

`RecommendationRunResult` retains:

```text
tool
    exact resolved Tool used for generation

tool_fingerprint
    deterministic fingerprint of that Tool

generation_tool_bindings
    exact selected installation feature for ToolAttachment-mediated candidates,
    plus the original ToolAttachmentInstallationBinding when the route was evidence-bound

generated_candidates
    all physical alternatives produced by generation

evaluations
    one hard evaluation for every generated candidate

ranking_context
    the explicit context used for contextual feasibility/ranking,
    or null when no explicit context was supplied

selection
    the CandidateSelectionResult produced for those exact inputs
```

`CandidateSelectionResult` covers the complete generated set across three mutually exclusive partitions:

```text
ranked_viable_candidates
contextually_infeasible_candidates
blocked_candidates
```

The result intentionally preserves full stage outputs rather than returning only the selected candidate.

This supports:

- explanation/audit of why ordering or feasibility changed under explicit context;
- inspection of hard-blocked and contextually infeasible alternatives separately;
- deterministic session fallback;
- tracing selected component, installation-feature, exact evidence-bound installation, endpoint, anchor-path, source-product, and candidate-fact provenance; and
- adding later context families without reconstructing candidate identity.

The authoritative global outcome remains `selection.state`; orchestration does not duplicate `CandidateSelectionState` with another enum.

## Generation binding provenance

For every ToolAttachment-mediated generated candidate, `generation_tool_bindings` retains the exact Tool feature that generation used.

For an ordinary reusable technical route this is the bound feature selected by the generator.

For an evidence-bound route it additionally retains the original exact `ToolAttachmentInstallationBinding`, including:

```text
binding_id
tool_ref
source_product_ref
installation_feature_id
issuer_manufacturer
scope
source_urls
```

This prevents the execution-local eligibility projection from becoming the apparent source of truth. The explanation/audit boundary can recover that the route existed because accepted manufacturer evidence documented that exact product at that exact feature, while still showing that downstream load/connection checks were performed by ordinary reusable logic.

If the binding refers to a Tool feature that is absent from the selected resolved Tool, the route is not generated. The run boundary must not fabricate that feature.

## Result self-consistency validation

A `RecommendationRunResult` may be created directly or deserialized outside `run_recommendation()`. It therefore cannot assume that its retained `selection` was actually produced from its retained generated candidates, evaluations, and ranking context.

The model validator enforces two levels of consistency.

### 1. Identity and coverage

It requires:

- generated candidate IDs to be unique;
- evaluation candidate IDs to be unique;
- generated/evaluation ID sets to match exactly;
- the union of `ranked_viable_candidates`, `contextually_infeasible_candidates`, and `blocked_candidates` to cover the exact generated set; and
- every retained `EvaluatedCandidate` to contain the exact corresponding generated candidate and hard evaluation from the run.

Generation Tool bindings are also tied to candidate identity and must refer only to candidates in the generated set.

### 2. Selection semantics

Coverage alone is insufficient. A manually constructed result could otherwise retain, for example:

- `required_reach_mm = 1000`;
- a selected candidate with known `tether_max_length_mm = 900`; and
- an empty contextual-infeasible partition.

That would be structurally complete but semantically contradictory.

To prevent this, the validator recomputes:

```python
expected_selection = rank_and_select_candidates(
    generated_candidates,
    evaluations,
    ranking_context=ranking_context,
)
```

and requires the retained `selection` to equal that expected deterministic result.

This deliberately reuses the selector instead of reimplementing reach, snag, baseline ranking, partition, or exhaustion logic inside orchestration. Future contextual families therefore inherit the same run-result consistency protection as long as their semantics remain centralized in the selector.

## Failure semantics

An unsuccessful orchestration stage or result invariant is not a recommendation outcome.

If generation, evidence-bound assembly validation, candidate evaluation, selection, or result validation raises because its inputs/invariants are invalid, the exception propagates.

The orchestration layer must not catch such failures and translate them into:

```text
no_suitable_recommendation
```

That state retains this bounded meaning:

```text
generation succeeded
AND generated set is non-empty
AND every generated candidate was evaluated
AND no generated candidate remains selectable after
    hard evaluation + explicit contextual feasibility
```

A complete set may therefore be exhausted by:

- hard evaluator blocking alone;
- proven contextual infeasibility alone; or
- a mixture of both.

Required reach can create contextual infeasibility only when a hard-viable candidate's established maximum working length is below the explicit requirement.

A hard-viable candidate whose maximum working length is unknown remains a selectable unknown fallback, so missing reach data cannot be converted into a false global exhaustion conclusion.

Successful generation of no alternatives remains:

```text
no_generated_candidates
```

The run boundary does not infer why no candidates were generated.

## Provenance and identity

The run retains original `GeneratedCandidate` objects throughout evaluation and selection.

Candidate identity is therefore not reconstructed from SKU pairs, product names, or the canonical candidate-ID string. Selected, ranked, contextually infeasible, and blocked candidates continue to carry their original:

- tool reference;
- tether reference;
- ToolAttachment assembly and installation feature where applicable;
- exact evidence-bound installation binding where applicable;
- tool-side and anchor-side endpoint/target bindings;
- anchor path;
- component-instance references;
- source-product references;
- minimum tether working-length ranking fact where known; and
- maximum tether working length on the retained evaluator-ready configuration where known.

The ranking context itself is retained on the run result rather than inferred later from the selected product.

Evidence-bound provenance remains distinct from technical eligibility. Retaining a Hilti binding, for example, records why that exact known installation route entered generation; it does not assert an invented `through_opening`, captive state or dimension and does not make another attachment technically incompatible.

## Downstream session-local condition resolution

The completed run result is now the immutable input to `recommendation_session.py`.

Session resolution uses only:

```text
selection.ranked_viable_candidates
```

for fallback. It does not regenerate candidates, alter hard evaluations, re-run contextual feasibility, or re-rank survivors.

Original pending condition identifiers are wrapped in candidate scope:

```text
(candidate_id, runtime_verification, connection_id)
(candidate_id, pre_use_action, constraint_id)
```

A satisfied condition keeps the candidate active. A failed condition rejects only that candidate for the current session/configuration and advances to the next item in the original ranking.

If every originally ranked selectable candidate later fails a session condition, the session layer reports its own `exhausted` state. The originating run remains unchanged with its original selector outcome.

This distinction is intentional:

```text
selector no_suitable_recommendation
    = no candidate was selectable after hard evaluation/contextual feasibility

session exhausted
    = selectable candidates existed, but each later failed a session-local condition
```

See `recommendation-session.md` for condition identity, lazy fallback, canonical resolution ordering, self-consistency validation, and deliberate boundaries.

## Deliberate boundaries

The recommendation-run layer itself does not add:

- environmental ranking/feasibility beyond the selector's explicit context model;
- capacity-headroom preferences;
- direct-versus-ToolAttachment preference;
- tether-form preference by itself;
- brand or SKU-pair technical rules;
- automatic promotion of evidence-bound installations into reusable eligibility rules;
- inference of missing Tool feature geometry;
- cross-product compatibility inference;
- user-facing recommendation prose;
- catalogue/ingestion resolution; or
- persistence/retry machinery beyond validating a reconstructed run result.

Session-local condition disposition and fallback remain implemented in the separate `recommendation_session.py` layer rather than folded back into orchestration.

## Test expectations

Focused orchestration/context tests continue to cover at least:

- a complete multi-candidate run selecting the real hard-viable alternative;
- explicit elevated snag context changing the ordering of otherwise baseline-equivalent candidates when minimum working lengths are known;
- explicit required reach retaining a hard-viable but known-short candidate as contextually infeasible rather than hard-blocked;
- the run retaining the explicit ranking context used for selection;
- complete coverage across ranked, contextually infeasible, and hard-blocked partitions;
- a complete run where every remaining candidate is proven too short and global exhaustion is valid;
- a non-empty complete run where every candidate is hard-blocked and global exhaustion is valid;
- empty generation remaining `no_generated_candidates`;
- every generated candidate being evaluated exactly once;
- a manually constructed/deserialized run whose selection ignores active required reach being rejected;
- a manually constructed/deserialized run carrying contextual exclusions without the corresponding context being rejected;
- stage/invariant failure propagating instead of being converted into recommendation exhaustion;
- evidence-bound installation generating only when its exact Tool feature exists;
- evidence-bound installation remaining scoped to its exact Tool/product/feature route;
- ordinary geometry-backed competitors continuing to generate alongside the documented route; and
- duplicate/ambiguous evidence-bound assembly identities failing before candidate generation.

The lower-layer selector tests remain responsible for detailed baseline precedence, required-reach threshold/equality semantics, missing-reach fallback, excess-reach neutrality, snag interaction, deterministic ordering, hard-viability separation, identity, and exact coverage semantics.

The session tests separately own terminal condition resolution, candidate scoping, immutable evaluation preservation, lazy fallback, session exhaustion, and session-result self-consistency.

## End-to-end recommendation coverage

PR #48 added the first separate downstream semantic golden over this run boundary. It is intentionally distinct from the supply-side ingestion/readiness benchmark and from the session-local fallback model.

`tests/test_recommendation_benchmark.py` constructs generic normalized runtime fixtures independently of `benchmarks/recommendation_e2e_golden.json`. The golden records expected recommendation semantics only; it does not provide runtime candidate construction and does not contain SKU pairs, product refs or canonical candidate IDs.

Subsequent work added ToolAttachment-mediated benchmark coverage across explicit feature eligibility, selected installation-feature binding, normalized installation constraints, the ToolAttachment-provided tether interface, candidate generation, hard evaluation and selection.

PR #69 adds a separate **real catalogue-backed field vertical** for the sparse-geometry case. The Hilti SF 4-22 route is not encoded into a semantic golden as an SKU pair; accepted manufacturer installation/connection evidence is resolved at runtime and then enters the same ordinary generation/evaluation/selection layers.

## Next architecture step

The next architecture step is **not** to infer a generic Hilti geometry rule from the documented #2293133 route.

Higher-value follow-up work is to validate the evidence-bound pattern against another real manufacturer/product family and to introduce explicit rule epistemic/provenance metadata only when a real cross-product inference case requires it. Configuration-component or assembled-configuration feature ownership should likewise wait for a concrete attachment case that installs on a selected Battery/configuration rather than the bare Tool.

The principle remains: broaden from repeated evidence, not from the desire to eliminate every exact documented relationship.
