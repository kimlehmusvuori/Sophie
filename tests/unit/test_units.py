from __future__ import annotations

from sophie.domain.units import (
    format_duration,
    format_pace,
    kg_to_lb,
    km_to_m,
    lb_to_kg,
    m_to_km,
    pace_s_per_km,
)


def test_km_m_roundtrip():
    assert km_to_m(10) == 10000
    assert m_to_km(10000) == 10


def test_pace_calculation():
    assert pace_s_per_km(10000, 3000) == 300
    assert pace_s_per_km(0, 3000) is None
    assert pace_s_per_km(10000, 0) is None


def test_format_pace():
    assert format_pace(300) == "5:00/km"
    assert format_pace(None) == "—"


def test_format_duration():
    assert format_duration(None) == "—"
    assert format_duration(45) == "45s"
    assert format_duration(125) == "2m05s"
    assert format_duration(3725) == "1h02m"


def test_weight_conversions():
    assert round(lb_to_kg(kg_to_lb(80)), 4) == 80.0
