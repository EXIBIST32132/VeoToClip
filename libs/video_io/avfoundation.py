"""AVFoundation-backed video loading for local macOS development."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import AVFoundation
import CoreMedia
import Quartz
import numpy as np
from Foundation import NSURL

from libs.schemas import FrameReference, VideoAsset


def _slugify(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")


@dataclass(slots=True)
class VideoFrame:
    """Decoded frame payload emitted by the frame provider."""

    reference: FrameReference
    image: np.ndarray


class AVFoundationFrameProvider:
    """Decode `.mp4` assets through native macOS AVFoundation APIs.

    The provider is optimized for sequential frame access, which matches the
    tracking pipeline's sampled sweep over a full match.
    """

    def __init__(self) -> None:
        self._asset = None
        self._video_track = None
        self._video: VideoAsset | None = None
        self._reader = None
        self._reader_output = None

    @property
    def video(self) -> VideoAsset:
        if self._video is None:
            msg = "Video source has not been opened yet."
            raise RuntimeError(msg)
        return self._video

    def open(self, source: Path) -> VideoAsset:
        source = source.expanduser().resolve()
        if not source.exists():
            msg = f"Video source does not exist: {source}"
            raise FileNotFoundError(msg)

        url = NSURL.fileURLWithPath_(str(source))
        asset = AVFoundation.AVURLAsset.URLAssetWithURL_options_(url, None)
        video_tracks = asset.tracksWithMediaType_(AVFoundation.AVMediaTypeVideo)
        if not video_tracks:
            msg = f"No video track found in source: {source}"
            raise ValueError(msg)

        video_track = video_tracks[0]
        frame_rate = float(video_track.nominalFrameRate()) or 30.0
        duration = asset.duration()
        duration_s = float(duration.value / duration.timescale) if duration.timescale else 0.0
        natural_size = video_track.naturalSize()

        self._asset = asset
        self._video_track = video_track
        self._video = VideoAsset(
            asset_id=_slugify(source.stem),
            source_path=str(source),
            frame_rate=frame_rate,
            duration_s=duration_s,
            width=int(natural_size.width),
            height=int(natural_size.height),
        )
        self.close()
        return self.video

    def close(self) -> None:
        if self._reader is not None:
            self._reader.cancelReading()
        self._reader = None
        self._reader_output = None

    def read_frame(self, frame_index: int) -> tuple[FrameReference, np.ndarray]:
        if frame_index < 0:
            msg = "frame_index must be non-negative"
            raise ValueError(msg)

        sampled = self.iter_frames(start_frame=frame_index, max_frames=1)
        try:
            frame = next(sampled)
        except StopIteration as exc:
            msg = f"Frame index {frame_index} is outside the available range."
            raise IndexError(msg) from exc
        return frame.reference, frame.image

    def iter_frames(
        self,
        *,
        start_frame: int = 0,
        frame_step: int = 1,
        max_frames: int | None = None,
    ) -> Iterator[VideoFrame]:
        if frame_step <= 0:
            msg = "frame_step must be >= 1"
            raise ValueError(msg)
        if start_frame < 0:
            msg = "start_frame must be non-negative"
            raise ValueError(msg)

        reader, output = self._build_reader()
        yielded = 0
        source_index = -1
        try:
            while True:
                sample_buffer = output.copyNextSampleBuffer()
                if sample_buffer is None:
                    break
                source_index += 1
                if source_index < start_frame:
                    continue
                if (source_index - start_frame) % frame_step != 0:
                    continue

                reference, image = self._decode_sample(source_index, sample_buffer)
                yield VideoFrame(reference=reference, image=image)
                yielded += 1
                if max_frames is not None and yielded >= max_frames:
                    break
        finally:
            reader.cancelReading()

    def sample_frames(
        self,
        *,
        sample_fps: float,
        start_time_s: float = 0.0,
        max_frames: int | None = None,
    ) -> Iterator[VideoFrame]:
        if sample_fps <= 0:
            msg = "sample_fps must be > 0"
            raise ValueError(msg)
        frame_step = max(1, round(self.video.frame_rate / sample_fps))
        start_frame = max(0, round(start_time_s * self.video.frame_rate))
        return self.iter_frames(start_frame=start_frame, frame_step=frame_step, max_frames=max_frames)

    def _build_reader(self):
        if self._asset is None or self._video_track is None:
            msg = "open() must be called before building a reader."
            raise RuntimeError(msg)

        self.close()
        reader, error = AVFoundation.AVAssetReader.alloc().initWithAsset_error_(self._asset, None)
        if reader is None:
            msg = f"Failed to create AVAssetReader: {error}"
            raise RuntimeError(msg)

        settings = {
            Quartz.kCVPixelBufferPixelFormatTypeKey: Quartz.kCVPixelFormatType_32BGRA,
        }
        output = AVFoundation.AVAssetReaderTrackOutput.alloc().initWithTrack_outputSettings_(
            self._video_track,
            settings,
        )
        output.setAlwaysCopiesSampleData_(False)
        if not reader.canAddOutput_(output):
            msg = "AVAssetReader cannot add the configured track output."
            raise RuntimeError(msg)
        reader.addOutput_(output)
        if not reader.startReading():
            msg = f"AVAssetReader failed to start: {reader.error()}"
            raise RuntimeError(msg)

        self._reader = reader
        self._reader_output = output
        return reader, output

    def _decode_sample(
        self,
        frame_index: int,
        sample_buffer,
    ) -> tuple[FrameReference, np.ndarray]:
        pts = CoreMedia.CMSampleBufferGetPresentationTimeStamp(sample_buffer)
        timestamp_s = float(pts.value / pts.timescale) if pts.timescale else 0.0
        pixel_buffer = CoreMedia.CMSampleBufferGetImageBuffer(sample_buffer)

        Quartz.CVPixelBufferLockBaseAddress(pixel_buffer, 0)
        try:
            width = Quartz.CVPixelBufferGetWidth(pixel_buffer)
            height = Quartz.CVPixelBufferGetHeight(pixel_buffer)
            bytes_per_row = Quartz.CVPixelBufferGetBytesPerRow(pixel_buffer)
            base_address = Quartz.CVPixelBufferGetBaseAddress(pixel_buffer)
            if base_address is None:
                msg = "Could not access pixel buffer base address."
                raise RuntimeError(msg)

            array = np.frombuffer(
                base_address.as_buffer(bytes_per_row * height),
                dtype=np.uint8,
            )
            array = array.reshape((height, bytes_per_row // 4, 4))[:, :width, :]
            # Convert BGRA into RGB to match torchvision's expected input.
            rgb = np.ascontiguousarray(array[:, :, :3][:, :, ::-1])
        finally:
            Quartz.CVPixelBufferUnlockBaseAddress(pixel_buffer, 0)

        reference = FrameReference(frame_index=frame_index, timestamp_s=timestamp_s)
        return reference, rgb
