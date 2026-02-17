"""
Public endpoints for unauthenticated access (Phase 12.2: Public Agent Links).

These endpoints do NOT require authentication and are used by public users
to access agents via shareable links.
"""
import secrets
import httpx
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import (
    db,
    PublicLinkInfo,
    VerificationRequest,
    VerificationConfirm,
    VerificationResponse,
    PublicChatRequest,
    PublicChatResponse,
    PublicChatMessage
)
from services.docker_service import get_agent_container
from services.email_service import email_service


class PublicChatHistoryResponse(BaseModel):
    """Response model for chat history endpoint."""
    messages: List[dict]
    session_id: str
    message_count: int


class ClearSessionResponse(BaseModel):
    """Response model for clear session endpoint."""
    cleared: bool
    new_session_id: Optional[str] = None



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
    Send a chat message via a public link with conversation persistence.

    For links requiring email verification, a valid session_token must be provided.
    For anonymous links, a session_id can be provided to maintain conversation context.
    Returns session_id for anonymous links to store in localStorage.
    """
    client_ip = _get_client_ip(request)

    # Validate link token
    is_valid, reason, link = db.is_public_link_valid(token)
    if not is_valid:
        raise HTTPException(status_code=404, detail=f"Invalid link: {reason}")

    # Determine session identifier and type
    session_identifier = None
    identifier_type = None
    verified_email = None

    if link["require_email"]:
        # Email-required link: use verified email as identifier
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
        session_identifier = email.lower()
        identifier_type = "email"
    else:
        # Anonymous link: use provided session_id or generate new one
        if chat_request.session_id:
            session_identifier = chat_request.session_id
        else:
            session_identifier = secrets.token_urlsafe(16)
        identifier_type = "anonymous"

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

    # Get or create chat session
    chat_session = db.get_or_create_public_chat_session(
        link_id=link["id"],
        session_identifier=session_identifier,
        identifier_type=identifier_type
    )

    # Store user message
    db.add_public_chat_message(
        session_id=chat_session.id,
        role="user",
        content=chat_request.message
    )

    # Record usage
    db.record_public_link_usage(
        link_id=link["id"],
        email=verified_email,
        ip_address=client_ip
    )

    # Build context-enriched prompt with conversation history
    context_prompt = db.build_public_chat_context(
        session_id=chat_session.id,
        new_message=chat_request.message,
        max_turns=10
    )

    # Execute via parallel task endpoint
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"http://agent-{agent_name}:8000/api/task",
                json={
                    "message": context_prompt,
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
            assistant_response = result.get("response", result.get("result", ""))

            # Calculate cost from usage if available
            cost = None
            usage = result.get("usage")
            if usage:
                # Rough cost estimate (adjust rates as needed)
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)

            # Store assistant response
            db.add_public_chat_message(
                session_id=chat_session.id,
                role="assistant",
                content=assistant_response,
                cost=cost
            )

            # Get updated message count
            updated_session = db.get_public_chat_session(chat_session.id)
            message_count = updated_session.message_count if updated_session else 0

            return PublicChatResponse(
                response=assistant_response,
                session_id=session_identifier if identifier_type == "anonymous" else None,
                message_count=message_count,
                usage=usage
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


@router.get("/history/{token}", response_model=PublicChatHistoryResponse)
async def get_public_chat_history(
    token: str,
    request: Request,
    session_token: str = None,
    session_id: str = None
):
    """
    Get chat history for a public link session.

    For email-required links, provide session_token query param.
    For anonymous links, provide session_id query param.
    Returns messages array for current session, or empty if no history.
    """
    # Validate link token
    is_valid, reason, link = db.is_public_link_valid(token)
    if not is_valid:
        raise HTTPException(status_code=404, detail=f"Invalid link: {reason}")

    # Determine session identifier
    session_identifier = None

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
        session_identifier = email.lower()
    else:
        if not session_id:
            # No session_id means no history yet
            return PublicChatHistoryResponse(
                messages=[],
                session_id="",
                message_count=0
            )
        session_identifier = session_id

    # Look up session
    chat_session = db.get_public_chat_session_by_identifier(
        link_id=link["id"],
        session_identifier=session_identifier
    )

    if not chat_session:
        return PublicChatHistoryResponse(
            messages=[],
            session_id=session_identifier if not link["require_email"] else "",
            message_count=0
        )

    # Get messages (oldest first for display)
    messages = db.get_recent_public_chat_messages(chat_session.id, limit=100)

    return PublicChatHistoryResponse(
        messages=[
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ],
        session_id=session_identifier if not link["require_email"] else "",
        message_count=chat_session.message_count
    )


@router.delete("/session/{token}", response_model=ClearSessionResponse)
async def clear_public_session(
    token: str,
    request: Request,
    session_token: str = None,
    session_id: str = None
):
    """
    Clear a public chat session (start new conversation).

    For email-required links, provide session_token query param.
    For anonymous links, provide session_id query param.
    Returns new_session_id for anonymous links to update localStorage.
    """
    # Validate link token
    is_valid, reason, link = db.is_public_link_valid(token)
    if not is_valid:
        raise HTTPException(status_code=404, detail=f"Invalid link: {reason}")

    # Determine session identifier
    session_identifier = None

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
        session_identifier = email.lower()
    else:
        if not session_id:
            raise HTTPException(
                status_code=400,
                detail="session_id required for anonymous links"
            )
        session_identifier = session_id

    # Look up and delete session
    chat_session = db.get_public_chat_session_by_identifier(
        link_id=link["id"],
        session_identifier=session_identifier
    )

    if chat_session:
        db.clear_public_chat_session(chat_session.id)

    # For anonymous links, generate new session_id
    new_session_id = None
    if not link["require_email"]:
        new_session_id = secrets.token_urlsafe(16)

    return ClearSessionResponse(
        cleared=True,
        new_session_id=new_session_id
    )
