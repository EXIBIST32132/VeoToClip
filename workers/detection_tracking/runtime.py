"""Minimal real-video detection + tracking runtime for Bot A validation."""

from __future__ import annotations

import argparse
from pathlib import Path

from libs.tracking.baseline import TrackingRunConfig, run_tracking_pass, write_tracking_run


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Path to a football match video.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where JSON tracking artifacts should be written.",
    )
    parser.add_argument("--sample-fps", type=float, default=2.0, help="Frame sampling rate.")
    parser.add_argument("--start-time-s", type=float, default=0.0, help="Start time in seconds.")
    parser.add_argument("--max-frames", type=int, default=None, help="Cap the sampled frame count.")
    parser.add_argument(
        "--model-name",
        default="ssdlite320_mobilenet_v3_large",
        choices=["ssdlite320_mobilenet_v3_large", "fasterrcnn_mobilenet_v3_large_320_fpn"],
        help="Torchvision detector backbone.",
    )
    parser.add_argument(
        "--player-threshold",
        type=float,
        default=0.15,
        help="Minimum confidence for player detections.",
    )
    parser.add_argument(
        "--ball-threshold",
        type=float,
        default=0.10,
        help="Minimum confidence for ball detections.",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    config = TrackingRunConfig(
        sample_fps=args.sample_fps,
        start_time_s=args.start_time_s,
        max_frames=args.max_frames,
    )
    config.detector.model_name = args.model_name
    config.detector.player_confidence_threshold = args.player_threshold
    config.detector.ball_confidence_threshold = args.ball_threshold

    result = run_tracking_pass(args.video, config=config)
    paths = write_tracking_run(result, output_dir=args.output_dir)

    print(f"Processed {result.video_asset['source_path']}")
    print(f"Sampled frames: {result.sampled_frames}")
    print(f"Unique player tracks: {result.summary['unique_player_tracks']}")
    print(f"Unique ball tracks: {result.summary['unique_ball_tracks']}")
    print(f"Summary: {paths['summary']}")
    print(f"Track frames: {paths['track_frames']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
