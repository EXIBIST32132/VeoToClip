import unittest

from apps.api.main import build_manifest


class ManifestContractTest(unittest.TestCase):
    def test_manifest_contract_contains_docs_and_routes(self) -> None:
        manifest = build_manifest()
        self.assertEqual(manifest["phase"], "phase-0")
        self.assertIn("/health", manifest["api"]["routes"])
        self.assertIn("/manifest", manifest["api"]["routes"])
        self.assertGreaterEqual(len(manifest["docs"]), 6)
        self.assertEqual(
            manifest["architecture"]["player_tracker_primary"],
            "BoT-SORT-ReID",
        )


if __name__ == "__main__":
    unittest.main()
