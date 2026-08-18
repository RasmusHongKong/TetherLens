# TetherLens Recommendation Engine

## Purpose

This document defines the basic reasoning model used to turn:

- a resolved tool profile;
- product data;
- work context;
- reusable rules; and
- policy

into a useful tethering recommendation.

The recommendation engine should be explainable, conservative about hard constraints, and practical about imperfect field conditions.

## Objective

> **Return the most useful defensible recommendation available.**

The engine should not maximise abstention.

If a viable option exists but is less than ideal, TetherLens should normally recommend it with the relevant caution rather than returning no answer.

## Core model

```text
Resolved tool profile
      +
Work context
      +
Product catalogue
      ↓
Generate candidate configurations
      ↓
Apply hard constraints
      ↓
Remove non-viable candidates
      ↓
Apply contextual rules
      ↓
Rank remaining candidates
      ↓
Apply policy
      ↓
Assess evidence limitations
      ↓
Produce recommendation + cautions
```

## Four recommendation dimensions

### 1. Hard constraints -> viability

Hard constraints determine whether a candidate may remain in consideration.

### 2. Context -> suitability and ranking

Context determines which viable candidate is best for the current task.

### 3. Evidence -> confidence and qualification

Evidence determines what TetherLens is entitled to claim about the result and what uncertainty should be communicated.

### 4. Policy -> permission

Policy determines whether an otherwise technically suitable configuration is allowed in the current organisation/site context.

## Step 1: resolve the tool

An exact catalogue match is preferred, but it must not be a prerequisite for receiving help.

TetherLens should support two resolution paths.

### Catalogue-tool path

Where possible, TetherLens should identify an exact or sufficiently specific manufacturer/model record and ask the worker to confirm it.

This path can use verified catalogue facts such as:

- mass;
- known geometry;
- native tether features;
- materials; and
- declared product constraints.

Catalogue facts retain their provenance. For physical tool or battery mass, manufacturer evidence is preferred, but a reputable exact-SKU secondary product-detail source may be accepted where manufacturer mass is unavailable or incomplete. Manufacturer-rated capacities, restrictions and compliance claims retain their stricter manufacturer-evidence requirements.

### Generic-tool path

Where exact identification is not possible or useful — for example because the tool is generic, unbranded, absent from the catalogue, or the worker cannot identify the model — TetherLens should stop trying to force an exact match and create a session-level generic tool profile.

The generic profile should capture only the information required by the applicable recommendation rules, such as:

- broad tool type/category;
- object mass or mass range;
- source of that mass information;
- relevant visible or user-confirmed geometry; and
- attachment/interface features needed to establish a viable tethering method.

Suggested runtime mass-source states include:

- `manufacturer_confirmed`
- `user_confirmed_from_label_or_document`
- `user_measured`
- `user_estimated`

For `user_estimated` mass, TetherLens should prefer bounded ranges where practical and evaluate load capacity against the upper bound.

Example:

```text
User-selected mass range: 2-3 kg
Required capacity for load rules: >= 3 kg
```

A generic-tool recommendation should clearly state when the object mass is user-provided rather than a verified catalogue fact.

Generic runtime observations must not automatically become accepted catalogue Claims. If the product is later submitted for catalogue inclusion, it should enter the normal ingestion/review process.

The purpose of this fallback path is to preserve field usefulness without weakening the evidence standard for the persistent catalogue.

## Step 2: gather relevant context

TetherLens should ask only for context that can materially affect the recommendation.

The questions should be selected dynamically based on:

- the tool;
- available candidate components;
- applicable rules.

Examples:

- Is the work area congested or high-snag?
- Is person anchoring permitted/appropriate?
- What anchorage type is available?
- Is there a relevant contaminant exposure?
- Is additional working reach required?

The MVP can rely on user input rather than automatic scene interpretation.

## Step 3: generate candidate configurations

Candidate configurations may combine:

- tool;
- tool attachment, where needed;
- tether;
- anchor attachment, where needed;
- permitted anchorage method;
- container, where relevant.

The system should avoid requiring a manually curated exact pairing for every candidate.

Candidate generation should increasingly rely on reusable product facts and interface rules.

## Step 4: apply hard constraints

At minimum, the MVP should enforce:

### Load capacity

For every applicable load-bearing component:

`rated_capacity >= object_mass_used_for_reasoning`

Component capacity should come from manufacturer information.

For a catalogued tool, object mass should come from verified physical-mass evidence bound to the exact product identity. Manufacturer evidence is preferred; a reputable exact-SKU secondary source may be accepted where manufacturer mass is unavailable or incomplete. Visual inference, similar-model estimates and unverified aggregate/search pages are not acceptable catalogue mass evidence.

For the generic-tool fallback path, the engine may use a user-confirmed label/document value, a user measurement, or — with clear qualification — a user-estimated mass range. Where a range is used, the upper bound should be used for the load-capacity comparison.

Runtime user-provided mass should affect the recommendation's qualification/confidence and should not be persisted as a verified catalogue fact.

### Interface compatibility

Each required connection must have sufficient compatibility evidence.

This may come from:

- published dimensions;
- internal measurement;
- explicit manufacturer pairing;
- kit relationships;
- observed/confirmed tool geometry evaluated by a validated attachment rule; or
- validated reusable interface rules.

The engine should not treat `no manufacturer-documented tether point` as equivalent to `no tethering method`. A valid path may use another captive feature, a controlled loop/cinch method, or a suitable ToolAttachment.

### Explicit product limits

A source-backed manufacturer limit may invalidate a candidate.

### Anchorage viability

The proposed anchorage method must be technically possible and compatible with the current policy/context.

A structural anchor is not universally required.

For lighter tools, person anchoring may be appropriate where:

