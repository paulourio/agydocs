"""Tests for BigQuery Schema Extraction and Dry-Run Utility."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock

from schema_extraction import (
    BYTES_PER_TERABYTE,
    MIN_BILLABLE_BYTES,
    PRICE_PER_TERABYTE_USD,
    field_to_dict,
)


class TestSchemaExtraction(unittest.TestCase):
    def test_pricing_constants(self) -> None:
        """Verify BigQuery decimal pricing constants."""
        self.assertEqual(BYTES_PER_TERABYTE, Decimal(10**12))
        self.assertEqual(PRICE_PER_TERABYTE_USD, Decimal("6.25"))
        self.assertEqual(MIN_BILLABLE_BYTES, Decimal(10 * 1024 * 1024))

    def test_pricing_cost_calculation(self) -> None:
        """Verify cost calculation with decimal TB and 10 MB minimum."""
        # 1. Zero bytes scanned -> $0.00
        bytes_scanned = Decimal(0)
        bytes_billed = Decimal(0)
        effective = (
            bytes_billed
            if bytes_billed > 0
            else (
                max(bytes_scanned, MIN_BILLABLE_BYTES)
                if bytes_scanned > 0
                else Decimal(0)
            )
        )
        cost = (effective / BYTES_PER_TERABYTE) * PRICE_PER_TERABYTE_USD
        self.assertEqual(cost, Decimal(0))

        # 2. 1 MB scanned (sub-10MB) -> billed at 10 MB minimum
        bytes_scanned = Decimal(1024 * 1024)
        bytes_billed = Decimal(0)
        effective = (
            bytes_billed
            if bytes_billed > 0
            else (
                max(bytes_scanned, MIN_BILLABLE_BYTES)
                if bytes_scanned > 0
                else Decimal(0)
            )
        )
        self.assertEqual(effective, MIN_BILLABLE_BYTES)
        cost = (effective / BYTES_PER_TERABYTE) * PRICE_PER_TERABYTE_USD
        expected_cost = (Decimal(10485760) / Decimal(10**12)) * Decimal("6.25")
        self.assertEqual(cost, expected_cost)

        # 3. 2 TB scanned -> 2 * $6.25 = $12.50
        bytes_scanned = Decimal(2 * 10**12)
        bytes_billed = bytes_scanned
        effective = bytes_billed
        cost = (effective / BYTES_PER_TERABYTE) * PRICE_PER_TERABYTE_USD
        self.assertEqual(cost, Decimal("12.5000"))

    def test_field_to_dict(self) -> None:
        """Verify recursive conversion of SchemaField mock."""
        mock_field = MagicMock()
        mock_field.name = "user_id"
        mock_field.field_type = "INT64"
        mock_field.mode = "REQUIRED"
        mock_field.description = "Unique user ID"
        mock_field.fields = []
        mock_field.policy_tags = None

        d = field_to_dict(mock_field)
        self.assertEqual(
            d,
            {
                "name": "user_id",
                "type": "INT64",
                "mode": "REQUIRED",
                "description": "Unique user ID",
            },
        )


if __name__ == "__main__":
    unittest.main()
