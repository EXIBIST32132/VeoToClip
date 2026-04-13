from libs.schemas import WorkerCapability


def describe_capability() -> WorkerCapability:
    return WorkerCapability(
        name="identity_lock",
        responsibilities=[
            "Fuse tracker, appearance, and contextual cues",
            "Maintain selected-player continuity",
            "Recover identity across occlusion and cuts",
        ],
        phase_targets=["phase-3"],
    )
