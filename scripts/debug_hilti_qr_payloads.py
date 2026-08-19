from bs4 import BeautifulSoup

from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import SourceType


PDF_URL = "https://productdata.hilti.com/APQ_HC_RAW/PUB_5664433_000.pdf"
INDEX_URL = "https://www.hilti.com/technical-library?search=true&text=SF+4-22"
QR_URL = "http://qr.hilti.com/manual/?id=2272253"


def interesting_text(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("2272253", "2272254", "manual", "document", "api", "country", "language"))


fetcher = HttpxFetcher()
try:
    pdf = fetcher.get(PDF_URL, SourceType.MANUFACTURER_DOCUMENT)
    print({
        "type": "hilti_qr_diagnostic",
        "pdf_url": pdf.url,
        "document_qr_payloads": pdf.metadata.get("document_qr_payloads", []),
    })

    index = fetcher.get(INDEX_URL)
    soup = BeautifulSoup(index.body, "html.parser")
    heading = next(
        node for node in soup.find_all(["h2", "h3", "h4"])
        if "Operating Instruction SF" in " ".join(node.stripped_strings)
        and "4-22" in " ".join(node.stripped_strings)
    )
    card = heading
    for _ in range(5):
        if card.parent is None:
            break
        card = card.parent
    print({
        "type": "hilti_index_diagnostic",
        "card_links": [link.get("href") for link in card.find_all("a", href=True)],
        "card_attrs": dict(card.attrs),
    })

    resolver = fetcher.get(QR_URL)
    resolver_soup = BeautifulSoup(resolver.body, "html.parser")
    scripts = [script.get("src") for script in resolver_soup.find_all("script", src=True)]
    forms = [form.get("action") for form in resolver_soup.find_all("form")]
    links = [link.get("href") for link in resolver_soup.find_all("a", href=True)]
    snippets = []
    for node in resolver_soup.find_all(["script", "input", "form", "a"]):
        rendered = str(node)
        if interesting_text(rendered):
            snippets.append(rendered[:500])
        if len(snippets) >= 12:
            break
    print({
        "type": "hilti_qr_resolver_diagnostic",
        "resolved_url": resolver.url,
        "content_type": resolver.content_type,
        "title": resolver_soup.title.get_text(" ", strip=True) if resolver_soup.title else None,
        "scripts": scripts,
        "forms": forms,
        "links": links[:30],
        "interesting_snippets": snippets,
    })
finally:
    fetcher.close()
