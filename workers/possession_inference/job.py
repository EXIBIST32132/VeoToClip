from libs.schemas import WorkerCapability


def describe_capability() -> WorkerCapability:
    return WorkerCapability(
        name="possession_inference",
        responsibilities=[
            "Infer touches and controlled interactions",
            "Segment possession intervals",
            "Emit clip candidate intervals with confidence",
        ],
        phase_targets=["phase-4", "phase-5"],
    )
