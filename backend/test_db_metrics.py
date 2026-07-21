import unittest
from unittest.mock import AsyncMock, patch, MagicMock

from bl.metrics_service import save_metrics_to_db


class TestDBMetrics(unittest.IsolatedAsyncioTestCase):
    @patch("bl.metrics_service.SessionLocal")
    async def test_save_metrics_to_db(self, mock_session_local):
        # Create mock session
        mock_session = AsyncMock()
        # Configure async context manager so 'async with SessionLocal() as session:' returns mock_session
        mock_session_local.return_value.__aenter__.return_value = mock_session
        
        # Configure execute to return a synchronous MagicMock result object
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (15.0, 10.0)
        mock_session.execute.return_value = mock_result
        
        stream_id = "test-stream"
        
        await save_metrics_to_db(
            stream_id=stream_id,
            frame_seq=2,
            total_latency_ms=20.0,
            yolo_latency_ms=12.0,
            detections_count=1,
            track_count=1,
            detections_json=[{"track_id": 1, "class_name": "Suspect", "confidence": 0.85}],
            cpu_utilization=18.0,
            gpu_vram_used=510,
            evaluated_sequences=[{
                "track_id": 1,
                "start_frame_seq": 1,
                "end_frame_seq": 2,
                "action_label": "Shooting",
                "action_confidence": 0.95,
                "best_frame_seq": 1,
                "best_frame_score": 0.9,
            }]
        )
        
        # Assert SessionLocal was instantiated
        mock_session_local.assert_called_once()
        
        # Check that session.add was called for both FrameMetric and SequenceMetric
        self.assertEqual(mock_session.add.call_count, 2)
        
        # Check calls
        added_objs = [call.args[0] for call in mock_session.add.call_args_list]
        
        # Verify first added is FrameMetric
        frame_metric = added_objs[0]
        self.assertEqual(frame_metric.stream_id, stream_id)
        self.assertEqual(frame_metric.frame_seq, 2)
        self.assertEqual(frame_metric.total_latency_ms, 20.0)
        self.assertEqual(frame_metric.cpu_utilization, 18.0)
        
        # Verify second added is SequenceMetric
        seq_metric = added_objs[1]
        self.assertEqual(seq_metric.stream_id, stream_id)
        self.assertEqual(seq_metric.action_label, "Shooting")
        self.assertEqual(seq_metric.action_confidence, 0.95)
        self.assertEqual(seq_metric.avg_total_latency_ms, 15.0)
        self.assertEqual(seq_metric.avg_yolo_latency_ms, 10.0)
        
        # Verify commit was called
        mock_session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
