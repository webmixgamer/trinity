"""
Skills listing endpoint for agent playbooks.

Scans .claude/skills/ directory for SKILL.md files, parses YAML frontmatter,
and returns skill metadata for the Playbooks tab in the Trinity UI.
"""
import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class SkillInfo(BaseModel):
    """Information about a single skill/playbook."""
    name: str
    description: Optional[str] = None
    path: str
    user_invocable: bool = True
    automation: Optional[str] = None  # autonomous, gated, manual, null
    allowed_tools: Optional[List[str]] = None
    argument_hint: Optional[str] = None
    has_schedule: bool = False  # Placeholder for future schedule integration


class SkillsResponse(BaseModel):
    """Response for GET /api/skills endpoint."""
    skills: List[SkillInfo]
    count: int
    skill_paths: List[str]


def parse_yaml_frontmatter(content: str) -> Dict[str, Any]:
    """
    Parse YAML frontmatter from a SKILL.md file.

    Frontmatter is delimited by --- at the start and end:
    ---
    name: my-skill
    description: Does something
    ---
    """
    # Match YAML frontmatter at the start of the file
    pattern = r'^---\s*\n(.*?)\n---'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return {}

    try:
        import yaml
        frontmatter = yaml.safe_load(match.group(1))
        return frontmatter if isinstance(frontmatter, dict) else {}
    except Exception as e:
        logger.warning(f"Failed to parse YAML frontmatter: {e}")
        return {}


def extract_description_from_body(content: str) -> Optional[str]:
    """
    Extract description from the first paragraph after frontmatter.
    Falls back to first non-empty line if no clear paragraph.
    """
    # Remove frontmatter
    pattern = r'^---\s*\n.*?\n---\s*\n?'
    body = re.sub(pattern, '', content, flags=re.DOTALL)

    # Get first non-empty paragraph (skip headers)
    lines = body.strip().split('\n')
    description_lines = []

    for line in lines:
        stripped = line.strip()
        # Skip empty lines and headers
        if not stripped or stripped.startswith('#'):
            if description_lines:
                break
            continue
        description_lines.append(stripped)

    if description_lines:
        description = ' '.join(description_lines)
        # Truncate at ~200 chars on word boundary
        if len(description) > 200:
            description = description[:197].rsplit(' ', 1)[0] + '...'
        return description

    return None


def scan_skills_directory(skills_dir: Path) -> List[SkillInfo]:
    """
    Scan a skills directory for subdirectories containing SKILL.md files.

    Returns list of SkillInfo objects sorted by name.
    """
    skills = []

    if not skills_dir.exists():
        return skills

    # Scan for subdirectories with SKILL.md
    for entry in skills_dir.iterdir():
        if not entry.is_dir():
            continue

        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            content = skill_md.read_text(encoding='utf-8')
            frontmatter = parse_yaml_frontmatter(content)

            # Extract skill info
            name = frontmatter.get('name', entry.name)
            description = frontmatter.get('description')

            # Try to extract description from body if not in frontmatter
            if not description:
                description = extract_description_from_body(content)

            # Parse boolean fields properly
            user_invocable_raw = frontmatter.get('user-invocable', True)
            if isinstance(user_invocable_raw, str):
                user_invocable = user_invocable_raw.lower() in ('true', 'yes', '1')
            else:
                user_invocable = bool(user_invocable_raw)

            skill = SkillInfo(
                name=name,
                description=description,
                path=str(skill_md.relative_to(Path('/home/developer'))),
                user_invocable=user_invocable,
                automation=frontmatter.get('automation'),
                allowed_tools=frontmatter.get('allowed-tools'),
                argument_hint=frontmatter.get('argument-hint'),
                has_schedule=False  # TODO: Check if schedule exists for this skill
            )
            skills.append(skill)

        except Exception as e:
            logger.warning(f"Failed to parse skill at {skill_md}: {e}")
            # Still include the skill with minimal info
            skills.append(SkillInfo(
                name=entry.name,
                description=None,
                path=str(skill_md.relative_to(Path('/home/developer'))),
            ))

    return skills


@router.get("/api/skills", response_model=SkillsResponse)
async def list_skills():
    """
    List all available skills (playbooks) from the agent's skills directories.

    Scans:
    - .claude/skills/ (project skills)
    - ~/.claude/skills/ (personal skills)

    Returns skill metadata parsed from SKILL.md YAML frontmatter.
    """
    home_dir = Path('/home/developer')

    # Skills directories to scan
    skill_paths = [
        home_dir / '.claude' / 'skills',
        Path.home() / '.claude' / 'skills'  # Personal skills
    ]

    all_skills: List[SkillInfo] = []
    scanned_paths: List[str] = []

    for skills_dir in skill_paths:
        # Convert to relative path for display
        if skills_dir.is_relative_to(home_dir):
            display_path = str(skills_dir.relative_to(home_dir))
        else:
            display_path = str(skills_dir).replace(str(Path.home()), '~')

        scanned_paths.append(display_path)

        skills = scan_skills_directory(skills_dir)
        all_skills.extend(skills)

    # Remove duplicates (by name), keeping project skills over personal
    seen_names = set()
    unique_skills = []
    for skill in all_skills:
        if skill.name not in seen_names:
            seen_names.add(skill.name)
            unique_skills.append(skill)

    # Sort by name
    unique_skills.sort(key=lambda s: s.name.lower())

    return SkillsResponse(
        skills=unique_skills,
        count=len(unique_skills),
        skill_paths=scanned_paths
    )
