# Tether Endpoint Assignment Semantics

## Purpose

This document defines the bounded evidence-backed model used when a tether's individual connection points do not have accepted `tool_side`, `anchor_side`, or `either` roles, but accepted evidence establishes that a pair of endpoints may be assigned between the tool and anchor positions in either orientation.

The model exists to preserve two important distinctions:

```text
endpoint role evidence != endpoint-pair assignment evidence
manufacturer declaration != TetherLens evidence-derived assignment
```

Missing endpoint role evidence must not be rewritten as `either`, and physical symmetry must not be treated as proof of interchangeability by itself.

## Existing endpoint roles remain authoritative

`ConnectionInterface.tether_side` retains the existing values:

- `tool_side`
- `anchor_side`
- `either`
- `unknown`

Normal role-backed candidate generation remains unchanged:

```text
TOOL_SIDE / EITHER   -> may serve tool side
ANCHOR_SIDE / EITHER -> may serve anchor side
UNKNOWN              -> not assigned from endpoint role alone
```

A reversible endpoint-assignment declaration does not mutate these values. In particular, an endpoint whose accepted role is missing remains `TetherSide.UNKNOWN` through generation and connection evaluation.

## Reusable v1 relation

The first supported relation is:

```text
reversible_tool_anchor_pair
```

A resolved `TetherEndpointAssignmentDeclaration` contains:

- declaration identity;
- owning tether reference;
- exactly two distinct endpoint references;
- assignment semantics;
- assignment basis;
- issuer manufacturer;
- evidence scope; and
- source URLs.

Its meaning is narrow:

> Accepted evidence establishes that the two named tether endpoints may occupy the tool-side and anchor-side positions in either orientation.

It is evidence about the relationship between two endpoint subjects, not an intrinsic `either` role claim about either endpoint.

## Assignment basis

V1 distinguishes how the relation was established:

```text
manufacturer_declared
```

The manufacturer directly establishes reversibility, interchangeability, non-directionality, `either end` use, or an equivalently unambiguous assignment relationship.

```text
derived_endpoint_equivalence
```

TetherLens derives the same bounded relation from a conjunction of accepted first-party facts that establish endpoint-construction equivalence and undifferentiated tool-to-anchor pair use. The derived basis is retained explicitly; it must never be presented as though the manufacturer directly declared reversibility.

`EndpointAssignmentProof` retains the assignment basis alongside declaration ID, semantics, issuer, scope and source URLs so rehydration cannot silently change a derived inference into a manufacturer declaration.

## Evidence threshold

### Direct manufacturer declaration

A `manufacturer_declared` relation requires first-party wording that directly establishes reversibility, interchangeability, non-directionality, `either end` use, or an equivalent assignment fact.

### Derived endpoint equivalence

A `derived_endpoint_equivalence` relation is permitted only when all of the following are established:

1. the tether has exactly two terminal endpoints in the derived pair;
2. accepted first-party evidence affirmatively establishes the same named connector construction at both ends;
3. accepted first-party evidence establishes tool-to-anchor pair use without distinguishing those endpoints by assigned role;
4. neither endpoint has accepted `tool_side`, `anchor_side`, or `either` role evidence;
5. no accepted evidence establishes different connector construction, mechanism, specification, location-specific identity, or designated use between the two ends; and
6. the derivation is local to the concrete tether and retains the underlying evidence URL(s).

The positive evidence must come from the conjunction. Absence of contrary evidence is only a veto check; it is not itself positive proof.

The following remain insufficient by themselves:

- identical endpoint interface types;
- endpoints referencing the same normalized `ConnectorSpec`;
- `dual`, `double`, or `twin` connector naming;
- connectors described generically as being at both ends;
- one-connector-to-tool / one-connector-to-anchor pair-use wording;
- absence of wording that distinguishes the ends; or
- the fact that both connector forms could physically engage some target.

Those facts may identify a symmetric-looking product or support another part of the conjunction, but none alone establishes reversible assignment.

## Production derivations

### NLG Quick Clip pair

The first production rule is deliberately narrower than the general conceptual threshold.

For NLG Quick Clip tethers, ingestion may emit a `derived_endpoint_equivalence` / `reversible_tool_anchor_pair` relation only when the same local evidence set establishes:

- exactly two unresolved tether endpoints;
- both endpoints are `clip` interfaces bound to the normalized `quick_clip` connector spec;
- wording equivalent to `Quick Clip connectors at each/both end`, affirmatively establishing the same named connector construction at the two ends;
- affirmative tool-to-anchor tether use; and
- no endpoint-labelled, separately designated, or separately named connector evidence that would make the ends directional or undermine equivalence.

