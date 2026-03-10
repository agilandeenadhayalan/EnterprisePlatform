"""
RL Dispatch Service — FastAPI application.

RL-based dispatch decision engine for driver-request matching.

ROUTES:
  POST /rl-dispatch/decide               — Make dispatch decision
  GET  /rl-dispatch/actions               — List actions
  GET  /rl-dispatch/actions/{id}          — Get action
  POST /rl-dispatch/reward                — Record reward
  GET  /rl-dispatch/policies              — List policies
  POST /rl-dispatch/policies              — Create policy
  POST /rl-dispatch/policies/{id}/activate — Activate policy
  GET  /rl-dispatch/stats                 — Stats
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
    description="RL-based dispatch decision engine for driver-request matching",
    lifespan=lifespan,
)


# ── Routes ──


@app.post("/rl-dispatch/decide", response_model=schemas.DecideResponse)
async def decide(req: schemas.DecideRequest):
    """Make a dispatch decision using the active policy."""
    action = repository.repo.decide(req.state, req.available_drivers, req.pending_requests)
    if action is None:
        raise HTTPException(status_code=404, detail="No active policy found or no drivers/requests available")
    active_policy = repository.repo.get_active_policy()
    return schemas.DecideResponse(
        action=schemas.DispatchActionResponse(**action.to_dict()),
        policy_used=active_policy.name if active_policy else "unknown",
    )


@app.get("/rl-dispatch/actions", response_model=schemas.DispatchActionListResponse)
async def list_actions(
    policy_id: Optional[str] = Query(default=None, description="Filter by policy ID"),
):
    """List all dispatch actions."""
    actions = repository.repo.list_actions(policy_id)
    return schemas.DispatchActionListResponse(
        actions=[schemas.DispatchActionResponse(**a.to_dict()) for a in actions],
        total=len(actions),
    )


@app.get("/rl-dispatch/actions/{action_id}", response_model=schemas.DispatchActionResponse)
async def get_action(action_id: str):
    """Get a specific dispatch action."""
    action = repository.repo.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")
    return schemas.DispatchActionResponse(**action.to_dict())


@app.post("/rl-dispatch/reward", response_model=schemas.RewardResponse)
async def record_reward(req: schemas.RewardRequest):
    """Record a reward for a dispatch action."""
    action = repository.repo.record_reward(req.action_id, req.reward)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action '{req.action_id}' not found")
    return schemas.RewardResponse(action_id=req.action_id, reward=req.reward, updated=True)


@app.get("/rl-dispatch/policies", response_model=schemas.PolicyListResponse)
async def list_policies():
    """List all dispatch policies."""
    policies = repository.repo.list_policies()
    return schemas.PolicyListResponse(
        policies=[schemas.DispatchPolicyResponse(**p.to_dict()) for p in policies],
        total=len(policies),
    )


@app.post("/rl-dispatch/policies", response_model=schemas.DispatchPolicyResponse, status_code=201)
async def create_policy(req: schemas.PolicyCreateRequest):
    """Create a new dispatch policy."""
    policy = repository.repo.create_policy(req.model_dump())
    return schemas.DispatchPolicyResponse(**policy.to_dict())


@app.post("/rl-dispatch/policies/{policy_id}/activate", response_model=schemas.DispatchPolicyResponse)
async def activate_policy(policy_id: str):
    """Activate a policy (deactivates all others)."""
    policy = repository.repo.activate_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    return schemas.DispatchPolicyResponse(**policy.to_dict())


@app.get("/rl-dispatch/stats", response_model=schemas.DispatchStatsResponse)
async def dispatch_stats():
    """Get dispatch statistics."""
    stats = repository.repo.get_stats()
    return schemas.DispatchStatsResponse(**stats)
