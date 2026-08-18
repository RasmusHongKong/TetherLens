# TetherLens Product Ingestion

## Purpose

This document defines how products and tethering components enter the TetherLens knowledge base.

The ingestion process is a core part of product viability.

If adding and maintaining products requires too much application-specific judgement, TetherLens will not scale.

## Guiding principle

> **Ingestion captures what a product is, not where someone thinks it should be used.**

The ingestion workflow should collect reusable low-level facts.

Application suitability should normally be derived later from:

`product facts + context + rules`

## Ingestion model

TetherLens should support multiple ingestion channels that converge on the same staging, review, and acceptance process.

```text
Manufacturer websites / documents
            ↓
Automated discovery and extraction ─┐
                                    │
Internal staff entry ───────────────┼→ Staging → Normalize / validate → Review → Accepted claims → Product catalogue
                                    │
Future user submissions ────────────┘
```

The channel should not change the evidence standard. An automatically extracted fact, staff-entered fact, and user-submitted fact should all become candidate information until the required source and review conditions are met.

### MVP ingestion priority

The MVP should prioritise:

1. automated or semi-automated extraction from public manufacturer sources;
2. human review/correction of extracted facts;
3. internal measurement or research for important gaps; and
4. repeat/refresh extraction to identify new products or changed information.

User submissions should be anticipated architecturally but do not need to be proven at scale during the MVP.

### Accepted workflow

```text
Identify or discover product
      ↓
Create staged product candidate
      ↓
Attach source(s)
      ↓
Extract / enter primitive technical facts
      ↓
Normalize and validate units / vocabulary
      ↓
Review candidate claims
      ↓
Identify mandatory gaps
      ↓
Measure or enrich where necessary
      ↓
Accept claims
      ↓
Catalogue / recommendation-ready for supported paths
```

Automated refreshes should generate candidate changes for review rather than silently overwriting accepted hard facts.

## What ingestion should capture

### Common identity data

- manufacturer;
- product name;
- model;
- SKU / product code;
- category;
- source references.

### Tool facts

At minimum for a catalogued tool:

- verified physical mass suitable for load reasoning.

Manufacturer evidence is preferred for tool and battery mass. Where the manufacturer does not publish a usable physical mass, a reputable secondary source may be used if the resolved source is verified against the exact SKU/model and provenance is retained. Physical mass must not be inferred from an image, a similar model, or an aggregate/search result that has not been bound to the expected product identity.

Interface information should be captured where available, but the model must not assume that a manufacturer will document a tether-specific attachment point.

Useful interface enrichment includes:

- native tether-point status;
- dedicated tether-eye geometry;
- captive holes or handles;
- grip / neck / waist geometry relevant to controlled loop or retrofit attachment methods;
- dimensions required by applicable ToolAttachment rules;
- evidence describing whether a feature is documented, measured, or observed.

The ingestion workflow must distinguish:

- `observed_absent` — there is no relevant native tether point;
- `not_documented` — manufacturer information does not address it; and
- `unknown` — TetherLens has not yet established the status.

`not_documented` must not be interpreted as `not tetherable`. A tool may still support a loop/cinch method or a retrofit ToolAttachment based on geometry.

Other useful enrichment includes:

- dimensions where relevant;
- materials where known;
- manufacturer-declared limits.

### Tether facts

At minimum:

- manufacturer-rated capacity;
- tether length or working-length range;
- enough connection-point information to reason about the required interfaces.

Tether ingestion should represent the lanyard body and connection points separately. Useful facts include:

- lanyard/body material(s);
- number of connection points / legs;
- connection-point role;
- interface type for each point;
- connector specification for each discrete connector;
- connector material;
- gate opening / relevant geometry;
- locking mode;
- opening action count;
- auto-locking behaviour;
- swivel;
- captive-eye features;
- tether behaviour/form;
- standards declarations;
- environmental limits;
- explicit manufacturer restrictions.

Where the same connector is reused across several tether products, its specification and internal measurements should be stored once and referenced rather than duplicated.

### ToolAttachment facts

At minimum:

