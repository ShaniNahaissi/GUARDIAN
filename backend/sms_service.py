from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

from sqlalchemy import select

from dal.database import SessionLocal
from models.camera import Camera
from models.user import User

logger = logging.getLogger("guardian.sms")

_last_sent_timestamp: dict[str, float] = {}
_cooldown_lock = threading.Lock()


def get_cooldown_seconds() -> float:
    try:
        return float(os.environ.get("SMS_COOLDOWN_SECONDS", "2"))
    except ValueError:
        return 2.0


def normalize_phone_number(raw: str) -> str:
    """Normalizes phone numbers, with specific rules for Israeli phone numbers:
    - 0501234567 / 054-123-4567 -> +972501234567 / +972541234567
    - +9720503533040 -> +972503533040
    - 972501234567 -> +972501234567
    - 031234567 -> +97231234567
    - Numbers already starting with '+' are sanitized to retain valid digits.
    """
    if not raw:
        return ""

    s = raw.strip()
    if not s:
        return ""

    # Keep leading + if present
    has_plus = s.startswith("+")
    # Remove non-digit characters
    digits = re.sub(r"\D", "", s)
    if not digits:
        return ""

    # Strip redundant leading zero after country code 972 (e.g. 972050... -> 97250...)
    if digits.startswith("9720"):
        digits = "972" + digits[4:]

    # Israeli local number starting with '0' (e.g., 0501234567, 039876543)
    if s.startswith("0") or (not has_plus and digits.startswith("0")):
        return f"+972{digits[1:]}"

    # Israeli number starting with 972 without +
    if not has_plus and digits.startswith("972"):
        return f"+{digits}"

    # If it had a +, format with +
    if has_plus:
        return f"+{digits}"

    # Standard fallback
    return f"+{digits}"


def normalize_phone_list(raw_input: str | list[str] | None) -> list[str]:
    """Splits and normalizes multiple phone numbers (separated by comma, semicolon, or newline)."""
    if not raw_input:
        return []

    if isinstance(raw_input, str):
        parts = re.split(r"[,;\n]+", raw_input)
    else:
        parts = raw_input

    result: list[str] = []
    for p in parts:
        norm = normalize_phone_number(p)
        if norm and norm not in result:
            result.append(norm)
    return result


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


def _send_twilio_sms_sync(to_phone: str, message: str) -> bool:
    """Dispatches SMS text message directly to Twilio REST API / Client SDK."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.environ.get("TWILIO_FROM_NUMBER", "+972539508482").strip()

    if not account_sid or not auth_token:
        logger.warning("sms.twilio_missing_credentials account_sid_present=%s", bool(account_sid))
        return False

    # 1. Try official Twilio SDK if available
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            to=to_phone,
            from_=from_number,
            body=message,
        )
        logger.info("sms.twilio_sdk_success sid=%s to=%s", getattr(msg, "sid", "sent"), to_phone)
        return True
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("sms.twilio_sdk_error to=%s error=%s, attempting direct REST fallback", to_phone, exc)

    # 2. Zero-dependency direct Twilio REST API fallback via urllib
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    post_data = urllib.parse.urlencode({
        "To": to_phone,
        "From": from_number,
        "Body": message,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=post_data, method="POST")
    creds = f"{account_sid}:{auth_token}"
    encoded_creds = base64.b64encode(creds.encode("utf-8")).decode("utf-8")
    req.add_header("Authorization", f"Basic {encoded_creds}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body_res = resp.read().decode("utf-8")
            logger.info("sms.twilio_rest_success to=%s status=%s body=%s", to_phone, resp.status, body_res[:100])
            return 200 <= resp.status < 300
    except Exception as exc:
        logger.error("sms.twilio_rest_error to=%s error=%s", to_phone, exc)
        return False


async def send_sms_twilio(recipients: list[str], message: str) -> bool:
    """Dispatches SMS alert to all recipients via Twilio."""
    results: list[bool] = []
    for phone in recipients:
        success = await asyncio.to_thread(_send_twilio_sms_sync, phone, message)
        results.append(success)
    return any(results)


def _post_webhook_sync(url: str, payload: dict[str, Any]) -> bool:
    """Synchronous HTTP POST helper for generic SMS Webhooks."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Guardian-SMS/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        logger.warning("sms.webhook_post_failed url=%s error=%s", url, exc)
        return False


