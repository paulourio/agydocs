# kiro-agent/Makefile
SHELL := /bin/bash
ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
QUALITY_GATE := $(ROOT_DIR)/writing/bin/quality_gate

.PHONY: all build check-build test audit install install-global install-workspace

all: build test audit

build:
	python3 scripts/build.py

check-build:
	python3 scripts/build.py --check

test: check-build
	python3 -m unittest discover -s tests -p "test_*.py" -v

audit:
	@if [ -f "$(QUALITY_GATE)" ]; then \
		$(QUALITY_GATE) --profile rfc antigravity.md antigravity.prompt.md antigravity-scout.md README.md steering/*.md; \
	else \
		echo "Warning: quality_gate binary not found at $(QUALITY_GATE)"; \
	fi
	@for wf in workflows/*.json; do \
		[ -f "$$wf" ] && python3 -m json.tool "$$wf" > /dev/null || exit 1; \
	done

install:
	./install.sh

install-global:
	./install.sh --global-only

install-workspace:
	./install.sh --workspace-only
