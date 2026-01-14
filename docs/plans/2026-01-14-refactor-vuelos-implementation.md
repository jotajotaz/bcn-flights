# Refactor Vuelos BCN - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactorizar el buscador de vuelos para eliminar código muerto de trenes, simplificar a dos rutas independientes (MAD↔BCN, OVD↔BCN), y añadir enlaces a Skyscanner/Trainline.

**Architecture:** Búsqueda independiente por ruta usando Amadeus API. Cada ruta devuelve un `RouteResult` con el mejor combo ida+vuelta y opcionalmente legs sueltos (solo MAD↔BCN si precio < umbral). El formatter genera el mensaje con URLs de Skyscanner y Trainline.

**Tech Stack:** Python 3.11, Amadeus SDK, requests, python-dotenv

**Design doc:** `docs/plans/2026-01-14-refactor-vuelos-design.md`

---

## Task 1: Actualizar configuración

**Files:**
- Modify: `config/settings.py`
- Create: `tests/test_settings.py`

**Step 1: Write test for new settings**

```python
# tests/test_settings.py
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
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_settings.py -v`
Expected: FAIL (missing SINGLE_LEG_THRESHOLD, RELAXED_MARGIN_MINUTES, ROUTES)

**Step 3: Update settings.py**

```python
# config/settings.py
"""Configuración del buscador de vuelos BCN."""

import os
from datetime import time


# Filtros de horario (parametrizables)
MAX_ARRIVAL_TIME = time(10, 0)       # Llegada ida ≤ 10:00
MIN_DEPARTURE_TIME = time(17, 0)     # Salida vuelta ≥ 17:00
RELAXED_MARGIN_MINUTES = 60          # Margen fijo para filtros relajados

# Umbral para mostrar legs sueltos (parametrizable)
SINGLE_LEG_THRESHOLD = 45  # euros

# Rutas a buscar
ROUTES = [
    ("MAD", "BCN"),
    ("OVD", "BCN"),
]

# Rutas con opción de legs sueltos (para combinar con tren)
ROUTES_WITH_SINGLE_LEGS = ["MAD"]

# Configuración de búsqueda
WEEKS_AHEAD = 2
MAX_RESULTS_PER_SEARCH = 10

# Pares de días (día de ida, día de vuelta) - 0=Lunes
DAY_PAIRS = [
    (0, 1),  # Lunes-Martes
    (1, 2),  # Martes-Miércoles
    (2, 3),  # Miércoles-Jueves
    (3, 4),  # Jueves-Viernes
]

DAY_NAMES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Reintentos
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# API Keys (desde variables de entorno)
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_settings.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add config/settings.py tests/test_settings.py
git commit -m "refactor(settings): simplify config, add SINGLE_LEG_THRESHOLD and ROUTES"
```

---

## Task 2: Crear URL builder

**Files:**
- Create: `src/url_builder.py`
- Create: `tests/test_url_builder.py`

**Step 1: Write tests for URL builder**

```python
# tests/test_url_builder.py
"""Tests for URL builder."""

from datetime import date

from src.url_builder import skyscanner_url, trainline_url


class TestSkyscannerUrl:
    def test_roundtrip_url(self):
        url = skyscanner_url("MAD", "BCN", date(2026, 1, 28), date(2026, 1, 29))
        assert "skyscanner.es" in url
        assert "mad" in url.lower()
        assert "bcn" in url.lower()
        assert "260128" in url  # fecha ida
        assert "260129" in url  # fecha vuelta

    def test_oneway_url(self):
        url = skyscanner_url("MAD", "BCN", date(2026, 1, 28))
        assert "skyscanner.es" in url
        assert "260128" in url
        assert "260129" not in url  # sin vuelta


class TestTrainlineUrl:
    def test_madrid_barcelona(self):
        url = trainline_url("MAD", "BCN")
        assert "thetrainline.com" in url
        assert "madrid" in url.lower()
        assert "barcelona" in url.lower()

    def test_barcelona_madrid(self):
        url = trainline_url("BCN", "MAD")
        assert "thetrainline.com" in url
        assert "barcelona-to-madrid" in url.lower() or "madrid" in url.lower()

    def test_oviedo_returns_none(self):
        url = trainline_url("OVD", "BCN")
        assert url is None

    def test_unknown_city_returns_none(self):
        url = trainline_url("XXX", "BCN")
        assert url is None
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_url_builder.py -v`
Expected: FAIL (module not found)

**Step 3: Implement URL builder**

