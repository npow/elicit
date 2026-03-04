"""FastAPI app entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from discovery_engine.database import init_db
from discovery_engine.api.projects import router as projects_router
from discovery_engine.api.interviews import router as interviews_router
from discovery_engine.api.analysis import router as analysis_router
from discovery_engine.api.coaching import router as coaching_router
from discovery_engine.api.simulation import router as simulation_router
from discovery_engine.api.calibration import router as calibration_router

app = FastAPI(
    title="Elicit",
    description="Elicit what matters from customer interviews. Build the right thing.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(interviews_router, prefix="/api/interviews", tags=["interviews"])
app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])
app.include_router(coaching_router, prefix="/api/coaching", tags=["coaching"])
app.include_router(simulation_router, prefix="/api/simulation", tags=["simulation"])
app.include_router(calibration_router, prefix="/api/calibration", tags=["calibration"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
