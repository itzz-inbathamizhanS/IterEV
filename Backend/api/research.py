import os
import csv
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/research", tags=["research"])

RESULTS_DIR = Path("experiments/results")

def read_csv_as_dicts(filepath: Path) -> list[dict]:
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Result file {filepath.name} not found")
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def read_json_as_dict(filepath: Path) -> dict:
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Result file {filepath.name} not found")
    with open(filepath, mode="r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/baseline")
async def get_baseline(scenario: str = "constraint_feasible"):
    filename = f"baseline_comparison_{scenario.lower().replace(' ', '_')}.csv"
    data = read_csv_as_dicts(RESULTS_DIR / filename)
    return {"data": data, "metadata": {"source": filename}}

@router.get("/ablation")
async def get_ablation(scenario: str = "High Stress"):
    data = read_csv_as_dicts(RESULTS_DIR / "ablation.csv")
    filtered = [row for row in data if row.get("Condition", "") == scenario or row.get("condition", "") == scenario]
    return {"data": filtered, "metadata": {"source": "ablation.csv", "scenario": scenario}}

@router.get("/replication")
async def get_replication():
    data = read_csv_as_dicts(RESULTS_DIR / "independent_replication.csv")
    return {"data": data, "metadata": {"source": "independent_replication.csv"}}

@router.get("/monotonicity")
async def get_monotonicity():
    data = read_csv_as_dicts(RESULTS_DIR / "monotonicity.csv")
    return {"data": data, "metadata": {"source": "monotonicity.csv"}}

@router.get("/convergence")
async def get_convergence():
    data = read_csv_as_dicts(RESULTS_DIR / "mc_convergence.csv")
    return {"data": data, "metadata": {"source": "mc_convergence.csv"}}

@router.get("/sensitivity")
async def get_sensitivity(parameter: str):
    filename = f"{parameter.lower().replace(' ', '_')}_sensitivity.csv"
    data = read_csv_as_dicts(RESULTS_DIR / filename)
    return {"data": data, "metadata": {"source": filename}}

@router.get("/risk-decomposition")
async def get_risk_decomposition():
    filename = "risk_decomposition.csv"
    if not (RESULTS_DIR / filename).exists():
        raise HTTPException(status_code=404, detail="RESULT NOT GENERATED")
    data = read_csv_as_dicts(RESULTS_DIR / filename)
    return {"data": data, "metadata": {"source": filename}}

@router.get("/failure-taxonomy")
async def get_failure_taxonomy():
    data = read_json_as_dict(RESULTS_DIR / "failure_taxonomy.json")
    return {"data": data, "metadata": {"source": "failure_taxonomy.json"}}

@router.get("/trajectories")
async def get_trajectories():
    data = read_csv_as_dicts(RESULTS_DIR / "trajectories.csv")
    return {"data": data, "metadata": {"source": "trajectories.csv"}}

@router.get("/manifest")
async def get_manifest():
    data = read_json_as_dict(RESULTS_DIR / "reproducibility_manifest.json")
    return {"data": data, "metadata": {"source": "reproducibility_manifest.json"}}