```python
# src/url_builder.py
"""Generador de URLs para Skyscanner y Trainline."""

from datetime import date

# Mapeo de códigos IATA a nombres de ciudad para Trainline
TRAINLINE_CITIES = {
    "MAD": "madrid",
    "BCN": "barcelona",
}


def skyscanner_url(
    origin: str,
    destination: str,
    outbound_date: date,
    return_date: date | None = None,
) -> str:
    """
    Genera URL de Skyscanner.

    Args:
        origin: Código IATA origen (ej: "MAD")
        destination: Código IATA destino (ej: "BCN")
        outbound_date: Fecha de ida
        return_date: Fecha de vuelta (None para solo ida)

    Returns:
        URL de Skyscanner con la búsqueda pre-rellenada
    """
    origin_lower = origin.lower()
    dest_lower = destination.lower()

    # Formato fecha: YYMMDD
    outbound_str = outbound_date.strftime("%y%m%d")

    if return_date:
        return_str = return_date.strftime("%y%m%d")
        return f"https://www.skyscanner.es/transporte/vuelos/{origin_lower}/{dest_lower}/{outbound_str}/{return_str}/"
    else:
        return f"https://www.skyscanner.es/transporte/vuelos/{origin_lower}/{dest_lower}/{outbound_str}/"


def trainline_url(origin: str, destination: str) -> str | None:
    """
    Genera URL de Trainline para la ruta.

    Args:
        origin: Código IATA origen
        destination: Código IATA destino

    Returns:
        URL de Trainline o None si la ruta no tiene trenes
    """
    origin_city = TRAINLINE_CITIES.get(origin)
    dest_city = TRAINLINE_CITIES.get(destination)

    if not origin_city or not dest_city:
        return None

    return f"https://www.thetrainline.com/es/train-times/{origin_city}-to-{dest_city}"
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_url_builder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/url_builder.py tests/test_url_builder.py
git commit -m "feat(url_builder): add Skyscanner and Trainline URL generators"
```

---

## Task 3: Simplificar AmadeusClient

**Files:**
- Modify: `src/amadeus_client.py`
- Create: `tests/test_amadeus_client.py`

**Step 1: Write tests for simplified client**

```python
# tests/test_amadeus_client.py
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
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_amadeus_client.py -v`
Expected: FAIL (FlightOption missing flight_date, train carriers still exist)

**Step 3: Update amadeus_client.py**

```python
# src/amadeus_client.py
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
    """Representa una opción de vuelo."""
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


# Mapeo de códigos de aerolíneas
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

        Args:
            origin: Código IATA del aeropuerto de origen
            destination: Código IATA del aeropuerto de destino
            search_date: Fecha en formato YYYY-MM-DD
            max_arrival_time: Hora máxima de llegada (para vuelos de ida)
            min_departure_time: Hora mínima de salida (para vuelos de vuelta)

        Returns:
            Lista de opciones de vuelo ordenadas por precio
        """
        try:
            logger.info(f"Buscando {origin}→{destination} para {search_date}")

            response = self.client.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=search_date,
                adults=1,
                nonStop="true",  # String, no boolean
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
        """Verifica si la opción cumple los filtros de horario."""
        if max_arrival_time and option.arrival_time.time() > max_arrival_time:
            return False
        if min_departure_time and option.departure_time.time() < min_departure_time:
            return False
        return True
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_amadeus_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/amadeus_client.py tests/test_amadeus_client.py
git commit -m "refactor(amadeus_client): remove train logic, fix nonStop parameter"
```

---

## Task 4: Nueva lógica de búsqueda

**Files:**
- Modify: `src/search.py`
- Create: `tests/test_search.py`

**Step 1: Write tests for new search logic**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_search.py -v`
Expected: FAIL (RouteResult not defined, search_route not implemented)

**Step 3: Implement new search.py**

```python
# src/search.py
"""Lógica de búsqueda de vuelos."""

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
    """Resultado de búsqueda para una ruta."""
    origin: str
    destination: str
    best_combo: Optional[TripOption]
    best_outbound: Optional[FlightOption]  # Solo si origin in ROUTES_WITH_SINGLE_LEGS
    best_return: Optional[FlightOption]    # Solo si origin in ROUTES_WITH_SINGLE_LEGS
    week_start: date
    relaxed_filters: bool = False


def _add_minutes_to_time(t: time, minutes: int) -> time:
    """Añade minutos a un time object."""
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
            origin: Código IATA origen
            destination: Código IATA destino
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
            logger.warning(f"Sin resultados para {origin}→{destination}, probando filtros relajados")
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
        """Busca vuelos con filtros específicos."""
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

            # Combinar mejor ida + mejor vuelta para este par de días
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
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_search.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/search.py tests/test_search.py
git commit -m "refactor(search): new RouteResult structure, single legs only for MAD"
```

---

## Task 5: Nuevo formatter

**Files:**
- Modify: `src/formatter.py`
- Create: `tests/test_formatter.py`

**Step 1: Write tests for new formatter**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && pytest tests/test_formatter.py -v`
Expected: FAIL (format_telegram_message signature changed)

