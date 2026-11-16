"""
Ryanair Agent Gatekeeper - Test Suite & Verification Runner
Academic simulation for MBA Agentic AI assignment.
Student: Pankaj Kumar Tiwari | Reg No: PGD202564630 | Shoolini University

Covers all required Stage 1 test cases:
  1. 200 (Book Flight EUR 200 -> R4 ALLOW)
  2. 200.00 (Book Flight EUR 200.00 -> R4 ALLOW)
  3. 200.01 (Book Flight EUR 200.01 -> R5 ASK CUSTOMER)
  4. 0 (Book Flight EUR 0 -> R7 BLOCK)
  5. -1 (Book Flight EUR -1 -> R7 BLOCK)
  6. "abc" (Book Flight EUR "abc" -> R7 BLOCK)
  7. "" (Book Flight EUR "" -> R7 BLOCK)
  8. NaN (Book Flight EUR NaN -> R7 BLOCK)
  9. View Fares with -5 (View Fares EUR -5 -> R7 BLOCK)
  10. Whitespace and case variants of agent name (match registered agent)
  11. Unknown agent (R1 BLOCK)
  12. Unknown agent with unsupported action (R1 BLOCK, registered check precedes)
  13. Revoked agent with each of the four actions (R2 BLOCK for all 4)
  14. Revoked agent with amount -1 (R2 BLOCK, overrides invalid input)
  15. Unsupported action "Cancel Flight" (R7 BLOCK)
  + Additional tests: default amounts, registration constraints, append-only audit enforcement.

Runs cleanly via:
  - python test_cases.py (Command-line check)
  - python -m unittest test_cases.py (Standard Library runner)
  - pytest test_cases.py (Pytest runner)
"""

import math
import os
import sqlite3
import sys
import unittest
from decimal import Decimal
from pathlib import Path

from database import (
    get_agent,
    get_audit_events,
    init_db,
    list_agents,
    register_agent,
    revoke_agent,
    update_request_approval,
)
from gatekeeper import evaluate_request


