# Finders - Financial Deep Research

Deep financial research agent built with Python + LangChain 1.0 + LangGraph.

## Quick Start

```bash
# Install dependencies
cd backend
pip install -e ".[dev]"

# Set up API keys
cp .env.example .env
# Edit .env with your API keys

# Run CLI
finders

# Run API server
finders-serve
```

## Development

```bash
# Type check
ruff check src/

# Run tests
pytest tests/ -v

# Run in dev mode
pytest tests/ -v --tb=short
```