- manufacturer-rated capacity;
- tool-side attachment/interface information;
- tether-side interface information.

Useful enrichment:

- materials;
- dimensional limits;
- explicit compatible products;
- environmental limits.

### AnchorAttachment facts

At minimum:

- manufacturer-rated capacity;
- tether-side interface information;
- anchorage-side attachment/interface information.

Useful enrichment:

- materials;
- intended anchorage types;
- environmental limits;
- explicit product restrictions.

### Container facts

At minimum where the product is used in a recommendation:

- manufacturer-rated capacity;
- relevant closure/retention properties;
- attachment/anchorage interface information.

Useful enrichment:

- dimensions;
- materials;
- environmental limits.

## What ingestion should normally not capture

Avoid application-classification fields such as:

```text
suitable_for_hot_work
suitable_for_scaffolding
suitable_for_offshore
suitable_for_tight_spaces
suitable_for_pipework
```

These create an unscalable product-by-application matrix.

Instead, capture the facts that allow those conclusions to be derived.

Example:

```text
material = polyester
length = 1.8 m
connector = aluminium screwgate
```

Then the recommendation engine evaluates those facts against context using reusable rules.

## Exception: explicit manufacturer constraints

If a manufacturer explicitly states a product-specific limit, retain it.

Examples:

- maximum operating temperature;
- explicit chemical restriction;
- "use only with attachment X";
- "not intended for use around rotating equipment";
- explicit compatible product pairing.

These should be represented as source-backed declared constraints, not vague application tags.

## Mandatory recommendation facts

A product becomes recommendation-ready for baseline use when the facts required for its role are known.

### Object/tool mass

Must be established from evidence that is acceptable for the physical mass property and bound to the exact product identity.

Manufacturer information is preferred. Where manufacturer mass is unavailable or incomplete, a reputable exact-SKU secondary source may establish tool-body or battery mass. The source and evidence method must remain explicit, and unverified search/aggregate pages, visual estimates, similar-model inference, or other ambiguous identity matches are not acceptable for catalogue load reasoning.

### Rated capacity

Must come from manufacturer information for every applicable load-bearing component.

### Interface compatibility

A proposed configuration must have enough information to establish its required physical connections through at least one acceptable route:

- published dimensions;
- internal measurement;
- explicit manufacturer compatibility;
- manufacturer kit relationship;
- observed/confirmed tool geometry evaluated by a validated rule; or
- another validated reusable interface rule.

A tool does not need a manufacturer-documented tether point to enter the catalogue. For a particular recommendation path, however, TetherLens must be able to establish a valid connection method from the available geometry, a native feature, a loop/cinch rule, or a ToolAttachment.

## Recommendation-readiness

Suggested internal states:

### Identified

Basic product identity exists.

### Sourced

At least one credible source is attached.

### Incomplete

One or more mandatory facts are missing.

### Recommendation-ready

Mandatory facts are available.

### Enriched

Additional technical data improves context-based recommendations.

### Field-enriched

Reviewed field evidence has contributed to reusable application knowledge.

These states are internal workflow aids, not necessarily user-facing labels.

## Internal measurement

Internal measurement is expected to be an important enrichment method, especially for connector and attachment geometry that manufacturers do not consistently publish.

A simple measurement record should capture:

- product/component ID;
- property measured;
- value;
- unit;
- measurement method;
- tool used;
- date;
- person responsible;
- optional photo/reference.

Internal measurements should create source/evidence records rather than silently overwriting product fields.

## Source handling

One product may require several sources.

Example:

```text
rated capacity -> manufacturer datasheet
material       -> manufacturer webpage
gate opening   -> internal measurement
```

The ingestion interface should make this normal rather than forcing one "product source".

## Automated extraction and refresh

Automated scraping or document extraction is expected to be the most scalable way to build and maintain the initial catalogue.

Automation should:

- discover candidate products and sources;
- extract candidate primitive facts;
- retain the source location where practical;
- normalize units and common vocabulary;
- flag missing mandatory data; and
- compare newly extracted values with currently accepted claims.

Automation should **not** silently replace accepted hard facts.

