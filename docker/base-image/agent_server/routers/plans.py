"""
Task DAG / Plan endpoints for explicit planning.
"""
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..models import PlanCreateRequest, TaskUpdateRequest
from ..state import agent_state

logger = logging.getLogger(__name__)
router = APIRouter()


def get_plans_dir() -> Path:
    """Get the plans directory path"""
    return Path("/home/developer/plans")


def load_plan(plan_id: str) -> Optional[dict]:
    """Load a plan from file"""
    import yaml

    plans_dir = get_plans_dir()
    plan_file = plans_dir / "active" / f"{plan_id}.yaml"

    if not plan_file.exists():
        # Check archive
        plan_file = plans_dir / "archive" / f"{plan_id}.yaml"

    if not plan_file.exists():
        return None

    try:
        with open(plan_file) as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load plan {plan_id}: {e}")
        return None


def save_plan(plan: dict) -> bool:
    """Save a plan to file"""
    import yaml

    plans_dir = get_plans_dir()
    plan_id = plan.get("id")
    status = plan.get("status", "active")

    # Determine target directory based on status
    if status in ["completed", "failed"]:
        target_dir = plans_dir / "archive"
    else:
        target_dir = plans_dir / "active"

    target_dir.mkdir(parents=True, exist_ok=True)
    plan_file = target_dir / f"{plan_id}.yaml"

    try:
        # Update the updated timestamp
        plan["updated"] = datetime.now().isoformat()

        with open(plan_file, "w") as f:
            yaml.dump(plan, f, default_flow_style=False, sort_keys=False)

        # If moving to archive, remove from active
        if status in ["completed", "failed"]:
            active_file = plans_dir / "active" / f"{plan_id}.yaml"
            if active_file.exists():
                active_file.unlink()

        return True
    except Exception as e:
        logger.error(f"Failed to save plan {plan_id}: {e}")
        return False


def update_blocked_tasks(plan: dict) -> None:
    """Update blocked status based on dependencies"""
    tasks_by_id = {t["id"]: t for t in plan.get("tasks", [])}

    for task in plan.get("tasks", []):
        if task["status"] == "blocked":
            # Check if all dependencies are completed
            deps = task.get("dependencies", [])
            all_deps_complete = all(
                tasks_by_id.get(dep_id, {}).get("status") == "completed"
                for dep_id in deps
            )
            if all_deps_complete:
                task["status"] = "pending"
        elif task["status"] == "pending" and task.get("dependencies"):
            # Check if should be blocked
            deps = task.get("dependencies", [])
            any_dep_incomplete = any(
                tasks_by_id.get(dep_id, {}).get("status") not in ["completed"]
                for dep_id in deps
            )
            if any_dep_incomplete:
                task["status"] = "blocked"


def check_plan_completion(plan: dict) -> None:
    """Check if plan should be marked as completed or failed"""
    tasks = plan.get("tasks", [])
    if not tasks:
        return

    all_completed = all(t["status"] == "completed" for t in tasks)
    any_failed = any(t["status"] == "failed" for t in tasks)

    if all_completed:
        plan["status"] = "completed"
    elif any_failed:
        # Check if failed task blocks remaining tasks
        # For now, don't auto-fail the plan - let agent decide
        pass


@router.get("/api/plans")
async def list_plans(status: Optional[str] = None):
    """
    List all plans for this agent.

    Query params:
    - status: Filter by plan status (active, completed, failed, paused)

    Returns list of plan summaries.
    """
    plans_dir = get_plans_dir()
    plans = []

    # Scan active plans
    active_dir = plans_dir / "active"
    if active_dir.exists():
        for plan_file in active_dir.glob("*.yaml"):
            plan = load_plan(plan_file.stem)
            if plan and (not status or plan.get("status") == status):
                # Return summary only
                tasks = plan.get("tasks", [])
                completed = len([t for t in tasks if t.get("status") == "completed"])
                plans.append({
                    "id": plan.get("id"),
                    "name": plan.get("name"),
                    "status": plan.get("status"),
                    "created": plan.get("created"),
                    "updated": plan.get("updated"),
                    "task_count": len(tasks),
                    "completed_count": completed,
                    "progress_percent": round(completed / len(tasks) * 100) if tasks else 0
                })

    # Scan archived plans if status allows
    if status in [None, "completed", "failed"]:
        archive_dir = plans_dir / "archive"
        if archive_dir.exists():
            for plan_file in archive_dir.glob("*.yaml"):
                plan = load_plan(plan_file.stem)
                if plan and (not status or plan.get("status") == status):
                    tasks = plan.get("tasks", [])
                    completed = len([t for t in tasks if t.get("status") == "completed"])
                    plans.append({
                        "id": plan.get("id"),
                        "name": plan.get("name"),
                        "status": plan.get("status"),
                        "created": plan.get("created"),
                        "updated": plan.get("updated"),
                        "task_count": len(tasks),
                        "completed_count": completed,
                        "progress_percent": round(completed / len(tasks) * 100) if tasks else 0
                    })

    # Sort by updated timestamp (newest first)
    plans.sort(key=lambda p: p.get("updated") or p.get("created") or "", reverse=True)

    return {
        "agent_name": agent_state.agent_name,
        "plans": plans,
        "count": len(plans)
    }


