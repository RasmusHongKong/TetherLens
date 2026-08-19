from tetherlens_ingest.http import HttpxFetcher
from tetherlens_ingest.models import SourceType


PDF_URL = "https://productdata.hilti.com/APQ_HC_RAW/PUB_5664433_000.pdf"


fetcher = HttpxFetcher()
try:
    artifact = fetcher.get(PDF_URL, SourceType.MANUFACTURER_DOCUMENT)
    print({
        "type": "hilti_qr_diagnostic",
        "pdf_url": artifact.url,
        "document_qr_payloads": artifact.metadata.get("document_qr_payloads", []),
    })
finally:
    fetcher.close()
