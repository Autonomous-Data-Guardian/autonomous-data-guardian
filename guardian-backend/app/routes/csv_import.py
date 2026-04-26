from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.dependencies import get_csv_analysis_service, get_csv_import_executor_service
from app.models.csv_import_models import CsvAnalyzeResponse, CsvImportRequest, CsvImportResponse
from app.services.csv_analysis import CsvAnalysisService
from app.services.csv_import_executor import CsvImportExecutorService

router = APIRouter(prefix="/csv", tags=["csv-import"])


@router.post("/analyze", response_model=CsvAnalyzeResponse)
async def analyze_csv_upload(
    file: UploadFile = File(...),
    intent: str = Form(...),
    csv_analysis_service: CsvAnalysisService = Depends(get_csv_analysis_service),
) -> CsvAnalyzeResponse:
    """Analyze one uploaded CSV file and return AI review before import."""
    try:
        content = await file.read()
        return await csv_analysis_service.analyze_csv(
            file_name=file.filename or "uploaded.csv",
            content=content,
            intent=intent,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/import", response_model=CsvImportResponse)
async def confirm_csv_import(
    request: CsvImportRequest,
    csv_import_executor: CsvImportExecutorService = Depends(get_csv_import_executor_service),
) -> CsvImportResponse:
    """Import one previously analyzed CSV into DB and OpenMetadata."""
    try:
        return await csv_import_executor.execute_import(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
