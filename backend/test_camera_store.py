import unittest
from unittest.mock import AsyncMock, patch, MagicMock

from bl import camera_store
from schemas.camera import CameraCreateRequest, CameraUpdateRequest


class TestCameraStore(unittest.IsolatedAsyncioTestCase):
    def _mock_session(self, mock_session_local):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        return mock_session

    @patch("bl.camera_store.SessionLocal")
    async def test_add_camera_generates_sequential_id(self, mock_session_local):
        mock_session = self._mock_session(mock_session_local)
        mock_session.scalar.return_value = 2  # 2 cameras already exist

        response = await camera_store.add_camera(CameraCreateRequest(name="Lobby"))

        self.assertEqual(response.status_code, 200)
        added = mock_session.add.call_args.args[0]
        self.assertEqual(added.id, "CAM-003")
        self.assertEqual(added.name, "Lobby")
        mock_session.commit.assert_awaited_once()

    @patch("bl.camera_store.SessionLocal")
    async def test_add_camera_uses_stream_uuid_when_given(self, mock_session_local):
        mock_session = self._mock_session(mock_session_local)

        response = await camera_store.add_camera(
            CameraCreateRequest(name="Gate", streamUuid="cam-abc")
        )

        added = mock_session.add.call_args.args[0]
        self.assertEqual(added.id, "cam-abc")
        self.assertIn("cam-abc", response.body.decode())

    @patch("bl.camera_store.SessionLocal")
    async def test_update_camera_not_found(self, mock_session_local):
        mock_session = self._mock_session(mock_session_local)
        mock_session.get.return_value = None

        response = await camera_store.update_camera("missing", CameraUpdateRequest(name="X"))

        self.assertEqual(response.status_code, 404)

    @patch("bl.camera_store.SessionLocal")
    async def test_compute_stats_counts_by_status(self, mock_session_local):
        mock_session = self._mock_session(mock_session_local)
        mock_result = MagicMock()
        mock_result.all.return_value = [("normal",), ("warning",), ("critical",), ("critical",)]
        mock_session.execute.return_value = mock_result

        stats = await camera_store.compute_stats()

        self.assertEqual(stats.activeCameras, 4)
        self.assertEqual(stats.warningAlerts, 1)
        self.assertEqual(stats.criticalAlerts, 2)
        self.assertEqual(stats.majorAlerts, 0)


if __name__ == "__main__":
    unittest.main()
