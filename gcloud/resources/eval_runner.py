#!/usr/bin/env python3
"""Automated prompt evaluation runner for tool skills.

Asserts dialect purity, architectural token requirements, RFC 1035 cloud naming compliance,
and formatting consistency against agent-generated code artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvaluationSpec:
    """Specification defining required invariants and constraints for code artifacts."""

    tool_name: str
    prohibited_tokens: list[str] = field(default_factory=list)
    required_tokens: list[str] = field(default_factory=list)
    naming_conventions: list[str] = field(default_factory=list)
    max_line_length: int = 120
    indent_step: int = 2

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationSpec:
        return cls(
            tool_name=data.get("tool_name", "generic_tool"),
            prohibited_tokens=data.get("prohibited_tokens", []),
            required_tokens=data.get("required_tokens", []),
            naming_conventions=data.get("naming_conventions", []),
            max_line_length=data.get("max_line_length", 120),
            indent_step=data.get("indent_step", 2),
        )

    @classmethod
    def from_file(cls, path: Path) -> EvaluationSpec:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


@dataclass
class EvaluationResult:
    """Evaluation result detailing rule compliance and specific violations."""

    passed: bool
    violations: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "metrics": self.metrics,
        }


def evaluate_artifact(code_text: str, spec: EvaluationSpec) -> EvaluationResult:
    """Evaluates code text against the provided evaluation specification."""
    violations: list[str] = []
    lines = code_text.splitlines()

    # 1. Dialect Purity (Rule of Complete Omission)
    for token in spec.prohibited_tokens:
        if token.lower() in code_text.lower():
            violations.append(
                f"Prohibited dialect token detected: '{token}' (Rule of Complete Omission)"
            )

    # 2. Required Architectural Tokens (Server-side filters, headless execution)
    for token in spec.required_tokens:
        if token not in code_text:
            violations.append(f"Missing required invariant token: '{token}'")

    # 3. Cloud Resource Naming Verification (RFC 1035 / DNS-1123 label standards)
    if spec.naming_conventions:
        compiled_patterns = [re.compile(p) for p in spec.naming_conventions]
        # Match explicit resource identifiers passed to create/delete/describe commands or project flags
        resource_matches = re.findall(
            r"(?:gcloud\s+[\w-]+\s+[\w-]+\s+(?:create|delete|describe)\s+([a-zA-Z0-9_-]+)|--project=([a-zA-Z0-9_-]+))",
            code_text,
        )
        for pos_match, flag_match in resource_matches:
            target = pos_match or flag_match
            if not target or target.startswith("$"):
                continue
            if not any(pat.match(target) for pat in compiled_patterns):
                violations.append(
                    f"Resource identifier '{target}' violates cloud naming convention ({spec.naming_conventions})"
                )

    # 4. Mechanical Formatting Checks
    long_lines = [
        i + 1 for i, line in enumerate(lines) if len(line) > spec.max_line_length
    ]
    if long_lines:
        violations.append(
            f"Line length limit ({spec.max_line_length} chars) exceeded on lines: {long_lines[:5]}"
        )

    # Indentation step consistency check (skipped if indent_step <= 0)
    if spec.indent_step > 0:
        odd_indents = []
        for i, line in enumerate(lines):
            stripped = line.lstrip(" ")
            if stripped and not stripped.startswith(("--", "//", "#", "/*", "*")):
                indent = len(line) - len(stripped)
                if indent > 0 and (indent % spec.indent_step) != 0:
                    odd_indents.append(i + 1)
        if odd_indents:
            violations.append(
                f"Inconsistent indentation (must be multiple of {spec.indent_step}) on lines: {odd_indents[:5]}"
            )

    passed = len(violations) == 0
    metrics = {
        "line_count": len(lines),
        "word_count": len(code_text.split()),
        "prohibited_checks": len(spec.prohibited_tokens),
        "required_checks": len(spec.required_tokens),
        "violations_count": len(violations),
    }

    return EvaluationResult(passed=passed, violations=violations, metrics=metrics)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate code artifacts against skill invariants."
    )
    parser.add_argument(
        "--spec",
        type=Path,
        required=True,
        help="Path to evaluation specification JSON file.",
    )
    parser.add_argument(
        "--artifact",
        type=Path,
        required=True,
        help="Path to code artifact to evaluate.",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output result as structured JSON."
    )

    args = parser.parse_args()

    if not args.spec.is_file():
        print(f"Error: Specification file not found: {args.spec}", file=sys.stderr)
        return 2

    if not args.artifact.is_file():
        print(f"Error: Artifact file not found: {args.artifact}", file=sys.stderr)
        return 2

    spec = EvaluationSpec.from_file(args.spec)
    with open(args.artifact, "r", encoding="utf-8") as f:
        code_text = f.read()

    result = evaluate_artifact(code_text, spec)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status_symbol = "🟢 PASS" if result.passed else "🔴 FAIL"
        print(f"=== Artifact Evaluation: {args.artifact.name} ===")
        print(f"Status: {status_symbol}")
        print(
            f"Lines: {result.metrics['line_count']} | Violations: {len(result.violations)}"
        )
        if result.violations:
            print("\nViolations:")
            for v in result.violations:
                print(f"  ❌ {v}")

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
