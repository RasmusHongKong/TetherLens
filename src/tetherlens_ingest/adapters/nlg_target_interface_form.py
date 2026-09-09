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
    """Preserve evidence-backed D-ring form on already-resolved target identities.

    The existing container topology layer can bind an unlocated counted D-ring form to
    one repeated interface set only when its count maps to exactly one resolved
    location. This final enrichment layer reuses that concrete subject binding rather
    than materializing another target set or inferring form from a product name.

    Only an existing ``container_connection`` subject whose own ``interface.type =
    ring`` claim carries explicit D-ring wording receives ``ring_form = d_ring``.
    Generic rings, unknown-form anchors and ambiguous repeated sets remain unchanged.
    """

    extractor = "nlg.v0.15"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.CONTAINER:
            return claims

        container_subjects = {
            claim.subject_ref
            for claim in claims
            if claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
            and claim.property_key == "interface.role"
            and claim.value == "container_connection"
        }

        form_claims: list[CandidateClaim] = []
        for claim in claims:
            if (
                claim.subject_type != ClaimSubjectType.PHYSICAL_INTERFACE
                or claim.subject_ref not in container_subjects
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
