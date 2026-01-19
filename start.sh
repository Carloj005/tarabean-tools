#!/bin/bash
# Convenient startup script for Tarabean Solver
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
python3 main.py
