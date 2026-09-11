# -*- coding: utf-8 -*-
"""ModalShell 组合重构的冒烟测试：确认两个弹窗行为与几何不变。"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame
pygame.init()

from daisymo_widgets import ConfirmDialog, InputDialog, ModalShell  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""), flush=True)


def main():
    surf = pygame.display.set_mode((1280, 720))

    # ConfirmDialog 几何不变：460x210，按钮 y 与中心
    cd = ConfirmDialog()
    check("ConfirmDialog 默认尺寸", (cd.shell.width, cd.shell.height) == (460, 210))
    check("ConfirmDialog 确认键中心", cd.rect_confirm.center == (745, 425),
          f"{cd.rect_confirm.center}")
    check("ConfirmDialog 取消键中心", cd.rect_cancel.center == (535, 425),
          f"{cd.rect_cancel.center}")

    # InputDialog 几何不变：520x250
    idlg = InputDialog()
    check("InputDialog 默认尺寸", (idlg.shell.width, idlg.shell.height) == (520, 250))

    # 开合与 action_context 转发
    cd.open(title="测试", sub1="a", context=("x", 1))
    check("ConfirmDialog 打开", cd.is_open)
    check("action_context 透传", cd.action_context == ("x", 1))

    # 空值校验：InputDialog 回车确认被拦
    idlg.open(title="重命名", default_text="", context=("rename", "id"))
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0, "unicode": ""})
    res = idlg.handle_event(ev, 640, 360)
    check("InputDialog 空值回车被拦", res == "block" and idlg.is_open and idlg.error_text == "名称不能为空",
          f"res={res} err={idlg.error_text}")

    # 有值时回车确认
    idlg.box.text = "新名字"
    res = idlg.handle_event(ev, 640, 360)
    check("InputDialog 有值回车确认", res == "confirm" and not idlg.is_open)

    # render 不抛异常（冒烟）
    cd.open(title="渲染测试")
    cd.render(surf, 640, 360)
    idlg.open(title="渲染测试2")
    idlg.render(surf, 640, 360)
    check("两个弹窗 render 无异常", True)

    # ModalShell 独立可用
    ms = ModalShell(title="独立外壳", width=460, height=210)
    ms.open()
    ms.render_frame(surf, 640, 360)
    check("ModalShell 独立 render_frame 无异常", True)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n==== {passed}/{total} PASSED ====", flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
