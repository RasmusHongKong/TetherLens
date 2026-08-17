from __future__ import annotations

import argparse
import html
import re
from urllib.parse import quote_plus, urljoin

import httpx

SEARCH_URL = "https://www.grainger.ca/en/search?searchQuery={query}"
USER_AGENT = "TetherLensLocalSourceProbe/0.1"


def candidate_url(raw: str, sku: str) -> str | None:
    decoded = html.unescape(raw)
    for match in re.finditer(r'href=["\']([^"\']*?/en/product/[^"\']+/p/[^"\']+)["\']', decoded, re.I):
        href = match.group(1)
        context = decoded[max(0, match.start() - 400): min(len(decoded), match.end() + 400)]
        if re.search(rf"(?<![A-Z0-9]){re.escape(sku)}(?![A-Z0-9])", context, re.I):
            return urljoin("https://www.grainger.ca", href)
    return None


def fetch(client: httpx.Client, label: str, url: str) -> httpx.Response | None:
    try:
        response = client.get(url)
    except Exception as exc:
        print(f"{label}: request error: {type(exc).__name__}: {exc}")
        return None
    print(f"{label}: {response.status_code} {response.url}")
    print(f"{label}: content-type={response.headers.get('content-type')} bytes={len(response.content)}")
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare local Grainger access with CI behavior.")
    parser.add_argument("sku", nargs="?", default="2602-20")
    parser.add_argument(
        "--product-url",
        help="Optional known Grainger product URL. If search is blocked or JS-only, this tests the product page directly.",
    )
    args = parser.parse_args()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en;q=0.9",
    }
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        search_url = SEARCH_URL.format(query=quote_plus(args.sku))
        search = fetch(client, "search", search_url)
        discovered = None
        if search is not None and search.is_success:
            discovered = candidate_url(search.text, args.sku)
            print(f"search: exact-SKU product link={'FOUND' if discovered else 'NOT FOUND'}")

        product_url = args.product_url or discovered
        if not product_url:
            print("product: not requested (no URL discovered/provided)")
            print("result: search access may work while discovery is JS-only; retry with --product-url if you know the exact product page.")
            return

        product = fetch(client, "product", product_url)
        if product is None:
            return

        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", product.text)))
        model_match = bool(re.search(rf"Mfr\.?\s*Model\s*#?\s*{re.escape(args.sku)}\b", text, re.I))
        weight = re.search(r"\bTool\s+Weight\s*[:#]?\s*(\d+(?:\.\d+)?)\s*(lb|lbs|kg)\.?\b", text, re.I)
        shipping = re.search(r"\bShipping\s+Weight\s*[:#]?\s*(\d+(?:\.\d+)?)\s*(lb|lbs|kg)\.?\b", text, re.I)
        print(f"product: exact Mfr. Model match={model_match}")
        print(f"product: Tool Weight={weight.group(1) + ' ' + weight.group(2) if weight else 'NOT FOUND'}")
        print(f"product: Shipping Weight={shipping.group(1) + ' ' + shipping.group(2) if shipping else 'NOT FOUND'}")


if __name__ == "__main__":
    main()
