"""
Ryanair Agent Gatekeeper - Gatekeeper Engine
Academic simulation for MBA Agentic AI assignment.
Student: Pankaj Kumar Tiwari | Reg No: PGD202564630 | Shoolini University

Enforces deterministic gatekeeper rules for customer external AI agents.
Evaluation Order:
  1. Registered? -> else R1
  2. Revoked? -> R2 (overrides everything, including invalid input)
  3. Valid action and amount? -> else R7
  4. Apply R3-R6:
       R3: View Fares -> ALLOW
       R4: Book Flight <= EUR 200.00 -> ALLOW
       R5: Book Flight > EUR 200.00 -> ASK CUSTOMER
       R6: Change Booking / Request Refund -> ASK CUSTOMER
  5. Return decision, rule number, explanation, timestamp
  6. Write to audit log
"""

import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

from database import (
    get_agent,
    get_ist_now_iso,
    log_request,
)

SUPPORTED_ACTIONS = ("View Fares", "Book Flight", "Change Booking", "Request Refund")
EUR_LIMIT = Decimal("200.00")


@dataclass
class GatekeeperResult:
    """
    Standard result returned by the Ryanair Agent Gatekeeper evaluation engine.
    Supports both attribute access (result.decision) and dictionary access (result['decision']).
    """
    decision: str          # ALLOW | ASK CUSTOMER | BLOCK
    rule: str              # R1 .. R7
    explanation: str       # Standardized explanation
    timestamp: str         # ISO 8601 in Asia/Kolkata
    request_id: str        # Unique request identifier
    customer_id: str       # Normalized customer identifier
    agent_name: str        # Normalized agent name
    action: str            # Requested action
    amount: Optional[Decimal]  # Parsed Decimal amount (or None)
    status: str            # ALLOWED | BLOCKED | PENDING APPROVAL
    agent_id: Optional[str] = None  # Agent ID from database (if found)
    revoked_at: Optional[str] = None # Revocation timestamp (if R2)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "rule": self.rule,
            "explanation": self.explanation,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "customer_id": self.customer_id,
            "agent_name": self.agent_name,
            "action": self.action,
            "amount": str(self.amount) if self.amount is not None else None,
            "status": self.status,
            "agent_id": self.agent_id,
            "revoked_at": self.revoked_at,
        }


