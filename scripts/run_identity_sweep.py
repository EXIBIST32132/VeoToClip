"""Run the Phase 1 baseline identity sweep over enumerated player tracks.

Input JSON shape:

{
  "video": {
    "asset_id": "match-1"
  },
  "tracks": [
    {
      "track_id": "player-1",
      "entity": "player",
      "confidence": 0.88,
      "source_detection_confidence": 0.90,
      "frame": {"frame_index": 10, "timestamp_s": 0.4},
      "bbox": {"x": 100, "y": 220, "width": 40, "height": 120},
      "metadata": {"team_color": "red"}
    }
  ]
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libs.schemas import BoundingBox, ClipBoundaryRule, FrameReference, TrackObservation
from workers.identity_lock import BaselineIdentitySweepBuilder


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path, help="tracking export JSON")
    parser.add_argument(
        "--output",
        type=Path,
        help="optional output path for the sweep report JSON",
    )
    parser.add_argument(
        "--asset-id",
        help="override source asset id if the JSON does not provide one",
    )
    parser.add_argument(
        "--min-visible-frames",
        type=int,
        default=3,
        help="minimum player frames before a sweep entry is flagged",
    )
    return parser.parse_args()


def _build_observation(payload: dict[str, object]) -> TrackObservation:
    frame_payload = payload["frame"]
    bbox_payload = payload["bbox"]
    return TrackObservation(
        track_id=str(payload["track_id"]),
        entity=str(payload["entity"]),
        frame=FrameReference(
            frame_index=int(frame_payload["frame_index"]),
            timestamp_s=float(frame_payload["timestamp_s"]),
        ),
        bbox=BoundingBox(
            x=float(bbox_payload["x"]),
            y=float(bbox_payload["y"]),
            width=float(bbox_payload["width"]),
            height=float(bbox_payload["height"]),
        ),
        confidence=float(payload["confidence"]),
        source_detection_confidence=float(payload["source_detection_confidence"]),
        metadata={str(key): str(value) for key, value in payload.get("metadata", {}).items()},
    )


def _source_asset_id(document: dict[str, object], override: str | None) -> str:
    if override:
        return override
    video_payload = document.get("video", {})
    asset_id = video_payload.get("asset_id") if isinstance(video_payload, dict) else None
    if asset_id:
        return str(asset_id)
    return "unknown-asset"


def main() -> int:
    args = _parse_args()
    document = json.loads(args.input_json.read_text())
    asset_id = _source_asset_id(document, args.asset_id)
    observations = [_build_observation(item) for item in document.get("tracks", [])]

    builder = BaselineIdentitySweepBuilder(
        source_asset_id=asset_id,
        clip_boundary_rule=ClipBoundaryRule(),
        min_visible_frames=args.min_visible_frames,
    )
    reports = builder.build(observations)
    payload = {
        "source_asset_id": asset_id,
        "player_count": len(reports),
        "reports": [report.to_dict() for report in reports],
    }
    output_text = json.dumps(payload, indent=2, sort_keys=True)

    if args.output:
        args.output.write_text(output_text + "\n")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
