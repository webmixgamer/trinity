"""
Public endpoints for unauthenticated access (Phase 12.2: Public Agent Links).

These endpoints do NOT require authentication and are used by public users
to access agents via shareable links.
"""
import httpx
import logging
from fastapi import APIRouter, HTTPException, Request

from database import (
    db,
    PublicLinkInfo,
    VerificationRequest,
    VerificationConfirm,
    VerificationResponse,
    PublicChatRequest,
    PublicChatResponse
)
from services.docker_service import get_agent_container
from services.email_service import email_service



logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["public"])

# Rate limiting constants
MAX_VERIFICATION_REQUESTS_PER_EMAIL = 3  # per 10 minutes
MAX_CHAT_MESSAGES_PER_IP = 30  # per minute


def _get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/link/{token}", response_model=PublicLinkInfo)
async def get_public_link_info(token: str, request: Request):
    """
    Get information about a public link.

    Returns whether the link is valid and if email verification is required.
    Also includes agent metadata (name, description, status flags).
    Does NOT expose sensitive data like the link ID.
    """
    is_valid, reason, link = db.is_public_link_valid(token)

    if not is_valid:
        return PublicLinkInfo(
            valid=False,
            require_email=False,
            agent_available=False,
            reason=reason
        )

    agent_name = link["agent_name"]

    # Check if agent is available
    container = get_agent_container(agent_name)
    agent_available = container is not None and container.status == "running"

    # Get agent metadata from database
    is_autonomous = db.get_autonomy_enabled(agent_name)
    read_only_data = db.get_read_only_mode(agent_name)
    is_read_only = read_only_data.get("enabled", False)

    # Get display name and description from template.yaml (if agent running)
    agent_display_name = agent_name  # Fallback to agent name
    agent_description = None

    if agent_available:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://agent-{agent_name}:8000/api/template/info")
                if response.status_code == 200:
                    info = response.json()
                    agent_display_name = info.get("name") or info.get("display_name") or agent_name
                    agent_description = info.get("description")
        except Exception as e:
            logger.warning(f"Failed to fetch template info for {agent_name}: {e}")
            # Use container labels as fallback
            if container:
                labels = container.labels or {}
                agent_display_name = labels.get("trinity.agent-type", agent_name)

    return PublicLinkInfo(
        valid=True,
        require_email=link["require_email"],
        agent_available=agent_available,
        reason=None,
        agent_display_name=agent_display_name,
        agent_description=agent_description,
        is_autonomous=is_autonomous,
        is_read_only=is_read_only
    )


@router.post("/verify/request")
async def request_verification_code(
    verification: VerificationRequest,
    request: Request
):
    """
    Request an email verification code.

    Sends a 6-digit code to the provided email address.
    Rate limited to 3 requests per email per 10 minutes.
    """
    # Validate link token
    is_valid, reason, link = db.is_public_link_valid(verification.token)
    if not is_valid:
        raise HTTPException(status_code=404, detail=f"Invalid link: {reason}")

    if not link["require_email"]:
        raise HTTPException(
            status_code=400,
            detail="This link does not require email verification"
        )

    # Rate limiting
    recent_requests = db.count_recent_verification_requests(verification.email, minutes=10)
    if recent_requests >= MAX_VERIFICATION_REQUESTS_PER_EMAIL:
        raise HTTPException(
            status_code=429,
            detail="Too many verification requests. Please wait 10 minutes."
        )

    # Create verification code
    verification_data = db.create_verification(
        link_id=link["id"],
        email=verification.email,
        expiry_minutes=10
    )

    # Send email
    email_sent = await email_service.send_verification_code(
        verification.email,
        verification_data["code"]
    )

    if not email_sent:
        logger.error(f"Failed to send verification email to {verification.email}")
        # Don't expose email failure details to client
        raise HTTPException(
            status_code=500,
            detail="Failed to send verification code. Please try again."
        )

    return {
        "message": "Verification code sent",
        "expires_in_seconds": verification_data["expires_in_seconds"]
    }


@router.post("/verify/confirm", response_model=VerificationResponse)
async def confirm_verification_code(
    confirmation: VerificationConfirm,
    request: Request
):
    """
    Confirm an email verification code.

    Returns a session token if the code is valid.
    """
    # Validate link token
    is_valid, reason, link = db.is_public_link_valid(confirmation.token)
    if not is_valid:
        raise HTTPException(status_code=404, detail=f"Invalid link: {reason}")

    # Verify the code
    success, error, session_data = db.verify_code(
        link_id=link["id"],
        email=confirmation.email,
        code=confirmation.code,
        session_hours=24
    )

    if not success:
        return VerificationResponse(
            verified=False,
            error=error
        )

    return VerificationResponse(
        verified=True,
        session_token=session_data["session_token"],
        expires_at=session_data["expires_at"]
    )


