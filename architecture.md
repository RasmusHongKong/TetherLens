# TetherLens Architecture

## Purpose

This document describes the logical architecture of TetherLens.

It intentionally avoids committing to a specific frontend framework, database technology, AI provider, or deployment platform.

The purpose is to define the boundaries between:

- product knowledge;
- evidence and provenance;
- reusable rules;
- documented relationships/installations;
- recognition;
- work context;
- policy; and
- the recommendation engine.

## Architectural principle

The central architectural principle is:

> **The catalogue describes what products are. Evidence records what sources actually establish. Rules describe how reusable properties matter. The recommendation engine combines those facts, relationships and rules with the current work context.**

TetherLens should not depend on manually authoring every possible tool-to-tether combination. It should also not assume that manufacturers publish enough geometry to explain every valid installation path.

Therefore:

- reusable physical/topological rules are preferred when the evidence supports them;
- exact geometry is strong evidence, not a universal prerequisite;
- a manufacturer-documented relationship may establish one narrowly scoped known-valid path when lower-level geometry is incomplete;
- that relationship must not be silently promoted to a generic rule or universal exclusion; and
- missing physical facts must remain unknown rather than being invented to make an existing rule fit.

See `compatibility-evidence-and-inference.md` for the governing evidence/inference boundary.

## High-level architecture

```text
                         SUPPLY SIDE

 Manufacturer web/docs      Internal staff       Future users
          │                      │                    │
          └──────────────┬───────┴──────────┬─────────┘
                         ▼                  │
                 ┌────────────────┐         │
                 │ Ingestion      │◄────────┘
                 │ staging/review │
                 └───────┬────────┘
                         ▼
                    ┌─────────┐
                    │ Sources │
                    └────┬────┘
                         │
                         ▼
                    ┌──────────┐
                    │ Evidence │
                    └────┬─────┘
                         │
              ┌──────────┴───────────┐
              ▼                      ▼
          ┌────────┐              ┌───────┐
          │ Claims │              │ Rules │
          └────┬───┘              └───┬───┘
               │                      │
               ▼                      │
        ┌───────────────┐             │
        │ Product data  │             │
        │ + documented  │             │
        │ relationships │             │
        └───────┬───────┘             │
                └──────────┬───────────┘
                           ▼
                   ┌────────────────┐
                   │ Recommendation │
                   │     Engine     │
                   └───────┬────────┘
                           ▲
                ┌──────────┴───────────┐
                │                      │
       Resolved tool profile       Work context
                ▲                      ▲
          ┌─────┴──────┐               │
          │            │               │
   Catalogue tool   Generic tool     Worker /
      identity        profile        site data
          ▲            ▲
          └─────┬──────┘
                │
           Vision / user
            resolution

                         DEMAND SIDE
```

## Main architectural layers

### 1. Product catalogue

The product catalogue contains the current accepted technical values used by the recommendation engine.

Core tethering product categories include:

- Tool
- Tether
- ToolAttachment
- AnchorAttachment
- Container

The catalogue may also contain supporting configuration products such as interchangeable Batteries when they are required to establish the operational state of a Tool. Supporting products are not themselves tethering components merely because they participate in the product graph.

The catalogue should favour primitive technical attributes rather than application classifications.

Examples:

- tool-body and battery mass where configuration-dependent;
- derived operational mass profiles;
- rated capacity;
- tether length;
- lanyard/body material;
- tether connection points and legs;
- reusable connector specifications;
- connector material, gate geometry, locking mode, action count, swivel, and captive-eye features;
- tool/interface geometry **where established**;
- functional feature role/location where exact geometry is not established;
- native tether-point status;
- material;
- explicit product limits; and
- exact accepted product/interface ownership needed to scope manufacturer evidence.

For cordless tools with interchangeable batteries, the catalogue should preserve the graph explicitly:

```text
tool identity + accepted tool-body mass
       │
       ├── manufacturer-backed compatible battery relationship
       │
       └── exact battery identity + accepted battery mass
                         │
                         ▼
                OperationalMassProfile
```

