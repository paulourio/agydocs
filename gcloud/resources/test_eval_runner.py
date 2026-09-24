#!/usr/bin/env python3
"""Unit tests for the automated prompt evaluation runner."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_runner import EvaluationSpec, evaluate_artifact


class TestEvalRunner(unittest.TestCase):
    """Test suite verifying evaluation runner invariant enforcement."""

    def setUp(self) -> None:
        self.spec = EvaluationSpec(
            tool_name="gcloud",
            prohibited_tokens=[
                "gsutil ",
                "bq query",
                "aws ",
                "az ",
                "activate-service-account --key-file",
                "| grep",
            ],
            required_tokens=["--quiet", "--format="],
            naming_conventions=["^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$"],
            max_line_length=140,
            indent_step=0,
        )

    def test_clean_artifact_passes(self) -> None:
        valid_script = (
            "gcloud compute instances list \\\n"
            "  --project=core-infra-prod \\\n"
            '  --filter="status=RUNNING" \\\n'
            '  --format="json" \\\n'
            "  --quiet\n"
        )
        result = evaluate_artifact(valid_script, self.spec)
        self.assertTrue(
            result.passed, f"Expected clean pass, got violations: {result.violations}"
        )
        self.assertEqual(len(result.violations), 0)

    def test_prohibited_token_fails(self) -> None:
        invalid_script = (
            "gsutil cp -r ./data gs://my-bucket/ \\\n  --quiet --format=json\n"
        )
        result = evaluate_artifact(invalid_script, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("gsutil " in v for v in result.violations))

    def test_static_key_prohibition_fails(self) -> None:
        invalid_script = (
            "gcloud auth activate-service-account --key-file=sa-key.json \\\n"
            "  --quiet --format=json\n"
        )
        result = evaluate_artifact(invalid_script, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(
            any("activate-service-account --key-file" in v for v in result.violations)
        )

    def test_missing_required_token_fails(self) -> None:
        missing_quiet_script = 'gcloud compute instances list \\\n  --format="json"\n'
        result = evaluate_artifact(missing_quiet_script, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("--quiet" in v for v in result.violations))

    def test_client_side_grep_fails(self) -> None:
        grep_script = (
            "gcloud compute instances list --format=text | grep worker-01 --quiet\n"
        )
        result = evaluate_artifact(grep_script, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("| grep" in v for v in result.violations))

    def test_naming_convention_enforcement(self) -> None:
        invalid_name_script = (
            "gcloud compute instances create INVALID_UPPERCASE \\\n"
            '  --format="json" \\\n'
            "  --quiet\n"
        )
        result = evaluate_artifact(invalid_name_script, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(
            any("violates cloud naming convention" in v for v in result.violations)
        )

        valid_name_script = (
            "gcloud compute instances create worker-prod-01 \\\n"
            '  --format="json" \\\n'
            "  --quiet\n"
        )
        result_valid = evaluate_artifact(valid_name_script, self.spec)
        self.assertTrue(result_valid.passed)

    def test_line_length_violation(self) -> None:
        long_line = (
            "gcloud compute instances create "
            + ("x" * 150)
            + " --quiet --format=json\n"
        )
        result = evaluate_artifact(long_line, self.spec)
        self.assertFalse(result.passed)
        self.assertTrue(any("Line length limit" in v for v in result.violations))


if __name__ == "__main__":
    unittest.main()
