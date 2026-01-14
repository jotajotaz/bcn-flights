# src/search.py
"""Logica de busqueda de vuelos."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional

from config.settings import (
    DAY_PAIRS,
    MAX_ARRIVAL_TIME,
    MIN_DEPARTURE_TIME,
    RELAXED_MARGIN_MINUTES,
    SINGLE_LEG_THRESHOLD,
    ROUTES_WITH_SINGLE_LEGS,
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


@dataclass
class RouteResult:
    """Resultado de busqueda para una ruta."""
    origin: str
    destination: str
    best_combo: Optional[TripOption]
    best_outbound: Optional[FlightOption]  # Solo si origin in ROUTES_WITH_SINGLE_LEGS
    best_return: Optional[FlightOption]    # Solo si origin in ROUTES_WITH_SINGLE_LEGS
    week_start: date
    relaxed_filters: bool = False


def _add_minutes_to_time(t: time, minutes: int) -> time:
    """Anade minutos a un time object."""
    dt = datetime.combine(date.today(), t)
    dt += timedelta(minutes=minutes)
    return dt.time()


def _subtract_minutes_from_time(t: time, minutes: int) -> time:
    """Resta minutos a un time object."""
    dt = datetime.combine(date.today(), t)
    dt -= timedelta(minutes=minutes)
    return dt.time()


class FlightSearcher:
    """Buscador de vuelos."""

    def __init__(self, client: Optional[AmadeusClient] = None):
        self.client = client or AmadeusClient()

    def search_route(self, origin: str, destination: str, target_date: date) -> RouteResult:
        """
        Busca vuelos para una ruta durante una semana.

        Args:
            origin: Codigo IATA origen
            destination: Codigo IATA destino
            target_date: Fecha de referencia (se usa el lunes de esa semana)

        Returns:
            RouteResult con el mejor combo y legs sueltos (si aplica)
        """
        week_start = target_date - timedelta(days=target_date.weekday())

        # Intentar con filtros estrictos
        result = self._search_with_filters(
            origin, destination, week_start,
            MAX_ARRIVAL_TIME, MIN_DEPARTURE_TIME,
            relaxed=False,
        )

        # Si no hay resultados, intentar con filtros relajados
        if result.best_combo is None:
            logger.warning(f"Sin resultados para {origin}->{destination}, probando filtros relajados")
            relaxed_arrival = _add_minutes_to_time(MAX_ARRIVAL_TIME, RELAXED_MARGIN_MINUTES)
            relaxed_departure = _subtract_minutes_from_time(MIN_DEPARTURE_TIME, RELAXED_MARGIN_MINUTES)
            result = self._search_with_filters(
                origin, destination, week_start,
                relaxed_arrival, relaxed_departure,
                relaxed=True,
            )

        return result

    def _search_with_filters(
        self,
        origin: str,
        destination: str,
        week_start: date,
        max_arrival: time,
        min_departure: time,
        relaxed: bool,
    ) -> RouteResult:
        """Busca vuelos con filtros especificos."""
        all_combos: list[TripOption] = []
        all_outbound: list[FlightOption] = []
        all_return: list[FlightOption] = []

        for day_out, day_ret in DAY_PAIRS:
            outbound_date = week_start + timedelta(days=day_out)
            return_date = week_start + timedelta(days=day_ret)

            # Buscar vuelos de ida
            outbound_flights = self.client.search_flights(
                origin=origin,
                destination=destination,
                search_date=outbound_date.isoformat(),
                max_arrival_time=max_arrival,
            )
            all_outbound.extend(outbound_flights)

            # Buscar vuelos de vuelta
            return_flights = self.client.search_flights(
                origin=destination,
                destination=origin,
                search_date=return_date.isoformat(),
                min_departure_time=min_departure,
            )
            all_return.extend(return_flights)

            # Combinar mejor ida + mejor vuelta para este par de dias
            if outbound_flights and return_flights:
                best_out = min(outbound_flights, key=lambda x: x.price)
                best_ret = min(return_flights, key=lambda x: x.price)
                all_combos.append(TripOption(
                    outbound=best_out,
                    return_flight=best_ret,
                    outbound_date=outbound_date,
                    return_date=return_date,
                ))

        # Encontrar mejor combo
        best_combo = min(all_combos, key=lambda x: x.total_price) if all_combos else None

        # Single legs solo para rutas configuradas
        best_outbound = None
        best_return = None
        if origin in ROUTES_WITH_SINGLE_LEGS and all_outbound:
            cheapest_out = min(all_outbound, key=lambda x: x.price)
            if cheapest_out.price < SINGLE_LEG_THRESHOLD:
                best_outbound = cheapest_out

        if origin in ROUTES_WITH_SINGLE_LEGS and all_return:
            cheapest_ret = min(all_return, key=lambda x: x.price)
            if cheapest_ret.price < SINGLE_LEG_THRESHOLD:
                best_return = cheapest_ret

        return RouteResult(
            origin=origin,
            destination=destination,
            best_combo=best_combo,
            best_outbound=best_outbound,
            best_return=best_return,
            week_start=week_start,
            relaxed_filters=relaxed,
        )
