# TetherLens Benchmark Goals

## Purpose

The ingestion benchmark exists to answer the main supply-side viability question for TetherLens:

> Can TetherLens resolve the trustworthy facts required to make real tethering decisions, with sufficiently little product-specific effort and sufficiently low acquisition cost to scale across manufacturer catalogues?

The useful structured output is the goal. The acquisition method is what the benchmark is intended to discover and evaluate.

This principle takes precedence over narrow extractor or source-path success. Manufacturer pages, APIs, embedded application state, documents, related-product graphs, reputable secondary sources, internal measurements, and future extraction techniques are candidate evidence channels. They are not themselves the benchmark outcome.

Where this document conflicts with older product-specific assumptions in `ingestion-benchmark.md`, this document should be treated as the current benchmark direction.

## Primary success criterion: recommendation-ready output

A benchmark product succeeds at the product-viability level only when TetherLens resolves the recommendation-critical facts required for the intended decision, with acceptable evidence and provenance.

For example, a cordless power tool requires a defensible operational mass for load reasoning. Recovering its SKU, battery platform, or API record is useful engineering progress, but does not make the product recommendation-ready if operational mass remains unresolved.

The benchmark must therefore distinguish two kinds of success.

### Engineering health

Measures whether acquisition machinery behaves correctly, for example:

- canonical identity discovery;
- manufacturer catalogue enumeration;
- API or structured-state acquisition;
- document discovery and download;
- source-graph traversal;
- relationship extraction;
- deterministic parsing and normalization;
- evidence provenance; and
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
- product-specific exception/code rate; and
- acquisition cost per product and per resolved critical fact.

A run may therefore be `engineering-success / product-failure` if acquisition behaves correctly but a recommendation-critical fact remains unresolved.

## Source-graph philosophy

The Hilti work established the preferred mental model for cordless-tool ingestion: treat the available evidence as a product graph rather than as one page that must contain every fact.

For a cordless tool, the graph may include:

```text
tool identity
  -> compatible/recommended battery relationship(s)
  -> tool-body mass
  -> battery mass
  -> derived operational mass profile(s)
```

Hilti often exposes those nodes and edges within its own first-party ecosystem. Other manufacturers may expose the same conceptual graph less completely.

TetherLens should keep the same graph model even when the evidence crosses source boundaries. A fact or relationship may come from Milwaukee while another physical fact comes from a qualified industrial distributor such as Grainger, provided exact product identity is maintained and provenance is retained per fact.

The downstream structured result should not depend on whether every operand came from one publisher.

## Outcome-first, cost-aware acquisition order

The benchmark should not prescribe one source path when several evidence-qualified paths can establish the required fact. It should, however, prefer cheaper and more deterministic paths before expensive general discovery.

The preferred progression is:

1. use deterministic first-party manufacturer sources first;
2. follow manufacturer product graphs, kit composition, recommended/related products, regional pages, APIs and technical documents;
3. if a physical fact is still missing, use a qualified exact-SKU distributor or other deterministic secondary source where the evidence policy allows it;
4. reconcile evidence across sources while preserving the source and evidence method for every fact;
5. use paid/general web-search discovery only for genuinely difficult cases after deterministic graph paths have been exhausted;
6. stop when the required fact is resolved to the required evidence standard or the permitted acquisition budget is exhausted.

Paid search should therefore be treated as a later fallback capability, not the default ingestion path for ordinary catalogue products.

## Property-specific evidence qualification

Evidence requirements depend on the property being asserted.

Examples:

- a manufacturer's rated tether capacity, restriction or standards/compliance declaration should normally require manufacturer evidence;
- a physical tool-body mass may be accepted from a reputable exact-SKU industrial distributor when the manufacturer does not publish that fact directly;
- battery/tool compatibility should preferably come from manufacturer product relationships, kit composition or explicit compatibility data;
- internal physical measurements may be appropriate for interface geometry that manufacturers and distributors do not publish.

Secondary evidence must never be silently represented as manufacturer-stated evidence. Exact model/SKU identity, raw evidence and source provenance must remain attached to the accepted claim.

Evidence priority only applies after the resolved source itself has been verified against the expected identity. A request sent to a manufacturer domain is not sufficient on its own: before a claim receives manufacturer priority, the resolved product-detail page or document must identify the expected product. The same principle applies to secondary evidence: an exact-SKU request that redirects to a search, fallback or different-product page must not inherit exact-SKU qualification merely because the requested SKU appears somewhere in the URL or aggregate body.