A prohibition such as `never attach tools to anchor points` cannot satisfy the pair-use requirement. Likewise, wording that separately designates two Quick Clips to opposite sides — for example a red clip to the tool and a blue clip to the anchor — is directional evidence and vetoes the derived relation even when the page also says that Quick Clip connectors are present at each end.

This rule is not SKU-specific. NLG 101434 is the first known positive catalogue case because its current first-party product wording establishes both tool-to-anchor use and `360° Quick Clip™ connectors at each end`.

The extractor intentionally does **not** derive assignment from `dual Quick Clips` plus tool/anchor pair-use wording alone.

### NLG collective double-action carabiner pair

PR #51 adds a second production evidence family without changing the reusable relation or candidate-generation semantics.

The source graph is deliberately decision-bound. It does **not** crawl NLG datasheets generally. A first-party product-page datasheet may be followed only when the primary product evidence already identifies a symmetric-looking dual/twin/double carabiner tether candidate and does not itself establish an obvious directional split or mixed named connector construction. The download must be an explicitly labelled `Datasheet` PDF on an NLG-owned host.

The datasheet may then emit the existing `derived_endpoint_equivalence` / `reversible_tool_anchor_pair` relation only when one first-party artifact itself establishes the full conjunction:

- exactly two unresolved tether endpoints;
- both endpoints remain concrete `carabiner` interfaces bound to the existing `tether_connector` connector-spec subject;
- a collective shared construction phrase equivalent to `dual/twin/two ... double-action carabiners`, rather than multiplicity wording alone;
- affirmative tool-to-anchor pair use without assigning one named carabiner to either side; and
- no endpoint labels, one/other or first/second side assignments, Rotobiner/Quick Clip/snap-hook/loop split, or other evidence that distinguishes the two ends.

The collective action construction is intentionally required. `dual carabiners`, `twin carabiners`, a shared `ConnectorSpec`, or generic pair-use wording remain insufficient separately or in weaker combinations. Product names may identify the source-graph candidate but cannot establish the assignment relation.

NLG 101519 is the first positive case. Its primary page identifies the Twin Carabiner product and a dual double-action carabiner pair, while the first-party datasheet states that the dual double-action carabiners provide attachment to the tool and anchor point. The resulting relation keeps `connection_point_1` and `connection_point_2` as concrete endpoint identities with `TetherSide.UNKNOWN`; it authorizes the two bounded orientations without rewriting either endpoint to `either`.

NLG 101756 remains a hard negative control. Its first-party evidence distinguishes an integral belt/anchor carabiner from the tool-side Rotobiner, so the directional/mixed-construction evidence prevents both decision-bound datasheet traversal for equivalence and any reversible assignment derivation.

This new evidence family remains assignment-only. It does not establish that either carabiner can engage a particular D-ring, ToolAttachment interface, anchor, container interface, handle or tool point. Those connections still require their ordinary independent compatibility basis.

## Candidate-generation semantics

Candidate generation first applies the ordinary endpoint roles.

A `reversible_tool_anchor_pair` declaration may add assignments only when:

1. the declaration belongs to the same `tether_ref` as the `TetherOption`;
2. both declared endpoint references exist on that tether;
3. the declaration covers exactly two distinct endpoints; and
4. both covered endpoints still have `TetherSide.UNKNOWN`.

When those conditions hold, generation may create:

```text
endpoint A -> tool side; endpoint B -> anchor side
endpoint B -> tool side; endpoint A -> anchor side
```

The underlying endpoint objects remain unchanged.

If either endpoint already has a fixed or otherwise known role, v1 does not use the reversible declaration to widen the pair. This prevents relation evidence from overriding stronger endpoint-specific evidence and leaves mixed known/unknown cases fail-closed.

## Selection significance and user-facing semantics

Endpoint direction is primarily a **configuration-validity constraint**, not a product-ranking attribute.

For product selection, the practical question is:

> Does at least one manufacturer-permitted endpoint assignment produce a viable tool-side connection and a viable anchor-side connection for this job?

A directional tether may therefore remain a perfectly suitable product when its permitted orientation works. Direction becomes selection-critical only when endpoint identity changes the result — for example because the two ends use different connector constructions, different mechanisms or geometry, different manufacturer-designated uses, or different compatibility with the selected tool and anchor interfaces.

A reversible relation does not make a tether better and must not improve its rank merely because both orientations are permitted. Its purpose is to prevent an otherwise valid symmetric product from being blocked simply because the catalogue does not assign arbitrary `tool_side` / `anchor_side` identities to equivalent ends.

