#!/usr/bin/env python3
"""
Google Cloud CLI (gcloud) Documentation Fetcher and Link Rewriter

Extracts official gcloud reference documentation from the local Google Cloud CLI
installation (via 'gcloud meta generate-help-docs') or upstream documentation endpoints,
transforms raw help specifications into structured Markdown, rewrites inter-document
cross-references into local relative file links with code fence shielding, and generates
a comprehensive documentation index.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DOCS_HOST = "https://cloud.google.com"

# Core command groups and topics partitioned by functional cloud domain
DEFAULT_CATALOG: dict[str, list[str]] = {
    "topic": [
        "filters",
        "formats",
        "projections",
        "configurations",
        "flags-file",
        "escaping",
        "datetimes",
        "resource-keys",
        "command-conventions",
        "client-certificate",
        "cli-trees",
        "gcloudignore",
        "offline-help",
        "startup",
        "accessibility",
    ],
    "config": [
        "set",
        "get-value",
        "list",
        "unset",
        "configurations",
    ],
    "auth": [
        "login",
        "activate-service-account",
        "print-access-token",
        "print-identity-token",
        "application-default",
        "list",
        "revoke",
    ],
    "projects": [
        "create",
        "describe",
        "list",
        "delete",
        "add-iam-policy-binding",
        "get-iam-policy",
        "set-iam-policy",
        "remove-iam-policy-binding",
    ],
    "iam": [
        "service-accounts",
        "roles",
        "policies",
        "service-account-keys",
    ],
    "compute": [
        "instances",
        "disks",
        "snapshots",
        "networks",
        "firewall-rules",
        "routers",
        "instance-templates",
        "instance-groups",
        "operations",
    ],
    "container": [
        "clusters",
        "node-pools",
        "operations",
    ],
    "run": [
        "deploy",
        "services",
        "jobs",
    ],
    "functions": [
        "deploy",
        "describe",
        "list",
        "delete",
        "call",
        "logs",
    ],
    "storage": [
        "buckets",
        "objects",
        "cp",
        "mv",
        "rm",
        "rsync",
        "cat",
    ],
    "pubsub": [
        "topics",
        "subscriptions",
        "snapshots",
    ],
    "secrets": [
        "create",
        "describe",
        "list",
        "delete",
        "versions",
    ],
    "logging": [
        "read",
        "write",
        "sinks",
        "metrics",
    ],
    "sql": [
        "instances",
        "databases",
        "users",
        "backups",
    ],
    "services": [
        "enable",
        "disable",
        "list",
    ],
}


def normalize_doc_path(path_or_url: str) -> str:
    """
    Normalizes a gcloud doc path or URL to a canonical slash-delimited path.
    Example:
      'https://cloud.google.com/sdk/gcloud/reference/compute/instances/create' -> 'compute/instances/create'
      'gcloud.compute.instances' -> 'compute/instances'
    """
    parsed = urllib.parse.urlparse(path_or_url)
    p = parsed.path if parsed.path else path_or_url
    p = p.rstrip("/")
    # Strip URL prefixes
    prefixes = [
        "/sdk/gcloud/reference/",
        "sdk/gcloud/reference/",
        "/docs/reference/",
        "docs/reference/",
    ]
    for pref in prefixes:
        if p.startswith(pref):
            p = p[len(pref) :]
            break

    # Strip leading 'gcloud.' if provided in dotted syntax
    if p.startswith("gcloud."):
        p = p[len("gcloud.") :].replace(".", "/")

    # Remove file extension if present
    if p.endswith(".md.txt"):
        p = p[:-7]
    elif p.endswith((".md", ".html")):
        p = p.rsplit(".", 1)[0]

    return p.strip("/")


def categorize_path(path: str) -> str:
    """Categorizes a canonical path into one of the domain folders."""
    parts = path.split("/")
    first = parts[0]
    if first in DEFAULT_CATALOG:
        return first
    return "general"


def mask_code_blocks(text: str) -> tuple[str, list[str]]:
    """
    Replaces fenced code blocks (``` ... ``` or ~~~ ... ~~~) and inline code
    with deterministic placeholders to protect code tokens from regex rewriting.
    """
    blocks: list[str] = []

    def replace_fenced(match: re.Match) -> str:
        idx = len(blocks)
        blocks.append(match.group(0))
        return f"___CODE_BLOCK_{idx:05d}___"

    # Match fenced code blocks (at least 3 backticks or tildes)
    fenced_pattern = re.compile(
        r"(```[^\n]*\n[\s\S]*?\n```|~~~[^\n]*\n[\s\S]*?\n~~~)", re.MULTILINE
    )
    masked = fenced_pattern.sub(replace_fenced, text)

    # Match inline code backticks
    def replace_inline(match: re.Match) -> str:
        idx = len(blocks)
        blocks.append(match.group(0))
        return f"___CODE_BLOCK_{idx:05d}___"

    inline_pattern = re.compile(r"(`[^`\n]+`)")
    masked = inline_pattern.sub(replace_inline, masked)

    return masked, blocks


def unmask_code_blocks(text: str, blocks: list[str]) -> str:
    """Restores masked code blocks in reverse placeholder order."""
    unmasked = text
    for idx, block in enumerate(blocks):
        placeholder = f"___CODE_BLOCK_{idx:05d}___"
        unmasked = unmasked.replace(placeholder, block)
    return unmasked


def convert_raw_help_to_markdown(raw_text: str, command_title: str) -> str:
    """
    Converts raw man/help text emitted by 'gcloud meta generate-help-docs'
    into clean, formatted Markdown.
    """
    lines = raw_text.splitlines()
    md_lines: list[str] = []

    md_lines.append(f"# {command_title}")
    md_lines.append("")

    in_synopsis = False
    synopsis_buffer: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Top-level section header: column 0, ALL CAPS, e.g. NAME, SYNOPSIS, DESCRIPTION, FLAGS
        if re.match(r"^[A-Z][A-Z0-9 _\-]{1,30}$", line):
            section_name = line.strip()

            if in_synopsis:
                # Flush synopsis block
                md_lines.append("```bash")
                md_lines.extend(synopsis_buffer)
                md_lines.append("```")
                md_lines.append("")
                in_synopsis = False
                synopsis_buffer = []

            md_lines.append(f"## {section_name}")
            md_lines.append("")
            if section_name == "SYNOPSIS":
                in_synopsis = True
            i += 1
            continue

        if in_synopsis:
            synopsis_buffer.append(line)
            i += 1
            continue

        # Subsections indented by 2 or 4 spaces with Title Case, e.g. "  Filter Expressions"
        sub_match = re.match(r"^(?: {2,4})([A-Z][a-zA-Z0-9 \-_]+)$", line)
        if sub_match and not line.strip().startswith("--"):
            sub_title = sub_match.group(1).strip()
            md_lines.append("")
            md_lines.append(f"### {sub_title}")
            md_lines.append("")
            i += 1
            continue

        # Standard prose or bullet lines
        md_lines.append(line)
        i += 1

    if in_synopsis and synopsis_buffer:
        md_lines.append("```bash")
        md_lines.extend(synopsis_buffer)
        md_lines.append("```")
        md_lines.append("")

    content = "\n".join(md_lines)
    # Deduplicate excessive empty lines
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content


def rewrite_links(
    content: str, current_file: Path, doc_mapping: dict[str, Path]
) -> str:
    """
    Rewrites cross-document references to relative markdown file paths.
    Protects fenced code blocks and inline code blocks from modification.
    """
    masked, blocks = mask_code_blocks(content)

    # 1. Rewrite explicit Markdown links: [anchor](https://cloud.google.com/sdk/gcloud/reference/...)
    def replace_md_link(match: re.Match) -> str:
        anchor = match.group(1)
        target = match.group(2)
        parsed = urllib.parse.urlparse(target)
        norm = normalize_doc_path(parsed.path)

        if norm in doc_mapping:
            target_path = doc_mapping[norm]
            rel_path = os.path.relpath(target_path, current_file.parent)
            hash_suffix = f"#{parsed.fragment}" if parsed.fragment else ""
            return f"[{anchor}]({rel_path}{hash_suffix})"
        return match.group(0)

    md_link_regex = re.compile(
        r"\[([^\]]+)\]\((https?://cloud\.google\.com/sdk/gcloud/reference/[^\)]+)\)"
    )
    masked = md_link_regex.sub(replace_md_link, masked)

    # 2. Rewrite command references in prose, e.g., '$ gcloud topic formats' or 'gcloud topic filters'
    def replace_topic_ref(match: re.Match) -> str:
        topic_name = match.group(1)
        key = f"topic/{topic_name}"
        if key in doc_mapping:
            rel_path = os.path.relpath(doc_mapping[key], current_file.parent)
            return f"[`gcloud topic {topic_name}`]({rel_path})"
        return match.group(0)

    topic_regex = re.compile(r"(?:\$ )?gcloud topic ([a-z\-]+)")
    masked = topic_regex.sub(replace_topic_ref, masked)

    return unmask_code_blocks(masked, blocks)


def generate_index_markdown(docs_dir: Path, doc_mapping: dict[str, Path]) -> str:
    """Generates INDEX.md listing all ingested documentation grouped by domain."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = [
        "# Google Cloud CLI Documentation Catalog",
        "",
        f"Generated: {now} | Total Documents: {len(doc_mapping)}",
        "",
        "This directory contains local offline mirrors of Google Cloud CLI command specifications.",
        "Cross-references use relative local links to eliminate runtime network latency.",
        "",
        "## Domain Navigation Matrix",
        "",
    ]

    domains = sorted({categorize_path(k) for k in doc_mapping})

    for domain in domains:
        lines.append(f"### {domain.upper()}")
        lines.append("")
        items = sorted([k for k in doc_mapping if categorize_path(k) == domain])
        for item in items:
            path = doc_mapping[item]
            rel_path = os.path.relpath(path, docs_dir)
            title = item.replace("/", " ")
            lines.append(f"- [`gcloud {title}`]({rel_path})")
        lines.append("")

    return "\n".join(lines)


