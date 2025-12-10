from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import json
import sqlite3
from pathlib import Path
import os

app = FastAPI(title="Audit Logger Service")

AUDIT_DB_PATH = os.getenv("AUDIT_DB_PATH", "/data/audit.db")

def init_db():
    db_path = Path(AUDIT_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(AUDIT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            user_id TEXT,
            agent_name TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            result TEXT,
            ip_address TEXT,
            user_agent TEXT,
            details TEXT,
            severity TEXT DEFAULT 'info'
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs(timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_event_type ON audit_logs(event_type)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_agent_name ON audit_logs(agent_name)
    """)
    
    conn.commit()
    conn.close()

init_db()

class AuditLogEntry(BaseModel):
    event_type: str
    user_id: Optional[str] = None
    agent_name: Optional[str] = None
    action: str
    resource: Optional[str] = None
    result: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    severity: str = "info"

@app.post("/api/audit/log")
async def create_audit_log(entry: AuditLogEntry):
    conn = sqlite3.connect(AUDIT_DB_PATH)
    cursor = conn.cursor()
    
    details_json = json.dumps(entry.details) if entry.details else None
    
    cursor.execute("""
        INSERT INTO audit_logs 
        (timestamp, event_type, user_id, agent_name, action, resource, result, 
         ip_address, user_agent, details, severity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().isoformat(),
        entry.event_type,
        entry.user_id,
        entry.agent_name,
        entry.action,
        entry.resource,
        entry.result,
        entry.ip_address,
        entry.user_agent,
        details_json,
        entry.severity
    ))
    
    conn.commit()
    conn.close()
    
    return {"status": "logged", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/audit/logs")
async def get_audit_logs(
    event_type: Optional[str] = None,
    agent_name: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    conn = sqlite3.connect(AUDIT_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    
    if agent_name:
        query += " AND agent_name = ?"
        params.append(agent_name)
    
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
    
    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    logs = [dict(row) for row in rows]
    
    conn.close()
    
    return {"logs": logs, "count": len(logs)}

@app.get("/api/audit/stats")
async def get_audit_stats():
    conn = sqlite3.connect(AUDIT_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM audit_logs")
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT event_type, COUNT(*) as count 
        FROM audit_logs 
        GROUP BY event_type
    """)
    by_type = {row[0]: row[1] for row in cursor.fetchall()}
    
    cursor.execute("""
        SELECT severity, COUNT(*) as count 
        FROM audit_logs 
        GROUP BY severity
    """)
    by_severity = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        "total": total,
        "by_type": by_type,
        "by_severity": by_severity
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "audit-logger"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)

