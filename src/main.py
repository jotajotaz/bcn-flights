"""Punto de entrada principal del buscador de vuelos."""

import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Añadir el directorio raíz al path para imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config.settings import WEEKS_AHEAD
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

    with open(log_file, "w", encoding="utf-8") as f:
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
        # Inicializar cliente de búsqueda
        amadeus = AmadeusClient()
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

        # Formatear mensaje
        message = format_telegram_message(mad_result, ovd_result)
        logger.info(f"Mensaje a enviar:\n{message}")

        # Enviar por Telegram
        try:
            telegram = TelegramClient()
            success = telegram.send_message(message)
        except ValueError as e:
            logger.warning(f"Telegram no configurado: {e}")
            logger.info("El mensaje se ha generado pero no se ha enviado")
            return 0

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
        except Exception as alert_error:
            logger.warning(f"No se pudo enviar alerta a Telegram: {alert_error}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
