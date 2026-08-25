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
Select highest-ranked permitted candidate
      ↓
Resolve any required runtime verification
      ↓
If verification fails, reject candidate and try next ranked permitted candidate
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

Evidence determines what TetherLens is entitled to claim about the result and what uncertainty or runtime verification should be communicated.

### 4. Policy -> permission

Policy determines whether an otherwise technically suitable configuration is allowed in the current organisation/site context.

## Step 1: resolve the tool

An exact catalogue match is preferred, but it must not be a prerequisite for receiving help.

TetherLens should support two resolution paths.

### Catalogue-tool path

Where possible, TetherLens should identify an exact or sufficiently specific manufacturer/model record and ask the worker to confirm it.

This path can use verified catalogue facts such as:

- operational mass or configuration-specific mass profiles;
- known geometry;
- native tether features;
- materials; and
- declared product constraints.

Catalogue facts retain their provenance. For physical tool-body or battery mass, manufacturer evidence is preferred, but a reputable exact-SKU secondary product-detail source may be accepted where manufacturer mass is unavailable or incomplete. Manufacturer-rated capacities, restrictions and compliance claims retain their stricter manufacturer-evidence requirements.

For a cordless Tool with an interchangeable installed Battery, the resolved catalogue profile must identify a valid `OperationalMassProfile` for the exact Tool/Battery configuration used in the recommendation. The profile must be based on exact Tool and Battery identities, a manufacturer-backed configuration relationship, and accepted primitive mass Claims.

If several compatible Batteries produce several valid profiles, TetherLens must resolve which installed configuration applies before performing load checks. It must not silently choose the lightest, heaviest, first-listed, or otherwise arbitrary Battery, and it must not use bare-tool/body mass as a substitute.

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

- resolved Tool configuration, including installed Battery profile where applicable;
- tool attachment, where needed;
- tether;
- anchor attachment, where needed;
- permitted anchorage method;
- container, where relevant.

The system should avoid requiring a manually curated exact tethering pairing for every candidate.

Candidate generation should increasingly rely on reusable product facts, explicit manufacturer configuration relationships, interface rules, and controlled runtime verification where catalogue evidence cannot economically establish every physical fit in advance.

## Step 4: apply hard constraints

At minimum, the MVP should enforce:

### Load capacity

For every applicable load-bearing component:

`rated_capacity >= object_mass_used_for_reasoning`

Component capacity should come from manufacturer information.

For a catalogued Tool, `object_mass_used_for_reasoning` must represent the Tool as configured for use.

For a non-battery Tool whose mass is not configuration-dependent, the accepted physical Tool mass may be used directly.

For a cordless Tool with an interchangeable installed Battery:

```text
accepted tool-body mass
    +
accepted exact Battery mass
    ↓
validated OperationalMassProfile
    ↓
object_mass_used_for_reasoning
```

The Tool/Battery relationship supporting that profile must come from manufacturer evidence such as explicit compatibility or kit composition. A shared voltage/platform label alone is insufficient.

Physical tool-body and Battery mass must come from verified physical-mass evidence bound to the exact product identities. Manufacturer evidence is preferred; a reputable exact-SKU secondary source may be accepted where manufacturer mass is unavailable or incomplete. Visual inference, similar-model estimates and unverified aggregate/search pages are not acceptable catalogue mass evidence.

If a Tool requires an operational profile and the installed Battery/profile is unresolved, the engine cannot complete the load-capacity check for that candidate. It must not compare component capacity against bare-tool/body mass.

For the generic-tool fallback path, the engine may use a user-confirmed label/document value, a user measurement, or — with clear qualification — a user-estimated mass range. Where a range is used, the upper bound should be used for the load-capacity comparison.

Runtime user-provided mass should affect the recommendation's qualification/confidence and should not be persisted as a verified catalogue fact.

### Interface compatibility

Each required physical connection must have an **acceptable compatibility basis**.

Detailed dimensional proof is one possible basis, but it is not a universal catalogue requirement. The compatibility model is defined in `connection-compatibility.md`.

Initial technical connection states are:

```text
compatible
incompatible
requires_verification
unresolved
```

Initial compatibility bases are:

```text
manufacturer_declared
validated_geometry
validated_interface_class
runtime_verification
none
```

A connection may therefore be established through:

- explicit manufacturer compatibility or prescribed system relationships;
- a validated reusable geometry rule using published or accepted measured dimensions;
- a validated reusable interface class based on primitive physical facts; or
- a validated bounded runtime verification procedure applied to the actual equipment.

The engine must **not** infer compatibility from interface names alone. `carabiner + ring`, for example, is topology that may select an applicable rule, not proof of engagement.

`requires_verification` is a conditional but usable technical state. It should be returned only when:

