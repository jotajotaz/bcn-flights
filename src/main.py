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
from src.search import FlightSearcher, SearchResult
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


def save_log(result: SearchResult, log_dir: Path) -> None:
    """Guarda el resultado en un archivo de log."""
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"search_{timestamp}.log"

    with open(log_file, "w") as f:
        f.write(f"Búsqueda realizada: {datetime.now().isoformat()}\n")
        f.write(f"Semana objetivo: {result.week_start}\n")
        f.write(f"Filtros relajados: {result.relaxed_filters}\n")
        f.write(f"Opciones encontradas: {len(result.options)}\n")
        f.write("\n--- TOP OPCIONES ---\n\n")

        for i, opt in enumerate(result.options[:10], 1):
            f.write(f"{i}. {opt.total_price:.0f}€ - {opt}\n")
            f.write(f"   Ida: {opt.outbound.origin}→{opt.outbound.destination} ")
            f.write(f"{opt.outbound.departure_time_str} ({opt.outbound.transport_type}) ")
            f.write(f"{opt.outbound.price:.0f}€\n")
            f.write(f"   Vuelta: {opt.return_flight.origin}→{opt.return_flight.destination} ")
            f.write(f"{opt.return_flight.departure_time_str} ({opt.return_flight.transport_type}) ")
            f.write(f"{opt.return_flight.price:.0f}€\n\n")

        if result.errors:
            f.write("\n--- ERRORES ---\n\n")
            for error in result.errors:
                f.write(f"- {error}\n")

    logger.info(f"Log guardado en {log_file}")


def main() -> int:
    """Función principal."""
    logger.info("Iniciando búsqueda de vuelos BCN")

    try:
        # Inicializar clientes
        amadeus = AmadeusClient()
        telegram = TelegramClient()
        searcher = FlightSearcher(client=amadeus)

        # Calcular fecha objetivo (dentro de WEEKS_AHEAD semanas)
        target_date = date.today() + timedelta(weeks=WEEKS_AHEAD)
        logger.info(f"Buscando para semana del {target_date}")

        # Realizar búsqueda
        result = searcher.search_week(target_date)

        # Guardar log
        log_dir = ROOT_DIR / "logs"
        save_log(result, log_dir)

        # Formatear y enviar mensaje
        message = format_telegram_message(result)
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

        # Intentar enviar alerta por Telegram
        try:
            telegram = TelegramClient()
            telegram.send_error_alert(str(e))
        except Exception:
            pass

        return 1


if __name__ == "__main__":
    sys.exit(main())
