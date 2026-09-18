import pytest

from tetherlens_ingest.models import CandidateClaim, ClaimSubjectType
from tetherlens_ingest.product_relationship import (
    DeclaredProductRelationshipType,
    resolve_declared_product_relationships,
)


def _claims(
    *,
    relationship_id: str = "kit:H01088:H01067",
    relationship_type: str = "kit_relationship",
    object_identifier: str = "H01067",
    quantities: tuple[int, ...] = (1,),
) -> list[CandidateClaim]:
    values = [
        ("declared_relationship.type", relationship_type),
        ("declared_relationship.object_product_identifier", object_identifier),
        ("declared_relationship.scope", "Manufacturer-published Kit Contents row"),
        *[("declared_relationship.quantity", quantity) for quantity in quantities],
    ]
    return [
        CandidateClaim(
            subject_type=ClaimSubjectType.DECLARED_RELATIONSHIP,
            subject_ref=relationship_id,
            property_key=key,
            value=value,
            raw_value="H01067 Webbing Wrist Tether Single-Action 1",
            source_url="https://manufacturer.test/kit",
            evidence_method="manufacturer_kit_composition",
            extractor="test",
        )
        for key, value in values
    ]


def test_declared_product_relationship_requires_explicit_catalogue_identity_mapping() -> None:
    claims = _claims()

    assert resolve_declared_product_relationships(
        claims,
        subject_product_ref="GRIPPS:H01088",
        product_refs_by_identifier={},
    ) == []

    resolved = resolve_declared_product_relationships(
        claims,
        subject_product_ref="GRIPPS:H01088",
        product_refs_by_identifier={"H01067": "GRIPPS:H01067"},
    )

    assert len(resolved) == 1
    relationship = resolved[0]
    assert relationship.relationship_id == "kit:H01088:H01067"
    assert relationship.subject_product_ref == "GRIPPS:H01088"
    assert relationship.object_product_identifier == "H01067"
    assert relationship.object_product_ref == "GRIPPS:H01067"
    assert relationship.relationship_type == DeclaredProductRelationshipType.KIT_RELATIONSHIP
    assert relationship.quantity == 1
    assert relationship.source_urls == ["https://manufacturer.test/kit"]


def test_explicit_endorsement_uses_same_identity_bound_relationship_model() -> None:
    resolved = resolve_declared_product_relationships(
        _claims(
            relationship_id="endorsed:H01085:H01067",
            relationship_type="explicitly_endorsed",
            quantities=(),
        ),
        subject_product_ref="GRIPPS:H01085-S",
        product_refs_by_identifier={"H01067": "GRIPPS:H01067"},
    )

    assert resolved[0].relationship_type == (
        DeclaredProductRelationshipType.EXPLICITLY_ENDORSED
    )
    assert resolved[0].object_product_ref == "GRIPPS:H01067"
    assert resolved[0].quantity is None


def test_declared_relationship_conflicting_quantity_fails_closed() -> None:
    with pytest.raises(ValueError, match="conflicting.*quantity"):
        resolve_declared_product_relationships(
            _claims(quantities=(1, 2)),
            subject_product_ref="GRIPPS:H01088",
            product_refs_by_identifier={"H01067": "GRIPPS:H01067"},
        )


def test_declared_relationship_does_not_accept_unknown_relationship_type() -> None:
    with pytest.raises(ValueError, match="unsupported declared relationship type"):
        resolve_declared_product_relationships(
            _claims(relationship_type="looks_compatible"),
            subject_product_ref="GRIPPS:H01088",
            product_refs_by_identifier={"H01067": "GRIPPS:H01067"},
        )



def test_kit_relationship_requires_source_backed_quantity() -> None:
    with pytest.raises(ValueError, match="missing.*declared_relationship.quantity"):
        resolve_declared_product_relationships(
            _claims(quantities=()),
            subject_product_ref="GRIPPS:H01088",
            product_refs_by_identifier={"H01067": "GRIPPS:H01067"},
        )
