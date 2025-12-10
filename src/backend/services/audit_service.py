"""
Audit logging service for Trinity.
"""
from typing import Dict, Optional
import httpx
from config import AUDIT_URL


async def log_audit_event(
    event_type: str,
    action: str,
    user_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    resource: Optional[str] = None,
    result: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[Dict] = None,
    severity: str = "info"
):
    """
    Log an audit event to the audit service.

    This is fire-and-forget with a 2-second timeout.
    Operations continue if audit logger is unavailable.
    """
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{AUDIT_URL}/api/audit/log",
                json={
                    "event_type": event_type,
                    "user_id": user_id,
                    "agent_name": agent_name,
                    "action": action,
                    "resource": resource,
                    "result": result,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "details": details,
                    "severity": severity
                },
                timeout=2.0
            )
    except Exception as e:
        print(f"Failed to log audit event: {e}")
