from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
    SourceRequest,
    SourceType,
)

from .common import page_text
from .nlg_connector_mechanism import _dedupe_claims
from .nlg_target_interface_form import NLGAdapter as BaseNLGAdapter


_EXTRACTOR = "nlg.v0.16"
_CARABINER_PAIR_REF = "endpoint_assignment:carabiner_equivalent_pair"
_ALLOWED_NLG_HOSTS = {"neverletgo.com", "www.neverletgo.com", "go.neverletgo.com"}
_GENERIC_CARABINER_DESCRIPTORS = {
    "the",
    "a",
    "an",
    "one",
    "first",
    "second",
    "other",
    "double",
    "dual",
    "twin",
    "double-action",
    "single-action",
    "triple-action",
    "locking",
    "lock",
    "auto-locking",
    "automatic",
    "manual",
    "sturdy",
    "integral",
}


class NLGAdapter(BaseNLGAdapter):
    """Add one decision-bound NLG datasheet evidence path for endpoint assignment.

    The source graph does not crawl NLG documents generally. It follows a first-party
    product datasheet only for a tether whose primary page already establishes a
    symmetric-looking dual/twin/double carabiner pair and does not establish an obvious
    directional split. The datasheet must then independently satisfy the bounded
    carabiner-equivalence conjunction before a reversible assignment relation is emitted.
    """

    extractor = _EXTRACTOR

    def related_sources(
        self,
        identity: ProductIdentity,
        source_artifact: SourceArtifact,
    ) -> list[SourceRequest]:
        requests = list(super().related_sources(identity, source_artifact))
        if identity.product_type != ProductType.TETHER:
            return requests
        if source_artifact.source_type != SourceType.MANUFACTURER_WEBPAGE:
            return requests

        text = page_text(source_artifact.body)
        search_text = f"{identity.name or ''}\n{text}"
        if not _looks_like_dual_carabiner_assignment_candidate(search_text):
            return requests
        if _has_obvious_directional_split(text):
            return requests

        datasheet_url = _first_party_datasheet_url(source_artifact)
        if datasheet_url is None:
            return requests

        requests.append(
            SourceRequest(
                url=datasheet_url,
                source_type=SourceType.MANUFACTURER_DOCUMENT,
                metadata={
                    "role": "product_datasheet",
                    "relationship_basis": "first_party_product_download",
                },
            )
        )
        return requests

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        effective_artifacts = artifacts
        if identity.product_type == ProductType.TETHER:
            # A decision-bound datasheet that fails final-host, content-type or product-
            # identity validation is rejected as evidence altogether. Do not let inherited
            # NLG layers consume ordinary safety-relevant facts from that document either.
            effective_artifacts = [
                artifact
                for artifact in artifacts
                if not _is_decision_bound_datasheet(artifact)
                or _identity_bound_first_party_datasheet(identity, artifact)
            ]

        claims = list(super().extract(identity, effective_artifacts))
        if identity.product_type != ProductType.TETHER:
            return claims

        for artifact in effective_artifacts:
            claims.extend(_carabiner_endpoint_assignment_claims(identity, artifact, claims))
        return _dedupe_claims(claims)


def _looks_like_dual_carabiner_assignment_candidate(text: str) -> bool:
    """Identify a narrow source-graph candidate without asserting reversibility."""

    pair = re.search(
        r"\b(?:dual|double|twin)(?![-\s]+action\b)\s+"
        r"(?:[\w™®-]+\s+){0,3}carabiners?\b",
        text,
        re.I,
    )
    if pair is None:
        return False

    # Distinct named connector families are strong evidence that the two ends are not
    # one anonymous same-construction pair. Do not fetch a datasheet to try to widen it.
    if re.search(r"\b(?:rotobiner|quick\s*clip|snap\s*hook|cord\s+loop)\b", text, re.I):
        return False
    return True


def _is_allowed_nlg_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").casefold()
    return host in _ALLOWED_NLG_HOSTS


def _first_party_datasheet_url(source_artifact: SourceArtifact) -> str | None:
    """Return one explicitly labelled first-party PDF datasheet link from the page."""

    soup = BeautifulSoup(source_artifact.body, "html.parser")
    for anchor in soup.find_all("a", href=True):
        label = " ".join(anchor.stripped_strings).strip().casefold()
        if "datasheet" not in label:
            continue

        url = urljoin(source_artifact.url, str(anchor["href"]))
        parsed = urlparse(url)
        if not _is_allowed_nlg_url(url):
            continue
        if not parsed.path.casefold().endswith(".pdf"):
            continue
        return url
    return None


