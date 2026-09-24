#!/usr/bin/env python3
"""Unit tests for the automated prompt evaluation runner."""

import unittest
from pathlib import Path
from eval_runner import EvaluationSpec, EvaluationResult, evaluate_artifact


class TestEvalRunner(unittest.TestCase):
    """Test suite verifying evaluation runner invariant enforcement."""

    def setUp(self) -> None:
        self.spec = EvaluationSpec(
            tool_name="test_sql_engine",
            prohibited_tokens=["AS MATERIALIZED", "SELECT AS VALUE", "TEMPORARY FUNCTION"],
            required_tokens=["WHERE event_ts >=", "event_id"],
            max_line_length=100,
            indent_step=0,
        )

    def test_clean_artifact_passes(self) -> None:
        valid_sql = (
            "WITH filtered_events AS (\n"
            "  SELECT event_id, user_id, event_ts\n"
            "    FROM telemetry_events\n"
            "   WHERE event_ts >= TIMESTAMP('2026-03-01 00:00:00 UTC')\n"
            ")\n"
            "SELECT user_id, COUNT(event_id) AS event_qty\n"
            "  FROM filtered_events\n"
            " GROUP BY user_id\n"
        )
        result = evaluate_artifact(valid_sql, self.spec)
        self.assertTrue(result.passed, f"Expected clean pass, got violations: {result.violations}")
        self.assertEqual(len(result.violations), 0)

    def test_prohibited_token_fails(self) -> None:
        invalid_sql = (
            "WITH filtered_events AS MATERIALIZED (\n"
            "  SELECT event_id, user_id, event_ts\n"
            "    FROM telemetry_events\n"
            "   WHERE event_ts >= TIMESTAMP('2026-03-01 00:00:00 UTC')\n"
            ")\n"
            "SELECT user_id, COUNT(event_id) AS event_qty\n"
            "  FROM filtered_events\n"
            " GROUP BY user_id\n"
        )
        result = evaluate_artifact(invalid_sql, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("AS MATERIALIZED" in v for v in result.violations))

    def test_missing_required_token_fails(self) -> None:
        missing_filter_sql = (
            "SELECT user_id, COUNT(event_id) AS event_qty\n"
            "  FROM telemetry_events\n"
            " GROUP BY user_id\n"
        )
        result = evaluate_artifact(missing_filter_sql, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("WHERE event_ts >=" in v for v in result.violations))

    def test_line_length_violation(self) -> None:
        long_line_sql = (
            "SELECT " + ("x" * 120) + " AS event_id\n"
            "  FROM telemetry_events\n"
            " WHERE event_ts >= TIMESTAMP('2026-03-01 00:00:00 UTC')\n"
        )
        result = evaluate_artifact(long_line_sql, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("Line length limit" in v for v in result.violations))

    def test_indent_step_violation(self) -> None:
        py_spec = EvaluationSpec(
            tool_name="test_py_engine",
            indent_step=2,
        )
        bad_indent = "def foo():\n   x = 1\n"
        result = evaluate_artifact(bad_indent, py_spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("Inconsistent indentation" in v for v in result.violations))


if __name__ == "__main__":
    unittest.main()
