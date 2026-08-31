from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from app.repositories.csv_repository import InMemoryRepository
from simulation.scenarios import run_simulation_engine
from simulation.scenarios import setup_demo_csv_files

app = FastAPI(title="SmartDialer Prototype API", version="1.0.0")

# Setup demo repository for direct API queries
agents_csv, borrowers_csv = setup_demo_csv_files(10, 50)
global_repo = InMemoryRepository()
global_repo.load_from_csv(agents_csv, borrowers_csv)


class RunSimRequest(BaseModel):
    mode: str = "predictive"
    provider: str = "A"
    agents: int = 10
    borrowers: int = 50
    duration: float = 3.0


@app.get("/health")
def health_check():
    return {"status": "HEALTHY", "service": "SmartDialer"}


@app.get("/agents")
def get_agents():
    return list(global_repo.agents.values())


@app.get("/calls")
def get_calls():
    return list(global_repo.calls.values())


@app.post("/simulation/run")
async def run_simulation(req: RunSimRequest):
    metrics = await run_simulation_engine(
        mode=req.mode,
        provider_type=req.provider,
        agents_count=req.agents,
        borrowers_count=req.borrowers,
        duration=req.duration,
    )
    return metrics