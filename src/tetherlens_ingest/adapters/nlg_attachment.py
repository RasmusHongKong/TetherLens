from __future__ import annotations

import re

from tetherlens_ingest.models import ProductIdentity, ProductType, SourceArtifact

from .common import page_text
from .nlg import NLGAdapter as _BaseNLGAdapter


class NLGAdapter(_BaseNLGAdapter):
    """NLG adapter with normalized primitive ToolAttachment retention semantics."""

    def extract(self, identity: ProductIdentity, artifacts: list[SourceArtifact]):
        claims = super().extract(identity, artifacts)
        if identity.product_type != ProductType.TOOL_ATTACHMENT:
            return claims

        for artifact in artifacts:
            if "json" in artifact.content_type:
                continue
            text = page_text(artifact.body)
            method = attachment_method_code(text)
            if method and not any(
                claim.subject_ref == "self"
                and claim.property_key == "attachment_method_code"
                and claim.value == method
                for claim in claims
            ):
                claims.append(self._claim(
                    "attachment_method_code",
                    method,
                    None,
                    _attachment_method_evidence(text, method),
                    artifact.url,
                ))
        return claims


def attachment_method_code(text: str) -> str | None:
    """Return the primary primitive mechanism retaining a ToolAttachment on a tool.

    The vocabulary is intentionally mechanism-led. Tool geometry, companion
    products, substrate restrictions and application/cure requirements belong in
    separate claims rather than compound attachment-method values.
    """
    normalized = _without_negative_adhesive_phrases(text)

    # Adhesive bonding is intrinsic retention. Explicit negative wording such as
    # "adhesive-free" and "no adhesive" is removed before this check.
    if re.search(
        r"\b(?:3m\s+)?adhesive\b|\bself[-\s]?adhesive\b|\bpressure[-\s]?sensitive\s+adhesive\b",
        normalized,
        re.I,
    ):
        return "adhesive"

    # A rigid attachment captured by existing tool geometry is normalized to the
    # mechanism, not to application-specific labels such as grinder_bracket.
    if re.search(
        r"\b(?:bracket|attachment)\b.{0,140}\b(?:attach\w*|secure\w*|fit\w*)\b.{0,100}"
        r"\b(?:by|to|onto|around)\s+(?:the\s+)?(?:side\s+)?handle\b",
        text,
        re.I | re.S,
    ) or re.search(
        r"\b(?:attach\w*|secure\w*|fit\w*)\b.{0,80}\b(?:bracket|attachment)\b.{0,100}"
        r"\bhandle\b",
        text,
        re.I | re.S,
    ):
        return "mechanical_capture"

    # Through-feature is reserved for a loop/attachment passed through a captive
    # feature and then closed by an explicit closure, rather than simply cinched.
    if re.search(
        r"\b(?:pass|feed|thread)\w*\b.{0,100}\bthrough\b.{0,100}"
        r"\b(?:captive\s+)?(?:hole|handle|eye)\b.{0,140}"
        r"\b(?:threaded|screw|closure|close|fasten|secure)\w*\b",
        text,
        re.I | re.S,
    ):
        return "through_feature"

    # Cinching is a constricting loop/choke mechanism. It takes precedence over
    # secondary tape/wrap wording on products whose primary retention is a cinch.
    if re.search(
        r"\b(?:cinch|cinches|cinched|cinching|choke|chokes|choked|choking)\b.{0,100}"
        r"\b(?:around|onto|to)\b",
        text,
        re.I | re.S,
    ) or re.search(
        r"\b(?:around|onto)\b.{0,80}\b(?:captive\s+)?(?:handle|hole|feature)\b.{0,100}"
        r"\b(?:cinch|cinched|cinching|choke)\b",
        text,
        re.I | re.S,
    ):
        return "cinch"

    if re.search(
        r"\bwrap(?:s|ped|ping)?\b.{0,120}\b(?:around|round)\b",
        text,
        re.I | re.S,
    ):
        return "wrap"

    return None


def _without_negative_adhesive_phrases(text: str) -> str:
    return re.sub(
        r"\b(?:no|without)\s+adhesive\b|\badhesive[-\s]?(?:free|less)\b",
        " ",
        text,
        flags=re.I,
    )


def _attachment_method_evidence(text: str, method: str) -> str:
    if method == "adhesive":
        return _adhesive_evidence(text)

    patterns = {
        "mechanical_capture": r".{0,50}\b(?:bracket|attachment)\b.{0,150}\bhandle\b.{0,50}",
        "through_feature": r".{0,50}\b(?:pass|feed|thread)\w*\b.{0,180}\b(?:hole|handle|eye)\b.{0,80}",
        "cinch": r".{0,50}\b(?:cinch|cinched|cinching|choke)\b.{0,120}",
        "wrap": r".{0,50}\bwrap(?:s|ped|ping)?\b.{0,120}\b(?:around|round)\b.{0,50}",
    }
    match = re.search(patterns[method], text, re.I | re.S)
    if not match:
        return method
    return re.sub(r"\s+", " ", match.group(0)).strip()


def _adhesive_evidence(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    candidates: list[tuple[int, int, str]] = []
    for match in re.finditer(r"\b(?:3m\s+)?adhesive\b", collapsed, re.I):
        left = max(collapsed.rfind(".", 0, match.start()), collapsed.rfind("!", 0, match.start()), collapsed.rfind("?", 0, match.start()))
        right_positions = [
            position
            for position in (
                collapsed.find(".", match.end()),
                collapsed.find("!", match.end()),
                collapsed.find("?", match.end()),
            )
            if position != -1
        ]
        right = min(right_positions) if right_positions else min(len(collapsed), match.end() + 180)
        sentence = collapsed[left + 1:right + 1].strip()
        if not sentence:
            continue

        score = 0
        if re.search(r"\b3m\s+adhesive\b", sentence, re.I):
            score += 2
        if re.search(r"\b(?:use|uses|using|with|via|bond|bonds|bonding|attach|attaches|surface|technology|pad|permanent|permanently)\b", sentence, re.I):
            score += 3
        if re.search(r"\b(?:shipping|orders?|free shipping)\b", sentence, re.I):
            score -= 4
        # Prefer later contextual copy over an otherwise-equal title occurrence.
        candidates.append((score, match.start(), sentence))

    if not candidates:
        return "adhesive"
    _, _, best = max(candidates, key=lambda item: (item[0], item[1]))
    return best
