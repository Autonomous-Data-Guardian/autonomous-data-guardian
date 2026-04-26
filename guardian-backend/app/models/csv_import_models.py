from __future__ import annotations

from pydantic import BaseModel, Field


class CsvColumnProfile(BaseModel):
    """Represents one inferred CSV column profile."""

    name: str
    inferredType: str
    nullRatio: float = Field(ge=0, le=1)
    sampleValues: list[str]


class CsvAnalyzeResponse(BaseModel):
    """Response payload returned after CSV AI analysis."""

    analysisId: str
    fileName: str
    rowCount: int
    columns: list[CsvColumnProfile]
    aiComment: str
    aiWarnings: list[str]
    suggestedTableName: str
    suggestedDescription: str
    createdAt: str


class CsvImportRequest(BaseModel):
    """Request payload for confirmed CSV import execution."""

    analysisId: str = Field(min_length=1)
    tableName: str | None = None
    databaseSchemaFqn: str | None = None
    overwriteExistingTable: bool = False


class CsvImportResponse(BaseModel):
    """Response payload returned after confirmed CSV import."""

    analysisId: str
    tableName: str
    rowsImported: int
    databaseImportStatus: str
    metadataImportStatus: str
    metadataTableFqn: str | None = None
    metadataEntityId: str | None = None
    warnings: list[str]
