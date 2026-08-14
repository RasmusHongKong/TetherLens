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
