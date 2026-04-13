"""Phase 0 dependency-free API manifest server."""

from __future__ import annotations

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from workers.registry import build_worker_registry


def build_manifest() -> dict[str, object]:
    workers = [asdict(worker) for worker in build_worker_registry()]
    return {
        "name": "VeoToClip",
        "phase": "phase-0",
        "mode": "scaffold",
        "architecture": {
            "detector_baseline": "YOLO-family detector behind adapter",
            "player_tracker_primary": "BoT-SORT-ReID",
            "player_tracker_fallback": "ByteTrack",
            "identity_strategy": "fused scorer over short tracklets",
            "interaction_strategy": "temporal geometry state machine first, learned rescoring later",
            "storage_posture": "local-first filesystem manifests and artifacts",
        },
        "api": {
            "routes": ["/health", "/manifest"],
            "notes": "FastAPI or equivalent remains a Phase 1+ decision after evaluation harness needs settle.",
        },
        "workers": workers,
        "docs": [
            "docs/phase-0/technical-design.md",
            "docs/phase-0/product-requirements.md",
            "docs/phase-0/evaluation-benchmark-plan.md",
            "docs/phase-0/risk-register.md",
            "docs/phases/phase-1-milestone.md",
            "docs/phases/phase-2-milestone.md",
        ],
    }


class ManifestRequestHandler(BaseHTTPRequestHandler):
    """Serve a small JSON manifest without external dependencies."""

    server_version = "VeoToClipPhase0/0.1"

    def _write_json(self, payload: dict[str, object], status_code: int = 200) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802 - http.server uses camel-case method names
        path = urlparse(self.path).path
        if path == "/health":
            self._write_json({"status": "ok", "phase": "phase-0"})
            return
        if path == "/manifest":
            self._write_json(build_manifest())
            return
        self._write_json({"error": "not_found", "path": path}, status_code=404)

    def log_message(self, format: str, *args: object) -> None:
        return


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), ManifestRequestHandler)
    print(f"VeoToClip Phase 0 API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
