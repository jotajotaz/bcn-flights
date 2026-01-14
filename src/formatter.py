"""Formateador de mensajes para Telegram."""

from config.settings import DAY_NAMES, DAY_PAIRS, TOP_OPTIONS_TO_SHOW
from src.search import SearchResult, TripOption


def format_trip_option(option: TripOption, rank: int) -> str:
    """Formatea una opción de viaje para el mensaje."""
    medals = {1: "🥇 MEJOR OPCIÓN", 2: "🥈 Segunda", 3: "🥉 Tercera"}
    medal = medals.get(rank, f"#{rank}")

    outbound = option.outbound
    return_flight = option.return_flight

    outbound_day = DAY_NAMES[option.outbound_date.weekday()]
    return_day = DAY_NAMES[option.return_date.weekday()]

    lines = [
        f"{medal}: {option.total_price:.0f}€",
        f"   {outbound_day} {option.outbound_date.day} → {return_day} {option.return_date.day}",
        f"   {outbound.origin}→{outbound.destination} {outbound.departure_time_str} ({outbound.transport_type}) {outbound.price:.0f}€",
        f"   {return_flight.origin}→{return_flight.destination} {return_flight.departure_time_str} ({return_flight.transport_type}) {return_flight.price:.0f}€",
    ]

    return "\n".join(lines)


def format_day_summary(result: SearchResult) -> str:
    """Formatea el resumen por par de días."""
    best_by_day = result.get_best_by_day_pair()

    parts = []
    for day_pair in DAY_PAIRS:
        day1 = DAY_NAMES[day_pair[0]][0]  # Primera letra
        day2 = DAY_NAMES[day_pair[1]][0]

        option = best_by_day.get(day_pair)
        if option:
            parts.append(f"{day1}-{day2}: desde {option.total_price:.0f}€")
        else:
            parts.append(f"{day1}-{day2}: -")

    return " | ".join(parts)


def find_best_days(result: SearchResult) -> str:
    """Encuentra el mejor par de días."""
    if not result.options:
        return "Sin datos"

    best = result.best_option
    day1 = DAY_NAMES[best.outbound_date.weekday()]
    day2 = DAY_NAMES[best.return_date.weekday()]

    return f"{day1}-{day2}"


def format_telegram_message(result: SearchResult) -> str:
    """Formatea el mensaje completo para Telegram."""
    if not result.options:
        return (
            f"⚠️ VUELOS BCN - Semana del {result.week_start.day} "
            f"{_month_name(result.week_start.month)}\n\n"
            "No se encontraron opciones con los filtros configurados.\n\n"
            + ("\n".join(result.errors) if result.errors else "")
        )

    lines = [
        f"✈️ VUELOS BCN - Semana del {result.week_start.day} {_month_name(result.week_start.month)}",
        "",
    ]

    # Aviso si se relajaron los filtros
    if result.relaxed_filters:
        lines.append("⚠️ Sin opciones en horario estricto, mostrando horarios ampliados")
        lines.append("")

    # Top opciones
    for i, option in enumerate(result.options[:TOP_OPTIONS_TO_SHOW], 1):
        lines.append(format_trip_option(option, i))
        lines.append("")

    # Resumen por días
    lines.append("📊 Resumen por días:")
    lines.append(f"   {format_day_summary(result)}")
    lines.append("")

    # Recomendación
    lines.append(f"💡 Mejor día: {find_best_days(result)}")

    # Errores (si los hay)
    if result.errors:
        lines.append("")
        lines.append(f"⚠️ Hubo {len(result.errors)} errores durante la búsqueda")

    return "\n".join(lines)


def _month_name(month: int) -> str:
    """Retorna el nombre abreviado del mes en español."""
    months = {
        1: "ene", 2: "feb", 3: "mar", 4: "abr",
        5: "may", 6: "jun", 7: "jul", 8: "ago",
        9: "sep", 10: "oct", 11: "nov", 12: "dic"
    }
    return months.get(month, str(month))
