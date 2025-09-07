# Backtrader-Alpaca Trading Platform Makefile
# Provides convenient commands for development, testing, and trading operations

.PHONY: help install test lint clean backtest paper live coverage format
.ONESHELL:

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
SYMBOL ?= NQ
DAYS ?= 60
STRATEGY ?= DivergenceStrategy

# Strategy parameter defaults (can be overridden on the command line)
STOP_LOSS_PCT ?= 0.05
TAKE_PROFIT_PCT ?= 0.10
TSI_FAST ?= 25
TSI_SLOW ?= 13
EMA_PERIOD ?= 25
ENTRY_LIMIT_OFFSET_PCT ?= 0.001
USE_MARKET_PARENT ?= 0
DISPLAY_PLOT ?= 0
# Divergence flexibility
SLOPE_EPS ?= 1e-6
MAX_PIVOT_AGE_BARS ?= 50
REQUIRE_BOTH_SERIES ?= 1
VERBOSE ?= 0
STRATEGY_DEBUG ?= 0

backtest:
	@echo "Running backtest for $(SYMBOL) with $(STRATEGY)..."
	@echo "Data period: $(DAYS) days"
	@PYTHONUNBUFFERED=1 \
	DISPLAY_PLOT=$(DISPLAY_PLOT) \
	VERBOSE=$(VERBOSE) \
	SYMBOL=$(SYMBOL) \
	DAYS=$(DAYS) \
	STOP_LOSS_PCT=$(STOP_LOSS_PCT) \
	TAKE_PROFIT_PCT=$(TAKE_PROFIT_PCT) \
	TSI_FAST=$(TSI_FAST) \
	TSI_SLOW=$(TSI_SLOW) \
	EMA_PERIOD=$(EMA_PERIOD) \
	ENTRY_LIMIT_OFFSET_PCT=$(ENTRY_LIMIT_OFFSET_PCT) \
	USE_MARKET_PARENT=$(USE_MARKET_PARENT) \
	SLOPE_EPS=$(SLOPE_EPS) \
	MAX_PIVOT_AGE_BARS=$(MAX_PIVOT_AGE_BARS) \
	REQUIRE_BOTH_SERIES=$(REQUIRE_BOTH_SERIES) \
	STRATEGY_DEBUG=$(STRATEGY_DEBUG) \
	python3 scripts/run_backtest.py

paper:
	@echo "Starting paper trading for $(SYMBOL) with $(STRATEGY)..."
	@echo "Press Ctrl+C to stop"
	@TRADING_ENVIRONMENT=paper python -c "\
import sys; \
sys.path.append('src'); \
from backtrader_alpaca.strategies.divergence_strategy import DivergenceStrategy; \
from backtrader_alpaca.execution.live_runner import run_paper_trading; \
run_paper_trading(DivergenceStrategy, symbol='$(SYMBOL)');"

live:
	@echo "WARNING: Starting LIVE trading for $(SYMBOL) with $(STRATEGY)"
	@echo "This will use real money. Press Ctrl+C within 10 seconds to cancel..."
	@sleep 10
	@TRADING_ENVIRONMENT=live python -c "\
import sys; \
sys.path.append('src'); \
from backtrader_alpaca.strategies.divergence_strategy import DivergenceStrategy; \
from backtrader_alpaca.execution.live_runner import run_live_trading; \
run_live_trading(DivergenceStrategy, symbol='$(SYMBOL)');"

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
