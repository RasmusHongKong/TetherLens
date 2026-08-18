from __future__ import annotations

import argparse
import os

from tetherlens_ingest.models import ProductIdentity, ProductType
from tetherlens_ingest.resolvers import SearchIndexedToolMassResolver
from tetherlens_ingest.search import BraveSearchProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe generic search-index tool-mass resolution.")
    parser.add_argument("sku", nargs="?", default="2602-20")
    parser.add_argument("--manufacturer", default="Milwaukee")
    args = parser.parse_args()

    if not os.getenv("BRAVE_SEARCH_API_KEY"):
        raise SystemExit("Set BRAVE_SEARCH_API_KEY before running this probe.")

    provider = BraveSearchProvider.from_env()
    assert provider is not None
    resolver = SearchIndexedToolMassResolver(provider)
    identity = ProductIdentity(
        manufacturer=args.manufacturer,
        sku=args.sku,
        product_type=ProductType.TOOL,
        url="https://example.invalid/source-page-not-used-by-search-probe",
    )

    try:
        queries = resolver._queries(identity)
        candidates = []
        for number, query in enumerate(queries, start=1):
            print(f"query {number}: {query}")
            results = provider.search(query, limit=8)
            print(f"results: {len(results)}")
            for result in results:
                candidate = resolver._candidate(result, identity)
                marker = "CANDIDATE" if candidate else "-"
                print(f"  {marker} rank={result.rank} {result.title}")
                print(f"    {result.url}")
                print(f"    {result.snippet}")
                if candidate:
                    candidates.append(candidate)
                    print(
                        f"    mass={candidate.raw_mass} ({candidate.mass_kg:.6f} kg) "
                        f"domain={candidate.domain} qualified_domain={candidate.qualified_domain}"
                    )
            accepted = resolver._accepted(candidates)
            if accepted:
                primary = accepted[0]
                print("result: RESOLVED")
                print(f"mass: {primary.raw_mass} = {primary.mass_kg:.6f} kg")
                print(f"source: {primary.result.url}")
                if len(accepted) > 1:
                    print("corroboration:")
                    for extra in accepted[1:]:
                        print(f"  {extra.result.url}")
                return
        print("result: UNRESOLVED")
    finally:
        provider.close()


if __name__ == "__main__":
    main()
