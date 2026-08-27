from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    CandidateClaim,
    ClaimSubjectType,
    ClaimType,
    ProductIdentity,
    ProductType,
    SourceArtifact,
)
from tetherlens_ingest.normalize import parse_mass

from .nlg_interfaces import NLGAdapter as BaseNLGAdapter


_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}

_INTERFACE_COUNT = r"(?P<count>\d+|an?|one)\s*x?"
_LOCATION = r"(?:(?P<location>internal|external)\s+)?"
_MODIFIER = r"(?:(?:load[-\s]?rated|integrated)\s+){0,2}"
_FORM = r"(?P<form>d[\s-]?rings?|anchor\s+points?|daisy\s+chain(?:\s+loops?)?)"
_COUNTED_INTERFACE_RE = re.compile(
    rf"\b{_INTERFACE_COUNT}\s*{_LOCATION}{_MODIFIER}{_FORM}\b",
    re.I,
)
_SPLIT_COUNT_RE = re.compile(
    r"\b(?P<total>\d+)\s+(?:load[-\s]?rated\s+)?anchor\s+points?\b"
    r".{0,40}?\b(?P<external>\d+)\s+external\s*,\s*(?P<internal>\d+)\s+internal\b",
    re.I | re.S,
)
_TOOL_RELATION_PATTERN = (
    r"(?:tool\s+lanyards?|tool\s+tethers?|attach(?:ing|ed)?\s+tools?|"
    r"secur(?:e|ing|ed)\s+tools?)"
)
_TOOL_RELATION_RE = re.compile(rf"\b{_TOOL_RELATION_PATTERN}\b", re.I)
_PROHIBITION_BEFORE_TOOL_RE = re.compile(
    rf"(?:"
    rf"\b(?:must|shall|should|may|can)\s+not\b|"
    rf"\bcannot\b|"
    rf"\b(?:do|does|did)\s+not\b|"
    rf"\bnever\b|"
    rf"\bnot\s+(?:to|for|used|intended|designed|suitable)\b"
    rf").{{0,80}}\b{_TOOL_RELATION_PATTERN}\b",
    re.I | re.S,
)
_PROHIBITION_AFTER_TOOL_RE = re.compile(
    rf"\b{_TOOL_RELATION_PATTERN}\b.{{0,80}}\b"
    rf"(?:(?:is|are|was|were)\s+)?"
    rf"(?:prohibited|forbidden|not\s+(?:permitted|allowed))\b",
    re.I | re.S,
)
_MOUNTING_RELATION_RE = re.compile(
    r"\b(?:mount(?:ed|ing)?|fit(?:ted|ting)?|attach(?:ed|ing)?)\b.{0,40}"
    r"\b(?:belt|harness|handrail|rail|braces?)\b",
    re.I | re.S,
)
_PER_INTERFACE_RATING_RE = re.compile(
    r"(?:internal\s+anchor\s+points?\s*/\s*daisy\s+chain|"
    r"internal\s+load[-\s]?rated\s+anchor\s+points?)"
    r".{0,60}?max\s+load\s*:?\s*"
    r"(?P<mass>\d+(?:\.\d+)?\s*(?:kg|lbs?))"
    r".{0,30}?\beach\b",
    re.I | re.S,
)


@dataclass(frozen=True)
class _SourceClause:
    text: str
    source_url: str


@dataclass(frozen=True)
class _TopologyObservation:
    location: str | None
    count: int
    interface_type: str | None
    evidence: str
    source_url: str


@dataclass(frozen=True)
class _ResolvedTopology:
    count: int
    interface_type: str | None
    count_observation: _TopologyObservation
    type_observation: _TopologyObservation | None


@dataclass(frozen=True)
class _RatingObservation:
    value_kg: float
    evidence: str
    source_url: str


