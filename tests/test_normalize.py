from tetherlens_ingest.normalize import mass_to_kg, parse_length_range_mm


def test_lb_to_kg():
    assert mass_to_kg(15, "lb") == 6.803886


def test_nlg_length_range():
    assert parse_length_range_mm("Dimensions: Extends 80cm to120cm") == (800.0, 1200.0)
