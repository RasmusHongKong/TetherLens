from __future__ import annotations

import re


_ADHESIVE_TERM = r"(?:3m(?:®|™)?\s*)?(?:self[-\s]?|pressure[-\s]?sensitive\s+)?adhesive"


def attachment_method_code(text: str) -> str | None:
    """Return the primary primitive mechanism retaining a ToolAttachment on a tool.

    The vocabulary is intentionally mechanism-led. Tool geometry, companion
    products, substrate restrictions and application/cure requirements belong in
    separate claims rather than compound attachment-method values.
    """
    normalized = _without_negative_adhesive_phrases(text)

    # Adhesive bonding is only accepted when the local copy positively describes
    # adhesive as the retention mechanism. A bare product/navigation mention such
    # as "Adhesive D Ring" must not outrank the current product's own mechanism.
    if _adhesive_evidence(normalized):
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


def attachment_method_evidence(text: str, method: str) -> str:
    if method == "adhesive":
        return _adhesive_evidence(_without_negative_adhesive_phrases(text)) or "adhesive"

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


def _without_negative_adhesive_phrases(text: str) -> str:
    return re.sub(
        r"\b(?:no|without)\s+adhesive\b"
        r"|\bnon[-\s]?adhesive\b"
        r"|\badhesive[-\s]?(?:free|less)\b"
        r"|\bnot\s+(?:an?\s+)?adhesive\b"
        r"|\bdoes(?:\s+not|n['’]t)\s+(?:use|require)\s+adhesive\b",
        " ",
        text,
        flags=re.I,
    )


def _adhesive_evidence(text: str) -> str | None:
    collapsed = re.sub(r"\s+", " ", text).strip()
    candidates: list[tuple[int, int, str]] = []
    for match in re.finditer(rf"\b{_ADHESIVE_TERM}\b", collapsed, re.I):
        left = max(
            collapsed.rfind(".", 0, match.start()),
            collapsed.rfind("!", 0, match.start()),
            collapsed.rfind("?", 0, match.start()),
        )
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
        if not sentence or not _positive_adhesive_context(sentence, match.group(0)):
            continue

        score = 0
        if re.search(r"\b3m(?:®|™)?\s*adhesive\b", sentence, re.I):
            score += 2
        if re.search(
            r"\b(?:bond|bonds|bonding|adher\w*|attach\w*|secure\w*|retain\w*|surface|technology|pad|backing|tether\s+point)\b",
            sentence,
            re.I,
        ):
            score += 3
        if re.search(r"\b(?:shipping|orders?|free shipping|related products?)\b", sentence, re.I):
            score -= 4
        candidates.append((score, match.start(), sentence))

    if not candidates:
        return None
    _, _, best = max(candidates, key=lambda item: (item[0], item[1]))
    return best


def _positive_adhesive_context(sentence: str, matched_term: str) -> bool:
    # Product-name mentions such as "Adhesive D Ring" are not themselves
    # evidence that the current ToolAttachment is retained by adhesive.
    if re.search(r"\badhesive\s+d[\s-]?ring\b", matched_term, re.I):
        return False

    patterns = (
        rf"\b(?:this|the)\s+(?:attachment|d[\s-]?ring|product)\b.{{0,60}}\b(?:is|uses?|features?|has)\b.{{0,40}}\b{_ADHESIVE_TERM}\b",
        rf"\b(?:uses?|using|utilis(?:e|es|ed|ing)|utiliz(?:e|es|ed|ing)|appl(?:y|ies|ied|ying))\b.{{0,70}}\b{_ADHESIVE_TERM}\b.{{0,140}}\b(?:bond\w*|adher\w*|attach\w*|secure\w*|retain\w*|surface|tool|tether\s+point|technology|pad|backing)\b",
        rf"\b{_ADHESIVE_TERM}\b.{{0,140}}\b(?:bond\w*|adher\w*|attach\w*|secure\w*|retain\w*|create\w*|provide\w*)\b.{{0,100}}\b(?:tool|surface|tether\s+point)\b",
        rf"\b(?:bond\w*|attach\w*|secure\w*|retain\w*)\b.{{0,60}}\b(?:with|using|via)\b.{{0,50}}\b{_ADHESIVE_TERM}\b",
    )
    return any(re.search(pattern, sentence, re.I | re.S) for pattern in patterns)
