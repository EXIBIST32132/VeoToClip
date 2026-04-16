"""Video IO contracts and AVFoundation-backed implementations."""

from .avfoundation import AVFoundationFrameProvider, VideoFrame

__all__ = ["AVFoundationFrameProvider", "VideoFrame"]
