# AGENTS.md

This file provides repository-wide guidance for AI coding agents working on TetherLens.

It describes how to understand the project, where to find authoritative context, how to make changes safely, and which architectural and evidence boundaries must be preserved.

## 1. Start here

Before changing code:

1. Read `project-status.md`.
2. Inspect the relevant implementation on the current branch, preferably starting from current `main`.
3. Read the durable design document(s) relevant to the task.
4. Inspect existing tests and benchmark expectations for the affected behavior.
5. Identify the smallest reusable change that solves the actual problem before introducing new abstractions.

`project-status.md` is the operational handoff and the authoritative source for:

- the current merged semantic baseline;
- recently completed work;
- frozen benchmark/cohort results;
- current deliberate boundaries;
- the next recommended workstream; and
- important invariants exposed by recent review.

Do not copy assumptions from an old PR, old chat prompt, historical benchmark document, or earlier implementation if they conflict with the current `project-status.md` and current code.

The durable design documents explain the intended model. Important starting points include:

- `product-vision.md` — product purpose and user value;
- `mvp.md` — MVP scope;
- `architecture.md` — system boundaries and responsibilities;
- `domain-model.md` — product/domain concepts;
- `evidence-model.md` — evidence and provenance semantics;
- `ingestion.md` — ingestion architecture;
- `technical-schema.md` — detailed technical schema;
- `recommendation-engine.md` — recommendation architecture;
- `connection-compatibility.md` — connection reasoning;
- `tool-attachment-compatibility.md` — ToolAttachment behavior;
- `candidate-ranking-selection.md` — ranking and selection;
- `recommendation-run.md` and `recommendation-session.md` — runtime recommendation flow;
- `benchmark-goals.md` — what the benchmarks are intended to prove;
- `portability-benchmark.md` — portability methodology; and
- `adapter-review-guidance.md` — deciding whether an ingestion fix belongs in vendor-specific or shared code.

Read only the documents relevant to the task rather than attempting to treat every historical design note as current implementation guidance.

## 2. Product principle

The central product principle is:

> **AI identifies. Verified data and engineering rules determine the recommendation.**

TetherLens is intended to help a field worker determine how a tool should be tethered and what equipment is appropriate.

Probabilistic systems may assist with recognition, extraction, interpretation, and explanation. Safety-relevant recommendation decisions must resolve to inspectable structured facts, explicit evidence, reusable rules, exact documented relationships where appropriate, and policy.

Do not move recommendation authority into an LLM, search result, recognition confidence score, or unverified inference.

## 3. Architectural boundaries

Keep these concepts separate:

```text
manufacturer/source evidence
        ↓
ingestion and normalization
        ↓
accepted facts / claims / relationships
        ↓
reusable technical rules
        ↓
candidate generation
        ↓
hard evaluation
        ↓
contextual ranking / selection
        ↓
field recommendation / session resolution
```

Recognition and search are advisory inputs to tool resolution. They do not create accepted safety-critical facts.

Policy is separate from technical compatibility.

Manufacturer position or prescription is separate from technical compatibility unless accepted evidence establishes a causal technical reason for incompatibility.

Ranking is separate from hard viability. Ranking must never override a failed hard constraint.

## 4. Evidence first; fail closed

Never invent a physical or semantic fact because it would make a recommendation path convenient.

Missing evidence remains unknown.

In particular, do not infer without evidence:

- dimensions;
- opening geometry;
- captive state;
- connector direction;
- feature identity;
- installation suitability;
- load capacity;
- compatibility;
- manufacturer identity;
- product identity; or
- endorsement.

Absence from a manufacturer compatibility list is not evidence of incompatibility.

Marketing language must not be converted into precise numeric geometry or capacity.

If first-party evidence is conflicting or insufficient, preserve the conflict or unresolved state rather than selecting the value that makes a test pass.

## 5. Prefer reusable semantics, but do not over-generalize

The preferred progression is:

```text
exact physical geometry/dimensions
    -> reusable technical rule

functional/topological facts
    -> reusable technical rule

explicit documented relationship with insufficient reusable geometry
    -> narrowly scoped evidence-bound path
```

