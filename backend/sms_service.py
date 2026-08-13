from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import urllib.request
from typing import Any

logger = logging.getLogger("guardian.sms")

_last_sent_timestamp: dict[str, float] = {}
_cooldown_lock = threading.Lock()


def get_cooldown_seconds() -> float:
    try:
        return float(os.environ.get("SMS_COOLDOWN_SECONDS", "2"))
    except ValueError:
        return 2.0


def can_send_sms(camera_id: str) -> bool:
    """Enforces per-camera cooldown rate limiting (default: 2 seconds)."""
    cooldown = get_cooldown_seconds()
    now = time.time()
    with _cooldown_lock:
        last_sent = _last_sent_timestamp.get(camera_id, 0.0)
        if now - last_sent < cooldown:
            return False
        _last_sent_timestamp[camera_id] = now
        return True


def _send_telegram_sync(token: str, chat_id: str, message: str) -> bool:
    """Dispatches instant Telegram Bot push notification to chat_id."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info("sms.telegram_success chat_id=%s status=%s", chat_id, resp.status)
            return 200 <= resp.status < 300
    except Exception as exc:
        logger.error("sms.telegram_error chat_id=%s error=%s", chat_id, exc)
        return False


async def send_telegram_alert(message: str) -> bool:
    """Async wrapper for Telegram alert dispatching."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.warning("sms.telegram_missing_config token_present=%s chat_id_present=%s", bool(token), bool(chat_id))
        return False
    return await asyncio.to_thread(_send_telegram_sync, token, chat_id, message)


async def dispatch_threat_sms(camera_id: str, camera_name: str, threat_type: str, confidence: float) -> None:
    """Main threat alert dispatcher. Evaluates 2-second per-camera cooldown and dispatches instant Telegram push notification."""
    if not can_send_sms(camera_id):
        logger.debug("sms.cooldown_active camera_id=%s threat=%s", camera_id, threat_type)
        return

    display_name = camera_name or camera_id
    conf_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
    msg = f"🚨 GUARDIAN ALERT: Active threat '{threat_type}' ({conf_pct}%) detected on camera '{display_name}' ({camera_id})!"

    success = await send_telegram_alert(msg)
    if success:
        logger.info("sms.dispatch_success type=telegram camera_id=%s threat=%s", camera_id, threat_type)
    else:
        logger.warning("sms.dispatch_failed type=telegram camera_id=%s threat=%s", camera_id, threat_type)
