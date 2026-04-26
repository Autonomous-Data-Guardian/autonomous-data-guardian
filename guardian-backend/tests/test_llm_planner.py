import asyncio
import json

import pytest

from app.models.request_models import AnalyzeChangeRequest
from app.services.llm_planner import LlmPlannerError, LlmPlannerRateLimitError, LlmPlannerService
from app.services.openrouter_client import OpenRouterError


class StubOpenRouterClient:
    """Simple stub client that returns preconfigured model content."""

    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    async def create_chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        return self._response_text


class RateLimitedOpenRouterClient:
    """Stub that mimics a provider 429 failure."""

    async def create_chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        raise OpenRouterError("Client error '429 Too Many Requests' for url 'https://openrouter.ai/api/v1/chat/completions'")


def test_llm_planner_parses_structured_output() -> None:
    """Verify planner accepts valid JSON and returns typed result."""
    response_text = json.dumps(
        {
            "summary": "Deleting this table has downstream impact and needs staged rollout.",
            "recommendations": [
                "Create a compatible replacement table first.",
                "Update dashboards and pipelines to new schema.",
                "Run data quality checks before final cutover.",
            ],
            "riskAdjustment": 5,
            "adjustmentRationale": "Downstream dependencies increase blast radius.",
        }
    )
    planner = LlmPlannerService(StubOpenRouterClient(response_text))
    request = AnalyzeChangeRequest(
        assetType="table",
        assetFqn="sample.db.schema.table_a",
        intent="drop this table",
        description="drop this table",
        changeType="DELETE_TABLE",
    )

    result = asyncio.run(
        planner.build_summary_and_plan(
            request=request,
            base_risk_level="High",
            base_risk_score=76,
            affected_assets=["table.a", "dashboard.b"],
            factors=["downstream_dashboard"],
            owner_governance_gaps=["owner_missing"],
        )
    )

    assert result.riskAdjustment == 5
    assert len(result.recommendations) == 3
    assert "staged rollout" in result.summary


def test_llm_planner_rejects_invalid_adjustment() -> None:
    """Verify planner rejects output outside allowed risk adjustment range."""
    bad_response = json.dumps(
        {
            "summary": "High risk change.",
            "recommendations": ["a", "b", "c"],
            "riskAdjustment": 42,
            "adjustmentRationale": "too high",
        }
    )
    planner = LlmPlannerService(StubOpenRouterClient(bad_response))
    request = AnalyzeChangeRequest(
        assetType="table",
        assetFqn="sample.db.schema.table_a",
        intent="rename column",
        description="rename column",
        changeType="RENAME_COLUMN",
    )

    with pytest.raises(LlmPlannerError):
        asyncio.run(
            planner.build_summary_and_plan(
                request=request,
                base_risk_level="Medium",
                base_risk_score=50,
                affected_assets=[],
                factors=[],
                owner_governance_gaps=[],
            )
        )


def test_llm_planner_raises_rate_limit_error_and_supports_fallback_plan() -> None:
    """Verify planner surfaces rate limit and deterministic fallback can be built."""
    planner = LlmPlannerService(RateLimitedOpenRouterClient())
    request = AnalyzeChangeRequest(
        assetType="table",
        assetFqn="sample.db.schema.table_a",
        intent="analyze security",
        description="analyze security",
        changeType="DELETE_COLUMN",
    )

    with pytest.raises(LlmPlannerRateLimitError):
        asyncio.run(
            planner.build_summary_and_plan(
                request=request,
                base_risk_level="High",
                base_risk_score=70,
                affected_assets=["table.a"],
                factors=["downstream_table_or_pipeline"],
                owner_governance_gaps=[],
            )
        )

    fallback = planner.build_rate_limited_fallback_plan(
        request=request,
        base_risk_level="High",
        base_risk_score=70,
        factors=["downstream_table_or_pipeline"],
    )
    assert fallback.riskAdjustment == 0
    assert "rate-limited" in fallback.summary

