# TetherLens Evidence Model

## Purpose

This document defines how TetherLens records what it knows, where that information came from, and why the recommendation engine is allowed to rely on it.

The evidence model should provide traceability without making product ingestion impractically complex.

## Core model

The MVP uses four core knowledge concepts:

- `Source`
- `Claim`
- `Evidence`
- `Rule`

The relationships are:

`Source -> Evidence -> Claim`

and:

`Source -> Evidence -> Rule`

Evidence is therefore a reusable relationship that supports either a claim or a rule.

## Guiding principles

### 1. Evidence supports facts and rules

A worksite condition such as "restricted space" is not evidence.

It is context.

Evidence supports the rule that explains what restricted space means for a recommendation.

### 2. Provenance belongs at the claim level

A product may have information from several different sources.

For example:

- rated capacity from a datasheet;
- material from a product webpage;
- connector geometry from an internal measurement.

TetherLens should be able to trace each fact independently.

### 3. Different claims require different evidence

There should not be a universal rule that one evidence source is always stronger than another.

The appropriate evidence depends on the claim.

A manufacturer datasheet is the preferred source for rated capacity.

An internal calliper measurement may be perfectly appropriate for a connector opening.

A reputable exact-SKU secondary source may be appropriate for a physical tool or battery mass when the manufacturer does not publish a usable value.

Structured field evidence may be more useful than a manufacturer brochure for practical usability.

### 4. Mandatory safety facts use property-specific evidence requirements

Manufacturer-rated capacities, restrictions and compliance declarations should come from manufacturer evidence.

Physical tool and battery mass should be established from trustworthy evidence bound to the exact product identity. Manufacturer evidence is preferred, but a reputable exact-SKU secondary source may be accepted when manufacturer mass is unavailable or incomplete.

Physical mass should not be visually inferred, estimated from a similar model, or taken from an unverified search/aggregate result for persistent catalogue use.

### 5. Missing secondary evidence should constrain inference, not automatically block a recommendation

Unknown material composition may prevent a chemical-resistance conclusion.

It should not necessarily prevent a baseline load-and-interface recommendation.

### 6. Do not require exact combination-level validation where reusable facts and rules are sufficient

The evidence model should support reasoning from component properties and interface rules.

This avoids an unscalable manual compatibility matrix.

## Source

A `Source` is the artefact from which evidence is obtained.

### MVP fields

```text
Source
- id
- source_type
- title
- publisher
- url                     [where applicable]
- document_revision       [where available]
- publication_date        [where available]
- retrieved_at
- archived_reference      [optional in MVP]
- status
- notes
```

### Suggested source types

- `manufacturer_datasheet`
- `manufacturer_webpage`
- `manufacturer_manual`
- `manufacturer_declaration`
- `manufacturer_compatibility_statement`
- `standard_or_guidance`
- `internal_measurement`
- `internal_test`
- `third_party_test`
- `secondary_published`
- `structured_field_evidence`

### Source status

Suggested values:

- `active`
- `superseded`
- `unavailable`

`retrieved_at` should be mandatory because webpages and product documents change.

## Claim

A `Claim` is an atomic statement about a subject.

### MVP fields

```text
Claim
- id
- subject_type
- subject_id
- property
- value
- unit                    [where relevant]
- value_status
- claim_type
- status
- created_at
- notes
```

### Value status

Suggested values:

- `known`
- `not_published`
- `not_established`
- `not_applicable`

### Claim type

Suggested values:

- `direct`
- `measured`
- `declared_constraint`
- `derived`

### Claim status

Suggested values:

- `accepted`
- `disputed`
- `superseded`

## Evidence

`Evidence` records why TetherLens accepts or considers a Claim or Rule.

### MVP fields

```text
Evidence
- id
- target_type             # claim | rule
- target_id
- source_id
- evidence_method
- source_location         [optional]
- extracted_value         [optional]
- extracted_unit          [optional]
- strength                [optional for claim evidence, useful for rule evidence]
- recorded_by
- recorded_at
- notes
```

