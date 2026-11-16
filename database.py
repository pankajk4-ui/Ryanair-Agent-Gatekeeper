"""
Ryanair Agent Gatekeeper - Database Module
Academic simulation for MBA Agentic AI assignment.
Student: Pankaj Kumar Tiwari | Reg No: PGD202564630 | Shoolini University

Provides SQLite schema initialization, agent registration, revocation,
request logging, and append-only audit trail.
"""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import zoneinfo

# Standard IST timezone for all timestamps
IST = zoneinfo.ZoneInfo("Asia/Kolkata")

DEFAULT_DB_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "gatekeeper.db"


def get_ist_now_iso() -> str:
    """Return the current timestamp in ISO 8601 format in Asia/Kolkata timezone."""
    return datetime.now(IST).isoformat()


def get_default_db_path() -> Path:
    """Ensure data directory exists and return default DB path."""
    DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_PATH


def init_db(conn: sqlite3.Connection) -> None:
    """
    Initialize SQLite database tables, constraints, and append-only audit triggers.
    Safe to run repeatedly (CREATE TABLE IF NOT EXISTS).
    """
    conn.execute("PRAGMA foreign_keys = ON;")

    # 1. agents table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        agent_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        agent_name TEXT NOT NULL COLLATE NOCASE,
        description TEXT,
        status TEXT NOT NULL CHECK(status IN ('ACTIVE', 'REVOKED')),
        registered_at TEXT NOT NULL,
        revoked_at TEXT,
        UNIQUE (customer_id, agent_name COLLATE NOCASE)
    );
    """)

    # 2. requests table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        request_id TEXT PRIMARY KEY,
        agent_id TEXT,
        customer_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        action TEXT NOT NULL,
        amount TEXT,
        decision TEXT NOT NULL CHECK(decision IN ('ALLOW', 'ASK CUSTOMER', 'BLOCK')),
        rule_applied TEXT NOT NULL,
        explanation TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('ALLOWED', 'BLOCKED', 'PENDING APPROVAL', 'APPROVED', 'REJECTED')),
        timestamp TEXT NOT NULL,
        FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
    );
    """)

    # 3. approvals table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS approvals (
        approval_id TEXT PRIMARY KEY,
        request_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        decision TEXT NOT NULL CHECK(decision IN ('APPROVED', 'REJECTED')),
        decided_at TEXT NOT NULL,
        comments TEXT,
        FOREIGN KEY (request_id) REFERENCES requests(request_id)
    );
    """)

    # 4. audit_events table (append-only)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS audit_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        agent_id TEXT,
        customer_id TEXT,
        request_id TEXT,
        details TEXT NOT NULL
    );
    """)

    # Append-only enforcement triggers for audit_events
    conn.execute("""
    CREATE TRIGGER IF NOT EXISTS prevent_audit_update
    BEFORE UPDATE ON audit_events
    BEGIN
        SELECT RAISE(ABORT, 'audit_events is append-only: updates are prohibited');
    END;
    """)

    conn.execute("""
    CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
    BEFORE DELETE ON audit_events
    BEGIN
        SELECT RAISE(ABORT, 'audit_events is append-only: deletions are prohibited');
    END;
    """)


