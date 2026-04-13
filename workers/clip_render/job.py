from libs.schemas import WorkerCapability


def describe_capability() -> WorkerCapability:
    return WorkerCapability(
        name="clip_render",
        responsibilities=[
            "Render preview and final clips",
            "Attach export metadata sidecars",
            "Build optional compilation reels",
        ],
        phase_targets=["phase-5", "phase-6"],
    )
