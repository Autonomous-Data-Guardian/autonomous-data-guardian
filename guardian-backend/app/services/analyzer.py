from __future__ import annotations

from typing import Any

from app.models.request_models import AnalyzeChangeRequest
from app.services.openmetadata_mcp import OpenMetadataMcpClient, OpenMetadataMcpError
from app.services.openmetadata_rest import OpenMetadataRestClient
from app.services.risk_engine import RiskInputs, calculate_risk_score


class AnalysisContextError(RuntimeError):
    """Raised when OpenMetadata context cannot be fetched for analysis."""


class AnalyzerService:
    """Aggregates metadata signals and computes deterministic risk context."""

    def __init__(self, rest_client: OpenMetadataRestClient, mcp_client: OpenMetadataMcpClient) -> None:
        self._rest_client = rest_client
        self._mcp_client = mcp_client

    async def analyze(self, request: AnalyzeChangeRequest) -> dict[str, Any]:
        """Build normalized facts, affected assets, and score from OpenMetadata context."""
        try:
            table = await self._rest_client.get_table_by_fqn(request.assetFqn)
            table_id = table.get("id")
            if not table_id:
                raise AnalysisContextError(f"Table id missing for asset '{request.assetFqn}'.")
            lineage = await self._rest_client.get_lineage("table", table_id)
        except AnalysisContextError:
            raise
        except Exception as error:
            raise AnalysisContextError(
                f"Unable to fetch OpenMetadata context for '{request.assetFqn}': {error}"
            ) from error
        mcp_details: dict[str, Any] = {}
        mcp_lineage: dict[str, Any] = {}
        mcp_warning: str | None = None
        try:
            mcp_details = await self._mcp_client.get_entity_details("table", request.assetFqn)
            mcp_lineage = await self._mcp_client.get_entity_lineage("table", request.assetFqn)
        except OpenMetadataMcpError as error:
            # REST context is enough for core analysis; treat MCP as optional enrichment.
            mcp_warning = str(error)

        downstream_nodes = _extract_downstream_entities(lineage, mcp_lineage)
        tags = _extract_tags(table, mcp_details, request.columnName)
        has_sensitive_tag = any(tag.lower() in {"pii", "sensitive", "personaldata"} for tag in tags)

        inputs = RiskInputs(
            has_downstream_dashboard=any(item.startswith("dashboard.") for item in downstream_nodes),
            has_sensitive_tag=has_sensitive_tag,
            has_downstream_table_or_pipeline=any(
                item.startswith("table.") or item.startswith("pipeline.") for item in downstream_nodes
            ),
            is_owner_missing=not bool(table.get("owners")),
            is_description_missing=not bool(table.get("description")),
            has_recent_data_quality_failure=_has_recent_quality_failure(table, mcp_details),
            has_many_downstream_dependencies=len(downstream_nodes) >= 5,
            is_glossary_missing=not _has_glossary(table, mcp_details),
        )
        score, risk_level, factors = calculate_risk_score(inputs)
        owner_gaps = []
        if inputs.is_owner_missing:
            owner_gaps.append("owner_missing")
        if inputs.is_glossary_missing:
            owner_gaps.append("glossary_missing")
        if inputs.is_description_missing:
            owner_gaps.append("description_missing")

        return {
            "riskScore": score,
            "riskLevel": risk_level,
            "factors": factors,
            "affectedAssets": sorted(downstream_nodes),
            "sensitiveDataWarning": "PII or sensitive tag detected." if has_sensitive_tag else None,
            "ownerGovernanceGaps": owner_gaps,
            "rawContext": {
                "table": table,
                "lineage": lineage,
                "mcp_details": mcp_details,
                "mcp_lineage": mcp_lineage,
                "mcp_warning": mcp_warning,
            },
        }


def _extract_downstream_entities(lineage: dict, mcp_lineage: dict) -> set[str]:
    """Extract downstream references from REST and MCP lineage payloads."""
    results: set[str] = set()
    for edge in lineage.get("downstreamEdges", []):
        target = edge.get("toEntity", {})
        entity_type = target.get("type", "unknown")
        fqn = target.get("fullyQualifiedName") or target.get("name")
        if fqn:
            results.add(f"{entity_type}.{fqn}")
    for node in mcp_lineage.get("result", {}).get("downstream", []):
        entity_type = node.get("entityType", "unknown")
        fqn = node.get("fqn") or node.get("name")
        if fqn:
            results.add(f"{entity_type}.{fqn}")
    return results


def _extract_tags(table: dict, mcp_details: dict, column_name: str | None) -> set[str]:
    """Extract table-level and optional column-level tags from both sources."""
    tags: set[str] = set()
    for tag_label in table.get("tags", []):
        value = tag_label.get("tagFQN") or tag_label.get("labelType")
        if value:
            tags.add(value)
    if column_name:
        for column in table.get("columns", []):
            if column.get("name") != column_name:
                continue
            for tag_label in column.get("tags", []):
                value = tag_label.get("tagFQN") or tag_label.get("labelType")
                if value:
                    tags.add(value)
    for tag_value in mcp_details.get("result", {}).get("tags", []):
        if isinstance(tag_value, str):
            tags.add(tag_value)
    return tags


def _has_recent_quality_failure(table: dict, mcp_details: dict) -> bool:
    """Check quality signals from known OpenMetadata profile and test fields."""
    if table.get("testCaseResult") and table["testCaseResult"].get("testCaseStatus") == "Failed":
        return True
    quality = mcp_details.get("result", {}).get("dataQuality", {})
    return bool(quality.get("recentFailures", 0))


def _has_glossary(table: dict, mcp_details: dict) -> bool:
    """Check glossary terms from both REST and MCP responses."""
    if table.get("domain") or table.get("tags"):
        return True
    glossary_terms = mcp_details.get("result", {}).get("glossaryTerms", [])
    return bool(glossary_terms)
