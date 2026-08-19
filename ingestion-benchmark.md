# TetherLens Ingestion Benchmark

## Status

Initial benchmark specification created 2026-08-14 and consolidated 2026-08-19 after the first Hilti, Milwaukee and manufacturer-document acquisition experiments.

This benchmark tests the main supply-side uncertainty in TetherLens:

> Can a manufacturer product identity be converted into recommendation-ready structured knowledge with sufficiently little product-specific human effort and acquisition cost to scale across manufacturer catalogues?

`benchmark-goals.md` defines the current success criteria and should be read alongside this document.

The important distinction is between **data availability**, **data accessibility**, and **recommendation readiness**. A product can be acquired successfully while still failing to provide the facts needed for a safe recommendation.

---

# 1. Batch 1 scope

Batch 1 covers four deliberately different manufacturer patterns:

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

Detailed product-level cases are stored in `ingestion-benchmark-batch1.csv`.

The primary Milwaukee development SKU is now:

```text
2607-20 — M18 1/2 in Hammer Drill/Driver
```

This replaces `2602-20` as the normal Milwaukee development case. `2602-20` is a legacy/discontinued-product hard case and should be retained for later evaluation rather than used to shape the baseline Milwaukee architecture.

---

# 2. Cordless-tool operational mass convention

For TetherLens load reasoning, a battery-powered tool must use its **operational mass**, including the installed battery.

The benchmark must therefore represent separately:

- tool-body mass;
- compatible battery configuration(s);
- battery mass; and
- derived operational mass profile(s).

Conceptually:

```text
tool-body mass + installed battery mass = operational mass profile
```

A cordless tool can have several valid operational mass profiles when several compatible batteries exist.

The benchmark must not silently choose an arbitrary battery or treat bare-tool mass as the final reasoning value.

---

# 3. Source-graph ingestion model

The Hilti work established the preferred architecture: treat product evidence as a graph rather than expecting one page to contain every required fact.

A typical cordless-tool graph is:

```text
tool identity
  -> related / recommended / kit battery relationship(s)
  -> tool-body mass
  -> battery mass
  -> derived operational mass profile(s)
```

Hilti often exposes these nodes and edges entirely within its first-party ecosystem.

Milwaukee should use the **same conceptual graph**, but the evidence may cross publisher boundaries. For example:

```text
Milwaukee tool identity
  -> Milwaukee kit / product relationship
  -> Milwaukee battery identity
  -> qualified exact-SKU distributor fact where first-party physical data is incomplete
  -> derived operational mass
```

Cross-source ingestion is therefore allowed when the property-specific evidence policy permits it. The fact source and evidence method must remain explicit in provenance.

The downstream product graph should look the same regardless of whether every operand came from one publisher.

---

# 4. Evidence qualification

Evidence requirements depend on the property being asserted.

Examples:

- manufacturer-rated tether capacity, restrictions and standards/compliance claims should normally require manufacturer evidence;
- tool-body or battery physical mass may be accepted from a reputable exact-SKU industrial distributor when manufacturer evidence is unavailable or incomplete;
- tool/battery compatibility should preferably come from manufacturer relationships, kit composition or explicit manufacturer compatibility data;
- interface geometry may require internal measurement if it is not publicly published.

A distributor fact must never be represented as manufacturer-stated evidence.

Exact model/SKU identity, raw evidence, source URL and derivation provenance must be retained.

Evidence priority applies only after the resolved source has been verified against the expected product identity. A manufacturer-domain request that resolves to a search/fallback/different-product page must not be treated as manufacturer evidence merely because the requested SKU appears in the URL or aggregate content; the same rule applies to exact-SKU secondary evidence.

Conflicting values should remain visible. Reconciliation should operate at the highest applicable verified evidence priority: conflicting values at that highest priority block the affected fact, while lower-priority disagreement remains retained for provenance without automatically blocking a decisively established higher-priority value.

---

# 5. Acquisition progression

The preferred ingestion order is progressive and cost-aware:

1. deterministic manufacturer catalogue/product sources;
2. manufacturer APIs, embedded state, related products, kit composition, regional pages and technical documents;
3. deterministic qualified secondary sources such as exact-SKU industrial distributor records where the property policy permits them;
4. evidence reconciliation and derived configuration profiles;
5. paid/general search, browser automation or manual research only for genuinely difficult unresolved cases.

Paid web search should **not** be the default acquisition path for ordinary products. It is a later fallback capability whose cost and success rate should be measured separately.

A secondary-source access failure should also not invalidate already successful manufacturer acquisition; fallback channels must fail independently.

---

# 6. Manufacturer patterns

## 6.1 NLG

NLG remains the most ingestion-friendly pattern in the first batch:

- regular product pages;
- useful collection/listing structure;
- downloadable product documents;
- strong load/capacity coverage; and
- recurring interface-geometry gaps that may be solved through reusable measurements.

Likely baseline acquisition tier: **A**.

## 6.2 Hilti

Hilti demonstrates a scalable **source-graph adapter**:

- structured product/category surfaces;
- regional/canonical identity issues;
- related-product relationships;
- technical pages and documents; and
- first-party battery relationships and physical facts that can be joined into operational profiles.

The SF 4-22 case is the reference pattern for cordless-tool graph ingestion.

The `2293133` pass refined the original document-join assumption. Its rated capacity is now available directly on the current manufacturer product page, so a document join is not required for that scalar fact. The remaining distinct Hilti gap is **explicit drop-arrest relationship evidence**: current Hilti online operating instructions can name the required retaining strap and tether, but the deterministic US Technical Library path can return an operating-instruction PDF revision whose extractable evidence does not expose those exact component SKUs.

