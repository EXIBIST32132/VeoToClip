import json
import shutil
import tempfile
import unittest
from pathlib import Path

from libs.evaluation import SweepReportWriter
from libs.evaluation.reporting import PlayerSweepInput
from libs.identity.interfaces import IdentityAssignment, IdentityCandidate, IdentityCueScores
from libs.schemas import (
    BallInteraction,
    BoundingBox,
    ClipCandidate,
    FrameReference,
    PossessionSegment,
    TrackObservation,
    VideoAsset,
)


def _make_track_observation(track_id: str, frame_index: int, timestamp_s: float) -> TrackObservation:
    return TrackObservation(
        track_id=track_id,
        entity="player",
        frame=FrameReference(frame_index=frame_index, timestamp_s=timestamp_s),
        bbox=BoundingBox(x=10.0, y=20.0, width=25.0, height=60.0),
        confidence=0.9,
        source_detection_confidence=0.92,
    )


def _make_identity_assignment(state: str, confidence: float, visibility: float) -> IdentityAssignment:
    cue_scores = IdentityCueScores(
        tracker_continuity=0.9,
        appearance_similarity=0.8,
        team_color_similarity=0.95,
        motion_consistency=0.75,
        visibility_confidence=visibility,
    )
    return IdentityAssignment(
        selected_track_id="track-1" if state != "LOST" else None,
        state=state,
        confidence=confidence,
        visibility_confidence=visibility,
        margin_to_runner_up=0.2 if state != "LOST" else None,
        cue_scores=cue_scores if state != "LOST" else None,
        alternates=[
            IdentityCandidate(
                track_id="track-alt",
                score=0.6,
                confidence=0.55,
                cue_scores=cue_scores,
            )
        ],
    )