@router.post("/api/plans")
async def create_plan(request: PlanCreateRequest):
    """
    Create a new plan.

    Body:
    - name: Plan name
    - description: Optional description
    - tasks: List of task definitions

    Returns the created plan.
    """
    # Generate plan ID
    plan_id = f"plan-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:6]}"

    # Build tasks
    tasks = []
    for i, task_def in enumerate(request.tasks):
        task_id = task_def.get("id", f"task-{i+1}")
        deps = task_def.get("dependencies", [])

        # If has dependencies, start as blocked
        initial_status = "blocked" if deps else "pending"

        tasks.append({
            "id": task_id,
            "name": task_def.get("name", f"Task {i+1}"),
            "description": task_def.get("description"),
            "status": initial_status,
            "dependencies": deps,
            "started_at": None,
            "completed_at": None,
            "result": None
        })

    plan = {
        "id": plan_id,
        "name": request.name,
        "description": request.description,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "status": "active",
        "tasks": tasks
    }

    if save_plan(plan):
        logger.info(f"Created plan: {plan_id} ({request.name})")
        return plan
    else:
        raise HTTPException(status_code=500, detail="Failed to save plan")


# NOTE: /api/plans/summary must be defined BEFORE /api/plans/{plan_id}
# to avoid FastAPI matching "summary" as a plan_id
@router.get("/api/plans/summary")
async def get_plans_summary():
    """
    Get a summary of all plans for dashboard display.

    Returns aggregate statistics and active task info.
    """
    plans_dir = get_plans_dir()

    summary = {
        "agent_name": agent_state.agent_name,
        "total_plans": 0,
        "active_plans": 0,
        "completed_plans": 0,
        "failed_plans": 0,
        "total_tasks": 0,
        "completed_tasks": 0,
        "active_tasks": 0,
        "current_task": None,  # Currently active task
        "recent_plans": []  # Most recent 5 plans
    }

    all_plans = []

    # Scan all plans
    for subdir in ["active", "archive"]:
        dir_path = plans_dir / subdir
        if dir_path.exists():
            for plan_file in dir_path.glob("*.yaml"):
                plan = load_plan(plan_file.stem)
                if plan:
                    all_plans.append(plan)
                    summary["total_plans"] += 1

                    plan_status = plan.get("status")
                    if plan_status == "active":
                        summary["active_plans"] += 1
                    elif plan_status == "completed":
                        summary["completed_plans"] += 1
                    elif plan_status == "failed":
                        summary["failed_plans"] += 1

                    for task in plan.get("tasks", []):
                        summary["total_tasks"] += 1
                        task_status = task.get("status")
                        if task_status == "completed":
                            summary["completed_tasks"] += 1
                        elif task_status == "active":
                            summary["active_tasks"] += 1
                            # Track current active task
                            if summary["current_task"] is None:
                                summary["current_task"] = {
                                    "plan_id": plan.get("id"),
                                    "plan_name": plan.get("name"),
                                    "task_id": task.get("id"),
                                    "task_name": task.get("name"),
                                    "started_at": task.get("started_at")
                                }

    # Sort by updated time and get recent 5
    all_plans.sort(key=lambda p: p.get("updated") or p.get("created") or "", reverse=True)
    for plan in all_plans[:5]:
        tasks = plan.get("tasks", [])
        completed = len([t for t in tasks if t.get("status") == "completed"])
        summary["recent_plans"].append({
            "id": plan.get("id"),
            "name": plan.get("name"),
            "status": plan.get("status"),
            "progress_percent": round(completed / len(tasks) * 100) if tasks else 0
        })

    return summary


@router.get("/api/plans/{plan_id}")
async def get_plan(plan_id: str):
    """
    Get a specific plan by ID.

    Returns the full plan with all tasks.
    """
    plan = load_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    return plan


@router.put("/api/plans/{plan_id}")
async def update_plan(plan_id: str, updates: dict):
    """
    Update plan metadata (name, description, status).

    Body can contain:
    - name: New plan name
    - description: New description
    - status: New status (active, paused, completed, failed)
    """
    plan = load_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    # Update allowed fields
    if "name" in updates:
        plan["name"] = updates["name"]
    if "description" in updates:
        plan["description"] = updates["description"]
    if "status" in updates:
        if updates["status"] not in ["active", "paused", "completed", "failed"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        plan["status"] = updates["status"]

    if save_plan(plan):
        return plan
    else:
        raise HTTPException(status_code=500, detail="Failed to save plan")


@router.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: str):
    """
    Delete a plan.
    """
    plans_dir = get_plans_dir()

    # Try to find and delete the plan file
    for subdir in ["active", "archive"]:
        plan_file = plans_dir / subdir / f"{plan_id}.yaml"
        if plan_file.exists():
            plan_file.unlink()
            logger.info(f"Deleted plan: {plan_id}")
            return {"status": "deleted", "plan_id": plan_id}

    raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")


@router.put("/api/plans/{plan_id}/tasks/{task_id}")
async def update_task(plan_id: str, task_id: str, request: TaskUpdateRequest):
    """
    Update a task's status within a plan.

    Body:
    - status: New status (pending, active, completed, failed)
    - result: Optional result/output from task

    Side effects:
    - Updates dependent task statuses
    - May update overall plan status
    """
    plan = load_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    # Find the task
    task = None
    for t in plan.get("tasks", []):
        if t["id"] == task_id:
            task = t
            break

    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    # Validate status transition
    valid_statuses = ["pending", "active", "completed", "failed", "blocked"]
    if request.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")

    # Update task
    old_status = task["status"]
    task["status"] = request.status

    if request.status == "active" and old_status != "active":
        task["started_at"] = datetime.now().isoformat()

    if request.status in ["completed", "failed"]:
        task["completed_at"] = datetime.now().isoformat()

    if request.result is not None:
        task["result"] = request.result

    # Update dependent tasks
    update_blocked_tasks(plan)

    # Check if plan is complete
    check_plan_completion(plan)

    if save_plan(plan):
        logger.info(f"Updated task {task_id} in plan {plan_id}: {old_status} -> {request.status}")
        return plan
    else:
        raise HTTPException(status_code=500, detail="Failed to save plan")
