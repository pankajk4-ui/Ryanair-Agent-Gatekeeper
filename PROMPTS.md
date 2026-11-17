# Prompts & Requirements Log: Ryanair Agent Gatekeeper

**Academic Simulation — MBA Agentic AI Assignment**  
**Student:** Pankaj Kumar Tiwari | **Registration No.:** PGD202564630 | **Shoolini University**

---

## Stage 1 Prompt: Engine and Database Foundation

```text
PROJECT: Ryanair Agent Gatekeeper (academic simulation, MBA Agentic AI assignment)
Student: Pankaj Kumar Tiwari | Registration No.: PGD202564630 | Shoolini University
Company: Ryanair (airline). Do NOT connect to any real Ryanair system, account, payment gateway or API.

PURPOSE
Decide whether a request from a customer's external AI agent should be ALLOW, ASK CUSTOMER or BLOCK, with a rule number and explanation. Also register agents, revoke them with a saved date and time, and keep a permanent audit log.

STACK
Python, Streamlit, SQLite, Pandas, Plotly. Pin exact versions in requirements.txt.

STRUCTURE
Ryanair-Agent-Gatekeeper/
  app.py, database.py, gatekeeper.py, test_cases.py,
  requirements.txt, README.md, PROMPTS.md, .gitignore, data/.gitkeep
.gitignore must exclude data/*.db, __pycache__/ and .venv/.

GENERAL RULES
- Decisions are deterministic Python rules. No AI model, no randomness.
- Agent identity = (customer_id, agent_name), both normalised (trim whitespace, agent_name case-insensitive). Each agent also gets a generated Agent ID. State in the README that a real system would use credentials or tokens instead.
- Amounts use Decimal (never float). NaN, infinity, text and empty values are invalid.
- All timestamps: ISO 8601 in Asia/Kolkata (IST), stored consistently.
- database.py and gatekeeper.py must accept a database path or connection so tests can use a temporary database.
- Use parameterised SQL, create the database automatically, never delete data on restart, handle DB errors gracefully.
- audit_events is append-only (no updates or deletes). Request status may change PENDING -> APPROVED/REJECTED separately.
- Do NOT run git commands. I will make all commits myself.
- Before changing existing files, inspect them. Do not rewrite working files; if you find a bug, fix it minimally and tell me.
- Do not claim anything works unless you actually ran it. Report real output, including failures. Do not fabricate commits, screenshots, timestamps or claims of my personal work.
- Make reasonable decisions without asking for confirmation. Finish this stage once, with no retry loops.

THE SEVEN RULES (supported actions: View Fares, Book Flight, Change Booking, Request Refund)
Evaluation order (deterministic):
 1. Registered? -> else R1
 2. Revoked? -> R2 (overrides everything, including invalid input)
 3. Valid action and amount? -> else R7
 4. Apply R3-R6
 5. Return decision, rule number, explanation, timestamp
 6. Write to audit log
R1 Unknown agent: customer ID and agent identity not registered -> BLOCK. "The agent has not been authorised by the customer."
R2 Revoked agent: registered but REVOKED -> BLOCK, whatever the action or amount. "The customer has withdrawn the agent's permission." The revocation date and time are stored as proof of when permission ended.
R3 View Fares: registered, active agent -> ALLOW. "Viewing fares is read-only."
R4 Book Flight up to and including EUR 200.00: registered, active agent -> ALLOW. Registering the agent counts as the customer's authorisation of this limit.
R5 Book Flight above EUR 200.00 -> ASK CUSTOMER. "High-value bookings need explicit customer confirmation."
R6 Change Booking or Request Refund -> ASK CUSTOMER. "These affect existing travel arrangements and financial entitlements."
R7 Invalid request: unsupported action, missing details, or invalid amount -> BLOCK. R7 must not overlap with R1/R2.
AMOUNT VALIDATION: for every action, a negative, non-numeric, empty, NaN or infinite amount is invalid (R7). Zero is invalid only for Book Flight. For View Fares, Change Booking and Request Refund the amount defaults to 0.
Boundaries: exactly 200.00 = ALLOW (R4); 200.01 = ASK CUSTOMER (R5).
EUR 200 rationale (hypothetical limit, not Ryanair policy): "<I will fill in after checking Ryanair's average fare>". Leave this placeholder in the README.

STAGE 1 TASK: engine and database
Build only the foundation:
1. database.py: tables agents, requests, approvals, audit_events (with keys and relationships). agents has agent_id, customer_id, customer_name, agent_name, description, status (ACTIVE/REVOKED), registered_at, revoked_at.
2. Functions: register_agent (reject a duplicate active registration; reject re-registering a revoked agent name for the same customer, since there is no silent reactivation), revoke_agent (sets REVOKED and revoked_at, logs the event), get_agent, list_agents, log_request. Registration and revocation must write audit events even when no request was evaluated.
3. gatekeeper.py: evaluate_request(customer_id, agent_name, action, amount, db) implementing the seven rules in the stated order. Return a result object with decision, rule, explanation and timestamp. ASK CUSTOMER requests are saved as PENDING APPROVAL; nothing is ever executed.
4. A pytest file or command-line check covering: 200, 200.00, 200.01, 0, -1, "abc", "", NaN, View Fares with -5, whitespace and case variants of the agent name, unknown agent, unknown agent with unsupported action (R1), revoked agent with each of the four actions (R2), revoked agent with amount -1 (R2), and unsupported action "Cancel Flight" (R7).
Run the checks on a temporary database and report real results. Create requirements.txt, .gitignore and a short README stub. Do not build the UI yet.
```

