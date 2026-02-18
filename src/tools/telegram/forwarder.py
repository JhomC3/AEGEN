import json
import logging
import urllib.request

logger = logging.getLogger("polling_service")


def forward_to_local_api(update: dict, api_url: str) -> bool:
    """Reenvía update a la API local usando urllib (conexión local, no necesita persistencia)."""
    update_id = update.get("update_id")
    try:
        req = urllib.request.Request(
            api_url,
            data=json.dumps(update).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            if resp.status in (200, 202):
                logger.info(f"✅ Update {update_id} -> API Local: OK")
                return True
            logger.warning(f"❌ Update {update_id} -> API Local: Status {resp.status}")
            return False
    except Exception as e:
        logger.warning(f"❌ Update {update_id} -> API Local: {e}")
        return False
