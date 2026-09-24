.PHONY: all clean build test test-writing test-bigquery test-tool-skill-engineering test-gcloud audit help

SHELL := /bin/bash

all: clean build test audit

## clean: Remove build artifacts, bytecode, and cache directories
clean:
	@echo "==> Cleaning cache directories and bytecode..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".quality_gate_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.py[cod]" -delete 2>/dev/null || true
	@echo "Clean completed."

## build: Compile writing quality gate binary
build:
	@echo "==> Compiling writing quality gate binary..."
	@cd writing && go build -o bin/quality_gate ./cmd/quality_gate
	@echo "Build completed: writing/bin/quality_gate"

## test: Execute all Go and Python test suites
test: test-writing test-bigquery test-tool-skill-engineering test-gcloud

test-writing:
	@echo "==> Running writing Go tests..."
	@cd writing && go test -count=1 ./...

test-bigquery:
	@echo "==> Running bigquery-googlesql Go and Python tests..."
	@cd bigquery-googlesql/examples && go test -count=1 ./...
	@cd bigquery-googlesql/examples && python3 -m unittest test_schema_extraction.py
	@python3 -m unittest bigquery-googlesql/scripts/test_fetch_docs.py

test-tool-skill-engineering:
	@echo "==> Running tool-skill-engineering verification checks..."
	@bash tool-skill-engineering/scripts/verify.sh

test-gcloud:
	@echo "==> Running gcloud verification checks..."
	@bash gcloud/scripts/verify.sh

## audit: Run stylometric quality gate across all documentation files
audit: build
	@echo "==> Auditing writing documentation..."
	@writing/bin/quality_gate writing/references/ writing/resources/ writing/examples/ writing/benchmarks/ writing/SKILL.md --profile essay --workers 8 || true
	@echo "==> Auditing bigquery-googlesql documentation..."
	@writing/bin/quality_gate bigquery-googlesql/references/ bigquery-googlesql/resources/ bigquery-googlesql/SKILL.md --profile rfc --workers 8
	@echo "==> Auditing tool-skill-engineering documentation..."
	@writing/bin/quality_gate tool-skill-engineering/references/ tool-skill-engineering/resources/anti_patterns_catalog.md tool-skill-engineering/SKILL.md tool-skill-engineering/README.md tool-skill-engineering/examples/README.md --profile rfc --workers 8
	@echo "==> Auditing gcloud documentation..."
	@writing/bin/quality_gate gcloud/references/ gcloud/resources/anti_patterns_catalog.md gcloud/resources/cheat_sheet.md gcloud/SKILL.md gcloud/README.md gcloud/examples/README.md --profile rfc --workers 8

## help: Display available targets
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  all           Run clean, build, test, and audit"
	@echo "  clean         Remove cache directories (.quality_gate_cache, .ruff_cache, __pycache__)"
	@echo "  build         Compile writing/bin/quality_gate from Go sources"
	@echo "  test          Run all tests (writing Go tests and bigquery Go/Python tests)"
	@echo "  audit         Audit documentation files using the compiled quality gate"
	@echo "  help          Show this help message"
