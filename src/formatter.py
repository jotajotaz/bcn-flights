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
        mad_result: Resultado de busqueda MAD<->BCN
        ovd_result: Resultado de busqueda OVD<->BCN

    Returns:
        Mensaje formateado para Telegram
    """
    week_start = mad_result.week_start
    month_name = MONTH_NAMES.get(week_start.month, str(week_start.month))

    lines = [
        f"✈️ VUELOS BCN - Semana del {week_start.day} {month_name}",
        "",
    ]

    # Seccion MAD <-> BCN
    lines.append("🛫 MADRID ↔ BARCELONA")
    lines.extend(_format_route_section(mad_result, include_single_legs=True))
    lines.append("")

    # Seccion OVD <-> BCN
    lines.append("🛫 OVIEDO ↔ BARCELONA")
    lines.extend(_format_route_section(ovd_result, include_single_legs=False))
    lines.append("")

    # Enlace a Trainline (solo MAD<->BCN)
    trainline = trainline_url("MAD", "BCN")
    if trainline:
        lines.append("🚄 Compara trenes MAD↔BCN (iryo/OUIGO/AVE):")
        lines.append(f"   🔗 {trainline}")

    return "\n".join(lines)


def _format_route_section(result: RouteResult, include_single_legs: bool) -> list[str]:
    """Formatea una seccion de ruta."""
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

    # Single legs (solo si esta habilitado para esta ruta)
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