One Tool may therefore have several operational mass profiles. Load reasoning must use a specific valid profile rather than a bare-tool value or an arbitrary battery.

The operational catalogue may also retain exact accepted relationships that are useful before a generic physical rule is known. For example, a documented ToolAttachment installation can identify the Tool, attachment product and resolved Tool feature without asserting unsupported geometry. Such a relationship remains distinct from generic product attributes and reusable rules.

### 2. Evidence and provenance

The evidence layer records what supports a claim, relationship, installation or rule.

The core concepts are:

- Source;
- Claim;
- Evidence; and
- Rule.

This layer allows TetherLens to answer:

- where did this value or relationship come from?
- how was it established?
- when was it checked?
- is it directly stated, measured, derived, or inferred?
- which exact product/model/interface did the evidence apply to?
- which accepted facts does a derived value depend on?
- why does this recommendation rule exist?

The evidence layer should support traceability without forcing the recommendation engine to perform expensive provenance traversal for every user interaction.

Derived operational facts that are persisted for reuse should retain explicit dependency links to their accepted input Claims. For example, a cordless operational-mass claim should depend on the accepted tool-body mass Claim and the accepted battery-mass Claim, while the profile itself also records the manufacturer-backed tool/battery relationship that makes the configuration valid.

Manufacturer installation/compatibility evidence must preserve the narrowest supported scope. Product-scoped connection evidence belongs to the exact interface owner, model-specific instructions must be bound to the matching model-local source section, and evidence from several sources may be aggregated only without separating the primary source URL from its raw wording/method metadata.

### 3. Ingestion staging and review

Product knowledge may arrive through several channels:

- automated manufacturer-web/document extraction;
- internal staff entry; and
- future user submissions.

All channels should converge on a staging/review process before candidate information becomes accepted knowledge.

Automated extraction should create candidate claims and candidate changes rather than silently overwriting accepted mandatory facts.

This layer allows TetherLens to scale catalogue maintenance while preserving the evidence standards of the accepted knowledge base.

Document parsers must also preserve local attribution. A product/model name appearing somewhere in a combined document does not authorize unrelated sections, and repeated or alternative documented routes should remain distinct evidence records unless they are semantically the same relationship.

### 4. Rules

Rules contain reusable domain reasoning.

Examples include:

- load must not exceed rated capacity;
- interface geometry must permit a valid connection;
- person anchoring may be restricted by policy above a configured threshold;
- reduced free tether length should be preferred where snag risk is elevated;
- a documented product limit may invalidate a configuration in a particular environment.

Rules should be reusable across products wherever possible.

A documented product relationship is not automatically a Rule. If a manufacturer says attachment X installs at feature Y on Tool A, TetherLens may execute that exact accepted path when the evidence is sufficient for the relationship but insufficient for a generic geometry rule. Promotion to a reusable Rule requires independent support for the rule's predicates and scope.

Future reusable rules that originate from cross-product inference should retain an epistemic/provenance basis distinct from direct measurement or explicit technical description.

### 5. Tool resolution and recognition

Recognition attempts to identify the likely tool from an image.

Recognition may be probabilistic and should prefer an exact or sufficiently specific catalogue match where one is available.

However, the field workflow must also support tools that are generic, unbranded, absent from the catalogue, or impossible for the worker to identify exactly.

The tool-resolution layer should therefore produce either:

- a confirmed catalogue-tool identity plus the applicable operational configuration where required; or
- a session-level generic tool profile containing only the facts required to continue the recommendation safely.

For a cordless catalogue tool with interchangeable batteries, the resolved tool profile must identify a valid `OperationalMassProfile` or otherwise resolve which installed battery configuration is being used. The recognition layer does not need to infer the battery automatically, but the recommendation engine must not silently substitute bare-tool mass or choose an arbitrary compatible battery.

Generic runtime values such as user-provided mass or observed geometry are context for that recommendation. They should not silently become accepted catalogue Claims.

Recognition should not be responsible for inventing safety-critical product facts or recommendation logic.

### 6. Context

Context describes the current work situation.

