#!/usr/bin/env python3
"""
BigQuery Documentation Fetcher and Link Rewriter

Fetches official BigQuery GoogleSQL, BigQuery ML, INFORMATION_SCHEMA,
and Graph (GQL) documentation markdown files (.md.txt) from docs.cloud.google.com,
saves them locally within the bigquery-googlesql skill, rewrites inter-document
links to local relative file paths, and generates a structured navigation index.
"""

from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys
import time
from typing import Dict, List, Optional, Set, Tuple
import urllib.error
import urllib.parse
import urllib.request

# Base host for documentation
DOCS_HOST = "https://docs.cloud.google.com"

# Default catalog of documentation pages partitioned by architectural domain
STANDARD_SQL_PAGES: List[str] = [
    "/bigquery/docs/reference/standard-sql/aead_encryption_functions",
    "/bigquery/docs/reference/standard-sql/aggregate-dp-functions",
    "/bigquery/docs/reference/standard-sql/aggregate-function-calls",
    "/bigquery/docs/reference/standard-sql/aggregate_functions",
    "/bigquery/docs/reference/standard-sql/approximate_aggregate_functions",
    "/bigquery/docs/reference/standard-sql/array_functions",
    "/bigquery/docs/reference/standard-sql/bit_functions",
    "/bigquery/docs/reference/standard-sql/collation-concepts",
    "/bigquery/docs/reference/standard-sql/conditional_expressions",
    "/bigquery/docs/reference/standard-sql/conversion_functions",
    "/bigquery/docs/reference/standard-sql/conversion_rules",
    "/bigquery/docs/reference/standard-sql/data-control-language",
    "/bigquery/docs/reference/standard-sql/data-definition-language",
    "/bigquery/docs/reference/standard-sql/data-types",
    "/bigquery/docs/reference/standard-sql/date_functions",
    "/bigquery/docs/reference/standard-sql/datetime_functions",
    "/bigquery/docs/reference/standard-sql/debugging-statements",
    "/bigquery/docs/reference/standard-sql/debugging_functions",
    "/bigquery/docs/reference/standard-sql/dlp_functions",
    "/bigquery/docs/reference/standard-sql/dml-syntax",
    "/bigquery/docs/reference/standard-sql/export-statements",
    "/bigquery/docs/reference/standard-sql/federated_query_functions",
    "/bigquery/docs/reference/standard-sql/format-elements",
    "/bigquery/docs/reference/standard-sql/functions-all",
    "/bigquery/docs/reference/standard-sql/functions-reference",
    "/bigquery/docs/reference/standard-sql/geography_functions",
    "/bigquery/docs/reference/standard-sql/hash_functions",
    "/bigquery/docs/reference/standard-sql/hll_functions",
    "/bigquery/docs/reference/standard-sql/interval_functions",
    "/bigquery/docs/reference/standard-sql/json_functions",
    "/bigquery/docs/reference/standard-sql/kll_functions",
    "/bigquery/docs/reference/standard-sql/lexical",
    "/bigquery/docs/reference/standard-sql/load-statements",
    "/bigquery/docs/reference/standard-sql/mathematical_functions",
    "/bigquery/docs/reference/standard-sql/migrating-from-legacy-sql",
    "/bigquery/docs/reference/standard-sql/navigation_functions",
    "/bigquery/docs/reference/standard-sql/net_functions",
    "/bigquery/docs/reference/standard-sql/numbering_functions",
    "/bigquery/docs/reference/standard-sql/objectref_functions",
    "/bigquery/docs/reference/standard-sql/operators",
    "/bigquery/docs/reference/standard-sql/pipe-syntax",
    "/bigquery/docs/reference/standard-sql/procedural-language",
    "/bigquery/docs/reference/standard-sql/query-syntax",
    "/bigquery/docs/reference/standard-sql/range-functions",
    "/bigquery/docs/reference/standard-sql/search_functions",
    "/bigquery/docs/reference/standard-sql/security_functions",
    "/bigquery/docs/reference/standard-sql/statistical_aggregate_functions",
    "/bigquery/docs/reference/standard-sql/string_functions",
    "/bigquery/docs/reference/standard-sql/subqueries",
    "/bigquery/docs/reference/standard-sql/table-functions-built-in",
    "/bigquery/docs/reference/standard-sql/text-analysis",
    "/bigquery/docs/reference/standard-sql/text-analysis-functions",
    "/bigquery/docs/reference/standard-sql/time-series-functions",
    "/bigquery/docs/reference/standard-sql/time_functions",
    "/bigquery/docs/reference/standard-sql/timestamp_functions",
    "/bigquery/docs/reference/standard-sql/utility-functions",
    "/bigquery/docs/reference/standard-sql/vectorindex_functions",
    "/bigquery/docs/reference/standard-sql/window-function-calls",
    "/bigquery/docs/reference/standard-sql/window-functions",
]