def create_test_db() -> sqlite3.Connection:
    """Create an isolated, temporary in-memory database with full schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


# --- Pytest & Direct test functions ---

def test_r4_boundary_200():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        result = evaluate_request("CUST100", "FlightBot", "Book Flight", 200, db=conn)
        assert result.decision == "ALLOW", f"Expected ALLOW, got {result.decision}"
        assert result.rule == "R4", f"Expected R4, got {result.rule}"
        assert result.status == "ALLOWED"
        assert result.amount == Decimal("200")
    finally:
        conn.close()


def test_r4_boundary_200_00():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        # Test both Decimal("200.00") and string "200.00"
        result = evaluate_request("CUST100", "FlightBot", "Book Flight", Decimal("200.00"), db=conn)
        assert result.decision == "ALLOW"
        assert result.rule == "R4"
        assert result.status == "ALLOWED"

        result_str = evaluate_request("CUST100", "FlightBot", "Book Flight", "200.00", db=conn)
        assert result_str.decision == "ALLOW"
        assert result_str.rule == "R4"
    finally:
        conn.close()


def test_r5_boundary_200_01():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        # Test both Decimal("200.01") and string "200.01"
        result = evaluate_request("CUST100", "FlightBot", "Book Flight", Decimal("200.01"), db=conn)
        assert result.decision == "ASK CUSTOMER"
        assert result.rule == "R5"
        assert result.status == "PENDING APPROVAL"

        result_str = evaluate_request("CUST100", "FlightBot", "Book Flight", "200.01", db=conn)
        assert result_str.decision == "ASK CUSTOMER"
        assert result_str.rule == "R5"
        assert result_str.status == "PENDING APPROVAL"
    finally:
        conn.close()


def test_r7_amount_zero_book_flight():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        result = evaluate_request("CUST100", "FlightBot", "Book Flight", 0, db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R7"
        assert result.status == "BLOCKED"
        assert "Zero amount is invalid" in result.explanation
    finally:
        conn.close()


def test_r7_amount_negative_one():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        result = evaluate_request("CUST100", "FlightBot", "Book Flight", -1, db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R7"
        assert result.status == "BLOCKED"
        assert "Negative amount is invalid" in result.explanation
    finally:
        conn.close()


def test_r7_amount_text_abc():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        result = evaluate_request("CUST100", "FlightBot", "Book Flight", "abc", db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R7"
        assert result.status == "BLOCKED"
        assert "Non-numeric amount" in result.explanation
    finally:
        conn.close()


def test_r7_amount_empty_string():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        result = evaluate_request("CUST100", "FlightBot", "Book Flight", "", db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R7"
        assert result.status == "BLOCKED"
        assert "empty" in result.explanation.lower()
    finally:
        conn.close()


def test_r7_amount_nan():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        # Test float('nan')
        result_nan = evaluate_request("CUST100", "FlightBot", "Book Flight", float("nan"), db=conn)
        assert result_nan.decision == "BLOCK"
        assert result_nan.rule == "R7"
        assert result_nan.status == "BLOCKED"

        # Test string "NaN"
        result_str_nan = evaluate_request("CUST100", "FlightBot", "Book Flight", "NaN", db=conn)
        assert result_str_nan.decision == "BLOCK"
        assert result_str_nan.rule == "R7"
    finally:
        conn.close()


def test_r7_view_fares_with_negative_five():
    conn = create_test_db()
    try:
        register_agent("CUST100", "Alice Smith", "FlightBot", db=conn)
        result = evaluate_request("CUST100", "FlightBot", "View Fares", -5, db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R7"
        assert result.status == "BLOCKED"
        assert "Negative amount is invalid" in result.explanation
    finally:
        conn.close()


def test_whitespace_and_case_variants_of_agent_name():
    conn = create_test_db()
    try:
        agent = register_agent("  CUST200  ", "Bob Jones", "TravelScout", db=conn)
        assert agent["customer_id"] == "CUST200"
        assert agent["agent_name"] == "TravelScout"

        variants = [
            "  TravelScout  ",
            "travelscout",
            "TRAVELSCOUT",
            "  tRaVeLsCoUt  ",
            "TravelScout",
        ]
        for variant in variants:
            res = evaluate_request("CUST200", variant, "Book Flight", 150, db=conn)
            assert res.decision == "ALLOW", f"Variant '{variant}' failed with {res.decision}"
            assert res.rule == "R4", f"Variant '{variant}' failed with rule {res.rule}"
            assert res.agent_id == agent["agent_id"]
    finally:
        conn.close()


def test_r1_unknown_agent():
    conn = create_test_db()
    try:
        result = evaluate_request("GHOST_CUST", "UnknownAgent", "View Fares", db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R1"
        assert result.status == "BLOCKED"
        assert result.explanation == "The agent has not been authorised by the customer."
    finally:
        conn.close()


def test_r1_unknown_agent_with_unsupported_action():
    conn = create_test_db()
    try:
        # Step 1 (Registered?) precedes Step 3 (Valid action/amount?)
        result = evaluate_request("GHOST_CUST", "UnknownAgent", "Cancel Flight", -999, db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R1"
        assert result.explanation == "The agent has not been authorised by the customer."
    finally:
        conn.close()


def test_r2_revoked_agent_four_actions():
    conn = create_test_db()
    try:
        register_agent("CUST300", "Carol White", "BookingAssistant", db=conn)
        revoke_agent("CUST300", "BookingAssistant", db=conn)

        actions = [
            ("View Fares", None),
            ("Book Flight", 50),
            ("Change Booking", None),
            ("Request Refund", None),
        ]
        for action, amt in actions:
            result = evaluate_request("CUST300", "BookingAssistant", action, amt, db=conn)
            assert result.decision == "BLOCK", f"Action '{action}' did not return BLOCK"
            assert result.rule == "R2", f"Action '{action}' did not trigger R2 (got {result.rule})"
            assert result.status == "BLOCKED"
            assert result.explanation == "The customer has withdrawn the agent's permission."
            assert result.revoked_at is not None, "Revocation timestamp must be recorded"
    finally:
        conn.close()


def test_r2_revoked_agent_with_amount_negative_one():
    conn = create_test_db()
    try:
        register_agent("CUST300", "Carol White", "BookingAssistant", db=conn)
        revoke_agent("CUST300", "BookingAssistant", db=conn)

        # R2 overrides invalid input (Step 2 precedes Step 3)
        result = evaluate_request("CUST300", "BookingAssistant", "Book Flight", -1, db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R2"
        assert result.explanation == "The customer has withdrawn the agent's permission."
    finally:
        conn.close()


def test_r7_unsupported_action_cancel_flight():
    conn = create_test_db()
    try:
        register_agent("CUST400", "David Brown", "ActiveAgent", db=conn)
        result = evaluate_request("CUST400", "ActiveAgent", "Cancel Flight", db=conn)
        assert result.decision == "BLOCK"
        assert result.rule == "R7"
        assert result.status == "BLOCKED"
        assert "unsupported action" in result.explanation.lower()
    finally:
        conn.close()


def test_r3_view_fares_default_amount():
    conn = create_test_db()
    try:
        register_agent("CUST500", "Eva Green", "FaresBot", db=conn)
        result = evaluate_request("CUST500", "FaresBot", "View Fares", db=conn)
        assert result.decision == "ALLOW"
        assert result.rule == "R3"
        assert result.status == "ALLOWED"
        assert result.amount == Decimal("0.00")
        assert result.explanation == "Viewing fares is read-only."
    finally:
        conn.close()


def test_r6_change_booking_and_refund():
    conn = create_test_db()
    try:
        register_agent("CUST500", "Eva Green", "FaresBot", db=conn)

        res_change = evaluate_request("CUST500", "FaresBot", "Change Booking", db=conn)
        assert res_change.decision == "ASK CUSTOMER"
        assert res_change.rule == "R6"
        assert res_change.status == "PENDING APPROVAL"
        assert "affect existing travel arrangements" in res_change.explanation

        res_refund = evaluate_request("CUST500", "FaresBot", "Request Refund", db=conn)
        assert res_refund.decision == "ASK CUSTOMER"
        assert res_refund.rule == "R6"
        assert res_refund.status == "PENDING APPROVAL"
        assert "affect existing travel arrangements" in res_refund.explanation
    finally:
        conn.close()


def test_duplicate_registration_prevention():
    conn = create_test_db()
    try:
        register_agent("CUST600", "Frank Black", "AgentAlpha", db=conn)

        try:
            register_agent("CUST600", "Frank Black", "AgentAlpha", db=conn)
            assert False, "Should have raised ValueError on duplicate active registration"
        except ValueError as e:
            assert "already actively registered" in str(e)

        try:
            register_agent("CUST600", "Frank Black", "agentalpha", db=conn)
            assert False, "Should have raised ValueError on case-insensitive duplicate"
        except ValueError as e:
            assert "already actively registered" in str(e)
    finally:
        conn.close()


def test_re_registration_of_revoked_agent_prevention():
    conn = create_test_db()
    try:
        register_agent("CUST700", "Grace Hopper", "AgentBeta", db=conn)
        revoke_agent("CUST700", "AgentBeta", db=conn)

        try:
            register_agent("CUST700", "Grace Hopper", "AgentBeta", db=conn)
            assert False, "Should have raised ValueError on re-registering revoked agent"
        except ValueError as e:
            assert "no silent reactivation" in str(e).lower() or "previously revoked" in str(e).lower()
    finally:
        conn.close()


def test_audit_log_append_only_enforcement():
    conn = create_test_db()
    try:
        register_agent("CUST800", "Henry Ford", "AuditBot", db=conn)
        revoke_agent("CUST800", "AuditBot", db=conn)
        evaluate_request("CUST800", "AuditBot", "View Fares", db=conn)

        events = get_audit_events(db=conn)
        assert len(events) >= 3, "Expected at least 3 audit events (register, revoke, evaluate)"

        # Direct UPDATE on audit_events must be blocked by SQLite trigger
        try:
            conn.execute("UPDATE audit_events SET event_type = 'TAMPERED' WHERE event_id = 1")
            assert False, "SQLite trigger should have blocked UPDATE on audit_events"
        except sqlite3.DatabaseError as e:
            assert "append-only" in str(e).lower()

        # Direct DELETE on audit_events must be blocked by SQLite trigger
        try:
            conn.execute("DELETE FROM audit_events WHERE event_id = 1")
            assert False, "SQLite trigger should have blocked DELETE on audit_events"
        except sqlite3.DatabaseError as e:
            assert "append-only" in str(e).lower()
    finally:
        conn.close()


def test_pending_approval_state_transition():
    conn = create_test_db()
    try:
        register_agent("CUST900", "Iris Murdoch", "HighValueAgent", db=conn)
        result = evaluate_request("CUST900", "HighValueAgent", "Book Flight", 350, db=conn)
        assert result.decision == "ASK CUSTOMER"
        assert result.status == "PENDING APPROVAL"

        approval = update_request_approval(
            result.request_id,
            "CUST900",
            "APPROVED",
            comments="Approved by customer via SMS",
            db=conn
        )
        assert approval["decision"] == "APPROVED"

        cursor = conn.execute("SELECT status FROM requests WHERE request_id = ?", (result.request_id,))
        row = cursor.fetchone()
        assert row["status"] == "APPROVED"
    finally:
        conn.close()


# --- Standard Library unittest TestCase wrapper ---

class GatekeeperTestCase(unittest.TestCase):
    def test_01_boundary_200(self): test_r4_boundary_200()
    def test_02_boundary_200_00(self): test_r4_boundary_200_00()
    def test_03_boundary_200_01(self): test_r5_boundary_200_01()
    def test_04_amount_zero(self): test_r7_amount_zero_book_flight()
    def test_05_amount_negative(self): test_r7_amount_negative_one()
    def test_06_amount_text(self): test_r7_amount_text_abc()
    def test_07_amount_empty(self): test_r7_amount_empty_string()
    def test_08_amount_nan(self): test_r7_amount_nan()
    def test_09_view_fares_negative(self): test_r7_view_fares_with_negative_five()
    def test_10_name_variants(self): test_whitespace_and_case_variants_of_agent_name()
    def test_11_unknown_agent(self): test_r1_unknown_agent()
    def test_12_unknown_agent_unsupported_action(self): test_r1_unknown_agent_with_unsupported_action()
    def test_13_revoked_agent_four_actions(self): test_r2_revoked_agent_four_actions()
    def test_14_revoked_agent_amount_negative_one(self): test_r2_revoked_agent_with_amount_negative_one()
    def test_15_unsupported_action_cancel_flight(self): test_r7_unsupported_action_cancel_flight()
    def test_16_view_fares_default(self): test_r3_view_fares_default_amount()
    def test_17_change_booking_refund(self): test_r6_change_booking_and_refund()
    def test_18_duplicate_registration(self): test_duplicate_registration_prevention()
    def test_19_re_registration_revoked(self): test_re_registration_of_revoked_agent_prevention()
    def test_20_audit_append_only(self): test_audit_log_append_only_enforcement()
    def test_21_approval_transition(self): test_pending_approval_state_transition()


# --- Command-line Test Runner ---

def run_command_line_checks() -> int:
    """Run all test suites and output structured results to terminal."""
    tests = [
        ("1. EUR 200.00 exact limit (ALLOW, R4)", test_r4_boundary_200),
        ("2. EUR 200.00 formatted Decimal (ALLOW, R4)", test_r4_boundary_200_00),
        ("3. EUR 200.01 limit boundary (ASK CUSTOMER, R5)", test_r5_boundary_200_01),
        ("4. EUR 0 for Book Flight (BLOCK, R7)", test_r7_amount_zero_book_flight),
        ("5. Negative amount EUR -1 (BLOCK, R7)", test_r7_amount_negative_one),
        ("6. Non-numeric text amount 'abc' (BLOCK, R7)", test_r7_amount_text_abc),
        ("7. Empty string amount '' (BLOCK, R7)", test_r7_amount_empty_string),
        ("8. NaN amount handling (BLOCK, R7)", test_r7_amount_nan),
        ("9. View Fares with EUR -5 (BLOCK, R7)", test_r7_view_fares_with_negative_five),
        ("10. Whitespace and case variants of agent name", test_whitespace_and_case_variants_of_agent_name),
        ("11. Unknown agent (BLOCK, R1)", test_r1_unknown_agent),
        ("12. Unknown agent with unsupported action (BLOCK, R1)", test_r1_unknown_agent_with_unsupported_action),
        ("13. Revoked agent across all 4 actions (BLOCK, R2)", test_r2_revoked_agent_four_actions),
        ("14. Revoked agent with amount -1 (BLOCK, R2)", test_r2_revoked_agent_with_amount_negative_one),
        ("15. Unsupported action 'Cancel Flight' (BLOCK, R7)", test_r7_unsupported_action_cancel_flight),
        ("16. View Fares default amount 0.00 (ALLOW, R3)", test_r3_view_fares_default_amount),
        ("17. Change Booking / Refund (ASK CUSTOMER, R6)", test_r6_change_booking_and_refund),
        ("18. Duplicate active registration rejection", test_duplicate_registration_prevention),
        ("19. Re-registration of revoked agent rejection", test_re_registration_of_revoked_agent_prevention),
        ("20. Audit log append-only trigger enforcement", test_audit_log_append_only_enforcement),
        ("21. PENDING APPROVAL state transition", test_pending_approval_state_transition),
    ]

    print("=" * 75)
    print("RYANAIR AGENT GATEKEEPER - STAGE 1 TEST SUITE")
    print("Student: Pankaj Kumar Tiwari | Reg No: PGD202564630 | Shoolini University")
    print("=" * 75)

    passed_count = 0
    failed_count = 0

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"[PASS] {name}")
            passed_count += 1
        except Exception as exc:
            print(f"[FAIL] {name} -> Error: {exc}")
            failed_count += 1

    print("=" * 75)
    print(f"RESULTS: {passed_count} PASSED, {failed_count} FAILED (Total: {len(tests)})")
    print("=" * 75)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(run_command_line_checks())
