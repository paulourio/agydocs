#!/usr/bin/env python3
"""
Unit tests for BigQuery Documentation Fetcher and Link Rewriter (fetch_docs.py).
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_docs import (
    DEFAULT_CATALOG,
    STANDARD_SQL_PAGES,
    BIGQUERYML_PAGES,
    GRAPH_PAGES,
    INFORMATION_SCHEMA_PAGES,
    SYSTEM_PAGES,
    build_url_mapping,
    categorize_path,
    generate_index_markdown,
    mask_code_blocks,
    normalize_doc_path,
    rewrite_links,
    unmask_code_blocks,
)


class TestBigQueryDocFetcher(unittest.TestCase):
    def test_normalize_doc_path(self) -> None:
        cases = [
            ("https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax.md.txt", "/bigquery/docs/reference/standard-sql/query-syntax"),
            ("https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/pipe-syntax", "/bigquery/docs/reference/standard-sql/pipe-syntax"),
            ("/bigquery/docs/information-schema-tables.md.txt", "/bigquery/docs/information-schema-tables"),
            ("/bigquery/docs/reference/standard-sql/conversion_rules/", "/bigquery/docs/reference/standard-sql/conversion_rules"),
            ("https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/subqueries#concepts", "/bigquery/docs/reference/standard-sql/subqueries"),
        ]
        for inp, expected in cases:
            with self.subTest(inp=inp):
                self.assertEqual(normalize_doc_path(inp), expected)

    def test_categorize_path(self) -> None:
        self.assertEqual(categorize_path("/bigquery/docs/reference/standard-sql/query-syntax"), "standard-sql")
        self.assertEqual(categorize_path("/bigquery/docs/reference/standard-sql/pipe-syntax"), "standard-sql")
        self.assertEqual(categorize_path("/bigquery/docs/reference/standard-sql/geography_functions"), "standard-sql")
        self.assertEqual(categorize_path("/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create"), "bigqueryml")
        self.assertEqual(categorize_path("/bigquery/docs/reference/standard-sql/bigqueryml-syntax-predict"), "bigqueryml")
        self.assertEqual(categorize_path("/bigquery/docs/information-schema-tables"), "information-schema")
        self.assertEqual(categorize_path("/bigquery/docs/information-schema-jobs"), "information-schema")
        self.assertEqual(categorize_path("/bigquery/docs/reference/standard-sql/graph-query-statements"), "graph")
        self.assertEqual(categorize_path("/bigquery/docs/reference/standard-sql/graph-gql-functions"), "graph")
        self.assertEqual(categorize_path("/bigquery/docs/graph-iso-standards"), "graph")
        self.assertEqual(categorize_path("/bigquery/docs/reference/system-procedures"), "system")
        self.assertEqual(categorize_path("/bigquery/docs/reference/system-variables"), "system")

    def test_code_block_masking(self) -> None:
        sample = """Prose before