class NLGAdapter(BaseNLGAdapter):
    """Add repeated, evidence-bound container tether interfaces.

    A container feature becomes ``container_connection`` only when manufacturer copy
    establishes an anchor/tool-lanyard function. Physical form is a separate fact and
    remains unknown when the source says only ``anchor point``. Storage/tool holders,
    bag-mounting hardware, lifting handles, rope-management loops and structural rings
    are not promoted to tether interfaces merely because they are rings, loops or rated.
    """

    extractor = "nlg.v0.11"

    def extract(
        self,
        identity: ProductIdentity,
        artifacts: list[SourceArtifact],
    ) -> list[CandidateClaim]:
        claims = list(super().extract(identity, artifacts))
        if identity.product_type != ProductType.CONTAINER:
            return claims

        topology_claims = _container_interface_claims(artifacts, self.extractor)

        # Replace the legacy aggregate ``internal_anchor`` rating only when this layer
        # actually established repeated connection topology. Other container products
        # may still rely on the older interface-scoped rating until their public copy
        # establishes a reusable count/topology path; dropping that fact globally would
        # regress unrelated benchmark products.
        if any(
            claim.property_key == "interface.role"
            and claim.value == "container_connection"
            for claim in topology_claims
        ):
            claims = [
                claim
                for claim in claims
                if not (
                    claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
                    and claim.subject_ref == "internal_anchor"
                    and claim.property_key == "rated_capacity_kg"
                )
            ]

        claims.extend(topology_claims)
        return _dedupe_claims(claims)


def _container_interface_claims(
    artifacts: list[SourceArtifact],
    extractor: str,
) -> list[CandidateClaim]:
    clauses: list[_SourceClause] = []
    observations: list[_TopologyObservation] = []

    # Resolve one evidence set across all source artifacts. Counts that conflict across
    # a product page, datasheet or instruction source must be visible to the same
    # resolver rather than independently materializing and then being unioned.
    for artifact in artifacts:
        if "json" in artifact.content_type:
            continue
        artifact_clauses = [
            _SourceClause(text=clause, source_url=artifact.url)
            for clause in _rendered_clauses(artifact.body)
        ]
        clauses.extend(artifact_clauses)
        observations.extend(_topology_observations(artifact_clauses))

    topology = _resolve_topology(observations)
    rating = _per_interface_rating(clauses)
    claims: list[CandidateClaim] = []

    for location, resolved in topology.items():
        ref_prefix = f"{location}_anchor" if location else "anchor"
        count_observation = resolved.count_observation
        type_observation = resolved.type_observation

        for index in range(1, resolved.count + 1):
            subject_ref = f"{ref_prefix}_{index}"
            claims.append(
                _claim(
                    subject_ref,
                    "interface.role",
                    "container_connection",
                    count_observation.evidence,
                    count_observation.source_url,
                    extractor,
                )
            )
            if location is not None:
                claims.append(
                    _claim(
                        subject_ref,
                        "interface.location_description",
                        location,
                        count_observation.evidence,
                        count_observation.source_url,
                        extractor,
                    )
                )
            if resolved.interface_type is not None and type_observation is not None:
                claims.append(
                    _claim(
                        subject_ref,
                        "interface.type",
                        resolved.interface_type,
                        type_observation.evidence,
                        type_observation.source_url,
                        extractor,
                    )
                )
            if rating is not None:
                claims.append(
                    _claim(
                        subject_ref,
                        "rated_capacity_kg",
                        rating.value_kg,
                        rating.evidence,
                        rating.source_url,
                        extractor,
                        unit="kg",
                    )
                )

    return claims


