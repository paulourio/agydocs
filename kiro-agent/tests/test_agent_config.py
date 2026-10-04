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
        self.workflows_dir = MODULE_DIR / "workflows"
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
        expected_tools = [
            "read",
            "write",
            "shell",
            "web",
            "subagent",
            "run_workflow",
            "inspect_workflow",
            "update_workflow",
            "validate_workflow",
            "send_message",
        ]
        for required_tool in expected_tools:
            self.assertIn(
                required_tool,
                tools,
                f"Tool category or identifier '{required_tool}' must be in tools",
            )

        # Ensure CLI-only dead fields are absent to prevent schema debt
        self.assertNotIn(
            "allowedTools",
            frontmatter,
            "allowedTools is a CLI-only field dropped by Kiro IDE parser and must be omitted",
        )
        self.assertNotIn(
            "toolsSettings",
            frontmatter,
            "toolsSettings is a CLI-only field and must be omitted",
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
        self.assertIn("*git*commit* -n *", shell_denied)
        self.assertIn("*git*commit* -n", shell_denied)
        self.assertIn("*git*commit* -nm *", shell_denied)
        self.assertIn("*core.hooksPath*", shell_denied)
        self.assertIn("*rm -rf /*", shell_denied)
        self.assertIn("sudo *", shell_denied)

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

        # Ensure resources does not duplicate auto-discovered steering or skills
        resources = frontmatter.get("resources", [])
        self.assertNotIn(
            "file://.kiro/steering/**/*.md",
            resources,
            "Steering is auto-discovered; do not duplicate in resources",
        )
        self.assertNotIn(
            "skill://.kiro/skills/**/SKILL.md",
            resources,
            "Skills are auto-discovered; do not duplicate in resources",
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
        for t in [
            "read",
            "write",
            "shell",
            "web",
            "subagent",
            "run_workflow",
            "inspect_workflow",
            "update_workflow",
            "validate_workflow",
            "send_message",
        ]:
            self.assertIn(t, content.get("tools", []))

        self.assertNotIn(
            "allowedTools",
            content,
            "allowedTools must not be in JSON config",
        )

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
        self.assertIn("*git*commit* -n *", shell_denied)
        self.assertIn("*git*commit* -n", shell_denied)
        self.assertIn("*git*commit* -nm *", shell_denied)
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
        self.assertEqual(
            frontmatter.get("effortLevel"),
            "low",
            "Scout must use effortLevel low for token economy",
        )

        # Scout must be read-only: no write or goal tools, but has send_message for workflow completion
        tools = frontmatter.get("tools", [])
        self.assertIn("read", tools)
        self.assertIn("shell", tools)
        self.assertIn(
            "send_message",
            tools,
            "Scout must have send_message for workflow step completion",
        )
        self.assertNotIn("write", tools, "Scout must not have write tools")
        self.assertNotIn("goal", tools, "Scout must not have goal tool")

        self.assertNotIn(
            "allowedTools",
            frontmatter,
            "allowedTools must not be in scout frontmatter",
        )

        # Scout must deny fs_write
        rules = frontmatter.get("permissions", {}).get("rules", [])
        fs_write_denied = any(
            r.get("capability") == "fs_write" and r.get("effect") == "deny"
            for r in rules
        )
        self.assertTrue(fs_write_denied, "Scout must deny fs_write capability")

        # Scout shell rules must deny dangerous find arguments
        shell_rules = [r for r in rules if r.get("capability") == "shell"]
        shell_denied = [
            m for r in shell_rules if r.get("effect") == "deny" for m in r.get("match", [])
        ]
        self.assertIn("* -delete*", shell_denied)
        self.assertIn("* -exec*", shell_denied)

        # Scout body must document workflow step completion protocol
        body = parts[2]
        self.assertIn("Workflow Step Completion", body)
        self.assertIn("send_message", body)

    def test_single_source_of_truth_sync(self):
        """Assert antigravity.json and antigravity.prompt.md have zero drift from antigravity.md."""
        res = subprocess.run(
            ["python3", str(MODULE_DIR / "scripts" / "build.py"), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            res.returncode,
            0,
            f"Build check detected drift between antigravity.md, antigravity.prompt.md, and antigravity.json:\n{res.stderr}",
        )

    def test_git_commit_fnmatch_permission_rules(self):
        """Assert legitimate commit commands are allowed and illicit commands are denied."""
        md_content = self.md_file.read_text(encoding="utf-8")
        frontmatter = yaml.safe_load(md_content.split("---")[1])
        json_content = json.loads(self.json_file.read_text(encoding="utf-8"))

        configs = [("antigravity.md", frontmatter), ("antigravity.json", json_content)]

        legitimate_commands = [
            "git grep -n TODO",
            "git log -n 5",
            "git tag -n",
            "git diff -n",
            "git show -n",
            "git status --short",
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
            "rm -rf build",
            "rm -rf dist",
            "rm -rf node_modules",
        ]

        illicit_commands = [
            'git commit -n -m "bypass"',
            'git commit -nm "bypass"',
            'git commit -mn "bypass"',
            'git commit -anm "bypass"',
            'git commit -nam "bypass"',
            'git commit -qn -m "bypass"',
            'git commit -nqm "bypass"',
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
            'HUSKY=0 git commit -m "bypass"',
            'LEFTHOOK=0 git commit -m "bypass"',
            "sudo rm -rf /",
            "rm -rf /",
            "rm -rf /*",
            "rm -fr /",
            "rm -fr /*",
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

    def _validate_workflow_dict(self, wf: dict) -> list[str]:
        """Validates a workflow dictionary according to Kiro 1.2 runtime rules."""
        errors = []
        if not isinstance(wf.get("name"), str) or not wf.get("name"):
            errors.append("Workflow must have a non-empty string 'name'")
        steps = wf.get("steps")
        if not isinstance(steps, list) or len(steps) == 0:
            errors.append("Workflow must have a non-empty 'steps' list")
            return errors

        declared_inputs = (
            set(wf.get("inputs", {}).keys())
            if isinstance(wf.get("inputs"), dict)
            else set()
        )
        seen_ids = set()
        total_steps = 0

        def traverse(node, depth, earlier_step_ids):
            nonlocal total_steps
            if depth > 8:
                errors.append(
                    f"Exceeded max nesting depth of 8 at node {node.get('id')}"
                )
            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                errors.append(
                    f"Node at depth {depth} must have a non-empty string 'id'"
                )
            elif node_id in seen_ids:
                errors.append(f"Duplicate node id '{node_id}'")
            else:
                seen_ids.add(node_id)

            node_type = node.get("type")
            valid_types = ("step", "repeat", "sequence", "parallel", "watch")
            if node_type not in valid_types:
                errors.append(f"Node '{node_id}' has invalid type '{node_type}'")

            if node_type == "step":
                total_steps += 1
                prompt = node.get("prompt")
                if not isinstance(prompt, str) or not prompt.strip():
                    errors.append(f"Step '{node_id}' must have a non-empty 'prompt'")
                else:
                    import re

                    var_refs = re.findall(r"\{\{([a-zA-Z0-9_\-\.]+)\}\}", prompt)
                    for ref in var_refs:
                        base = ref.split(".")[0]
                        if (
                            base not in declared_inputs
                            and base not in earlier_step_ids
                            and base != "previous"
                        ):
                            errors.append(
                                f"Step '{node_id}' references undeclared variable or future step '{{{{{ref}}}}}'"
                            )
                earlier_step_ids.add(node_id)

            elif node_type == "repeat":
                max_iter = node.get("maxIterations")
                if not isinstance(max_iter, int) or max_iter < 1 or max_iter > 1000:
                    errors.append(
                        f"Repeat '{node_id}' maxIterations must be int between 1 and 1000"
                    )
                if node.get("onMaxIterations") not in ("pause", "continue", "abort"):
                    errors.append(
                        f"Repeat '{node_id}' onMaxIterations must be pause, continue, or abort"
                    )
                has_cond = "stopCondition" in node
                has_when = "stopWhen" in node
                if has_cond and has_when:
                    errors.append(
                        f"Repeat '{node_id}' cannot define both stopCondition and stopWhen"
                    )
                child_steps = node.get("steps", [])
                if not isinstance(child_steps, list) or len(child_steps) == 0:
                    errors.append(f"Repeat '{node_id}' must have non-empty child steps")
                for child in child_steps:
                    traverse(child, depth + 1, earlier_step_ids)

            elif node_type == "parallel":
                if node.get("joinPolicy") not in ("all", "allSettled", "any"):
                    errors.append(
                        f"Parallel '{node_id}' joinPolicy must be all, allSettled, or any"
                    )
                branches = node.get("branches", [])
                if not isinstance(branches, list) or len(branches) == 0:
                    errors.append(f"Parallel '{node_id}' must have non-empty branches")
                for b in branches:
                    traverse(b, depth + 1, earlier_step_ids)

            elif node_type == "sequence":
                child_steps = node.get("steps", [])
                if not isinstance(child_steps, list) or len(child_steps) == 0:
                    errors.append(
                        f"Sequence '{node_id}' must have non-empty child steps"
                    )
                for child in child_steps:
                    traverse(child, depth + 1, earlier_step_ids)

        earlier_ids = set()
        for s in steps:
            traverse(s, 1, earlier_ids)

        if total_steps > 50:
            errors.append(f"Workflow exceeds 50 step limit (found {total_steps})")

        return errors

    def test_workflow_recipes_valid(self):
        self.assertTrue(self.workflows_dir.is_dir(), "workflows/ directory must exist")
        recipes = list(self.workflows_dir.glob("*.workflow.json"))
        self.assertGreaterEqual(
            len(recipes), 2, "Must provide at least 2 workflow recipes"
        )

        for recipe in recipes:
            data = json.loads(recipe.read_text(encoding="utf-8"))
            errors = self._validate_workflow_dict(data)
            self.assertEqual(
                errors,
                [],
                f"Workflow recipe '{recipe.name}' failed validation:\n"
                + "\n".join(errors),
            )

        # Negative control 1: Duplicate node IDs must fail
        dup_workflow = {
            "name": "invalid-dup",
            "steps": [
                {
                    "type": "step",
                    "id": "step1",
                    "agent": "wf-coder",
                    "prompt": "Test 1",
                },
                {
                    "type": "step",
                    "id": "step1",
                    "agent": "wf-coder",
                    "prompt": "Test 2",
                },
            ],
        }
        self.assertTrue(
            any(
                "duplicate" in e.lower()
                for e in self._validate_workflow_dict(dup_workflow)
            )
        )

        # Negative control 2: Repeat with both stopCondition and stopWhen must fail
        both_stop_workflow = {
            "name": "invalid-stop",
            "steps": [
                {
                    "type": "repeat",
                    "id": "loop1",
                    "maxIterations": 5,
                    "onMaxIterations": "pause",
                    "stopCondition": {"containsText": "done"},
                    "stopWhen": "step1.terminal",
                    "steps": [
                        {
                            "type": "step",
                            "id": "sub1",
                            "agent": "wf-coder",
                            "prompt": "Loop",
                        },
                    ],
                }
            ],
        }
        self.assertTrue(
            any(
                "both" in e.lower()
                for e in self._validate_workflow_dict(both_stop_workflow)
            )
        )

        # Negative control 3: Missing prompt in step must fail
        no_prompt_workflow = {
            "name": "invalid-prompt",
            "steps": [
                {"type": "step", "id": "step1", "agent": "wf-coder", "prompt": ""}
            ],
        }
        self.assertTrue(
            any(
                "prompt" in e.lower()
                for e in self._validate_workflow_dict(no_prompt_workflow)
            )
        )

    def test_install_script_workflows_deployment(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            res = subprocess.run(
                [
                    "bash",
                    str(self.install_sh),
                    "--target-dir",
                    str(tmp_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"install.sh failed:\n{res.stderr}")
            wf_dir = tmp_path / "workflows"
            self.assertTrue(
                wf_dir.is_dir(), "workflows/ directory must exist in target"
            )
            self.assertTrue(
                (wf_dir / "zero-debt-gate.workflow.json").exists(),
                "zero-debt-gate.workflow.json must be deployed",
            )
            self.assertTrue(
                (wf_dir / "peer-review.workflow.json").exists(),
                "peer-review.workflow.json must be deployed",
            )

    def test_install_script_no_workflows_flag(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            res = subprocess.run(
                [
                    "bash",
                    str(self.install_sh),
                    "--target-dir",
                    str(tmp_path),
                    "--no-workflows",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res.returncode, 0, f"install.sh failed:\n{res.stderr}")
            wf_dir = tmp_path / "workflows"
            self.assertFalse(
                wf_dir.exists(),
                "workflows/ directory must not exist when --no-workflows is passed",
            )


if __name__ == "__main__":
    unittest.main()
