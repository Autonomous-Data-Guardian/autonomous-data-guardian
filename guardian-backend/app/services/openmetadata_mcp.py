from __future__ import annotations

from typing import Any

import httpx


class OpenMetadataMcpError(RuntimeError):
    """Raised when OpenMetadata MCP calls fail."""


class OpenMetadataMcpClient:
    """MCP client for AI-friendly OpenMetadata search and context retrieval."""

    def __init__(self, mcp_url: str, jwt_token: str) -> None:
        self._mcp_url = mcp_url
        self._headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}

    async def call(self, method_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call a specific MCP method with JSON-RPC style payload."""
        payload = {
            "jsonrpc": "2.0",
            "id": "guardian-mcp-call",
            "method": method_name,
            "params": params,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(self._mcp_url, json=payload, headers=self._headers)
            if not response.is_success:
                detail = response.text[:200]
                raise OpenMetadataMcpError(
                    f"MCP call '{method_name}' failed with status {response.status_code}: {detail}"
                )
            return response.json()

    async def search_metadata(self, query: str, entity_type: str = "table", limit: int = 10) -> dict[str, Any]:
        """Search metadata entities using MCP search_metadata."""
        return await self.call(
            "search_metadata",
            {"query": query, "entity_type": entity_type, "limit": limit},
        )

    async def semantic_search(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Run semantic search over metadata context."""
        return await self.call("semantic_search", {"query": query, "limit": limit})

    async def get_entity_details(self, entity_type: str, fqn: str) -> dict[str, Any]:
        """Fetch a single entity details payload from MCP."""
        return await self.call("get_entity_details", {"entity_type": entity_type, "fqn": fqn})

    async def get_entity_lineage(self, entity_type: str, fqn: str) -> dict[str, Any]:
        """Fetch lineage context using MCP entity lineage call."""
        return await self.call("get_entity_lineage", {"entity_type": entity_type, "fqn": fqn})
