from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_report_store_service
from app.models.response_models import AnalyzeChangeResponse
from app.services.report_store import ReportStoreService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_id}", response_model=AnalyzeChangeResponse)
async def get_report(
    report_id: str,
    report_store: ReportStoreService = Depends(get_report_store_service),
) -> AnalyzeChangeResponse:
    """Return a previously persisted analysis report by id."""
    stored_report = report_store.get_report(report_id)
    if not stored_report:
        raise HTTPException(status_code=404, detail="Report not found")
    return AnalyzeChangeResponse(**stored_report.model_dump())
