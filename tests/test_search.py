# tests/test_search.py
"""Tests for flight search logic."""

from dataclasses import dataclass
from datetime import date, datetime, time
from unittest.mock import Mock, patch

import pytest

from src.search import RouteResult, TripOption, FlightSearcher
from src.amadeus_client import FlightOption


def make_flight(origin, dest, hour, price, day_offset=0):
    """Helper to create FlightOption."""
    base_date = date(2026, 1, 27)  # Monday
    flight_date = date(2026, 1, 27 + day_offset)
    return FlightOption(
        origin=origin,
        destination=dest,
        departure_time=datetime(flight_date.year, flight_date.month, flight_date.day, hour, 0),
        arrival_time=datetime(flight_date.year, flight_date.month, flight_date.day, hour + 1, 15),
        price=price,
        carrier_code="VY",
        carrier_name="Vueling",
        flight_number="1234",
    )


class TestTripOption:
    def test_total_price(self):
        outbound = make_flight("MAD", "BCN", 7, 50.0)
        return_flight = make_flight("BCN", "MAD", 18, 60.0)
        trip = TripOption(
            outbound=outbound,
            return_flight=return_flight,
            outbound_date=date(2026, 1, 27),
            return_date=date(2026, 1, 28),
        )
        assert trip.total_price == 110.0


class TestRouteResult:
    def test_has_single_legs(self):
        result = RouteResult(
            origin="MAD",
            destination="BCN",
            best_combo=None,
            best_outbound=make_flight("MAD", "BCN", 7, 40.0),
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )
        assert result.best_outbound is not None
        assert result.best_return is None


class TestFlightSearcher:
    @patch("src.search.AmadeusClient")
    def test_search_route_returns_route_result(self, mock_client_class):
        mock_client = Mock()
        mock_client.search_flights.return_value = [
            make_flight("MAD", "BCN", 7, 50.0),
        ]
        mock_client_class.return_value = mock_client

        searcher = FlightSearcher(client=mock_client)
        result = searcher.search_route("MAD", "BCN", date(2026, 1, 27))

        assert isinstance(result, RouteResult)
        assert result.origin == "MAD"
        assert result.destination == "BCN"

    @patch("src.search.AmadeusClient")
    def test_single_legs_only_for_configured_routes(self, mock_client_class):
        mock_client = Mock()
        mock_client.search_flights.return_value = [
            make_flight("OVD", "BCN", 7, 30.0),  # Price < threshold
        ]
        mock_client_class.return_value = mock_client

        searcher = FlightSearcher(client=mock_client)
        result = searcher.search_route("OVD", "BCN", date(2026, 1, 27))

        # OVD should not have single legs even if price < threshold
        assert result.best_outbound is None
        assert result.best_return is None
