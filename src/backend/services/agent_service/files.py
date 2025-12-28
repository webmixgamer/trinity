"""
Agent Service Files - File browser operations.

Handles file listing, download, preview, and delete for agent workspaces.
"""
import logging

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from models import User
from database import db
from services.docker_service import get_agent_container
from services.audit_service import log_audit_event

logger = logging.getLogger(__name__)


async def list_agent_files_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> dict:
    """
    List files in the agent's workspace directory.
    Returns a flat list of files with metadata (name, size, modified date).
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.reload()
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to browse files")

    try:
        # Call agent's internal file listing API
        agent_url = f"http://agent-{agent_name}:8000/api/files"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(agent_url, params={"path": path})
            if response.status_code == 200:
                # Audit log the file list access
                await log_audit_event(
                    event_type="file_access",
                    action="file_list",
                    user_id=current_user.username,
                    agent_name=agent_name,
                    ip_address=request.client.host if request.client else None,
                    details={"path": path},
                    result="success"
                )
                return response.json()
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to list files: {response.text}"
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File listing timed out")
    except HTTPException:
        raise
    except Exception as e:
        await log_audit_event(
            event_type="file_access",
            action="file_list",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            details={"path": path, "error": str(e)},
            result="error"
        )
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


async def download_agent_file_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> PlainTextResponse:
    """
    Download a file from the agent's workspace.
    Returns the file content as plain text.
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.reload()
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to download files")

    try:
        # Call agent's internal file download API
        agent_url = f"http://agent-{agent_name}:8000/api/files/download"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(agent_url, params={"path": path})
            if response.status_code == 200:
                # Audit log the file download
                await log_audit_event(
                    event_type="file_access",
                    action="file_download",
                    user_id=current_user.username,
                    agent_name=agent_name,
                    ip_address=request.client.host if request.client else None,
                    details={"file_path": path},
                    result="success"
                )
                return PlainTextResponse(content=response.text)
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to download file: {response.text}"
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File download timed out")
    except HTTPException:
        raise
    except Exception as e:
        await log_audit_event(
            event_type="file_access",
            action="file_download",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            details={"file_path": path, "error": str(e)},
            result="error"
        )
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


async def delete_agent_file_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> dict:
    """
    Delete a file or directory from the agent's workspace.
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.reload()
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to delete files")

    try:
        # Call agent's internal file delete API
        agent_url = f"http://agent-{agent_name}:8000/api/files"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(agent_url, params={"path": path})
            if response.status_code == 200:
                result = response.json()
                # Audit log the file deletion
                await log_audit_event(
                    event_type="file_access",
                    action="file_delete",
                    user_id=current_user.username,
                    agent_name=agent_name,
                    ip_address=request.client.host if request.client else None,
                    details={
                        "path": path,
                        "type": result.get("type", "unknown"),
                        "file_count": result.get("file_count", 1)
                    },
                    result="success"
                )
                return result
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", f"Failed to delete: {response.text}")
                )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File deletion timed out")
    except HTTPException:
        raise
    except Exception as e:
        await log_audit_event(
            event_type="file_access",
            action="file_delete",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            details={"path": path, "error": str(e)},
            result="error"
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


async def preview_agent_file_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> StreamingResponse:
    """
    Get file with proper MIME type for preview.
    Streams the response from the agent container.
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    container.reload()
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to preview files")

    try:
        # Call agent's internal file preview API
        agent_url = f"http://agent-{agent_name}:8000/api/files/preview"

        # We need to stream the response for large files like videos
        async def stream_content():
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("GET", agent_url, params={"path": path}) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Failed to preview file: {error_body.decode()}"
                        )
                    async for chunk in response.aiter_bytes():
                        yield chunk

        # First make a HEAD-like request to get content-type
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(agent_url, params={"path": path})
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.json().get("detail", f"Failed to preview: {response.text}")
                )

            content_type = response.headers.get("content-type", "application/octet-stream")
            content_disposition = response.headers.get("content-disposition")

            # Audit log the preview access
            await log_audit_event(
                event_type="file_access",
                action="file_preview",
                user_id=current_user.username,
                agent_name=agent_name,
                ip_address=request.client.host if request.client else None,
                details={"file_path": path, "content_type": content_type},
                result="success"
            )

            # For small files, return directly
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers={"Content-Disposition": content_disposition} if content_disposition else {}
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File preview timed out")
    except HTTPException:
        raise
    except Exception as e:
        await log_audit_event(
            event_type="file_access",
            action="file_preview",
            user_id=current_user.username,
            agent_name=agent_name,
            ip_address=request.client.host if request.client else None,
            details={"file_path": path, "error": str(e)},
            result="error"
        )
        raise HTTPException(status_code=500, detail=f"Failed to preview file: {str(e)}")