**Step 3: Implement new formatter**

```python
# src/formatter.py
"""Formateador de mensajes para Telegram."""

from config.settings import DAY_NAMES
from src.search import RouteResult
from src.url_builder import skyscanner_url, trainline_url


MONTH_NAMES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "sep", 10: "oct", 11: "nov", 12: "dic"
}


def format_telegram_message(mad_result: RouteResult, ovd_result: RouteResult) -> str:
    """
    Formatea el mensaje completo para Telegram.

    Args:
        mad_result: Resultado de búsqueda MAD↔BCN
        ovd_result: Resultado de búsqueda OVD↔BCN

    Returns:
        Mensaje formateado para Telegram
    """
    week_start = mad_result.week_start
    month_name = MONTH_NAMES.get(week_start.month, str(week_start.month))

    lines = [
        f"✈️ VUELOS BCN - Semana del {week_start.day} {month_name}",
        "",
    ]

    # Sección MAD ↔ BCN
    lines.append("🛫 MADRID ↔ BARCELONA")
    lines.extend(_format_route_section(mad_result, include_single_legs=True))
    lines.append("")

    # Sección OVD ↔ BCN
    lines.append("🛫 OVIEDO ↔ BARCELONA")
    lines.extend(_format_route_section(ovd_result, include_single_legs=False))
    lines.append("")

    # Enlace a Trainline (solo MAD↔BCN)
    trainline = trainline_url("MAD", "BCN")
    if trainline:
        lines.append("🚄 Compara trenes MAD↔BCN (iryo/OUIGO/AVE):")
        lines.append(f"   🔗 {trainline}")

    return "\n".join(lines)


def _format_route_section(result: RouteResult, include_single_legs: bool) -> list[str]:
    """Formatea una sección de ruta."""
    lines = []

    if result.best_combo:
        combo = result.best_combo
        out_day = DAY_NAMES[combo.outbound_date.weekday()]
        ret_day = DAY_NAMES[combo.return_date.weekday()]

        lines.append(f"   Mejor combo: {combo.total_price:.0f}€")
        lines.append(f"   {out_day} {combo.outbound_date.day} → {ret_day} {combo.return_date.day}")
        lines.append(
            f"   {combo.outbound.origin}→{combo.outbound.destination} "
            f"{combo.outbound.departure_time_str} ({combo.outbound.carrier_name}) "
            f"{combo.outbound.price:.0f}€"
        )
        lines.append(
            f"   {combo.return_flight.origin}→{combo.return_flight.destination} "
            f"{combo.return_flight.departure_time_str} ({combo.return_flight.carrier_name}) "
            f"{combo.return_flight.price:.0f}€"
        )

        # URL del combo
        url = skyscanner_url(
            result.origin, result.destination,
            combo.outbound_date, combo.return_date
        )
        lines.append(f"   🔗 {url}")

        if result.relaxed_filters:
            lines.append("   ⚠️ Horarios ampliados (sin opciones en horario ideal)")
    else:
        lines.append("   Sin opciones disponibles")

    # Single legs (solo si está habilitado para esta ruta)
    if include_single_legs:
        if result.best_outbound:
            out = result.best_outbound
            out_day = DAY_NAMES[out.flight_date.weekday()]
            lines.append("")
            lines.append(
                f"   📤 Ida suelta: {out.price:.0f}€ "
                f"{out_day} {out.flight_date.day} {out.departure_time_str} ({out.carrier_name})"
            )
            url = skyscanner_url(result.origin, result.destination, out.flight_date)
            lines.append(f"   🔗 {url}")

        if result.best_return:
            ret = result.best_return
            ret_day = DAY_NAMES[ret.flight_date.weekday()]
            lines.append("")
            lines.append(
                f"   📥 Vuelta suelta: {ret.price:.0f}€ "
                f"{ret_day} {ret.flight_date.day} {ret.departure_time_str} ({ret.carrier_name})"
            )
            url = skyscanner_url(result.destination, result.origin, ret.flight_date)
            lines.append(f"   🔗 {url}")

    return lines
```

**Step 4: Run test to verify it passes**

Run: `source venv/bin/activate && pytest tests/test_formatter.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/formatter.py tests/test_formatter.py
git commit -m "refactor(formatter): new message format with Skyscanner/Trainline URLs"
```

---

## Task 6: Actualizar main.py

**Files:**
- Modify: `src/main.py`

**Step 1: Update main.py**

