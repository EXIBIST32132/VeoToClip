"""Sweep-oriented baseline for selected-player identity requests."""

from __future__ import annotations

from libs.schemas import WorkerCapability
from workers.identity_lock.sweep import (
    BaselineIdentitySweepBuilder,
    PlayerSweepReport,
    PlayerSweepRequest,
    PlayerTrackSummary,
)


def describe_capability() -> WorkerCapability:
    return WorkerCapability(
        name="identity_lock",
        responsibilities=[
            "Enumerate player tracks for selected-player sweep testing",
            "Produce explicit baseline identity confidence summaries",
            "Prepare per-player possession and clip-generation run requests",
        ],
        phase_targets=["phase-1", "phase-3"],
    )


__all__ = [
    "BaselineIdentitySweepBuilder",
    "PlayerSweepReport",
    "PlayerSweepRequest",
    "PlayerTrackSummary",
    "describe_capability",
]
