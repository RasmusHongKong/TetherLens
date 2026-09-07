# Tether Endpoint Assignment Semantics

## Purpose

This document defines the bounded evidence-backed model used when a tether's individual connection points do not have accepted `tool_side`, `anchor_side`, or `either` roles, but accepted manufacturer evidence explicitly establishes that a pair of endpoints is reversible between the tool and anchor positions.

The model exists to preserve an important distinction:

```text
endpoint role evidence != endpoint-pair assignment evidence
```

Missing endpoint role evidence must not be rewritten as `either`, and physical symmetry must not be treated as proof of interchangeability.

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
- issuer manufacturer;
- evidence scope; and
- source URLs.

Its meaning is narrow:

> Accepted evidence establishes that the two named tether endpoints may occupy the tool-side and anchor-side positions in either orientation.

It is evidence about the relationship between two endpoint subjects, not an intrinsic `either` role claim about either endpoint.

## Evidence threshold

The declaration must come from accepted evidence that establishes reversibility, interchangeability, non-directionality, or an equivalently unambiguous assignment relationship.

The following are not sufficient by themselves:

- identical endpoint interface types;
- endpoints referencing the same `ConnectorSpec`;
- `dual`, `double`, or `twin` connector naming;
- connectors described as being at both ends;
- absence of wording that distinguishes the ends; or
- the fact that both connector forms could physically engage some target.

Those facts may identify a symmetric-looking product, but symmetry is not evidence of non-directional use.

Production extraction should therefore remain fail-closed until manufacturer wording clears the assignment-evidence threshold.

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

## Provenance and identity

Endpoint-assignment evidence is retained on generated candidate selections as `EndpointAssignmentProof` values containing:

- declaration ID;
- semantics;
- issuer manufacturer;
- evidence scope; and
- source URLs.

The declaration is also retained on the generated configuration only where it structurally authorizes the selected unknown/unknown pair.

Candidate identity remains physical. It continues to include the selected tool endpoint and anchor endpoint IDs, so the two orientations are distinct candidates. Evidence references are not added to the canonical candidate ID.

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

## V1 non-goals

V1 deliberately does not introduce:

- product-level `non_directional = true` booleans;
- automatic `UNKNOWN -> EITHER` promotion;
- inference from identical hardware or connector specifications;
- assignment rules for three-or-more endpoint sets or branched tethers;
- precedence rules that combine a reversible declaration with partially known endpoint roles;
- SKU-pair recommendation logic;
- connection-compatibility inference; or
- ranking/context preferences based on interchangeability.

Those should be added only when a concrete evidence-backed decision need requires them.

## Representative evidence boundary

Existing symmetric-looking catalogue cases remain useful regression examples rather than automatic positive declarations.

- NLG 101434 has two Quick Clip endpoints with no accepted individual role claims. Its physical symmetry does not itself establish interchangeability.
- Hilti 2261970 and representative Stopdrop double-carabiner topology likewise show that repeated/shared connector hardware is insufficient by itself.
- NLG 101756 demonstrates the opposite case: a product described as double-carabiner can still have accepted directional endpoint evidence, with one connector assigned to the anchor/belt side and another to tool attachment.

The production extractor should therefore be introduced only when first-party wording explicitly establishes the reversible assignment relationship for the concrete tether endpoint pair.
