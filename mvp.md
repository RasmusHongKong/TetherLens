# TetherLens MVP

## Objective

The MVP should test whether TetherLens can turn a maintainable, reusable body of product knowledge into field recommendations that are more useful and convenient than existing alternatives.

It therefore has two equally important sides:

1. **Demand-side usability:** can a field worker receive a useful tethering recommendation through a workflow that is more convenient than current lookup methods?
2. **Supply-side scalability:** can the product knowledge required to generate those recommendations be added and maintained efficiently enough for the system to scale?

The MVP is not successful if only one of these is true.

## Core MVP proposition

> **Can TetherLens identify a tool, capture the work context that matters, and produce a useful defensible tethering recommendation using a knowledge base that can be expanded primarily by adding reusable product facts rather than manually authoring every tool-to-tether combination?**

## Demand-side hypotheses

### 1. Camera-first lookup reduces friction

For a curated tool catalogue, image recognition can get the worker to the correct tool faster than manual lookup.

### 2. Workers can provide the missing context

Where worksite conditions materially affect the recommendation, TetherLens can ask a small number of targeted questions that a worker can answer without specialist knowledge.

### 3. Context changes recommendations meaningfully

For at least some tools, different task, environmental, or anchorage conditions should result in a different recommended configuration, ranking, caution, or genuine no-suitable-solution outcome.

### 4. Useful recommendations can be graded

TetherLens can distinguish between:

- recommended;
- recommended with constraints;
- limited-confidence recommendation; and
- no suitable recommendation.

The system should not abstain solely because a viable option is imperfect.

### 5. Mixed-manufacturer recommendations are possible

TetherLens can evaluate products according to technical facts, interfaces, and reusable rules rather than assuming that all tethering components must come from the same manufacturer.

## Supply-side hypotheses

### 1. Product ingestion can remain fact-based

Adding a product can primarily consist of capturing low-level technical facts and their sources rather than manually classifying the product for every possible application.

### 2. Existing rules can be reused

A newly added tool or tethering component can participate in recommendations through existing rules without requiring a manually curated compatibility entry for every pairing.

### 3. Missing secondary data does not block the catalogue unnecessarily

Products can become recommendation-ready once the mandatory recommendation facts are known, while richer data improves later ranking and context sensitivity.

### 4. Evidence remains traceable without creating an excessive maintenance burden

The system can record where mandatory facts and rules came from without making ingestion so onerous that the catalogue becomes impractical to build.

### 5. The model scales by adding facts, not exceptions

As more products are added, the proportion of products requiring one-off rules or manually authored pairings should remain low.

## MVP user

The demand-side MVP is designed for a worker using a mobile phone at the point of use.

The supply-side MVP is designed for the person maintaining the TetherLens catalogue. This may initially be an internal technical or product specialist rather than an end customer.

## Pilot catalogue

The pilot should be large enough to exercise reuse and variation rather than merely prove that two database records can be linked.

A useful initial target is:

- approximately **15-30 tools**; and
- approximately **20-40 tethering components** across relevant categories.

Supporting configuration products such as interchangeable Batteries are additional catalogue records where needed to establish a Tool's operational state; they are not counted as tethering components merely because they appear in the product graph.

The exact numbers are less important than the diversity.

The catalogue should deliberately include:

- multiple manufacturers;
- several tools that can use the same tethering components;
- several components that can work with multiple tools;
- at least some cordless tools with more than one valid installed-battery mass profile;
- mixed-manufacturer tethering configurations;
- different attachment mechanisms;
- different capacities and lengths;
- body-anchoring and structural-anchoring scenarios;
- products with excellent manufacturer data;
- products with incomplete public geometry or material data;
- cases requiring internal measurement; and
- scenarios where context affects the preferred configuration.

## Demand-side scope

### 1. Mobile-first image capture

The worker can take or upload a photograph of **one tool at a time**.

The MVP does not need to interpret a full toolbox, workbench, or scene containing multiple candidate tools.

### 2. Recognition against the pilot catalogue

The recognition layer attempts to match the image to the curated tool catalogue.

The system may return one likely match or a short list of candidates.

### 3. User confirmation

Before a recommendation is shown, the worker confirms the identified tool.

Where visually similar tools cannot be distinguished reliably, TetherLens should ask for the smallest amount of additional information required to resolve the ambiguity.

For a cordless Tool whose load reasoning depends on the installed Battery, confirmation of the Tool identity alone is not enough if several materially different operational mass profiles remain possible. The workflow should resolve the applicable Battery/profile through the least-friction reliable method available; the MVP does not require automatic battery recognition from the image.

