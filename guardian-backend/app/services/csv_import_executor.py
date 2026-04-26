from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models.csv_import_models import CsvImportRequest, CsvImportResponse
from app.services.csv_analysis import CsvAnalysisService
from app.services.openmetadata_rest import OpenMetadataRestClient


class CsvImportExecutorService:
    """Executes confirmed CSV import into database and OpenMetadata metadata."""

    def __init__(
        self,
        csv_analysis_service: CsvAnalysisService,
        rest_client: OpenMetadataRestClient,
        database_url: str,
        default_database_schema_fqn: str,
    ) -> None:
        self._csv_analysis_service = csv_analysis_service
        self._rest_client = rest_client
        self._database_url = database_url
        self._default_database_schema_fqn = default_database_schema_fqn

    async def execute_import(self, request: CsvImportRequest) -> CsvImportResponse:
        """Execute one confirmed import from cached analysis session."""
        session = self._csv_analysis_service.get_session(request.analysisId)
        if session is None:
            raise ValueError("Analysis session not found. Please analyze the CSV again.")

        table_name = request.tableName or session.suggested_table_name
        database_schema_fqn = request.databaseSchemaFqn or self._default_database_schema_fqn
        if not database_schema_fqn:
            raise ValueError("databaseSchemaFqn is required for OpenMetadata import.")

        rows_imported = self._import_rows_to_sqlite(
            table_name=table_name,
            rows=session.rows,
            overwrite_existing=request.overwriteExistingTable,
        )

        metadata = await self._rest_client.create_or_update_table_metadata(
            database_schema_fqn=database_schema_fqn,
            table_name=table_name,
            columns=[column.model_dump() for column in session.columns],
            description=session.suggested_description,
        )

        warnings: list[str] = []
        metadata_status = str(metadata.get("status", "unknown"))
        if metadata_status != "created":
            warnings.append("OpenMetadata table already existed; metadata was reused.")

        return CsvImportResponse(
            analysisId=request.analysisId,
            tableName=table_name,
            rowsImported=rows_imported,
            databaseImportStatus="imported",
            metadataImportStatus=metadata_status,
            metadataTableFqn=metadata.get("tableFqn"),
            metadataEntityId=metadata.get("tableId"),
            warnings=warnings,
        )

    def _import_rows_to_sqlite(self, table_name: str, rows: list[dict[str, str]], overwrite_existing: bool) -> int:
        """Import rows into configured sqlite database."""
        if not self._database_url.startswith("sqlite:///"):
            raise ValueError("Only sqlite database url is supported in this version (sqlite:///path.db).")
        database_path = self._database_url.removeprefix("sqlite:///")
        if not database_path:
            raise ValueError("Invalid sqlite database url.")

        Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        try:
            if not rows:
                return 0
            columns = list(rows[0].keys())
            if overwrite_existing:
                connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            create_columns_sql = ", ".join(f'"{column}" TEXT' for column in columns)
            connection.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({create_columns_sql})')

            placeholders = ", ".join("?" for _ in columns)
            quoted_columns = ", ".join(f'"{column}"' for column in columns)
            insert_sql = f'INSERT INTO "{table_name}" ({quoted_columns}) VALUES ({placeholders})'
            values = [[row.get(column, "") for column in columns] for row in rows]
            connection.executemany(insert_sql, values)
            connection.commit()
            return len(values)
        finally:
            connection.close()
