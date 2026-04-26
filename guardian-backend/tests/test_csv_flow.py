import asyncio
import tempfile
from pathlib import Path

from app.models.csv_import_models import CsvImportRequest
from app.services.csv_analysis import CsvAnalysisService, CsvAnalysisSessionStore
from app.services.csv_import_executor import CsvImportExecutorService


class StubOpenRouterClient:
    """Stub OpenRouter client that returns deterministic CSV analysis output."""

    async def create_chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        return (
            '{"comment":"Looks safe to import with minor null checks.",'
            '"warnings":["check nulls in price column"],'
            '"suggestedTableName":"uploaded_prices",'
            '"suggestedDescription":"CSV import candidate table."}'
        )


class StubOpenMetadataRestClient:
    """Stub OpenMetadata client that returns deterministic metadata import output."""

    async def create_or_update_table_metadata(
        self,
        database_schema_fqn: str,
        table_name: str,
        columns: list[dict],
        description: str,
    ) -> dict:
        return {
            "status": "created",
            "tableId": "tbl-1",
            "tableFqn": f"{database_schema_fqn}.{table_name}",
        }


def test_csv_analyze_returns_profiles_and_session() -> None:
    """Verify CSV analyze step infers profile and stores analysis session."""
    store = CsvAnalysisSessionStore()
    service = CsvAnalysisService(
        openrouter_client=StubOpenRouterClient(),
        session_store=store,
        max_file_size_bytes=1_000_000,
    )
    content = b"date,price\n2026-01-01,100.2\n2026-01-02,\n"
    response = asyncio.run(service.analyze_csv(file_name="prices.csv", content=content, intent="review and import"))

    assert response.rowCount == 2
    assert response.analysisId
    assert len(response.columns) == 2
    assert service.get_session(response.analysisId) is not None


def test_csv_import_executes_sqlite_and_metadata_import() -> None:
    """Verify import step writes rows and returns metadata import summary."""
    store = CsvAnalysisSessionStore()
    analysis_service = CsvAnalysisService(
        openrouter_client=StubOpenRouterClient(),
        session_store=store,
        max_file_size_bytes=1_000_000,
    )
    analyze_response = asyncio.run(
        analysis_service.analyze_csv(
            file_name="prices.csv",
            content=b"date,price\n2026-01-01,100.2\n2026-01-02,98.5\n",
            intent="review and import",
        )
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        sqlite_path = Path(temp_dir) / "imports.db"
        executor = CsvImportExecutorService(
            csv_analysis_service=analysis_service,
            rest_client=StubOpenMetadataRestClient(),
            database_url=f"sqlite:///{sqlite_path}",
            default_database_schema_fqn="guardian.guardian-db.guardian_demo",
        )
        response = asyncio.run(
            executor.execute_import(
                CsvImportRequest(
                    analysisId=analyze_response.analysisId,
                    overwriteExistingTable=True,
                )
            )
        )

        assert response.rowsImported == 2
        assert response.metadataImportStatus == "created"
        assert response.metadataTableFqn == "guardian.guardian-db.guardian_demo.uploaded_prices"