Conflicting values must be retained and reconciled explicitly rather than hidden by source precedence. Reconciliation should be evaluated at the highest applicable **verified** evidence priority; lower-priority disagreement remains in provenance but does not automatically block a decisively established higher-priority value, while disagreement at the same highest priority remains a blocking conflict.

### Evidence fitness and acquisition reliability are separate

A source should be evaluated along two independent dimensions:

- **evidence fitness** asks whether the source is acceptable for the property being asserted and whether exact product identity can be established;
- **acquisition reliability** asks whether the ingestion runtime can retrieve that source deterministically and consistently at acceptable cost.

A source can therefore be evidence-qualified but operationally unsuitable for unattended ingestion. Repeated access blocks, anti-bot responses or unstable delivery should be recorded as acquisition telemetry rather than interpreted as evidence-quality failures.

Likewise, failure to fetch an optional secondary source must not invalidate manufacturer evidence or other graph nodes that were acquired successfully.

Where several evidence-qualified providers can establish the same property, normal ingestion should prefer providers that are both trustworthy and reliably retrievable. Provider-specific reliability history may later justify skipping or deprioritizing sources that repeatedly fail in the target runtime, but the benchmark should collect that evidence before introducing a more elaborate source registry or ranking system.

## Cordless-tool operational mass

For TetherLens load reasoning, the relevant mass is the configured tool in use, not an arbitrary bare-tool value.

The benchmark should therefore resolve separately:

```text
tool-body mass + installed battery mass = operational mass profile
```

A tool with several compatible batteries may have several valid operational mass profiles.

The objective is to recover enough graph structure and physical facts to represent those configurations explicitly rather than choosing one battery silently.

## Milwaukee development case

The primary Milwaukee development case is now:

```text
2607-20 — M18 1/2 in Hammer Drill/Driver
```

This replaces `2602-20` as the main Milwaukee benchmark/development SKU.

The earlier difficulty with `2602-20` was materially affected by product selection: it is a legacy product that Milwaukee marks as no longer available, and its current first-party data is comparatively sparse. That made it useful as a hard acquisition case but a poor first product for deciding whether Milwaukee's catalogue structure is fundamentally different from Hilti's.

`2607-20` is a better development case because the product and its surrounding catalogue graph are still exposed through normal sales/product surfaces. For example, Milwaukee's `2607-22` kit explicitly contains tool `2607-20` and M18 battery `48-11-1828`, while qualified distributor records can provide additional exact-model physical facts where Milwaukee's own page does not.

The benchmark should therefore test Milwaukee using the same conceptual approach as Hilti:

```text
Milwaukee tool/product identity
  -> Milwaukee kit / related-product / battery relationships
  -> first-party physical facts where available
  -> qualified exact-SKU secondary physical facts where needed
  -> derived operational mass profile
```

The 2026-08-18 live experiment validated this pattern end to end. The first-party graph discovered the `2607-22` and `2607-22CT` kits and their `48-11-1828` and `48-11-1815` batteries. A deterministic exact-SKU secondary provider supplied usable tool-body and `48-11-1828` battery mass, allowing a derived operational profile for `2607-20 + 48-11-1828` with full provenance.

The same experiment also clarified acquisition reliability. Grainger and Home Depot returned HTTP 403 responses in both GitHub Actions and a local run, while the alternative exact-SKU provider succeeded in both environments. The useful conclusion is not that those blocked publishers are intrinsically poor evidence sources; it is that their ordinary HTML surfaces are unsuitable for the current unattended direct-HTTP acquisition path. This distinction should inform future provider selection without forcing product-specific exceptions into the Milwaukee adapter.

`2602-20` should be retained for a later legacy/discontinued-product or hard-case cohort rather than used to shape the primary Milwaukee adapter.

## Representative product selection

Development products should be representative of the catalogue behavior TetherLens expects to ingest in normal operation.

The first product used to design a manufacturer strategy should normally be:

- a current or actively supported product;
- discoverable through the manufacturer's normal catalogue structure;
- representative of the manufacturer's ordinary product relationships; and
- sufficiently documented to test the intended architecture without immediately forcing exceptional recovery techniques.

Legacy, discontinued, sparse or unusually difficult products remain valuable, but should normally be held for a separate hard-case or unseen evaluation cohort after the baseline manufacturer strategy has been established.

This prevents a pathological first SKU from driving unnecessary complexity into the normal ingestion architecture.

