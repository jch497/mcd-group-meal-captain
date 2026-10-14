"""轻量测试运行器（仅依赖标准库，无需 pytest）。

用法：python tests/run_tests.py
会从 tests/ 下导入所有 test_*.py，执行其中 test_* 函数并汇总结果。
"""

import importlib.util
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)


def collect():
    mods = []
    for name in sorted(os.listdir(HERE)):
        if name.startswith("test_") and name.endswith(".py"):
            path = os.path.join(HERE, name)
            spec = importlib.util.spec_from_file_location(name[:-3], path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mods.append(mod)
    return mods


def main():
    mods = collect()
    total = 0
    failed = 0
    for mod in mods:
        funcs = [f for f in dir(mod) if f.startswith("test_") and callable(getattr(mod, f))]
        for fn in funcs:
            total += 1
            try:
                getattr(mod, fn)()
                print(f"  PASS  {mod.__name__}.{fn}")
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"  FAIL  {mod.__name__}.{fn}: {e}")
                traceback.print_exc()
    print(f"\n总计 {total} 个测试，通过 {total - failed}，失败 {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
