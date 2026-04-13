"""Benchmark and metric interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from libs.schemas import EvaluationMetricSpec


@dataclass(slots=True)
class BenchmarkCase:
    case_id: str
    video_path: Path
    annotation_path: Path
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MetricResult:
    metric_name: str
    value: float
    unit: str
    notes: list[str] = field(default_factory=list)


class EvaluationRunner(Protocol):
    name: str
    metrics: list[EvaluationMetricSpec]

    def run(self, case: BenchmarkCase) -> list[MetricResult]:
        ...