Use reusable manufacturer-neutral semantics wherever the evidence supports them.

However, do not invent a generic abstraction merely to eliminate a vendor-specific implementation detail.

A manufacturer adapter is allowed to understand that manufacturer's URLs, page structure, terminology, SKU grammar, documents, and source quirks.

Downstream recommendation logic should normally operate on manufacturer-neutral concepts.

A useful rule of thumb is:

```text
vendor-specific source interpretation
        ↓
shared normalization / evidence / safety invariant
        ↓
manufacturer-neutral downstream reasoning
```

Do not add manufacturer- or SKU-specific branches to shared recommendation logic merely to make one product work.

If a downstream exception genuinely cannot be represented by existing reusable semantics, document why before introducing it.

## 6. When fixing an adapter, inspect the generalization boundary

A bug first found in one manufacturer adapter may reveal either:

1. a source-specific parsing/acquisition problem; or
2. a reusable TetherLens invariant.

Before making a narrowly local fix, inspect equivalent paths in relevant adapters.

Shared code is appropriate for manufacturer-independent invariants such as:

- provenance validation;
- exact product/variant binding;
- unit normalization;
- evidence reconciliation;
- record/scope boundaries;
- prevention of cross-product evidence leakage; and
- fail-closed ambiguity handling.

Keep source grammar local when the generic layer cannot safely know it.

Do not refactor every adapter merely for symmetry. Generalize only when a real reusable semantic boundary exists.

See `adapter-review-guidance.md`.

## 7. Preserve provenance and identity

Recommendation behavior must remain traceable.

Preserve exact provenance through the pipeline, including where applicable:

- source;
- raw evidence;
- evidence method;
- extractor metadata;
- manufacturer;
- exact product/variant;
- Tool operational configuration;
- Tool feature;
- ToolAttachment installation binding;
- connector/interface;
- endpoint assignment;
- AnchorAttachment installation binding;
- candidate identity; and
- selected component identity.

Do not derive manufacturer identity from a product-ref or SKU naming convention.

Do not allow evidence from one product, model, document section, interface, or related-product card to leak into another.

When several sources support the same logical fact or relationship, keep source/evidence metadata aligned. Do not merge provenance in a way that separates a source URL from wording or extraction metadata that came from another source.

## 8. Product-scoped and document-scoped evidence must stay local

Exact page identity does not imply that every piece of text on the page belongs to the selected product.

Manufacturer pages and documents may contain:

- related products;
- product cards;
- multiple SKUs;
- several models;
- repeated headings;
- cross-sell content; or
- combined manuals.

Bound evidence to the narrowest supported product/model/section before turning it into an executable claim.

A model name occurring somewhere in a document does not authorize every section of that document for that model.

Repeated evidence for one relationship and evidence for two genuinely different installation routes are not the same thing.

## 9. Recommendation invariants

The recommendation engine should preserve the following behavior unless the task explicitly establishes a justified architectural change.

### Hard viability versus ranking

Hard constraints determine whether a candidate is viable.

Ranking compares candidates that have already passed the applicable hard evaluation.

Never use ranking to rescue:

- hard incompatibility;
- exceeded load limits;
- invalid installation;
- missing evidence required for a hard decision; or
- prohibited configurations.

### Exhaustion

Do not conclude that no suitable recommendation exists until the complete generated alternative set relevant to the run has been evaluated.

### Sparse manufacturer geometry

Exact geometry is preferred when published, but incomplete geometry is a normal catalogue condition.

An exact manufacturer-documented installation or connection may be used as an evidence-bound positive path when the relationship itself is established but reusable physical predicates are not.

Such a path:

- proves only the documented relationship;
- does not establish generic compatibility;
- does not establish why the relationship works unless the source says so; and
- does not prove alternatives incompatible.

### Manufacturer position

Manufacturer instruction, endorsement, prescription, or contrary guidance belongs on its own assessment axis unless there is evidence of a causal technical incompatibility.

Do not convert a mixed-manufacturer configuration into technical incompatibility solely because a source prescribes its own product family.

