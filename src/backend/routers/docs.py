"""
Documentation router - serves process documentation files.

Provides endpoints for:
- Listing available documentation
- Serving markdown content
- Documentation index
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import json

router = APIRouter(prefix="/api/docs", tags=["Documentation"])

# Documentation directory - relative to trinity root
# In Docker, /app/config/process-docs
# In development, ../../../config/process-docs
DOCS_PATHS = [
    Path("/app/config/process-docs"),
    Path(__file__).parent.parent.parent.parent / "config" / "process-docs",
]


def get_docs_dir() -> Path:
    """Find the documentation directory."""
    for path in DOCS_PATHS:
        if path.exists():
            return path
    return None


@router.get("/index")
async def get_docs_index():
    """Get documentation index/navigation structure."""
    docs_dir = get_docs_dir()
    if not docs_dir:
        raise HTTPException(status_code=404, detail="Documentation directory not found")

    index_path = docs_dir / "index.json"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Documentation index not found")

    try:
        with open(index_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read index: {str(e)}")


@router.get("/content/{slug:path}")
async def get_doc_content(slug: str):
    """Get documentation content by slug."""
    docs_dir = get_docs_dir()
    if not docs_dir:
        raise HTTPException(status_code=404, detail="Documentation directory not found")

    # Security: Prevent path traversal
    if ".." in slug or slug.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid document path")

    # Try with .md extension
    doc_path = docs_dir / f"{slug}.md"
    if not doc_path.exists():
        # Maybe the slug already includes the extension
        doc_path = docs_dir / slug
        if not doc_path.exists() or not doc_path.suffix == ".md":
            raise HTTPException(status_code=404, detail="Document not found")

    # Verify the path is still within docs_dir (security)
    try:
        doc_path.resolve().relative_to(docs_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document path")

    try:
        content = doc_path.read_text(encoding="utf-8")
        return JSONResponse(content={"content": content, "slug": slug})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read document: {str(e)}")


@router.get("/list")
async def list_docs():
    """List all available documentation files."""
    docs_dir = get_docs_dir()
    if not docs_dir:
        raise HTTPException(status_code=404, detail="Documentation directory not found")

    docs = []
    for md_file in docs_dir.rglob("*.md"):
        relative_path = md_file.relative_to(docs_dir)
        slug = str(relative_path).replace(".md", "")
        docs.append({
            "slug": slug,
            "path": str(relative_path),
            "title": md_file.stem.replace("-", " ").title()
        })

    return {"documents": docs}
