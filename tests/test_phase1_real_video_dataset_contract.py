from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "FootballVideos"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}


class Phase1RealVideoDatasetContractTest(unittest.TestCase):
    def test_football_videos_directory_exists(self) -> None:
        self.assertTrue(
            VIDEO_DIR.exists(),
            "Phase 1 requires a FootballVideos/ directory with real match footage.",
        )
        self.assertTrue(VIDEO_DIR.is_dir(), "FootballVideos/ must be a directory.")

    def test_real_match_videos_are_present_and_non_empty(self) -> None:
        video_files = sorted(
            path for path in VIDEO_DIR.iterdir() if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        )
        self.assertGreaterEqual(
            len(video_files),
            2,
            "Phase 1 requires at least two real match videos in FootballVideos/.",
        )
        for video_file in video_files:
            self.assertGreater(
                video_file.stat().st_size,
                0,
                f"Video file is empty: {video_file.name}",
            )


if __name__ == "__main__":
    unittest.main()
