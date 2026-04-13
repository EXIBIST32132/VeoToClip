from libs.schemas import WorkerCapability


def describe_capability() -> WorkerCapability:
    return WorkerCapability(
        name="ingest",
        responsibilities=[
            "Register input video assets",
            "Probe media metadata",
            "Emit canonical project manifests",
        ],
        phase_targets=["phase-1", "phase-2"],
    )
