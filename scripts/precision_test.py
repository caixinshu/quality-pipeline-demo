#!/usr/bin/env python3
"""精准测试 - 根据代码变更筛选测试用例"""
import subprocess
import sys
import os
import re
import json
from pathlib import Path


def get_changed_files(base_ref, head_ref):
    """获取两个 ref 之间变更的文件列表"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', f'{base_ref}...{head_ref}'],
            capture_output=True,
            text=True,
            check=True
        )
        files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        return files
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff: {e.stderr}")
        return []


def get_pr_changed_files():
    """在 GitHub Actions PR 环境中获取变更文件"""
    base = os.environ.get('GITHUB_BASE_REF', '')
    head = os.environ.get('GITHUB_HEAD_REF', '')

    if base and head:
        base_ref = f'origin/{base}'
        head_ref = 'HEAD'
        subprocess.run(['git', 'fetch', 'origin', base], capture_output=True)
        return get_changed_files(base_ref, head_ref)

    return []


def match_tests(changed_files):
    """
    根据变更文件匹配相关测试用例
    返回: (test_files, test_markers, reasons)
    """
    test_files = set()
    test_markers = set()
    reasons = []

    RULES = [
        (r'^app/main\.py$', 'tests/test_api.py', '修改主程序 -> 全部接口测试'),
        (r'^app/models/', 'tests/test_api.py', '修改数据模型 -> 接口测试'),
        (r'^app/utils/(\w+)', 'tests/test_{name}.py', '修改工具 -> 对应工具测试'),
        (r'^app/services/(\w+)', 'tests/test_{name}.py', '修改服务 -> 对应服务测试'),
        (r'^tests/', None, '修改测试文件 -> 跑修改的测试本身'),
        (r'.*\.(yml|yaml)$', 'smoke', '配置变更 -> 只跑冒烟兜底'),
        (r'.*\.(md|txt)$', 'smoke', '文档变更 -> 只跑冒烟兜底'),
        (r'^\.github/', 'smoke', 'CI 配置变更 -> 只跑冒烟兜底'),
    ]

    for f in changed_files:
        matched = False

        if f.startswith('tests/') and f.endswith('.py'):
            test_files.add(f)
            reasons.append(f"测试文件变更: {f} -> 直接跑此文件")
            matched = True
            continue

        for pattern, target, reason in RULES:
            m = re.match(pattern, f)
            if m:
                if target == 'smoke':
                    test_markers.add('smoke')
                    reasons.append(f"{f} -> {reason}")
                elif target and '{name}' in target:
                    name = m.group(1) if m.groups() else ''
                    test_file = target.format(name=name)
                    if os.path.exists(test_file):
                        test_files.add(test_file)
                        reasons.append(f"{f} -> {test_file} ({reason})")
                    else:
                        test_markers.add('smoke')
                        reasons.append(f"{f} -> 无对应测试 {test_file} -> 冒烟兜底")
                elif target:
                    test_files.add(target)
                    reasons.append(f"{f} -> {target} ({reason})")
                else:
                    reasons.append(f"{f} -> {reason}")

                matched = True
                break

        if not matched:
            test_markers.add('smoke')
            reasons.append(f"{f} -> 未匹配规则 -> 冒烟兜底")

    return sorted(test_files), sorted(test_markers), reasons


def build_pytest_command(test_files, test_markers):
    """构建 pytest 执行命令"""
    cmd_parts = ['pytest']

    if test_files:
        cmd_parts.extend(test_files)

    if test_markers:
        marker_expr = ' or '.join(test_markers)
        cmd_parts.extend(['-m', marker_expr])

    if not test_files and not test_markers:
        cmd_parts.extend(['-m', 'smoke'])

    return ' '.join(cmd_parts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='精准测试 - 根据代码变更筛选用例')
    parser.add_argument('--base', help='基准 commit/分支')
    parser.add_argument('--head', help='目标 commit/分支，默认 HEAD')
    parser.add_argument('--mode', choices=['pr', 'diff'], default='pr',
                        help='模式：pr=从环境变量获取，diff=手动指定 base/head')
    parser.add_argument('--dry-run', action='store_true',
                        help='只打印不执行')
    parser.add_argument('--output', help='输出 pytest 参数到文件')
    args = parser.parse_args()

    if args.mode == 'pr':
        changed_files = get_pr_changed_files()
    else:
        if not args.base:
            print("Error: diff mode requires --base argument")
            sys.exit(1)
        head = args.head or 'HEAD'
        changed_files = get_changed_files(args.base, head)

    print(f"Changed files: {len(changed_files)}")
    for f in changed_files:
        print(f"  - {f}")

    test_files, test_markers, reasons = match_tests(changed_files)

    print(f"\nMatch results:")
    for r in reasons:
        print(f"  {r}")

    print(f"\nTest files: {len(test_files)}")
    for f in test_files:
        print(f"  - {f}")

    print(f"Test markers: {', '.join(test_markers) if test_markers else 'none'}")

    cmd = build_pytest_command(test_files, test_markers)
    print(f"\nPytest command:")
    print(f"  {cmd}")

    if args.output:
        with open(args.output, 'w') as f:
            f.write(cmd)
        print(f"\nCommand written to: {args.output}")

    stats = {
        'changed_files': len(changed_files),
        'test_files': len(test_files),
        'markers': list(test_markers),
        'pytest_cmd': cmd,
    }

    print(f"\nStats:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))

    if args.dry_run:
        return


if __name__ == '__main__':
    main()
