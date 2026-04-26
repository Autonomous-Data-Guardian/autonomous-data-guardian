from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from app.models.csv_import_models import CsvAnalyzeResponse, CsvColumnProfile
from app.services.openrouter_client import OpenRouterClient, OpenRouterError


@dataclass
class CsvAnalysisSession:
    """In-memory session object used between analyze and import steps."""

    analysis_id: str
    file_name: str
    rows: list[dict[str, str]]
    columns: list[CsvColumnProfile]
    suggested_table_name: str
    suggested_description: str
    created_at: datetime


class CsvAnalysisSessionStore:
    """Simple in-memory session store for CSV analyze/import flow."""

    def __init__(self) -> None:
        self._sessions: dict[str, CsvAnalysisSession] = {}

    def put(self, session: CsvAnalysisSession) -> None:
        """Store one session by analysis id."""
        self._sessions[session.analysis_id] = session

    def get(self, analysis_id: str) -> CsvAnalysisSession | None:
        """Read one session by analysis id."""
        return self._sessions.get(analysis_id)


class CsvAiSummary(BaseModel):
    """Expected AI payload shape for CSV analysis response."""

    comment: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    suggestedTableName: str = Field(min_length=1)
    suggestedDescription: str = Field(min_length=1)


class CsvAnalysisService:
    """Parses CSV content and returns AI review with suggested metadata."""

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        session_store: CsvAnalysisSessionStore,
        max_file_size_bytes: int,
    ) -> None:
        self._openrouter_client = openrouter_client
        self._session_store = session_store
        self._max_file_size_bytes = max_file_size_bytes

    async def analyze_csv(self, file_name: str, content: bytes, intent: str) -> CsvAnalyzeResponse:
        """Analyze one CSV file and create an analysis session."""
        self._validate_file(file_name=file_name, content=content)
        rows = _parse_csv_rows(content)
        if not rows:
            raise ValueError("CSV is empty. Please upload a CSV with headers and rows.")

        columns = _build_column_profiles(rows)
        default_table_name = _normalize_table_name(file_name.rsplit(".", 1)[0] if "." in file_name else file_name)
        ai_summary = await self._build_ai_summary(intent=intent, columns=columns, row_count=len(rows), default_table_name=default_table_name)

        analysis_id = str(uuid4())
        session = CsvAnalysisSession(
            analysis_id=analysis_id,
            file_name=file_name,
            rows=rows,
            columns=columns,
            suggested_table_name=ai_summary.suggestedTableName,
            suggested_description=ai_summary.suggestedDescription,
            created_at=datetime.now(UTC),
        )
        self._session_store.put(session)

        return CsvAnalyzeResponse(
            analysisId=analysis_id,
            fileName=file_name,
            rowCount=len(rows),
            columns=columns,
            aiComment=ai_summary.comment,
            aiWarnings=ai_summary.warnings,
            suggestedTableName=ai_summary.suggestedTableName,
            suggestedDescription=ai_summary.suggestedDescription,
            createdAt=session.created_at.isoformat(),
        )

    def get_session(self, analysis_id: str) -> CsvAnalysisSession | None:
        """Fetch a cached analysis session."""
        return self._session_store.get(analysis_id)

    def _validate_file(self, file_name: str, content: bytes) -> None:
        if not file_name.lower().endswith(".csv"):
            raise ValueError("Only CSV files are supported in this version.")
        if not content:
            raise ValueError("Uploaded CSV is empty.")
        if len(content) > self._max_file_size_bytes:
            raise ValueError(f"CSV exceeds max size of {self._max_file_size_bytes} bytes.")

    async def _build_ai_summary(
        self,
        intent: str,
        columns: list[CsvColumnProfile],
        row_count: int,
        default_table_name: str,
    ) -> CsvAiSummary:
        system_prompt = (
            "You are a data governance assistant for metadata import review. "
            "Return strict JSON keys: comment, warnings, suggestedTableName, suggestedDescription."
        )
        user_payload = {
            "intent": intent,
            "rowCount": row_count,
            "columns": [column.model_dump() for column in columns],
            "defaultTableName": default_table_name,
        }
        try:
            raw = await self._openrouter_client.create_chat_completion(
                system_prompt=system_prompt,
                user_prompt=json.dumps(user_payload),
            )
            payload = json.loads(raw)
            parsed = CsvAiSummary.model_validate(payload)
            parsed.suggestedTableName = _normalize_table_name(parsed.suggestedTableName) or default_table_name
            return parsed
        except (OpenRouterError, json.JSONDecodeError, ValidationError):
            return CsvAiSummary(
                comment="AI review is temporarily unavailable. Deterministic CSV checks were used.",
                warnings=["AI fallback mode active."],
                suggestedTableName=default_table_name,
                suggestedDescription="Imported from uploaded CSV with deterministic schema inference.",
            )


def _parse_csv_rows(content: bytes) -> list[dict[str, str]]:
    """Parse CSV bytes into normalized row dictionaries."""
    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        return []
    rows: list[dict[str, str]] = []
    for row in reader:
        normalized_row: dict[str, str] = {}
        for key in reader.fieldnames:
            if key is None:
                continue
            normalized_row[key] = str((row or {}).get(key, "") or "").strip()
        rows.append(normalized_row)
    return rows


def _build_column_profiles(rows: list[dict[str, str]]) -> list[CsvColumnProfile]:
    """Infer column profiles using simple deterministic heuristics."""
    if not rows:
        return []
    names = list(rows[0].keys())
    profiles: list[CsvColumnProfile] = []
    for name in names:
        values = [row.get(name, "") for row in rows]
        non_empty = [value for value in values if value != ""]
        inferred_type = _infer_type(non_empty)
        null_ratio = (len(values) - len(non_empty)) / len(values) if values else 0
        sample_values = non_empty[:3]
        profiles.append(
            CsvColumnProfile(
                name=name,
                inferredType=inferred_type,
                nullRatio=round(null_ratio, 4),
                sampleValues=sample_values,
            )
        )
    return profiles


def _infer_type(values: list[str]) -> str:
    """Infer one simple scalar type from sampled values."""
    if not values:
        return "TEXT"
    if all(_is_int(value) for value in values):
        return "INT"
    if all(_is_float(value) for value in values):
        return "DOUBLE"
    return "TEXT"


def _is_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _normalize_table_name(name: str) -> str:
    """Normalize arbitrary name into safe SQL/OpenMetadata table name format."""
    normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "uploaded_table"
