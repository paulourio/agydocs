# kiro-agent/Makefile
SHELL := /bin/bash
ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
QUALITY_GATE := $(ROOT_DIR)/writing/bin/quality_gate

.PHONY: all test audit install install-global install-workspace

all: test audit

test:
	python3 -m unittest discover -s tests -p "test_*.py" -v

audit:
	@if [ -f "$(QUALITY_GATE)" ]; then \
		$(QUALITY_GATE) --profile rfc antigravity.md antigravity.prompt.md README.md steering/*.md; \
	else \
		echo "Warning: quality_gate binary not found at $(QUALITY_GATE)"; \
	fi

install:
	./install.sh

install-global:
	./install.sh --global-only

install-workspace:
	./install.sh --workspace-only
