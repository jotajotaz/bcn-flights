"""Cliente de Telegram para enviar notificaciones."""

import logging
import time

import requests

from config.settings import (
    MAX_RETRIES,
    RETRY_DELAY_SECONDS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

logger = logging.getLogger(__name__)


class TelegramClient:
    """Cliente para enviar mensajes por Telegram."""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or TELEGRAM_CHAT_ID

        if not self.token or not self.chat_id:
            raise ValueError(
                "Faltan credenciales de Telegram. "
                "Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID"
            )

        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str) -> bool:
        """
        Envía un mensaje de texto.

        Args:
            text: Texto del mensaje (máximo 4096 caracteres)

        Returns:
            True si se envió correctamente
        """
        # Telegram tiene un límite de 4096 caracteres
        if len(text) > 4096:
            logger.warning("Mensaje muy largo, truncando...")
            text = text[:4090] + "\n..."

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",  # Permite formato básico
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(url, json=payload, timeout=30)
                response.raise_for_status()

                result = response.json()
                if result.get("ok"):
                    logger.info("Mensaje enviado correctamente")
                    return True
                else:
                    logger.error(f"Error de Telegram: {result}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Intento {attempt}/{MAX_RETRIES} falló: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_SECONDS)

        logger.error("No se pudo enviar el mensaje después de todos los intentos")
        return False

    def send_error_alert(self, error_message: str) -> bool:
        """Envía una alerta de error."""
        text = f"🔴 ERROR en buscador de vuelos BCN\n\n{error_message}"
        return self.send_message(text)
