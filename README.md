# Ryanair Agent Gatekeeper

**Academic Simulation — MBA Agentic AI Coursework Assignment**  
**Student:** Pankaj Kumar Tiwari  
**Registration Number:** PGD202564630  
**Institution:** Shoolini University  
**Target Enterprise:** Ryanair (Airline Simulation)  
**GitHub Repository:** [pankajk4-ui/Ryanair-Agent-Gatekeeper](https://github.com/pankajk4-ui/Ryanair-Agent-Gatekeeper)  

> **ACADEMIC DISCLAIMER:** This project is strictly an academic simulation developed for an MBA Agentic AI coursework assignment. It does **NOT** connect to, interact with, or represent any real Ryanair production system, passenger account, internal database, payment gateway, or commercial API. No financial transactions, flight bookings, booking modifications, or refunds are executed.

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Project Objectives](#3-project-objectives)
4. [Key Features](#4-key-features)
5. [The Seven Gatekeeper Rules & Evaluation Hierarchy](#5-the-seven-gatekeeper-rules--evaluation-hierarchy)
6. [Agent Identity & Security Model](#6-agent-identity--security-model)
7. [Audit Log & Non-Repudiation Architecture](#7-audit-log--non-repudiation-architecture)
8. [Database Schema & Data Integrity](#8-database-schema--data-integrity)
9. [Technology Stack](#9-technology-stack)
10. [Local Installation & Setup](#10-local-installation--setup)
11. [Running the Application](#11-running-the-application)
12. [Testing & Verification Suite](#12-testing--verification-suite)
13. [Enterprise Production Security Considerations](#13-enterprise-production-security-considerations)

---

## 1. Project Overview

The **Ryanair Agent Gatekeeper** is a deterministic policy enforcement and security control gateway designed to mediate interactions between external, customer-owned autonomous AI agents (e.g., personal digital assistants, flight scanners, autonomous booking agents) and Ryanair's transactional layer.

As consumers increasingly deploy agentic AI assistants to automate commercial travel arrangements, airlines require an enterprise gatekeeper that inspects, validates, and authorizes every incoming agent payload before it reaches downstream flight reservation services.

The Gatekeeper enforces a **tri-state decision paradigm**:
- **`ALLOW`**: Automatically approve and process read-only queries (e.g., viewing fares) or low-risk bookings up to a pre-authorized financial ceiling (EUR 200.00).
- **`ASK CUSTOMER`**: Quarantine high-value bookings (> EUR 200.00), itinerary modifications, or refund requests into an explicit **Human-in-the-Loop (HITL)** queue (`PENDING APPROVAL`). Nothing is executed without human customer authorization.
- **`BLOCK`**: Instantly reject unregistered agents, revoked agents, unsupported operations, or structurally invalid request payloads.

The platform provides complete lifecycle management (registration, monitoring, revocation), an immutable append-only SQLite audit log, and an executive Streamlit telemetry dashboard.

---

## 2. Problem Statement

The rapid rise of autonomous client-side AI agents introduces fundamental governance, financial, and operational challenges for commercial airlines:

1. **Unconstrained Autonomous Spending:** Autonomous agents given open payment access risk committing customers to unintended, duplicate, or high-value bookings due to goal-misalignment, prompt ambiguity, or model hallucination.
2. **High-Impact State Alterations:** Operations such as flight rescheduling (`Change Booking`) or cancellations/refunds (`Request Refund`) directly alter passenger travel itineraries and trigger fee policies. Permitting bots to trigger these autonomously without confirmation exposes customers and airlines to dispute liabilities.
3. **Authorization Drift & Revocation Latency:** Customers must retain absolute sovereignty over their delegated agents. When a customer revokes an agent, permission must terminate instantaneously across all transactions with legally defensible proof of revocation.
4. **Stochastic Vulnerabilities of LLM Evaluators:** Using Large Language Models (LLMs) to make authorization and security decisions introduces latency, non-deterministic outputs, prompt injection vectors, and floating-point rounding errors. Security gatekeepers must be 100% deterministic.
5. **Auditability and Dispute Resolution:** Traditional transactional logs rarely distinguish whether an API call originated from a verified human or an external AI bot. Airlines require an immutable, tamper-proof audit trail documenting the exact rule, timestamp, and authorization status for every agent interaction.

---

## 3. Project Objectives

- **Deterministic Rule Enforcement:** Implement a zero-randomness, rule-based decision engine (`gatekeeper.py`) executing seven unambiguous business rules in a strict, deterministic sequence.
- **Financial Risk Mitigation:** Enforce a pre-authorized limit of **EUR 200.00** for automated flight bookings, quarantine bookings exceeding EUR 200.00, and enforce exact `Decimal` arithmetic to eliminate binary float precision errors.
- **Human-in-the-Loop (HITL) Governance:** Intercept sensitive, high-value, and entitlement-altering actions into a `PENDING APPROVAL` state where customers can explicitly approve or reject requests with audit comments.
- **Robust Agent Lifecycle Management:** Provide identity pairing `(customer_id, agent_name)`, unique Agent ID generation (`AGT-XXXXXXXX`), case-insensitive identity normalization, duplicate registration prevention, and permanent revocation (preventing silent reactivation).
- **Non-Repudiation & Tamper-Proof Audit Logging:** Enforce an append-only audit trail in SQLite (`audit_events`) using database-level triggers that actively reject `UPDATE` and `DELETE` operations.
- **Enterprise-Grade Observability:** Deliver a responsive, airline-themed Streamlit dashboard (`app.py`) featuring live operational metrics, interactive Plotly visualizations, agent management forms, and approval queues.

---

## 4. Key Features

- **Tri-State Decision Engine:** Immediate classification into `ALLOW`, `ASK CUSTOMER`, or `BLOCK` with explicit rule citations (`R1` through `R7`) and standardized explanations.
- **Strict Deterministic Precedence:** Unregistered agents are blocked by Rule R1 before action validation; revoked agents are blocked by Rule R2 regardless of payload validity; invalid amounts or actions are blocked by Rule R7 before threshold checks.
- **Exact Decimal Arithmetic:** All transaction values are processed via Python's `decimal.Decimal`. String parsing, negative amounts, empty values, non-numeric strings, `NaN`, and `Infinity` are strictly rejected.
- **Single-Identity Agent Registration:** Agents are registered under `(customer_id, agent_name)`. The system blocks duplicate active registrations and permanently blocks re-registering a revoked agent name for the same customer.
- **Non-Repudiation Revocation:** Revoking an agent transitions its status to `REVOKED` and records an immutable ISO 8601 IST timestamp (`revoked_at`) documenting the exact moment authority was withdrawn.
- **Interactive Human-in-the-Loop Review Queue:** Dedicated approval interface allowing customers to inspect pending requests, enter review notes, and approve or reject transactions.
- **Database-Enforced Append-Only Audit Trail:** SQLite database triggers (`prevent_audit_update`, `prevent_audit_delete`) guarantee that audit records cannot be altered or purged even by administrative operations.
- **Ryanair-Themed Streamlit UI:** Multi-page dashboard styled with Ryanair Navy Blue (`#00205B`), Sunburst Yellow (`#F4C300`), real-time metric cards, interactive Plotly charts, and responsive tabular views.
- **100% Automated Test Coverage:** Comprehensive test suite (`test_cases.py`) verifying all boundary conditions, invalid inputs, whitespace/case variations, and trigger integrity across 21 test cases.

---

## 5. The Seven Gatekeeper Rules & Evaluation Hierarchy

### Evaluation Order (Deterministic Precedence)
Every incoming request is evaluated through an immutable six-step sequence:
1. **Registered?** $\rightarrow$ If not registered, return **`BLOCK (R1)`**.
2. **Revoked?** $\rightarrow$ If status is `REVOKED`, return **`BLOCK (R2)`** (overrides all actions and inputs).
3. **Valid Action & Amount?** $\rightarrow$ If action unsupported or amount invalid, return **`BLOCK (R7)`**.
4. **Apply Action-Specific Rules (`R3`–`R6`)**:
   - `View Fares` $\rightarrow$ **`ALLOW (R3)`**
   - `Book Flight` $\le$ EUR 200.00 $\rightarrow$ **`ALLOW (R4)`**
   - `Book Flight` $>$ EUR 200.00 $\rightarrow$ **`ASK CUSTOMER (R5)`**
   - `Change Booking` or `Request Refund` $\rightarrow$ **`ASK CUSTOMER (R6)`**
5. **Return Result Object:** Output structured `GatekeeperResult` (Decision, Rule, Explanation, Timestamp, Request ID, Status).
6. **Write to Audit Log:** Atomically persist request record and append-only audit event.

```
                              [Incoming Agent Request]
                                         │
                                         ▼
                            ┌─────────────────────────┐
                            │ Step 1: Registered?     │──── No ─────► [R1: BLOCK]
                            └─────────────────────────┘
                                         │ Yes
                                         ▼
                            ┌─────────────────────────┐
                            │ Step 2: Revoked?        │──── Yes ────► [R2: BLOCK] (Overrides all inputs)
                            └─────────────────────────┘
                                         │ Active
                                         ▼
                            ┌─────────────────────────┐
                            │ Step 3: Valid Input?    │──── No ─────► [R7: BLOCK]
                            │ (Action & Amount)       │
                            └─────────────────────────┘
                                         │ Valid
                                         ▼
                            ┌─────────────────────────┐
                            │ Step 4: Evaluate Action │
                            └─────────────────────────┘
                                         │
         ┌───────────────────┬───────────┴───────────┬───────────────────┐
         ▼                   ▼                       ▼                   ▼
    View Fares          Book Flight             Book Flight       Change Booking /
         │            (<= EUR 200.00)         (> EUR 200.00)       Request Refund
         ▼                   ▼                       ▼                   ▼
    [R3: ALLOW]         [R4: ALLOW]          [R5: ASK CUSTOMER]  [R6: ASK CUSTOMER]
                                              (PENDING APPROVAL)  (PENDING APPROVAL)
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │ Step 5: Generate Result Object  │
                        └─────────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │ Step 6: Append to Audit Trail   │
                        └─────────────────────────────────┘
```

### Comprehensive Rule Reference Table

| Rule | Trigger Condition | Decision | Request Status | Official Gatekeeper Explanation |
|:---:|---|:---:|:---:|---|
| **R1** | Customer ID or agent identity not registered | **`BLOCK`** | `BLOCKED` | *"The agent has not been authorised by the customer."* |
| **R2** | Agent is registered but in `REVOKED` status | **`BLOCK`** | `BLOCKED` | *"The customer has withdrawn the agent's permission."* (Revocation timestamp stored as proof of when permission ended. Overrides invalid inputs/actions.) |
| **R3** | `View Fares` requested by active agent | **`ALLOW`** | `ALLOWED` | *"Viewing fares is read-only."* (Amount defaults to EUR 0.00) |
| **R4** | `Book Flight` up to and including EUR 200.00 | **`ALLOW`** | `ALLOWED` | *"Registering the agent counts as the customer's authorisation of this limit."* |
| **R5** | `Book Flight` strictly above EUR 200.00 | **`ASK CUSTOMER`** | `PENDING APPROVAL` | *"High-value bookings need explicit customer confirmation."* |
| **R6** | `Change Booking` or `Request Refund` | **`ASK CUSTOMER`** | `PENDING APPROVAL` | *"These affect existing travel arrangements and financial entitlements."* |
| **R7** | Unsupported action, missing details, or invalid amount | **`BLOCK`** | `BLOCKED` | *"Invalid request: unsupported action, missing details, or invalid amount."* |

### Amount Validation Specifications
- **Data Type:** Evaluated strictly using Python `Decimal` (never binary `float`).
- **Invalid Formats:** Empty strings (`""`), whitespace, non-numeric text (`"abc"`), `NaN` (both `float('nan')` and `"NaN"`), and `Infinity` (both `float('inf')` and `"inf"`) trigger **`R7 (BLOCK)`**.
- **Negative Values:** Any negative amount (e.g., `-1`, `-5.00`) triggers **`R7 (BLOCK)`**.
- **Zero Value Policy:** `0.00` is invalid **only** for `Book Flight` (`R7`). For `View Fares`, `Change Booking`, and `Request Refund`, the amount defaults to `0.00` if omitted (`None`).
- **Strict Boundary Behavior:**
  - Exactly `EUR 200.00` $\rightarrow$ **`ALLOW (Rule R4)`**
  - Exactly `EUR 200.01` $\rightarrow$ **`ASK CUSTOMER (Rule R5)`**

### EUR 200 Limit Rationale
<I will fill in after checking Ryanair's average fare>

---

## 6. Agent Identity & Security Model

In this academic simulation:
- **Agent Identity Tuple:** Represented by the composite key `(customer_id, agent_name)`.
- **Identity Normalization:**
  - Leading and trailing whitespace is stripped from both fields: `customer_id.strip()`, `agent_name.strip()`.
  - Agent name matching is strictly case-insensitive using SQLite's `COLLATE NOCASE` and Python normalization.
  - Examples: `"TravelScout"`, `"travelscout"`, and `"  TRAVELSCOUT  "` map to the same agent identity.
- **Generated Agent ID:** Each registered agent receives a permanent, system-generated identifier (`AGT-XXXXXXXX`).
- **Lifecycle Guarantees:**
  - **Duplicate Prevention:** A customer cannot register two active agents with the same name.
  - **No Silent Reactivation:** Once an agent is revoked, re-registering an agent with the same name under that customer is rejected by backend business logic.

---

## 7. Audit Log & Non-Repudiation Architecture

The Gatekeeper enforces permanent, verifiable auditability to protect both customer rights and airline regulatory compliance.

### Immutable SQLite Triggers
The `audit_events` table is **append-only**. Even with direct SQL access, records cannot be modified or deleted. Two SQLite database triggers actively intercept and abort tampering attempts:

```sql
CREATE TRIGGER IF NOT EXISTS prevent_audit_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only: updates are prohibited');
END;

CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit_events is append-only: deletions are prohibited');
END;
```

### Event Lifecycle Logging
Audit events are recorded independently of whether a transaction was approved:
- `AGENT_REGISTERED`: Triggered upon successful agent registration (capturing `agent_id`, `customer_id`, timestamp).
- `AGENT_REVOKED`: Triggered when an agent is revoked, permanently logging the `revoked_at` timestamp.
- `REQUEST_EVALUATED`: Triggered on every gatekeeper evaluation (capturing request details, rule applied, decision, and status).
- `REQUEST_APPROVED`: Triggered when a human customer authorizes a `PENDING APPROVAL` request.
- `REQUEST_REJECTED`: Triggered when a human customer denies a `PENDING APPROVAL` request.

### Standardized Timezone
All timestamps across the application, database records, and audit events are generated in **ISO 8601 format in the Asia/Kolkata (IST, UTC+05:30) timezone** (`YYYY-MM-DDTHH:MM:SS.mmmmmm+05:30`) via Python standard library `zoneinfo.ZoneInfo("Asia/Kolkata")`.

### Non-Repudiation Defense
When an agent is revoked, Rule R2 stores and outputs the revocation timestamp. If a compromised or rogue agent attempts transactions after revocation, the Gatekeeper blocks the request under Rule R2 and provides the exact timestamp proving customer authorization had already ended.

---

## 8. Database Schema & Data Integrity

The SQLite database (`data/gatekeeper.db`) is automatically initialized with strict foreign keys (`PRAGMA foreign_keys = ON;`) and check constraints:

```
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│             agents              │           │            requests             │
├─────────────────────────────────┤           ├─────────────────────────────────┤
│ agent_id (PK, TEXT)             │◄───┐      │ request_id (PK, TEXT)           │◄───┐
│ customer_id (TEXT)              │    │      │ agent_id (FK, TEXT, NULLABLE)   │────┘
│ customer_name (TEXT)            │    └──────│ customer_id (TEXT)              │
│ agent_name (TEXT COLLATE NOCASE)│           │ agent_name (TEXT)               │
│ description (TEXT)              │           │ action (TEXT)                   │
│ status (TEXT: ACTIVE / REVOKED) │           │ amount (TEXT)                   │
│ registered_at (TEXT, ISO 8601)  │           │ decision (TEXT)                 │
│ revoked_at (TEXT, ISO 8601)     │           │ rule_applied (TEXT)             │
│ UNIQUE(customer_id, agent_name) │           │ explanation (TEXT)              │
└─────────────────────────────────┘           │ status (TEXT)                   │
                                              │ timestamp (TEXT, ISO 8601)      │
                                              └─────────────────────────────────┘
                                                               │
                                                               ▲
                                                               │
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│          audit_events           │           │            approvals            │
├─────────────────────────────────┤           ├─────────────────────────────────┤
│ event_id (PK, AUTOINCREMENT)    │           │ approval_id (PK, TEXT)          │
│ timestamp (TEXT, ISO 8601)      │           │ request_id (FK, TEXT)           │────┘
│ event_type (TEXT)               │           │ customer_id (TEXT)              │
│ agent_id (TEXT, NULLABLE)       │           │ decision (TEXT: APPROVED/REJECT)│
│ customer_id (TEXT, NULLABLE)    │           │ decided_at (TEXT, ISO 8601)     │
│ request_id (TEXT, NULLABLE)     │           │ comments (TEXT)                 │
│ details (TEXT)                  │           └─────────────────────────────────┘
└─────────────────────────────────┘
```

---

## 9. Technology Stack

The project adheres to pinned, reproducible dependencies compatible with Python 3.13+:

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Programming Language** | Python | `3.13.1` | Core runtime and standard library execution |
| **Web UI Framework** | Streamlit | `1.67.0` | Reactive, multi-page administrative dashboard |
| **Data Visualization** | Plotly | `7.1.0` | Interactive decision distribution and volume charts |
| **Data Manipulation** | Pandas | `3.0.6` | Tabular data formatting and telemetry analysis |
| **Database Engine** | SQLite3 | `3.45.3` | Relational storage with foreign keys and SQL triggers |
| **Precise Arithmetic** | `decimal.Decimal` | Standard Library | Fixed-point financial computation without float drift |
| **Timezone Management** | `zoneinfo` / `tzdata` | Standard Library | ISO 8601 Asia/Kolkata (IST) timestamp generation |
| **Test Framework** | `unittest` / `pytest` | `pytest 8.3.4` | Automated test suite with isolated temp databases |

All dependencies are pinned in [requirements.txt](file:///c:/Users/panka/OneDrive/Desktop/Ryanair-Agent-Gatekeeper/requirements.txt):
```text
pandas==3.0.6
plotly==7.1.0
streamlit==1.67.0
```

---

## 10. Local Installation & Setup

### Prerequisites
- Python `3.13+` installed on your machine.
- Git installed.

### Step 1: Clone the Repository
```bash
git clone https://github.com/pankajk4-ui/Ryanair-Agent-Gatekeeper.git
cd Ryanair-Agent-Gatekeeper
```

### Step 2: Create and Activate a Virtual Environment
- **On Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
- **On macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### Step 3: Install Pinned Dependencies
```bash
pip install -r requirements.txt
```

---

## 11. Running the Application

Launch the Streamlit web dashboard locally:
```bash
streamlit run app.py
```

The application will start and be accessible in your web browser at:
```text
http://localhost:8501
```

### Dashboard Navigation Guide
The sidebar provides access to six dedicated operational modules:
1. **`📊 Dashboard`**: Real-time KPI metric cards (Total Agents, Active, Revoked, Requests, Decisions breakdown), interactive Plotly decision distribution donut chart, requests-by-action bar chart, and recent audit logs.
2. **`📝 Register Agent`**: Provision new agents with Customer ID, Customer Name, Agent Name, and optional Description. Displays generated Agent IDs and enforces duplicate/revocation checks.
3. **`⚡ Check Agent Request`**: Interactive transaction tester. Select an agent or input parameters manually, select an action (`View Fares`, `Book Flight`, `Change Booking`, `Request Refund`), specify an amount in EUR, and evaluate against the 7 rules with immediate visual feedback.
4. **`🚫 Revoke Agent`**: Select any active agent from the database, confirm revocation, and terminate authority with an immutable timestamp.
5. **`📋 Customer Approvals`**: Human-in-the-Loop review queue displaying requests placed in `PENDING APPROVAL` by Rules R5 and R6. Customers can approve or reject with custom comments.
6. **`ℹ️ About Project`**: Academic details, rule reference tables, and production architecture notes.

---

## 12. Testing & Verification Suite

All business rules, amount boundaries, and database triggers are verified using an automated test suite ([test_cases.py](file:///c:/Users/panka/OneDrive/Desktop/Ryanair-Agent-Gatekeeper/test_cases.py)) executing against isolated in-memory databases (`:memory:`).

### Running Tests
Execute the test suite using either of the following commands:

```bash
# 1. Direct Command-Line Runner (with formatted test output)
python test_cases.py

# 2. Python Standard Library Unittest Runner
python -m unittest test_cases.py -v

# 3. Pytest Runner (if installed)
pytest test_cases.py -v
```

### Test Suite Coverage (21 Test Cases)
The test suite systematically verifies every requirement:
- **`test_r4_boundary_200`**: Verifies exact `EUR 200.00` integer evaluates to `ALLOW (R4)`.
- **`test_r4_boundary_200_00`**: Verifies `EUR 200.00` formatted Decimal/string evaluates to `ALLOW (R4)`.
- **`test_r5_boundary_200_01`**: Verifies `EUR 200.01` boundary evaluates to `ASK CUSTOMER (R5)`.
- **`test_r7_amount_zero_book_flight`**: Verifies `EUR 0` for `Book Flight` evaluates to `BLOCK (R7)`.
- **`test_r7_amount_negative_one`**: Verifies negative amount `EUR -1` evaluates to `BLOCK (R7)`.
- **`test_r7_amount_text_abc`**: Verifies non-numeric string `"abc"` evaluates to `BLOCK (R7)`.
- **`test_r7_amount_empty_string`**: Verifies empty amount string `""` evaluates to `BLOCK (R7)`.
- **`test_r7_amount_nan`**: Verifies `NaN` (`float('nan')` and `"NaN"`) evaluates to `BLOCK (R7)`.
- **`test_r7_view_fares_with_negative_five`**: Verifies negative amount on read-only action evaluates to `BLOCK (R7)`.
- **`test_whitespace_and_case_variants_of_agent_name`**: Verifies case-insensitivity and whitespace trimming for agent names.
- **`test_r1_unknown_agent`**: Verifies unregistered agent evaluates to `BLOCK (R1)`.
- **`test_r1_unknown_agent_with_unsupported_action`**: Verifies unregistered check precedes action validation (returns `R1`, not `R7`).
- **`test_r2_revoked_agent_four_actions`**: Verifies revoked agent evaluates to `BLOCK (R2)` across all 4 supported actions.
- **`test_r2_revoked_agent_with_amount_negative_one`**: Verifies Rule R2 overrides invalid inputs (returns `R2`, not `R7`).
- **`test_r7_unsupported_action_cancel_flight`**: Verifies unsupported action evaluates to `BLOCK (R7)`.
- **`test_r3_view_fares_default_amount`**: Verifies `View Fares` with omitted amount defaults to `EUR 0.00` and evaluates to `ALLOW (R3)`.
- **`test_r6_change_booking_and_refund`**: Verifies `Change Booking` and `Request Refund` evaluate to `ASK CUSTOMER (R6)`.
- **`test_duplicate_registration_prevention`**: Verifies duplicate active registrations for the same customer are rejected.
- **`test_re_registration_of_revoked_agent_prevention`**: Verifies re-registering a revoked agent name is blocked (no silent reactivation).
- **`test_audit_log_append_only_enforcement`**: Verifies database triggers abort direct SQL `UPDATE` and `DELETE` on `audit_events`.
- **`test_pending_approval_state_transition`**: Verifies transition from `PENDING APPROVAL` to `APPROVED`/`REJECTED`.

### Verified Test Run Output
```text
===========================================================================
RYANAIR AGENT GATEKEEPER - STAGE 1 TEST SUITE
Student: Pankaj Kumar Tiwari | Reg No: PGD202564630 | Shoolini University
===========================================================================
[PASS] 1. EUR 200.00 exact limit (ALLOW, R4)
[PASS] 2. EUR 200.00 formatted Decimal (ALLOW, R4)
[PASS] 3. EUR 200.01 limit boundary (ASK CUSTOMER, R5)
[PASS] 4. EUR 0 for Book Flight (BLOCK, R7)
[PASS] 5. Negative amount EUR -1 (BLOCK, R7)
[PASS] 6. Non-numeric text amount 'abc' (BLOCK, R7)
[PASS] 7. Empty string amount '' (BLOCK, R7)
[PASS] 8. NaN amount handling (BLOCK, R7)
[PASS] 9. View Fares with EUR -5 (BLOCK, R7)
[PASS] 10. Whitespace and case variants of agent name
[PASS] 11. Unknown agent (BLOCK, R1)
[PASS] 12. Unknown agent with unsupported action (BLOCK, R1)
[PASS] 13. Revoked agent across all 4 actions (BLOCK, R2)
[PASS] 14. Revoked agent with amount -1 (BLOCK, R2)
[PASS] 15. Unsupported action 'Cancel Flight' (BLOCK, R7)
[PASS] 16. View Fares default amount 0.00 (ALLOW, R3)
[PASS] 17. Change Booking / Refund (ASK CUSTOMER, R6)
[PASS] 18. Duplicate active registration rejection
[PASS] 19. Re-registration of revoked agent rejection
[PASS] 20. Audit log append-only trigger enforcement
[PASS] 21. PENDING APPROVAL state transition
===========================================================================
RESULTS: 21 PASSED, 0 FAILED (Total: 21)
===========================================================================
```

---

## 13. Enterprise Production Security Considerations

While this academic project simulates agent identity using normalized tuples `(customer_id, agent_name)` and SQLite storage, an enterprise production deployment in commercial aviation would implement:

1. **Mutual TLS (mTLS) & PKI:** Every external agent client would be issued an X.509 client certificate verified by an airline API Gateway.
2. **OAuth 2.0 / OpenID Connect (OIDC) Scopes:** Fine-grained authorization tokens (RFC 6749 / RFC 7519) binding the agent to cryptographic scopes (e.g., `ryanair:fares:read`, `ryanair:booking:create:max200`).
3. **Cryptographic Payload Signing:** Agent requests would carry an asymmetric HTTP signature (RFC 9421) generated by a secure hardware module (TPM / Apple Secure Enclave) for mathematical non-repudiation.
4. **Distributed WORM Audit Storage:** Audit events would stream into Write-Once-Read-Many (WORM) cloud object storage (e.g., AWS S3 Object Lock, Google Cloud Storage Bucket Lock) or an enterprise append-only distributed ledger for regulatory audit readiness.
5. **Dynamic Anomaly Detection:** Real-time rate limiting, IP reputation filtering, and token velocity checks to thwart automated scraping or denial-of-inventory attacks.
