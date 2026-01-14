"""Cliente para la API de Amadeus."""

import logging
from dataclasses import dataclass
from datetime import datetime, time
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
    """Representa una opción de vuelo/tren."""
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    currency: str
    carrier: str
    carrier_name: str
    flight_number: str
    is_train: bool = False

    @property
    def departure_time_str(self) -> str:
        return self.departure_time.strftime("%H:%M")

    @property
    def arrival_time_str(self) -> str:
        return self.arrival_time.strftime("%H:%M")

    @property
    def transport_type(self) -> str:
        return "AVE" if self.is_train else self.carrier_name


class AmadeusClient:
    """Cliente para buscar vuelos y trenes en Amadeus."""

    # Códigos de aerolíneas/trenes comunes
    CARRIER_NAMES = {
        "IB": "Iberia",
        "VY": "Vueling",
        "FR": "Ryanair",
        "UX": "Air Europa",
        "6Y": "SmartLynx",
        "I2": "Iberia Express",
        "RENFE": "AVE",
        "2C": "SNCF",
    }

    # Códigos que indican tren
    TRAIN_CARRIERS = {"RENFE", "2C", "9F"}

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
        date: str,
        max_arrival_time: Optional[time] = None,
        min_departure_time: Optional[time] = None,
    ) -> list[FlightOption]:
        """
        Busca vuelos/trenes para una ruta y fecha.

        Args:
            origin: Código IATA del aeropuerto de origen
            destination: Código IATA del aeropuerto de destino
            date: Fecha en formato YYYY-MM-DD
            max_arrival_time: Hora máxima de llegada (para vuelos de ida)
            min_departure_time: Hora mínima de salida (para vuelos de vuelta)

        Returns:
            Lista de opciones de vuelo ordenadas por precio
        """
        try:
            logger.info(f"Buscando {origin}→{destination} para {date}")

            response = self.client.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=date,
                adults=1,
                nonStop=True,  # Solo vuelos directos
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

            # Ordenar por precio
            options.sort(key=lambda x: x.price)

            logger.info(f"Encontradas {len(options)} opciones para {origin}→{destination}")
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
            currency = offer["price"]["currency"]

            # Tomar el primer segmento (vuelo directo)
            itinerary = offer["itineraries"][0]
            segment = itinerary["segments"][0]

            carrier = segment["carrierCode"]
            flight_number = segment.get("number", "")

            departure = datetime.fromisoformat(segment["departure"]["at"])
            arrival = datetime.fromisoformat(segment["arrival"]["at"])

            origin = segment["departure"]["iataCode"]
            destination = segment["arrival"]["iataCode"]

            is_train = carrier in self.TRAIN_CARRIERS
            carrier_name = self.CARRIER_NAMES.get(carrier, carrier)

            return FlightOption(
                origin=origin,
                destination=destination,
                departure_time=departure,
                arrival_time=arrival,
                price=price,
                currency=currency,
                carrier=carrier,
                carrier_name=carrier_name,
                flight_number=flight_number,
                is_train=is_train,
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
        """Verifica si la opción cumple los filtros de horario."""
        if max_arrival_time and option.arrival_time.time() > max_arrival_time:
            return False
        if min_departure_time and option.departure_time.time() < min_departure_time:
            return False
        return True
