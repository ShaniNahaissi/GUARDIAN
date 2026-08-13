import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sms_service import (
    can_send_sms,
    get_target_recipients_for_camera,
    normalize_phone_list,
    normalize_phone_number,
    send_sms_webhook,
)


class TestSmsService(unittest.IsolatedAsyncioTestCase):
    def test_normalize_israeli_phone_numbers(self):
        self.assertEqual(normalize_phone_number("0501234567"), "+972501234567")
        self.assertEqual(normalize_phone_number("054-987-6543"), "+972549876543")
        self.assertEqual(normalize_phone_number("972521112233"), "+972521112233")
        self.assertEqual(normalize_phone_number("+972501234567"), "+972501234567")
        self.assertEqual(normalize_phone_number("031234567"), "+97231234567")
        self.assertEqual(normalize_phone_number(""), "")

    def test_normalize_phone_list(self):
        raw = "050-123-4567, 0529876543; +12025550123"
        normalized = normalize_phone_list(raw)
        self.assertEqual(normalized, ["+972501234567", "+972529876543", "+12025550123"])

    def test_cooldown_rate_limiting(self):
        cam_id = "test_cooldown_cam_99"
        self.assertTrue(can_send_sms(cam_id))
        # Immediate subsequent call within 2 seconds should return False
        self.assertFalse(can_send_sms(cam_id))

    @patch("sms_service.SessionLocal")
    async def test_strict_routing_owner_only(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        mock_cam = MagicMock()
        mock_cam.primaryPhone = "0501234567"
        mock_cam.additionalPhone = ""
        mock_session.get.return_value = mock_cam

        recipients = await get_target_recipients_for_camera("CAM-001")
        self.assertEqual(recipients, ["+972501234567"])

    @patch("sms_service.SessionLocal")
    async def test_strict_routing_additional_only(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        mock_cam = MagicMock()
        mock_cam.primaryPhone = ""
        mock_cam.additionalPhone = "0529876543, 0541112222"
        mock_session.get.return_value = mock_cam

        recipients = await get_target_recipients_for_camera("CAM-002")
        self.assertEqual(recipients, ["+972529876543", "+972541112222"])

    @patch("sms_service.SessionLocal")
    async def test_strict_routing_both_owner_and_additional(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        mock_cam = MagicMock()
        mock_cam.primaryPhone = "0501234567"
        mock_cam.additionalPhone = "0529876543"
        mock_session.get.return_value = mock_cam

        recipients = await get_target_recipients_for_camera("CAM-003")
        self.assertEqual(recipients, ["+972501234567", "+972529876543"])

    @patch("sms_service._post_webhook_sync", return_value=True)
    async def test_send_sms_webhook_dispatches_http(self, mock_post):
        with patch.dict(os.environ, {"SMS_WEBHOOK_URL": "http://localhost:9999/webhook"}):
            ok = await send_sms_webhook(["+972501234567"], "Test Alert", {"camera_id": "CAM-001"})
            self.assertTrue(ok)
            mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
