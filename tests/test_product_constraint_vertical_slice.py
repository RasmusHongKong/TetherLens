from tetherlens_ingest.adapters import NLGAdapter
from tetherlens_ingest.compatibility import FeatureKind, ToolInterfaceFeature
from tetherlens_ingest.constraints import (
    ProductConstraintContext,
    ProductConstraintStatus,
    evaluate_product_constraints,
    resolve_product_constraints,
)
from tetherlens_ingest.models import (
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)


def test_nlg_adhesive_installation_claims_resolve_into_runtime_constraints():
    identity = ProductIdentity(
        manufacturer="NLG",
        product_type=ProductType.TOOL_ATTACHMENT,
        name="Mini Adhesive D Ring",
        sku="101481",
        url="https://example.test/nlg/101481",
    )
    artifact = SourceArtifact(
        url="https://example.test/nlg/101481-instructions.pdf",
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=(
            "Attach the D Ring to a flat surface on the tool. "
            "The surface must be clean and grease-free. "
            "Do not attach the tether point to a battery compartment door as it can come off the tool. "
            "Allow 24 hours for the adhesive to fully bond before use. "
            "Test the tether point before use. "
            "Max Lanyard Length: 1.5 m."
        ),
    )

    claims = NLGAdapter().extract(identity, [artifact])
    constraints = resolve_product_constraints(claims)

    assert {
        (constraint.constraint_key, str(constraint.value))
        for constraint in constraints
    } >= {
        ("installation_surface_profile", "flat"),
        ("required_surface_condition", "clean"),
        ("required_surface_condition", "grease_free"),
        ("prohibited_tool_part_type", "removable_cover_or_door"),
        ("minimum_bond_time_h", "24.0"),
        ("pre_use_attachment_test_required", "True"),
        ("max_lanyard_length_mm", "1500.0"),
    }

    installation_surface = ToolInterfaceFeature(
        feature_id="fixed_flat_housing",
        feature_kind=FeatureKind.SURFACE,
        attributes={
            "surface_profile": "flat",
            "surface_condition.clean": True,
            "surface_condition.grease_free": True,
            "part_type": "fixed_housing",
        },
    )
    evaluations = evaluate_product_constraints(
        constraints,
        ProductConstraintContext(
            installation_feature=installation_surface,
            tether_max_length_mm=1200.0,
        ),
    )

    hard_keys = {
        "installation_surface_profile",
        "required_surface_condition",
        "prohibited_tool_part_type",
        "max_lanyard_length_mm",
    }
    assert all(
        evaluation.status == ProductConstraintStatus.PASSED
        for evaluation in evaluations
        if evaluation.constraint_key in hard_keys
    )
    assert all(
        evaluation.status == ProductConstraintStatus.REQUIRES_ACTION
        for evaluation in evaluations
        if evaluation.constraint_key
        in {"minimum_bond_time_h", "pre_use_attachment_test_required"}
    )
