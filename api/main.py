"""
Extract — FastAPI application entry point.

Start the server:
    uvicorn api.main:app --reload --port 8000

Interactive docs at: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import activate, analyze, comparables, drillholes, export, ingest, news, notes, npv, portfolio, projects, renders, reports, resources, royalties, settings, tools
from api.routers.ingest import edgar_router, url_router
from api.routers.settings import load_and_apply_settings

# Apply saved API keys to env before anything else loads
load_and_apply_settings()

app = FastAPI(
    title="Extract API",
    version="0.1.0",
    description="Internal API — not for public access.",
)

# Allow the React dev server and Tauri window to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(projects.router)
app.include_router(ingest.router)
app.include_router(url_router)
app.include_router(edgar_router)
app.include_router(analyze.router)
app.include_router(reports.router)
app.include_router(export.router)
app.include_router(notes.router)
app.include_router(comparables.router)
app.include_router(resources.router)
app.include_router(royalties.router)
app.include_router(portfolio.router)
app.include_router(drillholes.router)
app.include_router(renders.router)
app.include_router(npv.router)
app.include_router(tools.router)
app.include_router(news.router)
app.include_router(settings.router)
app.include_router(activate.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness check — returns ok when the server is running."""
    return {"status": "ok", "version": "0.1.0"}
