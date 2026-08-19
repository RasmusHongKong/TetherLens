# TetherLens Architecture

## Purpose

This document describes the logical architecture of TetherLens.

It intentionally avoids committing to a specific frontend framework, database technology, AI provider, or deployment platform.

The purpose is to define the boundaries between:

- product knowledge;
- evidence and provenance;
- reusable rules;
- recognition;
- work context;
- policy; and
- the recommendation engine.

## Architectural principle

The central architectural principle is:

> **The catalogue describes what products are. Rules describe how those properties matter. The recommendation engine combines those facts and rules with the current work context.**

TetherLens should not depend on manually authoring every possible tool-to-tether combination.

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
- tool/interface geometry;
- native tether-point status;
- material;
- explicit product limits.

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

### 2. Evidence and provenance

The evidence layer records what supports a claim or rule.

The core concepts are:

- Source;
- Claim;
- Evidence; and
- Rule.

This layer allows TetherLens to answer:

- where did this value come from?
- how was it established?
- when was it checked?
- is it directly stated, measured, or derived?
- which accepted facts does a derived value depend on?
- why does this recommendation rule exist?

The evidence layer should support traceability without forcing the recommendation engine to perform expensive provenance traversal for every user interaction.

Derived operational facts that are persisted for reuse should retain explicit dependency links to their accepted input Claims. For example, a cordless operational-mass claim should depend on the accepted tool-body mass Claim and the accepted battery-mass Claim, while the profile itself also records the manufacturer-backed tool/battery relationship that makes the configuration valid.

### 3. Ingestion staging and review

Product knowledge may arrive through several channels:

- automated manufacturer-web/document extraction;
- internal staff entry; and
- future user submissions.

All channels should converge on a staging/review process before candidate information becomes accepted knowledge.

Automated extraction should create candidate claims and candidate changes rather than silently overwriting accepted mandatory facts.

This layer allows TetherLens to scale catalogue maintenance while preserving the evidence standards of the accepted knowledge base.

### 4. Rules

Rules contain reusable domain reasoning.

Examples include:

- load must not exceed rated capacity;
- interface geometry must permit a valid connection;
- person anchoring may be restricted by policy above a configured threshold;
- reduced free tether length should be preferred where snag risk is elevated;
- a documented product limit may invalidate a configuration in a particular environment.

Rules should be reusable across products wherever possible.

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

Policy should be separate from technical suitability.

Examples include:

- maximum permitted operational mass for person anchoring;
- required product families;
- prohibited components;
- site-specific restrictions.

### 8. Recommendation engine

The recommendation engine combines:

- resolved tool profile — exact catalogue tool/configuration or generic runtime profile;
- product data;
- candidate components/configurations;
- hard constraints;
- contextual rules;
- evidence limitations; and
- policy.

It should produce the most useful defensible recommendation available.

## AI boundary

AI can assist with:

- image-based tool recognition;
- extracting candidate product facts from datasheets or webpages;
- identifying potentially relevant context from an image;
- asking contextual questions;
- explaining a structured recommendation in clear language; and
- helping catalogue maintainers identify missing data.

AI should not be the final persistent source of truth for:

- catalogued tool-body or battery mass;
- tool/battery compatibility relationships;
- derived operational mass profiles;
- rated capacity;
- interface dimensions;
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
- natural-language explanation.

### Deterministic or controlled

- derivation of operational mass from accepted tool-body and battery mass;
- load-capacity comparison;
- application of known interface rules;
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

Explicit product-specific limitations or compatibility statements.

Examples:

- maximum operating temperature;
- "use only with attachment X";
- manufacturer-specified compatible component pairing;
- manufacturer kit composition establishing a valid tool/battery configuration.

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

## Scalability principle

The system should scale through reuse.

Adding a new product should ideally involve:

`capture facts -> attach evidence -> existing relationships/rules evaluate it`

rather than:

`capture product -> manually author compatibility with every other product`

A growing number of one-off exceptions is an architectural warning sign.

## Explainability

A recommendation should be traceable through several levels:

```text
Why this recommendation?
    ↓
Because Configuration A ranked highest.

Why is Configuration A viable?
    ↓
All hard constraints passed.

Why did the load constraint pass?
    ↓
Operational tool mass = 2.09 kg.
Every applicable component rating >= 2.09 kg.

Where did 2.09 kg come from?
    ↓
Tool-body mass Claim + installed Battery mass Claim
+ manufacturer-backed tool/battery relationship.
```

The product does not need to expose all of this detail to every worker, but the underlying system should be able to provide it.

## MVP architectural constraints

The MVP does not require:

- a graph database;
- a full standards ontology;
- automated contradiction resolution;
- automatic rule generation;
- a separate microservice for every layer; or
- real-time inference over arbitrary product combinations.

A simple implementation is acceptable as long as the conceptual boundaries remain intact.

## Architectural success criteria

The architecture is working if:

- new products can be added without redesigning the schema;
- cordless tools can represent multiple exact battery configurations without collapsing them into one mass;
- existing rules handle most newly added products;
- one product fact can be updated without manually editing many pairings;
- mandatory facts remain traceable to evidence and derived operational facts retain their input dependencies;
- recommendation logic can distinguish hard constraints, context, evidence, and policy; and
- AI can improve the experience without becoming the untraceable source of safety-critical decisions.
