import asyncio

import httpx
import pytest

from app.services.openmetadata_rest import OpenMetadataRestClient, _build_fqn_candidates


def test_build_fqn_candidates_keeps_original_and_trimmed_variant() -> None:
    """Ensure lookup candidates include original and one leading-trimmed variant."""
    candidates = _build_fqn_candidates("guardian.guardian-db.guardian_demo.sentiment_market_panel")
    assert candidates == [
        "guardian.guardian-db.guardian_demo.sentiment_market_panel",
        "guardian-db.guardian_demo.sentiment_market_panel",
    ]


def test_build_fqn_candidates_for_four_part_fqn_adds_trimmed_variant() -> None:
    """Ensure 4-part FQNs include one leading-trimmed candidate."""
    candidates = _build_fqn_candidates("svc.db.schema.table_a")
    assert candidates == ["svc.db.schema.table_a", "db.schema.table_a"]


def test_get_table_by_fqn_uses_trimmed_fallback_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure client retries with trimmed candidate when first FQN misses."""

    class FakeAsyncClient:
        """Minimal AsyncClient test double for deterministic endpoint responses."""

        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            return None

        async def get(self, url: str, *, headers=None, params=None) -> httpx.Response:  # noqa: ANN001
            request = httpx.Request("GET", url, params=params)
            if "tables/name/guardian.guardian-db.guardian_demo.sentiment_market_panel" in str(request.url):
                return httpx.Response(404, request=request, json={"message": "not found"})
            if "tables/name/guardian-db.guardian_demo.sentiment_market_panel" in str(request.url):
                return httpx.Response(200, request=request, json={"id": "table-id-123"})
            return httpx.Response(404, request=request, json={"message": "not found"})

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    client = OpenMetadataRestClient(base_url="http://localhost:8585", jwt_token="")

    result = asyncio.run(client.get_table_by_fqn("guardian.guardian-db.guardian_demo.sentiment_market_panel"))
    assert result["id"] == "table-id-123"


def test_create_or_update_table_metadata_sends_database_schema_as_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure CreateTable payload uses string databaseSchema expected by OpenMetadata."""

    captured_payload: dict = {}

    class FakeAsyncClient:
        """Minimal AsyncClient test double for table create payload assertions."""

        def __init__(self, timeout: int) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
            return None

        async def post(self, url: str, *, headers=None, json=None) -> httpx.Response:  # noqa: ANN001
            captured_payload.update(json or {})
            request = httpx.Request("POST", url)
            return httpx.Response(200, request=request, json={"id": "tbl-1", "fullyQualifiedName": "svc.db.schema.tbl"})

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    client = OpenMetadataRestClient(base_url="http://localhost:8585", jwt_token="")
    monkeypatch.setattr(client, "get_table_by_fqn", _raise_not_found)

    result = asyncio.run(
        client.create_or_update_table_metadata(
            database_schema_fqn="guardian.guardian-db.guardian_demo",
            table_name="diabetes",
            columns=[{"name": "Age", "inferredType": "INT"}],
            description="CSV uploaded table",
        )
    )

    assert captured_payload["databaseSchema"] == "guardian.guardian-db.guardian_demo"
    assert result["status"] == "created"


async def _raise_not_found(asset_fqn: str) -> dict:  # noqa: ARG001
    """Force metadata create path by simulating missing existing table."""
    raise httpx.HTTPStatusError(
        "not found",
        request=httpx.Request("GET", "http://localhost:8585/api/v1/tables/name/mock"),
        response=httpx.Response(404),
    )