@router.post("/chat/{token}", response_model=PublicChatResponse)
async def public_chat(
    token: str,
    chat_request: PublicChatRequest,
    request: Request
):
    """
    Send a chat message via a public link.

    Uses the parallel task execution endpoint (stateless, no conversation context).
    For links requiring email verification, a valid session_token must be provided.
    """
    client_ip = _get_client_ip(request)

    # Validate link token
    is_valid, reason, link = db.is_public_link_valid(token)
    if not is_valid:
        raise HTTPException(status_code=404, detail=f"Invalid link: {reason}")

    # Verify session if email required
    verified_email = None
    if link["require_email"]:
        if not chat_request.session_token:
            raise HTTPException(
                status_code=401,
                detail="Session token required for this link"
            )

        session_valid, email = db.validate_session(link["id"], chat_request.session_token)
        if not session_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session. Please verify your email again."
            )
        verified_email = email

    # Rate limiting by IP
    recent_messages = db.count_recent_messages_by_ip(client_ip, minutes=1)
    if recent_messages >= MAX_CHAT_MESSAGES_PER_IP:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a moment."
        )

    # Check agent is available
    container = get_agent_container(link["agent_name"])
    if not container or container.status != "running":
        raise HTTPException(
            status_code=503,
            detail="Agent is not available. Please try again later."
        )

    agent_name = link["agent_name"]

    # Record usage BEFORE making the request
    db.record_public_link_usage(
        link_id=link["id"],
        email=verified_email,
        ip_address=client_ip
    )

    # Execute via parallel task endpoint (stateless)
    # Uses Docker network to reach agent container directly
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"http://agent-{agent_name}:8000/api/task",
                json={
                    "message": chat_request.message,
                    "timeout_seconds": 120
                }
            )

            if response.status_code != 200:
                logger.error(f"Agent task failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail="Failed to process your request. Please try again."
                )

            result = response.json()

            return PublicChatResponse(
                response=result.get("response", result.get("result", "")),
                usage=result.get("usage")
            )

    except httpx.TimeoutException:
        logger.error(f"Agent request timed out for {link['agent_name']}")
        raise HTTPException(
            status_code=504,
            detail="Request timed out. Please try again with a simpler question."
        )
    except httpx.RequestError as e:
        logger.error(f"Agent request failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to reach the agent. Please try again."
        )


# Introduction prompt - asks agent to introduce itself
INTRO_PROMPT = """Provide a brief 2-paragraph introduction of yourself.

First paragraph: Who you are and what you do.
Second paragraph: Your purpose and how you can help the user.

Be concise, welcoming, and conversational. Do not use headers, bullet points, or markdown formatting."""


@router.get("/intro/{token}")
async def get_agent_intro(
    token: str,
    request: Request,
    session_token: str = None
):
    """
    Get an introduction message from the agent.

    Sends a prompt asking the agent to introduce itself.
    Used to provide context to users before they start chatting.
    For links requiring email verification, a valid session_token query param must be provided.
    """
    client_ip = _get_client_ip(request)

    # Validate link token
    is_valid, reason, link = db.is_public_link_valid(token)
    if not is_valid:
        raise HTTPException(status_code=404, detail=f"Invalid link: {reason}")

    # Verify session if email required
    if link["require_email"]:
        if not session_token:
            raise HTTPException(
                status_code=401,
                detail="Session token required for this link"
            )

        session_valid, email = db.validate_session(link["id"], session_token)
        if not session_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session. Please verify your email again."
            )

    # Check agent is available
    container = get_agent_container(link["agent_name"])
    if not container or container.status != "running":
        raise HTTPException(
            status_code=503,
            detail="Agent is not available. Please try again later."
        )

    agent_name = link["agent_name"]

    # Execute intro prompt via parallel task endpoint
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"http://agent-{agent_name}:8000/api/task",
                json={
                    "message": INTRO_PROMPT,
                    "timeout_seconds": 60
                }
            )

            if response.status_code != 200:
                logger.error(f"Agent intro failed: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail="Failed to get introduction. Please try again."
                )

            result = response.json()

            return {
                "intro": result.get("response", result.get("result", ""))
            }

    except httpx.TimeoutException:
        logger.error(f"Agent intro request timed out for {link['agent_name']}")
        raise HTTPException(
            status_code=504,
            detail="Request timed out. Please try again."
        )
    except httpx.RequestError as e:
        logger.error(f"Agent intro request failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Failed to reach the agent. Please try again."
        )