def parse_and_validate_amount(amount: Any, action: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Validate and convert amount to Decimal (never float).
    Amounts cannot be negative, non-numeric, empty, NaN, or infinite.
    Zero is invalid only for Book Flight.
    For View Fares, Change Booking, and Request Refund, amount defaults to 0.00 when omitted (None).
    """
    if isinstance(amount, bool):
        return None, "Boolean amount is invalid."

    # Default amount for non-booking actions if omitted
    if amount is None:
        if action in ("View Fares", "Change Booking", "Request Refund"):
            return Decimal("0.00"), None
        return None, "Missing booking amount for Book Flight."

    # String parsing
    if isinstance(amount, str):
        cleaned = amount.strip()
        if not cleaned:
            return None, "Amount cannot be empty."
        if cleaned.lower() in ("nan", "inf", "-inf", "+inf", "infinity", "-infinity"):
            return None, "NaN or infinite amounts are invalid."
        try:
            val = Decimal(cleaned)
        except InvalidOperation:
            return None, f"Non-numeric amount: '{amount}'."
    elif isinstance(amount, float):
        if math.isnan(amount) or math.isinf(amount):
            return None, "NaN or infinite amounts are invalid."
        val = Decimal(str(amount))
    elif isinstance(amount, Decimal):
        if amount.is_nan() or amount.is_infinite():
            return None, "NaN or infinite amounts are invalid."
        val = amount
    elif isinstance(amount, int):
        val = Decimal(amount)
    else:
        return None, f"Unsupported amount type: {type(amount).__name__}."

    # Additional validations
    if val.is_nan() or val.is_infinite():
        return None, "NaN or infinite amounts are invalid."

    if val < Decimal("0.00"):
        return None, f"Negative amount is invalid: EUR {val}."

    if val == Decimal("0.00") and action == "Book Flight":
        return None, "Zero amount is invalid for Book Flight."

    return val, None


def evaluate_request(
    customer_id: str,
    agent_name: str,
    action: str,
    amount: Any = None,
    db: Any = None
) -> GatekeeperResult:
    """
    Evaluate an incoming customer agent request against the seven deterministic rules.

    Evaluation Order:
      1. Registered? -> else R1
      2. Revoked? -> R2 (overrides everything, including invalid input)
      3. Valid action and amount? -> else R7
      4. Apply R3-R6:
           R3: View Fares -> ALLOW
           R4: Book Flight <= EUR 200.00 -> ALLOW
           R5: Book Flight > EUR 200.00 -> ASK CUSTOMER
           R6: Change Booking or Request Refund -> ASK CUSTOMER
      5. Return decision, rule number, explanation, timestamp
      6. Write to audit log
    """
    timestamp = get_ist_now_iso()
    norm_customer_id = str(customer_id).strip() if customer_id is not None else ""
    norm_agent_name = str(agent_name).strip() if agent_name is not None else ""
    clean_action = str(action).strip() if action is not None else ""

    # 1. Registered? -> else R1
    agent = None
    if norm_customer_id and norm_agent_name:
        agent = get_agent(customer_id=norm_customer_id, agent_name=norm_agent_name, db=db)

    if not agent:
        decision = "BLOCK"
        rule = "R1"
        explanation = "The agent has not been authorised by the customer."
        status = "BLOCKED"
        req_id = log_request({
            "agent_id": None,
            "customer_id": norm_customer_id,
            "agent_name": norm_agent_name,
            "action": clean_action,
            "amount": amount if isinstance(amount, (int, str, Decimal)) else (str(amount) if amount is not None else None),
            "decision": decision,
            "rule_applied": rule,
            "explanation": explanation,
            "status": status,
            "timestamp": timestamp,
        }, db=db)
        return GatekeeperResult(
            decision=decision,
            rule=rule,
            explanation=explanation,
            timestamp=timestamp,
            request_id=req_id,
            customer_id=norm_customer_id,
            agent_name=norm_agent_name,
            action=clean_action,
            amount=None,
            status=status,
            agent_id=None,
        )

    # 2. Revoked? -> R2 (overrides everything, including invalid input)
    if agent["status"] == "REVOKED":
        decision = "BLOCK"
        rule = "R2"
        explanation = "The customer has withdrawn the agent's permission."
        status = "BLOCKED"
        revoked_at = agent.get("revoked_at")
        req_id = log_request({
            "agent_id": agent["agent_id"],
            "customer_id": norm_customer_id,
            "agent_name": norm_agent_name,
            "action": clean_action,
            "amount": amount if isinstance(amount, (int, str, Decimal)) else (str(amount) if amount is not None else None),
            "decision": decision,
            "rule_applied": rule,
            "explanation": explanation,
            "status": status,
            "timestamp": timestamp,
        }, db=db)
        return GatekeeperResult(
            decision=decision,
            rule=rule,
            explanation=explanation,
            timestamp=timestamp,
            request_id=req_id,
            customer_id=norm_customer_id,
            agent_name=norm_agent_name,
            action=clean_action,
            amount=None,
            status=status,
            agent_id=agent["agent_id"],
            revoked_at=revoked_at,
        )

    # 3. Valid action and amount? -> else R7
    if clean_action not in SUPPORTED_ACTIONS:
        decision = "BLOCK"
        rule = "R7"
        explanation = f"Invalid request: unsupported action '{clean_action}'."
        status = "BLOCKED"
        req_id = log_request({
            "agent_id": agent["agent_id"],
            "customer_id": norm_customer_id,
            "agent_name": norm_agent_name,
            "action": clean_action,
            "amount": amount if isinstance(amount, (int, str, Decimal)) else (str(amount) if amount is not None else None),
            "decision": decision,
            "rule_applied": rule,
            "explanation": explanation,
            "status": status,
            "timestamp": timestamp,
        }, db=db)
        return GatekeeperResult(
            decision=decision,
            rule=rule,
            explanation=explanation,
            timestamp=timestamp,
            request_id=req_id,
            customer_id=norm_customer_id,
            agent_name=norm_agent_name,
            action=clean_action,
            amount=None,
            status=status,
            agent_id=agent["agent_id"],
        )

    parsed_amount, amount_err = parse_and_validate_amount(amount, clean_action)
    if amount_err is not None:
        decision = "BLOCK"
        rule = "R7"
        explanation = f"Invalid request: {amount_err}"
        status = "BLOCKED"
        req_id = log_request({
            "agent_id": agent["agent_id"],
            "customer_id": norm_customer_id,
            "agent_name": norm_agent_name,
            "action": clean_action,
            "amount": amount if isinstance(amount, (int, str, Decimal)) else (str(amount) if amount is not None else None),
            "decision": decision,
            "rule_applied": rule,
            "explanation": explanation,
            "status": status,
            "timestamp": timestamp,
        }, db=db)
        return GatekeeperResult(
            decision=decision,
            rule=rule,
            explanation=explanation,
            timestamp=timestamp,
            request_id=req_id,
            customer_id=norm_customer_id,
            agent_name=norm_agent_name,
            action=clean_action,
            amount=None,
            status=status,
            agent_id=agent["agent_id"],
        )

    # 4. Apply R3-R6
    if clean_action == "View Fares":
        # R3: View Fares: registered, active agent -> ALLOW
        decision = "ALLOW"
        rule = "R3"
        explanation = "Viewing fares is read-only."
        status = "ALLOWED"

    elif clean_action == "Book Flight":
        # parsed_amount is guaranteed valid Decimal > 0
        if parsed_amount <= EUR_LIMIT:
            # R4: Book Flight up to and including EUR 200.00 -> ALLOW
            decision = "ALLOW"
            rule = "R4"
            explanation = "Registering the agent counts as the customer's authorisation of this limit."
            status = "ALLOWED"
        else:
            # R5: Book Flight above EUR 200.00 -> ASK CUSTOMER
            decision = "ASK CUSTOMER"
            rule = "R5"
            explanation = "High-value bookings need explicit customer confirmation."
            status = "PENDING APPROVAL"

    elif clean_action in ("Change Booking", "Request Refund"):
        # R6: Change Booking or Request Refund -> ASK CUSTOMER
        decision = "ASK CUSTOMER"
        rule = "R6"
        explanation = "These affect existing travel arrangements and financial entitlements."
        status = "PENDING APPROVAL"

    else:
        # Fallback (should not be reached due to earlier checks)
        decision = "BLOCK"
        rule = "R7"
        explanation = "Invalid request: unsupported operation."
        status = "BLOCKED"

    # 5. Return decision, rule number, explanation, timestamp & 6. Write to audit log
    req_id = log_request({
        "agent_id": agent["agent_id"],
        "customer_id": norm_customer_id,
        "agent_name": norm_agent_name,
        "action": clean_action,
        "amount": parsed_amount,
        "decision": decision,
        "rule_applied": rule,
        "explanation": explanation,
        "status": status,
        "timestamp": timestamp,
    }, db=db)

    return GatekeeperResult(
        decision=decision,
        rule=rule,
        explanation=explanation,
        timestamp=timestamp,
        request_id=req_id,
        customer_id=norm_customer_id,
        agent_name=norm_agent_name,
        action=clean_action,
        amount=parsed_amount,
        status=status,
        agent_id=agent["agent_id"],
    )
