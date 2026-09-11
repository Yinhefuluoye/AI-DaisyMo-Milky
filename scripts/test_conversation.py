# -*- coding: utf-8 -*-
"""
Conversation 单元测试 —— 纯 Python，不开窗口、不碰磁盘。

跑法：
  .venv\\Scripts\\python.exe scripts\\test_conversation.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from daisymo_conversation import Conversation, normalize_messages  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""), flush=True)


def main():
    # 空
    c = Conversation()
    check("空初始化", len(c) == 0 and not c, f"len={len(c)}")

    # append
    c = Conversation()
    c.append("user", "你好")
    c.append("assistant", '{"text": "嗯"}')
    check("append 正常写入", len(c) == 2 and c.messages()[-1]["role"] == "assistant")
    check("append 不留空记录", c.append("user", "") is False and len(c) == 2)
    check("append 拒绝非法角色", c.append("system", "x") is False and len(c) == 2)

    # messages 是只读视图：同一份、不拷贝
    c = Conversation()
    c.append("user", "a")
    check("messages() 返回内部同一份列表（不拷贝）", c.messages() is c.messages())

    # replace_with 会过滤非法记录并返回条数
    c = Conversation()
    n = c.replace_with([{"role": "user", "content": "1"},
                        {"role": "system", "content": "应被过滤"},
                        {"nope": True},
                        {"role": "assistant", "content": "2"}])
    check("replace_with 返回实际条数", n == 2, f"n={n}")
    check("replace_with 过滤非法角色", all(m["role"] in ("user", "assistant") for m in c.messages()))

    # clear 是原地清空：外部若持旧引用也能看到
    c = Conversation()
    c.append("user", "a")
    hold = c.messages()
    c.clear()
    check("clear 后长度归零", len(c) == 0)
    check("clear 是原地清空（旧引用同样被清掉，不再有过期视图）", len(hold) == 0)

    # normalize_messages 直接测
    check("normalize 对 None 返回空列表", normalize_messages(None) == [])
    check("normalize 对非列表返回空列表", normalize_messages("x") == [])
    check("normalize 把非字符串 content 转成字符串",
          normalize_messages([{"role": "user", "content": 123}])[0]["content"] == "123")

    # 载入分支语义：replace_with 整段替换而不是追加
    c = Conversation()
    c.append("user", "旧的")
    c.replace_with([{"role": "assistant", "content": "新的"}])
    check("replace_with 是整段替换而非追加",
          len(c) == 1 and c.messages()[0]["content"] == "新的",
          f"len={len(c)}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n==== {passed}/{total} PASSED ====", flush=True)
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAILED: {name}  {detail}", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