BIGQUERYML_PAGES: List[str] = [
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-advanced-weights",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-agg",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-classify",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-count-tokens",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-detect-anomalies",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-embed",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-evaluate",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-forecast",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-bool",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-double",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-embedding",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-int",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-generate-text",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-if",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-key-drivers",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-predict",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-score",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-search",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ai-similarity",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-alter-model",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-annotate-image",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-arima-coefficients",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-arima-evaluate",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-bag-of-words",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-bucketize",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-causal-effect",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-centroids",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-confusion",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-convert-color-space",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-convert-image-type",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-correlation",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-autoencoder",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-automl",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-boosted-tree",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-contribution-analysis",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-dnn-models",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-glm",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-kmeans",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-matrix-factorization",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-multivariate-time-series",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-onnx",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-pca",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-random-forest",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model-embedding-maas",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model-https",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model-open",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model-service",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-remote-model-tuned",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-tensorflow",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-tflite",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-time-series",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-transform",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-wnd-models",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-xgboost",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-decode-image",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-describe-data",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-detect-anomalies",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-detect-change-points",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-distance",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-drop-model",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-entity-feature-time",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-evaluate",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-explain-forecast",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-explain-predict",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-export-model",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-feature",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-feature-cross",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-feature-time",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-forecast",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-embedding",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-table",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-text",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-get-insights",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-global-explain",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-hash-bucketize",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-holiday-info",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-importance",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-imputer",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-label-encoder",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-lp-norm",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-max-abs-scaler",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-metrics",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-min-max-scaler",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-multi-hot-encoder",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-ngrams",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-normalizer",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-one-hot-encoder",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-polynomial-expand",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-predict",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-principal-component-info",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-principal-components",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-process-document",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-quantile-bucketize",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-recommend",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-reconstruction-loss",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-resize-image",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-robust-scaler",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-roc",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-seasonality",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-standard-scaler",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-tf-idf",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-tfdv-describe",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-tfdv-validate",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-train",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-transcribe",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-transform",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-translate",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-trend",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-trial-info",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-understand-text",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-validate-data-drift",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-validate-data-skew",
    "/bigquery/docs/reference/standard-sql/bigqueryml-syntax-weights",
]

GRAPH_PAGES: List[str] = [
    "/bigquery/docs/graph-iso-standards",
    "/bigquery/docs/reference/standard-sql/graph-conditional-expressions",
    "/bigquery/docs/reference/standard-sql/graph-data-types",
    "/bigquery/docs/reference/standard-sql/graph-gql-functions",
    "/bigquery/docs/reference/standard-sql/graph-intro",
    "/bigquery/docs/reference/standard-sql/graph-operators",
    "/bigquery/docs/reference/standard-sql/graph-patterns",
    "/bigquery/docs/reference/standard-sql/graph-query-statements",
    "/bigquery/docs/reference/standard-sql/graph-schema-statements",
    "/bigquery/docs/reference/standard-sql/graph-sql-queries",
    "/bigquery/docs/reference/standard-sql/graph-subqueries",
]

