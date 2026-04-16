"""Detection, tracking contracts, and Phase 1 baseline implementations."""

from .baseline import (
    DetectorConfig,
    IoUTracker,
    TorchvisionCocoDetector,
    TrackerConfig,
    TrackingRunConfig,
    TrackingRunResult,
    run_tracking_pass,
    write_tracking_run,
)

__all__ = [
    "DetectorConfig",
    "IoUTracker",
    "TorchvisionCocoDetector",
    "TrackerConfig",
    "TrackingRunConfig",
    "TrackingRunResult",
    "run_tracking_pass",
    "write_tracking_run",
]