def _topology_observations(
    clauses: list[_SourceClause],
) -> list[_TopologyObservation]:
    observations: list[_TopologyObservation] = []

    for source_clause in clauses:
        clause = source_clause.text
        if split := _SPLIT_COUNT_RE.search(clause):
            total = int(split.group("total"))
            external = int(split.group("external"))
            internal = int(split.group("internal"))
            if external + internal == total:
                evidence = split.group(0)
                observations.extend(
                    [
                        _TopologyObservation(
                            "external",
                            external,
                            None,
                            evidence,
                            source_clause.source_url,
                        ),
                        _TopologyObservation(
                            "internal",
                            internal,
                            None,
                            evidence,
                            source_clause.source_url,
                        ),
                    ]
                )

        for match in _COUNTED_INTERFACE_RE.finditer(clause):
            form = match.group("form").casefold()
            count = _count_value(match.group("count"))
            location = match.group("location")
            if location is None and re.search(r"\binternally\b", clause, re.I):
                location = "internal"

            interface_type = _interface_type(form)
            if not _is_tether_interface_assertion(clause, form, location):
                continue

            # An unlocated generic ``anchor point`` observation cannot refine form and
            # would duplicate stronger location/count evidence elsewhere on the page.
            if location is None and interface_type is None:
                continue

            observations.append(
                _TopologyObservation(
                    location=location.casefold() if location else None,
                    count=count,
                    interface_type=interface_type,
                    evidence=match.group(0),
                    source_url=source_clause.source_url,
                )
            )

    return observations


def _resolve_topology(
    observations: list[_TopologyObservation],
) -> dict[str | None, _ResolvedTopology]:
    """Resolve repeated counts without manufacturing certainty across conflicts."""

    by_location: dict[str, list[_TopologyObservation]] = defaultdict(list)
    unlocated: list[_TopologyObservation] = []
    for observation in observations:
        if observation.location is None:
            unlocated.append(observation)
        else:
            by_location[observation.location].append(observation)

    resolved: dict[str | None, _ResolvedTopology] = {}
    for location, items in by_location.items():
        counts = {item.count for item in items}
        if len(counts) != 1:
            continue

        count = next(iter(counts))
        types = {item.interface_type for item in items if item.interface_type is not None}
        interface_type = next(iter(types)) if len(types) == 1 else None
        count_observation = next(item for item in items if item.count == count)
        type_observation = next(
            (item for item in items if item.interface_type == interface_type),
            None,
        )
        resolved[location] = _ResolvedTopology(
            count=count,
            interface_type=interface_type,
            count_observation=count_observation,
            type_observation=type_observation,
        )

    unmatched_unlocated: list[_TopologyObservation] = []
    for observation in unlocated:
        matching_locations = [
            location
            for location, item in resolved.items()
            if item.count == observation.count
        ]
        if len(matching_locations) == 1:
            location = matching_locations[0]
            current = resolved[location]
            if current.interface_type is None and observation.interface_type is not None:
                resolved[location] = _ResolvedTopology(
                    count=current.count,
                    interface_type=observation.interface_type,
                    count_observation=current.count_observation,
                    type_observation=observation,
                )
            elif (
                current.interface_type is not None
                and observation.interface_type is not None
                and current.interface_type != observation.interface_type
            ):
                resolved[location] = _ResolvedTopology(
                    count=current.count,
                    interface_type=None,
                    count_observation=current.count_observation,
                    type_observation=None,
                )
        elif not matching_locations:
            unmatched_unlocated.append(observation)
        # More than one matching location means the form evidence is ambiguous. It may
        # not be rebound as an additional topology group because that would manufacture
        # extra physical interfaces beyond the stated count.

    # Unlocated observations may establish topology only when there is no located
    # topology evidence anywhere in the evidence set. Once a source establishes a
    # location, a differently counted unlocated observation is an unbindable refinement,
    # not permission to materialize an additional anonymous interface group.
    if unmatched_unlocated and not by_location:
        counts = {item.count for item in unmatched_unlocated}
        if len(counts) == 1:
            count = next(iter(counts))
            types = {
                item.interface_type
                for item in unmatched_unlocated
                if item.interface_type is not None
            }
            interface_type = next(iter(types)) if len(types) == 1 else None
            if interface_type is not None:
                count_observation = unmatched_unlocated[0]
                type_observation = next(
                    item
                    for item in unmatched_unlocated
                    if item.interface_type == interface_type
                )
                resolved[None] = _ResolvedTopology(
                    count=count,
                    interface_type=interface_type,
                    count_observation=count_observation,
                    type_observation=type_observation,
                )

    return resolved


