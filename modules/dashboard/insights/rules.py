"""Regras de insights automáticos."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InsightLevel(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    DANGER = "danger"


@dataclass
class Insight:
    message: str
    level: InsightLevel = InsightLevel.INFO


CONCENTRATION_THRESHOLD = 0.4
WIN_RATE_GATE = 0.40
WIN_RATE_IMPROVEMENT_PP = 0.05