Likewise, matching the named manufacturer does not automatically prove blanket endorsement of every product from that manufacturer.

## 10. Tool configuration and operational mass

Operational mass must be configuration-specific where the Tool requires an installed configuration such as a Battery.

Do not silently use:

- bare-tool mass;
- an arbitrary compatible battery;
- the lightest configuration;
- the heaviest configuration; or
- a user-entered value in place of accepted catalogue evidence for an identified catalogue configuration.

A generic/session-level Tool profile may use explicitly supplied runtime facts when the worker cannot resolve to a suitable catalogue identity, but those session facts do not automatically become accepted catalogue Claims.

## 11. Field workflow boundary

Search and recognition may narrow Tool candidates, but an advisory match is not recommendation authority.

Where the current workflow requires explicit worker confirmation, retain that boundary.

Do not silently:

- accept a fuzzy identity as an exact Tool;
- infer an installed Battery from the Tool model;
- promote recognition confidence into safety confidence; or
- persist generic runtime observations as accepted catalogue facts.

## 12. Repository map

The Python package lives under:

```text
src/tetherlens_ingest/
```

Important areas include:

```text
adapters/
    Manufacturer/source-specific acquisition and extraction.

models.py
    Core ingestion-facing models.

resolution.py
    Claim/fact resolution.

reconciliation.py
    Shared reconciliation behavior.

normalize.py
    Normalization helpers.

operational_profile.py
    Tool operational/configuration profiles.

attachment_method.py
anchor_installation.py
tool_attachment_installation.py
    Installation and attachment semantics.

connection.py
compatibility.py
declared_compatibility.py
endpoint_assignment.py
manufacturer_instruction.py
    Connection, compatibility, endpoint and manufacturer-position reasoning.

constraints.py
    Normalized/hard constraint behavior.

candidate_generation.py
    Recommendation candidate composition.

candidate_selection.py
    Candidate evaluation/ranking/selection behavior.

recommendation.py
recommendation_run.py
recommendation_session.py
recommendation_session_adapter.py
    Recommendation runtime and session layers.

field_tool_search.py
field_recommendation.py
    Demand-side / field orchestration.

benchmark.py
runner.py
cli.py
    Ingestion and benchmark execution support.
```

Tests live under `tests/`.

Scripts for benchmark and smoke execution live under `scripts/`.

Before introducing a new module, inspect whether an existing semantic layer already owns the responsibility.

## 13. Development environment

TetherLens requires Python 3.11 or later.

Install the package and development dependency with:

```bash
python -m pip install -e ".[dev]"
```

Run the full unit-test suite with:

```bash
pytest -q
```

During development, first run the narrowest relevant tests, for example:

```bash
pytest -q tests/test_<relevant_area>.py
```

Then run the full suite before considering the change complete.

The GitHub Actions ingestion smoke workflow currently runs the unit suite plus live manufacturer benchmark/scoring scripts. Check `.github/workflows/ingestion-smoke.yml` for the authoritative CI commands rather than duplicating an assumed workflow here.

Live-source tests depend on external manufacturer content. When one fails, determine whether the failure is:

- a code regression;
- a source acquisition/provenance failure;
- changed manufacturer content; or
- an intentionally fail-closed result.

Do not weaken evidence checks merely to restore a green live test.

## 14. Benchmark discipline

Benchmarks are semantic tests, not targets to game.

Historical portability cohorts and blind baselines are immutable at the semantic revision where they were frozen.

Do not rewrite a historical answer key because later work closes a gap that the cohort exposed.

Do not broaden a regex, parser, compatibility rule, or candidate rule merely to improve the score of one known benchmark item.

A benchmark-driven fix should express a reusable semantic truth or a correctly scoped source-specific interpretation.

When changing benchmark behavior, read:

- `benchmark-goals.md`;
- the relevant benchmark documentation;
- the affected test cases; and
- `project-status.md`.

Preserve the distinction between historical benchmark results and current production capability.

## 15. Testing expectations for changes

A good change normally includes:

