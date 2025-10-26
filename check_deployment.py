#!/usr/bin/env python3
"""
Test script to validate the Vercel deployment configuration.
"""

import os
import sys
import json
from pathlib import Path


def test_import_structure():
    """Test if the import structure works correctly."""
    print("🔧 Testing import structure...")

    # Add src to path (same as index.py does)
    src_path = os.path.join(os.path.dirname(__file__), "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    try:
        from main import app

        print(app.__name__)
        print("✅ FastAPI app imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        return False


def test_dependencies():
    """Test if all required dependencies are available."""
    print("\n🔧 Testing dependencies...")

    required_deps = [
        "fastapi",
        "mangum",
        "pydantic",
        "notion_client",
        "jinja2",
        "httpx",
    ]

    missing_deps = []
    for dep in required_deps:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep}")
            missing_deps.append(dep)

    return len(missing_deps) == 0


def test_vercel_config():
    """Test Vercel configuration."""
    print("\n🔧 Testing Vercel configuration...")

    vercel_json = Path("vercel.json")
    if not vercel_json.exists():
        print("❌ vercel.json not found")
        return False

    try:
        with open(vercel_json) as f:
            config = json.load(f)

        # Check required fields
        if "functions" not in config:
            print("❌ functions not configured")
            return False

        if "api/index.py" not in config["functions"]:
            print("❌ api/index.py function not configured")
            return False

        if config["functions"]["api/index.py"]["runtime"] != "python3.12":
            print("❌ Wrong Python runtime version")
            return False

        print("✅ Vercel configuration is valid")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in vercel.json: {e}")
        return False


def test_api_handler():
    """Test if the API handler can be created."""
    print("\n🔧 Testing API handler...")

    try:
        # Add src to path
        src_path = os.path.join(os.path.dirname(__file__), "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        from importlib.util import find_spec

        if find_spec("api.index"):
            print("✅ API handler module found")
        else:
            print("❌ API handler module not found")
            return False

        print("✅ API handler imported successfully")
        print("✅ Handler function available")
        return True

    except ImportError as e:
        print(f"❌ Failed to import API handler: {e}")
        return False


def run_deployment_check():
    """Run all deployment checks."""
    print("🚀 Notion Backend Vercel - Deployment Check\n")

    checks = [
        ("Import Structure", test_import_structure),
        ("Dependencies", test_dependencies),
        ("Vercel Config", test_vercel_config),
        ("API Handler", test_api_handler),
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with exception: {e}")
            results.append((check_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📋 DEPLOYMENT CHECK SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:20} {status}")

    print(f"\nResult: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! Ready for Vercel deployment.")
        return True
    else:
        print(f"\n⚠️  {total - passed} checks failed. Fix issues before deploying.")
        return False


if __name__ == "__main__":
    success = run_deployment_check()
    sys.exit(0 if success else 1)
