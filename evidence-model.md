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

Where a derived Claim is persisted for operational reuse, it may additionally depend on other Claims:

`input Claims -> derived Claim`

That dependency is distinct from Evidence. The input Claims retain their own source Evidence; the dependency records which accepted facts were used by the derivation.

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
- connector geometry from an internal measurement;
- tool-body mass from one exact-SKU source; and
- battery mass from another exact-SKU source.

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

Physical tool-body and battery mass should be established from trustworthy evidence bound to the exact product identity. Manufacturer evidence is preferred, but a reputable exact-SKU secondary source may be accepted when manufacturer mass is unavailable or incomplete.

Physical mass should not be visually inferred, estimated from a similar model, or taken from an unverified search/aggregate result for persistent catalogue use.

For a cordless Tool with an interchangeable Battery, these primitive physical-mass Claims are not themselves sufficient to establish the mass used by load reasoning. TetherLens must also establish a manufacturer-backed Tool/Battery configuration relationship and derive an operational-mass Claim/profile for the exact combination.

### 5. Missing secondary evidence should constrain inference, not automatically block a recommendation

Unknown material composition may prevent a chemical-resistance conclusion.

It should not necessarily prevent a baseline load-and-interface recommendation.

### 6. Do not require exact tethering combination-level validation where reusable facts and rules are sufficient

The evidence model should support reasoning from component properties and interface rules.

This avoids an unscalable manual compatibility matrix.

This principle does not mean that interchangeable configuration products may be combined arbitrarily. Where a Tool's operational mass depends on an installed Battery, the Tool/Battery relationship itself should be manufacturer-backed because it establishes that the physical configuration whose mass is being derived is valid.

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

## Claim dependency

`ClaimDependency` records which Claims were inputs to a persisted derived Claim.

It is required when TetherLens persists a derived value that is itself used as an operational safety input, such as a cordless Tool operational mass.

Suggested MVP fields:

```text
ClaimDependency
- derived_claim_id
- input_claim_id
- role_code
- sequence_no              [optional]
```

For example:

```text
Tool body mass Claim = 1.360777 kg
Battery 48-11-1828 mass Claim = 0.725748 kg
        ↓
Operational mass Claim = 2.086525 kg
```

The operational Claim should have dependencies identifying the exact body-mass and battery-mass Claims. If either accepted primitive Claim is superseded, the dependent operational Claim/profile must be re-derived before recommendation use.

A human-readable derivation note or list of source URLs is not a substitute for these structured dependencies where the derived value is persisted as a mandatory operational fact.

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

`derived_from_claims` describes the method for a derived Claim; the specific input Claims should be represented through `ClaimDependency` when that derivation is persisted for operational use.

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
  object.operational_mass
  component.rated_capacity

condition:
  component.rated_capacity >= object.operational_mass

outcome:
  pass -> continue
  fail -> exclude configuration
```

For a cordless catalogue Tool, `object.operational_mass` should resolve from the applicable valid Tool/Battery profile rather than bare-tool mass.

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

### Tool and Battery physical mass

Required evidence:

- trustworthy physical-mass evidence bound to the exact Tool or Battery identity.

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

### Cordless operational mass

For a cordless Tool requiring an installed interchangeable Battery, the mandatory mass used by load reasoning is a derived configuration fact.

An accepted operational-mass profile should require:

- an accepted exact Tool-body mass Claim;
- an accepted exact Battery-mass Claim;
- a manufacturer-backed Tool/Battery relationship such as explicit compatibility or kit composition; and
- a derived operational-mass Claim whose structured dependencies point to those primitive mass Claims.

If several Batteries are valid, several operational-mass Claims/profiles may be valid. The recommendation workflow must resolve which profile applies rather than treating any one as a universal Tool mass.

If the installed profile cannot be resolved, bare-tool mass must not be substituted for load reasoning.

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

A manufacturer-backed Tool/Battery relationship used to establish an operational configuration is a specific product-configuration fact, not a general rule that all tethering components must be from one manufacturer.

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

For an operational-mass profile, primitive Tool-body and Battery mass Claims should each be reconciled under this rule before the derived profile is accepted. A conflict in a required highest-priority primitive Claim blocks or invalidates the dependent profile until reconciled.

## Conflicting evidence

The MVP should preserve conflicting evidence rather than discard it.

Where sources disagree:

1. preserve all evidence records;
2. determine the highest applicable verified evidence priority for the property;
3. if claims at that highest priority disagree materially, mark the affected fact as disputed and require reconciliation/review before using it as a mandatory fact;
4. if the highest-priority verified claims agree, they may establish the accepted value even when lower-priority evidence differs;
5. retain lower-priority conflicting or superseded evidence for traceability.

Mandatory safety facts should not be silently resolved by convenience, request order, or unverified source labels.

Dependent operational Claims must not remain silently active after one of their required primitive inputs becomes disputed or superseded.

## Derived claims and dependency

Where a claim is derived, TetherLens should retain enough information to explain the derivation.

Example runtime-only derivation:

```text
Connector A gate opening = 18 mm
Attachment B required clearance = 12 mm
Compatibility Rule 7 applies
        ↓
Derived conclusion:
Connector A can engage Attachment B
```

Many recommendation conclusions can remain runtime-only and do not require a persisted dependency graph.

Where a derived Claim is persisted as a reusable operational fact, however, its dependency chain should be structured. Cordless operational mass is the current MVP example:

```text
Tool-body mass Claim ──┐
                      ├──> Operational-mass Claim
Battery-mass Claim ───┘

Manufacturer Tool/Battery relationship -> OperationalMassProfile validity
```

This distinction keeps the evidence model lightweight for ordinary runtime reasoning while preserving deterministic traceability for derived values used repeatedly by safety-critical load checks.

## Evidence-model success criteria

The model is successful if:

- every mandatory fact used in a recommendation can be traced to a source;
- persisted derived operational facts can be traced to their exact accepted input Claims;
- exact Tool/Battery configuration validity can be traced to manufacturer evidence;
- the same source can support many claims;
- one product can use different sources for different properties;
- missing secondary data does not force false precision;
- rules can cite why they exist;
- conflicting evidence can be represented without data loss and invalidates dependent operational facts where necessary; and
- evidence capture remains simple enough for catalogue ingestion to scale.
