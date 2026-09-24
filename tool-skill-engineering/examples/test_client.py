#!/usr/bin/env python3
"""Unit tests for the reference Python client implementation."""

import unittest
from client import Client, ColumnMetadata, InvalidNamingError, ProhibitedDialectError


class TestClient(unittest.TestCase):
    """Test suite verifying Python client behavior and invariants."""

    def test_client_init_validation(self) -> None:
        with self.assertRaises(ValueError):
            Client("")

        cli = Client("mock://localhost:9000")
        self.assertEqual(cli.endpoint, "mock://localhost:9000")
        self.assertEqual(cli.timeout_seconds, 30.0)

    def test_column_naming_validation(self) -> None:
        valid_cols = [
            ColumnMetadata("user_id", "INT64"),
            ColumnMetadata("total_amt", "NUMERIC"),
            ColumnMetadata("event_ts", "TIMESTAMP"),
        ]
        for col in valid_cols:
            col.validate_naming()  # Should not raise

        invalid_cols = [
            ColumnMetadata("user", "STRING"),
            ColumnMetadata("user_name", "STRING"),  # Should be user_nm
            ColumnMetadata("amount", "NUMERIC"),     # Should be amount_amt or total_amt
        ]
        for col in invalid_cols:
            with self.assertRaises(InvalidNamingError):
                col.validate_naming()

    def test_execute_query_dialect_rejection(self) -> None:
        cli = Client("mock://localhost:9000")
        with self.assertRaises(ProhibitedDialectError):
            cli.execute_query("WITH t AS MATERIALIZED (SELECT 1)")

    def test_execute_query_clean(self) -> None:
        cli = Client("mock://localhost:9000")
        res = cli.execute_query("SELECT user_id, event_ts FROM events_fact")
        self.assertEqual(res.rows_scanned, 42)
        self.assertTrue(res.query_id.startswith("py-mock"))


if __name__ == "__main__":
    unittest.main()