```python
# src/main.py
"""Punto de entrada principal del buscador de vuelos."""

import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Añadir el directorio raíz al path para imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config.settings import WEEKS_AHEAD, ROUTES
from src.amadeus_client import AmadeusClient
from src.formatter import format_telegram_message
from src.search import FlightSearcher, RouteResult
from src.telegram import TelegramClient

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def save_log(mad_result: RouteResult, ovd_result: RouteResult, log_dir: Path) -> None:
    """Guarda el resultado en un archivo de log."""
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"search_{timestamp}.log"

    with open(log_file, "w") as f:
        f.write(f"Búsqueda realizada: {datetime.now().isoformat()}\n")
        f.write(f"Semana objetivo: {mad_result.week_start}\n\n")

        for result in [mad_result, ovd_result]:
            f.write(f"--- {result.origin} ↔ {result.destination} ---\n")
            f.write(f"Filtros relajados: {result.relaxed_filters}\n")
            if result.best_combo:
                f.write(f"Mejor combo: {result.best_combo.total_price:.0f}€\n")
                f.write(f"  Ida: {result.best_combo.outbound.origin}→{result.best_combo.outbound.destination} ")
                f.write(f"{result.best_combo.outbound.departure_time_str} {result.best_combo.outbound.price:.0f}€\n")
                f.write(f"  Vuelta: {result.best_combo.return_flight.origin}→{result.best_combo.return_flight.destination} ")
                f.write(f"{result.best_combo.return_flight.departure_time_str} {result.best_combo.return_flight.price:.0f}€\n")
            if result.best_outbound:
                f.write(f"Mejor ida suelta: {result.best_outbound.price:.0f}€\n")
            if result.best_return:
                f.write(f"Mejor vuelta suelta: {result.best_return.price:.0f}€\n")
            f.write("\n")

    logger.info(f"Log guardado en {log_file}")


def main() -> int:
    """Función principal."""
    logger.info("Iniciando búsqueda de vuelos BCN")

    try:
        # Inicializar clientes
        amadeus = AmadeusClient()
        telegram = TelegramClient()
        searcher = FlightSearcher(client=amadeus)

        # Calcular fecha objetivo
        target_date = date.today() + timedelta(weeks=WEEKS_AHEAD)
        logger.info(f"Buscando para semana del {target_date}")

        # Buscar cada ruta
        mad_result = searcher.search_route("MAD", "BCN", target_date)
        ovd_result = searcher.search_route("OVD", "BCN", target_date)

        # Guardar log
        log_dir = ROOT_DIR / "logs"
        save_log(mad_result, ovd_result, log_dir)

        # Formatear y enviar mensaje
        message = format_telegram_message(mad_result, ovd_result)
        logger.info(f"Mensaje a enviar:\n{message}")

        success = telegram.send_message(message)

        if success:
            logger.info("Proceso completado correctamente")
            return 0
        else:
            logger.error("Error enviando mensaje a Telegram")
            return 1

    except Exception as e:
        logger.exception(f"Error crítico: {e}")

        try:
            telegram = TelegramClient()
            telegram.send_error_alert(str(e))
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Run all tests**

Run: `source venv/bin/activate && pytest tests/ -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add src/main.py
git commit -m "refactor(main): simplify flow with two independent route searches"
```

---

## Task 7: Test de integración manual

**Step 1: Run the application**

Run: `source venv/bin/activate && python src/main.py`

Expected:
- Logs mostrando búsquedas para MAD↔BCN y OVD↔BCN
- Mensaje formateado en consola
- Error de Telegram (si no hay credenciales configuradas) - esto es OK para el test

**Step 2: Verify message format**

Check that the output contains:
- Header with week date
- MAD ↔ BARCELONA section with combo and/or single legs
- OVD ↔ BARCELONA section with combo only
- Trainline link at the bottom
- Skyscanner URLs for each flight option

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete refactor of flight search

- Remove train logic (Amadeus Self-Service doesn't support trains)
- Two independent routes: MAD↔BCN and OVD↔BCN
- Single legs only for MAD (to combine with train)
- Skyscanner URLs for flight booking
- Trainline URL for train comparison
- Parametrizable: arrival time, departure time, single leg threshold"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Update settings | `config/settings.py`, `tests/test_settings.py` |
| 2 | Create URL builder | `src/url_builder.py`, `tests/test_url_builder.py` |
| 3 | Simplify Amadeus client | `src/amadeus_client.py`, `tests/test_amadeus_client.py` |
| 4 | New search logic | `src/search.py`, `tests/test_search.py` |
| 5 | New formatter | `src/formatter.py`, `tests/test_formatter.py` |
| 6 | Update main | `src/main.py` |
| 7 | Integration test | Manual verification |

**Estimated commits:** 7
**Test files created:** 5