```sql
SELECT 'https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax' AS url;
```
Middle prose with `inline_code_url` and `[nested](brackets)`.
````markdown
Fenced 4-backtick block with [link](https://example.com)
````
~~~yaml
key: val
~~~
Prose after"""
        masked, blocks = mask_code_blocks(sample)
        self.assertNotIn("SELECT 'https://docs.cloud.google.com", masked)
        self.assertNotIn("inline_code_url", masked)
        self.assertNotIn("Fenced 4-backtick", masked)

        unmasked = unmask_code_blocks(masked, blocks)
        self.assertEqual(unmasked, sample)

    def test_rewrite_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            sql_file = base / "standard-sql" / "query-syntax.md"
            pipe_file = base / "standard-sql" / "pipe-syntax.md"
            graph_file = base / "graph" / "graph-sql-queries.md"
            info_file = base / "information-schema" / "information-schema-tables.md"

            url_to_path = {
                "https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax": sql_file,
                "https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/pipe-syntax": pipe_file,
                "https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-queries": graph_file,
                "https://docs.cloud.google.com/bigquery/docs/information-schema-tables": info_file,
            }

            content = """# Query Syntax

1. Internal self-anchor: [Aliases](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax#implicit_aliases)
2. Same category: [Pipe Syntax](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/pipe-syntax#from_queries)
3. Cross category: [Graph Queries](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/graph-sql-queries#graph_table_operator)
4. Info Schema: [Tables View](/bigquery/docs/information-schema-tables)
5. Relative doc link: [Pipe Guide](pipe-syntax#pipes)
6. External link: [Google](https://google.com)
7. HTML tag: <a href="https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/pipe-syntax">HTML Pipe</a>
8. Reference link:
[ref1]: https://docs.cloud.google.com/bigquery/docs/information-schema-tables "Table info"

```sql
-- URL inside code block MUST be preserved:
SELECT * FROM `docs.cloud.google.com/bigquery/docs/reference/standard-sql/pipe-syntax`;
```
"""
            page_url = "https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax"
            rewritten, count = rewrite_links(content, page_url, sql_file, url_to_path)

            self.assertGreater(count, 0)
            # 1. Self anchor rewritten to #implicit_aliases
            self.assertIn("[Aliases](#implicit_aliases)", rewritten)
            # 2. Same category rewritten to pipe-syntax.md#from_queries
            self.assertIn("[Pipe Syntax](pipe-syntax.md#from_queries)", rewritten)
            # 3. Cross category rewritten to ../graph/graph-sql-queries.md#graph_table_operator
            self.assertIn("[Graph Queries](../graph/graph-sql-queries.md#graph_table_operator)", rewritten)
            # 4. Info schema rewritten to ../information-schema/information-schema-tables.md
            self.assertIn("[Tables View](../information-schema/information-schema-tables.md)", rewritten)
            # 5. Relative doc link rewritten
            self.assertIn("[Pipe Guide](pipe-syntax.md#pipes)", rewritten)
            # 6. External link untouched
            self.assertIn("[Google](https://google.com)", rewritten)
            # 7. HTML tag rewritten
            self.assertIn('<a href="pipe-syntax.md">HTML Pipe</a>', rewritten)
            # 8. Reference link rewritten
            self.assertIn('[ref1]: ../information-schema/information-schema-tables.md "Table info"', rewritten)
            # Code block preserved exactly
            self.assertIn("SELECT * FROM `docs.cloud.google.com/bigquery/docs/reference/standard-sql/pipe-syntax`;", rewritten)

    def test_build_url_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            catalog = {
                "standard-sql": ["/bigquery/docs/reference/standard-sql/query-syntax"],
                "bigqueryml": ["/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create"],
            }

            # Category layout
            cat_map = build_url_mapping(catalog, base, layout="category")
            self.assertEqual(
                cat_map["https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax"],
                base / "standard-sql" / "query-syntax.md",
            )
            self.assertEqual(
                cat_map["https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create"],
                base / "bigqueryml" / "bigqueryml-syntax-create.md",
            )

            # Mirror layout
            mir_map = build_url_mapping(catalog, base, layout="mirror")
            self.assertEqual(
                mir_map["https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax"],
                base / "bigquery" / "docs" / "reference" / "standard-sql" / "query-syntax.md",
            )

            # Flat layout
            flat_map = build_url_mapping(catalog, base, layout="flat")
            self.assertEqual(
                flat_map["https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax"],
                base / "query-syntax.md",
            )

    def test_catalog_contains_all_user_requested_urls(self) -> None:
        required_slugs = [
            "query-syntax",
            "pipe-syntax",
            "data-types",
            "lexical",
            "conversion_rules",
            "format-elements",
            "collation-concepts",
            "text-analysis",
            "functions-reference",
            "aggregate-function-calls",
            "window-function-calls",
            "operators",
            "subqueries",
            "functions-all",
            "window-functions",
            "data-definition-language",
            "dml-syntax",
            "data-control-language",
            "procedural-language",
            "export-statements",
            "load-statements",
            "debugging-statements",
            "system-procedures",
            "system-variables",
        ]
        all_paths = [p for paths in DEFAULT_CATALOG.values() for p in paths]
        all_slugs = {p.split("/")[-1] for p in all_paths}

        for slug in required_slugs:
            with self.subTest(slug=slug):
                self.assertIn(slug, all_slugs)

    def test_generate_index_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            catalog = {
                "standard-sql": ["/bigquery/docs/reference/standard-sql/query-syntax"],
                "system": ["/bigquery/docs/reference/system-procedures"],
            }
            url_map = build_url_mapping(catalog, base, layout="category")
            index_md = generate_index_markdown(catalog, url_map, base)
            self.assertIn("# Official Google Cloud BigQuery Documentation Reference", index_md)
            self.assertIn("standard-sql/query-syntax.md", index_md)
            self.assertIn("system/system-procedures.md", index_md)


if __name__ == "__main__":
    unittest.main()
