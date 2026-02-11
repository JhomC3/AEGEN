from __future__ import annotations

import http.client
import json
import logging
import ssl

logger = logging.getLogger("polling_service")

TELEGRAM_HOST = "api.telegram.org"
POLLING_TIMEOUT = 20  # Reducido a 20s para mayor margen con GCE


class PersistentTelegramClient:
    """
    Cliente HTTP con conexión TLS persistente a api.telegram.org.
    Reutiliza el socket TLS evitando el handshake costoso en cada request.
    """

    def __init__(self, token: str):
        self.token = token
        self.base_path = f"/bot{token}"
        self.conn: http.client.HTTPSConnection | None = None
        self._connect()

    def _connect(self):
        """Crea o recrea la conexión TLS persistente."""
        try:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:  # noqa: BLE001
                    pass  # nosec B110

            ctx = ssl.create_default_context()
            self.conn = http.client.HTTPSConnection(
                TELEGRAM_HOST,
                timeout=POLLING_TIMEOUT + 10,  # Timeout generoso para el socket
                context=ctx,
            )
            # Forzar el handshake TLS ahora (no lazy)
            self.conn.connect()
            logger.info("🔐 Conexión TLS persistente establecida con Telegram.")
        except Exception as e:
            logger.warning(f"Error creando conexión TLS: {e}")
            self.conn = None

    def request(self, method: str, params: dict | None = None) -> dict | None:
        """
        Realiza una petición a la API de Telegram reutilizando la conexión TLS.
        Si la conexión se pierde, la recrea automáticamente (1 solo reintento).
        """
        path = f"{self.base_path}/{method}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            path = f"{path}?{query}"

        for attempt in range(2):  # Máximo 1 reintento con reconexión
            try:
                if self.conn is None:
                    self._connect()
                    if self.conn is None:
                        return None

                self.conn.request("GET", path)
                response = self.conn.getresponse()
                data = response.read().decode()
                return json.loads(data)

            except (
                http.client.RemoteDisconnected,
                ConnectionResetError,
                BrokenPipeError,
                OSError,
            ) as e:
                if attempt == 0:
                    logger.info(
                        f"🔄 Conexión TLS perdida ({type(e).__name__}). Reconectando..."
                    )
                    self._connect()
                else:
                    logger.warning(f"Fallo de red tras reconexión: {e}")
                    return None

            except Exception as e:
                logger.warning(f"Error inesperado en request ({type(e).__name__}): {e}")
                self._connect()  # Reset conexión por seguridad
                return None

        return None

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except Exception:  # noqa: BLE001
                pass  # nosec B110
