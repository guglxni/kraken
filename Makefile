.PHONY: install test lint type-check security-check rust-checks ci clean

# ── Install ──────────────────────────────────────────────────────────────────

install:
	uv sync --all-extras
	cd ui && pnpm install

# ── Test ─────────────────────────────────────────────────────────────────────

test:
	uv run pytest tests/ -x -q --timeout=90

test-voyages:
	uv run pytest tests/voyages/ -v

test-sources:
	uv run pytest tests/sources/ -v

test-agents:
	uv run pytest tests/agents/ -v

test-e2e:
	uv run pytest tests/e2e/ -v

# ── Lint / Format ─────────────────────────────────────────────────────────────

lint:
	uv run ruff check kraken/ tests/
	uv run ruff format --check kraken/ tests/
	cd ui && pnpm biome check .

format:
	uv run ruff format kraken/ tests/
	uv run ruff check --fix kraken/ tests/
	cd ui && pnpm biome format --write .

# ── Type check ───────────────────────────────────────────────────────────────

type-check:
	uv run mypy kraken/ --strict
	cd ui && pnpm tsc --noEmit

# ── Security ─────────────────────────────────────────────────────────────────

security-check:
	uv run bandit -r kraken/ -ll
	uv run python -m detect_secrets scan --baseline .secrets.baseline
	@echo "Security checks passed."

# ── Rust (source specs) ───────────────────────────────────────────────────────

rust-checks:
	@for spec in sources/*/manifest.yaml; do \
		coral source lint $$spec && echo "✓ $$spec"; \
	done

# ── CI (all checks) ──────────────────────────────────────────────────────────

ci: lint type-check security-check test
	@echo "✓ All CI checks passed."

# ── Voyage helpers ───────────────────────────────────────────────────────────

voyage-compile:
	@read -p "Voyage name: " name; uv run kraken voyage:compile $$name

voyage-lint:
	uv run kraken voyage:lint

# ── Clean ────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	cd ui && rm -rf .next out
