# TetherLens Benchmark Goals

## Purpose

The ingestion benchmark exists to answer the main supply-side viability question for TetherLens:

> Can TetherLens resolve the trustworthy facts required to make real tethering decisions, with sufficiently little product-specific effort and sufficiently low acquisition cost to scale across manufacturer catalogues?

The useful structured output is the goal. The acquisition method is what the benchmark is intended to discover and evaluate.

This principle takes precedence over narrow extractor or source-path success. Manufacturer pages, APIs, embedded application state, documents, related-product graphs, reputable secondary sources, search/discovery mechanisms, internal measurements, and future extraction techniques are candidate evidence channels. They are not themselves the benchmark outcome.

## Primary success criterion: recommendation-ready output

A benchmark product succeeds at the product-viability level only when TetherLens resolves the recommendation-critical facts required for the intended decision, with acceptable evidence and provenance.

For example, a cordless power tool requires a defensible operational mass for load reasoning. Recovering its SKU, battery platform, or API record is useful engineering progress, but does not make the product recommendation-ready if operational mass remains unresolved.

Likewise, correctly diagnosing `MISSING_TOOL_BODY_MASS` is a successful diagnostic result but a failed recommendation-readiness result when tool mass is required to make the tethering decision.

The benchmark must therefore distinguish two kinds of success:

### Engineering health

Measures whether acquisition machinery behaves correctly, for example:

- canonical identity discovery;
- manufacturer catalogue enumeration;
- API or structured-state acquisition;
- document discovery and download;
- source-graph traversal;
- relationship extraction;
- deterministic parsing and normalization;
- evidence provenance;
- accurate failure classification.

These metrics are necessary for debugging and maintaining the ingestion system, but they are not substitutes for useful output.

### Product viability

Measures whether the resulting knowledge is useful to TetherLens, for example:

- recommendation-readiness rate;
- recommendation-critical fact coverage;
- operational-mass profile coverage for cordless tools;
- evidence quality and corroboration;
- unseen-SKU generalization;
- human intervention rate;
- product-specific exception/code rate;
- acquisition cost per product and per resolved critical fact.

A run may therefore be `engineering-success / product-failure`. Milwaukee `2602-20`, when its manufacturer acquisition succeeds but operational mass remains unresolved, is an example of this distinction.

## Outcome-first acquisition

The benchmark should not prescribe one source path when several evidence-qualified paths can establish the required fact.

The preferred strategy is progressive and cost-aware:

1. exploit cheap, deterministic manufacturer sources first;
2. follow manufacturer source graphs, regional pages, related products and technical documents where useful;
3. when a recommendation-critical fact remains unresolved, continue through permitted fallback evidence channels rather than stopping merely because the primary manufacturer page/API lacks the field;
4. preserve exact product identity, provenance, raw evidence and derivation for every accepted fact;
5. stop when the fact is resolved to the required evidence standard or when the permitted search budget is exhausted.

The evidence policy should be property-specific. A manufacturer declaration may be mandatory for a manufacturer's rated tether capacity or compliance claim, while a physical tool mass may be resolvable from a reputable exact-SKU industrial distributor when the manufacturer does not publish it directly. Secondary evidence must not be silently promoted to manufacturer-stated evidence.

Conflicting values must be retained and reconciled explicitly rather than hidden by source precedence.

## Required-fact resolution

Manufacturer adapters should efficiently exploit manufacturer-specific structure, but they should not be expected to contain bespoke solutions for every missing fact.

The intended ingestion flow is:

```text
identity
  -> manufacturer acquisition
  -> candidate claims + source relationships
  -> required-fact assessment
  -> generic fact resolution for remaining critical gaps
  -> evidence reconciliation
  -> derived operational/configuration profiles
  -> recommendation-readiness assessment
```

This means a missing required fact is a trigger for further resolution, not automatically the end of ingestion.

For cordless power tools, the system should seek enough evidence to represent the relevant operational configuration rather than treating bare-tool mass as the final product fact:

```text
tool-body mass + installed battery mass = operational mass profile
```

Hilti `SF 4-22` demonstrates the desired multi-source outcome: tool-body mass, compatible battery relationships and battery masses can be joined to derive operational profiles. The benchmark should test whether the same outcome can be achieved economically when another manufacturer exposes those operands differently or incompletely.

## Generalization, not golden-SKU overfitting

Golden data is an answer key for scoring. It must not become acquisition configuration.

Benchmark code should not encode product-specific URLs, values, relationships or exceptions merely to make a known golden SKU pass unless the purpose of that seed is explicitly to measure a separate assisted-ingestion mode.

A scalable strategy should work on products that were not used to develop it. Manufacturer evaluation should therefore evolve from isolated golden SKUs toward cohorts containing:

- a development set used to build and debug the adapter/resolver; and
- an unseen evaluation set used to measure generalization without additional SKU-specific code.

A manufacturer strategy that performs well only on the development SKU has not demonstrated catalogue scalability.

## Economic scalability

A fact that can eventually be found is not necessarily economically ingestible.

The benchmark should record enough telemetry to estimate catalogue-scale cost, including where practical:

- HTTP requests and sources fetched;
- documents downloaded;
- bytes transferred;
- browser-rendering calls;
- search/discovery calls;
- LLM calls/tokens;
- elapsed processing time;
- human review/research minutes;
- new product-specific code or configuration.

The objective is not simply to minimize requests. More expensive fallback acquisition can be justified when it materially increases recommendation readiness. The benchmark should reveal the marginal cost of closing those gaps so that TetherLens can make an informed product/economic decision.

## Benchmark interpretation rules

The following rules should guide future benchmark design and scoring:

1. **Useful output is the hard product criterion.** A required fact left unresolved is a product-readiness failure even when the failure is diagnosed perfectly.
2. **Acquisition diagnostics remain visible.** They explain why a product succeeded or failed and help improve the pipeline.
3. **Do not reward a particular mechanism.** API, HTML, document or secondary-source acquisition is valuable only insofar as it produces qualified evidence efficiently.
4. **Do not fabricate completeness.** Missing or conflicting evidence must remain explicit.
5. **Do not use goldens as lookup tables.** They validate outputs; they do not tell ingestion where the answer is.
6. **Measure generalization.** Success on unseen products without code changes matters more than success on one hand-tuned SKU.
7. **Measure cost.** A strategy that works but cannot be afforded at catalogue scale has failed the viability question.
8. **Keep provenance first-class.** Derived facts must retain the evidence chain for every operand.

## Immediate implication for Batch 1

The existing Batch 1 acquisition/source-graph tests remain useful as engineering regression tests. They should not, by themselves, be interpreted as proof that a product or manufacturer is recommendation-ready.

The next benchmark iteration should add a product-viability scorecard alongside those regression tests. `operational_mass_kg` should be the first required-fact resolution case exercised across Hilti and Milwaukee:

- Hilti should satisfy the resolver from first-party source-graph evidence without unnecessary fallback work;
- Milwaukee should continue resolution when first-party acquisition leaves tool-body mass unresolved;
- both should be scored on the usefulness, evidence quality, generalization and acquisition cost of the final operational profiles.

This is the standard future ingestion work should optimize for.