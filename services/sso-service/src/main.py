"""
SSO Service — FastAPI application.

ROUTES:
  GET    /sso/providers                     — List enabled SSO providers
  POST   /sso/authorize                     — Start SSO flow (returns authorization URL)
  POST   /sso/callback                      — Handle SSO callback (mock — create/link user)
  GET    /sso/connections                    — List current user's SSO connections (requires auth)
  DELETE /sso/connections/{connection_id}    — Unlink SSO provider
  GET    /health                            — Health check (provided by create_app)
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root for mobility-common imports
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "shared" / "python" / "mobility-common" / "src"))
# Add service src for local imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mobility_common.fastapi.app import create_app
from mobility_common.fastapi.database import create_engine_and_session, get_db, dispose_engine
from mobility_common.fastapi.errors import not_found, conflict
from mobility_common.fastapi.middleware import get_current_user, TokenPayload

import config as sso_config
import models  # noqa: F401 — needed so SQLAlchemy sees the models
import schemas
import repository


@asynccontextmanager
async def lifespan(app):
    """Startup: create DB engine. Shutdown: close connections."""
    create_engine_and_session(sso_config.settings.database_url)
    yield
    await dispose_engine()


app = create_app(
    title="SSO Service",
    version="0.1.0",
    description="SSO provider integration and account linking for Smart Mobility Platform",
    lifespan=lifespan,
)


# -- Routes --


@app.get("/sso/providers", response_model=list[schemas.SsoProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_db)):
    """List all enabled SSO providers."""
    repo = repository.SsoRepository(db)
    providers = await repo.list_enabled_providers()
    return [
        schemas.SsoProviderResponse(
            id=str(p.id),
            name=p.name,
            display_name=p.display_name,
            provider_type=p.provider_type,
            authorization_url=p.authorization_url,
            scopes=p.scopes,
            is_enabled=p.is_enabled,
        )
        for p in providers
    ]


@app.post("/sso/authorize", response_model=schemas.AuthorizeResponse)
async def authorize(
    body: schemas.AuthorizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start the SSO authorization flow.

    Returns an authorization URL that the client should redirect the user to.
    The state parameter is used for CSRF protection — the client must store it
    and verify it in the callback.
    """
    repo = repository.SsoRepository(db)

    provider = await repo.get_provider_by_name(body.provider_name)
    if not provider:
        raise not_found("SSO Provider", body.provider_name)

    if not provider.is_enabled:
        raise not_found("SSO Provider", body.provider_name)

    state = repo.generate_state()
    auth_url = repo.build_authorization_url(provider, body.redirect_uri, state)

    return schemas.AuthorizeResponse(
        authorization_url=auth_url,
        state=state,
        provider_name=provider.name,
    )


@app.post("/sso/callback", response_model=schemas.CallbackResponse)
async def callback(
    body: schemas.CallbackRequest,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle the SSO callback after the user authorizes with the provider.

    MOCK IMPLEMENTATION: In production, this would exchange the authorization
    code for tokens and fetch the user's profile from the provider. Here we
    simulate the flow by generating a mock external user ID.
    """
    repo = repository.SsoRepository(db)

    provider = await repo.get_provider_by_name(body.provider_name)
    if not provider:
        raise not_found("SSO Provider", body.provider_name)

    # Mock: generate an external user ID from the code
    # In production: exchange code for tokens, then call userinfo endpoint
    external_user_id = f"{body.provider_name}_{body.code[:8]}"
    external_email = f"{external_user_id}@{body.provider_name}.example.com"

    # Check if this external identity is already linked
    existing = await repo.get_connection_by_external(
        str(provider.id), external_user_id
    )
    if existing:
        raise conflict(
            f"External identity '{external_user_id}' is already linked to a user"
        )

    # Create the SSO connection
    connection = await repo.create_connection(
        user_id=user.sub,
        provider_id=str(provider.id),
        external_user_id=external_user_id,
        external_email=external_email,
    )

    return schemas.CallbackResponse(
        user_id=user.sub,
        provider_name=body.provider_name,
        external_user_id=external_user_id,
        external_email=external_email,
    )


@app.get("/sso/connections", response_model=list[schemas.SsoConnectionResponse])
async def list_connections(
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all SSO connections for the authenticated user."""
    repo = repository.SsoRepository(db)
    rows = await repo.get_user_connections(user.sub)
    return [
        schemas.SsoConnectionResponse(
            id=str(conn.id),
            provider_name=provider.name,
            provider_display_name=provider.display_name,
            external_user_id=conn.external_user_id,
            external_email=conn.external_email,
            external_name=conn.external_name,
            connected_at=conn.connected_at,
            last_login_at=conn.last_login_at,
        )
        for conn, provider in rows
    ]


@app.delete("/sso/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unlink an SSO provider from the authenticated user's account."""
    repo = repository.SsoRepository(db)
    connection = await repo.get_connection_by_id(connection_id)
    if not connection:
        raise not_found("SSO Connection", connection_id)

    # Only the owner can unlink their own SSO connection
    if str(connection.user_id) != user.sub:
        from mobility_common.fastapi.errors import forbidden
        raise forbidden("You can only unlink your own SSO connections")

    await repo.delete_connection(connection_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=sso_config.settings.service_port,
        reload=sso_config.settings.debug,
    )
