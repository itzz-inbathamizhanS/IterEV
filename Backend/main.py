"""
Future-Mobility-Aware EV Decision System — FastAPI Backend
Research prototype. Phase 1: Consumer flow (deterministic, no ML).

Run with:
  cd Backend
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8000

Frontend connects via:
  VITE_API_URL=http://localhost:8000  (set in Frontend/.env.local)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.consumer import router as consumer_router
from api.fleet import router as fleet_router
from api.simulation import router as simulation_router

app = FastAPI(
    title="Future Mobility API",
    description=(
        "Research prototype backend for Future-Mobility-Aware EV Decision System. "
        "Implements Future Mobility Feasibility (FMF) and Future Mobility Risk (FMR) "
        "as defined in the research document: Section 13–14."
    ),
    version="1.0.0-phase1",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — allow the Lovable frontend (Vite dev server and production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://*.lovable.app",   # Lovable preview deployments
        "https://*.lovableproject.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(consumer_router)
app.include_router(fleet_router)
app.include_router(simulation_router)


@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint — used by frontend to detect if backend is running."""
    return {
        "status": "ok",
        "phase": 1,
        "description": "Consumer flow active. Fleet and Simulation stubs available.",
        "engines": ["energy", "battery", "feasibility", "optimizer", "explanation"],
    }


@app.get("/")
async def root() -> dict:
    return {"message": "Future Mobility API — see /api/docs for endpoints"}