- endpoint and target topology/roles are plausible;
- no accepted evidence proves incompatibility;
- catalogue evidence is insufficient to establish complete physical engagement; and
- a validated bounded field-verification procedure exists for that connection family.

`unresolved` remains blocking when no accepted compatibility basis or validated verification path exists.

For tools, this does **not** require a manufacturer-documented tether point. A valid path may use another captive feature, a controlled loop/cinch method, or a suitable ToolAttachment.

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

Once non-viable candidates are removed, context should influence ranking. A candidate may remain in the ranked set while one or more connections are `requires_verification`; that conditional state should not force the worker to assemble the candidate before TetherLens knows whether it is otherwise preferred.

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

Policy should be evaluated separately from technical viability and before asking the worker to perform a physical verification.

Examples:

- person anchoring permitted only below a configured operational mass;
- certain product families prohibited;
- mixed-brand combinations disallowed by a particular site;
- specific anchor methods required.

The engine should be able to represent:

```text
technical_suitability = suitable
policy_status = prohibited
```

without pretending the configuration itself is technically unsafe.

A policy-prohibited candidate should not trigger runtime assembly or verification merely because its connection topology was otherwise plausible.

## Step 6a: verify the selected candidate where required

After hard constraints, contextual ranking and policy have identified the highest-ranked permitted candidate, TetherLens should resolve any `requires_verification` connections for **that candidate**.

A candidate with a `requires_verification` connection is not yet ready for unconditional use. TetherLens should present the validated verification procedure for that connection family and require the worker to verify the actual assembled connection before the candidate is treated as usable.

A field-verification procedure must be bounded and observable. It must not reduce to a generic confirmation such as "looks safe" or "does it fit?".

Depending on the validated rule, checks may include whether:

- the connector installs onto the intended interface normally;
- the gate closes completely;
- the locking mechanism fully engages where applicable;
- the interface does not obstruct or capture the gate;
- the connector can settle into an intended loaded orientation;
- the connection does not force obvious cross-loading or unstable seating; and
- adjacent hardware does not interfere with gate or locking operation.

The exact checklist must come from the versioned rule for the relevant connection family.

If the runtime check fails, that candidate connection/configuration becomes unusable for the session. The engine should then fall back to the next highest-ranked permitted candidate and request verification only if that candidate also requires it.

This avoids requiring the worker to obtain or assemble lower-ranked alternatives unnecessarily.

A successful runtime check is session/configuration evidence. It must not silently become a persistent universal catalogue Claim that the two product SKUs are compatible.

Computer vision may later assist these checks, but machine-observed criteria should replace worker confirmation only after each criterion has been separately validated.

## Step 7: assess evidence limitations

Evidence should affect qualification, not necessarily viability.

Examples:

### Strong support

Mandatory facts and relevant contextual properties are well established.

For a cordless Tool this includes a resolved operational profile whose Tool-body and Battery mass dependencies and manufacturer-backed configuration relationship are traceable.

For a physical connection, strong support may come from an accepted manufacturer declaration or a validated rule whose required primitive facts are established.

### Conditional runtime verification

Catalogue facts establish a plausible connection path, but final physical fit must be checked on the actual components.

This is represented by `requires_verification`, not by pretending the catalogue has complete geometry and not by treating the connection as generically unresolved.

The recommendation should state exactly what must be checked before use.

### Secondary uncertainty

The hard constraints are established, but some secondary property is incomplete.

Example:

- operational mass known;
- capacities known;
- interfaces established or field-verified;
- chemical resistance not established.

The recommendation may remain usable with a clear limitation.

### Runtime user-supplied object data

Where the generic-tool path is used, the engine should distinguish the source of the object mass from persistent verified catalogue facts.

A recommendation may remain useful when the worker provides or measures the mass, but the result should state the basis clearly.

Example:

> Recommended based on the information provided: the selected configuration is rated above the 3 kg upper weight you confirmed. The exact tool model and catalogue mass could not be verified.

### Insufficient hard-constraint information

A required fact cannot be established and no validated runtime verification path can close the gap.

Examples:

- component capacity unknown;
- required cordless operational profile unresolved;
- connection topology ambiguous;
- interface compatibility has no acceptable basis and no validated field-verification procedure.

This can require abstention for the affected candidate.

## Recommendation states

### Recommended

Use when:

- hard constraints pass;
- all required physical connections are established or any required runtime verification has been successfully completed;
- the configuration is well suited to context; and
- no material qualification changes how the worker should interpret the result.

### Recommended with constraints

Use when:

- hard constraints pass;
- the configuration is viable;
- one or more practical limitations should be actively managed; or
- a specific runtime verification must be completed before use.

Example:

> This configuration meets the published load requirements. Before use, connect the carabiner to the D-ring and confirm that the gate closes and locks fully, the ring does not obstruct the gate, and the connector settles without obvious cross-loading.

