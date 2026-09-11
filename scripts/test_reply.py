# -*- coding: utf-8 -*-
"""daisymo_reply 单元测试 —— 纯 Python。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from daisymo_reply import parse_scene, reply_text  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""), flush=True)


def main():
    # reply_text：干净 JSON
    check("reply_text 取 JSON 的 text",
          reply_text('{"text": "去公园吧"}') == "去公园吧")
    # reply_text：夹带 Markdown 前缀
    check("reply_text 夹带前缀也能取到",
          reply_text('好的，以下是回复：```json\n{"text": "嗯"}\n```') == "嗯")
    # reply_text：纯文本兜底
    check("reply_text 纯文本原样兜底", reply_text("今天好累") == "今天好累")
    # reply_text：空
    check("reply_text 空串", reply_text("") == "")

    # parse_scene：完整 JSON
    s = parse_scene('{"where": "江汉路", "face": "温柔-笑", "body": "便服单叉腰", "text": "hi"}')
    check("parse_scene 完整 JSON", s["where"] == "江汉路" and s["text"] == "hi")

    # parse_scene：夹带前缀
    s = parse_scene('xxx {"where": "a", "text": "t"} yyy')
    check("parse_scene 夹带前后缀", s.get("text") == "t")

    # parse_scene：纯文本降级为默认场景
    s = parse_scene("今天天气不错")
    check("parse_scene 纯文本降级", s.get("where") == "小菊卧室白天" and s["text"] == "今天天气不错")

    # parse_scene：带引号的纯文本会被剥掉
    s = parse_scene('"你好呀"')
    check("parse_scene 剥掉包裹引号", s["text"] == "你好呀")

    # parse_scene：清洗函数生效
    s = parse_scene('{"text": "有emoji😀"}', clean_text=lambda t: t.replace("😀", ""))
    check("parse_scene 清洗函数生效", s["text"] == "有emoji")

    # parse_scene：空串返回空 dict
    check("parse_scene 空串返回空", parse_scene("") == {})

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n==== {passed}/{total} PASSED ====", flush=True)
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAILED: {name}  {detail}", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
