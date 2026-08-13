import asyncio
import os
import unittest
from unittest.mock import patch

from sms_service import (
    can_send_sms,
    send_telegram_alert,
)


class TestSmsService(unittest.IsolatedAsyncioTestCase):
    def test_cooldown_rate_limiting(self):
        cam_id = "test_cooldown_cam_99"
        self.assertTrue(can_send_sms(cam_id))
        # Immediate subsequent call within 2 seconds should return False
        self.assertFalse(can_send_sms(cam_id))

    @patch("sms_service._send_telegram_sync", return_value=True)
    async def test_send_telegram_alert(self, mock_sync):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123:ABC", "TELEGRAM_CHAT_ID": "456"}):
            ok = await send_telegram_alert("🚨 Test Alert")
            self.assertTrue(ok)
            mock_sync.assert_called_once_with("123:ABC", "456", "🚨 Test Alert")


if __name__ == "__main__":
    unittest.main()
