# src/tools/telegram/forwarder.py
# ruff: noqa: S310
import json
import logging
import urllib.request

logger = logging.getLogger("polling")


def forward_to_local_api(update: dict, api_url: str) -> bool:
    """Reenvía update."""
    try:
        data = json.dumps(update).encode("utf-8")
        h = {"Content-Type": "application/json"}
        req = urllib.request.Request(api_url, data=data, headers=h, method="POST")  # noqa: S310
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return resp.status in (200, 202)
    except Exception:
        return False
