from bs4 import BeautifulSoup

from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import SourceType


PDF_URL = "https://productdata.hilti.com/APQ_HC_RAW/PUB_5664433_000.pdf"
INDEX_URL = "https://www.hilti.com/technical-library?search=true&text=SF+4-22"


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
    ancestors = []
    node = heading
    for _ in range(5):
        if node is None:
            break
        ancestors.append({
            "tag": node.name,
            "attrs": dict(node.attrs),
            "links": [
                {"text": " ".join(link.stripped_strings), "href": link.get("href"), "attrs": dict(link.attrs)}
                for link in node.find_all("a", href=True)
            ],
        })
        node = node.parent
    print({"type": "hilti_index_diagnostic", "ancestors": ancestors})
finally:
    fetcher.close()