### Limited-confidence recommendation

Use when:

- hard constraints can still be established;
- the configuration is defensible;
- secondary evidence is incomplete or the exact tethering combination has not previously been assessed as a named pairing.

The limitation should be specific rather than a generic disclaimer.

A validated runtime verification requirement should not automatically make a result "limited confidence"; it is a separate technical condition with an explicit procedure.

### No suitable recommendation

Use only when:

- all candidates fail a hard constraint;
- a required hard-constraint fact or operational configuration cannot be established;
- an interface remains unresolved and no validated runtime verification can close the gap;
- all candidates create an unacceptable hazard; or
- policy prevents every otherwise viable option and no permitted alternative exists.

## Explainability

Every recommendation should be explainable in worker-friendly terms.

At minimum:

- selected configuration;
- key reason it is viable;
- compatibility basis for each required physical connection;
- any runtime verification that must be completed;
- key reason it ranked highest;
- important caution; and
- policy conflict, where relevant.

Internally, the engine should be able to trace:

```text
Recommendation
  ↓
Candidate configuration
  ↓
Resolved Tool operational profile
  ↓
Derived operational-mass Claim
  ↓
Tool-body mass Claim + Battery-mass Claim
  ↓
Evidence / sources
```

alongside:

```text
Connection evaluation
  ↓
compatibility status + basis
  ↓
accepted Claims / validated Rule
  ↓
optional session verification observations
```

and the other tethering component Claims, rules and policy evidence used by the recommendation.

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

For connection reasoning, prefer:

```text
accepted primitive interface facts
        +
validated connection rule
        ↓
compatibility status + basis
```

over:

```text
IF endpoint.type = carabiner
AND target.type = ring
THEN compatible
```

This keeps the recommendation logic reusable.

## Mixed-manufacturer reasoning

Brand should not be treated as a tethering compatibility rule by default.

The engine should evaluate:

- rated capacities;
- interfaces;
- geometry where available;
- accepted compatibility bases;
- explicit restrictions;
- product facts;
- relevant reusable rules; and
- controlled runtime verification where applicable.

Manufacturer endorsement may be shown separately.

The manufacturer-backed relationship requirement for a cordless Tool/Battery operational profile is a configuration-evidence requirement, not a rule that all tethering components must share a brand.

## Initial rule set for the MVP

The first rule set should stay small.

Likely rules include:

### Hard constraints / deterministic derivation

- derive operational mass from accepted Tool-body + exact installed Battery mass;
- object operational mass must not exceed tether capacity;
- object operational mass must not exceed tool-attachment capacity where used;
- object operational mass must not exceed anchor-attachment capacity where used;
- object/contents mass must not exceed container capacity where used;
- required interfaces must have an acceptable compatibility basis;
- failed runtime connection verification invalidates that candidate for the session;
- explicit manufacturer hard limits must be respected where applicable.

### Context preferences

- prefer reduced free tether length in high-snag environments;
- prefer sufficient reach for the stated task;
- select anchorage method based on technical viability and configured policy.

### Cautions

- warn where a viable tether creates increased snagging potential;
- warn where relevant secondary environmental information is not established;
- surface manufacturer restrictions or non-endorsement where material to the decision;
- present required runtime connection verification as an actionable pre-use condition.

The rule set should expand only when real use cases justify it.

## User-facing wording principle

Cautions and verification requirements should be actionable.

Avoid:

> Use with caution.

Prefer:

> The tether is long enough to create additional snagging potential around the pipework. Keep excess tether clear of obstructions and use a shorter option if available.

Avoid:

> Check that the connector fits.

Prefer a validated bounded procedure such as:

> Attach the connector to the intended ring. Confirm that the gate closes and locks fully, the ring does not obstruct the gate, and the connector can settle without obvious cross-loading.

The goal is to help the worker manage the limitation.

## Recommendation-engine success criteria

The engine is working if:

- hard constraints are reliably enforced using configured operational mass where required;
- cordless Tools with multiple Batteries do not silently collapse to a bare-tool or arbitrary Battery mass;
- the same tool can produce different recommendations under different context;
- viable but imperfect options are not unnecessarily rejected;
- mixed-manufacturer tethering configurations can be evaluated;
- missing public connector dimensions do not automatically force catalogue-wide abstention when another acceptable compatibility basis exists;
- `requires_verification` is kept distinct from both `compatible` and genuinely `unresolved`;
- runtime field verification remains session/configuration evidence rather than universal catalogue compatibility;
- evidence limitations are communicated without generic over-warning;
- policy remains separate from technical suitability;
- rules can be reused across newly added products; and
- a recommendation can be traced back to the facts, compatibility bases, configuration relationships, dependencies, runtime observations and rules that produced it.