### Suggested evidence methods

- `manufacturer_stated`
- `manufacturer_pairing`
- `manufacturer_certification_statement`
- `certificate_reviewed`
- `qualified_secondary_exact_sku`
- `published_geometry`
- `internally_measured`
- `internally_tested`
- `standard_requirement`
- `engineering_judgement`
- `third_party_tested`
- `derived_from_claims`
- `structured_field_observation`

The exact vocabulary can evolve.

## Rule

A `Rule` contains reusable recommendation logic.

### MVP fields

```text
Rule
- id
- name
- rule_type
- description
- inputs
- condition
- outcome
- severity                [where relevant]
- status
- version
- owner
- notes
```

### Suggested rule types

- `hard_constraint`
- `compatibility`
- `context_preference`
- `caution`
- `policy`

### Example: capacity rule

```text
name:
  Component capacity must meet object load

rule_type:
  hard_constraint

inputs:
  object.mass
  component.rated_capacity

condition:
  component.rated_capacity >= object.mass

outcome:
  pass -> continue
  fail -> exclude configuration
```

### Example: snagging preference

```text
name:
  Prefer reduced free length in high-snag environments

rule_type:
  context_preference

inputs:
  context.snag_risk
  tether.length / tether_behaviour

condition:
  context.snag_risk = high

outcome:
  rank lower-free-length options higher
```

## Mandatory claim evidence

### Tool mass

Required evidence:

- trustworthy physical-mass evidence bound to the exact tool or battery identity.

Preferred examples:

- manufacturer datasheet;
- technical product page;
- manufacturer manual.

Acceptable fallback where manufacturer mass is unavailable or incomplete:

- a reputable secondary product-detail source that is verified against the exact SKU/model and clearly states the relevant physical mass.

Not acceptable as the normal catalogue source:

- visual estimation;
- user estimate;
- inferred mass from a similar model;
- a secondary search/aggregate page whose resolved identity is not the expected exact product.

Secondary physical-mass evidence must remain labelled as secondary evidence; it must never be represented as manufacturer-stated evidence.

### Rated capacity

Required source:

- manufacturer information for every applicable load-bearing component.

This may apply to:

- tether;
- tool attachment;
- anchor attachment;
- container.

The absence of a known manufacturer rating is a hard data gap.

### Interface compatibility

Acceptable evidence routes include:

#### Published geometry

Published dimensions are sufficient where they establish valid engagement.

#### Internal measurement

Relevant connector or interface dimensions can be measured internally.

#### Explicit manufacturer compatibility

A manufacturer explicitly recommends two components for use together.

#### Manufacturer kit relationship

Components sold together as a kit can be treated as explicitly compatible for that intended interface.

#### Derived interface compatibility

A validated reusable rule may establish compatibility from known geometry or interface classes.

Where geometry alone is insufficient to establish correct seating or engagement, a physical fit test or more specific rule may be required.

## Secondary claims

Secondary claims improve recommendation quality but are not necessarily required for baseline viability.

Examples:

- detailed material composition;
- chemical resistance;
- standards compliance;
- tether form or behaviour;
- temperature limits;
- detailed component dimensions;
- practical usability.

### Material

Material should be stored at the resolution actually known.

Examples:

- `polymer`
- `polyester`
- `aramid`
- `UHMWPE / Dyneema`

The system should not invent precision.

### Standards compliance

TetherLens should separate **what the manufacturer claims** from **what supporting artefact TetherLens has been able to obtain and inspect**.

These are related but should not be collapsed into a single compliance tier. Public certificate availability is partly a documentation/accessibility issue and should not become a proxy for manufacturer credibility.

The compliance claim may record distinctions such as:

- explicit manufacturer declaration that the product complies with a named standard;
- explicit manufacturer statement that the product is third-party certified/tested;
- general manufacturer reference to a standard without a product-specific compliance statement; and
- no established compliance claim.