Example:

```text
Accepted rated capacity: 5 kg
New manufacturer-page extraction: 4.5 kg

Outcome: flag change for review
```

A periodic refresh process can later be used to identify:

- new products;
- discontinued products;
- updated datasheets;
- changed technical facts; and
- newly published evidence.

## User submissions

Future user submissions should use the same staging model.

User-provided information may be valuable for:

- identifying missing tools/products;
- supplying photos;
- suggesting manufacturer sources;
- reporting geometry or usability observations; and
- surfacing recurring field problems.

User submissions should not directly overwrite accepted mandatory claims. They should become staged candidates for review.

The MVP does not need to validate user-based ingestion at scale, but the ingestion model should not prevent it later.

## Missing data

Missing data should be explicit.

Suggested states include:

- not published;
- not established;
- not applicable.

Missing secondary information should not block a product unnecessarily.

Missing mandatory information should prevent recommendation-readiness for the affected use.

## Product ingestion should require minimal application expertise

The person adding a product should mostly answer questions such as:

- What does it weigh?
- What is it rated to?
- How long is it?
- What material does the manufacturer identify?
- What connector does it use?
- What are the relevant interface dimensions?
- Where did this information come from?

They should not routinely need to answer:

- Is this good for scaffolding?
- Is this good in a refinery?
- Is this ideal around pipework?
- Would I personally use this in a tight space?

Those decisions belong in reusable rules.

## Suggested MVP ingestion tooling

A polished administration system is not required initially.

The MVP may combine:

- scraping/document extraction scripts;
- structured review forms;
- a controlled spreadsheet;
- YAML/JSON records with validation; or
- a lightweight internal web interface.

Whatever tooling is used should:

- make mandatory gaps obvious;
- attach sources at field/claim level;
- support internal measurements;
- prevent invalid units or obvious data errors;
- distinguish unknown from zero/false;
- show whether the product is recommendation-ready.

## Ingestion metrics

The MVP should measure the supply-side workflow.

### Time to recommendation-ready

Human time required from initial product identification to recommendation-ready status.

### Public-data completion rate

Percentage of products that can become recommendation-ready from public first-party information alone.

### Enrichment rate

Percentage requiring internal measurement or additional research.

### Claims per product

Useful for estimating catalogue maintenance burden.

### Sources per product

Useful for understanding how fragmented manufacturer data is.

### Automated extraction yield

Percentage of required and useful primitive facts that can be extracted correctly before human enrichment.

### Refresh-change rate

Number and type of product additions, removals, and fact changes identified by a repeat extraction pass.

### Review burden

Human time required to review and accept automatically extracted candidate claims.

### Rule reuse

Percentage of new products handled entirely by existing rules.

### Exception rate

Percentage requiring a bespoke rule or manual compatibility relationship.

### Compatibility leverage

Number of candidate configurations unlocked by adding one new product without manually authoring each pairing.

## Two-stage ingestion test

The MVP should use two ingestion batches.

### Batch 1

Build an initial diverse catalogue and create the reusable rules required.

### Batch 2

Freeze the core domain model and rules, then ingest a new set of tools and tethering components.

The second batch should reveal whether the model truly scales.

A strong outcome is:

`new product -> facts + evidence -> recommendations`

A weak outcome is:

`new product -> specialist analysis -> new bespoke rule -> manual pairings -> extensive updates to existing products`

## Future ingestion opportunities

Once the manual model is proven, AI may help:

- find manufacturer sources;
- extract candidate facts;
- highlight conflicting sources;
- suggest missing fields;
- identify likely duplicate products;
- prepare claims for human approval.

AI-assisted ingestion should remain reviewable and should not silently establish mandatory safety facts without an accepted source.

## Ingestion success criteria

The ingestion model is successful if:

- catalogue maintainers can add products quickly;
- mandatory facts remain traceable;
- application judgement is rarely required during product entry;
- internal measurement fills geometry gaps efficiently;
- existing rules handle most new products;
- the exception rate remains low as the catalogue grows; and
- product maintenance does not require editing a large compatibility matrix.
