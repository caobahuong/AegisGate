# Thin Makefile forwarding all targets to scripts/tasks.py
.PHONY: dev test check seed clean help default

default: help

help:
	@echo "AegisGate Task Runner"
	@echo "Usage:"
	@echo "  make dev    - Run backend + frontend concurrently"
	@echo "  make test   - Run backend pytest + frontend vitest"
	@echo "  make check  - Run full CI checks (lint, types, tests)"
	@echo "  make seed   - Seed demo data against simulated plugin"
	@echo "  make clean  - Clean temporary and cache artifacts"

dev:
	python scripts/tasks.py dev

test:
	python scripts/tasks.py test

check:
	python scripts/tasks.py check

seed:
	python scripts/tasks.py seed

clean:
	python scripts/tasks.py clean
