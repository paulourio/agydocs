"""Reference Python client implementation demonstrating SDK parity,
naming validation, and deterministic dialect error classification.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set


class EngineError(Exception):
    """Base exception for engine errors."""


class ProhibitedDialectError(EngineError):
    """Raised when foreign dialect constructs are detected."""


class InvalidNamingError(EngineError):
    """Raised when an identifier violates ISO 11179 naming conventions."""


ALLOWED_CLASS_WORDS: Set[str] = {
    "id", "nm", "dt", "ts", "amt", "qty", "val", "rt", "p", "ind", "cd"
}


@dataclass(frozen=True)
class ColumnMetadata:
    """Schema column metadata."""

    name: str
    data_type: str
    nullable: bool = True

    def validate_naming(self) -> None:
        """Verifies column identifier terminates with a valid ISO 11179 class word."""
        parts = self.name.split("_")
        if len(parts) < 2:
            raise InvalidNamingError(
                f"Column '{self.name}' lacks required domain prefix and class word suffix"
            )
        suffix = parts[-1]
        if suffix not in ALLOWED_CLASS_WORDS:
            raise InvalidNamingError(
                f"Column '{self.name}' has non-standard suffix '{suffix}'. Allowed: {sorted(ALLOWED_CLASS_WORDS)}"
            )


@dataclass
class QueryResult:
    """Represents the execution outcome of an engine query."""

    query_id: str
    rows_scanned: int
    execution_ms: int


class Client:
    """High-performance client for tool execution."""

    def __init__(self, endpoint: str, timeout_seconds: float = 30.0) -> None:
        if not endpoint:
            raise ValueError("Endpoint must not be empty")
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def execute_query(self, query: str) -> QueryResult:
        """Executes a query after asserting dialect hygiene."""
        prohibited = ["AS MATERIALIZED", "SELECT AS VALUE"]
        upper = query.upper()
        for p in prohibited:
            if p in upper:
                raise ProhibitedDialectError(f"Query contains prohibited dialect construct: '{p}'")

        # Simulate execution
        time.sleep(0.005)
        return QueryResult(
            query_id="py-mock-001",
            rows_scanned=42,
            execution_ms=5,
        )