@contextmanager
def get_db_connection(db: Any = None):
    """
    Context manager yielding a SQLite connection.
    Accepts:
      - None: connects to default data/gatekeeper.db
      - str / Path: connects to the specified database file or ':memory:'
      - sqlite3.Connection: uses the existing open connection without closing it
    """
    if isinstance(db, sqlite3.Connection):
        init_db(db)
        yield db
        db.commit()
    else:
        db_path = str(db) if db is not None else str(get_default_db_path())
        if db_path != ":memory:":
            Path(db_path).resolve().parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        init_db(conn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def normalize_identity(customer_id: str, agent_name: str) -> tuple[str, str]:
    """
    Normalise agent identity: trim whitespace for both, agent_name is case-insensitive.
    """
    if customer_id is None or agent_name is None:
        raise ValueError("customer_id and agent_name cannot be None.")
    c_id = str(customer_id).strip()
    a_name = str(agent_name).strip()
    if not c_id:
        raise ValueError("customer_id cannot be empty.")
    if not a_name:
        raise ValueError("agent_name cannot be empty.")
    return c_id, a_name


def register_agent(
    customer_id: str,
    customer_name: str,
    agent_name: str,
    description: str = "",
    db: Any = None
) -> Dict[str, Any]:
    """
    Register a new customer agent.
    Rejects duplicate active registrations.
    Rejects re-registering a revoked agent name for the same customer (no silent reactivation).
    Generates unique Agent ID and writes an audit event.
    """
    norm_customer_id, norm_agent_name = normalize_identity(customer_id, agent_name)
    norm_customer_name = str(customer_name).strip() if customer_name else norm_customer_id

    with get_db_connection(db) as conn:
        conn.row_factory = sqlite3.Row
        # Check if an agent already exists for this (customer_id, agent_name COLLATE NOCASE)
        cursor = conn.execute(
            """
            SELECT * FROM agents
            WHERE customer_id = ? AND agent_name = ? COLLATE NOCASE
            """,
            (norm_customer_id, norm_agent_name)
        )
        existing = cursor.fetchone()

        if existing:
            if existing["status"] == "ACTIVE":
                raise ValueError(
                    f"Agent '{norm_agent_name}' is already actively registered for customer '{norm_customer_id}' "
                    f"(Agent ID: {existing['agent_id']}). Duplicate active registration rejected."
                )
            elif existing["status"] == "REVOKED":
                raise ValueError(
                    f"Agent '{norm_agent_name}' was previously revoked for customer '{norm_customer_id}' "
                    f"(Agent ID: {existing['agent_id']}). Re-registering a revoked agent name is rejected "
                    f"(no silent reactivation allowed)."
                )

        agent_id = f"AGT-{uuid.uuid4().hex[:8].upper()}"
        now_ts = get_ist_now_iso()

        conn.execute(
            """
            INSERT INTO agents (
                agent_id, customer_id, customer_name, agent_name,
                description, status, registered_at, revoked_at
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, NULL)
            """,
            (agent_id, norm_customer_id, norm_customer_name, norm_agent_name, description.strip(), now_ts)
        )

        # Audit event for registration
        audit_details = (
            f"Agent '{norm_agent_name}' ({agent_id}) registered with ACTIVE status "
            f"for customer '{norm_customer_id}' ({norm_customer_name})."
        )
        conn.execute(
            """
            INSERT INTO audit_events (timestamp, event_type, agent_id, customer_id, request_id, details)
            VALUES (?, 'AGENT_REGISTERED', ?, ?, NULL, ?)
            """,
            (now_ts, agent_id, norm_customer_id, audit_details)
        )

        return {
            "agent_id": agent_id,
            "customer_id": norm_customer_id,
            "customer_name": norm_customer_name,
            "agent_name": norm_agent_name,
            "description": description.strip(),
            "status": "ACTIVE",
            "registered_at": now_ts,
            "revoked_at": None,
        }


def revoke_agent(
    customer_id: str,
    agent_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    db: Any = None
) -> Dict[str, Any]:
    """
    Revoke an agent's permissions. Sets status to REVOKED and records revoked_at timestamp.
    Logs the revocation event in audit_events.
    """
    with get_db_connection(db) as conn:
        conn.row_factory = sqlite3.Row
        agent = None

        if agent_id:
            cursor = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id.strip(),))
            agent = cursor.fetchone()
        elif customer_id and agent_name:
            norm_c_id, norm_a_name = normalize_identity(customer_id, agent_name)
            cursor = conn.execute(
                "SELECT * FROM agents WHERE customer_id = ? AND agent_name = ? COLLATE NOCASE",
                (norm_c_id, norm_a_name)
            )
            agent = cursor.fetchone()
        else:
            raise ValueError("Must provide either agent_id or both customer_id and agent_name.")

        if not agent:
            target = agent_id if agent_id else f"{customer_id}:{agent_name}"
            raise ValueError(f"Agent '{target}' not found.")

        if agent["status"] == "REVOKED":
            raise ValueError(
                f"Agent '{agent['agent_name']}' ({agent['agent_id']}) is already revoked "
                f"at {agent['revoked_at']}."
            )

        now_ts = get_ist_now_iso()
        conn.execute(
            "UPDATE agents SET status = 'REVOKED', revoked_at = ? WHERE agent_id = ?",
            (now_ts, agent["agent_id"])
        )

        audit_details = (
            f"Agent '{agent['agent_name']}' ({agent['agent_id']}) revoked by customer "
            f"'{agent['customer_id']}'. Permission terminated at {now_ts}."
        )
        conn.execute(
            """
            INSERT INTO audit_events (timestamp, event_type, agent_id, customer_id, request_id, details)
            VALUES (?, 'AGENT_REVOKED', ?, ?, NULL, ?)
            """,
            (now_ts, agent["agent_id"], agent["customer_id"], audit_details)
        )

        return {
            "agent_id": agent["agent_id"],
            "customer_id": agent["customer_id"],
            "customer_name": agent["customer_name"],
            "agent_name": agent["agent_name"],
            "description": agent["description"],
            "status": "REVOKED",
            "registered_at": agent["registered_at"],
            "revoked_at": now_ts,
        }


