# TetherLens MVP

## Objective

The MVP should test one narrow proposition:

> **Can a field worker photograph a tool, confirm its identity, provide a small amount of relevant work context, and reach the correct verified tethering configuration faster and more reliably than through the current lookup process?**

The MVP is not intended to prove that TetherLens can recognise every tool, understand an entire worksite from an image, or automate a complete dropped-object prevention programme.

It should prove that the core architecture works:

`recognition + context + structured compatibility data -> verified recommendation or safe abstention`

## Core hypotheses

The MVP should test four related hypotheses.

### 1. Camera-first lookup reduces friction

For a small, curated tool catalogue, image recognition can get the worker to the correct tool faster than manual lookup.

### 2. Workers can provide the missing context

Where worksite conditions affect the recommendation, TetherLens can ask a small number of targeted questions that a worker can answer without specialist knowledge.

### 3. Context changes the recommendation meaningfully

For at least some tools, different task, environmental, or anchorage conditions should result in a different validated configuration, a conditional recommendation, or a safe abstention.

### 4. Structured rules can support independent compatibility decisions

TetherLens can recommend a technically suitable configuration from structured evidence and constraints without requiring all components to come from the tool manufacturer.

If the system cannot do these things reliably for a small, controlled set, expanding the catalogue will not solve the underlying product problem.

## MVP user

The MVP is designed for a worker using a mobile phone at the point of use.

The pilot should use a **defined tool population**, ideally a real toolbox, worksite, team, or representative set of approximately 20-30 commonly used tools.

The purpose of the limit is to make the catalogue, compatibility data, and contextual rules complete enough to test rather than broad enough to impress.

## MVP scope

### 1. Mobile-first image capture

The worker can take or upload a photograph of **one tool at a time**.

The MVP does not need to interpret a full toolbox, workbench, or scene containing multiple candidate tools.

### 2. Recognition against a known tool catalogue

The recognition layer attempts to match the image to the curated MVP tool catalogue.

The system may return one likely match or a short list of candidates, but it should not silently convert an uncertain visual guess into a safety-related recommendation.

### 3. User confirmation

Before a recommendation is shown, the worker confirms the identified tool.

Where visually similar tools cannot be distinguished reliably, TetherLens should ask for the smallest amount of additional information required to resolve the ambiguity.

### 4. Targeted context questions

The MVP should include a deliberately small set of contextual constraints that can materially change the recommendation.

Rather than attempting general worksite understanding, the system should ask only questions triggered by the confirmed tool or candidate configuration.

The pilot should cover approximately **3-5 contextual dimensions**, for example:

- restricted or congested working space / elevated snag risk;
- relevant contaminant or chemical exposure;
- available anchorage type or location;
- reach or tether-length constraint; and
- another pilot-specific environmental condition that affects component suitability.

The exact dimensions should be chosen from real pilot use cases.

The MVP does **not** need to infer these conditions automatically from the camera image. Manual confirmation is acceptable and preferable to unreliable inference.

### 5. Structured tool data

Each in-scope tool should have a maintained record containing, where applicable:

- internal tool ID;
- manufacturer;
- model or model family;
- category;
- known mass or mass range;
- recognition labels;
- attachment characteristics;
- relevant operational constraints; and
- source references.

The MVP should not depend on the vision model inferring safety-critical properties that already exist in the data.

### 6. Structured component data

Tethering equipment should be represented at component level so that TetherLens is not structurally limited to same-brand or pre-packaged solutions.

At minimum, component records should distinguish roles such as:

- tool attachment;
- tether / lanyard;
- anchor attachment; and
- other relevant connector or retaining component.

A component record may include:

- component ID;
- manufacturer;
- product/model;
- component role;
- capacity;
- material;
- length or geometry;
- connector type;
- environmental limitations;
- relevant standards or certifications;
- manufacturer restrictions or endorsements; and
- evidence references.

### 7. Validated configurations

The worker-facing recommendation should resolve to a known configuration assembled from structured component records.

For the MVP, configurations can be curated in advance rather than generated dynamically.

A configuration should include:

- configuration ID;
- tool or tool-family applicability;
- component IDs;
- attachment method;
- anchorage requirements;
- contextual conditions;
- important limitations;
- technical validation status;
- evidence references; and
- manufacturer endorsement status where relevant.

