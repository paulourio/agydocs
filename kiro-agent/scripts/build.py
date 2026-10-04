#!/usr/bin/env python3
"""
build.py - Single-source-of-truth compiler for kiro-agent configurations.

Derives `antigravity.prompt.md` and `antigravity.json` deterministically from
`antigravity.md`. Supports --check mode to detect representation drift.
"""

import json
import sys
from pathlib import Path
import yaml

AGENT_DIR = Path(__file__).resolve().parent.parent
CANONICAL_MD = AGENT_DIR / "antigravity.md"
TARGET_PROMPT_MD = AGENT_DIR / "antigravity.prompt.md"
TARGET_JSON = AGENT_DIR / "antigravity.json"


def build(check_only: bool = False) -> int:
    if not CANONICAL_MD.exists():
        print(f"Error: Canonical source {CANONICAL_MD} not found", file=sys.stderr)
        return 1

    content = CANONICAL_MD.read_text(encoding="utf-8")
    parts = content.split("---")
    if len(parts) < 3:
        print(f"Error: {CANONICAL_MD} must contain YAML frontmatter", file=sys.stderr)
        return 1

    frontmatter = yaml.safe_load(parts[1])
    body = "---".join(parts[2:]).strip() + "\n"

    # Derive JSON configuration
    json_config = dict(frontmatter)
    json_config["prompt"] = "file://./antigravity.prompt.md"

    # Reorder keys cleanly
    key_order = [
        "name",
        "description",
        "tools",
        "excludedTools",
        "model",
        "effortLevel",
        "includeMcpJson",
        "includePowers",
        "mcpServers",
        "resources",
        "permissions",
        "prompt",
        "welcomeMessage",
        "dispatchKind",
        "hooks",
    ]
    ordered_config = {}
    for k in key_order:
        if k in json_config and json_config[k] is not None:
            ordered_config[k] = json_config[k]
    for k, v in json_config.items():
        if k not in ordered_config and v is not None:
            ordered_config[k] = v

    json_str = json.dumps(ordered_config, indent=2, ensure_ascii=False) + "\n"

    if check_only:
        drift = False
        if not TARGET_PROMPT_MD.exists() or TARGET_PROMPT_MD.read_text(encoding="utf-8") != body:
            print(f"Drift detected in {TARGET_PROMPT_MD}", file=sys.stderr)
            drift = True
        if not TARGET_JSON.exists() or TARGET_JSON.read_text(encoding="utf-8") != json_str:
            print(f"Drift detected in {TARGET_JSON}", file=sys.stderr)
            drift = True
        if drift:
            print("Run 'python3 scripts/build.py' or 'make build' to synchronize representations.", file=sys.stderr)
            return 1
        return 0

    TARGET_PROMPT_MD.write_text(body, encoding="utf-8")
    TARGET_JSON.write_text(json_str, encoding="utf-8")
    print(f"Built {TARGET_PROMPT_MD.name} and {TARGET_JSON.name} from {CANONICAL_MD.name}")
    return 0


if __name__ == "__main__":
    check_mode = "--check" in sys.argv
    sys.exit(build(check_only=check_mode))
