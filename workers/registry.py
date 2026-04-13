"""Worker capability registry for scaffold inspection and future orchestration."""

from libs.schemas import WorkerCapability
from workers.clip_render.job import describe_capability as clip_render_capability
from workers.detection_tracking.job import describe_capability as detection_capability
from workers.identity_lock.job import describe_capability as identity_capability
from workers.ingest.job import describe_capability as ingest_capability
from workers.possession_inference.job import describe_capability as possession_capability


def build_worker_registry() -> list[WorkerCapability]:
    return [
        ingest_capability(),
        detection_capability(),
        identity_capability(),
        possession_capability(),
        clip_render_capability(),
    ]
