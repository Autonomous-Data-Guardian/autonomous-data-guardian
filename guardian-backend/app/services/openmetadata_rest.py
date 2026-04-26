from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx


class OpenMetadataUpstreamError(RuntimeError):
    """Raised when OpenMetadata upstream APIs fail."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenMetadataRestClient:
    """REST client for deterministic OpenMetadata entity and lineage reads."""

    def __init__(self, base_url: str, jwt_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {jwt_token}"} if jwt_token else {}

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Extract upstream error detail from JSON payload or plain text."""
        try:
            payload = response.json()
            if isinstance(payload, dict):
                message = payload.get("message") or payload.get("detail")
                if message:
                    return str(message)
        except Exception:
            pass
        return response.text[:160]

    async def get_table_by_fqn(self, asset_fqn: str) -> dict[str, Any]:
        """Fetch table details by fully qualified name."""
        async with httpx.AsyncClient(timeout=20) as client:
            last_response: httpx.Response | None = None
            for candidate_fqn in _build_fqn_candidates(asset_fqn):
                endpoint = f"{self._base_url}/api/v1/tables/name/{quote(candidate_fqn, safe='')}"
                response = await client.get(endpoint, headers=self._headers)
                last_response = response
                if response.is_success:
                    return response.json()
                if response.status_code != 404:
                    response.raise_for_status()

            fallback_id = await self._resolve_table_id_by_search(client=client, asset_fqn=asset_fqn)
            if fallback_id:
                fallback_endpoint = f"{self._base_url}/api/v1/tables/{quote(fallback_id, safe='')}"
                fallback_response = await client.get(fallback_endpoint, headers=self._headers)
                fallback_response.raise_for_status()
                return fallback_response.json()

            if last_response is not None:
                raise httpx.HTTPStatusError(
                    f"Table not found for FQN: {asset_fqn}",
                    request=last_response.request,
                    response=last_response,
                )
            raise httpx.HTTPError(f"Invalid empty table FQN: {asset_fqn}")

    async def _resolve_table_id_by_search(self, client: httpx.AsyncClient, asset_fqn: str) -> str | None:
        """Resolve table id from search hits when direct name lookup misses."""
        search_endpoint = f"{self._base_url}/api/v1/search/query"
        search_response = await client.get(
            search_endpoint,
            params={"q": asset_fqn, "index": "table", "from": 0, "size": 25},
            headers=self._headers,
        )
        if not search_response.is_success:
            return None
        search_payload = search_response.json()
        hits = search_payload.get("hits", {}).get("hits", [])
        normalized_requested_fqns = {candidate.lower() for candidate in _build_fqn_candidates(asset_fqn)}
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            source = hit.get("_source")
            if not isinstance(source, dict):
                continue
            hit_fqn = source.get("fullyQualifiedName") or source.get("fqn")
            if not isinstance(hit_fqn, str):
                continue
            if hit_fqn.lower() not in normalized_requested_fqns:
                continue
            hit_id = source.get("id") or hit.get("_id")
            if hit_id:
                return str(hit_id)
        return None

    async def get_lineage(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        """Fetch lineage graph by entity type and id."""
        endpoint = f"{self._base_url}/api/v1/lineage/{entity_type}/{entity_id}"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(endpoint, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def search_tables(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        """Search OpenMetadata tables with discovery API and fallback list API."""
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                search_endpoint = f"{self._base_url}/api/v1/search/query"
                search_params = {"q": query, "index": "table", "from": 0, "size": limit}
                search_response = await client.get(search_endpoint, params=search_params, headers=self._headers)
                if search_response.is_success:
                    search_payload = search_response.json()
                    hits = search_payload.get("hits", {}).get("hits", [])
                    results: list[dict[str, Any]] = []
                    for hit in hits:
                        source = hit.get("_source") if isinstance(hit, dict) else None
                        if isinstance(source, dict):
                            results.append(source)
                    return results

                list_endpoint = f"{self._base_url}/api/v1/tables"
                list_params = {"limit": limit, "fields": "owners,tags"}
                list_response = await client.get(list_endpoint, params=list_params, headers=self._headers)
                if not list_response.is_success:
                    search_message = self._extract_error_message(search_response)
                    list_message = self._extract_error_message(list_response)
                    status_code = (
                        401
                        if 401 in {search_response.status_code, list_response.status_code}
                        else 403
                        if 403 in {search_response.status_code, list_response.status_code}
                        else 502
                    )
                    raise OpenMetadataUpstreamError(
                        f"OpenMetadata table search failed: search={search_response.status_code} "
                        f"tables={list_response.status_code} "
                        f"search_message={search_message} tables_message={list_message}",
                        status_code=status_code,
                    )
                list_payload = list_response.json()
                data = list_payload.get("data", [])
                normalized_data = [item for item in data if isinstance(item, dict)]
                lowered_query = query.lower()
                return [
                    item
                    for item in normalized_data
                    if lowered_query in str(item.get("name", "")).lower()
                    or lowered_query in str(item.get("fullyQualifiedName", "")).lower()
                ]
        except httpx.HTTPError as error:
            raise OpenMetadataUpstreamError(f"OpenMetadata table search connection failed: {error}") from error

    async def get_database_schema_by_fqn(self, database_schema_fqn: str) -> dict[str, Any]:
        """Fetch database schema entity by fully qualified name."""
        endpoint = f"{self._base_url}/api/v1/databaseSchemas/name/{quote(database_schema_fqn, safe='')}"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(endpoint, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def create_or_update_table_metadata(
        self,
        database_schema_fqn: str,
        table_name: str,
        columns: list[dict[str, Any]],
        description: str,
    ) -> dict[str, Any]:
        """Create metadata table entity in OpenMetadata or return existing table."""
        try:
            existing = await self.get_table_by_fqn(f"{database_schema_fqn}.{table_name}")
            return {
                "status": "existing",
                "tableId": existing.get("id"),
                "tableFqn": existing.get("fullyQualifiedName"),
            }
        except Exception:
            pass

        payload = {
            "name": table_name,
            "tableType": "Regular",
            "description": description,
            "databaseSchema": database_schema_fqn,
            "columns": [
                {
                    "name": str(column.get("name", "")),
                    "dataType": _map_to_openmetadata_data_type(str(column.get("inferredType", "TEXT"))),
                }
                for column in columns
                if column.get("name")
            ],
        }
        endpoint = f"{self._base_url}/api/v1/tables"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(endpoint, headers=self._headers, json=payload)
            if not response.is_success:
                message = self._extract_error_message(response)
                raise OpenMetadataUpstreamError(
                    f"OpenMetadata table create failed: status={response.status_code} message={message}",
                    status_code=502,
                )
            body = response.json()
            return {
                "status": "created",
                "tableId": body.get("id"),
                "tableFqn": body.get("fullyQualifiedName"),
            }


def _build_fqn_candidates(asset_fqn: str) -> list[str]:
    """Generate deterministic FQN candidates for tolerant table name lookup."""
    normalized = asset_fqn.strip()
    if not normalized:
        return []
    candidates: list[str] = [normalized]
    segments = [segment for segment in normalized.split(".") if segment]
    # Some search payloads include one extra namespace prefix before service name.
    if len(segments) >= 4:
        trimmed = ".".join(segments[1:])
        if trimmed and trimmed not in candidates:
            candidates.append(trimmed)
    return candidates


def _map_to_openmetadata_data_type(inferred_type: str) -> str:
    """Map inferred CSV type to OpenMetadata table column data type."""
    normalized = inferred_type.upper()
    if normalized in {"INT", "INTEGER", "BIGINT"}:
        return "INT"
    if normalized in {"DOUBLE", "FLOAT", "DECIMAL"}:
        return "DOUBLE"
    return "STRING"
