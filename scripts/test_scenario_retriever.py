# -*- coding: utf-8 -*-
"""剧情检索器可注入性单测 —— 纯 Python，验证沙箱干净。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from daisymo_memory import ScenarioMemoryRetriever, build_scenario_retriever  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""), flush=True)


def main():
    # 1. 用「不存在的路径」显式构造空检索器：不加载真实库 → facts 为空
    #    （这才是沙箱的正确用法：测试传假路径隔离真实剧情库）
    r = build_scenario_retriever(json_path="/nonexistent/foo.json")
    check("空检索器（假路径）facts 为空", r.facts == [], f"facts={len(r.facts)}")
    check("空检索器查询返回空字符串", r.query_relevant_facts("红烧肉") == "")

    # 2. 直接构造（不传路径）会回退加载真实库 —— 这是默认行为，不是污染
    r_default = ScenarioMemoryRetriever()
    check("默认构造会加载真实剧情库", len(r_default.facts) > 0, f"facts={len(r_default.facts)}")

    # 3. 注入一个带事实的检索器，验证查询真的走实例而非全局
    #    手工塞一条 fact，验证 query_relevant_facts 命中
    from daisymo_memory import ScenarioFact
    r3 = ScenarioMemoryRetriever(json_path="/nonexistent/bar.json")
    r3.facts = [ScenarioFact(
        id="f1", chapter="C1", title="画集被烧",
        keywords=["画集", "烧"], facts="邱诚的画集被父母烧毁",
        xiaoju_perspective="小菊冲上去救，烫伤了手"
    )]
    out = r3.query_relevant_facts("他的画集被烧了")
    check("注入事实后能命中", "画集被烧" in out, out[:40])
    check("未命中关键词返回空", r3.query_relevant_facts("今天天气不错") == "")

    # 4. 不同实例互不污染（沙箱）
    r4 = build_scenario_retriever(json_path="/nonexistent/baz.json")
    check("实例之间互不污染", r4.facts == [] and len(r3.facts) == 1)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n==== {passed}/{total} PASSED ====", flush=True)
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAILED: {name}  {detail}", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
