"""
Bandit Service — FastAPI application.

Multi-armed bandit experiment management with epsilon-greedy, UCB1, and Thompson sampling.

ROUTES:
  POST /bandits                  — Create bandit experiment
  GET  /bandits                  — List bandits
  GET  /bandits/{id}             — Get bandit detail
  POST /bandits/{id}/pull        — Select arm
  POST /bandits/{id}/reward      — Record reward
  GET  /bandits/{id}/decisions   — List decisions
  GET  /bandits/{id}/stats       — Arm performance stats
  POST /bandits/{id}/reset       — Reset arm counts
  GET  /health                   — Health check
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app

import config as service_config
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    yield


app = create_app(
    title=service_config.settings.service_name,
    version="0.1.0",
    description="Multi-armed bandit experiment management with epsilon-greedy, UCB1, and Thompson sampling",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/bandits", response_model=schemas.BanditExperimentResponse, status_code=201)
async def create_bandit(req: schemas.BanditCreateRequest):
    """Create a new bandit experiment."""
    bandit = repository.repo.create_bandit(req.model_dump())
    return schemas.BanditExperimentResponse(**bandit.to_dict())


@app.get("/bandits", response_model=schemas.BanditListResponse)
async def list_bandits():
    """List all bandit experiments."""
    bandits = repository.repo.list_bandits()
    return schemas.BanditListResponse(
        bandits=[schemas.BanditExperimentResponse(**b.to_dict()) for b in bandits],
        total=len(bandits),
    )


@app.get("/bandits/{bandit_id}", response_model=schemas.BanditExperimentResponse)
async def get_bandit(bandit_id: str):
    """Get a bandit experiment by ID."""
    bandit = repository.repo.get_bandit(bandit_id)
    if not bandit:
        raise HTTPException(status_code=404, detail=f"Bandit '{bandit_id}' not found")
    return schemas.BanditExperimentResponse(**bandit.to_dict())


@app.post("/bandits/{bandit_id}/pull", response_model=schemas.PullResponse)
async def pull_arm(bandit_id: str):
    """Select an arm using the bandit's algorithm."""
    arm_name = repository.repo.pull(bandit_id)
    if arm_name is None:
        raise HTTPException(status_code=404, detail=f"Bandit '{bandit_id}' not found")
    return schemas.PullResponse(arm_selected=arm_name, experiment_id=bandit_id)


@app.post("/bandits/{bandit_id}/reward", response_model=schemas.RewardResponse)
async def record_reward(bandit_id: str, req: schemas.RewardRequest):
    """Record a reward for an arm."""
    result = repository.repo.record_reward(bandit_id, req.arm_name, req.reward, req.success)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Bandit '{bandit_id}' not found")
    if result == "arm_not_found":
        raise HTTPException(status_code=404, detail=f"Arm '{req.arm_name}' not found in bandit '{bandit_id}'")
    return schemas.RewardResponse(
        experiment_id=bandit_id,
        arm_name=req.arm_name,
        reward=req.reward,
        success=req.success,
        updated_arm=result,
    )


@app.get("/bandits/{bandit_id}/decisions", response_model=schemas.DecisionListResponse)
async def list_decisions(bandit_id: str):
    """List decisions for a bandit experiment."""
    decisions = repository.repo.list_decisions(bandit_id)
    return schemas.DecisionListResponse(
        decisions=[schemas.BanditDecisionResponse(**d.to_dict()) for d in decisions],
        total=len(decisions),
    )


@app.get("/bandits/{bandit_id}/stats", response_model=schemas.BanditStatsResponse)
async def bandit_stats(bandit_id: str):
    """Get arm performance statistics."""
    stats = repository.repo.get_stats(bandit_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Bandit '{bandit_id}' not found")
    return schemas.BanditStatsResponse(
        experiment_id=stats["experiment_id"],
        arms=[schemas.ArmStatsResponse(**a) for a in stats["arms"]],
    )


@app.post("/bandits/{bandit_id}/reset", response_model=schemas.BanditExperimentResponse)
async def reset_bandit(bandit_id: str):
    """Reset all arm counts to zero."""
    bandit = repository.repo.reset(bandit_id)
    if not bandit:
        raise HTTPException(status_code=404, detail=f"Bandit '{bandit_id}' not found")
    return schemas.BanditExperimentResponse(**bandit.to_dict())