def _is_tether_interface_assertion(clause: str, form: str, location: str | None) -> bool:
    """Separate tether-anchor function from storage, mounting and structural form."""

    # A prohibition must win over every weaker positive signal such as ``load-rated``
    # or an internal location. Manufacturer copy can place the prohibition before or
    # after the tool-use relation, so both clause-local directions fail closed.
    if _PROHIBITION_BEFORE_TOOL_RE.search(clause) or _PROHIBITION_AFTER_TOOL_RE.search(clause):
        return False

    if _MOUNTING_RELATION_RE.search(clause) and not _TOOL_RELATION_RE.search(clause):
        return False

    if "anchor" in form:
        return bool(
            _TOOL_RELATION_RE.search(clause)
            or re.search(r"load[-\s]?rated", clause, re.I)
            or (location == "internal" and re.search(r"\binternal\b|\binternally\b", clause, re.I))
        )

    if "daisy" in form:
        return bool(
            re.search(r"load[-\s]?rated", clause, re.I)
            and re.search(r"\battach(?:ing|ed)?\s+(?:items|tools?)\b|\banchor\b", clause, re.I)
        )

    # A D-ring is only physical form. It becomes a tether interface when the same
    # clause binds it to tools/lanyards rather than to bag, belt, brace or rail mounting.
    return bool(_TOOL_RELATION_RE.search(clause))


def _interface_type(form: str) -> str | None:
    if re.search(r"d[\s-]?rings?", form, re.I):
        return "ring"
    if "daisy" in form:
        return "loop"
    return None


def _per_interface_rating(
    clauses: list[_SourceClause],
) -> _RatingObservation | None:
    matches: list[_RatingObservation] = []
    for source_clause in clauses:
        if match := _PER_INTERFACE_RATING_RE.search(source_clause.text):
            if quantity := parse_mass(match.group("mass")):
                matches.append(
                    _RatingObservation(
                        value_kg=quantity.value,
                        evidence=match.group(0),
                        source_url=source_clause.source_url,
                    )
                )

    values = {match.value_kg for match in matches}
    if len(values) != 1:
        return None
    value = next(iter(values))
    return next(match for match in matches if match.value_kg == value)


def _count_value(raw: str) -> int:
    normalized = raw.strip().casefold()
    if normalized in {"a", "an", "one"}:
        return 1
    return int(normalized)


def _claim(
    subject_ref: str,
    property_key: str,
    value: int | float | str | bool,
    raw_value: str,
    source_url: str,
    extractor: str,
    *,
    unit: str | None = None,
) -> CandidateClaim:
    return CandidateClaim(
        subject_type=ClaimSubjectType.PHYSICAL_INTERFACE,
        subject_ref=subject_ref,
        property_key=property_key,
        value=value,
        unit=unit,
        raw_value=raw_value,
        source_url=source_url,
        evidence_method="manufacturer_stated",
        extractor=extractor,
        claim_type=ClaimType.DIRECT,
    )


def _rendered_clauses(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.insert_before("\n")
        tag.insert_after("\n")

    text = soup.get_text("", strip=False).replace("\xa0", " ")
    text = re.sub(r"[\t\r\f\v ]+", " ", text)
    text = re.sub(r" *\n+ *", "\n", text)

    clauses: list[str] = []
    for block in text.split("\n"):
        block = block.strip()
        if not block:
            continue
        clauses.extend(
            clause.strip()
            for clause in re.split(r"(?<=[.!?;])\s+", block)
            if clause.strip()
        )
    return clauses


def _dedupe_claims(claims: list[CandidateClaim]) -> list[CandidateClaim]:
    out: list[CandidateClaim] = []
    seen: set[tuple[object, ...]] = set()
    for claim in claims:
        key = (
            claim.subject_type,
            claim.subject_ref,
            claim.property_key,
            claim.value,
            claim.unit,
            claim.source_url,
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(claim)
    return out
