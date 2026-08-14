# TetherLens Ingestion Benchmark

## Status

Initial benchmark specification and exploratory baseline, created 2026-08-14.

This benchmark tests the main supply-side uncertainty in TetherLens:

> Can a manufacturer product identity be converted into recommendation-ready structured knowledge with sufficiently little product-specific human effort to scale to hundreds or thousands of products?

The benchmark deliberately measures **data availability** separately from **data accessibility**.

A fact may exist publicly but still be expensive to ingest if it is hidden behind dynamic rendering, spread across multiple documents, represented inconsistently across variants, or difficult to normalize.

The benchmark is not intended to prove that a human or an LLM can eventually find a value. It is intended to test whether repeatable acquisition and normalization strategies can do most of the work.

---

# 1. Frozen Batch 1 scope

The full Batch 1 product list is frozen apart from one correction:

- Milwaukee kit `2602-22DC` is replaced by the canonical tool-only identity `2602-20`.

The first benchmark run covers four deliberately different manufacturer patterns:

- NLG
- Hilti
- StopDrop
- Milwaukee

The current subset contains 12 canonical products:

| Manufacturer | Products |
|---|---:|
| NLG | 4 |
| Hilti | 3 |
| StopDrop | 4 |
| Milwaukee | 1 |
| **Total** | **12** |

Detailed product-level results are stored in `ingestion-benchmark-batch1.csv`.

---

# 2. Cordless-tool operational mass convention

For TetherLens load reasoning, a battery-powered power tool must use its **operational mass**, including the installed battery.

Bare-tool mass is not sufficient because the tool is not used in that state.

The benchmark must therefore record separately:

- tool-body mass;
- compatible battery configuration(s);
- battery mass; and
- derived operational mass for the configuration being evaluated.

Example from the first Hilti test:

```text
SF 4-22 tool body mass = 1.30 kg
B 22-55 battery mass   = 0.55 kg
--------------------------------
operational mass       = 1.85 kg
```

or:

```text
SF 4-22 tool body mass = 1.30 kg
B 22-85 battery mass   = 0.76 kg
--------------------------------
operational mass       = 2.06 kg
```

Both component masses are available from first-party Hilti technical data.

This confirms that a single invariant `tool.mass_kg` is not always sufficient for cordless products. The schema should eventually represent operational mass profiles/configurations rather than silently storing bare-tool mass or choosing an arbitrary battery.

This schema change should be made after the benchmark has tested the pattern across more than one power-tool manufacturer.

---

# 3. Benchmark questions

For every product, the benchmark asks the following questions in order.

## 3.1 Discovery

Given a manufacturer plus model/SKU/product code:

1. Can the canonical first-party product page be found deterministically?
2. Is there a manufacturer catalogue/listing surface from which products can be enumerated?
3. Are there stable product IDs, SKUs, variant IDs, family IDs, or URLs that can be retained for refreshes?

## 3.2 Acquisition

Which source channels are available?

```text
structured JSON / API-like endpoint
structured static HTML
semi-structured static HTML
dynamically rendered HTML
manufacturer PDF / technical document
manufacturer relationship / related-products data
image-only information
```

The benchmark records source type rather than treating all webpages as equivalent.

## 3.3 Extraction

Can deterministic extraction recover candidate low-level facts such as:

- identity;
- mass / rated capacity;
- length;
- product form;
- connector/interface type;
- locking/action characteristics;
- material;
- declared restrictions;
- product relationships; and
- document links?

An LLM may later be tested as a document-extraction aid, but **LLM browsing product-by-product is not the baseline ingestion strategy**.

## 3.4 Normalization

Can extracted values be converted to TetherLens vocabulary and canonical units without product-specific code?

Examples:

```text
15 lb -> 6.803886 kg
80cm to 120cm -> min_length_mm=800, max_length_mm=1200
"double action" -> opening_action_count=2
```

Normalization must preserve the source value in Evidence while writing normalized candidate Claims separately.

## 3.5 Evidence qualification

Does the source meet the evidence requirement for the Claim?

Examples:

- manufacturer technical page: acceptable for manufacturer-stated capacity;
- manufacturer datasheet: acceptable for manufacturer-stated capacity;
- internal measurement: acceptable for connector geometry;
- retailer page: potentially useful for discovery/corroboration but not the normal source for mandatory manufacturer mass/capacity.

## 3.6 Recommendation-readiness

After automated acquisition/extraction, which mandatory facts remain missing?

