# -*- coding: utf-8 -*-
"""聊天回合回归测试：玩家发言 → 异步回复 → 思考态复位；输入框空文本光标。"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import pygame
pygame.init()

from DaisyMo import Screen, DaisyMo, PLAYER  # noqa: E402
from daisymo_widgets import TextInputBox  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""), flush=True)


REPLY = {"where": "小菊卧室白天", "face": "温柔-说", "body": "便服单叉腰",
         "text": "哼，测试回复收到啦。别愣着，赶紧继续说啊。", "bgm": "", "sfx": ""}


def test_chat_round():
    """完整聊天回合：Tab 进输入 → 打字 → 回车 → 思考态必须复位且回复上屏。"""
    app = Screen()
    app.daisymo = DaisyMo(app.conversation, on_first_meet=None)
    app.daisymo.chat_then_parse = lambda text: dict(REPLY)
    app.daisymo.auto_save = lambda: None
    if not DaisyMo.api_key:
        DaisyMo.api_key = "test-key"

    # 帧脚本：空帧×3 → TAB 进输入 → TEXTINPUT 打字 → 回车提交 → 空帧×30 → ESC 退出
    script = [None] * 3
    script.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_TAB, "mod": 0}))
    script.append(pygame.event.Event(pygame.TEXTINPUT, {"text": "你"}))
    script.append(pygame.event.Event(pygame.TEXTINPUT, {"text": "好"}))
    script.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0, "unicode": ""}))
    script += [None] * 30
    script.append(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0}))

    state = {"i": 0}
    orig_get = pygame.event.get

    def fake_get(*a, **k):
        orig_get()
        i = state["i"]
        state["i"] = i + 1
        ev = script[i] if i < len(script) else pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE, "mod": 0})
        return [ev] if ev is not None else []

    pygame.event.get = fake_get
    try:
        app.main()
    finally:
        pygame.event.get = orig_get

    check("提交后进入思考态再复位", app.ui.is_thinking is False, f"is_thinking={app.ui.is_thinking}")
    check("回复文本进入打字机", app.ui.current_text == REPLY["text"],
          f"current_text={app.ui.current_text[:20]!r}")


def test_cursor_empty_box():
    """空文本输入框（激活态）必须画光标：spy pygame.draw.line。"""
    pygame.font.init()
    box = TextInputBox(
        rect=pygame.Rect(0, 0, 400, 60), text="",
        font=pygame.font.Font(None, 20), max_lines=2
    )
    box.is_active = True
    surf = pygame.Surface((400, 60))

    calls = []
    orig_line = pygame.draw.line

    def spy_line(surface, color, p1, p2, width=1):
        calls.append((p1, p2))
        return orig_line(surface, color, p1, p2, width)

    pygame.draw.line = spy_line
    try:
        box.render(surf, True)
    finally:
        pygame.draw.line = orig_line

    check("空文本激活态画出光标竖线", len(calls) > 0, f"draw.line 调用 {len(calls)} 次")


def main():
    test_chat_round()
    test_cursor_empty_box()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n==== {passed}/{total} PASSED ====", flush=True)
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAILED: {name}  {detail}", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