class SweepReportWriterIntegrationTest(unittest.TestCase):
    def _make_temp_dir(self) -> Path:
        base_dir = Path("artifacts/test_runs")
        base_dir.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(dir=base_dir))

    def test_writer_emits_per_player_and_summary_reports(self) -> None:
        video = VideoAsset(
            asset_id="video-1",
            source_path="FootballVideos/Match One.mp4",
            frame_rate=25.0,
            duration_s=120.0,
            width=1920,
            height=1080,
        )
        player_inputs = [
            PlayerSweepInput(
                player_track_id="track-1",
                track_observations=[
                    _make_track_observation("track-1", 100, 4.0),
                    _make_track_observation("track-1", 101, 4.04),
                    _make_track_observation("track-1", 102, 4.08),
                ],
                identity_assignments=[
                    _make_identity_assignment("LOCKED", 0.86, 0.7),
                    _make_identity_assignment("LOCKED", 0.82, 0.72),
                    _make_identity_assignment("UNCERTAIN", 0.61, 0.5),
                ],
                interactions=[
                    BallInteraction(
                        interaction_id="i-1",
                        player_track_id="track-1",
                        frame=FrameReference(frame_index=100, timestamp_s=4.0),
                        label="touch",
                        confidence=0.74,
                        reasons=["ball_near_feet"],
                    ),
                    BallInteraction(
                        interaction_id="i-2",
                        player_track_id="track-1",
                        frame=FrameReference(frame_index=101, timestamp_s=4.04),
                        label="dribble",
                        confidence=0.69,
                        reasons=["temporal_hold"],
                    ),
                ],
                possession_segments=[
                    PossessionSegment(
                        segment_id="seg-1",
                        player_track_id="track-1",
                        start_time_s=4.0,
                        end_time_s=6.0,
                        confidence=0.71,
                        end_reason="controller_switch",
                        interaction_ids=["i-1", "i-2"],
                    )
                ],
                clips=[
                    ClipCandidate(
                        clip_id="clip-1",
                        source_asset_id=video.asset_id,
                        segment_id="seg-1",
                        start_time_s=3.0,
                        end_time_s=6.5,
                        confidence=0.79,
                        reason="controlled_first_touch",
                    )
                ],
                debug_artifact_paths=[Path("artifacts/debug_videos/video-1_track-1.mp4")],
                preview_artifact_paths=[Path("artifacts/previews/video-1_track-1_clip-1.mp4")],
            ),
            PlayerSweepInput(
                player_track_id="track-2",
                track_observations=[],
                identity_assignments=[],
                interactions=[],
                possession_segments=[],
                clips=[],
                failure_flags=["ball_track_missing"],
            ),
        ]

        temp_dir = self._make_temp_dir()
        try:
            writer = SweepReportWriter(temp_dir)
            written = writer.write_video_report(video, player_inputs)

            self.assertTrue(written.summary_path.exists())
            self.assertEqual(sorted(written.player_report_paths), ["track-1", "track-2"])

            player_payload = json.loads(written.player_report_paths["track-1"].read_text(encoding="utf-8"))
            self.assertEqual(player_payload["player_track_id"], "track-1")
            self.assertEqual(player_payload["total_frames_visible"], 3)
            self.assertEqual(player_payload["number_of_detected_touches"], 2)
            self.assertEqual(player_payload["number_of_generated_clips"], 1)
            self.assertEqual(player_payload["identity_confidence_summary"]["state_counts"]["LOCKED"], 2)
            self.assertEqual(player_payload["clip_intervals"][0]["duration_s"], 3.5)

            failed_payload = json.loads(written.player_report_paths["track-2"].read_text(encoding="utf-8"))
            self.assertIn("ball_track_missing", failed_payload["failure_flags"])
            self.assertIn("no_clips_generated", failed_payload["failure_flags"])
            self.assertIn("missing_identity_results", failed_payload["failure_flags"])

            summary_payload = json.loads(written.summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary_payload["video_asset_id"], "video-1")
            self.assertEqual(summary_payload["total_players_tested"], 2)
            self.assertEqual(summary_payload["players_with_generated_clips"], 1)
            self.assertEqual(summary_payload["total_generated_clips"], 1)
            self.assertEqual(summary_payload["player_report_paths"]["track-1"], "players/track-1.json")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_writer_emits_cross_video_aggregate_summary(self) -> None:
        first_video = VideoAsset(
            asset_id="video-1",
            source_path="FootballVideos/Match One.mp4",
            frame_rate=25.0,
            duration_s=120.0,
            width=1920,
            height=1080,
        )
        second_video = VideoAsset(
            asset_id="video-2",
            source_path="FootballVideos/Match Two.mp4",
            frame_rate=25.0,
            duration_s=130.0,
            width=1920,
            height=1080,
        )

        temp_dir = self._make_temp_dir()
        try:
            writer = SweepReportWriter(temp_dir)
            first_written = writer.write_video_report(
                first_video,
                [
                    PlayerSweepInput(
                        player_track_id="track-1",
                        track_observations=[_make_track_observation("track-1", 1, 0.04)],
                        identity_assignments=[_make_identity_assignment("LOCKED", 0.8, 0.7)],
                        interactions=[],
                        possession_segments=[],
                        clips=[],
                    )
                ],
            )
            second_written = writer.write_video_report(
                second_video,
                [
                    PlayerSweepInput(
                        player_track_id="track-9",
                        track_observations=[_make_track_observation("track-9", 10, 0.4)],
                        identity_assignments=[_make_identity_assignment("UNCERTAIN", 0.55, 0.45)],
                        interactions=[
                            BallInteraction(
                                interaction_id="i-9",
                                player_track_id="track-9",
                                frame=FrameReference(frame_index=10, timestamp_s=0.4),
                                label="touch",
                                confidence=0.66,
                                reasons=["candidate_contact"],
                            )
                        ],
                        possession_segments=[
                            PossessionSegment(
                                segment_id="seg-9",
                                player_track_id="track-9",
                                start_time_s=0.4,
                                end_time_s=2.0,
                                confidence=0.64,
                                end_reason="timeout",
                                interaction_ids=["i-9"],
                            )
                        ],
                        clips=[
                            ClipCandidate(
                                clip_id="clip-9",
                                source_asset_id=second_video.asset_id,
                                segment_id="seg-9",
                                start_time_s=0.2,
                                end_time_s=2.0,
                                confidence=0.67,
                                reason="touch_window",
                            )
                        ],
                    )
                ],
            )

            aggregate_path = writer.write_aggregate_report([first_written, second_written])
            self.assertTrue(aggregate_path.exists())

            aggregate_payload = json.loads(aggregate_path.read_text(encoding="utf-8"))
            self.assertEqual(aggregate_payload["total_videos_processed"], 2)
            self.assertEqual(aggregate_payload["total_players_tested"], 2)
            self.assertEqual(aggregate_payload["total_generated_clips"], 1)
            self.assertEqual(aggregate_payload["videos_with_failures"], 1)
            self.assertEqual(len(aggregate_payload["per_video_summaries"]), 2)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
