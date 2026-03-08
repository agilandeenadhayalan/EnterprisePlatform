#!/usr/bin/env python3
"""
Phase 1: Platform Foundation -- Run All Demos
==============================================

Runs all 6 learning module demos in sequence.

Usage:
    python learning/phase_1/run_phase1.py
    python -m learning.phase_1.run_phase1
"""

import sys
import os
import importlib

# Ensure project root is on sys.path so 'learning' package is importable
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


MODULES = [
    ("Module 01: API Gateway Patterns", "learning.phase_1.src.m01_api_gateway.demo"),
    ("Module 02: Authentication & Authorization", "learning.phase_1.src.m02_authentication.demo"),
    ("Module 03: RESTful API Design", "learning.phase_1.src.m03_rest_api_design.demo"),
    ("Module 04: Database Connection Patterns", "learning.phase_1.src.m04_database_patterns.demo"),
    ("Module 05: Caching Strategies", "learning.phase_1.src.m05_caching.demo"),
    ("Module 06: Containerization", "learning.phase_1.src.m06_containerization.demo"),
]


def run_all() -> None:
    print("\n" + "=" * 60)
    print("  PHASE 1: Platform Foundation -- All Demos")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, module_path in MODULES:
        try:
            mod = importlib.import_module(module_path)
            mod.main()
            passed += 1
        except Exception as e:
            print(f"\n[FAIL] {name} FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"  PHASE 1 SUMMARY: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
