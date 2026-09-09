from __future__ import annotations

import re

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
)

from .nlg_anchor_interface_form import NLGAdapter as BaseNLGAdapter
from .nlg_connector_mechanism import _dedupe_claims


_D_RING_EVIDENCE = re.compile(r"\bd[\s-]?rings?\b", re.I)


class NLGAdapter(BaseNLGAdapter):
    """Preserve D-ring form on an already-established ToolAttachment target.

    ``nlg_interfaces`` creates the concrete ``tool_attachment_tether_side`` ring only
    when manufacturer evidence itself binds a D-ring to the provided tether point or
    lanyard connection. This final enrichment layer retains that narrower form on the
    same subject; it does not create an interface, infer form from a product name, or
    widen the interface's structural role.
    """

    extractor = "nlg.v0.15"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return claims

        tether_side_subjects = {
            claim.subject_ref
            for claim in claims
            if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
            and claim.property_key == "interface.role"
            and claim.value == "tool_attachment_tether_side"
        }

        form_claims: list[CandidateClaim] = []
        for claim in claims:
            if (
                claim.subject_type != ClaimSubjectType.PHYSICAL_INTERFACE
                or claim.subject_ref not in tether_side_subjects
                or claim.property_key != "interface.type"
                or claim.value != "ring"
                or claim.raw_value is None
                or _D_RING_EVIDENCE.search(claim.raw_value) is None
            ):
                continue

            form_claims.append(
                claim.model_copy(
                    update={
                        "property_key": "interface.attribute.ring_form",
                        "value": "d_ring",
                        "unit": None,
                        "extractor": self.extractor,
                    }
                )
            )

        return _dedupe_claims([*claims, *form_claims])