- component capacities are sufficient;
- the configuration is otherwise technically viable; and
- the applicable site/organisation policy permits it.

The exact person-anchoring threshold should be policy-driven rather than hard-coded globally.

## Step 5: rank viable configurations by context

Once non-viable candidates are removed, context should influence ranking.

Examples:

### Snagging

In a congested or pipe-heavy environment:

- prefer reduced free tether length;
- prefer configurations that reduce unnecessary slack where other factors are equal.

If no ideal low-snag option exists, a longer viable tether may still be recommended with a caution.

### Reach

Where additional reach is required:

- configurations that are too restrictive should rank lower;
- the recommendation should balance reach against snagging and control.

### Environment

Known environmental facts and rules may affect ranking or viability.

Where product material information is incomplete, the engine should communicate the limitation rather than automatically assume compatibility.

## Step 6: apply policy

Policy should be evaluated separately from technical viability.

Examples:

- person anchoring permitted only below a configured mass;
- certain product families prohibited;
- mixed-brand combinations disallowed by a particular site;
- specific anchor methods required.

The engine should be able to represent:

```text
technical_suitability = suitable
policy_status = prohibited
```

without pretending the configuration itself is technically unsafe.

## Step 7: assess evidence limitations

Evidence should affect qualification, not necessarily viability.

Examples:

### Strong support

Mandatory facts and relevant contextual properties are well established.

### Secondary uncertainty

The hard constraints are established, but some secondary property is incomplete.

Example:

- mass known;
- capacities known;
- interfaces known;
- chemical resistance not established.

The recommendation may remain usable with a clear limitation.

### Runtime user-supplied object data

Where the generic-tool path is used, the engine should distinguish the source of the object mass from persistent verified catalogue facts.

A recommendation may remain useful when the worker provides or measures the mass, but the result should state the basis clearly.

Example:

> Recommended based on the information provided: the selected configuration is rated above the 3 kg upper weight you confirmed. The exact tool model and catalogue mass could not be verified.

### Insufficient hard-constraint information

A required fact cannot be established.

Example:

- component capacity unknown;
- interface compatibility cannot be determined.

This can require abstention for the affected candidate.

## Recommendation states

### Recommended

Use when:

- hard constraints pass;
- the configuration is well suited to context;
- no material qualification changes how the worker should interpret the result.

### Recommended with constraints

Use when:

- hard constraints pass;
- the configuration is viable;
- one or more practical limitations should be actively managed.

Example:

> This tether has sufficient capacity and compatible attachments, but its length increases snagging potential around pipework. Keep the tether path clear and use a shorter alternative if one becomes available.

### Limited-confidence recommendation

Use when:

- hard constraints can still be established;
- the configuration is defensible;
- secondary evidence is incomplete or the exact combination has not previously been assessed as a named pairing.

The limitation should be specific rather than a generic disclaimer.

### No suitable recommendation

Use only when:

- all candidates fail a hard constraint;
- a required hard-constraint fact cannot be established;
- all candidates create an unacceptable hazard; or
- policy prevents every otherwise viable option and no permitted alternative exists.

## Explainability

Every recommendation should be explainable in worker-friendly terms.

At minimum:

- selected configuration;
- key reason it is viable;
- key reason it ranked highest;
- important caution;
- policy conflict, where relevant.

Internally, the engine should be able to trace:

```text
Recommendation
  ↓
Candidate configuration
  ↓
Rules evaluated
  ↓
Claims used
  ↓
Evidence / sources
```

## Rules should operate on low-level facts

Avoid rules based on manually entered application labels.

Prefer:

```text
IF snag_risk = high
AND tether.free_length is greater
THEN rank lower
```

over:

```text
IF tether.suitable_for_tight_spaces = false
THEN rank lower
```

Prefer:

```text
IF environment.temperature > declared_max_temperature
THEN exclude
```

over:

```text
IF tether.suitable_for_hot_work = false
THEN exclude
```

This keeps the recommendation logic reusable.

## Mixed-manufacturer reasoning

Brand should not be treated as a compatibility rule by default.

The engine should evaluate:

- rated capacities;
- interfaces;
- geometry;
- explicit restrictions;
- product facts;
- relevant reusable rules.

Manufacturer endorsement may be shown separately.

## Initial rule set for the MVP

The first rule set should stay small.

Likely rules include:

### Hard constraints

- object mass must not exceed tether capacity;
- object mass must not exceed tool-attachment capacity where used;
- object mass must not exceed anchor-attachment capacity where used;
- object/contents mass must not exceed container capacity where used;
- required interfaces must be compatible;
- explicit manufacturer hard limits must be respected where applicable.

### Context preferences

- prefer reduced free tether length in high-snag environments;
- prefer sufficient reach for the stated task;
- select anchorage method based on technical viability and configured policy.

### Cautions

- warn where a viable tether creates increased snagging potential;
- warn where relevant secondary environmental information is not established;
- surface manufacturer restrictions or non-endorsement where material to the decision.

The rule set should expand only when real use cases justify it.

## User-facing wording principle

Cautions should be actionable.

Avoid:

> Use with caution.

Prefer:

> The tether is long enough to create additional snagging potential around the pipework. Keep excess tether clear of obstructions and use a shorter option if available.

The goal is to help the worker manage the limitation.

## Recommendation-engine success criteria

The engine is working if:

- hard constraints are reliably enforced;
- the same tool can produce different recommendations under different context;
- viable but imperfect options are not unnecessarily rejected;
- mixed-manufacturer configurations can be evaluated;
- evidence limitations are communicated without generic over-warning;
- policy remains separate from technical suitability;
- rules can be reused across newly added products; and
- a recommendation can be traced back to the facts and rules that produced it.
