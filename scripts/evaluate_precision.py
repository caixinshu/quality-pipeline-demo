#!/usr/bin/env python3
"""精准测试准确率评估

对比「精准筛选的用例」和「全量用例」的结果，计算召回率、精确率、节省时间。
"""
import subprocess
import sys
import os
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from precision_test import get_changed_files, match_tests, build_pytest_command


def count_tests(junit_xml_path):
    """从 junit XML 中解析测试总数和失败数"""
    if not os.path.exists(junit_xml_path):
        return 0, 0
    tree = ET.parse(junit_xml_path)
    root = tree.getroot()
    total = 0
    failures = 0
    for testcase in root.iter('testcase'):
        total += 1
        failure = testcase.find('failure')
        if failure is not None:
            failures += 1
    return total, failures


def run_tests_and_measure(cmd, junit_output, label):
    """运行测试并测量耗时"""
    full_cmd = f"{cmd} --junitxml={junit_output}"
    print(f"\n{'='*60}")
    print(f"[{label}] Running: {full_cmd}")
    print(f"{'='*60}")
    start = time.time()
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start

    print(f"[{label}] Exit code: {result.returncode}")
    print(f"[{label}] Time: {elapsed:.1f}s")
    if result.stdout:
        print(f"[{label}] stdout (last 500 chars): {result.stdout[-500:]}")
    if result.stderr:
        print(f"[{label}] stderr (last 500 chars): {result.stderr[-500:]}")

    return elapsed, result.returncode


def evaluate(base_ref=None, head_ref='HEAD', output_file=None):
    """评估精准测试的准确率"""
    results = {}

    if base_ref:
        changed_files = get_changed_files(base_ref, head_ref)
    else:
        from precision_test import get_pr_changed_files
        changed_files = get_pr_changed_files()

    print(f"Changed files ({len(changed_files)}):")
    for f in changed_files:
        print(f"  - {f}")

    test_files, test_markers, reasons = match_tests(changed_files)
    precision_cmd = build_pytest_command(test_files, test_markers)

    print(f"\nPrecision command: {precision_cmd}")
    print(f"Match reasons:")
    for r in reasons:
        print(f"  {r}")

    full_cmd = "pytest tests/"

    precision_junit = "precision-results.xml"
    full_junit = "full-results.xml"

    print("\n--- Running precision tests ---")
    precision_time, precision_rc = run_tests_and_measure(
        precision_cmd, precision_junit, "PRECISION"
    )

    print("\n--- Running full tests ---")
    full_time, full_rc = run_tests_and_measure(
        full_cmd, full_junit, "FULL"
    )

    precision_total, precision_failures = count_tests(precision_junit)
    full_total, full_failures = count_tests(full_junit)

    recall = 1.0 if full_failures == 0 else (1.0 - (precision_failures / full_failures)) if precision_failures <= full_failures else 0.0
    precision_rate = (full_total - precision_total) / full_total if full_total > 0 else 0.0
    time_saved = 1.0 - (precision_time / full_time) if full_time > 0 else 0.0
    test_reduction = 1.0 - (precision_total / full_total) if full_total > 0 else 0.0

    results = {
        'changed_files': len(changed_files),
        'precision_cmd': precision_cmd,
        'precision_test_count': precision_total,
        'full_test_count': full_total,
        'precision_failures': precision_failures,
        'full_failures': full_failures,
        'recall': f"{recall*100:.1f}%",
        'precision_rate': f"{(1-precision_rate)*100:.1f}%",
        'time_saved': f"{time_saved*100:.1f}%",
        'test_reduction': f"{test_reduction*100:.1f}%",
        'precision_time': f"{precision_time:.1f}s",
        'full_time': f"{full_time:.1f}s",
        'all_pass': precision_failures == 0 and full_failures == 0,
    }

    print(f"\n{'='*60}")
    print("EVALUATION RESULTS")
    print(f"{'='*60}")
    for k, v in results.items():
        print(f"  {k}: {v}")

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {output_file}")

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='精准测试准确率评估')
    parser.add_argument('--base', help='基准 commit/分支')
    parser.add_argument('--head', default='HEAD', help='目标 commit/分支')
    parser.add_argument('--output', help='输出 JSON 结果到文件')
    parser.add_argument('--mode', choices=['pr', 'diff'], default='diff',
                        help='模式：pr=从环境变量获取，diff=手动指定')
    args = parser.parse_args()

    if args.mode == 'pr':
        results = evaluate(output_file=args.output)
    else:
        if not args.base:
            print("Error: diff mode requires --base argument")
            sys.exit(1)
        results = evaluate(base_ref=args.base, head_ref=args.head, output_file=args.output)


if __name__ == '__main__':
    main()