### 4. Targeted context questions

The MVP should include a deliberately small set of contextual inputs that can materially change the recommendation.

The pilot should cover approximately **3-5 contextual dimensions**, selected from real use cases, such as:

- restricted or congested working space / elevated snag risk;
- relevant contaminant or environmental exposure;
- available anchorage method;
- reach or tether-length constraint; and
- another pilot-specific condition that affects practical suitability.

The MVP does not need to infer these conditions automatically from the camera image.

### 5. Candidate configuration generation

The system should identify candidate configurations from the available product catalogue.

For the MVP, this may use a mixture of:

- predefined compatible interface relationships;
- reusable compatibility rules; and
- a limited number of curated configurations where necessary.

The goal is to reduce reliance on manually authored exact tool-to-tether pairings over time.

A resolved cordless Tool operational profile is an input to candidate generation/load checking, not a separately tethered component in the candidate configuration.

### 6. Hard-constraint evaluation

The recommendation engine should remove configurations that fail defined hard constraints.

At minimum, the MVP should evaluate:

- verified **operational object/tool mass** from evidence acceptable for the physical-mass property and exact product/configuration identity;
- manufacturer-published rated capacity of every applicable load-bearing component; and
- sufficient evidence of interface compatibility.

For a non-battery Tool whose physical mass is not configuration-dependent, the accepted Tool mass may be used directly.

For a cordless Tool with an interchangeable installed Battery, operational mass must be represented explicitly as:

```text
accepted exact Tool body mass
  + accepted exact Battery mass
  + manufacturer-backed Tool/Battery configuration relationship
  -> validated operational mass profile
```

The load rule must use that profile mass. Bare-tool mass must not be substituted when an installed Battery is required, and one profile must not be selected arbitrarily when several compatible Batteries exist.

For catalogued Tool-body and Battery mass, manufacturer evidence is preferred. A reputable exact-SKU secondary product-detail source may be accepted where manufacturer physical mass is unavailable or incomplete, with provenance retained. Visual inference, similar-model estimates and unverified aggregate/search results are not acceptable catalogue mass evidence.

### 7. Context-based ranking and cautions

Configurations that pass hard constraints should be ranked according to work context.

A viable option should not automatically be rejected because it is less than ideal.

Where a viable option has a meaningful limitation, TetherLens should recommend it with an appropriate caution if it remains the best defensible choice.

### 8. Policy treatment

The MVP data model should distinguish technical viability from site or organisation policy.

A simple static policy layer is sufficient for the pilot.

### 9. Result screen

The result should answer:

- What tool did I confirm?
- Which operational configuration/mass was used where relevant?
- What tethering configuration should I use?
- How should it be attached?
- Why is this the best available option here?
- What limitations or hazards should I watch for?
- Is the recommendation constrained by incomplete secondary data?
- Is there any manufacturer or site-policy conflict I should be aware of?

### 10. Lightweight feedback

The worker should be able to indicate that:

- the tool identification was wrong;
- the installed configuration/battery was wrong where relevant;
- the correct tool was not listed;
- the work context was not represented;
- the recommended configuration was impractical; or
- the recommendation was otherwise not useful.

## Supply-side scope

### 1. Minimal product-ingestion workflow

The MVP should include a simple way to add tools and tethering components.

This does not require a polished administration application. A controlled form, spreadsheet-backed workflow, structured editor, or similar internal interface is acceptable.

The workflow should be:

`identify product -> add source(s) -> capture primitive facts/relationships -> identify mandatory gaps -> enrich where necessary -> recommendation-ready`

### 2. Primitive facts only

The ingestion workflow should capture what the product **is**, not where someone thinks it should be used.

Examples include:

- manufacturer;
- model / SKU;
- Tool-body or Battery mass, where applicable;
- manufacturer-backed Tool/Battery configuration relationships where required;
- rated capacity, where applicable;
- tether length;
- connector type and geometry;
- relevant attachment geometry;
- materials, at the level actually known;
- explicit manufacturer limits; and
- data source/provenance.

Derived operational mass profiles should be computed from accepted primitive mass Claims and valid configuration relationships rather than entered as unexplained standalone numbers.

The workflow should avoid application-level fields such as:

- `suitable_for_scaffolding`;
- `suitable_for_hot_work`;
- `suitable_for_offshore`; or
- `suitable_for_tight_spaces`.

Those should normally be derived through reusable rules and work context.

### 3. Recommendation-ready threshold

