import unittest

from apps.api.main import build_manifest
from scripts.validate_scaffold import validate


class ProjectLayoutTest(unittest.TestCase):
    def test_scaffold_validation_passes(self) -> None:
        self.assertEqual(validate(), [])

    def test_manifest_lists_expected_workers(self) -> None:
        worker_names = [worker["name"] for worker in build_manifest()["workers"]]
        self.assertEqual(
            worker_names,
            [
                "ingest",
                "detection_tracking",
                "identity_lock",
                "possession_inference",
                "clip_render",
            ],
        )


if __name__ == "__main__":
    unittest.main()
