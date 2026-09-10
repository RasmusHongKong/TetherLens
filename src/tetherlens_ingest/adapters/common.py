from __future__ import annotations

import re

from bs4 import BeautifulSoup


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return "\n".join(s.strip() for s in soup.stripped_strings)


def labeled_value(text: str, label: str) -> str | None:
    pattern = rf"{re.escape(label)}\s*[:\n]?\s*([^\n]+)"
    m = re.search(pattern, text, re.I)
    return m.group(1).strip() if m else None


def first_match(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1).strip() if m else None


def bounded_record_for_identifier(
    text: str,
    identifier: str,
    record_marker_pattern: str | re.Pattern[str],
) -> str | None:
    """Return one identity-local record from flattened multi-record text.

    The caller defines the source-format-specific record marker pattern. The returned
    slice starts at the requested identifier marker and stops before the next record
    marker, so a field parser cannot silently consume facts from a neighboring product
    row. If the requested identifier is not itself a recognized record marker, fail
    closed rather than searching unbounded text.
    """

    marker = (
        record_marker_pattern
        if isinstance(record_marker_pattern, re.Pattern)
        else re.compile(record_marker_pattern, re.I)
    )
    target = identifier.casefold()
    matches = list(marker.finditer(text))
    for index, match in enumerate(matches):
        if match.group(0).casefold() != target:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[match.start():end]
    return None