Separately, the supporting artefact status may record:

- `public_and_reviewed`
- `available_on_request`
- `manufacturer_states_exists`
- `not_identified`

For example, if a manufacturer explicitly states that a product complies with ANSI/ISEA 121 and that third-party certification documentation is available on request, TetherLens can record those manufacturer claims even if it has not yet obtained the certificate. If the certificate is later obtained, a new Source/Evidence record strengthens the provenance without changing the historical fact that the manufacturer made the original compliance claim.

A general marketing reference to a standard should still not be converted into a stronger product-specific declaration than the manufacturer actually makes.

Unless standards compliance is configured as a hard policy requirement, certificate accessibility alone should not materially penalise an otherwise viable worker-facing recommendation.

### Chemical resistance

Preferred evidence:

- product-specific manufacturer data;
- controlled product testing.

Fallback evidence may include:

- known constituent material properties;
- internal engineering assessment.

Material-derived compatibility should be treated as derived environmental evidence, not as proof that the complete product assembly has been tested for that exposure.

### Practical usability

Practical usability is inherently context-sensitive.

Possible evidence includes:

- structured field trials;
- internal user testing;
- aggregated worker feedback.

Raw user feedback should not automatically create or modify recommendation rules.

A future workflow may be:

`raw observations -> aggregated signal -> review -> reusable rule`

## Manufacturer endorsement states

Suggested values:

- `explicitly_endorsed`
- `explicitly_restricted`
- `not_addressed`
- `unknown`

TetherLens should not infer an explicit restriction merely because a manufacturer only markets its own ecosystem.

## Rule evidence

Rules should also be evidence-backed.

A rule may be supported by:

- standards;
- manufacturer guidance;
- controlled internal testing;
- engineering judgement;
- structured field evidence.

A simple qualitative strength model may be sufficient:

- `authoritative`
- `supported`
- `provisional`

The evidence burden should depend on the consequence of the rule being wrong.

A hard load-capacity rule requires strong support.

A practical ranking preference such as reducing free tether length in congested areas can tolerate a broader evidence base.

## Evidence identity and priority

Evidence priority only applies after source identity has been verified for the claim being asserted.

A request to a manufacturer domain does not automatically make the resolved response manufacturer evidence. Before a fact receives `manufacturer_stated` status, the resolved product-detail page or document must be bound to the expected product identity. Likewise, a secondary source must resolve to the expected exact-SKU product record before it can receive exact-SKU secondary status.

For properties where evidence priority is defined, reconciliation should be evaluated at the **highest applicable verified priority**. Lower-priority disagreement remains part of the provenance record but does not automatically block a claim when a higher-priority verified source decisively establishes the value.

## Conflicting evidence

The MVP should preserve conflicting evidence rather than discard it.

Where sources disagree:

1. preserve all evidence records;
2. determine the highest applicable verified evidence priority for the property;
3. if claims at that highest priority disagree materially, mark the affected fact as disputed and require reconciliation/review before using it as a mandatory fact;
4. if the highest-priority verified claims agree, they may establish the accepted value even when lower-priority evidence differs;
5. retain lower-priority conflicting or superseded evidence for traceability.

Mandatory safety facts should not be silently resolved by convenience, request order, or unverified source labels.

## Derived claims and dependency

Where a claim is derived, TetherLens should retain enough information to explain the derivation.

Example:

```text
Connector A gate opening = 18 mm
Attachment B required clearance = 12 mm
Compatibility Rule 7 applies
        ↓
Derived claim:
Connector A can engage Attachment B
```

The MVP may compute this at runtime rather than persist a complete dependency graph.

## Evidence-model success criteria

The model is successful if:

- every mandatory fact used in a recommendation can be traced to a source;
- the same source can support many claims;
- one product can use different sources for different properties;
- missing secondary data does not force false precision;
- rules can cite why they exist;
- conflicting evidence can be represented without data loss; and
- evidence capture remains simple enough for catalogue ingestion to scale.
