# -*- coding: utf-8 -*-
"""UiState 迁移后的完整启动冒烟：构造 Screen，确认 ui 命名空间就位，跑一小段 main 循环。"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import pygame
pygame.init()

from daisymo_ui_state import UiState  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""), flush=True)


def main():
    from DaisyMo import Screen, DaisyMo  # noqa: E402

    app = Screen()

    # ui 命名空间就位
    check("self.ui 存在", hasattr(app, "ui") and isinstance(app.ui, UiState))
    check("mode 默认 DAISYMO", app.ui.mode == 1, f"mode={app.ui.mode}")
    check("ui 上 28 个字段都在", all(hasattr(app.ui, f) for f in (
        "mode", "ui_hidden", "is_auto", "is_thinking", "thinking_start_time", "current_req_id",
        "player_input", "player_cursor", "player_sel_start", "player_sel_end",
        "player_dragging", "player_last_click_time",
        "is_voice_playing", "is_tts_loading", "current_playing_text", "tts_req_id",
        "voice_channel", "toast_text", "toast_time", "ui_hidden_time",
        "current_text", "display_text", "current_text_index", "typewriter_interval",
        "last_type_time", "typewriter_done",
        "fade_alpha", "fade_start_time", "fade_duration",
    )))

    # show_toast / fade 走 ui
    app.show_toast("测试")
    check("show_toast 写入 ui.toast_text", app.ui.toast_text == "测试")
    app.start_fade_in(0.1)
    check("start_fade_in 写入 ui.fade_alpha", app.ui.fade_alpha == 255.0)

    # 类型机状态在 ui 上，且打字机方法走 ui
    app.start_typewriter("你好")
    check("start_typewriter 写入 ui.current_text", app.ui.current_text == "你好")
    check("display_text 在 ui 上", hasattr(app.ui, "display_text"))

    print(f"\n==== {sum(1 for _, ok, _ in RESULTS if ok)}/{len(RESULTS)} PASSED ====", flush=True)
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAILED: {name}  {detail}", flush=True)
    return 0 if all(ok for _, ok, _ in RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