This allows the MVP to include mixed-manufacturer configurations without treating them as inherently invalid.

### 8. Explicit suitability rules

The recommendation engine should evaluate the confirmed tool, contextual inputs, and available validated configurations using deterministic rules or explicit compatibility mappings.

The AI should not invent the compatibility relationship.

A simplified MVP relationship is:

`confirmed tool + relevant context -> validated configuration(s) -> policy check -> result`

### 9. Distinct technical and policy status

The MVP should not use a single ambiguous "approved" flag.

At minimum, it should distinguish:

- **technical validation status** — whether TetherLens considers the configuration suitable under the stated conditions;
- **manufacturer endorsement status** — endorsed, restricted/prohibited, not addressed, or unknown; and
- **site/company policy status** — permitted, prohibited, or not configured.

For the first pilot, site/company policy may be minimal or static, but the data model should accommodate it from the start.

### 10. Result screen

The result should answer the worker's immediate questions with minimal reading:

- **What tool did I confirm?**
- **What configuration should I use?**
- **How should it be attached?**
- **Why is this configuration suitable here?**
- **What important limit or condition do I need to know?**
- **Is there any manufacturer or site-policy conflict I should be aware of?**

The result should distinguish clearly between technical suitability and external endorsement or policy.

### 11. Safe failure

If TetherLens cannot identify the tool with sufficient confidence, cannot resolve the required context, finds no validated configuration, or encounters a policy condition that prevents recommendation, it should return a clear **no verified recommendation available** state.

An incomplete result is preferable to a fabricated one.

### 12. Lightweight feedback capture

The worker should be able to indicate that:

- the tool identification was wrong;
- the correct tool was not listed;
- the work context was not represented;
- the recommended configuration was impractical; or
- the recommendation was otherwise not useful.

This feedback is primarily for evaluating the MVP and improving the data and rules. A full administrative workflow is not required.

## Deliberate non-goals

The MVP will not attempt to provide:

- recognition of arbitrary tools outside the curated pilot catalogue;
- multiple-tool or full-scene recognition;
- automatic understanding of all worksite conditions from images or video;
- dynamic generation of previously unvalidated tethering configurations;
- site-specific anchor-point engineering assessment from an image;
- complete inventory or asset management;
- procurement or stock availability;
- organisation-wide user management or SSO;
- a native iOS or Android application;
- offline operation;
- augmented-reality overlays;
- a general-purpose conversational safety assistant;
- training records or competency management;
- programme analytics dashboards; or
- automated ingestion of every manufacturer's catalogue.

These may become useful later, but none are required to test the core hypotheses.

## Suggested MVP data model

The MVP data model should be simple enough to implement quickly but should preserve the distinctions required by the product vision.

### Tool

```text
Tool
- id
- manufacturer
- model
- category
- mass
- recognition_labels
- attachment_characteristics
- operational_constraints
- evidence_references
```

### Component

```text
Component
- id
- manufacturer
- model
- role
- capacity
- material
- geometry
- connector_type
- environmental_limits
- manufacturer_restrictions
- evidence_references
```

### Configuration

```text
Configuration
- id
- component_ids
- attachment_method
- anchorage_requirements
- context_conditions
- limitations
- validation_status
- evidence_references
- manufacturer_endorsement_status
```

### Tool-configuration compatibility

```text
Compatibility
- tool_id
- configuration_id
- conditions
- rationale
- validated_by
- validation_date
- validation_status
```

### Policy

```text
Policy
- scope
- tool_id or category
- configuration_id or component_id
- status
- condition
- authority
- source_reference
```

The MVP can store these records in simple structured files or a lightweight database. The important architectural decision is that recognition, technical suitability, evidence, manufacturer endorsement, and site policy remain separable.

## MVP workflow

```text
Open TetherLens
      ↓
Photograph one tool
      ↓
Recognition returns likely catalogue match(es)
      ↓
Worker confirms or corrects the tool
      ↓
System asks only the context questions relevant to this tool
      ↓
Rules evaluate validated configurations
      ↓
Policy / endorsement information is checked
      ↓
Show suitable configuration + key constraints
      ↓
Optional feedback
```

If any required step cannot be completed reliably, the workflow ends in a safe failure state rather than an invented recommendation.

## Pilot design

