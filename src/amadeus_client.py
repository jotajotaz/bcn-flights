"""Cliente para la API de Amadeus."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Optional

from amadeus import Client, ResponseError

from config.settings import (
    AMADEUS_API_KEY,
    AMADEUS_API_SECRET,
    MAX_RESULTS_PER_SEARCH,
)

logger = logging.getLogger(__name__)


@dataclass
class FlightOption:
    """Representa una opcion de vuelo."""
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    carrier_code: str
    carrier_name: str
    flight_number: str

    @property
    def departure_time_str(self) -> str:
        return self.departure_time.strftime("%H:%M")

    @property
    def arrival_time_str(self) -> str:
        return self.arrival_time.strftime("%H:%M")

    @property
    def flight_date(self) -> date:
        return self.departure_time.date()


# Mapeo de codigos de aerolineas
CARRIER_NAMES = {
    "IB": "Iberia",
    "VY": "Vueling",
    "UX": "Air Europa",
    "I2": "Iberia Express",
    "FR": "Ryanair",
    "6Y": "SmartLynx",
}


class AmadeusClient:
    """Cliente para buscar vuelos en Amadeus."""

    def __init__(self):
        if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
            raise ValueError("Faltan credenciales de Amadeus. Configura AMADEUS_API_KEY y AMADEUS_API_SECRET")

        self.client = Client(
            client_id=AMADEUS_API_KEY,
            client_secret=AMADEUS_API_SECRET,
        )

    def search_flights(
        self,
        origin: str,
        destination: str,
        search_date: str,
        max_arrival_time: Optional[time] = None,
        min_departure_time: Optional[time] = None,
    ) -> list[FlightOption]:
        """
        Busca vuelos para una ruta y fecha.
        """
        try:
            logger.info(f"Buscando {origin}->{destination} para {search_date}")

            response = self.client.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=search_date,
                adults=1,
                nonStop="true",  # String, not boolean - this is the fix!
                currencyCode="EUR",
                max=MAX_RESULTS_PER_SEARCH,
            )

            options = []
            for offer in response.data:
                try:
                    option = self._parse_offer(offer)
                    if option and self._matches_time_filter(option, max_arrival_time, min_departure_time):
                        options.append(option)
                except Exception as e:
                    logger.warning(f"Error parseando oferta: {e}")
                    continue

            options.sort(key=lambda x: x.price)
            logger.info(f"Encontradas {len(options)} opciones para {origin}->{destination}")
            return options

        except ResponseError as e:
            logger.error(f"Error de Amadeus API: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado buscando vuelos: {e}")
            return []

    def _parse_offer(self, offer: dict) -> Optional[FlightOption]:
        """Parsea una oferta de Amadeus a FlightOption."""
        try:
            price = float(offer["price"]["total"])
            itinerary = offer["itineraries"][0]
            segment = itinerary["segments"][0]

            carrier_code = segment["carrierCode"]
            flight_number = segment.get("number", "")
            departure = datetime.fromisoformat(segment["departure"]["at"])
            arrival = datetime.fromisoformat(segment["arrival"]["at"])
            origin = segment["departure"]["iataCode"]
            destination = segment["arrival"]["iataCode"]
            carrier_name = CARRIER_NAMES.get(carrier_code, carrier_code)

            return FlightOption(
                origin=origin,
                destination=destination,
                departure_time=departure,
                arrival_time=arrival,
                price=price,
                carrier_code=carrier_code,
                carrier_name=carrier_name,
                flight_number=flight_number,
            )
        except (KeyError, IndexError, ValueError) as e:
            logger.warning(f"Error parseando oferta: {e}")
            return None

    def _matches_time_filter(
        self,
        option: FlightOption,
        max_arrival_time: Optional[time],
        min_departure_time: Optional[time],
    ) -> bool:
        """Verifica si la opcion cumple los filtros de horario."""
        if max_arrival_time and option.arrival_time.time() > max_arrival_time:
            return False
        if min_departure_time and option.departure_time.time() < min_departure_time:
            return False
        return True