The benchmark distinguishes:

```text
available and machine-extractable
available but requires another manufacturer source
available but requires document extraction
not publicly established
requires internal measurement
requires product-specific engineering review
```

---

# 4. Benchmark metrics

The benchmark should collect the following metrics once adapters are executable.

## Discovery metrics

- exact first-party discovery rate;
- products enumerated from manufacturer catalogue surfaces;
- duplicate/variant resolution rate;
- stable identifier coverage.

## Acquisition metrics

- requests/sources required per product;
- percentage with structured catalogue endpoints;
- percentage with static parseable HTML;
- percentage requiring dynamic/JS acquisition;
- percentage with downloadable technical documents;
- document download success rate.

## Extraction metrics

- primitive candidate Claims extracted per product;
- mandatory scalar fact yield before human review;
- field-level extraction precision after review;
- unit-normalization success rate;
- declared-constraint extraction yield;
- relationship extraction yield.

## Readiness metrics

- percentage recommendation-ready from public first-party information alone;
- percentage requiring an additional manufacturer document;
- percentage requiring internal measurement;
- percentage blocked by missing mandatory manufacturer data;
- blocking field distribution.

## Human-effort metrics

- human review minutes per product;
- LLM-assisted extraction rate;
- manual research rate;
- manual correction rate;
- product-specific code/change rate.

## Reuse metrics

- products handled by an existing manufacturer adapter without code changes;
- reusable connector/interface measurements created;
- products unlocked per reusable measurement;
- new schema concepts required per batch;
- bespoke exception rate.

## Refresh metrics

A later repeat run should also record:

- source changes detected;
- unchanged facts correctly retained;
- candidate changes generated rather than silently accepted;
- discontinued/redirected products detected;
- adapter breakage rate.

---

# 5. Acquisition tiers

These tiers describe ingestion cost, not product quality.

## Tier A — deterministic structured acquisition

Typical characteristics:

- machine-readable catalogue/listing surface;
- highly regular product pages;
- stable field labels;
- downloadable supporting documents;
- little product-specific parsing logic.

Expected strategy:

```text
manufacturer adapter -> deterministic extraction -> normalization -> review
```

## Tier B — deterministic multi-source acquisition

Facts are public and structured enough to automate, but must be joined across:

- product page;
- regional page;
- battery/accessory page;
- technical document;
- related-products relationship; or
- manufacturer technical library.

Expected strategy:

```text
manufacturer adapter -> source graph -> deterministic/document extraction -> normalization -> review
```

## Tier C — difficult acquisition / enrichment

Typical characteristics:

- dynamic specs;
- sparse manufacturer pages;
- inconsistent variants;
- important facts only in documents or hidden endpoints;
- missing interface geometry.

A manufacturer-specific dynamic/API adapter, document extraction, internal measurement, or limited human research may be required.

## Tier D — source blocked

Mandatory facts cannot be established from acceptable sources.

No amount of better parsing makes the product recommendation-ready until the underlying evidence gap is addressed.

---

# 6. Initial exploratory baseline

This first run is a source-surface audit rather than a timed executable scraper run. It establishes what the future adapters need to target.

## 6.1 NLG

### Observed acquisition pattern

NLG currently provides an unusually ingestion-friendly combination of:

1. category/collection pages;
2. machine-readable collection JSON views;
3. regular product pages with repeated Description / Specification / Features / Downloads sections; and
4. downloadable product datasheets, inspection checklists, and instructions.

A verified collection JSON example is:

```text
https://neverletgo.com/collections/anchor-points?view=json
```

The response contains product title, `max_load`, internal product/variant IDs, canonical product URL, image URLs, price, availability, and other listing metadata.

A second verified JSON collection is:

```text
https://neverletgo.com/collections/tool-bags?view=json
```

which includes the MEWP Bag and its `max_load` and canonical URL.

### Tested products

#### 101372 — Bungee Tool Lanyard

Public first-party page exposes:

- 5 kg / 11 lb maximum load;
- 80–120 cm length range;
- 360° Rotobiner;
- two-stage/dual-action locking gate;
- climbing-cord loop;
- standards declarations; and
- datasheet/instruction links.

Main remaining gap for generic cross-brand interface reasoning:

- connector gate/internal geometry.

#### 101363 — 360 D Ring Loop Tool Tether

Public page and text-extractable PDF expose:

