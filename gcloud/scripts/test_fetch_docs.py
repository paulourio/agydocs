#!/usr/bin/env python3
"""
Unit tests for Google Cloud CLI Documentation Fetcher and Link Rewriter (fetch_docs.py).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_docs import (
    categorize_path,
    convert_raw_help_to_markdown,
    generate_index_markdown,
    mask_code_blocks,
    normalize_doc_path,
    rewrite_links,
    unmask_code_blocks,
)


class TestGcloudDocFetcher(unittest.TestCase):
    def test_normalize_doc_path(self) -> None:
        cases = [
            (
                "https://cloud.google.com/sdk/gcloud/reference/compute/instances/create",
                "compute/instances/create",
            ),
            (
                "https://cloud.google.com/sdk/gcloud/reference/topic/filters.html",
                "topic/filters",
            ),
            (
                "/sdk/gcloud/reference/container/clusters/create.md.txt",
                "container/clusters/create",
            ),
            ("sdk/gcloud/reference/auth/login", "auth/login"),
            ("gcloud.compute.instances.list", "compute/instances/list"),
            ("gcloud.topic.formats", "topic/formats"),
            ("compute/disks/create/", "compute/disks/create"),
        ]
        for inp, expected in cases:
            with self.subTest(inp=inp):
                self.assertEqual(normalize_doc_path(inp), expected)

    def test_categorize_path(self) -> None:
        self.assertEqual(categorize_path("topic/filters"), "topic")
        self.assertEqual(categorize_path("topic/formats"), "topic")
        self.assertEqual(categorize_path("compute/instances/create"), "compute")
        self.assertEqual(categorize_path("container/clusters/create"), "container")
        self.assertEqual(categorize_path("run/deploy"), "run")
        self.assertEqual(categorize_path("storage/buckets/create"), "storage")
        self.assertEqual(categorize_path("iam/service-accounts/create"), "iam")
        self.assertEqual(categorize_path("pubsub/topics/create"), "pubsub")
        self.assertEqual(categorize_path("secrets/create"), "secrets")
        self.assertEqual(categorize_path("logging/read"), "logging")
        self.assertEqual(categorize_path("sql/instances/create"), "sql")
        self.assertEqual(categorize_path("unknown/command"), "general")

    def test_code_block_masking(self) -> None:
        sample = """Prose before code block
```bash
gcloud compute instances list --filter="zone:us-central1-*"
```
Middle text with inline command `gcloud topic formats` and brackets [anchor](target).
~~~yaml
service: my-service
port: 8080
~~~
Final paragraph."""
        masked, blocks = mask_code_blocks(sample)
        self.assertNotIn("gcloud compute instances list", masked)
        self.assertNotIn("`gcloud topic formats`", masked)
        self.assertNotIn("service: my-service", masked)

        unmasked = unmask_code_blocks(masked, blocks)
        self.assertEqual(unmasked, sample)

    def test_convert_raw_help_to_markdown(self) -> None:
        raw_help = """NAME
    gcloud topic filters - resource filters supplementary help

SYNOPSIS
    gcloud topic filters [GCLOUD_WIDE_FLAG ...]

DESCRIPTION
    Filter expressions evaluate server or client side.

  Filter Expressions
    A filter expression is a boolean function.
"""
        md = convert_raw_help_to_markdown(raw_help, "gcloud topic filters")
        self.assertIn("# gcloud topic filters", md)
        self.assertIn("## NAME", md)
        self.assertIn("## SYNOPSIS", md)
        self.assertIn("```bash", md)
        self.assertIn("gcloud topic filters [GCLOUD_WIDE_FLAG ...]", md)
        self.assertIn("## DESCRIPTION", md)
        self.assertIn("### Filter Expressions", md)

    def test_rewrite_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            filter_file = base / "topic" / "topic-filters.md"
            format_file = base / "topic" / "topic-formats.md"
            instance_file = base / "compute" / "compute-instances-list.md"

            doc_mapping = {
                "topic/filters": filter_file,
                "topic/formats": format_file,
                "compute/instances/list": instance_file,
            }

            content = """# Filters Topic
Refer to gcloud topic formats for formatting guidelines.
Also see [Compute Instances](https://cloud.google.com/sdk/gcloud/reference/compute/instances/list#flags).
Code block must remain intact:
```bash
gcloud topic formats
```
"""
            rewritten = rewrite_links(content, filter_file, doc_mapping)
            self.assertIn("[`gcloud topic formats`](topic-formats.md)", rewritten)
            self.assertIn(
                "[Compute Instances](../compute/compute-instances-list.md#flags)",
                rewritten,
            )
            self.assertIn("```bash\ngcloud topic formats\n```", rewritten)

    def test_generate_index_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            doc_mapping = {
                "compute/instances/create": base
                / "compute"
                / "compute-instances-create.md",
                "storage/buckets/create": base
                / "storage"
                / "storage-buckets-create.md",
                "topic/filters": base / "topic" / "topic-filters.md",
            }
            index = generate_index_markdown(base, doc_mapping)
            self.assertIn("# Google Cloud CLI Documentation Catalog", index)
            self.assertIn("### COMPUTE", index)
            self.assertIn("### STORAGE", index)
            self.assertIn("### TOPIC", index)
            self.assertIn("`gcloud compute instances create`", index)


if __name__ == "__main__":
    unittest.main()
