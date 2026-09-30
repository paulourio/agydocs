"""
test_prompt_integrity.py - Validates prompt contents, toxic phrase absence, and NLP quality gates.
"""

import subprocess
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = MODULE_DIR.parent


class TestPromptIntegrity(unittest.TestCase):
    def setUp(self):
        self.agent_md = MODULE_DIR / "antigravity.md"
        self.prompt_md = MODULE_DIR / "antigravity.prompt.md"
        self.readme_md = MODULE_DIR / "README.md"
        self.steering_dir = MODULE_DIR / "steering"
        self.quality_gate_bin = WORKSPACE_ROOT / "writing" / "bin" / "quality_gate"

    def test_absence_of_kiro_toxic_phrases(self):
        content = self.agent_md.read_text(encoding="utf-8")
        toxic_patterns = [
            "annoy them",
            "don't take it too seriously",
            "follow up with appends",
            "absolute MINIMAL skeleton",
            "cracks a joke",
            "supportive, not authoritative",
            "in as few steps as possible",
        ]
        for pattern in toxic_patterns:
            self.assertNotIn(
                pattern.lower(),
                content.lower(),
                f"Toxic Kiro pattern '{pattern}' must not appear in antigravity.md",
            )

    def test_presence_of_antigravity_invariants(self):
        # Invariants are distributed across the agent prompt body and steering
        # files. Aggregate content from both sources for the invariant check.
        agent_content = self.agent_md.read_text(encoding="utf-8")
        steering_content = "".join(
            f.read_text(encoding="utf-8")
            for f in sorted(self.steering_dir.glob("*.md"))
        )
        combined = (agent_content + steering_content).lower()
        required_invariants = [
            "write",
            "fs_write",
            "shell",
            "read",
            "Gate 0",
            "CI=1 PAGER=cat NO_COLOR=1",
            "--no-verify",
            "Ousterhout",
            "Deep Modules",
            "Text-First",
            "Empirical Ground Truth",
            "Clickable",
            "file://",
            "Layer 0",
            "Layer 1",
            "Layer 2",
            "Conventional Commits",
            "GoogleSQL",
            "BigQuery",
            "Full-Stack Verification",
            "`cd`",
            "Hardware Truth",
            "subagent",
            "Compute Cadences",
            "ISO 11179",
            "_feat",
            "_jnl",
            "subsystem and stage boundaries",
            "prefer `rg`",
            "prefer `fd`",
            "Conversational Pairing Register",
            "references/conversational_pairing.md",
            "Zero Sycophancy",
        ]
        for invariant in required_invariants:
            self.assertIn(
                invariant.lower(),
                combined,
                f"Antigravity invariant '{invariant}' must be present in "
                f"antigravity.md or steering files",
            )

    def test_nlp_quality_gate_on_agent_and_steering(self):
        if not self.quality_gate_bin.exists():
            self.skipTest(f"Quality gate binary not found at {self.quality_gate_bin}")

        docs_to_check = [self.agent_md, self.prompt_md, self.readme_md] + sorted(
            self.steering_dir.glob("*.md")
        )
        for doc in docs_to_check:
            result = subprocess.run(
                [str(self.quality_gate_bin), "--profile", "rfc", str(doc)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"Quality gate failed on {doc.name}:\n{result.stdout}\n{result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
