import pytest

from tetherlens_ingest.adapters.hilti_tool_attachment import HiltiAdapter
from tetherlens_ingest.candidate_generation import CandidateComponentOption
from tetherlens_ingest.connection import ConnectionInterface, ConnectionInterfaceRole
from tetherlens_ingest.declared_compatibility import (
    ConnectorInterfaceCompatibilityDeclaration,
    connection_contexts_from_compatibility_declarations,
)
from tetherlens_ingest.models import (
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceType,
)
from tetherlens_ingest.tool_attachment_installation import (
    EvidenceBoundToolAttachmentAssemblyOption,
    ToolAttachmentInstallationBinding,
)


MANUAL_URL = "https://example.test/hilti-combined.pdf"
TOOL_URL = "https://example.test/hilti-sf4-22"


def _target(interface_id: str) -> ConnectionInterface:
    return ConnectionInterface(
        interface_id=interface_id,
        role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        interface_type="attachment_point",
    )


def _binding() -> ToolAttachmentInstallationBinding:
    return ToolAttachmentInstallationBinding(
        binding_id="binding:documented",
        tool_ref="Hilti:2253847",
        source_product_ref="Hilti:2293133",
        installation_feature_id="accessory_installation_openings",
        issuer_manufacturer="Hilti",
        scope="documented retaining strap installation",
        source_urls=[MANUAL_URL],
    )


def test_product_scoped_declaration_matches_only_interface_owned_by_declared_product():
    endpoint = ConnectionInterface(
        interface_id="tether:tool-end",
        role=ConnectionInterfaceRole.TETHER_CONNECTION,
        interface_type="carabiner",
        connector_spec_ref="tether_connector",
    )
    documented = _target("strap:attachment-point")
    unrelated = _target("other:attachment-point")
    declaration = ConnectorInterfaceCompatibilityDeclaration(
        declaration_id="hilti:tether-to-strap",
        connector_spec_ref="tether_connector",
        source_interface_type="carabiner",
        target_interface_type="attachment_point",
        target_role=ConnectionInterfaceRole.TOOL_ATTACHMENT_TETHER_SIDE,
        source_product_ref="Hilti:2261970",
        target_product_ref="Hilti:2293133",
        issuer_manufacturer="Hilti",
        scope="Hilti #2261970 carabiner to #2293133 retaining strap",
        source_urls=[MANUAL_URL],
    )

    contexts = connection_contexts_from_compatibility_declarations(
        tether_ref="Hilti:2261970",
        tether_product_ref="Hilti:2261970",
        endpoints=[endpoint],
        target_owner_ref="assembly:mixed",
        target_product_refs={"Hilti:2293133", "Other:component"},
        target_interface_product_refs={
            documented.interface_id: "Hilti:2293133",
            unrelated.interface_id: "Other:component",
        },
        target_interfaces=[documented, unrelated],
        declarations=[declaration],
    )

    assert len(contexts) == 1
    assert contexts[0].target_interface_id == documented.interface_id
    assert contexts[0].manufacturer_assessments[0].issuer_manufacturer == "Hilti"


def test_multi_product_evidence_assembly_requires_exact_interface_ownership():
    components = [
        CandidateComponentOption(
            component_ref="component:strap",
            source_product_ref="Hilti:2293133",
            rated_capacity_kg=6.8,
        ),
        CandidateComponentOption(
            component_ref="component:other",
            source_product_ref="Other:component",
            rated_capacity_kg=6.8,
        ),
    ]
    interfaces = [_target("strap:attachment-point"), _target("other:attachment-point")]

    with pytest.raises(ValueError, match="multi-product evidence-bound"):
        EvidenceBoundToolAttachmentAssemblyOption(
            assembly_ref="assembly:mixed",
            components=components,
            provided_interfaces=interfaces,
            installation_bindings=[_binding()],
        )

    assembly = EvidenceBoundToolAttachmentAssemblyOption(
        assembly_ref="assembly:mixed",
        components=components,
        provided_interfaces=interfaces,
        provided_interface_product_refs={
            "strap:attachment-point": "Hilti:2293133",
            "other:attachment-point": "Other:component",
        },
        installation_bindings=[_binding()],
    )
    assert assembly.provided_interface_product_refs["strap:attachment-point"] == "Hilti:2293133"


def _tool_identity() -> ProductIdentity:
    return ProductIdentity(
        manufacturer="Hilti",
        product_type=ProductType.TOOL,
        name="SF 4-22 Cordless drill driver",
        sku="2253847",
        url=TOOL_URL,
    )


def _primary() -> SourceArtifact:
    return SourceArtifact(
        url=TOOL_URL,
        source_type=SourceType.MANUFACTURER_WEBPAGE,
        content_type="text/html",
        body="<h1>SF 4-22 Cordless drill driver</h1><div>#2253847</div>",
    )


def _manual(body: str) -> SourceArtifact:
    return SourceArtifact(
        url=MANUAL_URL,
        source_type=SourceType.MANUFACTURER_DOCUMENT,
        content_type="application/pdf",
        body=body,
        metadata={"role": "operating_instruction"},
    )


def _drop_arrest_text(strap: str, tether: str) -> str:
    return (
        "Fall arrest. As drop arrester for this product, use only a combination of the Hilti "
        f"retaining strap #{strap} and the Hilti tool tether #{tether}. "
        "Secure the retaining strap to the installation openings for accessories. "
        "Secure one carabiner of the tool tether to the retaining strap and secure the "
        "second carabiner to a load-bearing structure."
    )


def test_combined_manual_uses_matching_model_section_not_first_fall_arrest_section():
    body = (
        "SF 6-22 (01). "
        + _drop_arrest_text("9999991", "9999992")
        + " SF 4-22 (02), SF 4H-22 (02). "
        + _drop_arrest_text("2293133", "2261970")
    )
    claims = HiltiAdapter().extract(_tool_identity(), [_primary(), _manual(body)])

    required_attachments = {
        str(claim.value)
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PRODUCT
        and claim.property_key == "tool.required_tool_attachment"
    }
    installation_identifiers = {
        str(claim.value)
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TOOL_ATTACHMENT_INSTALLATION_PATH
        and claim.property_key == "tool_attachment_installation.attachment_identifier"
    }
    assert required_attachments == {"2293133"}
    assert installation_identifiers == {"2293133"}


def test_document_level_model_mention_does_not_authorize_other_models_fall_arrest_section():
    body = (
        "This combined manual also includes SF 4-22 elsewhere in the document. "
        "SF 6-22 (01). "
        + _drop_arrest_text("9999991", "9999992")
    )
    claims = HiltiAdapter().extract(_tool_identity(), [_primary(), _manual(body)])

    executable_subjects = {
        claim.subject_type
        for claim in claims
        if claim.subject_type
        in {
            ClaimSubjectType.TOOL_ATTACHMENT_INSTALLATION_PATH,
            ClaimSubjectType.CONNECTION_COMPATIBILITY,
            ClaimSubjectType.PHYSICAL_INTERFACE,
        }
    }
    required_product_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.PRODUCT
        and claim.property_key in {"tool.required_tool_attachment", "tool.required_tether"}
    ]
    assert executable_subjects == set()
    assert required_product_claims == []
