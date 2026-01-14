"""Tests for configuration settings."""

from datetime import time


def test_time_settings_exist():
    from config.settings import MAX_ARRIVAL_TIME, MIN_DEPARTURE_TIME, RELAXED_MARGIN_MINUTES

    assert isinstance(MAX_ARRIVAL_TIME, time)
    assert isinstance(MIN_DEPARTURE_TIME, time)
    assert isinstance(RELAXED_MARGIN_MINUTES, int)
    assert RELAXED_MARGIN_MINUTES == 60


def test_single_leg_threshold_exists():
    from config.settings import SINGLE_LEG_THRESHOLD

    assert isinstance(SINGLE_LEG_THRESHOLD, (int, float))
    assert SINGLE_LEG_THRESHOLD == 45


def test_routes_defined():
    from config.settings import ROUTES

    assert ROUTES == [("MAD", "BCN"), ("OVD", "BCN")]


def test_routes_with_single_legs_defined():
    from config.settings import ROUTES_WITH_SINGLE_LEGS

    assert isinstance(ROUTES_WITH_SINGLE_LEGS, list)
    assert ROUTES_WITH_SINGLE_LEGS == ["MAD"]