1. a regression test reproducing the concrete issue;
2. tests for the reusable invariant if shared behavior changed;
3. negative tests proving that evidence or behavior does not leak beyond its intended scope;
4. preservation of existing tests for unaffected behavior; and
5. full-suite verification.

For parsers, include nearby false-positive or sibling-product cases when practical.

For compatibility/recommendation behavior, test both the valid path and the boundary where the rule must remain unresolved or incompatible.

For provenance-sensitive changes, assert provenance rather than only the final recommendation result.

Prefer semantic assertions over implementation-detail assertions.

## 16. Keep changes small and causal

Prefer the smallest change that fixes a demonstrated problem while preserving the architecture.

Avoid opportunistic refactors unrelated to the task.

Before adding a new enum, model, primitive, compatibility state, runtime component type, or abstraction, establish the decision need it represents.

A new product shape does not automatically require a new runtime primitive. For example, a commercial kit may be representable as relationships to existing recommendation components rather than as a new load-path component.

Do not create ontology in anticipation of hypothetical future products when existing semantics correctly represent the evidence.

## 17. Code style

Match the existing code style and local conventions.

General expectations:

- use typed Python;
- keep domain semantics explicit;
- prefer small named helpers for reusable safety/provenance invariants;
- avoid clever parsing that is difficult to bound or review;
- make fail-closed behavior obvious;
- preserve deterministic ordering where results are compared or ranked;
- avoid hidden mutation of accepted facts;
- keep source acquisition separate from semantic normalization where practical; and
- add comments/docstrings where the safety or evidence boundary is not obvious from the code.

Do not add dependencies unless the task materially requires them.

## 18. Documentation is part of the definition of done

Every PR must update `project-status.md` so that it accurately describes the post-merge state.

Also update the relevant durable design document when the change materially alters:

- architecture;
- domain vocabulary;
- evidence semantics;
- ingestion behavior;
- compatibility reasoning;
- recommendation behavior;
- field orchestration;
- benchmark methodology; or
- another documented invariant.

Do not turn `project-status.md` into a full design-history log. Keep durable design detail in its dedicated document and use `project-status.md` as the operational handoff.

Do not rewrite historical benchmark documents to make them describe current behavior.

## 19. Before finishing a task

Review the diff from a product and semantic perspective, not only for test success.

Check:

- Does this solve a reusable product need or only patch one SKU?
- Did source-specific behavior remain in the adapter where appropriate?
- Did a generic invariant get duplicated in a vendor adapter?
- Did any missing fact accidentally become an inferred fact?
- Did evidence leak across products, models, sections, or interfaces?
- Did manufacturer position accidentally become technical incompatibility?
- Did ranking change hard viability?
- Did candidate or installation provenance get lost?
- Did the change mutate a historical benchmark expectation?
- Did the change create an abstraction without a demonstrated decision need?
- Are negative/boundary tests present?
- Does `project-status.md` describe the resulting post-merge state?
- Do any durable design documents also need updating?

If the implementation passes tests but weakens one of these boundaries, it is not complete.

## 20. How to approach an ambiguous task

When a task asks to investigate, design, or tackle the "next" gap:

1. inspect current `main`;
2. read `project-status.md`;
3. inspect the relevant code, tests, and design docs;
4. identify the concrete gap before proposing ontology;
5. prefer existing reusable semantics where possible;
6. determine whether the problem belongs to ingestion, evidence, normalization, recommendation logic, policy, or field orchestration;
7. propose the smallest reusable implementation slice; and
8. only then change code.

Do not assume that the named product or failing test tells you what abstraction is needed.

The important question is what semantic or product capability the case proves.

## 21. What not to optimize for

Do not optimize primarily for:

- passing one SKU-specific test;
- maximizing benchmark scores at the expense of evidence integrity;
- eliminating every `UNRESOLVED` result;
- maximizing catalogue breadth without a field/user need;
- making all adapters structurally identical;
- minimizing code lines at the expense of provenance;
- speculative generality; or
- producing a recommendation when the evidence does not support one.

Optimize for defensible, reusable recommendation behavior that preserves evidence and remains useful to the field worker.