def _is_decision_bound_datasheet(artifact: SourceArtifact) -> bool:
    """Identify only the purpose-scoped datasheet edge introduced by this adapter."""

    return (
        artifact.source_type == SourceType.MANUFACTURER_DOCUMENT
        and artifact.metadata.get("role") == "product_datasheet"
        and artifact.metadata.get("relationship_basis") == "first_party_product_download"
    )


def _identity_bound_first_party_datasheet(
    identity: ProductIdentity,
    artifact: SourceArtifact,
) -> bool:
    """Require the fetched artifact itself to remain first-party and product-bound."""

    if not _is_decision_bound_datasheet(artifact):
        return False
    if not _is_allowed_nlg_url(artifact.url):
        return False
    if artifact.content_type.casefold() != "application/pdf":
        return False

    sku = (identity.sku or "").strip()
    if not sku:
        return False

    text = re.sub(r"\s+", " ", page_text(artifact.body))
    escaped_sku = re.escape(sku)
    return bool(
        re.search(
            rf"\b(?:product\s*(?:code|id)|sku|item\s*(?:code|number))\b"
            rf".{{0,30}}(?<!\w){escaped_sku}(?!\w)",
            text,
            re.I,
        )
    )


def _carabiner_endpoint_assignment_claims(
    identity: ProductIdentity,
    artifact: SourceArtifact,
    claims: list[CandidateClaim],
) -> list[CandidateClaim]:
    """Derive a reversible pair only from one fully sufficient first-party artifact."""

    if not _identity_bound_first_party_datasheet(identity, artifact):
        return []

    endpoint_claims = [
        claim
        for claim in claims
        if claim.subject_type == ClaimSubjectType.TETHER_CONNECTION_POINT
    ]
    endpoint_refs = sorted(
        {
            claim.subject_ref
            for claim in endpoint_claims
            if claim.property_key == "connection_point.interface_type"
        }
    )
    if endpoint_refs != ["connection_point_1", "connection_point_2"]:
        return []
    if any(claim.property_key == "connection_point.role" for claim in endpoint_claims):
        return []

    interface_types = {
        claim.subject_ref: str(claim.value)
        for claim in endpoint_claims
        if claim.property_key == "connection_point.interface_type"
    }
    connector_refs = {
        claim.subject_ref: str(claim.value)
        for claim in endpoint_claims
        if claim.property_key == "connection_point.connector_spec_ref"
    }
    if interface_types != {
        "connection_point_1": "carabiner",
        "connection_point_2": "carabiner",
    }:
        return []
    if connector_refs != {
        "connection_point_1": "tether_connector",
        "connection_point_2": "tether_connector",
    }:
        return []

    text = page_text(artifact.body)
    equivalent_match = _affirmative_collective_double_action_pair(text)
    if equivalent_match is None:
        return []

    tool_anchor_use = _affirmative_assignment_tool_anchor_use(text)
    if tool_anchor_use is None:
        return []

    if _has_obvious_directional_split(text):
        return []
    if re.search(r"\b(?:rotobiner|quick\s*clip|snap\s*hook|cord\s+loop)\b", text, re.I):
        return []

    scope = (
        "Derived from first-party evidence of one collective double-action carabiner "
        "pair and undifferentiated tool-to-anchor tether use"
    )
    evidence_raw = f"{equivalent_match}; {tool_anchor_use}"
    values = [
        ("endpoint_assignment.member_ref", "connection_point_1"),
        ("endpoint_assignment.member_ref", "connection_point_2"),
        ("endpoint_assignment.semantics", "reversible_tool_anchor_pair"),
        ("endpoint_assignment.basis", "derived_endpoint_equivalence"),
        ("endpoint_assignment.issuer_manufacturer", "NLG"),
        ("endpoint_assignment.scope", scope),
    ]
    return [
        CandidateClaim(
            subject_type=ClaimSubjectType.TETHER_ENDPOINT_ASSIGNMENT,
            subject_ref=_CARABINER_PAIR_REF,
            property_key=key,
            value=value,
            raw_value=evidence_raw,
            source_url=artifact.url,
            evidence_method="derived_endpoint_equivalence",
            extractor=_EXTRACTOR,
            claim_type=ClaimType.DERIVED,
        )
        for key, value in values
    ]


