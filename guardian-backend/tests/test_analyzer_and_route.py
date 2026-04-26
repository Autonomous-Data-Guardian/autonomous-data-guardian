import asyncio

import pytest

from app.models.request_models import AnalyzeChangeRequest
from app.routes.analyze import clamp_risk_score
from app.services.analyzer import AnalysisContextError, AnalyzerService
from app.services.openmetadata_mcp import OpenMetadataMcpError


class FailingRestClient:
    """Test double that always fails table lookup."""

    async def get_table_by_fqn(self, asset_fqn: str) -> dict:
        raise RuntimeError(f"failed to fetch {asset_fqn}")


class NoopMcpClient:
    """Test double used only to satisfy AnalyzerService constructor."""

    async def get_entity_details(self, entity_type: str, fqn: str) -> dict:
        return {}

    async def get_entity_lineage(self, entity_type: str, fqn: str) -> dict:
        return {}


class GoodRestClient:
    """Test double that returns minimal valid table + lineage payloads."""

    async def get_table_by_fqn(self, asset_fqn: str) -> dict:
        return {"id": "table-id-1", "owners": [{"name": "owner"}], "description": "desc", "tags": []}

    async def get_lineage(self, entity_type: str, entity_id: str) -> dict:
        return {"downstreamEdges": []}


class FailingMcpClient:
    """Test double that simulates MCP endpoint failures."""

    async def get_entity_details(self, entity_type: str, fqn: str) -> dict:
        raise OpenMetadataMcpError("mcp unavailable")

    async def get_entity_lineage(self, entity_type: str, fqn: str) -> dict:
        raise OpenMetadataMcpError("mcp unavailable")


def test_analyzer_fails_fast_when_openmetadata_unavailable() -> None:
    """Verify analyzer raises context error and never emits demo fallback."""
    service = AnalyzerService(FailingRestClient(), NoopMcpClient())
    request = AnalyzeChangeRequest(
        assetType="table",
        assetFqn="sample.db.schema.table_a",
        intent="delete a column",
        description="delete a column",
    )

    with pytest.raises(AnalysisContextError):
        asyncio.run(service.analyze(request))


def test_analyzer_continues_when_mcp_fails_but_rest_succeeds() -> None:
    """Verify REST-based analysis still succeeds when MCP enrichment fails."""
    service = AnalyzerService(GoodRestClient(), FailingMcpClient())
    request = AnalyzeChangeRequest(
        assetType="table",
        assetFqn="sample.db.schema.table_a",
        intent="delete a column",
        description="delete a column",
    )

    result = asyncio.run(service.analyze(request))
    assert "riskScore" in result
    assert result["rawContext"]["mcp_warning"] == "mcp unavailable"


def test_clamp_risk_score_bounds() -> None:
    """Verify hybrid score clamping enforces inclusive 0..100 limits."""
    assert clamp_risk_score(-1) == 0
    assert clamp_risk_score(0) == 0
    assert clamp_risk_score(66) == 66
    assert clamp_risk_score(100) == 100
    assert clamp_risk_score(101) == 100

