"""Configuración del buscador de vuelos BCN."""

import os
from dataclasses import dataclass
from datetime import time


@dataclass
class Route:
    """Representa una ruta origen-destino."""
    origin: str
    destination: str
    name: str


# Aeropuertos
MADRID = "MAD"
BARCELONA = "BCN"
ASTURIAS = "OVD"

# Rutas a buscar (ida)
OUTBOUND_ROUTES = [
    Route(MADRID, BARCELONA, "MAD→BCN"),
    Route(ASTURIAS, BARCELONA, "OVD→BCN"),
]

# Rutas a buscar (vuelta)
RETURN_ROUTES = [
    Route(BARCELONA, MADRID, "BCN→MAD"),
    Route(BARCELONA, ASTURIAS, "BCN→OVD"),
]

# Combinaciones completas de ida y vuelta
ROUTE_COMBINATIONS = [
    (Route(MADRID, BARCELONA, "MAD→BCN"), Route(BARCELONA, MADRID, "BCN→MAD")),
    (Route(MADRID, BARCELONA, "MAD→BCN"), Route(BARCELONA, ASTURIAS, "BCN→OVD")),
    (Route(ASTURIAS, BARCELONA, "OVD→BCN"), Route(BARCELONA, ASTURIAS, "BCN→OVD")),
    (Route(ASTURIAS, BARCELONA, "OVD→BCN"), Route(BARCELONA, MADRID, "BCN→MAD")),
]

# Pares de días (día de ida, día de vuelta)
# 0 = Lunes, 1 = Martes, etc.
DAY_PAIRS = [
    (0, 1),  # Lunes-Martes
    (1, 2),  # Martes-Miércoles
    (2, 3),  # Miércoles-Jueves
    (3, 4),  # Jueves-Viernes
]

DAY_NAMES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DAY_NAMES_FULL = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Filtros de horario
MAX_ARRIVAL_TIME = time(10, 0)  # Llegar antes de las 10:00
MIN_DEPARTURE_TIME = time(17, 0)  # Salir después de las 17:00

# Filtros de horario relajados (si no hay opciones)
MAX_ARRIVAL_TIME_RELAXED = time(11, 0)
MIN_DEPARTURE_TIME_RELAXED = time(16, 0)

# Filtros de precio
MIN_PRICE = 1  # Filtrar precios de 0€ (errores)
MAX_PRICE = 500  # Filtrar precios anómalos

# Configuración de búsqueda
WEEKS_AHEAD = 2  # Buscar para dentro de 2 semanas
MAX_RESULTS_PER_SEARCH = 10  # Resultados por búsqueda de Amadeus
TOP_OPTIONS_TO_SHOW = 3  # Mostrar top 3 en Telegram

# Reintentos
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# API Keys (desde variables de entorno)
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