A product or component becomes recommendation-ready when the mandatory facts required for the relevant recommendation logic are established.

For baseline tethering recommendations, the mandatory facts are:

- **object/tool operational mass** from trustworthy exact-product/configuration physical evidence, with manufacturer evidence preferred and reputable exact-SKU secondary evidence permitted for physical Tool/Battery mass where manufacturer mass is unavailable or incomplete;
- **rated capacity** from manufacturer information for every applicable load-bearing component; and
- **sufficient interface compatibility information** to establish that required connections can be made correctly.

For a cordless Tool requiring an installed interchangeable Battery, operational-mass readiness additionally requires:

- exact Tool identity and accepted Tool-body mass;
- exact Battery identity and accepted Battery mass;
- manufacturer-backed Tool/Battery validity; and
- a derived operational profile whose dependency chain points to those accepted primitive Claims.

If several valid profiles exist, a recommendation must resolve which profile applies before load checks; it must not silently choose one.

Interface compatibility may be established through:

- published dimensions;
- internal measurement;
- explicit manufacturer pairing or kit compatibility; or
- another sufficiently reliable reusable interface rule.

Everything else enriches recommendations rather than automatically blocking them.

### 4. Evidence capture

Mandatory facts should be traceable to a source.

Persisted derived operational mass should additionally be traceable to its primitive input Claims and the manufacturer-backed configuration relationship that makes the Tool/Battery combination valid.

Evidence capture should be lightweight enough that it does not dominate product ingestion.

### 5. Rule reuse

The MVP should intentionally test whether newly added products can be evaluated by existing rules.

The target operating model is:

`new product -> capture reusable facts/relationships -> existing rules evaluate configurations`

not:

`new product -> manually create every compatible tethering pairing`

## Two-stage scalability test

The MVP should deliberately test the supply-side model in two stages.

### Stage 1: establish the initial catalogue and rules

Build a small but diverse initial set of tools and tethering components, plus supporting configuration products such as Batteries where required.

Create only the reusable rules required to produce sensible recommendations for that set.

### Stage 2: freeze the core rules and add a new batch

Add a second batch of previously unseen tools and components without redesigning the model.

Measure:

- how many products become recommendation-ready through fact capture alone;
- how often additional configuration relationships/profiles are required for cordless tools;
- how often internal measurement is required;
- how often a new reusable rule is genuinely needed;
- how often a one-off compatibility exception is required;
- how many candidate configurations become available automatically; and
- whether existing products need to be manually edited as a side effect.

If most new products require custom rules or hand-authored tethering pairings, the model is not yet scalable.

## Suggested MVP data concepts

The MVP should represent at least:

### Operational product entities

- Tool
- Battery — supporting configuration product where required
- OperationalMassProfile — derived Tool configuration, not a tethering component
- Tether
- ToolAttachment
- AnchorAttachment
- Container

Not every recommendation uses all four tethering component categories. Tethers will always be present; the other tethering categories apply as required by the configuration. Batteries/operational profiles only apply where the Tool configuration requires them.

### Knowledge and reasoning entities

- Source
- Claim
- Claim dependency for persisted derived facts
- Evidence
- Declared manufacturer relationship
- Rule
- Context
- Policy
- CandidateConfiguration / Recommendation

The precise physical database schema is defined separately in `technical-schema.md`.

## Demand-side success criteria

A useful initial bar is:

- **Recognition:** the correct in-scope tool appears in the proposed candidate set for at least 90% of representative test images.
- **Confirmation:** users can reach the correct tool selection without outside help in at least 90% of in-scope tasks.
- **Configuration resolution:** where a cordless Tool has materially different operational mass profiles, users can resolve the applicable installed configuration without specialist help in at least 90% of test scenarios requiring it.
- **Context capture:** users can answer required contextual questions without specialist help in at least 90% of test scenarios.
- **Hard-constraint integrity:** configurations that fail a defined hard constraint are never recommended, and load checks never substitute bare-tool mass for a required operational profile.
- **Context sensitivity:** where a scenario requires a different ranking, caution, or outcome, the system produces the expected result.
- **Recommendation usefulness:** where at least one viable configuration exists, TetherLens provides a useful recommendation rather than abstaining solely because the option is imperfect.
- **Speed:** median time from image capture to recommendation is under 45 seconds for scenarios requiring context/configuration questions and under 30 seconds where no such questions are required.
- **Usability:** pilot users judge the workflow easier or more useful than the reference method they would otherwise use.

## Supply-side success criteria

