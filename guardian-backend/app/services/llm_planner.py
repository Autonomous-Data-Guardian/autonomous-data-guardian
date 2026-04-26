from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.models.request_models import AnalyzeChangeRequest
from app.services.openrouter_client import OpenRouterClient, OpenRouterError


class LlmPlannerError(RuntimeError):
    """Raised when LLM planning fails or returns invalid output."""


class LlmPlannerRateLimitError(LlmPlannerError):
    """Raised when provider rate limits the LLM request."""


class LlmRiskPlan(BaseModel):
    """Structured LLM output used for summary, recommendations, and risk delta."""

    summary: str = Field(min_length=1)
    recommendations: list[str] = Field(min_length=3)
    riskAdjustment: int = Field(ge=-15, le=15)
    adjustmentRationale: str = Field(min_length=1)


class LlmPlannerService:
    """Generates summary/recommendations and risk adjustments using an LLM."""

    def __init__(self, openrouter_client: OpenRouterClient) -> None:
        self._openrouter_client = openrouter_client

    async def build_summary_and_plan(
        self,
        request: AnalyzeChangeRequest,
        base_risk_level: str,
        base_risk_score: int,
        affected_assets: list[str],
        factors: list[str],
        owner_governance_gaps: list[str],
    ) -> LlmRiskPlan:
        """Generate structured analysis from OpenRouter output."""
        system_prompt = (
            "You are a data governance risk assistant. "
            "Return strict JSON with keys: summary, recommendations, riskAdjustment, adjustmentRationale. "
            "riskAdjustment must be an integer between -15 and 15. "
            "recommendations must be a short ordered list of concrete migration-safety steps."
        )
        user_payload: dict[str, Any] = {
            "intent": request.intent,
            "assetFqn": request.assetFqn,
            "changeType": request.changeType,
            "columnName": request.columnName,
            "newColumnName": request.newColumnName,
            "newColumnType": request.newColumnType,
            "baseRiskScore": base_risk_score,
            "baseRiskLevel": base_risk_level,
            "triggeredFactors": factors,
            "affectedAssets": affected_assets,
            "ownerGovernanceGaps": owner_governance_gaps,
        }

        try:
            raw_text = await self._openrouter_client.create_chat_completion(
                system_prompt=system_prompt,
                user_prompt=json.dumps(user_payload),
            )
            parsed = json.loads(raw_text)
            return LlmRiskPlan.model_validate(parsed)
        except (OpenRouterError, json.JSONDecodeError, ValidationError) as error:
            if "429" in str(error):
                raise LlmPlannerRateLimitError(f"LLM planning rate limited: {error}") from error
            raise LlmPlannerError(f"LLM planning failed: {error}") from error

    def build_rate_limited_fallback_plan(
        self,
        request: AnalyzeChangeRequest,
        base_risk_level: str,
        base_risk_score: int,
        factors: list[str],
    ) -> LlmRiskPlan:
        """Build deterministic fallback when LLM provider is rate-limited."""
        summary = (
            f"Intent '{request.intent}' analyzed with deterministic risk model because LLM provider is currently rate-limited. "
            f"Base risk is {base_risk_level} ({base_risk_score}). Triggered factors: {', '.join(factors) if factors else 'none'}."
        )
        recommendations = [
            "Retry AI explanation in a few minutes after rate limit resets.",
            "Review impacted downstream assets before applying changes.",
            "Run a staging migration and validate data quality checks before production rollout.",
        ]
        return LlmRiskPlan(
            summary=summary,
            recommendations=recommendations,
            riskAdjustment=0,
            adjustmentRationale="No AI adjustment applied due to provider rate limit.",
        )
