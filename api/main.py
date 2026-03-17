"""FastAPI application entry point."""

from fastapi import FastAPI

app = FastAPI(
    title="Mining Intelligence Platform API",
    version="0.1.0",
    description="Internal API — not for public access.",
)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
