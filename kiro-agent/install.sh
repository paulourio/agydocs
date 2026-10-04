#!/usr/bin/env bash
# ==============================================================================
# kiro-agent/install.sh - Idempotent installer for Kiro Antigravity Custom Agent
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${PWD}" == "${SCRIPT_DIR}" ]]; then
    WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
else
    WORKSPACE_ROOT="${PWD}"
fi

INSTALL_GLOBAL=true
INSTALL_WORKSPACE=true
INSTALL_STEERING=true
INSTALL_SKILLS=true
INSTALL_HOOKS=true
TARGET_DIR=""
MODEL_OVERRIDE=""
FORMAT="md"
DRY_RUN=false

usage() {
    local exit_code="${1:-0}"
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Installs the Antigravity custom agent and steering rules into Kiro IDE directories.

Options:
  --global-only     Install only to user global scope (~/.kiro/)
  --workspace-only  Install only to workspace scope (.kiro/)
  --target-dir <d>  Install to custom directory scope
  --format <md|json> Agent format to install (default: md)
  --no-steering     Skip installing steering documents
  --no-skills       Skip installing skills
  --no-hooks        Skip installing lifecycle hooks
  --model <id>      Override model identifier
  --dry-run         Print planned actions without modifying filesystem
  -h, --help        Show this help message
EOF
    exit "${exit_code}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --global-only)
            INSTALL_GLOBAL=true
            INSTALL_WORKSPACE=false
            TARGET_DIR=""
            shift
            ;;
        --workspace-only)
            INSTALL_GLOBAL=false
            INSTALL_WORKSPACE=true
            TARGET_DIR=""
            shift
            ;;
        --target-dir)
            if [[ $# -lt 2 ]]; then
                echo "Error: --target-dir requires a directory argument" >&2
                usage 1
            fi
            TARGET_DIR="$2"
            INSTALL_GLOBAL=false
            INSTALL_WORKSPACE=false
            shift 2
            ;;
        --format)
            if [[ $# -lt 2 ]]; then
                echo "Error: --format requires an argument (md|json)" >&2
                usage 1
            fi
            FORMAT="$2"
            shift 2
            ;;
        --no-steering)
            INSTALL_STEERING=false
            shift
            ;;
        --no-skills)
            INSTALL_SKILLS=false
            shift
            ;;
        --no-hooks)
            INSTALL_HOOKS=false
            shift
            ;;
        --model)
            if [[ $# -lt 2 ]]; then
                echo "Error: --model requires a model identifier argument" >&2
                usage 1
            fi
            MODEL_OVERRIDE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage 0
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            usage 1
            ;;
    esac
done

if [[ "${FORMAT}" != "md" && "${FORMAT}" != "json" ]]; then
    echo "Error: Invalid format '${FORMAT}'. Supported formats: md, json" >&2
    exit 1
fi

echo "==> Validating kiro-agent configuration files..."
for req_file in "antigravity.md" "antigravity.json" "antigravity.prompt.md" "antigravity-scout.md"; do
    if [[ ! -f "${SCRIPT_DIR}/${req_file}" ]]; then
        echo "Error: ${SCRIPT_DIR}/${req_file} not found!" >&2
        exit 1
    fi
done

# Prepare agent file sources
TEMP_DIR=""
AGENT_MD_SOURCE="${SCRIPT_DIR}/antigravity.md"
AGENT_JSON_SOURCE="${SCRIPT_DIR}/antigravity.json"
AGENT_PROMPT_SOURCE="${SCRIPT_DIR}/antigravity.prompt.md"

if [[ -n "${MODEL_OVERRIDE}" ]]; then
    TEMP_DIR="$(mktemp -d)"
    trap 'rm -rf "${TEMP_DIR}"' EXIT
    echo "==> Applying model override: ${MODEL_OVERRIDE}"
    cp "${SCRIPT_DIR}/antigravity.prompt.md" "${TEMP_DIR}/antigravity.prompt.md"
    AGENT_PROMPT_SOURCE="${TEMP_DIR}/antigravity.prompt.md"

    python3 -c "
import yaml, sys
path_src = sys.argv[1]
path_dst = sys.argv[2]
model = sys.argv[3]
content = open(path_src, 'r', encoding='utf-8').read()
parts = content.split('---', 2)
if len(parts) >= 3:
    fm = yaml.safe_load(parts[1]) or {}
    fm['model'] = model
    new_fm = yaml.dump(fm, sort_keys=False).strip()
    new_content = f'---\n{new_fm}\n---' + parts[2]
    open(path_dst, 'w', encoding='utf-8').write(new_content)
" "${SCRIPT_DIR}/antigravity.md" "${TEMP_DIR}/antigravity.md" "${MODEL_OVERRIDE}"
    AGENT_MD_SOURCE="${TEMP_DIR}/antigravity.md"

    python3 -c "
import json, sys
path_src = sys.argv[1]
path_dst = sys.argv[2]
model = sys.argv[3]
data = json.load(open(path_src, 'r', encoding='utf-8'))
data['model'] = model
json.dump(data, open(path_dst, 'w', encoding='utf-8'), indent=2)
open(path_dst, 'a', encoding='utf-8').write('\n')
" "${SCRIPT_DIR}/antigravity.json" "${TEMP_DIR}/antigravity.json" "${MODEL_OVERRIDE}"
    AGENT_JSON_SOURCE="${TEMP_DIR}/antigravity.json"
fi

install_to() {
    local target_base="$1"
    local agent_dir="${target_base}/agents"
    local steering_dir="${target_base}/steering"
    local prompts_dir="${target_base}/prompts"
    local skills_dir="${target_base}/skills"
    local hooks_dir="${target_base}/hooks"

    echo "==> Installing to: ${target_base} (format: ${FORMAT})"
    if [[ "${DRY_RUN}" = true ]]; then
        echo "  [DRY-RUN] mkdir -p ${agent_dir}"
        if [[ "${FORMAT}" == "md" ]]; then
            echo "  [DRY-RUN] cp ${AGENT_MD_SOURCE} ${agent_dir}/antigravity.md"
            echo "  [DRY-RUN] rm -f ${agent_dir}/antigravity.json ${agent_dir}/antigravity.prompt.md"
        else
            echo "  [DRY-RUN] mkdir -p ${prompts_dir}"
            echo "  [DRY-RUN] cp ${AGENT_PROMPT_SOURCE} ${prompts_dir}/antigravity.prompt.md"
            echo "  [DRY-RUN] cp ${AGENT_JSON_SOURCE} ${agent_dir}/antigravity.json (pointing to ${prompts_dir}/antigravity.prompt.md)"
            echo "  [DRY-RUN] rm -f ${agent_dir}/antigravity.md ${agent_dir}/antigravity.prompt.md"
        fi
        if [[ -f "${SCRIPT_DIR}/antigravity-scout.md" ]]; then
            echo "  [DRY-RUN] cp ${SCRIPT_DIR}/antigravity-scout.md ${agent_dir}/antigravity-scout.md"
        fi
        if [[ "${INSTALL_STEERING}" = true && -d "${SCRIPT_DIR}/steering" ]]; then
            echo "  [DRY-RUN] mkdir -p ${steering_dir}"
            echo "  [DRY-RUN] cp ${SCRIPT_DIR}/steering/*.md ${steering_dir}/"
        fi
        if [[ "${INSTALL_HOOKS}" = true && -d "${SCRIPT_DIR}/hooks" ]]; then
            echo "  [DRY-RUN] mkdir -p ${hooks_dir}"
            echo "  [DRY-RUN] cp ${SCRIPT_DIR}/hooks/*.json ${hooks_dir}/"
        fi
        if [[ "${INSTALL_SKILLS}" = true ]]; then
            local skill_names=("writing" "bigquery-googlesql" "tool-skill-engineering" "gcloud" "conventional-commits")
            local found_skills=()
            for s in "${skill_names[@]}"; do
                if [[ -f "${WORKSPACE_ROOT}/${s}/SKILL.md" ]]; then
                    found_skills+=("${s}")
                elif [[ -f "${HOME}/.gemini/config/skills/${s}/SKILL.md" ]]; then
                    found_skills+=("${s}")
                fi
            done
            if [[ ${#found_skills[@]} -gt 0 ]]; then
                echo "  [DRY-RUN] mkdir -p ${skills_dir}"
                for s in "${found_skills[@]}"; do
                    local src="${WORKSPACE_ROOT}/${s}"
                    if [[ ! -f "${src}/SKILL.md" && -f "${HOME}/.gemini/config/skills/${s}/SKILL.md" ]]; then
                        src="${HOME}/.gemini/config/skills/${s}"
                    fi
                    echo "  [DRY-RUN] ln -sfn ${src} ${skills_dir}/${s}"
                done
            fi
        fi
        return 0
    fi

    mkdir -p "${agent_dir}"

    if [[ "${FORMAT}" == "md" ]]; then
        cp "${AGENT_MD_SOURCE}" "${agent_dir}/antigravity.md"
        echo "  Installed: ${agent_dir}/antigravity.md"
        # Remove colliding or stray agent files in agents/
        rm -f "${agent_dir}/antigravity.json" "${agent_dir}/antigravity.prompt.md"
    else
        mkdir -p "${prompts_dir}"
        cp "${AGENT_PROMPT_SOURCE}" "${prompts_dir}/antigravity.prompt.md"
        python3 -c "
import json, sys
src_json = sys.argv[1]
dst_json = sys.argv[2]
prompt_uri = sys.argv[3]
data = json.load(open(src_json, 'r', encoding='utf-8'))
data['prompt'] = prompt_uri
json.dump(data, open(dst_json, 'w', encoding='utf-8'), indent=2)
open(dst_json, 'a', encoding='utf-8').write('\n')
" "${AGENT_JSON_SOURCE}" "${agent_dir}/antigravity.json" "file://${prompts_dir}/antigravity.prompt.md"
        echo "  Installed: ${agent_dir}/antigravity.json"
        echo "  Installed: ${prompts_dir}/antigravity.prompt.md"
        # Remove colliding or stray agent files in agents/
        rm -f "${agent_dir}/antigravity.md" "${agent_dir}/antigravity.prompt.md"
    fi

    # Deploy specialized subagent definitions
    if [[ -f "${SCRIPT_DIR}/antigravity-scout.md" ]]; then
        cp "${SCRIPT_DIR}/antigravity-scout.md" "${agent_dir}/antigravity-scout.md"
        echo "  Installed: ${agent_dir}/antigravity-scout.md"
    fi

    if [[ "${INSTALL_STEERING}" = true && -d "${SCRIPT_DIR}/steering" ]]; then
        mkdir -p "${steering_dir}"
        cp "${SCRIPT_DIR}/steering/"*.md "${steering_dir}/"
        echo "  Installed steering files to: ${steering_dir}/"
    fi

    if [[ "${INSTALL_HOOKS}" = true && -d "${SCRIPT_DIR}/hooks" ]]; then
        mkdir -p "${hooks_dir}"
        cp "${SCRIPT_DIR}/hooks/"*.json "${hooks_dir}/"
        echo "  Installed hooks to: ${hooks_dir}/"
    fi

    if [[ "${INSTALL_SKILLS}" = true ]]; then
        local skill_names=("writing" "bigquery-googlesql" "tool-skill-engineering" "gcloud" "conventional-commits")
        local found_skills=()
        for s in "${skill_names[@]}"; do
            if [[ -f "${WORKSPACE_ROOT}/${s}/SKILL.md" ]]; then
                found_skills+=("${s}")
            elif [[ -f "${HOME}/.gemini/config/skills/${s}/SKILL.md" ]]; then
                found_skills+=("${s}")
            fi
        done
        if [[ ${#found_skills[@]} -gt 0 ]]; then
            mkdir -p "${skills_dir}"
            for s in "${found_skills[@]}"; do
                local skill_src="${WORKSPACE_ROOT}/${s}"
                if [[ ! -f "${skill_src}/SKILL.md" && -f "${HOME}/.gemini/config/skills/${s}/SKILL.md" ]]; then
                    skill_src="${HOME}/.gemini/config/skills/${s}"
                fi
                local skill_dst="${skills_dir}/${s}"
                if [[ -L "${skill_dst}" ]]; then
                    rm -f "${skill_dst}"
                elif [[ -d "${skill_dst}" ]]; then
                    local backup="${skill_dst}.bak.$(date +%s)"
                    echo "  Warning: Backing up existing directory ${skill_dst} to ${backup}"
                    mv "${skill_dst}" "${backup}"
                elif [[ -e "${skill_dst}" ]]; then
                    rm -f "${skill_dst}"
                fi
                if ln -s "${skill_src}" "${skill_dst}" 2>/dev/null; then
                    echo "  Linked skill: ${skill_dst} -> ${skill_src}"
                else
                    cp -R "${skill_src}" "${skill_dst}"
                    echo "  Copied skill: ${skill_dst} -> ${skill_src}"
                fi
            done
        fi
    fi
}

if [[ -n "${TARGET_DIR}" ]]; then
    install_to "${TARGET_DIR}"
else
    if [[ "${INSTALL_GLOBAL}" = true ]]; then
        install_to "${HOME}/.kiro"
    fi

    if [[ "${INSTALL_WORKSPACE}" = true ]]; then
        install_to "${WORKSPACE_ROOT}/.kiro"
    fi
fi

echo "==> kiro-agent installation complete!"
echo "    In Kiro IDE AI Chat header, click the agent selector dropdown and choose 'antigravity'."
