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
