from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RiskLevel = Literal["Low", "Medium", "High", "Critical"]


@dataclass
class RiskInputs:
    """Normalized booleans/counts consumed by deterministic risk scoring."""

    has_downstream_dashboard: bool
    has_sensitive_tag: bool
    has_downstream_table_or_pipeline: bool
    is_owner_missing: bool
    is_description_missing: bool
    has_recent_data_quality_failure: bool
    has_many_downstream_dependencies: bool
    is_glossary_missing: bool


def map_risk_level(score: int) -> RiskLevel:
    """Map deterministic score to discrete risk level."""
    if score <= 30:
        return "Low"
    if score <= 60:
        return "Medium"
    if score <= 80:
        return "High"
    return "Critical"


def calculate_risk_score(inputs: RiskInputs) -> tuple[int, RiskLevel, list[str]]:
    """Calculate deterministic score and collect triggered factors."""
    score = 0
    factors: list[str] = []

    if inputs.has_downstream_dashboard:
        score += 30
        factors.append("downstream_dashboard")
    if inputs.has_sensitive_tag:
        score += 25
        factors.append("sensitive_tag")
    if inputs.has_downstream_table_or_pipeline:
        score += 20
        factors.append("downstream_table_or_pipeline")
    if inputs.is_owner_missing:
        score += 15
        factors.append("owner_missing")
    if inputs.is_description_missing:
        score += 15
        factors.append("description_missing")
    if inputs.has_recent_data_quality_failure:
        score += 20
        factors.append("recent_data_quality_failure")
    if inputs.has_many_downstream_dependencies:
        score += 10
        factors.append("many_downstream_dependencies")
    if inputs.is_glossary_missing:
        score += 10
        factors.append("glossary_missing")

    bounded_score = max(0, min(100, score))
    return bounded_score, map_risk_level(bounded_score), factors
