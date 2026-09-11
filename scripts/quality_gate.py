#!/usr/bin/env python3
"""Quality gate check script."""
import sys
import xml.etree.ElementTree as ET


def check_pass_rate(results_file, min_rate=1.0):
    """Check test pass rate from junit XML."""
    tree = ET.parse(results_file)
    root = tree.getroot()
    tests = int(root.get("tests", 0))
    failures = int(root.get("failures", 0))
    errors = int(root.get("errors", 0))

    if tests == 0:
        print("WARNING: No test cases found")
        return True

    passed = tests - failures - errors
    pass_rate = passed / tests

    print(f"Total tests: {tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Pass rate: {pass_rate:.2%}")

    if pass_rate < min_rate:
        print(f"FAIL: Pass rate below threshold {min_rate:.0%}")
        return False
    print("PASS: Pass rate gate passed")
    return True


def check_bandit_security(report_file, max_high=0, max_medium=2):
    """Check bandit security scan results."""
    with open(report_file, "r") as f:
        content = f.read()

    high_count = content.count("Severity: High") + content.count("severity: HIGH")
    medium_count = content.count("Severity: Medium") + content.count("severity: MEDIUM")

    print(f"High severity issues: {high_count}")
    print(f"Medium severity issues: {medium_count}")

    if high_count > max_high:
        print(f"FAIL: High severity issues exceed threshold {max_high}")
        return False
    if medium_count > max_medium:
        print(f"WARN: Medium severity issues exceed threshold {max_medium}")
    else:
        print("PASS: Security scan gate passed")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", help="junit XML report path")
    parser.add_argument("--bandit", help="bandit report path")
    parser.add_argument("--min-pass-rate", type=float, default=1.0)
    args = parser.parse_args()

    all_passed = True

    if args.junit:
        if not check_pass_rate(args.junit, args.min_pass_rate):
            all_passed = False

    if args.bandit:
        if not check_bandit_security(args.bandit):
            all_passed = False

    if not all_passed:
        print("\nBLOCKED: Quality gate failed, merge denied!")
        sys.exit(1)
    else:
        print("\nAll quality gates passed!")
        sys.exit(0)
