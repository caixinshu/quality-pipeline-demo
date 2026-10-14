#!/usr/bin/env python3
"""Quality gate check script.

Supports three gates:
1. Pass rate gate (junit XML)
2. Security scan gate (bandit report)
3. Coverage gate (via pytest-cov --cov-fail-under)

Skip mechanism: add label 'skip-quality-gate' to PR to bypass all gates.
"""
import os
import sys
import xml.etree.ElementTree as ET


def check_pass_rate(results_file, min_rate=1.0):
    """Check test pass rate from junit XML."""
    try:
        tree = ET.parse(results_file)
    except FileNotFoundError:
        print("ERROR: Test results file not found. Did pytest run?")
        print(f"  Expected: {results_file}")
        return False

    root = tree.getroot()
    tests = int(root.get("tests", 0))
    failures = int(root.get("failures", 0))
    errors = int(root.get("errors", 0))

    if tests == 0:
        print("WARNING: No test cases found")
        return True

    passed = tests - failures - errors
    pass_rate = passed / tests

    print(f"  Total tests: {tests}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failures}")
    print(f"  Errors: {errors}")
    print(f"  Pass rate: {pass_rate:.2%}")

    if pass_rate < min_rate:
        print(f"\n  FAIL: Pass rate {pass_rate:.2%} is below required {min_rate:.0%}")
        print(f"  Fix: Investigate {failures} failed and {errors} errored tests")
        return False
    print("  PASS: Pass rate gate passed")
    return True


def check_bandit_security(report_file, max_high=0, max_medium=2):
    """Check bandit security scan results."""
    try:
        with open(report_file, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("ERROR: Bandit report not found. Did bandit run?")
        print(f"  Expected: {report_file}")
        return False

    high_count = content.count("Severity: High") + content.count("severity: HIGH")
    medium_count = content.count("Severity: Medium") + content.count("severity: MEDIUM")

    print(f"  High severity issues: {high_count}")
    print(f"  Medium severity issues: {medium_count}")

    if high_count > max_high:
        print(f"\n  FAIL: {high_count} high severity issues (max allowed: {max_high})")
        print("  Fix: Review bandit report and fix high severity findings")
        return False
    if medium_count > max_medium:
        print(f"\n  WARN: {medium_count} medium severity issues (max allowed: {max_medium})")
        print("  Tip: Consider fixing medium severity issues to improve security")
    else:
        print("  PASS: Security scan gate passed")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Quality gate checker")
    parser.add_argument("--junit", help="junit XML report path")
    parser.add_argument("--bandit", help="bandit report path")
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    parser.add_argument("--skip", action="store_true", help="Skip all gates (for label-based bypass)")
    args = parser.parse_args()

    if args.skip or os.environ.get("SKIP_QUALITY_GATE") == "true":
        print("SKIP: Quality gate bypassed via skip flag")
        sys.exit(0)

    all_passed = True

    if args.junit:
        print("\n=== Pass Rate Gate ===")
        if not check_pass_rate(args.junit, args.min_pass_rate):
            all_passed = False

    if args.bandit:
        print("\n=== Security Scan Gate ===")
        if not check_bandit_security(args.bandit):
            all_passed = False

    if not all_passed:
        print("\n" + "=" * 50)
        print("BLOCKED: Quality gate failed!")
        print("Merge is denied. Fix the issues above and retry.")
        print("=" * 50)
        sys.exit(1)
    else:
        print("\n" + "=" * 50)
        print("All quality gates passed! Merge approved.")
        print("=" * 50)
        sys.exit(0)