## Required-fact resolution

Manufacturer adapters should efficiently exploit manufacturer-specific structure, but they should not be expected to contain bespoke solutions for every missing fact.

The intended ingestion flow is:

```text
identity
  -> deterministic manufacturer acquisition
  -> candidate claims + source relationships
  -> required-fact assessment
  -> deterministic cross-source completion where needed
  -> evidence reconciliation
  -> derived operational/configuration profiles
  -> recommendation-readiness assessment
  -> difficult/general search only for unresolved exceptional cases
```

A missing required fact is a trigger for further resolution, not automatically the end of ingestion.

## Generalization, not golden-SKU overfitting

Golden data is an answer key for scoring. It must not become acquisition configuration.

Benchmark code should not encode product-specific URLs, values, relationships or exceptions merely to make a known golden SKU pass unless the purpose of that seed is explicitly to measure a separate assisted-ingestion mode.

A scalable strategy should work on products that were not used to develop it. Manufacturer evaluation should therefore evolve from isolated golden SKUs toward cohorts containing:

- a development set used to build and debug the adapter/resolver;
- an unseen evaluation set used to measure generalization without additional SKU-specific code; and
- a hard-case/legacy set used to measure how gracefully the architecture handles sparse or discontinued products.

A manufacturer strategy that performs well only on the development SKU has not demonstrated catalogue scalability.

## Economic scalability

A fact that can eventually be found is not necessarily economically ingestible.

The benchmark should record enough telemetry to estimate catalogue-scale cost, including where practical:

- HTTP requests and sources fetched;
- documents downloaded;
- bytes transferred;
- browser-rendering calls;
- paid search/discovery calls;
- LLM calls/tokens;
- elapsed processing time;
- human review/research minutes; and
- new product-specific code or configuration.

The objective is not simply to minimize requests. More expensive fallback acquisition can be justified when it materially increases recommendation readiness, but it should be visible as a marginal cost rather than becoming the default path.

## Benchmark interpretation rules

The following rules should guide future benchmark design and scoring:

1. **Useful output is the hard product criterion.** A required fact left unresolved is a product-readiness failure even when the failure is diagnosed perfectly.
2. **Acquisition diagnostics remain visible.** They explain why a product succeeded or failed and help improve the pipeline.
3. **Use a product graph, not a single-page assumption.** Join identities, relationships and facts across the available evidence graph.
4. **Cross-source evidence is allowed when the property policy permits it.** Manufacturer evidence is preferred, but not every physical fact must come from the same publisher.
5. **Do not reward a particular mechanism.** API, HTML, document or secondary-source acquisition is valuable only insofar as it produces qualified evidence efficiently.
6. **Do not fabricate completeness.** Missing or conflicting evidence must remain explicit.
7. **Do not use goldens as lookup tables.** They validate outputs; they do not tell ingestion where the answer is.
8. **Measure generalization.** Success on unseen products without code changes matters more than success on one hand-tuned SKU.
9. **Measure cost.** A strategy that works but cannot be afforded at catalogue scale has failed the viability question.
10. **Keep provenance first-class.** Derived facts must retain the evidence chain for every operand.
11. **Reserve expensive general search for exceptional cases.** Deterministic manufacturer and qualified-source graph traversal should be exhausted first.
12. **Separate evidence fitness from retrievability.** A trustworthy source that the runtime cannot fetch reliably may remain useful evidence in principle while being unsuitable for the normal unattended acquisition path.
13. **Verify the resolved evidence identity before assigning source priority.** Request origin, domain, or query text alone must not promote a search/fallback/different-product response to manufacturer or exact-SKU evidence.

## Immediate implication for Batch 1

The existing Batch 1 source-surface work remains useful as an exploratory baseline, but product selection and evidence policy should evolve when the exploration identifies a better representative case.

For cordless-tool operational mass:

- Hilti `SF 4-22` remains the reference example for a source graph resolved almost entirely from first-party evidence;
- Milwaukee `2607-20` is the corresponding cross-source development case;
- Milwaukee should be allowed to combine first-party relationships with qualified exact-SKU distributor facts while retaining provenance;
- secondary providers should be judged separately for evidence fitness and runtime acquisition reliability;
- Milwaukee `2602-20` moves to a later legacy/hard-case cohort;
- paid/general search should not be required for the normal Milwaukee path unless deterministic manufacturer/distributor acquisition proves insufficient.

This is the standard future ingestion work should optimize for.