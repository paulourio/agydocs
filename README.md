# Developer Documentation & Engineering Skills (`agydocs`)

This repository curates production-grade skills, quality gates, and architectural reference suites for autonomous AI agents and software engineers.

---

## Core Engineering Skills

| Skill | Directory | Description | Validation Suite |
| :--- | :--- | :--- | :--- |
| **`writing`** | [`writing/`](writing/) | Stylometric quality gate (`quality_gate`) and guidelines for technical systems specifications, RFCs, and research papers. Eliminates AI clichés, formulaic strawmen, and bureaucratic nominalizations. | Calibrated against **20 canonical human monuments** (>3.5M words) and **18 Gen-AI failure incidents**. Full scorecards in [`writing/README.md`](writing/README.md). |
| **`bigquery-googlesql`** | [`bigquery-googlesql/`](bigquery-googlesql/) | Production engineering patterns, pipe syntax (`\|>`), graph queries (GQL), multi-statement transactions, and procedural routines formatted with `bqfmt`. | Machine-verified formatting against `.bqfmt.toml` and dialect boundary rules. Details in [`bigquery-googlesql/README.md`](bigquery-googlesql/README.md). |
| **`gcloud`** | [`gcloud/`](gcloud/) | Standardized operational patterns for the Google Cloud SDK (`gcloud`), infrastructure automation, IAM governance, and service management. | Dry-run validation and syntax checks. Details in [`gcloud/README.md`](gcloud/README.md). |
| **`tool-skill-engineering`** | [`tool-skill-engineering/`](tool-skill-engineering/) | Lifecycle methodology for designing, auditing, and maintaining production tool skills across complex CLI and SDK ecosystems. | Architecture standards in [`tool-skill-engineering/README.md`](tool-skill-engineering/README.md). |

---

## Technical Writing Verification Benchmarks

The writing quality gate engine (`writing/bin/quality_gate`) enforces a zero-debt quality policy calibrated against two empirical benchmark suites:

1. **Canonical Human Masterworks (Ground Truth Positives)**:
   - Evaluated across 20 canonical works (Claude Shannon, Donald Knuth, G. H. Hardy, P. A. M. Dirac, George Pólya, Randolph Quirk, Leslie Lamport, Richard Feynman, Linus Torvalds, and IETF RFC standards).
   - **Passing Status**: All masterworks achieve **100% clean passes under strict enforcement mode (0 errors, HVI = 100.0, TPI = 100.0)**.
2. **Gen-AI Benchmark Corpus (Ground Truth Negatives)**:
   - Evaluated across 18 documented real-world AI failure incidents (retracted Elsevier/Frontiers papers, prompt leakages, *Mata v. Avianca* hallucinated legal briefs, CNET math errors, and Claude-ese slop).
   - **Rejection Status**: Achieves **88.9% rejection under strict mode** and immediate Stage 1 fatal failures on prompt leakage and formulaic AI tells.

*Note: Raw benchmark texts, PDFs, and chapter extractions remain local and untracked via `.gitignore` in compliance with licensing and distribution constraints. Full methodology, test runs, and metric distributions are tracked in [`writing/README.md`](writing/README.md).*
