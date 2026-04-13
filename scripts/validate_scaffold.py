"""Validate the Phase 0 scaffold layout and print a compact tree when requested."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import build_manifest

REQUIRED_PATHS = [
    ROOT / "README.md",
    ROOT / "pyproject.toml",
    ROOT / "apps" / "api" / "main.py",
    ROOT / "apps" / "web-ui" / "index.html",
    ROOT / "workers" / "registry.py",
    ROOT / "libs" / "schemas" / "core.py",
    ROOT / "libs" / "tracking" / "interfaces.py",
    ROOT / "libs" / "identity" / "interfaces.py",
    ROOT / "libs" / "possession" / "interfaces.py",
    ROOT / "libs" / "evaluation" / "interfaces.py",
    ROOT / "docs" / "phase-0" / "technical-design.md",
    ROOT / "docs" / "phase-0" / "product-requirements.md",
    ROOT / "docs" / "phase-0" / "evaluation-benchmark-plan.md",
    ROOT / "docs" / "phase-0" / "risk-register.md",
    ROOT / "docs" / "phase-0" / "final-phased-roadmap.md",
    ROOT / "docs" / "phase-0" / "sub-bot-plan.md",
    ROOT / "docs" / "phases" / "phase-1-milestone.md",
    ROOT / "docs" / "phases" / "phase-2-milestone.md",
]


def build_tree_lines() -> list[str]:
    include_roots = [
        "apps",
        "workers",
        "libs",
        "data",
        "artifacts",
        "docs",
        "scripts",
        "tests",
    ]
    lines = ["."]
    for root_name in include_roots:
        root_path = ROOT / root_name
        lines.append(f"./{root_name}")
        for path in sorted(root_path.rglob("*")):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(ROOT)
            lines.append(f"./{relative}")
    return lines


def validate() -> list[str]:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_PATHS if not path.exists()]
    manifest = build_manifest()
    worker_names = [worker["name"] for worker in manifest["workers"]]
    if len(worker_names) != len(set(worker_names)):
        missing.append("duplicate worker names in manifest")
    return missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tree", action="store_true", help="Print the scaffold tree.")
    args = parser.parse_args()

    if args.tree:
        for line in build_tree_lines():
            print(line)
        return 0

    missing = validate()
    if missing:
        print("Scaffold validation failed:")
        for item in missing:
            print(f"- {item}")
        return 1

    print("Scaffold validation passed.")
    print("Workers:", ", ".join(worker["name"] for worker in build_manifest()["workers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