The adapter now treats manufacturer Technical Library results and operating-instruction PDFs as graph nodes, with model/SKU identity gates and PDF text extraction. Live acquisition therefore proves the document-join path itself; exact relationship claims remain revision-gated and must not be inferred when the acquired document does not state the SKU explicitly.

Likely baseline acquisition tier: **B**.

## 6.3 StopDrop

StopDrop demonstrates that simple acquisition does not guarantee complete evidence:

- static pages are easy to crawl;
- technical detail is often sparse;
- some required capacities or masses are not published; and
- the benchmark must distinguish source incompleteness from parser failure.

Likely baseline acquisition tier: **C/D depending on product**.

## 6.4 Milwaukee

Milwaukee is closer to Hilti than the first `2602-20` experiment suggested.

The primary development case is `2607-20`. The Milwaukee workstream has now validated the normal cross-source source-graph strategy end to end: manufacturer product and kit relationships establish tool/battery identity, while a qualified exact-SKU secondary product-detail source can supply permitted physical-mass facts when Milwaukee does not expose them directly.

The implemented strategy is:

```text
manufacturer product identity
  -> verified manufacturer kit / related-product / battery graph
  -> first-party physical facts where available
  -> qualified exact-SKU secondary facts where needed
  -> evidence reconciliation at highest verified priority
  -> operational mass profile
```

The implementation also verifies resolved manufacturer product-detail identity before assigning manufacturer evidence priority and verifies exact resolved secondary product-detail identity before accepting secondary mass evidence. Redirected search, fallback and different-product responses therefore do not inherit evidence priority from the original request.

The earlier `2602-20` case remains useful as a later test of sparse legacy-product handling, but it should not drive the normal Milwaukee adapter design.

Likely baseline acquisition tier: **B**, with selective cross-source enrichment.

---

# 7. Representative product selection

Development SKUs should represent the catalogue behavior TetherLens expects to encounter in normal operation.

The first development product for a manufacturer should normally be:

- current or actively supported;
- discoverable through the normal catalogue structure;
- representative of normal product relationships; and
- sufficiently documented to test the architecture without immediately forcing exceptional recovery methods.

Legacy, discontinued and unusually sparse products remain important, but should normally form a separate hard-case cohort after the baseline strategy is established.

This prevents one pathological first SKU from pushing unnecessary complexity into the normal ingestion design.

---

# 8. Benchmark questions

For every product, the benchmark should ask:

## Discovery

- Can the canonical product identity be found deterministically?
- Can the manufacturer catalogue be enumerated?
- Are stable product/model/variant identifiers available?

## Acquisition

- Which first-party pages, APIs, relationship surfaces and documents are available?
- Which qualified cross-source records are needed, if any?
- What is the acquisition cost of each channel?

## Extraction and normalization

- Can identity, physical facts, capacities, connector/interface properties and product relationships be extracted deterministically?
- Can values be normalized without SKU-specific rules?
- Are raw values and source provenance preserved?

## Recommendation readiness

- Are all recommendation-critical facts resolved?
- Which unresolved fields remain?
- Are derived facts supported by complete evidence chains?

---

# 9. Benchmark metrics

The benchmark should track both engineering health and product viability.

Useful metrics include:

- exact identity discovery rate;
- manufacturer catalogue enumeration rate;
- source requests per product;
- relationship extraction rate;
- mandatory fact coverage;
- operational-mass profile coverage;
- recommendation-readiness rate;
- secondary-source usage rate;
- paid-search/browser fallback rate;
- evidence conflicts;
- human review minutes;
- product-specific exception/code rate;
- acquisition cost per product; and
- acquisition cost per resolved critical fact.

Future evaluation should also separate:

- development SKUs;
- unseen same-manufacturer SKUs; and
- hard-case/legacy SKUs.

---

# 10. Adapter architecture to benchmark

Each manufacturer adapter should expose the same conceptual stages:

```text
discover(identity)
    -> CandidateProductIdentity[]

acquire(candidate)
    -> SourceArtifact[]

extract(source_graph)
    -> CandidateClaim[]

normalize(candidate_claims)
    -> NormalizedCandidateClaim[]

resolve_required_facts(product_graph)
    -> CandidateClaim[]

validate(product, claims, evidence)
    -> ReadinessAssessment
```

Manufacturer adapters should exploit manufacturer-specific structure, while normalization, evidence semantics and downstream graph representation should remain shared wherever possible.

Required-fact resolution should first traverse deterministic graph paths. General search is a later escalation, not the default implementation strategy.

---

# 11. Current conclusion

The first benchmark work does not support a single universal scraper.

It does support a common higher-level architecture:

> **manufacturer adapters + evidence-qualified product graphs + shared normalization + explicit provenance + reusable physical enrichment**

NLG demonstrates high-throughput structured acquisition.

Hilti demonstrates that multi-source first-party product graphs can be joined into useful operational configurations.

StopDrop demonstrates that some products remain incomplete because the source evidence itself is sparse.

Milwaukee demonstrates that the Hilti graph model can be reused even when selected physical facts cross into qualified secondary evidence, provided resolved source identity is verified before evidence priority is assigned.

The Milwaukee `2607-20` development path is now implemented and hardened enough to stop being the active benchmark workstream. The Hilti manufacturer-document pass has also established deterministic Technical Library discovery and PDF acquisition. The next distinct acquisition challenge is **current-revision operating-instruction selection** so explicit Hilti tool → retaining-strap/tether relationships can be captured without weakening evidence requirements.

See `benchmark-goals.md` for the benchmark success criteria and interpretation rules.