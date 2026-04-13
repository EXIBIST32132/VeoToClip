import unittest
from dataclasses import asdict

from libs.identity.interfaces import IdentityAssignment, IdentityCandidate, IdentityCueScores
from libs.schemas import (
    AnnotationBundle,
    BoundingBox,
    ClipBoundaryRule,
    ClipCandidate,
    ClipRequest,
    ExportJob,
    FrameReference,
    TargetPlayerSelection,
    TrackObservation,
    VideoAsset,
)


class ContractSmokeTest(unittest.TestCase):
    def test_selection_clip_and_export_contracts_are_serializable(self) -> None:
        video = VideoAsset(
            asset_id="video-1",
            source_path="data/samples/video-1.mp4",
            frame_rate=25.0,
            duration_s=90.0,
            width=1920,
            height=1080,
        )
        frame = FrameReference(frame_index=100, timestamp_s=4.0)
        selection = TargetPlayerSelection(
            project_id="project-1",
            mode="click",
            seed_frame=frame,
            selected_track_id="track-7",
            jersey_hint="17",
        )
        request = ClipRequest(
            request_id="clip-req-1",
            source_asset_id=video.asset_id,
            player_track_id="track-7",
            segment_id="segment-1",
            rules=ClipBoundaryRule(),
        )
        export = ExportJob(
            export_id="export-1",
            mode="batch",
            clip_ids=["clip-1", "clip-2"],
            destination_dir="artifacts/exports/project-1",
        )

        payload = {"selection": asdict(selection), "request": asdict(request), "export": asdict(export)}
        self.assertEqual(payload["selection"]["selected_track_id"], "track-7")
        self.assertEqual(payload["request"]["segment_id"], "segment-1")
        self.assertEqual(payload["export"]["mode"], "batch")

    def test_annotation_bundle_and_identity_assignment_contracts(self) -> None:
        frame = FrameReference(frame_index=100, timestamp_s=4.0)
        observation = TrackObservation(
            track_id="track-7",
            entity="player",
            frame=frame,
            bbox=BoundingBox(x=10.0, y=20.0, width=30.0, height=40.0),
            confidence=0.9,
            source_detection_confidence=0.92,
        )
        clip = ClipCandidate(
            clip_id="clip-1",
            source_asset_id="video-1",
            segment_id="segment-1",
            start_time_s=3.5,
            end_time_s=6.0,
            confidence=0.8,
            reason="controlled_first_touch",
        )
        bundle = AnnotationBundle(
            schema_version="0.1.0",
            video=VideoAsset(
                asset_id="video-1",
                source_path="data/samples/video-1.mp4",
                frame_rate=25.0,
                duration_s=90.0,
                width=1920,
                height=1080,
            ),
            tracks=[observation],
            clips=[clip],
        )
        cue_scores = IdentityCueScores(
            tracker_continuity=0.8,
            appearance_similarity=0.7,
            team_color_similarity=1.0,
            motion_consistency=0.75,
            visibility_confidence=0.6,
        )
        identity = IdentityAssignment(
            selected_track_id="track-7",
            state="LOCKED",
            confidence=0.85,
            visibility_confidence=0.6,
            margin_to_runner_up=0.2,
            cue_scores=cue_scores,
            alternates=[
                IdentityCandidate(
                    track_id="track-11",
                    score=0.65,
                    confidence=0.58,
                    cue_scores=cue_scores,
                )
            ],
        )

        self.assertEqual(bundle.tracks[0].track_id, "track-7")
        self.assertEqual(identity.state, "LOCKED")
        self.assertEqual(identity.alternates[0].track_id, "track-11")


if __name__ == "__main__":
    unittest.main()
