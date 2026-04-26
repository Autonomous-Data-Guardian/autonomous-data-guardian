import os

from app.config import settings
from app.services.csv_analysis import CsvAnalysisService, CsvAnalysisSessionStore
from app.services.csv_import_executor import CsvImportExecutorService
from app.services.analyzer import AnalyzerService
from app.services.llm_planner import LlmPlannerService
from app.services.openmetadata_mcp import OpenMetadataMcpClient
from app.services.openmetadata_rest import OpenMetadataRestClient
from app.services.openrouter_client import OpenRouterClient
from app.services.report_store import ReportStoreService

_csv_analysis_store = CsvAnalysisSessionStore()


def get_rest_client() -> OpenMetadataRestClient:
    """Build REST client dependency."""
    return OpenMetadataRestClient(settings.openmetadata_base_url, settings.openmetadata_jwt_token)


def get_mcp_client() -> OpenMetadataMcpClient:
    """Build MCP client dependency."""
    return OpenMetadataMcpClient(settings.openmetadata_mcp_url, settings.openmetadata_jwt_token)


def get_analyzer_service() -> AnalyzerService:
    """Build analyzer service dependency."""
    return AnalyzerService(get_rest_client(), get_mcp_client())


def get_llm_planner_service() -> LlmPlannerService:
    """Build planner service dependency."""
    return LlmPlannerService(get_openrouter_client())


def get_openrouter_client() -> OpenRouterClient:
    """Build OpenRouter client dependency."""
    env_api_keys = []
    for key_name in sorted(name for name in os.environ if name.startswith("GUARDIAN_OPENROUTER_API_KEY")):
        value = os.environ.get(key_name, "").strip()
        if value:
            env_api_keys.append(value)

    return OpenRouterClient(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        model=settings.openrouter_model,
        api_keys=env_api_keys,
        max_retries_per_key=settings.openrouter_max_retries_per_key,
        base_backoff_seconds=settings.openrouter_base_backoff_seconds,
        max_tokens=settings.openrouter_max_tokens,
    )


def get_report_store_service() -> ReportStoreService:
    """Build report store dependency."""
    return ReportStoreService(settings.report_store_path)


def get_csv_analysis_service() -> CsvAnalysisService:
    """Build CSV analysis service dependency."""
    return CsvAnalysisService(
        openrouter_client=get_openrouter_client(),
        session_store=_csv_analysis_store,
        max_file_size_bytes=settings.csv_import_max_file_size_bytes,
    )


def get_csv_import_executor_service() -> CsvImportExecutorService:
    """Build CSV import executor dependency."""
    return CsvImportExecutorService(
        csv_analysis_service=get_csv_analysis_service(),
        rest_client=get_rest_client(),
        database_url=settings.csv_import_database_url,
        default_database_schema_fqn=settings.csv_import_openmetadata_database_schema_fqn,
    )