Examples include:

- restricted space;
- snagging risk;
- contaminants;
- required reach;
- available anchorage method;
- site or task constraints.

Context may come from:

- explicit worker input;
- configured site data;
- inferred image information, where sufficiently reliable; or
- other future data sources.

Context is not evidence. It is an input to rules.

### 7. Policy

Policy represents organisation, site, project, or programme constraints.

Policy should be separate from technical suitability and from manufacturer position.

Examples include:

- maximum permitted operational mass for person anchoring;
- required product families;
- prohibited components;
- site-specific restrictions;
- requirements for a particular manufacturer's endorsement.

A manufacturer-documented combination is positive manufacturer evidence; whether a site permits only OEM-documented combinations is a separate policy question.

### 8. Recommendation engine

The recommendation engine combines:

- resolved tool profile — exact catalogue tool/configuration or generic runtime profile;
- product data;
- reusable technical rules;
- accepted exact installation/connection evidence where applicable;
- candidate components/configurations;
- hard constraints;
- contextual rules;
- evidence limitations; and
- policy.

It should produce the most useful defensible recommendation available.

Geometry-backed and evidence-bound ToolAttachment routes can coexist in the same run. Evidence-bound installation may establish the documented Tool-to-attachment step, while ordinary load, downstream connection, contextual and policy evaluation continue unchanged.

## AI boundary

AI can assist with:

- image-based tool recognition;
- extracting candidate product facts from datasheets or webpages;
- identifying potentially relevant context from an image;
- asking contextual questions;
- explaining a structured recommendation in clear language; and
- helping catalogue maintainers identify missing data or candidate patterns.

AI should not be the final persistent source of truth for:

- catalogued tool-body or battery mass;
- tool/battery compatibility relationships;
- derived operational mass profiles;
- rated capacity;
- interface dimensions;
- exact feature geometry not established by evidence;
- product limits;
- compatibility rules; or
- policy.

Those should resolve to structured facts, explicit relationships/rules, and traceable evidence.

## Deterministic and probabilistic responsibilities

TetherLens should deliberately separate probabilistic and deterministic tasks.

### Probabilistic

- computer vision;
- document extraction;
- contextual interpretation;
- ranking candidate tool identities;
- candidate pattern discovery for later validation;
- natural-language explanation.

### Deterministic or controlled

- derivation of operational mass from accepted tool-body and battery mass;
- load-capacity comparison;
- application of known interface rules;
- exact matching of accepted evidence-bound installation scope;
- hard-constraint evaluation;
- policy evaluation;
- explicit product limitations;
- provenance tracking.

The recommendation may be expressed conversationally, but the decisive reasoning should be inspectable.

## Product data versus evidence data

The operational product catalogue should contain current accepted values for fast recommendation queries.

Example:

```text
Tether
- id
- rated_capacity = 2.3 kg
- length = 1.0 m
```

For a cordless tool, the fast operational read model may expose multiple configurations:

```text
Tool
- id
- body_mass = 1.36 kg

OperationalMassProfile
- battery_sku = 48-11-1828
- operational_mass = 2.09 kg
```

The evidence layer explains why those values are accepted.

Example:

```text
Claim:
Tether X rated_capacity = 2.3 kg

Evidence:
Manufacturer datasheet, retrieved 2026-08-11
```

A derived operational-mass claim should additionally be traceable to its accepted input claims and the valid tool/battery relationship.

An exact installation binding may similarly be present in the operational read model for fast generation while retaining source URLs and subject scope that explain why that one route is accepted.

This allows simple runtime queries without losing traceability.

## Derived information

TetherLens should distinguish between:

### Primitive facts

Directly stated or measured product properties.

Examples:

- tool-body mass;
- battery mass;
- rated capacity;
- length;
- gate opening;
- material.

### Declared constraints and relationships

Explicit product-specific limitations, compatibility statements or installation relationships.

Examples:

- maximum operating temperature;
- "use only with attachment X";
- manufacturer-specified compatible component pairing;
- manufacturer-specified ToolAttachment installation at a named Tool feature;
- manufacturer kit composition establishing a valid tool/battery configuration.

