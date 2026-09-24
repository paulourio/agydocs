# Reference Client Implementations

This directory provides working reference implementations demonstrating SDK parity across Go and Python client drivers. Each client extracts table schemas, validates column names against ISO 11179 class words, and rejects foreign dialect tokens during query execution.

---

## 1. Directory Structure

```
examples/
├── README.md              # Setup and verification instructions
├── dot_formatter.toml     # Canonical formatter configuration
├── go.mod                 # Go module definition
├── client.go              # Go client implementation
├── client_test.go         # Go client unit tests
├── client.py              # Python client implementation
└── test_client.py         # Python client unit tests
```

---

## 2. Formatter Configuration

The `dot_formatter.toml` configuration specifies mechanical styling rules:
- Two-space indentation width.
- 100-character line length limits.
- Uppercase keywords for queries and expressions.
- ISO 11179 class word checks across column identifiers.

---

## 3. Running Verification Suites

Run the automated test suites using local toolchains:

```bash
# Run Go unit tests and vet checks
go -C examples vet ./...
go -C examples test -v -count=1 ./...

# Run Python unit tests
python3 -m unittest discover -s examples -p "test_*.py"
```

Both clients validate column names against standard class words (`_id`, `_nm`, `_dt`, `_ts`, `_amt`, `_qty`, `_val`, `_rt`, `_p`, `_ind`, `_cd`). Each client rejects foreign dialect tokens before executing statements against target engines.
