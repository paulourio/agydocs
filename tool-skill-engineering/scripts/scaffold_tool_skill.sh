#!/usr/bin/env bash
# Scaffold a new production tool skill adhering to the 7-stage engineering lifecycle.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <tool-name> [target-directory]"
  echo "Example: $0 snowflake ./snowflake-sql"
  exit 1
fi

TOOL_NAME="$1"
TARGET_DIR="${2:-./$TOOL_NAME}"
TOOL_DISPLAY_NAME="$(echo "$TOOL_NAME" | sed -r 's/(^|-)([a-z])/\U\2/g')"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
TEMPLATE_DIR="$SKILL_ROOT/resources/skill_template"

echo "==> Scaffolding tool skill '$TOOL_NAME' in '$TARGET_DIR'..."

mkdir -p "$TARGET_DIR/docs"
mkdir -p "$TARGET_DIR/references"
mkdir -p "$TARGET_DIR/resources"
mkdir -p "$TARGET_DIR/examples"
mkdir -p "$TARGET_DIR/scripts"

# Render SKILL.md
sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/SKILL.md.tmpl" > "$TARGET_DIR/SKILL.md"

# Render README.md
sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/README.md.tmpl" > "$TARGET_DIR/README.md"

# Render verify.sh
sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/scripts/verify.sh.tmpl" > "$TARGET_DIR/scripts/verify.sh"
chmod +x "$TARGET_DIR/scripts/verify.sh"

# Render docs mirror and topic catalog
sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/docs/README.md.tmpl" > "$TARGET_DIR/docs/README.md"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/docs/INDEX.md.tmpl" > "$TARGET_DIR/docs/INDEX.md"

# Render examples SDK parity templates
sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/examples/README.md.tmpl" > "$TARGET_DIR/examples/README.md"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/examples/dot_formatter.toml.tmpl" > "$TARGET_DIR/examples/dot_formatter.toml"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/examples/go.mod.tmpl" > "$TARGET_DIR/examples/go.mod"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/examples/client.go.tmpl" > "$TARGET_DIR/examples/client.go"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/examples/client_test.go.tmpl" > "$TARGET_DIR/examples/client_test.go"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/examples/client.py.tmpl" > "$TARGET_DIR/examples/client.py"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/examples/test_client.py.tmpl" > "$TARGET_DIR/examples/test_client.py"

# Copy eval runner tooling to resources
if [[ -f "$SKILL_ROOT/resources/eval_runner.py" ]]; then
  cp "$SKILL_ROOT/resources/eval_runner.py" "$TARGET_DIR/resources/eval_runner.py"
  cp "$SKILL_ROOT/resources/test_eval_runner.py" "$TARGET_DIR/resources/test_eval_runner.py"
fi

# Render rich reference specifications
sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/references/syntax_and_operators.md.tmpl" > "$TARGET_DIR/references/syntax_and_operators.md"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/references/engine_architecture.md.tmpl" > "$TARGET_DIR/references/engine_architecture.md"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/references/optimization_guide.md.tmpl" > "$TARGET_DIR/references/optimization_guide.md"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/references/style_and_formatting.md.tmpl" > "$TARGET_DIR/references/style_and_formatting.md"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/references/client_sdks.md.tmpl" > "$TARGET_DIR/references/client_sdks.md"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/resources/cheat_sheet.md.tmpl" > "$TARGET_DIR/resources/cheat_sheet.md"

sed -e "s/{{TOOL_NAME}}/$TOOL_NAME/g" \
    -e "s/{{TOOL_DISPLAY_NAME}}/$TOOL_DISPLAY_NAME/g" \
    "$TEMPLATE_DIR/resources/anti_patterns_catalog.md.tmpl" > "$TARGET_DIR/resources/anti_patterns_catalog.md"

echo "✅ Skill scaffolded successfully at: $TARGET_DIR"
echo "Next steps:"
echo "  1. Ingest upstream docs into $TARGET_DIR/docs/ and update $TARGET_DIR/docs/INDEX.md."
echo "  2. Populate synthesized RFCs in $TARGET_DIR/references/."
echo "  3. Deploy formatter configuration and executable patterns in $TARGET_DIR/examples/."
echo "  4. Execute $TARGET_DIR/scripts/verify.sh and audit with quality_gate."