INFORMATION_SCHEMA_PAGES: List[str] = [
    "/bigquery/docs/information-schema-assignments",
    "/bigquery/docs/information-schema-assignments-changes",
    "/bigquery/docs/information-schema-bi-capacities",
    "/bigquery/docs/information-schema-bi-capacity-changes",
    "/bigquery/docs/information-schema-capacity-commitment-changes",
    "/bigquery/docs/information-schema-capacity-commitments",
    "/bigquery/docs/information-schema-column-field-paths",
    "/bigquery/docs/information-schema-columns",
    "/bigquery/docs/information-schema-constraint-column-usage",
    "/bigquery/docs/information-schema-datasets-schemata",
    "/bigquery/docs/information-schema-datasets-schemata-links",
    "/bigquery/docs/information-schema-datasets-schemata-options",
    "/bigquery/docs/information-schema-effective-project-options",
    "/bigquery/docs/information-schema-index-column-options",
    "/bigquery/docs/information-schema-index-columns",
    "/bigquery/docs/information-schema-index-options",
    "/bigquery/docs/information-schema-indexes",
    "/bigquery/docs/information-schema-indexes-by-organization",
    "/bigquery/docs/information-schema-insights",
    "/bigquery/docs/information-schema-intro",
    "/bigquery/docs/information-schema-jobs",
    "/bigquery/docs/information-schema-jobs-by-folder",
    "/bigquery/docs/information-schema-jobs-by-organization",
    "/bigquery/docs/information-schema-jobs-by-user",
    "/bigquery/docs/information-schema-jobs-timeline",
    "/bigquery/docs/information-schema-jobs-timeline-by-folder",
    "/bigquery/docs/information-schema-jobs-timeline-by-organization",
    "/bigquery/docs/information-schema-jobs-timeline-by-user",
    "/bigquery/docs/information-schema-key-column-usage",
    "/bigquery/docs/information-schema-materialized-views",
    "/bigquery/docs/information-schema-object-privileges",
    "/bigquery/docs/information-schema-organization-options",
    "/bigquery/docs/information-schema-organization-options-changes",
    "/bigquery/docs/information-schema-parameters",
    "/bigquery/docs/information-schema-partitions",
    "/bigquery/docs/information-schema-project-options",
    "/bigquery/docs/information-schema-project-options-changes",
    "/bigquery/docs/information-schema-property-graphs",
    "/bigquery/docs/information-schema-recommendations",
    "/bigquery/docs/information-schema-recommendations-by-org",
    "/bigquery/docs/information-schema-reservation-changes",
    "/bigquery/docs/information-schema-reservation-timeline",
    "/bigquery/docs/information-schema-reservations",
    "/bigquery/docs/information-schema-routine-options",
    "/bigquery/docs/information-schema-routines",
    "/bigquery/docs/information-schema-schemata-replicas",
    "/bigquery/docs/information-schema-schemata-replicas-by-failover-reservation",
    "/bigquery/docs/information-schema-sessions-by-project",
    "/bigquery/docs/information-schema-sessions-by-user",
    "/bigquery/docs/information-schema-shared-dataset-usage",
    "/bigquery/docs/information-schema-snapshots",
    "/bigquery/docs/information-schema-streaming",
    "/bigquery/docs/information-schema-streaming-by-folder",
    "/bigquery/docs/information-schema-streaming-by-organization",
    "/bigquery/docs/information-schema-table-constraints",
    "/bigquery/docs/information-schema-table-options",
    "/bigquery/docs/information-schema-table-storage",
    "/bigquery/docs/information-schema-table-storage-by-folder",
    "/bigquery/docs/information-schema-table-storage-by-organization",
    "/bigquery/docs/information-schema-table-storage-usage",
    "/bigquery/docs/information-schema-table-storage-usage-by-folder",
    "/bigquery/docs/information-schema-table-storage-usage-by-organization",
    "/bigquery/docs/information-schema-tables",
    "/bigquery/docs/information-schema-vector-index-columns",
    "/bigquery/docs/information-schema-vector-index-options",
    "/bigquery/docs/information-schema-vector-indexes",
    "/bigquery/docs/information-schema-views",
    "/bigquery/docs/information-schema-write-api",
    "/bigquery/docs/information-schema-write-api-by-folder",
    "/bigquery/docs/information-schema-write-api-by-organization",
]

SYSTEM_PAGES: List[str] = [
    "/bigquery/docs/reference/system-procedures",
    "/bigquery/docs/reference/system-variables",
]

