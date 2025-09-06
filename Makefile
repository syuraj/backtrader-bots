# Backtrader-Alpaca Trading Platform Makefile
# Provides convenient commands for development, testing, and trading operations

.PHONY: help install test lint clean backtest paper live coverage format

# Default target
help:
	@echo "Backtrader-Alpaca Trading Platform"
	@echo "=================================="
	@echo ""
	@echo "Available commands:"
	@echo "  install     - Install dependencies"
	@echo "  test        - Run all tests"
	@echo "  coverage    - Run tests with coverage report"
	@echo "  lint        - Run code linting"
	@echo "  format      - Format code with black"
	@echo "  clean       - Clean build artifacts"
	@echo ""
	@echo "Trading Commands:"
	@echo "  backtest    - Run backtest with example strategy"
	@echo "  paper       - Run paper trading with example strategy"
	@echo "  live        - Run live trading (requires valid API keys)"
	@echo ""
	@echo "Examples:"
	@echo "  make backtest SYMBOL=AAPL DAYS=30"
	@echo "  make paper SYMBOL=TSLA"
	@echo "  make live SYMBOL=SPY"

# Development setup
install:
	pip install -e .
	pip install pytest pytest-cov black flake8

# Testing
test:
	python -m pytest -v

coverage:
	python -m pytest --cov=src/backtrader_alpaca --cov-report=term-missing --cov-report=html

lint:
	flake8 src/ --max-line-length=100 --ignore=E203,W503
	python -m pyright src/

format:
	black src/ --line-length=100

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf src/*.egg-info/
	rm -rf build/
	rm -rf dist/

# Trading operations
SYMBOL ?= AAPL
DAYS ?= 60
STRATEGY ?= UnifiedExampleStrategy

backtest:
	@echo "Running backtest for $(SYMBOL) with $(STRATEGY)..."
	@echo "Data period: $(DAYS) days"
	@python -c "\
import sys; \
sys.path.append('src'); \
from backtrader_alpaca.strategies.example_strategy import ExampleStrategy; \
from backtrader_alpaca.execution.backtest_runner import run_backtest; \
run_backtest(ExampleStrategy, symbol='$(SYMBOL)', days=$(DAYS));"

paper:
	@echo "Starting paper trading for $(SYMBOL) with $(STRATEGY)..."
	@echo "Press Ctrl+C to stop"
	@TRADING_ENVIRONMENT=paper python -c "\
import sys; \
sys.path.append('src'); \
from backtrader_alpaca.strategies.example_strategy import ExampleStrategy; \
from backtrader_alpaca.execution.live_runner import run_paper_trading; \
run_paper_trading(ExampleStrategy, symbol='$(SYMBOL)');"

live:
	@echo "WARNING: Starting LIVE trading for $(SYMBOL) with $(STRATEGY)"
	@echo "This will use real money. Press Ctrl+C within 10 seconds to cancel..."
	@sleep 10
	@TRADING_ENVIRONMENT=live python -c "\
import sys; \
sys.path.append('src'); \
from backtrader_alpaca.strategies.example_strategy import ExampleStrategy; \
from backtrader_alpaca.execution.live_runner import run_live_trading; \
run_live_trading(ExampleStrategy, symbol='$(SYMBOL)');"

# Quick development commands
dev-setup: install
	@echo "Development environment ready"

quick-test:
	@python -c "\
import sys; \
sys.path.append('src'); \
from backtrader_alpaca.strategies.example_strategy import ExampleStrategy; \
print('✅ Strategy framework imports successful');"

# Data management
download-data:
	@echo "Downloading sample data for $(SYMBOL)..."
	@python -c "\
import sys; \
sys.path.append('src'); \
from backtrader_alpaca.execution.backtest_runner import run_backtest; \
from backtrader_alpaca.strategies.example_strategy import ExampleStrategy; \
run_backtest(ExampleStrategy, symbol='$(SYMBOL)', days=5); \
print('Sample data generated for backtesting');"