def _affirmative_collective_double_action_pair(text: str) -> str | None:
    """Require affirmative, product-local shared construction on the plural pair."""

    pattern = re.compile(
        r"\b(?:dual|twin|two)\s+(?:[\w™®-]+\s+){0,3}"
        r"double[-\s]?action\s+carabiners?\b",
        re.I,
    )
    negated_prefix = re.compile(
        r"\b(?:no|not|never|neither|without|does\s+not|doesn't|do\s+not|don't|"
        r"is\s+not|isn't|are\s+not|aren't)\b[^.;:]{0,70}$",
        re.I,
    )
    negated_suffix = re.compile(
        r"^\s*(?:(?:is|are|was|were|has|have|had|does|do|did|can|could|may|might|"
        r"must|shall|should|will|would)\s+)?"
        r"(?:(?:expressly|explicitly|normally)\s+)?"
        r"(?:not(?!\s+only\b)|never|no\s+longer)\b",
        re.I,
    )
    comparative_context = re.compile(
        r"\b(?:unlike|whereas|compared\s+(?:to|with)|in\s+contrast\s+to)\b"
        r"|\b(?:another|other|previous|earlier|competitor(?:'s)?)\s+"
        r"(?:product|model|lanyard|tether)\b",
        re.I,
    )

    for fragment in _evidence_fragments(text):
        for match in pattern.finditer(fragment):
            prefix = fragment[max(0, match.start() - 100):match.start()]
            suffix = fragment[match.end():min(len(fragment), match.end() + 80)]
            context = fragment[
                max(0, match.start() - 120):min(len(fragment), match.end() + 120)
            ]
            if negated_prefix.search(prefix):
                continue
            if negated_suffix.search(suffix):
                continue
            if comparative_context.search(context):
                continue
            return match.group(0)
    return None


def _affirmative_assignment_tool_anchor_use(text: str) -> str | None:
    """Require an affirmative relation that actually binds the tool to the anchor."""

    patterns = (
        re.compile(
            r"\btools?\b\s+"
            r"(?:(?:is|are|was|were|can|could|may|might|must|shall|should|will|would)\s+)?"
            r"(?:(?:to\s+)?be\s+)?(?:connect\w*|attach\w*)\b"
            r".{0,30}\bto\b.{0,30}\banchor(?:\s+points?)?\b",
            re.I,
        ),
        re.compile(
            r"\b(?:connect\w*|attach\w*)\b\s+(?:the\s+|your\s+|a\s+|an\s+)?tools?\b"
            r".{0,30}\bto\b.{0,30}\banchor(?:\s+points?)?\b",
            re.I,
        ),
        re.compile(
            r"\battachment\b.{0,25}\bto\b.{0,20}"
            r"\b(?:the\s+|your\s+|a\s+|an\s+)?tools?\b"
            r".{0,20}\b(?:and|to)\b.{0,20}\banchor(?:\s+points?)?\b",
            re.I,
        ),
        re.compile(
            r"\bcarabiners?\b.{0,35}\b(?:connect\w*|attach\w*)\b"
            r".{0,30}\b(?:the\s+)?tool\b.{0,50}\band\b"
            r".{0,35}\bcarabiners?\b.{0,35}\b(?:connect\w*|attach\w*)\b"
            r".{0,30}\b(?:the\s+)?anchor(?:\s+point)?\b",
            re.I,
        ),
    )
    negated_prefix = re.compile(
        r"\b(?:no|not|never|do\s+not|don't|does\s+not|doesn't|must\s+not|"
        r"shall\s+not|should\s+not|cannot|can't|prohibit\w*|forbid\w*)\b"
        r"[^.;:]{0,60}$",
        re.I,
    )
    postposed_prohibition = re.compile(
        r"\b(?:is|are|was|were)\s+"
        r"(?:(?:strictly|expressly|explicitly)\s+)?"
        r"(?:not\s+(?:permitted|allowed|approved|authorized|recommended)"
        r"|prohibited|forbidden|disallowed)\b"
        r"|\b(?:must|shall|should|may)\s+not\s+be\s+"
        r"(?:used|made|performed|attempted|permitted|allowed)\b"
        r"|\b(?:prohibited|forbidden|disallowed)\b",
        re.I,
    )

    for fragment in _evidence_fragments(text):
        for pattern in patterns:
            for match in pattern.finditer(fragment):
                prefix = fragment[max(0, match.start() - 80):match.start()]
                if negated_prefix.search(prefix):
                    continue
                tail = fragment[match.end():]
                local_tail = re.split(r"[.;]", tail, maxsplit=1)[0]
                if postposed_prohibition.search(local_tail):
                    continue
                return match.group(0)
    return None


