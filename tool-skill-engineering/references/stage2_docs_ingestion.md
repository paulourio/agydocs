# Stage 2: Documentation Ingestion, Link Rewriting, and Topic Catalogs

Complex tooling platforms maintain hundreds of reference pages documenting function signatures, configuration flags, and system views. Relying on iterative search engine queries during code generation introduces high token latency, wastes search quotas, and generates inconsistent syntax snippets.

---

## 1. The Operational Invariant: Download Once, Analyze Locally

During skill development, agents often attempt live web searches to look up technical details. In conversation `39065542-d064-476b-b5dc-18f49489a3a7`, the user established an invariant regarding redundant searches:

> *"IT is not acceptable to repeatedly query ongoogle for the same docs. You will ned too download this docs and analyze and work with it in a local copy. Stop burning outcals unnecessarily"*

This instruction became a global behavioral rule. When authoring a tool skill, engineers must build an automated documentation ingestion pipeline that captures all relevant upstream documentation into a local offline repository (`docs/`).

```
Upstream Technical Docs ──► Ingestion Engine (fetch_docs.py) ──► Local Offline Mirror (docs/)
                                       │
              ┌────────────────────────┴────────────────────────┐
              ▼                                                 ▼
      Code Fence Shielding                             Relative Link Rewriting
 (Preserves internal code)                         (Web links become local .md)
```

---

## 2. Ingestion Pipeline Architecture

A production documentation fetcher consists of three core components:

```
scripts/
├── fetch_docs.py          # Asynchronous ingestion engine and link parser
├── fetch_docs.sh          # Execution wrapper with environment validation
└── test_fetch_docs.py     # Automated unit test suite verifying URL and link transforms
```

1. **The Ingestion Engine (`scripts/fetch_docs.py`):** An asynchronous or batch script that downloads official documentation pages, extracts clean markdown text, and categorizes files into functional directories (such as `standard-sql/`, `information-schema/`, or `system/`).
2. **The Execution Wrapper (`scripts/fetch_docs.sh`):** A shell runner that verifies network connectivity, sets directory paths, and invokes the Python engine.
3. **The Link Rewriter:** A parser that converts absolute and relative web URLs into local relative markdown links (`.md`), enabling offline cross-navigation across the documentation suite.

---

## 3. Link Rewriting and Code Fence Shielding

Documentation pages contain thousands of cross-references. An unshielded regular expression parser risks modifying code snippets inside SQL or Python listings.

### Code Fence Protection Protocol
The link rewriter must isolate code blocks before applying regex transformations:
1. **Extract Code Blocks:** Replace fenced code blocks (delimited by triple backticks) with unique deterministic placeholders (such as `___CODE_BLOCK_001___`).
2. **Rewrite Markdown Links:** Match markdown hyperlinks (`[text](url)`) and transform external URLs into relative file paths within the local `docs/` hierarchy.
3. **Restore Code Blocks:** Reinsert original code blocks into placeholder locations, guaranteeing that internal code examples remain intact.

### URL Canonicalization Rules
The URL rewriter maps diverse web link structures into deterministic local filesystem paths:

| Incoming Web URL Pattern | Local Target Path | Transformation Rule |
| :--- | :--- | :--- |
| `https://cloud.google.com/.../ref-functions` | `docs/functions/ref-functions.md` | Strip domain prefix; map path segments to directory tree |
| `/bigquery/docs/reference/standard-sql/dml` | `docs/standard-sql/dml.md` | Convert relative web path to local workspace markdown path |
| `ref-overview#partitioning-limits` | `ref-overview.md#partitioning-limits` | Preserve internal anchor fragment while appending `.md` extension |

---

## 4. Automated Testing for Documentation Ingestion

Documentation pipelines must include automated unit tests (`scripts/test_fetch_docs.py`). These tests verify three essential properties:
- **URL Canonicalization:** Verify that varying URL formats (with or without `.md.txt`, trailing slashes, or query parameters) map deterministically to the correct local target file.
- **Header Formatting:** Verify that downloaded documents retain valid level-one markdown headings and frontmatter metadata.
- **Link Transformation Integrity:** Assert that sample documents with nested code blocks preserve code verbatim while successfully converting relative web links to local file targets.

---

## 5. The Topic Catalog Protocol (`docs/INDEX.md`)

When an offline documentation tree spans hundreds of files, agents performing broad text searches encounter high context overhead and truncated result buffers.

The ingestion pipeline must generate a structured topic catalog (`docs/INDEX.md`):
- **Domain Taxonomies:** Group documentation links by subsystem (such as Storage Layouts, Analytical Functions, Model Training, or Security Views).
- **Exact Path Pointers:** Map each concept directly to its local markdown file path.
- **Fast Topic Routing:** Direct the agent to inspect `docs/INDEX.md` first before executing broad recursive searches across the documentation tree.

```markdown
# Topic Catalog Example: docs/INDEX.md
## 1. Declarative Grammar & Operators
- [Operators and Expressions](standard-sql/operators.md)
- [Query Syntax and Clauses](standard-sql/query-syntax.md)

## 2. Analytical Functions
- [Window Functions](functions/window-functions.md)
- [Mathematical Functions](functions/math-functions.md)
```

Generating this structured index ensures that large documentation collections remain immediately discoverable without exhaustive regex scans.