async def send_sms_webhook(recipients: list[str], message: str, metadata: dict[str, Any]) -> bool:
    """Dispatches SMS alert via generic SMS Webhook if SMS_WEBHOOK_URL is configured."""
    webhook_url = os.environ.get("SMS_WEBHOOK_URL", "").strip()
    if not webhook_url:
        logger.info("sms.dispatch_simulated recipients=%s message=%s", recipients, message)
        return True

    payload = {
        "to": recipients,
        "message": message,
        "timestamp": time.time(),
        "metadata": metadata,
    }

    success = await asyncio.to_thread(_post_webhook_sync, webhook_url, payload)
    if success:
        logger.info("sms.dispatch_success webhook=%s recipients=%s", webhook_url, recipients)
    else:
        logger.error("sms.dispatch_error webhook=%s recipients=%s", webhook_url, recipients)
    return success


async def get_target_recipients_for_camera(camera_id: str) -> list[str]:
    """Strict Camera Routing Rules:
    - Owner only -> send exclusively to Owner phone.
    - Additional only -> send to all Additional phones.
    - Both Owner & Additional -> send to all of them.
    - If camera has neither -> fallback to querying all system User phone numbers in DB.
    """
    async with SessionLocal() as session:
        camera = await session.get(Camera, camera_id)
        owner_raw = getattr(camera, "primaryPhone", "") or "" if camera else ""
        additional_raw = getattr(camera, "additionalPhone", "") or "" if camera else ""

        owner_phones = normalize_phone_list(owner_raw)
        additional_phones = normalize_phone_list(additional_raw)

        # 1. Owner only
        if owner_phones and not additional_phones:
            return owner_phones

        # 2. Additional only
        if additional_phones and not owner_phones:
            return additional_phones

        # 3. Both Owner & Additional
        if owner_phones and additional_phones:
            combined = list(owner_phones)
            for p in additional_phones:
                if p not in combined:
                    combined.append(p)
            return combined

        # 4. Fallback: Query system users in DB if camera has no numbers configured
        res = await session.execute(select(User))
        users = res.scalars().all()

        fallback_recipients: list[str] = []
        for u in users:
            for p in (u.primary_phone, u.additional_phone):
                norm_list = normalize_phone_list(p)
                for norm in norm_list:
                    if norm not in fallback_recipients:
                        fallback_recipients.append(norm)

        return fallback_recipients


async def dispatch_threat_sms(camera_id: str, camera_name: str, threat_type: str, confidence: float) -> None:
    """Main threat alert dispatcher. Evaluates cooldown, resolves target phone numbers,
    and sends SMS directly via Twilio (or Webhook as fallback)."""
    if not can_send_sms(camera_id):
        logger.debug("sms.cooldown_active camera_id=%s threat=%s", camera_id, threat_type)
        return

    recipients = await get_target_recipients_for_camera(camera_id)
    if not recipients:
        logger.info("sms.no_recipients camera_id=%s threat=%s", camera_id, threat_type)
        return

    display_name = camera_name or camera_id
    conf_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
    msg = f"🚨 GUARDIAN ALERT: Active threat '{threat_type}' ({conf_pct}%) detected on camera '{display_name}' ({camera_id})!"

    meta = {
        "camera_id": camera_id,
        "camera_name": camera_name,
        "threat_type": threat_type,
        "confidence": confidence,
    }

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()

    if account_sid and auth_token:
        await send_sms_twilio(recipients, msg)
    else:
        await send_sms_webhook(recipients, msg, meta)
