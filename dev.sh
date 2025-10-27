#!/bin/bash
# Development Helper Script
# This script sets up the environment for local development

export PYTHONPATH="$(pwd)/src"

echo "✅ PYTHONPATH configured: $PYTHONPATH"
echo ""
echo "Available commands:"
echo "  • uvicorn main:app --reload         (Run FastAPI server)"
echo "  • python -m pytest tests/           (Run tests)"
echo "  • ruff check src/                   (Check code quality)"
echo "  • ruff format src/                  (Format code)"
echo ""
echo "To activate, run: source dev.sh"
