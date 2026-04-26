from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_rest_client
from app.models.response_models import SearchAssetItem
from app.services.openmetadata_rest import OpenMetadataRestClient, OpenMetadataUpstreamError

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/search", response_model=list[SearchAssetItem])
async def search_assets(
    q: str = Query(min_length=1),
    rest_client: OpenMetadataRestClient = Depends(get_rest_client),
) -> list[SearchAssetItem]:
    """Search table assets from OpenMetadata REST and normalize to UI shape."""
    try:
        items = await rest_client.search_tables(q, limit=25)
    except OpenMetadataUpstreamError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from error

    output: list[SearchAssetItem] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id") or item.get("_id") or item.get("fullyQualifiedName") or item.get("name", "")
        item_name = item.get("name") or item.get("displayName") or ""
        item_fqn = item.get("fullyQualifiedName") or item.get("fqn") or item_name
        if not item_fqn:
            continue
        output.append(
            SearchAssetItem(
                id=str(item_id),
                name=str(item_name),
                fqn=str(item_fqn),
                entityType="table",
                description=item.get("description"),
            )
        )
    return output
