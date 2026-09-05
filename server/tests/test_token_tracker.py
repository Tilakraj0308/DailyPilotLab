"""
Unit test for TokenTracker and cost engine.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tokens.cost_engine import calculate_token_cost
from tokens.tracker import TokenTracker
from db.dbConnection import get_dict_cursor

class TestTokenTracker(unittest.TestCase):

    def test_cost_calculation(self):
        # gpt-4o-mini: 1000 prompt tokens ($0.00015), 500 completion tokens ($0.0003)
        cost = calculate_token_cost("gpt-4o-mini", 1000, 500)
        self.assertEqual(cost, 0.00045)

    def test_tracker_flow(self):
        # Fetch or insert a valid user_id for test
        with get_dict_cursor() as cur:
            cur.execute("SELECT auth_id FROM public.users LIMIT 1")
            row = cur.fetchone()
            if row:
                user_id = row["auth_id"]
            else:
                user_id = "test_auth_user_001"
                cur.execute(
                    "INSERT INTO public.users (auth_id, email, display_name) VALUES (%s, %s, %s)",
                    (user_id, "test@example.com", "Test User")
                )

        trace_id = TokenTracker.start_trace(
            user_id=user_id,
            request_type="chat",
            model="gpt-4o-mini",
            metadata={"test": True}
        )
        self.assertIsNotNone(trace_id)

        # Log step 1: LLM iteration
        TokenTracker.add_timeline_step(
            trace_id=trace_id,
            step_number=1,
            name="LLM Iteration 1",
            event_type="llm_call",
            model="gpt-4o-mini",
            prompt_tokens=450,
            completion_tokens=65,
            duration_ms=320,
            details={"finish_reason": "tool_calls"}
        )

        # Log step 2: Tool execution
        TokenTracker.add_timeline_step(
            trace_id=trace_id,
            step_number=2,
            name="Tool Execution: google_calendar_read",
            event_type="tool_execution",
            model=None,
            prompt_tokens=0,
            completion_tokens=0,
            duration_ms=180,
            details={"tool_name": "google_calendar_read"}
        )

        # Log step 3: Final LLM synthesis
        TokenTracker.add_timeline_step(
            trace_id=trace_id,
            step_number=3,
            name="LLM Iteration 2",
            event_type="llm_call",
            model="gpt-4o-mini",
            prompt_tokens=620,
            completion_tokens=110,
            duration_ms=450,
            details={"finish_reason": "stop"}
        )

        TokenTracker.finalize_trace(trace_id=trace_id, duration_ms=950, status="completed")

        # Fetch stats & timeline
        stats = TokenTracker.get_user_stats(user_id)
        self.assertGreaterEqual(stats["overview"]["total_requests"], 1)
        self.assertGreaterEqual(stats["overview"]["total_tokens"], 1245)

        timeline = TokenTracker.get_trace_timeline(trace_id, user_id)
        self.assertIsNotNone(timeline)
        self.assertEqual(len(timeline["timeline"]), 3)
        self.assertEqual(timeline["total_tokens"], 1245)

        print("TokenTracker Unit Test passed successfully!")

if __name__ == "__main__":
    unittest.main()