These relationships preserve what the issuer documented. They do not automatically become generic technical constraints or exclusions.

### Derived information

Information computed from facts and rules.

Examples:

- operational mass for Tool X with Battery Y;
- connector X is geometrically compatible with attachment Y;
- configuration A satisfies all load requirements;
- configuration B is less suitable in a high-snag environment;
- person anchoring is permitted under the current site policy.

Derived conclusions should not be written back into primitive product data as if they were original facts.

Most recommendation conclusions can remain runtime values. A reusable operational-mass profile is a useful persisted derived structure because it identifies the exact installed configuration and the mass that load rules must use.

## Candidate configurations

The architecture should allow candidate configurations to be assembled from multiple component categories.

A typical configuration may contain:

```text
Tool + operational configuration [battery profile where applicable]
  ↓
ToolAttachment          [where required]
  ↓
Tether
  ↓
AnchorAttachment        [where required]
  ↓
Person / structure / other permitted anchorage
```

Containers may form an alternative or additional configuration path for contained tools or equipment.

Not every recommendation requires all component categories.

A ToolAttachment candidate may enter generation through either:

- reusable technical eligibility against one exact bound Tool feature; or
- accepted evidence binding one exact ToolAttachment product to one exact resolved Tool feature.

Multi-component ToolAttachment assemblies must retain which selected product owns each provided interface whenever product-scoped manufacturer evidence depends on that ownership.

## Scalability principle

The system should scale through reuse.

Adding a new product should ideally involve:

`capture facts -> attach evidence -> existing relationships/rules evaluate it`

rather than:

`capture product -> manually author compatibility with every other product`

A growing number of unexplained one-off exceptions is an architectural warning sign. A growing set of source-backed exact relationships is not itself a failure when manufacturers omit explanatory geometry, provided those relationships remain narrowly scoped evidence and are not mistaken for generic rules.

The intended progression for repeated exact relationships is:

```text
retain known-valid evidence
-> inspect shared facts
-> form bounded hypothesis
-> validate on additional products/measurements
-> promote only justified reusable predicates
```

## Explainability

A recommendation should be traceable through several levels:

```text
Why this recommendation?
    ↓
Because Configuration A ranked highest.

Why is Configuration A viable?
    ↓
All applicable hard constraints passed and any exact documented
installation step was established by accepted scoped evidence.

Why did the load constraint pass?
    ↓
Operational tool mass = 2.09 kg.
Every applicable component rating >= 2.09 kg.

Where did 2.09 kg come from?
    ↓
Tool-body mass Claim + installed Battery mass Claim
+ manufacturer-backed tool/battery relationship.
```

For an evidence-bound installation, the system should additionally be able to answer which manufacturer source documented which product at which Tool feature, without pretending to know physical details that source did not establish.

The product does not need to expose all of this detail to every worker, but the underlying system should be able to provide it.

## MVP architectural constraints

The MVP does not require:

- a graph database;
- a full standards ontology;
- automated contradiction resolution;
- automatic rule generation;
- automatic promotion of repeated pairings into generic rules;
- a separate microservice for every layer; or
- real-time inference over arbitrary product combinations.

A simple implementation is acceptable as long as the conceptual boundaries remain intact.

## Architectural success criteria

The architecture is working if:

- new products can be added without redesigning the schema;
- cordless tools can represent multiple exact battery configurations without collapsing them into one mass;
- existing reusable rules handle most newly added products where the required facts are available;
- known manufacturer-documented paths can remain usable when complete geometry is unavailable, without inventing facts or becoming universal SKU-pair logic;
- one product fact can be updated without manually editing many unrelated pairings;
- mandatory facts remain traceable to evidence and derived operational facts retain their input dependencies;
- manufacturer evidence remains scoped to the exact model/product/interface/source context it supports;
- recommendation logic can distinguish hard constraints, context, evidence, manufacturer position, and policy; and
- AI can improve the experience without becoming the untraceable source of safety-critical decisions.
