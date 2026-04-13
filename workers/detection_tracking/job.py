from libs.schemas import WorkerCapability


def describe_capability() -> WorkerCapability:
    return WorkerCapability(
        name="detection_tracking",
        responsibilities=[
            "Run player and ball detectors",
            "Associate detections into temporal tracks",
            "Persist frame-aligned tracking outputs",
        ],
        phase_targets=["phase-2"],
    )