- 3 kg maximum load;
- 200 x 25 mm overall dimensions;
- loop/cinch attachment method;
- 360° D-ring;
- maximum lanyard length; and
- manufacturer evidence/documentation.

Main remaining gap:

- D-ring/interface geometry required for generic connector fit rules.

#### 101420 — Superlight Safety Tool Belt

Public page and catalogue JSON expose:

- 30 kg overall maximum load;
- multiple D-ring anchor points;
- triple-action buckle;
- 76–139 cm adjustment range;
- standards declarations; and
- downloadable documentation.

Remaining question:

- exact per-anchor capacity/geometry needed to use individual belt anchor points in generic cross-brand reasoning.

#### 101423 — MEWP Bag

Public page and catalogue JSON expose:

- 30 kg overall bag load;
- 5 kg internal anchor/daisy-chain load per point;
- integrated anchor points;
- dimensions;
- heavy-duty PVC construction;
- maximum lanyard length; and
- downloadable documentation.

Main remaining gap:

- interface geometry for generic connector engagement.

### Preliminary NLG assessment

```text
Discovery:             strong
Catalogue enumeration: strong
Static extraction:     strong
Document channel:      strong
Mandatory load data:   strong
Interface geometry:    recurring enrichment gap
Likely tier:           A + reusable measurement enrichment
```

NLG is the clearest initial candidate for a true brand-level adapter.

---

## 6.2 Hilti

### Observed acquisition pattern

Hilti exposes a different but also promising structure:

- structured product pages;
- structured category/list pages;
- configurators;
- related-product relationships;
- technical data sections;
- `productdata.hilti.com` assets; and
- downloadable guidance, declarations, instructions, and other technical documents.

Facts may be split across several manufacturer sources rather than appearing on one page.

### Important identity finding: regional SKUs

The same SF 4-22 technical product/family (`r13275669`) is represented with different sale-item codes in different Hilti regions.

Examples observed:

```text
USA listing:       #2253847
UK box listing:    #2253837
Singapore case:    #2253844
```

This is a schema warning: one `product.sku` field is unlikely to be sufficient for globally ingested products.

TetherLens will probably need to distinguish:

- canonical technical product/family identity; and
- one or more regional/catalogue identifiers or sale configurations.

### 2253847 — SF 4-22 cordless drill driver

The US page exposes model identity, battery platform, torque, speed, chuck range, configurator and related-product structure.

The UK first-party technical page exposes:

```text
tool body mass = 1.3 kg
```

Hilti battery pages expose, for example:

```text
B 22-55 = 0.55 kg
B 22-85 = 0.76 kg
```

Therefore operational mass is deterministically derivable for a selected battery configuration using manufacturer facts.

This is a good example of a Tier B join rather than missing data.

### 2261970 — Tool tether 15lbs double carabiner

Public Hilti page exposes:

- maximum load of approximately 6.8 kg;
- double-carabiner configuration;
- self-locking carabiner statement;
- ANSI compliance statement;
- related retaining strap; and
- downloadable Tethering Guidance and Declaration of Conformity.

Remaining tested gaps:

- tether length; and
- connector geometry.

### 2293133 — Retaining strap 15lb cordl.

Public page exposes:

- 6.8 kg / 15 lb product option;
- purpose as an accessory connecting compatible power tools to Hilti tool lanyards; and
- imagery showing an installed use case.

The exact complete compatible-tool set and interface limits were not exposed in the basic page content used in this exploratory run.

### Preliminary Hilti assessment

```text
Discovery:             strong
Catalogue enumeration: strong
Static extraction:     strong
Relationship data:     strong
Document channel:      strong
Mandatory data:        usually obtainable but join-heavy
Interface geometry:    recurring gap
Likely tier:           B
```

Hilti looks scalable through a **source-graph adapter** rather than a single-page scraper.

---

## 6.3 StopDrop

### Observed acquisition pattern

StopDrop's pages are straightforward to crawl but sparse.

This is an important distinction: the main problem is often not extraction technology but the amount of technical information actually published.

### SDKN1802 — Crimp tool for working at height

Manufacturer page establishes:

- tool identity/type; and
- a permanent StopDrop attachment point.

No manufacturer-published tool mass was surfaced in the tested page/search path.

Because manufacturer tool mass is mandatory for catalogued load reasoning, this product is currently blocked regardless of scraper sophistication.

### SDCOIL32 — Black Wire Coil Tool Lanyard

Page exposes:

- 1 m;
- 3 kg maximum load; and
- two locking screwgate carabiners.

