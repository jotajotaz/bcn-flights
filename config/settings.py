"""Configuracion del buscador de vuelos BCN."""

import os
from datetime import time


# Filtros de horario (parametrizables)
MAX_ARRIVAL_TIME = time(10, 0)       # Llegada ida <= 10:00
MIN_DEPARTURE_TIME = time(17, 0)     # Salida vuelta >= 17:00
RELAXED_MARGIN_MINUTES = 60          # Margen fijo para filtros relajados

# Umbral para mostrar legs sueltos (parametrizable)
SINGLE_LEG_THRESHOLD = 45  # euros

# Rutas a buscar
ROUTES = [
    ("MAD", "BCN"),
    ("OVD", "BCN"),
]

# Rutas con opcion de legs sueltos (para combinar con tren)
ROUTES_WITH_SINGLE_LEGS = ["MAD"]

# Configuracion de busqueda
WEEKS_AHEAD = 2
MAX_RESULTS_PER_SEARCH = 10

# Pares de dias (dia de ida, dia de vuelta) - 0=Lunes
DAY_PAIRS = [
    (0, 1),  # Lunes-Martes
    (1, 2),  # Martes-Miercoles
    (2, 3),  # Miercoles-Jueves
    (3, 4),  # Jueves-Viernes
]

DAY_NAMES = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]

# Reintentos
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# API Keys (desde variables de entorno)
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY", "")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
