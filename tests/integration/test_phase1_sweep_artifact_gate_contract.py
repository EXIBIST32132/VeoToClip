from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts"
METRICS_DIR = ARTIFACTS_DIR / "metrics"
DEBUG_DIR = ARTIFACTS_DIR / "debug_videos"
PREVIEWS_DIR = ARTIFACTS_DIR / "previews"
FP_FN_DIRS = [ARTIFACTS_DIR / "fp_gallery", ARTIFACTS_DIR / "fn_gallery"]

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
JSON_EXTENSIONS = {".json"}


def _iter_files(root: Path, suffixes: set[str]) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes and path.name != ".gitkeep"
    )


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _find_player_report_paths() -> list[Path]:
    report_paths: list[Path] = []
    for candidate in _iter_files(METRICS_DIR, JSON_EXTENSIONS):
        payload = _load_json(candidate)
        if isinstance(payload, dict) and "player_track_id" in payload:
            report_paths.append(candidate)
    return report_paths


def _find_summary_paths() -> list[Path]:
    summary_paths: list[Path] = []
    for candidate in _iter_files(METRICS_DIR, JSON_EXTENSIONS):
        payload = _load_json(candidate)
        if not isinstance(payload, dict):
            continue
        if any(
            key in payload
            for key in (
                "videos_processed",
                "total_players_tested",
                "players_with_generated_clips",
                "phase_gate",
            )
        ):
            summary_paths.append(candidate)
    return summary_paths


class Phase1SweepArtifactGateContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.player_reports = _find_player_report_paths()
        cls.summary_reports = _find_summary_paths()
        cls.debug_videos = _iter_files(DEBUG_DIR, VIDEO_EXTENSIONS)
        cls.preview_videos = _iter_files(PREVIEWS_DIR, VIDEO_EXTENSIONS)
        cls.fp_fn_assets = [
            path
            for gallery_dir in FP_FN_DIRS
            for path in _iter_files(gallery_dir, VIDEO_EXTENSIONS | {".jpg", ".jpeg", ".png"})
        ]

    def setUp(self) -> None:
        if not self.summary_reports and not self.player_reports:
            self.skipTest(
                "No Phase 1 sweep artifacts found yet. Run the real-video sweep pipeline first, then rerun this test."
            )

    def test_player_reports_are_readable_and_structured(self) -> None:
        self.assertGreaterEqual(
            len(self.player_reports),
            5,
            "Phase 1 requires readable per-player reports for at least 5 players.",
        )
        for report_path in self.player_reports:
            payload = _load_json(report_path)
            self.assertIsInstance(payload, dict, f"Player report must be a JSON object: {report_path}")
            self.assertIsInstance(payload.get("player_track_id"), str)
            self.assertGreater(payload.get("total_frames_visible", 0), 0)
            self.assertIn("identity_confidence_summary", payload)
            self.assertIn("number_of_detected_touches", payload)
            self.assertIn("number_of_generated_clips", payload)
            self.assertIn("average_clip_duration", payload)
            self.assertIn("failure_flags", payload)
            self.assertIn("confidence_metrics", payload)

            clips = payload.get("clips", [])
            self.assertIsInstance(clips, list, f"clips must be a list in {report_path}")
            for clip in clips:
                self.assertIsInstance(clip, dict, f"Each clip entry must be an object in {report_path}")
                self.assertIn("start_time_s", clip)
                self.assertIn("end_time_s", clip)
                self.assertLessEqual(clip["start_time_s"], clip["end_time_s"])

    def test_summary_reports_expose_phase_gate_inputs(self) -> None:
        self.assertGreaterEqual(len(self.summary_reports), 1, "Phase 1 requires at least one aggregate summary report.")
        aggregate_players = 0
        aggregate_clips = 0
        aggregate_videos = 0

        for report_path in self.summary_reports:
            payload = _load_json(report_path)
            self.assertIsInstance(payload, dict, f"Summary report must be a JSON object: {report_path}")
            aggregate_players += int(payload.get("total_players_tested", 0))
            aggregate_clips += int(payload.get("players_with_generated_clips", 0))
            aggregate_videos += int(payload.get("videos_processed", 0))

        self.assertGreaterEqual(aggregate_videos, 1, "At least one full video must be processed end-to-end.")
        self.assertGreaterEqual(aggregate_players, 5, "At least 5 players must be tested automatically.")
        self.assertGreaterEqual(
            aggregate_clips,
            1,
            "At least one tested player must yield generated clips for the Phase 1 gate to pass.",
        )

    def test_debug_visual_artifacts_exist(self) -> None:
        self.assertGreaterEqual(
            len(self.debug_videos),
            1,
            "Phase 1 requires at least one viewable debug overlay video.",
        )

    def test_preview_artifacts_exist(self) -> None:
        self.assertGreaterEqual(
            len(self.preview_videos),
            1,
            "Phase 1 requires at least one clip preview artifact.",
        )

    def test_fp_fn_gallery_surface_exists_when_errors_are_logged(self) -> None:
        self.assertTrue(
            all(path.exists() for path in FP_FN_DIRS),
            "Both fp_gallery and fn_gallery directories must exist.",
        )
        self.assertIsInstance(self.fp_fn_assets, list)


if __name__ == "__main__":
    unittest.main()