def _distinguished_carabiner_labels(clause: str) -> set[str]:
    """Return non-generic descriptors attached to singular carabiner mentions."""

    labels: set[str] = set()
    pattern = re.compile(
        r"\b(?P<label1>[\w-]+)(?:\s+(?P<label2>[\w-]+))?\s+carabiner\b",
        re.I,
    )
    for match in pattern.finditer(clause):
        words = [
            word.casefold()
            for word in (match.group("label1"), match.group("label2"))
            if word
        ]
        words = [word for word in words if word not in _GENERIC_CARABINER_DESCRIPTORS]
        if words:
            labels.add(" ".join(words))
    return labels


def _has_distinguished_carabiner_assignment(fragment: str) -> bool:
    """Detect two differently identified carabiners assigned to opposite roles."""

    tool_labels: set[str] = set()
    anchor_labels: set[str] = set()
    clauses = re.split(
        r"\s*(?:[.;:,]|\band\b|\bwhile\b|\bwhereas\b)\s*",
        fragment,
        flags=re.I,
    )
    for clause in clauses:
        labels = _distinguished_carabiner_labels(clause)
        if not labels:
            continue
        tool = bool(re.search(r"\btool\b", clause, re.I))
        anchor = bool(re.search(r"\banchor(?:\s+point)?\b", clause, re.I))
        if tool == anchor:
            continue
        if not re.search(r"\b(?:attach\w*|connect\w*|to|for|used\s+on)\b", clause, re.I):
            continue
        if tool:
            tool_labels.update(labels)
        else:
            anchor_labels.update(labels)

    return any(tool_label != anchor_label for tool_label in tool_labels for anchor_label in anchor_labels)


def _has_obvious_directional_split(text: str) -> bool:
    """Fail closed when first-party wording distinguishes endpoint identity or use."""

    endpoint_label = re.compile(
        r"\b(?:tool|anchor|belt|harness)[-\s]+(?:side|end)\b.{0,60}\bcarabiner\b"
        r"|\bcarabiner\b.{0,60}\b(?:tool|anchor|belt|harness)[-\s]+(?:side|end)\b",
        re.I,
    )
    one_other_pair = (
        re.compile(
            r"\b(?:one|first)\s+carabiner\b.{0,80}\b(?:to|for)\s+(?:the\s+)?tool\b"
            r".{0,140}\b(?:other|second)\s+carabiner\b.{0,80}"
            r"\b(?:to|for)\s+(?:the\s+)?anchor(?:\s+point)?\b",
            re.I,
        ),
        re.compile(
            r"\b(?:one|first)\s+carabiner\b.{0,80}\b(?:to|for)\s+(?:the\s+)?anchor(?:\s+point)?\b"
            r".{0,140}\b(?:other|second)\s+carabiner\b.{0,80}"
            r"\b(?:to|for)\s+(?:the\s+)?tool\b",
            re.I,
        ),
    )

    for fragment in _evidence_fragments(text):
        if endpoint_label.search(fragment):
            return True
        if any(pattern.search(fragment) for pattern in one_other_pair):
            return True
        if _has_distinguished_carabiner_assignment(fragment):
            return True

    # Preserve the established 101756-style mixed/directional construction veto.
    if re.search(
        r"integral\s+carabiner.{0,60}(?:belt|anchor).{0,100}"
        r"rotobiner.{0,60}tool\s+attachment",
        text,
        re.I | re.S,
    ):
        return True
    return False


def _evidence_fragments(text: str) -> list[str]:
    return [
        re.sub(r"\s+", " ", fragment).strip()
        for fragment in re.split(r"\n(?=\S)", text)
        if fragment.strip()
    ]