def get_agent(
    customer_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_id: Optional[str] = None,
    db: Any = None
) -> Optional[Dict[str, Any]]:
    """
    Retrieve an agent by agent_id or by (customer_id, agent_name) with case-insensitive agent_name.
    """
    with get_db_connection(db) as conn:
        conn.row_factory = sqlite3.Row
        if agent_id:
            cursor = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None
        elif customer_id and agent_name:
            norm_c_id = str(customer_id).strip()
            norm_a_name = str(agent_name).strip()
            cursor = conn.execute(
                "SELECT * FROM agents WHERE customer_id = ? AND agent_name = ? COLLATE NOCASE",
                (norm_c_id, norm_a_name)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        return None


def list_agents(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Any = None
) -> List[Dict[str, Any]]:
    """
    List all agents, optionally filtered by customer_id or status.
    """
    with get_db_connection(db) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM agents WHERE 1=1"
        params: List[Any] = []

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id.strip())
        if status:
            query += " AND status = ?"
            params.append(status.strip().upper())

        query += " ORDER BY registered_at DESC"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def log_request(request_data: Dict[str, Any], db: Any = None) -> str:
    """
    Insert a request record into the requests table and append a record to audit_events.
    """
    req_id = request_data.get("request_id") or f"REQ-{uuid.uuid4().hex[:8].upper()}"
    timestamp = request_data.get("timestamp") or get_ist_now_iso()

    with get_db_connection(db) as conn:
        conn.execute(
            """
            INSERT INTO requests (
                request_id, agent_id, customer_id, agent_name, action,
                amount, decision, rule_applied, explanation, status, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req_id,
                request_data.get("agent_id"),
                request_data.get("customer_id"),
                request_data.get("agent_name"),
                request_data.get("action"),
                str(request_data.get("amount")) if request_data.get("amount") is not None else None,
                request_data.get("decision"),
                request_data.get("rule_applied"),
                request_data.get("explanation"),
                request_data.get("status"),
                timestamp,
            )
        )

        audit_details = (
            f"Request {req_id} evaluated: action='{request_data.get('action')}', "
            f"amount='{request_data.get('amount')}', decision='{request_data.get('decision')}', "
            f"rule='{request_data.get('rule_applied')}', status='{request_data.get('status')}'."
        )
        conn.execute(
            """
            INSERT INTO audit_events (timestamp, event_type, agent_id, customer_id, request_id, details)
            VALUES (?, 'REQUEST_EVALUATED', ?, ?, ?, ?)
            """,
            (
                timestamp,
                request_data.get("agent_id"),
                request_data.get("customer_id"),
                req_id,
                audit_details,
            )
        )

    return req_id


def get_request(request_id: str, db: Any = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single request by request_id."""
    with get_db_connection(db) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM requests WHERE request_id = ?", (request_id.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_requests(
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Any = None
) -> List[Dict[str, Any]]:
    """List all evaluated requests, optionally filtered."""
    with get_db_connection(db) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM requests WHERE 1=1"
        params: List[Any] = []

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id.strip())
        if status:
            query += " AND status = ?"
            params.append(status.strip())

        query += " ORDER BY timestamp DESC"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def update_request_approval(
    request_id: str,
    customer_id: str,
    decision: str,
    comments: str = "",
    db: Any = None
) -> Dict[str, Any]:
    """
    Update a PENDING APPROVAL request to APPROVED or REJECTED.
    Inserts a record into the approvals table and logs to audit_events.
    """
    decision_clean = decision.strip().upper()
    if decision_clean not in ("APPROVED", "REJECTED"):
        raise ValueError("Decision must be either 'APPROVED' or 'REJECTED'.")

    with get_db_connection(db) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM requests WHERE request_id = ?", (request_id.strip(),))
        req = cursor.fetchone()
        if not req:
            raise ValueError(f"Request '{request_id}' not found.")
        if req["status"] != "PENDING APPROVAL":
            raise ValueError(f"Request '{request_id}' is in status '{req['status']}', not 'PENDING APPROVAL'.")

        now_ts = get_ist_now_iso()
        approval_id = f"APP-{uuid.uuid4().hex[:8].upper()}"

        conn.execute(
            "UPDATE requests SET status = ? WHERE request_id = ?",
            (decision_clean, request_id.strip())
        )

        conn.execute(
            """
            INSERT INTO approvals (approval_id, request_id, customer_id, decision, decided_at, comments)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (approval_id, request_id.strip(), customer_id.strip(), decision_clean, now_ts, comments.strip())
        )

        event_type = "REQUEST_APPROVED" if decision_clean == "APPROVED" else "REQUEST_REJECTED"
        audit_details = (
            f"Request {request_id} ({req['action']}, amount={req['amount']}) was {decision_clean} "
            f"by customer '{customer_id}'. Comments: '{comments.strip()}'."
        )
        conn.execute(
            """
            INSERT INTO audit_events (timestamp, event_type, agent_id, customer_id, request_id, details)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (now_ts, event_type, req["agent_id"], customer_id.strip(), request_id.strip(), audit_details)
        )

        return {
            "approval_id": approval_id,
            "request_id": request_id.strip(),
            "customer_id": customer_id.strip(),
            "decision": decision_clean,
            "decided_at": now_ts,
            "comments": comments.strip(),
        }


def get_audit_events(
    agent_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    request_id: Optional[str] = None,
    db: Any = None
) -> List[Dict[str, Any]]:
    """
    Retrieve permanent audit log events in chronological order.
    """
    with get_db_connection(db) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM audit_events WHERE 1=1"
        params: List[Any] = []

        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id.strip())
        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id.strip())
        if request_id:
            query += " AND request_id = ?"
            params.append(request_id.strip())

        query += " ORDER BY event_id ASC"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