The pilot should intentionally include cases where **the same tool produces different outcomes under different work conditions**.

For example, the test set should contain scenarios in which:

- an otherwise suitable tether becomes undesirable because of snagging or restricted-space risk;
- a component is excluded because of an environmental or contaminant limitation;
- the available anchorage changes the viable configuration;
- a mixed-manufacturer configuration is technically validated;
- a manufacturer does not endorse the configuration, but sufficient evidence supports technical suitability;
- a site policy prohibits an otherwise technically suitable configuration; and
- no suitable configuration exists, requiring abstention.

This is important because a pilot that only matches tools to tethers by weight would test the easiest part of the problem while missing a major source of real-world value.

## Test plan

The MVP should be evaluated against a fixed test set before expanding its scope.

The test set should include:

- clear photographs of known tools;
- poor-angle or imperfect photographs;
- visually similar in-scope tools;
- tools that are not in the catalogue;
- tools for which no validated configuration exists;
- tools with more than one validated configuration;
- contextual scenarios where the recommended configuration changes;
- mixed-manufacturer configurations; and
- policy conflicts.

Testing should include real field users rather than relying only on developer testing.

## Success criteria

The precise thresholds can be adjusted once the pilot tool set and worksite scenarios are selected, but the MVP should be judged on measurable outcomes.

A useful initial bar is:

- **Recognition:** the correct in-scope tool appears in the proposed candidate set for at least 90% of representative test images.
- **Confirmation:** users can reach the correct tool selection without outside help in at least 90% of in-scope tasks.
- **Context capture:** users can answer the required contextual questions correctly without specialist help in at least 90% of test scenarios.
- **Context sensitivity:** where the predefined scenario requires a different configuration or abstention, the system produces the correct contextual outcome in 100% of validated test cases.
- **Recommendation integrity:** every recommendation shown resolves to an existing validated configuration and supporting compatibility record.
- **Mixed-manufacturer integrity:** cross-brand configurations are treated according to technical evidence rather than brand matching alone.
- **Policy integrity:** technical suitability, manufacturer endorsement, and site/company policy are never presented as if they were the same thing.
- **Safe failure:** unknown tools, unresolved context, missing compatibility data, and unsupported configurations produce an explicit no-recommendation state rather than a guessed solution.
- **Speed:** median time from image capture to confirmed recommendation is under 45 seconds for scenarios requiring contextual questions, and under 30 seconds where no context questions are needed.
- **Usability:** pilot users judge the workflow easier or faster than the reference method they would otherwise use for the same task.

The most important MVP metric is not raw image-recognition accuracy.

It is the percentage of field scenarios that end with the **correct verified configuration or a safe abstention given the actual work context**.

## What the MVP should teach us

Before expanding TetherLens, the MVP should answer:

1. Do workers prefer a camera-first workflow for this problem?
2. Is visual recognition reliable enough to reduce lookup friction?
3. Which contextual factors materially change tethering decisions most often?
4. Can workers provide those factors accurately through a small number of questions?
5. Which contextual inputs might later be inferred reliably from images, site data, or sensors?
6. Is the structured configuration model expressive enough for real mixed-manufacturer tethering decisions?
7. What level of evidence is needed before a technical configuration should be treated as validated?
8. How should the product present conflicts between technical suitability, manufacturer endorsement, and site policy?
9. Which types of tools and tasks create the most ambiguity?
10. How often does the system need to abstain?
11. Do workers trust the result more when the reason and constraints are visible?
12. Is maintaining the underlying tool, component, configuration, evidence, and policy data operationally practical?

## Exit criteria

The MVP is successful enough to justify expansion when:

- field users can complete the core workflow with little or no assistance;
- validated recommendations are consistently correct for the in-scope catalogue and scenarios;
- the same tool can produce different correct outcomes when contextual conditions require it;
- mixed-manufacturer configurations can be represented and evaluated without compromising traceability;
- unsafe false certainty is controlled through confirmation, explicit rules, and abstention;
- technical suitability is clearly separated from manufacturer endorsement and site policy;
- the workflow is materially faster or easier than the existing alternative; and
- the team can identify a credible path to adding more tools, constraints, and configurations without changing the fundamental product architecture.

If those conditions are not met, the next step should be to improve the core workflow, evidence model, or compatibility logic rather than simply broaden the catalogue.