Remaining gaps include connector geometry and richer material/interface detail.

### SDLANWIRE10 — Wire Tool Lanyard

Page exposes two product variants on one page:

```text
1.0 m -> 5 kg
1.5 m -> 8 kg
```

This produces a second schema warning: product-page identity and technical variant identity cannot always be treated as the same thing.

The ingestion model needs to preserve variant-dependent ratings rather than accepting one capacity onto the parent page identity.

### SDBAG2 — Waist and Shoulder Bag

Page plus manufacturer Bag Range Flyer PDF establish:

- product code SDBAG2;
- bag type;
- adjustable strap; and
- six internal D-ring attachment points.

The tested manufacturer material did not expose a rated bag load or per-interface load.

That is a source gap, not a parser failure.

### Preliminary StopDrop assessment

```text
Discovery:             moderate/strong
Static extraction:     easy
Document channel:      limited
Mandatory load data:   mixed
Interface geometry:    weak
Source completeness:   primary bottleneck
Likely tier:           C/D depending on product
```

StopDrop is valuable to the benchmark precisely because it tests whether TetherLens can distinguish **automation failure** from **underlying evidence absence**.

---

## 6.4 Milwaukee

### Observed acquisition pattern

The corrected canonical product is:

```text
2602-20 — M18 Cordless 1/2 in Hammer Drill/Driver (Tool Only)
```

The first-party page is crawlable for identity, descriptive content, battery-system statements and document links, but its key Specs section presents as:

```text
Specs
Loading
```

for a basic crawler.

The page links a directly downloadable operator manual and multiple parts/service documents.

The operator manual is text-extractable and provides model-specific operating specifications, but the tested manual does not publish tool or operational mass.

The tool page explicitly states compatibility with both Compact and XC M18 REDLITHIUM battery packs, so even if bare-tool weight is recovered, operational mass remains battery-configuration dependent.

### Preliminary Milwaukee assessment

```text
Discovery:             strong
Static shell:          strong
Key spec acquisition:  dynamic / unresolved
Document channel:      strong
Mandatory mass:        not established in tested first-party sources
Interface data:        not established
Likely tier:           C pending dynamic/API investigation
```

Milwaukee is therefore the correct benchmark case for testing whether a manufacturer-specific JS/API adapter can convert an apparent page failure into deterministic acquisition.

---

# 7. Preliminary quantitative baseline

For the first 12 products:

## Product discovery

All 12 canonical product identities were located from the supplied manufacturer/model context, although StopDrop demonstrates that exact part numbers are not always surfaced cleanly in indexed page text.

## Mandatory mass/capacity scalar

A manufacturer-backed mandatory mass/capacity value is directly available or deterministically derivable from first-party product/battery facts for approximately **9 of 12** products in this first source-surface pass.

The three currently blocked scalar cases are:

- StopDrop SDKN1802 tool mass;
- StopDrop SDBAG2 container rated capacity; and
- Milwaukee 2602-20 operational mass in the tested first-party acquisition path.

This number is a preliminary availability measure, not yet an automated extraction success rate.

## Interface completeness

Interface information is materially less complete than load data.

Even the best-documented manufacturers often omit dimensions needed for generic cross-brand connector engagement.

This remains the leading candidate for a structured internal-measurement programme.

## Machine-readable catalogue surfaces

NLG has a verified machine-readable collection JSON surface that can support catalogue discovery and initial facts.

Hilti has strong structured category/product/relationship surfaces, but this run has not yet established a public raw JSON endpoint as the preferred acquisition method.

StopDrop exposes simple static HTML but no comparable structured catalogue endpoint was identified in this run.

Milwaukee's key specs remain dynamically loaded to the basic crawler used for this audit.

---

# 8. Cross-cutting schema findings

The benchmark has already exposed three implementation issues that should be resolved before a large seed dataset is built.

## 8.1 Operational mass profiles

Cordless tools can have multiple valid battery configurations and therefore multiple operational masses.

The eventual schema should represent the mass used for reasoning as configuration-specific while ensuring it always includes the installed battery.

## 8.2 Multiple manufacturer identifiers

A technical product can have:

- global family ID;
- model;
- regional SKU/item code;
- sale configuration/pack code; and
- manufacturer internal product ID.

Hilti demonstrates that one `product.sku` is insufficient for robust international ingestion.

A likely future addition is a reusable `product_identifier` table rather than adding more identifier columns one by one.

## 8.3 Variant-dependent facts

