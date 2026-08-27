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
_TOOL_RELATION_RE = re.compile(
    r"\b(?:tool\s+lanyards?|tool\s+tethers?|attach(?:ing|ed)?\s+tools?|"
    r"secur(?:e|ing|ed)\s+tools?)\b",
    re.I,
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
class _TopologyObservation:
    location: str | None
    count: int
    interface_type: str | None
    evidence: str


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

        # Replace the legacy aggregate ``internal_anchor`` rating emitted by the base
        # adapter. A rating must remain bound to the repeated physical interfaces that
        # the same evidence establishes rather than one overloaded synthetic subject.
        claims = [
            claim
            for claim in claims
            if not (
                claim.subject_type == ClaimSubjectType.PHYSICAL_INTERFACE
                and claim.subject_ref == "internal_anchor"
                and claim.property_key == "rated_capacity_kg"
            )
        ]

        for artifact in artifacts:
            if "json" in artifact.content_type:
                continue
            claims.extend(_container_interface_claims(artifact.body, artifact.url, self.extractor))

        return _dedupe_claims(claims)


def _container_interface_claims(
    html: str,
    source_url: str,
    extractor: str,
) -> list[CandidateClaim]:
    clauses = _rendered_clauses(html)
    observations: list[_TopologyObservation] = []

    for clause in clauses:
        if split := _SPLIT_COUNT_RE.search(clause):
            total = int(split.group("total"))
            external = int(split.group("external"))
            internal = int(split.group("internal"))
            if external + internal == total:
                evidence = split.group(0)
                observations.extend(
                    [
                        _TopologyObservation("external", external, None, evidence),
                        _TopologyObservation("internal", internal, None, evidence),
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
                )
            )

    topology = _resolve_topology(observations)
    rating = _per_interface_rating(clauses)
    claims: list[CandidateClaim] = []

    for location, resolved in topology.items():
        count, interface_type, count_evidence, type_evidence = resolved
        ref_prefix = f"{location}_anchor" if location else "anchor"
        for index in range(1, count + 1):
            subject_ref = f"{ref_prefix}_{index}"
            claims.append(
                _claim(
                    subject_ref,
                    "interface.role",
                    "container_connection",
                    count_evidence,
                    source_url,
                    extractor,
                )
            )
            if location is not None:
                claims.append(
                    _claim(
                        subject_ref,
                        "interface.location_description",
                        location,
                        count_evidence,
                        source_url,
                        extractor,
                    )
                )
            if interface_type is not None:
                claims.append(
                    _claim(
                        subject_ref,
                        "interface.type",
                        interface_type,
                        type_evidence or count_evidence,
                        source_url,
                        extractor,
                    )
                )
            if rating is not None:
                rating_value, rating_raw = rating
                claims.append(
                    _claim(
                        subject_ref,
                        "rated_capacity_kg",
                        rating_value,
                        rating_raw,
                        source_url,
                        extractor,
                        unit="kg",
                    )
                )

    return claims


def _resolve_topology(
    observations: list[_TopologyObservation],
) -> dict[str | None, tuple[int, str | None, str, str | None]]:
    """Resolve repeated counts without manufacturing certainty across conflicts."""

    by_location: dict[str, list[_TopologyObservation]] = defaultdict(list)
    unlocated: list[_TopologyObservation] = []
    for observation in observations:
        if observation.location is None:
            unlocated.append(observation)
        else:
            by_location[observation.location].append(observation)

    resolved: dict[str | None, tuple[int, str | None, str, str | None]] = {}
    for location, items in by_location.items():
        counts = {item.count for item in items}
        if len(counts) != 1:
            continue
        count = next(iter(counts))
        types = {item.interface_type for item in items if item.interface_type is not None}
        interface_type = next(iter(types)) if len(types) == 1 else None
        count_evidence = next(item.evidence for item in items if item.count == count)
        type_evidence = next(
            (item.evidence for item in items if item.interface_type == interface_type),
            None,
        )
        resolved[location] = (count, interface_type, count_evidence, type_evidence)

    unmatched_unlocated: list[_TopologyObservation] = []
    for observation in unlocated:
        matching_locations = [
            location
            for location, (count, _type, _count_raw, _type_raw) in resolved.items()
            if count == observation.count
        ]
        if len(matching_locations) == 1:
            location = matching_locations[0]
            count, current_type, count_raw, type_raw = resolved[location]
            if current_type is None and observation.interface_type is not None:
                resolved[location] = (
                    count,
                    observation.interface_type,
                    count_raw,
                    observation.evidence,
                )
            elif (
                current_type is not None
                and observation.interface_type is not None
                and current_type != observation.interface_type
            ):
                resolved[location] = (count, None, count_raw, None)
        else:
            unmatched_unlocated.append(observation)

    if unmatched_unlocated:
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
                first = unmatched_unlocated[0]
                type_raw = next(
                    item.evidence
                    for item in unmatched_unlocated
                    if item.interface_type == interface_type
                )
                resolved[None] = (count, interface_type, first.evidence, type_raw)

    return resolved


def _is_tether_interface_assertion(clause: str, form: str, location: str | None) -> bool:
    """Separate tether-anchor function from storage, mounting and structural form."""

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


def _per_interface_rating(clauses: list[str]) -> tuple[float, str] | None:
    matches: list[tuple[float, str]] = []
    for clause in clauses:
        if match := _PER_INTERFACE_RATING_RE.search(clause):
            if quantity := parse_mass(match.group("mass")):
                matches.append((quantity.value, match.group(0)))

    values = {value for value, _raw in matches}
    if len(values) != 1:
        return None
    value = next(iter(values))
    raw = next(raw for candidate, raw in matches if candidate == value)
    return value, raw


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
