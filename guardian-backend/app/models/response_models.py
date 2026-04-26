from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["Low", "Medium", "High", "Critical"]


class SearchAssetItem(BaseModel):
    """Single asset result returned from search endpoint."""

    id: str
    name: str
    fqn: str
    entityType: str
    description: str | None = None


class AnalyzeChangeResponse(BaseModel):
    """Final report payload returned after an analysis request."""

    reportId: str
    riskLevel: RiskLevel
    riskScore: int
    summary: str
    affectedAssets: list[str]
    sensitiveDataWarning: str | None
    ownerGovernanceGaps: list[str]
    triggeredFactors: list[str] = Field(default_factory=list)
    recommendations: list[str]
    createdAt: datetime


class StoredReport(AnalyzeChangeResponse):
    """Report model persisted in local storage."""

    inputSnapshot: dict
