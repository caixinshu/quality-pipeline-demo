"""Week 2 Day 11：memory_profiler 逐行分析驱动脚本。

直接以普通函数方式调用 slow_memory()（不经过 HTTP），
用 `python -m memory_profiler driver_memory_profiler.py` 运行，
输出每一行的内存增量（increment），定位泄漏行。

预期结论：`_leaky_cache.append(...)` 一行每轮 +~0.1MB，是唯一持续增长的行。
"""

import os
import sys

# 让脚本能 import 到 app.main（uvicorn 启动时由 cwd 保证，这里显式加路径）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import slow_memory  # noqa: E402

if __name__ == "__main__":
    # 模拟 20 次请求，每次泄漏 100KB
    for i in range(20):
        result = slow_memory(size_kb=100)
        if i % 5 == 0:
            print(f"iter={i} cache_mb={result['cache_mb']}")