One manufacturer page can represent multiple technical variants with different lengths and capacities.

StopDrop's Wire Tool Lanyard is the first explicit example.

TetherLens must not collapse variant-dependent ratings into a single accepted parent-product fact.

The implementation should determine whether variants become separate Product records or a first-class ProductVariant layer after a second manufacturer example is tested.

---

# 9. Reusable measurement hypothesis

The most common missing information so far is not load rating but interface geometry.

The benchmark should therefore measure both:

```text
percentage of products needing internal measurement
```

and, more importantly:

```text
number of unique reusable interface/connector specifications needing measurement
```

Example:

If the same NLG Rotobiner is reused across 25 products, one accepted internal connector measurement can potentially unlock generic compatibility reasoning for all 25.

The economically meaningful metric is therefore:

```text
products unlocked per measurement record
```

rather than simply `products requiring measurement`.

---

# 10. Adapter architecture to benchmark

Each manufacturer adapter should expose the same conceptual stages.

```text
discover(identity)
    -> CandidateProductIdentity[]

acquire(candidate)
    -> SourceArtifact[]

extract(source)
    -> CandidateClaim[]

normalize(candidate_claims)
    -> NormalizedCandidateClaim[]

validate(product, claims, evidence)
    -> ReadinessAssessment
```

## `discover`

Should use manufacturer-level listing/search/catalogue structure rather than general web search wherever possible.

## `acquire`

Should preserve source metadata and raw source artifacts for review/refresh comparison.

## `extract`

Should be deterministic where structure is reliable.

Document/LLM extraction should create **candidate** claims only.

## `normalize`

Should be shared across manufacturers where possible.

Manufacturer adapters should not each invent their own unit and vocabulary semantics.

## `validate`

Should apply the TetherLens evidence/readiness rules and report explicit missing facts.

---

# 11. First adapter prototypes

The initial adapters should be implemented in this order because they test different acquisition strategies.

## NLG adapter

Primary test:

```text
collection JSON discovery -> regular product HTML -> downloadable datasheet
```

Goal:

Prove high-throughput deterministic ingestion from an ingestion-friendly manufacturer.

## Hilti adapter

Primary test:

```text
product/category pages -> regional/canonical identity resolution -> related products -> technical pages/documents -> joined Claims
```

Goal:

Prove that multi-source manufacturer data can remain scalable without product-specific research.

## StopDrop adapter

Primary test:

```text
static HTML -> shared PDF where available -> explicit gap reporting
```

Goal:

Prove that the system distinguishes missing evidence from extraction failure and does not manufacture false completeness.

## Milwaukee adapter

Primary test:

```text
static shell -> dynamic spec/API investigation -> manufacturer documents -> battery configuration
```

Goal:

Determine whether dynamic manufacturer sites require expensive browser automation or expose a reusable underlying data endpoint.

---

# 12. Benchmark success criterion

The benchmark should ultimately answer a stricter question than whether Batch 1 can be populated:

> After a manufacturer adapter has been created from a small training set, can a second unseen set of that manufacturer's products be discovered, extracted, normalized and gap-assessed with little or no product-specific code or research?

The strongest outcome is:

```text
new product identity
    -> manufacturer adapter
    -> sources
    -> candidate facts
    -> normalization
    -> automatic gap assessment
    -> short human review
```

A weak outcome is:

```text
new product
    -> general web search
    -> bespoke LLM browsing
    -> manual interpretation
    -> custom fields/rules
    -> repeated human research
```

The second pattern may be workable for exceptional products but is not a viable catalogue operating model at scale.

---

# 13. Current conclusion

The first four manufacturers do **not** support a single universal scraper.

They do, however, provide early support for a more promising architecture:

> **manufacturer adapters + common normalization + explicit evidence validation + reusable physical measurement enrichment**

NLG suggests that a large product catalogue can sometimes be enumerated and partially populated from structured manufacturer surfaces.

Hilti suggests that multi-document and relationship-heavy manufacturer ecosystems can still be automated if the adapter treats manufacturer sources as a graph rather than a single page.

StopDrop shows that some products will remain incomplete because the source data itself is insufficient.

Milwaukee is the key unresolved technical test: whether dynamically loaded specs can be acquired through a reusable underlying endpoint rather than browser/LLM interaction.

The benchmark should therefore continue by implementing and running the four adapters, then testing them against unseen products from the same manufacturers before expanding Batch 1 to the remaining brands.