def extract_local_help_docs(output_docs_dir: Path) -> dict[str, Path]:
    """
    Invokes 'gcloud meta generate-help-docs' into a temporary directory,
    processes text documents into Markdown, categorizes them into docs/,
    and returns a mapping of canonical paths to file locations.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Build list of gcloud target groups
        groups: list[str] = []
        for domain, subcmds in DEFAULT_CATALOG.items():
            if domain == "topic":
                groups.append("gcloud.topic")
            else:
                for sub in subcmds:
                    groups.append(f"gcloud.{domain}.{sub}")

        cmd = [
            "gcloud",
            "meta",
            "generate-help-docs",
            *groups,
            f"--help-text-dir={tmp_path}",
        ]

        print(
            f"==> Extracting help documents from local Google Cloud CLI ({len(groups)} targets)..."
        )
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            print(
                f"Warning: gcloud meta generate-help-docs exited with {res.returncode}: {res.stderr}"
            )

        doc_mapping: dict[str, Path] = {}
        processed_files: list[tuple[Path, Path, str]] = []

        for root, _, files in os.walk(tmp_path):
            for file in files:
                src_file = Path(root) / file
                rel = src_file.relative_to(tmp_path)
                parts = list(rel.parts)

                # Skip raw GROUP files or hidden metadata
                if file == "GROUP" or file.startswith("."):
                    continue

                canonical = "/".join(parts)
                domain = categorize_path(canonical)
                target_dir = output_docs_dir / domain
                target_dir.mkdir(parents=True, exist_ok=True)

                filename = "-".join(parts) + ".md"
                dest_file = target_dir / filename

                doc_mapping[canonical] = dest_file
                processed_files.append((src_file, dest_file, canonical))

        print(
            f"==> Transforming {len(processed_files)} raw documents into structured Markdown..."
        )
        for src_file, dest_file, canonical in processed_files:
            try:
                raw_text = src_file.read_text(encoding="utf-8", errors="replace")
                title = f"gcloud {canonical.replace('/', ' ')}"
                md_content = convert_raw_help_to_markdown(raw_text, title)
                dest_file.write_text(md_content, encoding="utf-8")
            except (OSError, UnicodeDecodeError, ValueError) as e:
                print(f"Error transforming {src_file}: {e}")

        print("==> Rewriting inter-document relative links...")
        for _, dest_file, _ in processed_files:
            try:
                content = dest_file.read_text(encoding="utf-8")
                rewritten = rewrite_links(content, dest_file, doc_mapping)
                dest_file.write_text(rewritten, encoding="utf-8")
            except (OSError, UnicodeDecodeError, ValueError) as e:
                print(f"Error rewriting links in {dest_file}: {e}")

        # Generate INDEX.md and README.md
        index_md = generate_index_markdown(output_docs_dir, doc_mapping)
        (output_docs_dir / "INDEX.md").write_text(index_md, encoding="utf-8")

        readme_lines = [
            "# Google Cloud CLI Ingested Documentation Mirror",
            "",
            f"This directory stores offline reference mirrors for {len(doc_mapping)} `gcloud` commands and topics.",
            "All pages are organized by functional domain, formatted in Markdown, and cross-linked locally.",
            "",
            "Consult [INDEX.md](INDEX.md) for the complete command navigation matrix.",
            "",
        ]
        (output_docs_dir / "README.md").write_text(
            "\n".join(readme_lines), encoding="utf-8"
        )

        return doc_mapping


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch and format gcloud documentation locally."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs",
        help="Target output directory for ingested documentation",
    )
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    mapping = extract_local_help_docs(output_dir)
    print(
        f"✅ Successfully ingested {len(mapping)} documentation files into {output_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