DEFAULT_CATALOG: Dict[str, List[str]] = {
    "standard-sql": STANDARD_SQL_PAGES,
    "bigqueryml": BIGQUERYML_PAGES,
    "graph": GRAPH_PAGES,
    "information-schema": INFORMATION_SCHEMA_PAGES,
    "system": SYSTEM_PAGES,
}


def normalize_doc_path(url_or_path: str) -> str:
    """Normalizes an input URL or doc path to a canonical root path without extension or anchor."""
    clean = url_or_path.strip()
    if clean.startswith("http://") or clean.startswith("https://"):
        parsed = urllib.parse.urlparse(clean)
        clean = parsed.path
    else:
        clean = clean.split("#")[0]

    clean = clean.rstrip("/")
    if clean.endswith(".md.txt"):
        clean = clean[:-7]
    elif clean.endswith(".md"):
        clean = clean[:-3]
    return clean


def categorize_path(path: str) -> str:
    """Assigns a documentation path to one of the canonical categories."""
    slug = path.split("/")[-1].lower()
    if slug.startswith("information-schema"):
        return "information-schema"
    elif "bigqueryml" in slug or "bqml" in slug:
        return "bigqueryml"
    elif slug.startswith("system-"):
        return "system"
    elif (slug.startswith("graph-") or slug.startswith("graph_") or "gql" in slug) and "geography" not in slug:
        return "graph"
    else:
        return "standard-sql"