---

## Stage 2 Prompt: Streamlit Interface Development

```text
# STAGE 2: STREAMLIT INTERFACE DEVELOPMENT
## Ryanair Agent Gatekeeper

Act as a senior Python developer and professional UI/UX designer.

I have already completed Stage 1 of my Ryanair Agent Gatekeeper project.

The existing backend has:
- database.py
- gatekeeper.py
- app.py
- test_cases.py
- README.md
- PROMPTS.md
- requirements.txt

Stage 1 has passed 21 tests with zero failures.

GitHub repository:
https://github.com/pankajk4-ui/Ryanair-Agent-Gatekeeper

Student: Pankaj Kumar Tiwari
Registration Number: PGD202564630

## IMPORTANT INSTRUCTIONS
First inspect all existing project files.
Understand the existing database functions, decision engine, business rules and application structure before making changes.
Do not rebuild the backend from scratch.
Do not remove or weaken any existing functionality.
Do not change the seven established business rules.
Preserve compatibility with the existing database and test suite.
Make actual code changes rather than providing a development plan.
Complete this stage in one controlled task. Do not enter an infinite development or rewriting loop.

## 1. PROFESSIONAL DASHBOARD
Build a premium Streamlit dashboard for Ryanair Agent Gatekeeper.
Design requirements:
- Modern airline-inspired design.
- Navy blue, white and Ryanair-inspired yellow and blue accents.
- Professional typography.
- Clean spacing and alignment.
- Attractive metric cards.
- Modern tables.
- Clear status indicators.
- Consistent navigation.
- Responsive layout.

Display:
RYANAIR AGENT GATEKEEPER
AI Agent Permission & Transaction Control System
Student: Pankaj Kumar Tiwari
Registration Number: PGD202564630

Create dashboard metrics using actual database information:
- Total Registered Agents
- Active Agents
- Revoked Agents
- Total Requests

Also show:
- ALLOW decisions
- ASK CUSTOMER decisions
- BLOCK decisions

Include a decision distribution chart and recent activity section if the existing data supports them.
Do not use hardcoded dashboard numbers.

## 2. SIDEBAR NAVIGATION
Create the following navigation:
1. Dashboard
2. Register Agent
3. Check Agent Request
4. Revoke Agent
5. Customer Approvals
6. About Project

The interface should allow users to move between pages without losing saved database records.

## 3. AGENT REGISTRATION PAGE
Create a professional registration form.
Fields:
- Customer ID
- Customer Name
- Agent Name
- Agent Description (optional)

Use the existing registration functions from database.py.
Display registration success and validation errors clearly.
Show registered agents in a table with:
- Agent ID
- Customer ID
- Customer Name
- Agent Name
- Registration Date
- Status
Prevent duplicate registrations according to the existing backend rules.

## 4. REQUEST EVALUATION PAGE
Create a clean request evaluation interface.
Input fields:
- Customer ID
- Agent Name
- Requested Action
- Transaction Amount in EUR

Supported actions:
- View Fares
- Book Flight
- Change Booking
- Request Refund

Add a prominent EVALUATE REQUEST button.
Use the actual decision engine from gatekeeper.py.
Do not duplicate or rewrite the decision logic inside app.py.
Display the result prominently:
ALLOW
ASK CUSTOMER
BLOCK

Show:
- Decision
- Rule number
- Explanation
- Customer ID
- Agent Name
- Requested Action
- Amount
- Date and time

Use green for ALLOW, amber for ASK CUSTOMER and red for BLOCK.
All evaluated requests must be recorded using the existing database logging functions.
Do not execute real bookings, payments or refunds.

## 5. AGENT REVOCATION PAGE
Create a dedicated agent management page.
Display registered agents and their current status.
Allow the user to select an active agent and revoke its permission.
Use the existing real revocation function.
Record the exact revocation timestamp.
Require a confirmation before revoking.
Immediately reflect the revoked status.
```
