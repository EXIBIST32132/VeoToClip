import tempfile
import unittest
from pathlib import Path

import numpy as np

from libs.schemas import BallInteraction, BoundingBox, FrameReference, TrackObservation
from libs.video_io.visualization import (
    FrameOverlayContext,
    compute_interaction_zone,
    render_debug_frame,
    write_overlay_video,
)


class VisualizationSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.frame_ref = FrameReference(frame_index=120, timestamp_s=4.8)
        self.player_track = TrackObservation(
            track_id="player-7",
            entity="player",
            frame=self.frame_ref,
            bbox=BoundingBox(x=20, y=10, width=24, height=40),
            confidence=0.91,
            source_detection_confidence=0.93,
        )
        self.ball_track = TrackObservation(
            track_id="ball-1",
            entity="ball",
            frame=self.frame_ref,
            bbox=BoundingBox(x=30, y=38, width=8, height=8),
            confidence=0.88,
            source_detection_confidence=0.88,
        )

    def test_compute_interaction_zone_biases_toward_ball(self) -> None:
        center, radius = compute_interaction_zone(self.player_track.bbox, self.ball_track.bbox, radius_px=36)
        self.assertEqual(radius, 36)
        self.assertGreater(center[1], 35)
        self.assertGreater(center[0], 25)

    def test_render_debug_frame_draws_tracks_zones_and_interactions(self) -> None:
        frame = np.zeros((72, 96, 3), dtype=np.uint8)
        context = FrameOverlayContext(
            frame_ref=self.frame_ref,
            selected_track_id=self.player_track.track_id,
            selected_identity_confidence=0.82,
            track_confidences={self.player_track.track_id: 0.82},
            track_histories={self.player_track.track_id: [(18, 18), (24, 28), (32, 40)]},
            interaction_track_ids=frozenset({self.player_track.track_id}),
            possession_state="controlled_by_target",
        )
        interaction = BallInteraction(
            interaction_id="touch-1",
            player_track_id=self.player_track.track_id,
            frame=self.frame_ref,
            label="touch",
            confidence=0.77,
            reasons=["ball_inside_zone"],
        )

        rendered = render_debug_frame(
            frame,
            [self.player_track, self.ball_track],
            context=context,
            interactions=[interaction],
        )

        self.assertEqual(rendered.shape, frame.shape)
        self.assertGreater(int(rendered.sum()), 0)
        self.assertFalse(np.array_equal(rendered, frame))

    def test_write_overlay_video_creates_artifact(self) -> None:
        frames = [np.zeros((48, 64, 3), dtype=np.uint8) for _ in range(3)]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "overlay.avi"
            written = write_overlay_video(output_path, frames, frame_rate=10.0, codec="MJPG")
            self.assertEqual(written, output_path)
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
