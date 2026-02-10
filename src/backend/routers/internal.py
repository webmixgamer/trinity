"""
Internal agent-to-backend endpoints (no authentication required).

These endpoints are called by agent containers on the Docker network
to communicate back to the backend. They are not exposed externally.
"""
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
)


@router.get("/health")
async def internal_health():
    """Internal health check for agent containers."""
    return {"status": "ok"}