Internally, the two reversible orientations remain distinct physical candidates long enough for endpoint-to-target compatibility, hard constraints, provenance and installation semantics to be evaluated correctly. They must not be collapsed before evaluation because endpoint-specific facts can make apparently similar orientations behave differently.

Downstream presentation should, however, avoid showing duplicate user-facing product recommendations solely because a genuinely reversible pair produced two equivalent internal orientations. When the selected product is reversible and both orientations are equivalent for the chosen configuration, TetherLens should present one product solution and communicate the appropriate installation meaning — effectively that either equivalent end may occupy the tool/anchor position — rather than presenting two competing product choices.

## Provenance and identity

Endpoint-assignment evidence is retained on generated candidate selections as `EndpointAssignmentProof` values containing:

- declaration ID;
- semantics;
- assignment basis;
- issuer manufacturer;
- evidence scope; and
- source URLs.

The declaration is also retained on the generated configuration only where it structurally authorizes the selected unknown/unknown pair.

Candidate identity remains physical. It continues to include the selected tool endpoint and anchor endpoint IDs, so the two orientations are distinct candidates. Evidence references and assignment basis are not added to the canonical candidate ID.

Multiple declarations proving the same orientation therefore remain multiple audit proofs for one physical candidate rather than multiplying candidate identity.

Because endpoint IDs are local and commonly repeat across tether products, declaration ownership is explicitly scoped by `tether_ref`. A declaration for one tether must never authorize endpoints on another tether merely because their local IDs match.

## Separation from compatibility

Endpoint assignment answers only:

> Which physical tether endpoint may occupy each side of the candidate path?

It does not answer:

> Can that endpoint safely engage the selected target interface?

After generation, the ordinary connection evaluator remains authoritative. A relation-backed orientation may still evaluate as:

- `compatible`;
- `incompatible`;
- `requires_verification`; or
- `unresolved`.

Assignment evidence therefore cannot create connector/interface compatibility, bypass geometry, create a runtime-verification family, or rescue an otherwise hard-blocked candidate.

Hard candidate viability remains owned by `CandidateEvaluation`, and ranking/context remain downstream of that hard decision.

## Catalogue recommendation vs pre-use verification

Endpoint assignment needed to generate/recommend a catalogue configuration must be justified from catalogue evidence before recommendation. TetherLens must not rely on the worker already possessing and inspecting a candidate tether in order to rescue missing catalogue assignment semantics.

A later pre-use workflow may verify installation or use conditions on a selected product, but that is separate from establishing the catalogue relation required to recommend the product in the first place.

## V1 non-goals

V1 deliberately does not introduce:

- product-level `non_directional = true` booleans;
- automatic `UNKNOWN -> EITHER` promotion;
- a blanket `dual/double/twin -> reversible` inference;
- derivation from a shared normalized `ConnectorSpec` alone;
- blanket derived-equivalence rules for generic dual carabiners outside a proven first-party evidence pattern;
- assignment rules for three-or-more endpoint sets or branched tethers;
- precedence rules that combine a reversible declaration with partially known endpoint roles;
- SKU-pair recommendation logic;
- connection-compatibility inference; or
- ranking/context preferences based on interchangeability.

Those should be added only when a concrete evidence-backed decision need requires them.

## Representative evidence findings

The first-party evidence review now establishes the following boundary:

- **NLG 101434 — positive production case.** Current first-party copy establishes `360° Quick Clip™ connectors at each end` and that the tether connects tools to anchor points. This clears the narrow Quick Clip derived-equivalence conjunction without claiming that NLG literally said `either end`.
- **NLG 101519 — positive production case through decision-bound datasheet evidence.** The product page identifies the symmetric-looking twin/dual double-action carabiner pair but does not itself supply the complete tool-to-anchor conjunction. The first-party datasheet supplies the missing pair-use evidence on the same collective double-action carabiner subject, allowing the existing derived relation to resolve without SKU-specific assignment logic.
- **Hilti 2261970 — remains unknown.** Double-carabiner topology and one/second-carabiner use wording do not independently establish that both ends are the same connector construction.
- **StopDrop SDCOIL32 — remains unknown.** `2 locking screwgate carabiner` establishes multiplicity and mechanism family, but the reviewed evidence does not establish the complete equivalence-plus-pair-use conjunction under a production evidence family.
- **NLG 101756 — strong negative control.** The product is marketed as double-carabiner but first-party evidence distinguishes an integral anchor/belt carabiner from a tool-side 360° Rotobiner. Explicit directional evidence wins and prevents any symmetry-derived widening.

The practical conclusion is not that symmetric-looking tethers are assumed directional. Their assignment remains unknown until either direct reversible wording or one of the bounded evidence-derived equivalence conjunctions establishes the relation.
