"""
RL Training Environment Service — FastAPI application.

RL training environment management with episode tracking, replay buffers,
and training configs.

ROUTES:
  POST /rl-training/episodes              — Start episode
  GET  /rl-training/episodes              — List episodes
  GET  /rl-training/episodes/{id}         — Get episode
  POST /rl-training/episodes/{id}/step    — Record step
  POST /rl-training/episodes/{id}/complete — Complete episode
  GET  /rl-training/configs               — List configs
  POST /rl-training/configs               — Create config
  GET  /rl-training/stats                 — Stats
  GET  /health                            — Health check
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import Query, HTTPException

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
    description="RL training environment management with episode tracking, replay buffers, and training configs",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/rl-training/episodes", response_model=schemas.TrainingEpisodeResponse, status_code=201)
async def start_episode(req: schemas.StartEpisodeRequest):
    """Start a new training episode."""
    episode = repository.repo.start_episode(req.model_dump())
    return schemas.TrainingEpisodeResponse(**episode.to_dict())


@app.get("/rl-training/episodes", response_model=schemas.EpisodeListResponse)
async def list_episodes(
    env_name: Optional[str] = Query(default=None, description="Filter by environment name"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
):
    """List all training episodes."""
    episodes = repository.repo.list_episodes(env_name, status)
    return schemas.EpisodeListResponse(
        episodes=[schemas.TrainingEpisodeResponse(**e.to_dict()) for e in episodes],
        total=len(episodes),
    )


@app.get("/rl-training/episodes/{episode_id}", response_model=schemas.TrainingEpisodeResponse)
async def get_episode(episode_id: str):
    """Get a specific training episode."""
    episode = repository.repo.get_episode(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail=f"Episode '{episode_id}' not found")
    return schemas.TrainingEpisodeResponse(**episode.to_dict())


@app.post("/rl-training/episodes/{episode_id}/step", response_model=schemas.StepResponse)
async def record_step(episode_id: str, req: schemas.StepRequest):
    """Record a step in a training episode."""
    episode = repository.repo.record_step(episode_id, req.model_dump())
    if not episode:
        raise HTTPException(status_code=404, detail=f"Episode '{episode_id}' not found")
    return schemas.StepResponse(
        episode_id=episode.id,
        steps=episode.steps,
        total_reward=episode.total_reward,
        done=req.done,
        status=episode.status,
    )


@app.post("/rl-training/episodes/{episode_id}/complete", response_model=schemas.TrainingEpisodeResponse)
async def complete_episode(episode_id: str):
    """Complete a training episode."""
    episode = repository.repo.complete_episode(episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail=f"Episode '{episode_id}' not found")
    return schemas.TrainingEpisodeResponse(**episode.to_dict())


@app.get("/rl-training/configs", response_model=schemas.ConfigListResponse)
async def list_configs():
    """List all training configs."""
    configs = repository.repo.list_configs()
    return schemas.ConfigListResponse(
        configs=[schemas.TrainingConfigResponse(**c.to_dict()) for c in configs],
        total=len(configs),
    )


@app.post("/rl-training/configs", response_model=schemas.TrainingConfigResponse, status_code=201)
async def create_config(req: schemas.CreateConfigRequest):
    """Create a new training config."""
    config = repository.repo.create_config(req.model_dump())
    return schemas.TrainingConfigResponse(**config.to_dict())


@app.get("/rl-training/stats", response_model=schemas.TrainingStatsResponse)
async def training_stats():
    """Get training statistics."""
    stats = repository.repo.get_stats()
    return schemas.TrainingStatsResponse(**stats)
