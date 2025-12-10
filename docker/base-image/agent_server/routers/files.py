"""
File browser endpoints.
"""
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/files")
async def list_files(path: str = "/home/developer"):
    """
    List files in the workspace directory recursively.
    Only allows access to /home/developer for security.

    Returns a hierarchical tree structure with folders and files.
    """
    # Security: Only allow workspace access
    allowed_base = Path("/home/developer")
    requested_path = Path(path).resolve()

    # Ensure requested path is within workspace
    if not str(requested_path).startswith(str(allowed_base)):
        raise HTTPException(status_code=403, detail="Access denied: only /home/developer accessible")

    if not requested_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    def build_tree(directory: Path, base_path: Path) -> dict:
        """Build a hierarchical tree structure from a directory."""
        items = []
        total_files = 0

        try:
            # Get all items in directory
            dir_items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            for item in dir_items:
                # Skip hidden items
                if item.name.startswith('.'):
                    continue

                try:
                    stat = item.stat()
                    relative_path = item.relative_to(base_path)

                    if item.is_dir():
                        # Recursively build tree for subdirectory
                        subtree = build_tree(item, base_path)
                        items.append({
                            "name": item.name,
                            "path": str(relative_path),
                            "type": "directory",
                            "children": subtree["children"],
                            "file_count": subtree["file_count"],
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                        total_files += subtree["file_count"]
                    else:
                        # It's a file
                        items.append({
                            "name": item.name,
                            "path": str(relative_path),
                            "type": "file",
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                        total_files += 1

                except Exception as e:
                    logger.warning(f"Failed to process item {item}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to read directory {directory}: {e}")

        return {"children": items, "file_count": total_files}

    try:
        tree_data = build_tree(requested_path, allowed_base)

        return {
            "base_path": str(allowed_base),
            "requested_path": str(requested_path.relative_to(allowed_base)) if requested_path != allowed_base else ".",
            "tree": tree_data["children"],
            "total_files": tree_data["file_count"]
        }

    except Exception as e:
        logger.error(f"File listing error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/api/files/download")
async def download_file(path: str):
    """
    Download a file from the workspace.
    Only allows access to /home/developer for security.
    Max file size: 100MB

    Returns file content as plain text.
    """
    # Security: Only allow workspace access
    allowed_base = Path("/home/developer")

    # Handle both absolute and relative paths
    if path.startswith('/'):
        requested_path = Path(path).resolve()
    else:
        requested_path = (allowed_base / path).resolve()

    # Ensure requested path is within workspace
    if not str(requested_path).startswith(str(allowed_base)):
        raise HTTPException(status_code=403, detail="Access denied: only /home/developer accessible")

    if not requested_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not requested_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    # Check file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    file_size = requested_path.stat().st_size
    if file_size > max_size:
        raise HTTPException(status_code=413, detail=f"File too large: {file_size} bytes (max {max_size})")

    try:
        # Read file content
        content = requested_path.read_text(encoding='utf-8', errors='replace')
        return PlainTextResponse(content=content)

    except Exception as e:
        logger.error(f"File download error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
