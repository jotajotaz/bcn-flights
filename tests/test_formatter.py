# tests/test_formatter.py
"""Tests for message formatter."""

from datetime import date, datetime

from src.formatter import format_telegram_message
from src.search import RouteResult, TripOption
from src.amadeus_client import FlightOption


def make_flight(origin, dest, hour, price, flight_date):
    return FlightOption(
        origin=origin,
        destination=dest,
        departure_time=datetime(flight_date.year, flight_date.month, flight_date.day, hour, 30),
        arrival_time=datetime(flight_date.year, flight_date.month, flight_date.day, hour + 1, 45),
        price=price,
        carrier_code="VY",
        carrier_name="Vueling",
        flight_number="1234",
    )


class TestFormatTelegramMessage:
    def test_includes_header(self):
        mad_result = RouteResult(
            origin="MAD",
            destination="BCN",
            best_combo=None,
            best_outbound=None,
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )
        ovd_result = RouteResult(
            origin="OVD",
            destination="BCN",
            best_combo=None,
            best_outbound=None,
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )

        message = format_telegram_message(mad_result, ovd_result)

        assert "VUELOS BCN" in message
        assert "27" in message
        assert "ene" in message

    def test_includes_skyscanner_link_for_combo(self):
        outbound = make_flight("MAD", "BCN", 7, 50.0, date(2026, 1, 27))
        return_flight = make_flight("BCN", "MAD", 18, 60.0, date(2026, 1, 28))
        combo = TripOption(
            outbound=outbound,
            return_flight=return_flight,
            outbound_date=date(2026, 1, 27),
            return_date=date(2026, 1, 28),
        )
        mad_result = RouteResult(
            origin="MAD",
            destination="BCN",
            best_combo=combo,
            best_outbound=None,
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )
        ovd_result = RouteResult(
            origin="OVD",
            destination="BCN",
            best_combo=None,
            best_outbound=None,
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )

        message = format_telegram_message(mad_result, ovd_result)

        assert "skyscanner.es" in message

    def test_includes_trainline_link(self):
        mad_result = RouteResult(
            origin="MAD",
            destination="BCN",
            best_combo=None,
            best_outbound=None,
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )
        ovd_result = RouteResult(
            origin="OVD",
            destination="BCN",
            best_combo=None,
            best_outbound=None,
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )

        message = format_telegram_message(mad_result, ovd_result)

        assert "trainline" in message.lower()
        assert "madrid" in message.lower()

    def test_single_leg_shown_when_present(self):
        single_leg = make_flight("MAD", "BCN", 7, 40.0, date(2026, 1, 27))
        mad_result = RouteResult(
            origin="MAD",
            destination="BCN",
            best_combo=None,
            best_outbound=single_leg,
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )
        ovd_result = RouteResult(
            origin="OVD",
            destination="BCN",
            best_combo=None,
            best_outbound=None,
            best_return=None,
            week_start=date(2026, 1, 27),
            relaxed_filters=False,
        )

        message = format_telegram_message(mad_result, ovd_result)

        assert "Ida suelta" in message
        assert "40" in message
