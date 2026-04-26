from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.analyze import router as analyze_router
from app.routes.assets import router as assets_router
from app.routes.csv_import import router as csv_import_router
from app.routes.reports import router as reports_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets_router)
app.include_router(analyze_router)
app.include_router(reports_router)
app.include_router(csv_import_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health endpoint for local verification."""
    return {"status": "ok"}