def discover_nav_paths() -> Dict[str, List[str]]:
    """Discovers live documentation paths directly from Google Cloud devsite navigation."""
    nav_url = f"{DOCS_HOST}/bigquery/docs/reference/standard-sql/query-syntax"
    print(f"[*] Discovering live doc structure from devsite nav: {nav_url} ...")
    req = urllib.request.Request(nav_url, headers={"User-Agent": "Mozilla/5.0 (compatible; BigQueryDocFetcher/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"[!] Warning: devsite navigation discovery failed ({exc}); falling back to static catalog.")
        return DEFAULT_CATALOG

    raw_links = set(re.findall(r'href=["\'](/bigquery/docs/[^"\'#\s]+)', html))
    discovered: Dict[str, List[str]] = {k: list(v) for k, v in DEFAULT_CATALOG.items()}

    for link in raw_links:
        path = normalize_doc_path(link)
        # Filter for reference domains of interest
        is_sql = path.startswith("/bigquery/docs/reference/standard-sql/")
        is_info = "information-schema" in path
        is_sys = path.startswith("/bigquery/docs/reference/system-")
        is_graph = any(g in path for g in ["graph", "gql"]) and "geography" not in path

        if is_sql or is_info or is_sys or is_graph:
            cat = categorize_path(path)
            if cat in discovered and path not in discovered[cat]:
                discovered[cat].append(path)

    for cat in discovered:
        discovered[cat].sort()

    return discovered


def mask_code_blocks(text: str) -> Tuple[str, List[str]]:
    """Masks code blocks and inline code snippets to protect them from link rewriting."""
    blocks: List[str] = []

    def repl(m: re.Match) -> str:
        blocks.append(m.group(0))
        return f"__CODE_BLOCK_{len(blocks) - 1}__"

    # Match 4-backtick, 3-backtick, ~~~ fences, and inline `...`
    pattern = re.compile(r"(````[\s\S]*?````|```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]+`)")
    masked_text = pattern.sub(repl, text)
    return masked_text, blocks


def unmask_code_blocks(text: str, blocks: List[str]) -> str:
    """Restores masked code blocks in the markdown text."""
    for i, b in enumerate(blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", b)
    return text


def rewrite_links(
    content: str,
    page_canonical_url: str,
    page_filepath: Path,
    url_to_path: Dict[str, Path],
) -> Tuple[str, int]:
    """
    Rewrites markdown and HTML links pointing to other downloaded docs into local relative paths.
    Returns the modified content and the number of links rewritten.
    """
    masked, blocks = mask_code_blocks(content)
    source_dir = page_filepath.parent
    rewritten_count = 0

    def resolve_href(raw_href: str) -> str:
        nonlocal rewritten_count
        parts = raw_href.strip().split(None, 1)
        if not parts:
            return raw_href

        href_url = parts[0]
        title = f" {parts[1]}" if len(parts) > 1 else ""

        # Pure self-anchor links (#section) need no resolution
        if href_url.startswith("#"):
            return raw_href

        full_url = urllib.parse.urljoin(page_canonical_url, href_url)
        parsed = urllib.parse.urlparse(full_url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        if clean_url.endswith(".md.txt"):
            clean_url = clean_url[:-7]
        elif clean_url.endswith(".md"):
            clean_url = clean_url[:-3]

        if clean_url in url_to_path:
            target_path = url_to_path[clean_url]
            frag = f"#{parsed.fragment}" if parsed.fragment else ""
            if target_path.resolve() == page_filepath.resolve():
                new_href = frag if frag else "#"
            else:
                rel = os.path.relpath(target_path, source_dir)
                new_href = f"{rel}{frag}"

            rewritten_count += 1
            return f"{new_href}{title}"

        return raw_href

    # 1. Inline markdown links: [text](href)
    md_pattern = re.compile(r"(\[((?:[^\[\]]|\[[^\[\]]*\])+)\]\()([^)]+)(\))")

    def md_repl(m: re.Match) -> str:
        return f"{m.group(1)}{resolve_href(m.group(3))}{m.group(4)}"

    rewritten = md_pattern.sub(md_repl, masked)

    # 2. Markdown reference links: [ref]: url
    ref_pattern = re.compile(r"(^\[([^\]]+)\]:\s*)([^\s]+)(.*)$", re.MULTILINE)

    def ref_repl(m: re.Match) -> str:
        return f"{m.group(1)}{resolve_href(m.group(3))}{m.group(4)}"

    rewritten = ref_pattern.sub(ref_repl, rewritten)

    # 3. HTML <a> tags: <a href="...">
    html_pattern = re.compile(r'(<a\s+[^>]*?href=["\'])([^"\' >\s]+)(["\'][^>]*>)', re.IGNORECASE)

    def html_repl(m: re.Match) -> str:
        return f"{m.group(1)}{resolve_href(m.group(2))}{m.group(3)}"

    rewritten = html_pattern.sub(html_repl, rewritten)

    final_content = unmask_code_blocks(rewritten, blocks)
    return final_content, rewritten_count


def fetch_single_file(
    path: str,
    target_file: Path,
    force: bool = False,
    timeout: int = 15,
    max_retries: int = 3,
) -> Tuple[str, bool, Optional[str]]:
    """
    Fetches a single markdown document from Google Cloud docs and writes it to target_file.
    Returns (path, success, error_message).
    """
    if target_file.exists() and not force and target_file.stat().st_size > 0:
        return path, True, "cached"

    fetch_url = f"{DOCS_HOST}{path}.md.txt"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BigQueryDocFetcher/1.0)"}
    req = urllib.request.Request(fetch_url, headers=headers)

    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status != 200:
                    return path, False, f"HTTP {resp.status}"
                data = resp.read()
                if not data:
                    return path, False, "Empty response body"

                target_file.parent.mkdir(parents=True, exist_ok=True)
                with open(target_file, "wb") as f:
                    f.write(data)
                return path, True, None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(1.0 * attempt)
                continue
            return path, False, f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1.0 * attempt)
                continue
            return path, False, str(e)

    return path, False, "Max retries exceeded"


def build_url_mapping(
    catalog: Dict[str, List[str]],
    dest_dir: Path,
    layout: str = "category",
) -> Dict[str, Path]:
    """
    Builds a mapping from canonical doc URL (https://docs.cloud.google.com/...)
    to the target local Path according to layout strategy.
    """
    mapping: Dict[str, Path] = {}

    for category, paths in catalog.items():
        for path in paths:
            canonical_url = f"{DOCS_HOST}{path}"
            slug = path.split("/")[-1]

            if layout == "category":
                target_path = dest_dir / category / f"{slug}.md"
            elif layout == "mirror":
                # Mirrors path under dest_dir: e.g. dest/bigquery/docs/...
                rel_parts = path.strip("/").split("/")
                target_path = dest_dir / Path(*rel_parts[:-1]) / f"{slug}.md"
            elif layout == "flat":
                target_path = dest_dir / f"{slug}.md"
            else:
                raise ValueError(f"Unknown layout: {layout}")

            mapping[canonical_url] = target_path

    return mapping


def generate_index_markdown(
    catalog: Dict[str, List[str]],
    url_to_path: Dict[str, Path],
    dest_dir: Path,
) -> str:
    """Generates a structured, hyperlinked index README.md for the downloaded docs."""
    lines: List[str] = [
        "# Official Google Cloud BigQuery Documentation Reference",
        "",
        "This directory contains local, offline-accessible markdown copies of the official Google Cloud BigQuery reference documentation. Inter-document links have been rewritten to resolve against local relative files.",
        "",
        f"- **Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **Total Documents:** {sum(len(v) for v in catalog.values())}",
        "",
        "---",
        "",
        "## Table of Contents",
        "",
    ]

    category_titles = {
        "standard-sql": "GoogleSQL Classic & Pipe Syntax Reference",
        "bigqueryml": "BigQuery ML (BQML) Reference",
        "graph": "Graph Query Language (GQL) in BigQuery",
        "information-schema": "INFORMATION_SCHEMA System Views",
        "system": "System Procedures and System Variables",
    }

    for cat, title in category_titles.items():
        paths = catalog.get(cat, [])
        if not paths:
            continue
        anchor = title.lower().replace(" ", "-").replace("&", "").replace("(", "").replace(")", "").replace("--", "-")
        lines.append(f"- [{title}](#{anchor}) ({len(paths)} documents)")

    lines.append("")
    lines.append("---")
    lines.append("")

    for cat, title in category_titles.items():
        paths = catalog.get(cat, [])
        if not paths:
            continue

        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Document Name | Slug | Local Link | Upstream Link |")
        lines.append("| :--- | :--- | :--- | :--- |")

        for p in sorted(paths):
            canon_url = f"{DOCS_HOST}{p}"
            target_path = url_to_path.get(canon_url)
            slug = p.split("/")[-1]
            doc_name = slug.replace("-", " ").replace("_", " ").title()

            if target_path:
                rel_link = os.path.relpath(target_path, dest_dir)
                local_md = f"[{slug}.md]({rel_link})"
            else:
                local_md = "N/A"

            upstream_md = f"[docs.cloud.google.com]({canon_url})"
            lines.append(f"| **{doc_name}** | `{slug}` | {local_md} | {upstream_md} |")

        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch official BigQuery documentation markdown files, save locally, and rewrite links."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="Optional specific URLs or paths to fetch instead of or in addition to the catalog.",
    )
    parser.add_argument(
        "--urls-file",
        type=Path,
        help="Path to a text file containing URLs or paths to fetch (one per line).",
    )
    parser.add_argument(
        "-d",
        "--dest",
        type=Path,
        default=None,
        help="Destination directory (default: bigquery-googlesql/docs or ./docs).",
    )
    parser.add_argument(
        "-c",
        "--category",
        choices=["all", "standard-sql", "bigqueryml", "graph", "information-schema", "system"],
        default="all",
        help="Filter which documentation domain category to fetch (default: all).",
    )
    parser.add_argument(
        "-l",
        "--layout",
        choices=["category", "mirror", "flat"],
        default="category",
        help="Folder layout for downloaded docs (default: category).",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=10,
        help="Number of concurrent worker threads (default: 10).",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force re-download even if local files already exist.",
    )
    parser.add_argument(
        "--no-rewrite-links",
        action="store_true",
        help="Skip link rewriting stage (preserves raw upstream markdown links).",
    )
    parser.add_argument(
        "--no-discover",
        action="store_true",
        help="Skip live devsite navigation discovery and use static built-in catalog.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display target files and planned operations without downloading.",
    )

    args = parser.parse_args()

    # Determine default destination directory
    script_dir = Path(__file__).resolve().parent
    skill_root = script_dir.parent
    if args.dest:
        dest_dir = args.dest.resolve()
    elif (skill_root / "SKILL.md").exists():
        dest_dir = skill_root / "docs"
    else:
        dest_dir = Path("docs").resolve()

    print(f"[*] Target destination directory: {dest_dir}")
    print(f"[*] Layout mode: {args.layout}")

    # Discover or load catalog
    if args.no_discover or args.urls or args.urls_file:
        catalog = {k: list(v) for k, v in DEFAULT_CATALOG.items()}
    else:
        catalog = discover_nav_paths()

    # Process custom URLs if supplied
    custom_paths: List[str] = []
    if args.urls:
        custom_paths.extend([normalize_doc_path(u) for u in args.urls])

    if args.urls_file and args.urls_file.exists():
        with open(args.urls_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    custom_paths.append(normalize_doc_path(line))

    if custom_paths:
        for p in custom_paths:
            cat = categorize_path(p)
            if p not in catalog[cat]:
                catalog[cat].append(p)

    # Filter categories if requested
    if args.category != "all":
        catalog = {args.category: catalog.get(args.category, [])}

    # Count total files
    total_docs = sum(len(paths) for paths in catalog.values())
    print(f"[*] Active catalog contains {total_docs} documents across {len(catalog)} categories:")
    for cat, paths in catalog.items():
        print(f"    - {cat:20}: {len(paths)} documents")

    # Build mapping
    url_to_path = build_url_mapping(catalog, dest_dir, layout=args.layout)

    if args.dry_run:
        print("\n[DRY RUN] Planned file downloads:")
        for url, target_path in url_to_path.items():
            print(f"  {url} -> {target_path}")
        print(f"\n[DRY RUN] Would download {len(url_to_path)} files to {dest_dir}")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Concurrently fetch documents
    print(f"\n[*] Starting concurrent download of {len(url_to_path)} documents using {args.workers} workers...")
    fetch_tasks = []
    for url, target_path in url_to_path.items():
        doc_path = urllib.parse.urlparse(url).path
        fetch_tasks.append((doc_path, target_path))

    downloaded = 0
    cached = 0
    failed = 0

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_task = {
            executor.submit(fetch_single_file, doc_p, tgt_p, force=args.force): (doc_p, tgt_p)
            for doc_p, tgt_p in fetch_tasks
        }

        for future in concurrent.futures.as_completed(future_to_task):
            doc_p, tgt_p = future_to_task[future]
            try:
                p, ok, msg = future.result()
                if ok:
                    if msg == "cached":
                        cached += 1
                    else:
                        downloaded += 1
                else:
                    failed += 1
                    print(f"    [!] Failed to fetch {doc_p}: {msg}")
            except Exception as e:
                failed += 1
                print(f"    [!] Exception fetching {doc_p}: {e}")

    elapsed = time.time() - start_time
    print(f"[*] Ingestion complete in {elapsed:.2f}s:")
    print(f"    Downloaded : {downloaded}")
    print(f"    Cached     : {cached}")
    print(f"    Failed     : {failed}")

    if failed > 0:
        print(f"[!] Warning: {failed} files failed to download.")

    # Step 2: Rewrite inter-document links
    if not args.no_rewrite_links:
        print(f"\n[*] Rewriting inter-document links across {len(url_to_path)} files...")
        total_rewritten_links = 0
        files_modified = 0

        for url, target_path in url_to_path.items():
            if not target_path.exists():
                continue

            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read()

                new_content, count = rewrite_links(
                    content=content,
                    page_canonical_url=url,
                    page_filepath=target_path,
                    url_to_path=url_to_path,
                )

                if count > 0 and new_content != content:
                    with open(target_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    files_modified += 1
                    total_rewritten_links += count

            except Exception as e:
                print(f"[!] Error rewriting links in {target_path}: {e}")

        print(f"[*] Link rewriting complete:")
        print(f"    Files updated  : {files_modified}")
        print(f"    Links rewritten: {total_rewritten_links}")

    # Step 3: Generate master README / index
    index_path = dest_dir / "README.md"
    print(f"\n[*] Generating navigation index at: {index_path} ...")
    index_md = generate_index_markdown(catalog, url_to_path, dest_dir)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_md)
    print(f"[*] Documentation suite ready at: {dest_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
