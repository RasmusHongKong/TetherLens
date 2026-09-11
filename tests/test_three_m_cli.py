from tetherlens_ingest.adapters import ThreeMAdapter
from tetherlens_ingest.cli import ADAPTERS, build_parser


def test_three_m_adapter_is_executable_from_cli() -> None:
    assert ADAPTERS["3m"] is ThreeMAdapter

    args = build_parser().parse_args(
        [
            "3m",
            "https://www.3m.com/3M/en_LB/p/d/v100323604/",
            "--sku",
            "1500028",
            "--product-type",
            "tool_attachment",
        ]
    )

    assert args.manufacturer == "3m"
    assert args.sku == "1500028"
    assert args.product_type == "tool_attachment"
