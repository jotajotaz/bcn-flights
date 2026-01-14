"""Tests for Amadeus client."""

from datetime import datetime

from src.amadeus_client import FlightOption, CARRIER_NAMES


class TestFlightOption:
    def test_departure_time_str(self):
        flight = FlightOption(
            origin="MAD",
            destination="BCN",
            departure_time=datetime(2026, 1, 28, 7, 30),
            arrival_time=datetime(2026, 1, 28, 8, 45),
            price=50.0,
            carrier_code="UX",
            carrier_name="Air Europa",
            flight_number="1234",
        )
        assert flight.departure_time_str == "07:30"
        assert flight.arrival_time_str == "08:45"

    def test_flight_date(self):
        flight = FlightOption(
            origin="MAD",
            destination="BCN",
            departure_time=datetime(2026, 1, 28, 7, 30),
            arrival_time=datetime(2026, 1, 28, 8, 45),
            price=50.0,
            carrier_code="UX",
            carrier_name="Air Europa",
            flight_number="1234",
        )
        assert flight.flight_date.year == 2026
        assert flight.flight_date.month == 1
        assert flight.flight_date.day == 28


class TestCarrierNames:
    def test_known_carriers(self):
        assert CARRIER_NAMES["IB"] == "Iberia"
        assert CARRIER_NAMES["VY"] == "Vueling"
        assert CARRIER_NAMES["UX"] == "Air Europa"

    def test_no_train_carriers(self):
        # Train carriers should be removed
        assert "RENFE" not in CARRIER_NAMES
        assert "2C" not in CARRIER_NAMES
