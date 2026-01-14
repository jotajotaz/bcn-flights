"""Lógica de búsqueda y combinación de vuelos."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from config.settings import (
    DAY_PAIRS,
    MAX_ARRIVAL_TIME,
    MAX_ARRIVAL_TIME_RELAXED,
    MIN_DEPARTURE_TIME,
    MIN_DEPARTURE_TIME_RELAXED,
    MIN_PRICE,
    MAX_PRICE,
    ROUTE_COMBINATIONS,
    WEEKS_AHEAD,
)
from src.amadeus_client import AmadeusClient, FlightOption

logger = logging.getLogger(__name__)


@dataclass
class TripOption:
    """Representa un viaje completo (ida + vuelta)."""
    outbound: FlightOption
    return_flight: FlightOption
    outbound_date: date
    return_date: date

    @property
    def total_price(self) -> float:
        return self.outbound.price + self.return_flight.price

    @property
    def route_description(self) -> str:
        return f"{self.outbound.origin}→{self.outbound.destination}→{self.return_flight.destination}"

    def __str__(self) -> str:
        return (
            f"{self.outbound_date.strftime('%a %d')} → {self.return_date.strftime('%a %d')}: "
            f"{self.route_description} = {self.total_price:.0f}€"
        )


@dataclass
class SearchResult:
    """Resultado de la búsqueda semanal."""
    week_start: date
    options: list[TripOption]
    relaxed_filters: bool = False
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def best_option(self) -> Optional[TripOption]:
        return self.options[0] if self.options else None

    def get_best_by_day_pair(self) -> dict[tuple[int, int], Optional[TripOption]]:
        """Retorna la mejor opción por cada par de días."""
        result = {}
        for day_pair in DAY_PAIRS:
            matching = [
                opt for opt in self.options
                if (opt.outbound_date.weekday(), opt.return_date.weekday()) == day_pair
            ]
            result[day_pair] = matching[0] if matching else None
        return result


class FlightSearcher:
    """Buscador de vuelos que combina todas las opciones."""

    def __init__(self, client: Optional[AmadeusClient] = None):
        self.client = client or AmadeusClient()

    def search_week(self, target_date: Optional[date] = None) -> SearchResult:
        """
        Busca todas las opciones para una semana.

        Args:
            target_date: Fecha de referencia (por defecto: hoy + WEEKS_AHEAD semanas)

        Returns:
            SearchResult con todas las opciones ordenadas por precio
        """
        if target_date is None:
            target_date = date.today() + timedelta(weeks=WEEKS_AHEAD)

        # Encontrar el lunes de esa semana
        week_start = target_date - timedelta(days=target_date.weekday())

        logger.info(f"Buscando opciones para semana del {week_start}")

        all_options = []
        errors = []
        relaxed = False

        # Buscar para cada par de días y cada combinación de rutas
        for day_pair in DAY_PAIRS:
            outbound_date = week_start + timedelta(days=day_pair[0])
            return_date = week_start + timedelta(days=day_pair[1])

            for outbound_route, return_route in ROUTE_COMBINATIONS:
                try:
                    options = self._search_trip(
                        outbound_route.origin,
                        outbound_route.destination,
                        return_route.destination,
                        outbound_date,
                        return_date,
                    )
                    all_options.extend(options)
                except Exception as e:
                    error_msg = f"Error buscando {outbound_route.name} {outbound_date}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        # Si no hay opciones, intentar con filtros relajados
        if not all_options:
            logger.warning("Sin opciones con filtros estrictos, relajando horarios...")
            relaxed = True
            for day_pair in DAY_PAIRS:
                outbound_date = week_start + timedelta(days=day_pair[0])
                return_date = week_start + timedelta(days=day_pair[1])

                for outbound_route, return_route in ROUTE_COMBINATIONS:
                    try:
                        options = self._search_trip(
                            outbound_route.origin,
                            outbound_route.destination,
                            return_route.destination,
                            outbound_date,
                            return_date,
                            relaxed=True,
                        )
                        all_options.extend(options)
                    except Exception as e:
                        logger.error(f"Error en búsqueda relajada: {e}")

        # Filtrar precios anómalos y ordenar
        all_options = [
            opt for opt in all_options
            if MIN_PRICE <= opt.total_price <= MAX_PRICE
        ]
        all_options.sort(key=lambda x: x.total_price)

        logger.info(f"Encontradas {len(all_options)} opciones totales")

        return SearchResult(
            week_start=week_start,
            options=all_options,
            relaxed_filters=relaxed,
            errors=errors,
        )

    def _search_trip(
        self,
        origin: str,
        via: str,
        destination: str,
        outbound_date: date,
        return_date: date,
        relaxed: bool = False,
    ) -> list[TripOption]:
        """Busca opciones para un viaje completo (ida + vuelta)."""
        max_arrival = MAX_ARRIVAL_TIME_RELAXED if relaxed else MAX_ARRIVAL_TIME
        min_departure = MIN_DEPARTURE_TIME_RELAXED if relaxed else MIN_DEPARTURE_TIME

        # Buscar vuelos de ida
        outbound_options = self.client.search_flights(
            origin=origin,
            destination=via,
            date=outbound_date.isoformat(),
            max_arrival_time=max_arrival,
        )

        if not outbound_options:
            return []

        # Buscar vuelos de vuelta
        return_options = self.client.search_flights(
            origin=via,
            destination=destination,
            date=return_date.isoformat(),
            min_departure_time=min_departure,
        )

        if not return_options:
            return []

        # Combinar: tomar el vuelo más barato de ida con el más barato de vuelta
        # (podrían combinarse todas, pero aumentaría mucho el número de opciones)
        trips = []

        # Tomar las 3 mejores idas y las 3 mejores vueltas
        for outbound in outbound_options[:3]:
            for return_flight in return_options[:3]:
                trips.append(TripOption(
                    outbound=outbound,
                    return_flight=return_flight,
                    outbound_date=outbound_date,
                    return_date=return_date,
                ))

        return trips