The MVP should also measure:

### Time to recommendation-ready product

Human time required from initial product identification to recommendation-ready status.

### Mandatory-data availability

What proportion of products can reach recommendation-ready status using public first-party information alone, and what additional proportion can be completed through evidence-qualified deterministic secondary sources where the property policy permits them.

### Operational-profile coverage

For cordless Tools requiring installed Batteries, what proportion have one or more validated operational mass profiles, and how many compatible configurations can be represented without product-specific code.

### Enrichment burden

How often internal measurement or additional research is required.

### Rule reuse

How often adding a product requires no new rule.

### Compatibility leverage

How many viable candidate configurations become possible from newly added facts without manually authoring each tethering pairing.

### Maintenance locality

Changing one product fact should not require manual updates across many unrelated compatibility records. When a Tool-body or Battery mass Claim changes, dependent operational profiles should be identifiable from explicit dependency links and re-derived locally.

### Evidence traceability

Every mandatory fact used in a recommendation can be traced to a source; persisted operational mass can also be traced to its exact primitive mass Claims and configuration relationship.

### Exception rate

The proportion of products that require one-off compatibility logic should remain low.

Hard numerical thresholds for these supply-side metrics should be set after the first ingestion batch establishes a realistic baseline.

## Pilot scenarios

The pilot should intentionally include cases where:

- the same cordless Tool has multiple valid Battery operational profiles;
- the same tool produces different recommendations under different work conditions;
- a shorter or coiled tether is preferred because of snagging risk;
- a viable but suboptimal tether is recommended with a caution because a better option is unavailable;
- a component is excluded because of a hard constraint;
- person anchoring is technically possible but site policy changes whether it is permitted;
- a mixed-manufacturer tethering configuration is viable;
- a manufacturer explicitly endorses a component pairing;
- connector compatibility is established through internal measurement rather than public dimensions;
- secondary material data is incomplete but a baseline recommendation remains possible; and
- no viable configuration exists.

## Deliberate non-goals

The MVP will not attempt to provide:

- recognition of arbitrary tools outside the pilot catalogue;
- multiple-tool or full-scene recognition;
- automatic recognition of every installed Battery/configuration from images;
- automatic understanding of all worksite conditions from images or video;
- unrestricted dynamic generation of arbitrary tethering configurations;
- automatic engineering assessment of structural anchor points;
- complete inventory or asset management;
- procurement or stock availability;
- organisation-wide user management or SSO;
- a native iOS or Android application;
- offline operation;
- augmented-reality overlays;
- a general-purpose conversational safety assistant;
- training records or competency management;
- programme analytics dashboards;
- automated ingestion of every manufacturer's catalogue; or
- automated creation of new engineering rules from user feedback.

## What the MVP should teach us

Before expanding TetherLens, the MVP should answer:

1. Do workers prefer a camera-first workflow for this problem?
2. Is recognition reliable enough to reduce lookup friction?
3. Can workers resolve the installed configuration when it materially changes cordless Tool mass?
4. Which contextual factors materially change tethering decisions most often?
5. Can workers provide those factors through a small number of questions?
6. Can the recommendation engine provide useful answers without manually validating every exact tethering combination?
7. Which facts are genuinely required to make a baseline recommendation?
8. How much public manufacturer data is sufficient for catalogue ingestion?
9. How often can qualified deterministic secondary evidence close permitted physical-data gaps?
10. How often is internal measurement required?
11. Can new products reuse existing rules?
12. Does the number of one-off exceptions remain manageable as the catalogue grows?
13. How often does TetherLens genuinely need to return no suitable recommendation?
14. Do workers continue to trust the system when the best available option is imperfect?
15. Is maintaining the product, evidence, configuration-profile, and rule base operationally practical?

## Exit criteria

The MVP is successful enough to justify expansion when:

- field users can complete the recommendation workflow with little or no assistance;
- hard constraints are reliably enforced using configured operational mass where required;
- cordless Tool mass configurations can be represented and resolved without arbitrary Battery selection;
- viable configurations are ranked appropriately for context;
- useful recommendations can be made without manually validating every exact tethering combination;
- mixed-manufacturer tethering configurations can be represented and evaluated;
- new products can usually be added through fact capture and evidence rather than one-off application judgement;
- rule reuse remains high as the catalogue grows;
- mandatory evidence and derived operational dependencies remain traceable;
- no-suitable-recommendation outcomes are limited to genuine hard-stop cases; and
- the team can identify a credible path to scaling the catalogue without fundamentally changing the knowledge model.
