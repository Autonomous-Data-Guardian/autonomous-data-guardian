from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.models.response_models import AnalyzeChangeResponse, StoredReport


class ReportStoreService:
    """Simple JSON file report store for MVP report retrieval."""

    def __init__(self, store_path: str) -> None:
        self._path = Path(store_path)
        if not self._path.exists():
            self._path.write_text("{}", encoding="utf-8")

    def _read_all(self) -> dict[str, dict]:
        content = self._path.read_text(encoding="utf-8")
        return json.loads(content) if content.strip() else {}

    def _write_all(self, payload: dict[str, dict]) -> None:
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def create_report(self, report: AnalyzeChangeResponse, input_snapshot: dict) -> StoredReport:
        """Persist a generated report and return the stored representation."""
        report_id = str(uuid4())
        stored_report = StoredReport(
            reportId=report_id,
            riskLevel=report.riskLevel,
            riskScore=report.riskScore,
            summary=report.summary,
            affectedAssets=report.affectedAssets,
            sensitiveDataWarning=report.sensitiveDataWarning,
            ownerGovernanceGaps=report.ownerGovernanceGaps,
            triggeredFactors=report.triggeredFactors,
            recommendations=report.recommendations,
            createdAt=datetime.now(UTC),
            inputSnapshot=input_snapshot,
        )
        current_data = self._read_all()
        current_data[report_id] = stored_report.model_dump(mode="json")
        self._write_all(current_data)
        return stored_report

    def get_report(self, report_id: str) -> StoredReport | None:
        """Load a report by id from JSON storage."""
        current_data = self._read_all()
        target = current_data.get(report_id)
        if not target:
            return None
        return StoredReport.model_validate(target)
