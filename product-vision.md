# TetherLens Product Vision

## Purpose

TetherLens exists to help field-based workers choose a suitable dropped-object tethering solution at the point of use, without relying on memory, improvised judgement, or reference tools designed primarily for programme leads and office-based users.

## The problem

A persistent problem in dropped-object prevention is not simply access to tethering equipment. It is determining what combination is suitable for the tool, the task, and the environment in which the work will actually be performed.

A tether may be strong enough for a tool and still be a poor choice in practice. The worker may be operating around pipework, inside a restricted space, near rotating equipment, in the presence of contaminants, or with limited anchorage options. These conditions can change what constitutes a safe and practical tethering configuration.

Existing approaches such as catalogues, posters, product selectors, training, and manufacturer instructions can help when a tethering programme is designed, but they are often poorly suited to the worker who has to make a decision in the field.

This creates a gap between the programme as designed and the task as performed. When the answer is not obvious, workers may have to stop work, search through reference material, find someone who knows, use whatever equipment is available, or forgo tethering altogether.

## Vision

**TetherLens is an AI-powered field assistant that turns a worker's tool and work context into a verified tethering recommendation.**

A worker should be able to show TetherLens the tool they intend to use, confirm what the tool is, provide or capture the relevant worksite constraints, and receive a suitable tethering configuration supported by structured compatibility data and evidence.

The durable product model is:

`tool + task + environment + anchorage -> suitable tethering configuration`

The experience should make the correct path easier than improvisation.

## Primary user

The primary user is the **field-based worker** who needs to tether a tool before or during a task.

Programme leads, supervisors, HSE teams, engineers, and product specialists may maintain rules, policies, validation evidence, or approved catalogues, but the core experience is designed around the person making the decision at the point of use.

## Core user job

> "I have this tool, in this situation. Tell me how I should tether it using a solution I can trust."

TetherLens should reduce the distance between that question and an actionable answer.

## What "suitable" means

A **suitable tethering configuration** is one that:

- is technically compatible with the tool and all tethering components involved;
- remains within the verified performance limits of every component;
- is appropriate for the intended attachment method and available anchorage;
- accounts for relevant task and environmental constraints;
- does not introduce an unacceptable interference, snagging, reach, handling, or usability problem;
- is supported by sufficient evidence to meet the defined TetherLens validation standard; and
- is presented with any important conditions, limitations, or policy conflicts made explicit.

Suitability is therefore broader than weight rating alone.

It is also distinct from manufacturer endorsement or site approval.

## Suitability, validation, endorsement, and approval

TetherLens should treat the following as separate concepts.

### Technical suitability

Whether the configuration is safe and practical for the tool and work context based on verified engineering and product constraints.

### Validation evidence

What supports the suitability judgement, such as product documentation, relevant standards, certification, manufacturer test data, independent test data, engineering assessment, internal validation, or other controlled evidence.

### Manufacturer endorsement

Whether a tool or tether manufacturer explicitly endorses, restricts, prohibits, or does not address a particular combination.

Manufacturer endorsement is useful evidence, but it is not the sole definition of technical suitability.

A technically valid mixed-manufacturer configuration may exist even where a tool manufacturer only documents or endorses its own tethering products.

### Organisation or site approval

Whether a particular employer, site, project, or programme permits the configuration under its own rules.

A configuration may be technically suitable but disallowed by a site policy. Conversely, site approval should not make a technically unsuitable configuration acceptable.

TetherLens should preserve these distinctions rather than collapsing them into a single "approved" flag.

## Product principles

### 1. Field first

The product should be fast, mobile, and usable where the work happens. Every additional step must justify the friction it adds.

### 2. Context is part of the problem

The same tool may require different tethering configurations in different tasks or environments.

Task, environmental, and anchorage constraints are first-class product inputs, not optional metadata to be added later.

### 3. Recognition is a means, not the product

Computer vision is valuable because it reduces lookup friction. The value of TetherLens is not identifying a drill, hammer, spanner, or other tool; it is helping the worker reach the right tethering decision.

### 4. Structured data is the source of truth

AI may help identify tools, interpret images, and gather context, but it should not invent compatibility relationships or claim that an unvalidated configuration is suitable.

Recommendations should resolve to curated data describing tools, components, configurations, constraints, evidence, and policy status.

### 5. Safety-critical properties should not be guessed

Properties such as exact tool mass, component capacity, attachment suitability, material compatibility, anchorage requirements, or environmental limitations may not be reliably inferable from an image.

The product should use maintained data, explicit user confirmation, validated inference, or configured site information for these properties.

### 6. Uncertainty must be visible

TetherLens should not pretend to know what it cannot reliably determine.

Where identification or context is uncertain, the worker should be asked for clarification. Where no verified configuration exists, the product should say so clearly rather than generate a plausible answer.

### 7. Recommendations should be explainable

The worker should be able to understand why a configuration is being recommended and which conditions matter.

The product should surface the important compatibility factors, limitations, and any conflict between technical suitability, manufacturer endorsement, and site policy.

### 8. Manufacturer lock-in is not a compatibility model

TetherLens should not assume that equipment from different manufacturers is incompatible simply because one manufacturer only documents its own products.

Where sufficient evidence exists, TetherLens should be able to validate safe and practical mixed-manufacturer configurations.

Equally, manufacturer restrictions should not be hidden. They should be represented as evidence or policy information and shown when relevant.

### 9. The knowledge base should improve independently of the AI model

Recognition, compatibility logic, validation evidence, and policy should remain separable.

This allows the catalogue, engineering rules, evidence base, and site policies to evolve without requiring the recognition system itself to be rebuilt.

### 10. Safe abstention is a valid outcome

A trustworthy system sometimes has to say that it does not have enough information or evidence to recommend a solution.

A clear "no verified recommendation available" outcome is preferable to false certainty.

## Product boundary

TetherLens is not intended to replace formal dropped-object prevention programmes, competent-person judgement, site procedures, product instructions, or engineering controls.

It is also not primarily:

- an asset-management system;
- an inventory or procurement platform;
- a training management system;
- a generic chatbot about working at height;
- an automated engineering approval system;
- a system that treats manufacturer endorsement as the only definition of compatibility; or
- a system that generates novel tethering configurations without sufficient supporting evidence.

Those capabilities may exist around the product in future, but they are not the reason TetherLens exists.

## Long-term product direction

Over time, TetherLens could expand from a focused identification-and-recommendation workflow into a broader field knowledge layer for tool tethering.

Potential capabilities include:

- recognising a wider range of tools and, where practical, exact models;
- interpreting parts of the work environment from images or video;
- prompting only for contextual information that materially affects the recommendation;
- supporting organisation-specific approved tool, component, and configuration catalogues;
- evaluating multiple tethering configurations against task and environmental constraints;
- supporting mixed-manufacturer configurations backed by controlled evidence;
- incorporating site rules and policy overrides;
- presenting complete configurations and field installation guidance;
- learning from worker corrections, failed recognitions, and rejected recommendations;
- allowing programme leads or technical authorities to maintain compatibility rules and validation evidence; and
- providing aggregate insight into the situations in which workers most often struggle to tether equipment correctly.

These are extensions of the core vision, not requirements for the first product.

## What success looks like

TetherLens succeeds when a worker can move from:

**"I have to use this tool here. How can I tether it without creating another problem?"**

to:

**"This configuration is suitable for this tool and this task, I understand the important constraints, and I know whether there are any manufacturer or site-policy limitations."**

in a matter of seconds, with less dependence on memory, searching, or improvisation.
