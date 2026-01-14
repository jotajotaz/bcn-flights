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
