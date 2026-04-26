from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_analyzer_service, get_llm_planner_service, get_report_store_service
from app.models.request_models import AnalyzeChangeRequest, ChangeType
from app.models.response_models import AnalyzeChangeResponse
from app.services.analyzer import AnalysisContextError, AnalyzerService
from app.services.llm_planner import LlmPlannerError, LlmPlannerRateLimitError, LlmPlannerService
from app.services.report_store import ReportStoreService
from app.services.risk_engine import map_risk_level

router = APIRouter(tags=["analysis"])

# This function infers one MVP change type from user intent text.
def infer_change_type(intent: str) -> ChangeType | None:
    text = intent.lower()
    if "rename" in text:
        return "RENAME_COLUMN"
    if "change type" in text or "cast" in text or "datatype" in text:
        return "CHANGE_COLUMN_TYPE"
    if "drop table" in text or "delete table" in text or "remove table" in text:
        return "DELETE_TABLE"
    if (
        "delete column" in text
        or "drop column" in text
        or "remove column" in text
        or "drop field" in text
        or "remove field" in text
    ):
        return "DELETE_COLUMN"
    return None


def clamp_risk_score(score: int) -> int:
    """Clamp risk score to accepted API bounds."""
    return max(0, min(100, score))


@router.post("/analyze-change", response_model=AnalyzeChangeResponse)
async def analyze_change(
    request: AnalyzeChangeRequest,
    analyzer_service: AnalyzerService = Depends(get_analyzer_service),
    planner_service: LlmPlannerService = Depends(get_llm_planner_service),
    report_store: ReportStoreService = Depends(get_report_store_service),
) -> AnalyzeChangeResponse:
    """Analyze proposed change and return persisted report response."""
    if request.changeType is None:
        inferred_change_type = infer_change_type(request.intent)
        if inferred_change_type is not None:
            request.changeType = inferred_change_type

    try:
        analysis = await analyzer_service.analyze(request)
    except AnalysisContextError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    try:
        llm_plan = await planner_service.build_summary_and_plan(
            request=request,
            base_risk_level=analysis["riskLevel"],
            base_risk_score=analysis["riskScore"],
            affected_assets=analysis["affectedAssets"],
            factors=analysis["factors"],
            owner_governance_gaps=analysis["ownerGovernanceGaps"],
        )
    except LlmPlannerRateLimitError:
        llm_plan = planner_service.build_rate_limited_fallback_plan(
            request=request,
            base_risk_level=analysis["riskLevel"],
            base_risk_score=analysis["riskScore"],
            factors=analysis["factors"],
        )
    except LlmPlannerError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    final_score = clamp_risk_score(analysis["riskScore"] + llm_plan.riskAdjustment)
    final_level = map_risk_level(final_score)
    summary_with_rationale = f"{llm_plan.summary} AI adjustment rationale: {llm_plan.adjustmentRationale}"
    triggered_factors = [*analysis["factors"], f"ai_adjustment_{llm_plan.riskAdjustment:+d}"]

    payload = AnalyzeChangeResponse(
        reportId="pending",
        riskLevel=final_level,
        riskScore=final_score,
        summary=summary_with_rationale,
        affectedAssets=analysis["affectedAssets"],
        sensitiveDataWarning=analysis["sensitiveDataWarning"],
        ownerGovernanceGaps=analysis["ownerGovernanceGaps"],
        triggeredFactors=triggered_factors,
        recommendations=llm_plan.recommendations,
        createdAt=datetime.now(UTC),
    )
    stored = report_store.create_report(payload, request.model_dump())
    return AnalyzeChangeResponse(**stored.model_dump())
