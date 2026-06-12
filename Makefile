.PHONY: test test-docker clean setup

SHELL := /bin/bash
TEST_REPORT_DIR := test-reports

setup:
	@chmod +x test.sh
	@mkdir -p $(TEST_REPORT_DIR)
	@pip install ruff pytest pytest-asyncio httpx fastapi uvicorn

test: setup
	@echo "======================================================================"
	@echo "🚀 Starting BlueHub Automated Test Pipeline (Local Mode)"
	@echo "======================================================================"
	@./test.sh local

test-docker:
	@echo "======================================================================"
	@echo "🐳 Starting BlueHub Automated Test Pipeline (Docker Mode)"
	@echo "======================================================================"
	@docker build -f Dockerfile.test -t bluehub-test-runner .
	@docker run --rm -v $$(pwd)/$(TEST_REPORT_DIR):/app/$(TEST_REPORT_DIR) bluehub-test-runner

clean:
	@echo "🧹 Cleaning up test caches, logs, and reports..."
	@rm -rf .pytest_cache
	@rm -rf $(TEST_REPORT_DIR)
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.log" -delete
	@echo "✨ Cleanup completed!"