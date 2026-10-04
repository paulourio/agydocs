"""
test_agent_config.py - Validates kiro-agent configurations against Kiro specs.
"""

import fnmatch
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

MODULE_DIR = Path(__file__).resolve().parent.parent


class TestAgentConfig(unittest.TestCase):
    def setUp(self):
        self.md_file = MODULE_DIR / "antigravity.md"
        self.json_file = MODULE_DIR / "antigravity.json"
        self.prompt_file = MODULE_DIR / "antigravity.prompt.md"
        self.steering_dir = MODULE_DIR / "steering"
        self.hooks_dir = MODULE_DIR / "hooks"
        self.install_sh = MODULE_DIR / "install.sh"

    def test_markdown_agent_frontmatter(self):
        self.assertTrue(self.md_file.exists(), "antigravity.md must exist")
        content = self.md_file.read_text(encoding="utf-8")
        parts = content.split("---")
        self.assertGreaterEqual(
            len(parts), 3, "antigravity.md must contain YAML frontmatter"
        )

        frontmatter = yaml.safe_load(parts[1])
        self.assertEqual(frontmatter.get("name"), "antigravity")
        self.assertIn("description", frontmatter)
        # Default model is omitted to respect workspace or user default model
        self.assertIsNone(
            frontmatter.get("model"),
            "Default agent configuration should not pin a model",
        )

        # Ensure no MCP servers are declared for native mode
        self.assertNotIn(
            "mcpServers", frontmatter, "mcpServers must be absent for native mode"
        )

        # Validate tools include core categories and agentic tools
        tools = frontmatter.get("tools", [])
        expected_tools = ["read", "write", "shell", "web", "subagent"]
        for required_tool in expected_tools:
            self.assertIn(
                required_tool,
                tools,
                f"Tool category '{required_tool}' must be in tools",
            )

        # Validate excluded tools
        excluded = frontmatter.get("excludedTools", [])
        self.assertIn(
            "knowledge", excluded, "knowledge tool should be in excludedTools"
        )

        # Validate allowed tools (pre-approved tools for non-interactive execution)
        allowed = frontmatter.get("allowedTools", [])
        expected_allowed = [
            "read",
            "write",
            "shell",
            "glob",
            "grep",
            "web_search",
            "web_fetch",
            "subagent",
            "fs_read",
            "fs_write",
            "execute_bash",
            "invoke_subagent",
        ]
        for tool in expected_allowed:
            self.assertIn(tool, allowed, f"Tool '{tool}' must be in allowedTools")
        self.assertNotIn(
            "use_subagent",
            allowed,
            "use_subagent is not a valid tool name (use invoke_subagent)",
        )
        self.assertNotIn(
            "@builtin",
            allowed,
            "@builtin should not be in allowedTools to ensure granular permission enforcement",
        )

        # Validate permission rules
        permissions = frontmatter.get("permissions", {}).get("rules", [])
        self.assertTrue(len(permissions) > 0, "permissions.rules must not be empty")

        # Check deny rules
        deny_rules = [r for r in permissions if r.get("effect") == "deny"]
        self.assertTrue(
            len(deny_rules) >= 2, "Must have deny rules for shell and sensitive files"
        )

        shell_denied = []
        for r in deny_rules:
            if r.get("capability") == "shell":
                shell_denied.extend(r.get("match", []))

        self.assertIn("*--no-ver*", shell_denied)
        self.assertIn("*git * -n", shell_denied)
        self.assertIn("*git * -n *", shell_denied)
        self.assertIn("*git * -nm *", shell_denied)
        self.assertIn("*core.hooksPath*", shell_denied)
        self.assertTrue(
            any("rm -rf *" in m for m in shell_denied), "Must deny rm -rf *"
        )
        self.assertTrue(any("sudo *" in m for m in shell_denied), "Must deny sudo *")

        file_denied = []
        for r in deny_rules:
            if r.get("capability") in ("fs_write", "fs_read"):
                file_denied.extend(r.get("match", []))
        self.assertTrue(
            any(".env" in m for m in file_denied), "Must deny access to .env files"
        )

        # Check allow rules
        allow_rules = [r for r in permissions if r.get("effect") == "allow"]
        allowed_capabilities = {r.get("capability") for r in allow_rules}
        for cap in [
            "shell",
            "fs_read",
            "fs_write",
            "web_search",
            "web_fetch",
            "subagent",
            "skill",
        ]:
            self.assertIn(
                cap, allowed_capabilities, f"Capability '{cap}' must have an allow rule"
            )

        # Validate resources
        resources = frontmatter.get("resources", [])
        self.assertNotIn(
            "file://~/.gemini/GEMINI.md",
            resources,
            "GEMINI.md must not be in resources (steering files are canonical)",
        )
        self.assertIn("file://.kiro/steering/**/*.md", resources)
        self.assertIn("file://~/.kiro/steering/**/*.md", resources)
        self.assertTrue(
            any("skill://" in r for r in resources), "Must declare skill resources"
        )

        # Validate hooks are not embedded in agent config to ensure IDE 1.0 compatibility
        self.assertNotIn(
            "hooks",
            frontmatter,
            "hooks must be defined in standalone hooks/*.json rather than agent config",
        )

        # Validate welcome message
        self.assertIn("welcomeMessage", frontmatter)

    def test_json_agent_config(self):
        self.assertTrue(self.json_file.exists(), "antigravity.json must exist")
        content = json.loads(self.json_file.read_text(encoding="utf-8"))

        self.assertEqual(content.get("name"), "antigravity")
        self.assertNotIn(
            "mcpServers", content, "mcpServers must be absent in JSON config"
        )
        self.assertIsNone(content.get("model"))
        self.assertIn("knowledge", content.get("excludedTools", []))
        for t in ["read", "write", "shell", "web", "subagent"]:
            self.assertIn(t, content.get("tools", []))
        for at in [
            "read",
            "write",
            "shell",
            "glob",
            "grep",
            "web_search",
            "web_fetch",
            "subagent",
            "invoke_subagent",
        ]:
            self.assertIn(at, content.get("allowedTools", []))

        self.assertEqual(content.get("prompt"), "file://./antigravity.prompt.md")
        self.assertIn("welcomeMessage", content)
        self.assertNotIn(
            "hooks",
            content,
            "hooks must be defined in standalone hooks/*.json rather than JSON config",
        )

        permissions = content.get("permissions", {}).get("rules", [])
        deny_rules = [r for r in permissions if r.get("effect") == "deny"]
        shell_denied = []
        for r in deny_rules:
            if r.get("capability") == "shell":
                shell_denied.extend(r.get("match", []))

        self.assertIn("*--no-ver*", shell_denied)
        self.assertIn("*git * -n", shell_denied)
        self.assertIn("*git * -n *", shell_denied)
        self.assertIn("*git * -nm *", shell_denied)
        self.assertIn("*core.hooksPath*", shell_denied)

    def test_prompt_body_synchronization(self):
        self.assertTrue(self.prompt_file.exists(), "antigravity.prompt.md must exist")
        prompt_content = self.prompt_file.read_text(encoding="utf-8").strip()

        md_content = self.md_file.read_text(encoding="utf-8")
        parts = md_content.split("---")
        self.assertGreaterEqual(len(parts), 3)
        body = "---".join(parts[2:]).strip()

        self.assertEqual(
            prompt_content,
            body,
            "antigravity.prompt.md must match the markdown body of antigravity.md character-for-character",
        )

    def test_steering_documents(self):
        self.assertTrue(self.steering_dir.is_dir(), "steering/ directory must exist")
        steering_files = list(self.steering_dir.glob("*.md"))
        self.assertGreaterEqual(
            len(steering_files), 5, "Must have at least 5 steering files"
        )

        always_stems = [
            "01-engineering-discipline",
            "02-quality-gate",
            "03-anti-cheat",
        ]
        auto_stems = [
            "04-peer-review-and-audit",
            "05-text-first-assets",
        ]

        for stem in always_stems:
            sf = self.steering_dir / f"{stem}.md"
            self.assertTrue(
                sf.exists(), f"Missing expected steering document: {stem}.md"
            )
            text = sf.read_text(encoding="utf-8")
            self.assertIn(
                "inclusion: always", text, f"{sf.name} must specify 'inclusion: always'"
            )

        for stem in auto_stems:
            sf = self.steering_dir / f"{stem}.md"
            self.assertTrue(
                sf.exists(), f"Missing expected steering document: {stem}.md"
            )
            text = sf.read_text(encoding="utf-8")
            self.assertIn(
                "inclusion: auto", text, f"{sf.name} must specify 'inclusion: auto'"
            )
            self.assertIn(
                "description:",
                text,
                f"{sf.name} must specify a description for auto inclusion",
            )

    def test_lifecycle_hooks_config(self):
        self.assertTrue(self.hooks_dir.is_dir(), "hooks/ directory must exist")
        hook_files = list(self.hooks_dir.glob("*.json"))
        self.assertGreaterEqual(
            len(hook_files), 1, "Must have at least one hook config"
        )

        status_hook = self.hooks_dir / "workspace-status.json"
        self.assertTrue(status_hook.exists(), "workspace-status.json must exist")
        data = json.loads(status_hook.read_text(encoding="utf-8"))
        self.assertEqual(data.get("version"), "v1")
        hooks = data.get("hooks", [])
        self.assertGreaterEqual(len(hooks), 1)
        hook = hooks[0]
        self.assertEqual(hook.get("name"), "workspace-status")
        self.assertEqual(hook.get("trigger"), "SessionStart")
        self.assertEqual(hook.get("action", {}).get("type"), "command")
        self.assertIn("git status --short", hook.get("action", {}).get("command", ""))

    def test_scout_subagent_config(self):
        scout_file = MODULE_DIR / "antigravity-scout.md"
        self.assertTrue(scout_file.exists(), "antigravity-scout.md must exist")
        content = scout_file.read_text(encoding="utf-8")
        parts = content.split("---")
        self.assertGreaterEqual(
            len(parts), 3, "antigravity-scout.md must contain YAML frontmatter"
        )

        frontmatter = yaml.safe_load(parts[1])
        self.assertEqual(frontmatter.get("name"), "antigravity-scout")
        self.assertEqual(
            frontmatter.get("model"),
            "claude-haiku-4.5",
            "Scout must use claude-haiku-4.5 for token economy",
        )

        # Scout must be read-only: no write or goal tools
        tools = frontmatter.get("tools", [])
        self.assertIn("read", tools)
        self.assertNotIn("write", tools, "Scout must not have write tools")
        self.assertNotIn("goal", tools, "Scout must not have goal tool")

        excluded = frontmatter.get("excludedTools", [])
        self.assertIn("write", excluded, "write must be in excludedTools")
        self.assertIn("goal", excluded, "goal must be in excludedTools")

        # Scout must deny fs_write
        rules = frontmatter.get("permissions", {}).get("rules", [])
        fs_write_denied = any(
            r.get("capability") == "fs_write" and r.get("effect") == "deny"
            for r in rules
        )
        self.assertTrue(fs_write_denied, "Scout must deny fs_write capability")

    def test_git_commit_fnmatch_permission_rules(self):
        """Assert legitimate commit commands are allowed and illicit commands are denied."""
        md_content = self.md_file.read_text(encoding="utf-8")
        frontmatter = yaml.safe_load(md_content.split("---")[1])
        json_content = json.loads(self.json_file.read_text(encoding="utf-8"))

        configs = [("antigravity.md", frontmatter), ("antigravity.json", json_content)]

        legitimate_commands = [
            'git commit -m "feat: add-new-feature"',
            'git commit -m "refactor: re-name"',
            'git commit -a -m "docs: pre-notify"',
            'git commit -m "fix: resolve-issue-123"',
            'git commit --amend -m "chore: update-deps"',
            'git commit -s -m "feat: add-new-feature"',
            'git commit --signoff -m "feat: add-new-feature"',
            "git commit -F commit_msg.txt",
            "git commit -a -F commit_msg.txt",
            "git commit --amend --no-edit",
            'git commit -v -m "fix: test-suite"',
        ]

        illicit_commands = [
            'git commit -n -m "bypass"',
            'git commit -nm "bypass"',
            'git commit -anm "bypass"',
            'git commit -nam "bypass"',
            "git commit --no-verify",
            "git commit --no-verif",
            "git commit --no-veri",
            'git commit -m "msg" -n',
            "git commit -n",
            'git commit -a -n -m "bypass"',
            'git commit -a -m "msg" -n',
            "git commit --amend -n",
            'git commit --amend -n -m "bypass"',
            'git commit --no-verify -m "bypass"',
            'git commit -s -n -m "bypass"',
            "git commit -v -n",
            "git commit -s --no-verify",
            "git -c core.hooksPath=/dev/null commit -m bypass",
            "git commit -c core.hooksPath=/dev/null -m bypass",
        ]

        for source_name, config in configs:
            rules = config.get("permissions", {}).get("rules", [])
            shell_denied = []
            for r in rules:
                if r.get("capability") == "shell" and r.get("effect") == "deny":
                    shell_denied.extend(r.get("match", []))

            # Legitimate commands evaluate to False (allowed)
            for cmd in legitimate_commands:
                is_denied = any(fnmatch.fnmatch(cmd, p) for p in shell_denied)
                self.assertFalse(
                    is_denied,
                    f"Legitimate command '{cmd}' should be allowed (evaluated to denied in {source_name})",
                )

            # Illicit commands evaluate to True (denied)
            for cmd in illicit_commands:
                is_denied = any(fnmatch.fnmatch(cmd, p) for p in shell_denied)
                self.assertTrue(
                    is_denied,
                    f"Illicit command '{cmd}' should be denied (evaluated to allowed in {source_name})",
                )

    def test_install_script_dry_run(self):
        self.assertTrue(self.install_sh.exists(), "install.sh must exist")
        res = subprocess.run(
            ["bash", str(self.install_sh), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            res.returncode, 0, f"install.sh --dry-run failed:\n{res.stderr}"
        )
        self.assertIn("antigravity.md", res.stdout)
        self.assertIn("steering/*.md", res.stdout)
        self.assertIn("hooks/*.json", res.stdout)
        self.assertIn("skills/writing", res.stdout)
        self.assertIn("skills/bigquery-googlesql", res.stdout)
        self.assertIn("skills/tool-skill-engineering", res.stdout)
        self.assertIn("skills/gcloud", res.stdout)
        self.assertIn("skills/conventional-commits", res.stdout)

    def test_install_script_json_format_dry_run(self):
        res = subprocess.run(
            ["bash", str(self.install_sh), "--format", "json", "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            res.returncode,
            0,
            f"install.sh --format json --dry-run failed:\n{res.stderr}",
        )
        self.assertIn("antigravity.json", res.stdout)
        self.assertIn("prompts/antigravity.prompt.md", res.stdout)
        self.assertIn("hooks/*.json", res.stdout)
        self.assertIn("skills/writing", res.stdout)
        self.assertIn("skills/bigquery-googlesql", res.stdout)
        self.assertIn("skills/tool-skill-engineering", res.stdout)
        self.assertIn("skills/gcloud", res.stdout)
        self.assertIn("skills/conventional-commits", res.stdout)

    def test_install_script_model_override(self):
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_path = Path(tmp_dir_str) / ".kiro"
            model_id = "claude-sonnet-5.5"
            res = subprocess.run(
                [
                    "bash",
                    str(self.install_sh),
                    "--target-dir",
                    str(tmp_path),
                    "--model",
                    model_id,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                res.returncode, 0, f"install.sh --model failed:\n{res.stderr}"
            )
            agent_md = tmp_path / "agents" / "antigravity.md"
            self.assertTrue(agent_md.exists(), "antigravity.md must exist")
            parts = agent_md.read_text(encoding="utf-8").split("---")
            fm = yaml.safe_load(parts[1])
            self.assertEqual(
                fm.get("model"),
                model_id,
                f"Model override '{model_id}' was not applied to antigravity.md",
            )

            # Test JSON format with model override
            tmp_path_json = Path(tmp_dir_str) / "json" / ".kiro"
            res_json = subprocess.run(
                [
                    "bash",
                    str(self.install_sh),
                    "--format",
                    "json",
                    "--target-dir",
                    str(tmp_path_json),
                    "--model",
                    model_id,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                res_json.returncode,
                0,
                f"install.sh --format json --model failed:\n{res_json.stderr}",
            )
            agent_json = tmp_path_json / "agents" / "antigravity.json"
            data = json.loads(agent_json.read_text(encoding="utf-8"))
            self.assertEqual(
                data.get("model"),
                model_id,
                f"Model override '{model_id}' was not applied to antigravity.json",
            )

    def test_install_script_skills_deployment(self):
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_path = Path(tmp_dir_str) / ".kiro"
            res = subprocess.run(
                ["bash", str(self.install_sh), "--target-dir", str(tmp_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"install.sh --target-dir failed:\n{res.stderr}",
            )
            self.assertTrue((tmp_path / "agents" / "antigravity.md").exists())
            self.assertTrue((tmp_path / "agents" / "antigravity-scout.md").exists())
            self.assertTrue(
                (tmp_path / "steering" / "01-engineering-discipline.md").exists()
            )
            self.assertTrue(
                (tmp_path / "hooks" / "workspace-status.json").exists(),
                "workspace-status.json must be deployed to hooks/",
            )

            expected_skills = [
                "writing",
                "bigquery-googlesql",
                "tool-skill-engineering",
                "gcloud",
                "conventional-commits",
            ]
            for skill in expected_skills:
                skill_dir = tmp_path / "skills" / skill
                self.assertTrue(
                    skill_dir.is_dir(), f"Skill directory {skill} must exist"
                )
                self.assertTrue(
                    (skill_dir / "SKILL.md").exists(),
                    f"SKILL.md must exist in deployed skill {skill}",
                )

            # Test directory protection: existing real directory is backed up, not wiped
            custom_dir = tmp_path / "skills" / "writing"
            custom_dir.unlink()  # remove symlink
            custom_dir.mkdir(parents=True)
            custom_file = custom_dir / "custom_notes.txt"
            custom_file.write_text("important user notes", encoding="utf-8")

            res_idempotent = subprocess.run(
                ["bash", str(self.install_sh), "--target-dir", str(tmp_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                res_idempotent.returncode,
                0,
                f"Idempotent re-run with existing directory failed:\n{res_idempotent.stderr}",
            )
            # Verify backup was created and user data was preserved
            backups = list((tmp_path / "skills").glob("writing.bak.*"))
            self.assertGreaterEqual(
                len(backups),
                1,
                "Existing real directory must be backed up before replacing",
            )
            self.assertTrue((backups[0] / "custom_notes.txt").exists())

    def test_install_script_no_skills_flag(self):
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_path = Path(tmp_dir_str) / ".kiro"
            res = subprocess.run(
                [
                    "bash",
                    str(self.install_sh),
                    "--target-dir",
                    str(tmp_path),
                    "--no-skills",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"install.sh --no-skills failed:\n{res.stderr}",
            )
            self.assertFalse(
                (tmp_path / "skills").exists(),
                "skills/ directory must not exist when --no-skills is specified",
            )

    def test_install_script_no_hooks_flag(self):
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_path = Path(tmp_dir_str) / ".kiro"
            res = subprocess.run(
                [
                    "bash",
                    str(self.install_sh),
                    "--target-dir",
                    str(tmp_path),
                    "--no-hooks",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"install.sh --no-hooks failed:\n{res.stderr}",
            )
            self.assertFalse(
                (tmp_path / "hooks").exists(),
                "hooks/ directory must not exist when --no-hooks is specified",
            )

    def test_install_script_json_format_deployment(self):
        with tempfile.TemporaryDirectory() as tmp_dir_str:
            tmp_path = Path(tmp_dir_str) / ".kiro"
            res = subprocess.run(
                [
                    "bash",
                    str(self.install_sh),
                    "--format",
                    "json",
                    "--target-dir",
                    str(tmp_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"install.sh --format json failed:\n{res.stderr}",
            )

            # JSON agent and external prompt must be present
            json_file = tmp_path / "agents" / "antigravity.json"
            prompt_file = tmp_path / "prompts" / "antigravity.prompt.md"
            self.assertTrue(json_file.exists(), "antigravity.json must exist")
            self.assertTrue(
                prompt_file.exists(), "antigravity.prompt.md must exist in prompts/"
            )
            self.assertFalse(
                (tmp_path / "agents" / "antigravity.md").exists(),
                "antigravity.md must not exist in agents/ when format is json",
            )

            # Validate installed JSON content
            data = json.loads(json_file.read_text(encoding="utf-8"))
            self.assertEqual(data.get("name"), "antigravity")
            self.assertEqual(
                data.get("prompt"),
                f"file://{prompt_file}",
                "Installed JSON prompt URI must point to prompts/antigravity.prompt.md",
            )

    def test_install_script_cli_validation(self):
        invalid_invocations = [
            (["--unknown-flag"], "Unknown argument"),
            (["--format", "unsupported_fmt"], "Invalid format"),
            (["--format"], "requires an argument"),
            (["--target-dir"], "requires a directory argument"),
            (["--model"], "requires a model identifier argument"),
        ]
        for args, expected_err in invalid_invocations:
            res = subprocess.run(
                ["bash", str(self.install_sh)] + args,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(
                res.returncode,
                0,
                f"install.sh {' '.join(args)} should fail with non-zero exit code",
            )
            self.assertIn(
                expected_err.lower(),
                res.stderr.lower(),
                f"Error stream for {' '.join(args)} should mention '{expected_err}'",
            )

        # --help and -h must exit 0
        for help_flag in ["--help", "-h"]:
            res = subprocess.run(
                ["bash", str(self.install_sh), help_flag],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                res.returncode, 0, f"install.sh {help_flag} must exit with code 0"
            )


if __name__ == "__main__":
    unittest.main()
