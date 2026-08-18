# TetherLens Product Vision

## Purpose

TetherLens exists to help field-based workers choose a suitable dropped-object tethering solution at the point of use, without relying on memory, improvised judgement, or reference tools designed primarily for programme leads and office-based users.

The product should reduce the gap between a dropped-object prevention programme as designed and the decisions workers actually have to make in the field.

## The problem

A persistent problem in dropped-object prevention is not simply access to tethering equipment. It is determining what combination is suitable for the tool, the task, and the environment in which the work will actually be performed.

A tether may be strong enough for a tool and still be a poor choice in practice. The worker may be operating around pipework, inside a restricted space, near moving equipment, in the presence of contaminants, or with limited anchorage options. These conditions can change what constitutes a safe and practical tethering configuration.

Existing approaches such as catalogues, posters, product selectors, training, and manufacturer instructions can help when a tethering programme is designed, but they are often poorly suited to the worker who has to make a decision in the field.

When the answer is not obvious, workers may have to stop work, search through reference material, find someone who knows, use whatever equipment is available, improvise, or forgo tethering altogether.

TetherLens is intended to reduce that confusion and improvisation.

## Vision

**TetherLens is an AI-powered field assistant that turns a worker's tool and work context into the most suitable defensible tethering recommendation available.**

A worker should be able to show TetherLens the tool they intend to use, confirm what the tool is, provide or capture the relevant worksite constraints, and receive a tethering configuration supported by structured product data, reusable rules, and traceable evidence.

The durable product model is:

`tool + task + environment + anchorage -> ranked tethering recommendation`

The experience should make a well-reasoned tethering choice easier than improvisation.

## Primary user

The primary user is the **field-based worker** who needs to tether a tool before or during a task.

Programme leads, supervisors, HSE teams, engineers, and product specialists may maintain data, rules, policies, and evidence, but the core experience is designed around the person making the decision at the point of use.

## Core user job

> "I have this tool, in this situation. Tell me the best way to tether it, and what I need to watch out for."

TetherLens should reduce the distance between that question and an actionable answer.

## What success means

TetherLens succeeds if it helps move a worker from:

> "I can't figure out a practical way to tether this, so I'm not going to bother."

To:

> "This configuration lets me tether the tool safely. It may be slightly inconvenient, but I understand the limitations and can work with them."

The product does not need to make every tethering situation frictionless. It should make safe tethering more achievable and reduce the circumstances in which confusion or inconvenience leads to improvisation or non-compliance.

## What "suitable" means

A **suitable tethering configuration** is one that satisfies the applicable hard safety constraints and is practical for the stated work context.

Suitability is not binary. More than one viable configuration may exist, and some may be better suited to the task than others.

A suitable configuration may consider:

- the mass of the tool or contained objects relative to the rated capacity of every applicable load-bearing component;
- the integrity and appropriateness of the tool attachment;
- connector and interface compatibility;
- the intended anchorage and load path;
- environmental limitations of the components;
- task-specific hazards such as snagging, entanglement, restricted movement, or excessive reach;
- usability and interference with normal tool operation;
- available supporting evidence; and
- applicable site or organisation policy.

A configuration can therefore be technically viable while still carrying practical limitations that should be communicated to the worker.

## Four dimensions of a recommendation

### Hard constraints determine viability

Hard constraints determine whether a configuration can be recommended at all.

Examples may include:

- tool or object mass exceeding the rated capacity of an applicable component;
- an attachment method that cannot securely retain the tool;
- incompatible connectors or interfaces;
- an anchorage method that cannot satisfy the applicable load or policy requirements;
- a known environmental condition that makes a component unsuitable; or
- a configuration that introduces an unacceptable secondary hazard.

If a hard constraint fails, that configuration should not be recommended.

### Context determines suitability and ranking

Context affects which viable configuration is best for the task.

Examples may include:

- restricted or congested work areas;
- elevated snagging potential;
- required working reach;
- frequency of tool handling or transfer;
- contamination or cleaning requirements;
- whether body anchoring or structural anchoring is appropriate and permitted; and
- the position and type of available anchorage.

Context should influence ranking, cautions, and practical guidance rather than automatically forcing abstention.

### Evidence determines confidence and qualification

Evidence describes how strongly the product data and rules supporting the recommendation are established.

A recommendation can remain useful even where some secondary facts are incomplete, provided the hard constraints can still be determined.

### Policy determines permission

A technically suitable configuration may still be prohibited by a particular employer, site, project, or programme.

Technical suitability and policy permission are separate questions and should not be collapsed into a single "approved" status.

## Suitability, endorsement, and approval

TetherLens should distinguish between:

### Technical suitability

Whether the configuration satisfies the relevant hard constraints and is practical for the stated task and environment.

### Supporting evidence

What supports the underlying product facts and recommendation rules, such as manufacturer documentation, qualified exact-product secondary evidence where the property policy permits it, internal measurement, standards, engineering assessment, testing, or structured field evidence.

### Manufacturer endorsement

Whether a manufacturer explicitly endorses, restricts, prohibits, or does not address a particular combination.

Manufacturer endorsement is relevant information, but it is not the sole definition of technical suitability.

A technically suitable mixed-manufacturer configuration may exist even where a tool manufacturer only documents or endorses its own tethering products.

### Organisation or site approval

Whether a particular organisation or site permits the configuration under its own rules.

A configuration may be technically suitable but disallowed by policy. Site approval should likewise not make a technically unsuitable configuration acceptable.

## Recommendation outcomes

