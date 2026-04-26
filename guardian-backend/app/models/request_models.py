from typing import Literal

from pydantic import BaseModel, Field


ChangeType = Literal[
    "DELETE_COLUMN",
    "RENAME_COLUMN",
    "DELETE_TABLE",
    "CHANGE_COLUMN_TYPE",
]


class AnalyzeChangeRequest(BaseModel):
    """Request payload for change impact analysis."""

    assetType: Literal["table"] = "table"
    assetFqn: str = Field(min_length=1)
    changeType: ChangeType | None = None
    columnName: str | None = None
    newColumnName: str | None = None
    newColumnType: str | None = None
    description: str = Field(default="", max_length=2000)
    intent: str = Field(min_length=1, max_length=2000)
