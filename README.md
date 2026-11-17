# Ryanair Agent Gatekeeper

**Academic Simulation — MBA Agentic AI Assignment**  
**Student:** Pankaj Kumar Tiwari  
**Registration No.:** PGD202564630  
**Institution:** Shoolini University  
**Target Enterprise:** Ryanair (airline simulation)  
**GitHub Repository:** [pankajk4-ui/Ryanair-Agent-Gatekeeper](https://github.com/pankajk4-ui/Ryanair-Agent-Gatekeeper)

> **DISCLAIMER:** This project is strictly an academic simulation developed for an MBA coursework assignment. It does NOT connect to, interact with, or represent any real Ryanair production system, account, database, payment gateway, or API.

---

## 1. Purpose & Overview

The **Ryanair Agent Gatekeeper** serves as a deterministic security control layer between external customer AI agents (e.g., personal booking bots, travel assistants) and Ryanair's transaction layer. 

The Gatekeeper determines whether incoming agent requests should be:
- **`ALLOW`**: Execute read-only requests or low-risk bookings up to the pre-authorized limit.
- **`ASK CUSTOMER`**: Hold high-value bookings, booking modifications, or refund requests as `PENDING APPROVAL` until explicit customer authorization is received. Nothing is executed automatically.
- **`BLOCK`**: Deny unregistered agents, revoked agents, or structurally invalid requests.

The system enforces agent registration, lifecycle revocation with timestamped non-repudiation proof, human-in-the-loop approvals, and an append-only SQLite audit log.

---

## 2. Agent Identity & Security Model

In this academic simulation:
- **Agent Identity:** Represented as a normalized tuple `(customer_id, agent_name)`. Both strings are trimmed of leading/trailing whitespace, and `agent_name` comparison is strictly case-insensitive (`COLLATE NOCASE`).
- **Agent ID:** Each registered agent is assigned a unique generated identifier (e.g., `AGT-XXXXXXXX`).

> **Production Security Note:** In a real-world enterprise production environment, agent identity would never rely solely on names and identifiers. A production deployment would enforce cryptographic authentication, such as mutual TLS (mTLS), scoped OAuth 2.0 / OpenID Connect bearer tokens, hardware-backed JWTs, or client-signed payload certificates.

---

## 3. The Seven Deterministic Rules

The Gatekeeper applies rules in a strict, deterministic sequence without probabilistic AI models or randomness:

```
[Incoming Request]
        │
        ▼
1. Registered? ──────────── No ─────────────► [R1: BLOCK]
        │ Yes
        ▼
2. Revoked? ─────────────── Yes ────────────► [R2: BLOCK] (Overrides all actions & inputs)
        │ Active
        ▼
3. Valid action & amount? ─ No ─────────────► [R7: BLOCK]
        │ Valid
        ▼
4. Evaluate Action:
   ├─ View Fares ───────────────────────────► [R3: ALLOW]
   ├─ Book Flight (Amount <= EUR 200.00) ───► [R4: ALLOW]
   ├─ Book Flight (Amount > EUR 200.00) ────► [R5: ASK CUSTOMER] (Status: PENDING APPROVAL)
   └─ Change Booking / Request Refund ──────► [R6: ASK CUSTOMER] (Status: PENDING APPROVAL)
        │
        ▼
5. Output Result & Log to Append-Only Audit Trail
```

### Rule Definitions & Explanations

| Rule | Trigger Condition | Decision | Official Gatekeeper Explanation |
|---|---|---|---|
| **R1** | Customer ID or agent identity not registered | **`BLOCK`** | *"The agent has not been authorised by the customer."* |
| **R2** | Agent is registered but in `REVOKED` status | **`BLOCK`** | *"The customer has withdrawn the agent's permission."* (Timestamp stored as proof of when permission ended. Overrides invalid inputs/actions.) |
| **R3** | `View Fares` requested by active agent | **`ALLOW`** | *"Viewing fares is read-only."* (Amount defaults to EUR 0.00) |
| **R4** | `Book Flight` up to and including EUR 200.00 | **`ALLOW`** | *"Registering the agent counts as the customer's authorisation of this limit."* |
| **R5** | `Book Flight` strictly above EUR 200.00 | **`ASK CUSTOMER`** | *"High-value bookings need explicit customer confirmation."* |
| **R6** | `Change Booking` or `Request Refund` | **`ASK CUSTOMER`** | *"These affect existing travel arrangements and financial entitlements."* |
| **R7** | Unsupported action, missing details, or invalid amount | **`BLOCK`** | *"Invalid request: unsupported action, missing details, or invalid amount."* |

### Amount Validation Rules
- Amounts use Python `Decimal` (never binary floats).
- Negative, non-numeric, empty, `NaN`, or infinite values are invalid (`R7`).
- Zero (`0.00`) is invalid only for `Book Flight` (`R7`).
- For `View Fares`, `Change Booking`, and `Request Refund`, the amount defaults to `0.00` if omitted.
- **Boundaries:** Exactly `200.00` = `ALLOW` (`R4`); `200.01` = `ASK CUSTOMER` (`R5`).

### EUR 200 Limit Rationale
<I will fill in after checking Ryanair's average fare>

---

## 4. Database Schema & Architecture

The system uses SQLite with parameterized queries and strict schema constraints:

- **`agents`**: Stores agent identity (`agent_id`, `customer_id`, `customer_name`, `agent_name COLLATE NOCASE`, `description`, `status CHECK IN ('ACTIVE', 'REVOKED')`, `registered_at`, `revoked_at`). Enforces `UNIQUE(customer_id, agent_name COLLATE NOCASE)`.
- **`requests`**: Permanent log of evaluated requests (`request_id`, `agent_id`, `customer_id`, `agent_name`, `action`, `amount`, `decision`, `rule_applied`, `explanation`, `status`, `timestamp`).
- **`approvals`**: Tracks human customer approval decisions (`approval_id`, `request_id`, `customer_id`, `decision CHECK IN ('APPROVED', 'REJECTED')`, `decided_at`, `comments`).
- **`audit_events`**: Append-only audit trail (`event_id`, `timestamp`, `event_type`, `agent_id`, `customer_id`, `request_id`, `details`). Enforced via SQLite triggers `prevent_audit_update` and `prevent_audit_delete` to prohibit updates and deletions.

All timestamps are stored in ISO 8601 format in the **Asia/Kolkata (IST)** timezone.

---

## 5. Streamlit Dashboard Features (Stage 2)

The interactive dashboard is launched via `streamlit run app.py` and provides 6 navigation sections:

1. **📊 Dashboard**:
   - Executive operational telemetry with live metrics (Total Registered Agents, Active Agents, Revoked Agents, Total Requests, Decisions breakdown).
   - Interactive Plotly decision distribution donut chart and requests by action bar chart.
   - Live activity logs (recent requests and append-only audit events).
2. **📝 Register Agent**:
   - Customer and agent registration interface with duplicate active registration prevention and revoked agent re-registration blocking.
   - Comprehensive directory of registered agents.
3. **⚡ Check Agent Request**:
   - Real-time transaction evaluator calling the deterministic `gatekeeper.evaluate_request` engine.
   - Prominent high-contrast decision banners: Green (`ALLOW`), Amber (`ASK CUSTOMER`), Red (`BLOCK`).
   - Detailed request breakdown with rule numbers, explanations, and timestamps.
4. **🚫 Revoke Agent**:
   - Agent permission revocation with mandatory confirmation.
   - Records exact revocation timestamp for non-repudiation proof and updates audit log.
5. **📋 Customer Approvals**:
   - Human-in-the-loop review queue for `PENDING APPROVAL` requests generated by Rules R5 and R6.
   - Single-click Approve / Reject actions with customer notes.
   - Historical decision log.
6. **ℹ️ About Project**:
   - Complete architectural overview, rule table, student information, and production security specifications.

---

## 6. Technology Stack & Pinned Versions

- **Python:** 3.13+
- **Streamlit:** `1.67.0`
- **Plotly:** `7.1.0`
- **Pandas:** `3.0.6`
- **SQLite:** Standard library `sqlite3` (3.45+)

---

## 7. Running the Application & Tests

### Launch the Streamlit Web Application
```bash
streamlit run app.py
```

### Run the Verification Test Suite
```bash
# Run command-line test runner
python test_cases.py

# Run standard library unittest runner
python -m unittest test_cases.py -v
```

All 21 test cases covering boundary amounts (`200`, `200.00`, `200.01`, `0`, `-1`, `"abc"`, `""`, `NaN`), whitespace/case variants, unknown agents, revoked agents, unsupported actions, and append-only database triggers are verified and passing.