TetherLens should aim to provide the most useful defensible answer available.

### Recommended

The configuration satisfies the relevant hard constraints and is well suited to the stated context.

### Recommended with constraints

The configuration is viable, but it has meaningful practical limitations that the worker should manage.

For example, a tether may have sufficient capacity and compatible attachments but create more snagging potential than an ideal alternative.

### Limited-confidence recommendation

The available product data and reusable rules support the configuration, but some secondary evidence is incomplete or the exact combination has not previously been assessed as a named pairing.

Lack of exact combination-level validation should not automatically prevent a recommendation where the underlying facts and rules establish viability.

### No suitable recommendation

TetherLens should decline to recommend a configuration only when:

- a hard constraint cannot be satisfied;
- all available configurations create an unacceptable hazard; or
- information required to determine whether a hard constraint is satisfied is unavailable or cannot be resolved.

Abstention is a necessary outcome, but it should not be the default response to imperfect information or a merely suboptimal context.

## Product principles

### 1. Field first

The product should be fast, mobile, and usable where the work happens. Every additional step must justify the friction it adds.

### 2. Provide the most useful defensible answer

TetherLens should prefer a useful recommendation with clearly stated limitations over an unnecessarily binary pass/fail response.

### 3. Context is part of the problem

The same tool may require different tethering configurations in different tasks or environments.

Task, environmental, and anchorage constraints are first-class product inputs.

### 4. Recognition is a means, not the product

Computer vision is valuable because it reduces lookup friction. The value of TetherLens is not identifying a drill, hammer, spanner, or other tool; it is helping the worker reach the right tethering decision.

### 5. Product data should describe what an item is, not where someone thinks it should be used

The knowledge base should favour reusable primitive facts such as mass, rated capacity, length, materials, and interface geometry.

Application-level conclusions such as "suitable for scaffolding" or "suitable for hot work" should normally be derived from those facts and the work context through reusable rules.

Explicit manufacturer limitations should still be retained where they contain information that cannot safely be derived from lower-level properties.

### 6. Structured data and reusable rules are the foundation

AI may help identify tools, gather context, extract product information, and explain recommendations, but compatibility decisions should be grounded in structured data and explicit rules.

### 7. Validate facts and rules, not every permutation

TetherLens should not require every individual tool-and-tether combination to be manually approved before it can provide a recommendation.

Where the relevant product properties, interfaces, limits, and compatibility rules are known, the system should be able to reason over combinations in a controlled and explainable way.

### 8. Safety-critical facts should not be guessed

Physical tool and battery mass should be established from trustworthy evidence bound to the exact product identity. Manufacturer evidence is preferred; where manufacturer mass is unavailable or incomplete, a reputable verified exact-SKU secondary source may be accepted for physical mass.

Rated capacity of every applicable load-bearing component must come from manufacturer information.

Neither physical mass nor rated capacity should be visually inferred, guessed from a similar product, or taken from an unverified aggregate/search result for catalogue recommendation purposes.

Interface compatibility should be established through published geometry, internal measurement, explicit manufacturer compatibility, or another sufficiently reliable method.

### 9. Uncertainty should be visible

Missing or incomplete secondary information should limit the conclusions TetherLens draws rather than being silently filled with assumptions.

### 10. Recommendations should be explainable

The worker should be able to understand why a configuration is being recommended, which constraints matter, and what limitations need to be managed.

### 11. Manufacturer lock-in is not a compatibility model

TetherLens should not assume that equipment from different manufacturers is incompatible simply because one manufacturer only documents its own products.

Where sufficient evidence and compatible product properties exist, TetherLens should be able to recommend mixed-manufacturer configurations.

### 12. The knowledge base should scale independently of the AI model

Recognition, product facts, evidence, rules, context, and policy should remain separable.

This allows the product catalogue and recommendation logic to evolve without requiring the recognition system itself to be rebuilt.

## Product boundary

TetherLens is not intended to replace formal dropped-object prevention programmes, competent-person judgement, site procedures, product instructions, or engineering controls.

It is also not primarily:

- an asset-management system;
- an inventory or procurement platform;
- a training management system;
- a generic chatbot about working at height;
- an automated engineering approval system;
- a system that treats manufacturer endorsement as the only definition of compatibility; or
- a system that generates unconstrained tethering advice without sufficient supporting data.

## Long-term product direction

Over time, TetherLens could expand into a broader field knowledge layer for tool tethering.

Potential capabilities include:

- recognising a wider range of tools and exact models where practical;
- interpreting parts of the work environment from images or video;
- prompting only for contextual information that materially affects a recommendation;
- dynamically evaluating compatible components against explicit rules;
- ranking multiple viable configurations according to task and environmental suitability;
- supporting mixed-manufacturer configurations backed by controlled evidence;
- incorporating site-specific rules and policy;
- presenting complete configuration and installation guidance;
- learning from worker corrections and field feedback;
- using aggregated feedback to identify recurring application problems;
- allowing programme leads or technical authorities to maintain product data, rules, and policies; and
- identifying common situations in which available tethering products are technically viable but operationally inconvenient.

The last of these is important: TetherLens should not only help workers use existing products better. Over time, it should reveal where the industry still lacks practical solutions.

## What success looks like

TetherLens succeeds when a worker can move from:

**"I have to use this tool here. How can I tether it without creating another problem?"**

To:

**"This is the best available configuration for this task, I understand any limitations, and I can proceed without having to improvise."**

in a matter of seconds, with less dependence on memory, searching, or trial and error.
