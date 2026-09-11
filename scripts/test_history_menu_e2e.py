# -*- coding: utf-8 -*-
"""
回忆界面（history_menu）端到端回归测试 —— headless，全程不触碰真实存档。

覆盖：
1. 进入回忆界面不再崩溃（Any 未导入的 NameError 回归）
2. 新建备份走命名弹窗，自定义名称生效
3. 卡片[改名]按钮 + 命名弹窗，重命名生效
4. 载入分支的二次确认真正执行（ConfirmDialog 的 action_context 被 close() 清空后失效的回归）
5. 载入分支后自动关闭回忆界面（不再需要手点返回）
6. 删除备份为软删除，文件进入 .trash
7. 清空记录前自动快照并原地清空
8. 脏标记 + 缓存：同一标签页重复渲染不再重建正文
9. 数据层边界：同名自动快照只留一条、纯开场白不留快照、空名回退、超长截断、同秒不覆盖

运行：
  .venv\\Scripts\\python.exe scripts\\test_history_menu_e2e.py
"""

import os
import sys
import json
import shutil
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
pygame.init()

# 把所有磁盘写入重定向到临时目录，绝不污染用户真实存档
TMP = tempfile.mkdtemp(prefix="daisymo_e2e_")
TMP_HISTORY = os.path.join(TMP, "DaisyMo_history.json")

import daisymo_history_manager as hm

hm.BACKUP_DIR = os.path.join(TMP, "history_backups")
hm.TRASH_DIR = os.path.join(hm.BACKUP_DIR, ".trash")
hm.invalidate_cache()

_orig_clear = hm.clear_active_history
_orig_save = hm.save_active_history


def _clear_redirected(memory_ref, history_file_path=TMP_HISTORY):
    return _orig_clear(memory_ref, TMP_HISTORY)


def _save_redirected(memory_ref, history_file_path=TMP_HISTORY):
    return _orig_save(memory_ref, TMP_HISTORY)


hm.clear_active_history = _clear_redirected
hm.save_active_history = _save_redirected

from DaisyMo import Screen, DaisyMo  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""), flush=True)


def make_mem(rounds, tag="主线"):
    """构造 rounds 轮完整对话；用 tag 标记，便于确认载入的是哪一条时间线"""
    mem = []
    for i in range(rounds):
        mem.append({"role": "user", "content": f"[{tag}] 第{i + 1}轮邱诚的台词"})
        mem.append({"role": "assistant", "content": json.dumps(
            {"where": "江汉路", "face": "温柔-笑", "body": "便服单叉腰",
             "text": f"[{tag}] 第{i + 1}轮小菊的回复，长度接近真实对白。"},
            ensure_ascii=False)})
    return mem


def assistant_texts(memory):
    out = []
    for m in memory:
        if m.get("role") == "assistant":
            try:
                out.append(json.loads(m["content"]).get("text", ""))
            except Exception:
                out.append(m.get("content", ""))
    return out


# ------------------------------------------------------------------ 帧脚本
def frame(mouse, *events):
    return (mouse, list(events))


def btn(button=1, x=0, y=0):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": button, "pos": (x, y)})


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, {"key": k, "mod": 0, "unicode": ""})


def text(t):
    return pygame.event.Event(pygame.TEXTINPUT, {"text": t})


# 关键坐标（与 DaisyMo.py 中的几何常量一一对应）
TAB_BACKUP = (407, 57)       # rect_tab_backup      (350,42,115,30)
TAB_HIST = (199, 57)         # rect_tab_hist        (165,42,68,30)
BTN_NEW = (982, 57)          # rect_btn_new_backup  (930,42,105,30)
BTN_CLEAR = (990, 57)        # rect_btn_clear       (945,42,90,30)
BTN_BACK = (1203, 663)       # rect_back            (1165,625,76,76)
CARD0_RENAME = (817, 133)    # 第 0 张卡 paper(220,80)+card_x10+552, y=80+12+24+17
CARD0_DEL = (995, 133)       # 220 + 10 + 730 + 35
DLG_CONFIRM = (745, 425)     # ConfirmDialog rect_confirm 中心

# 第 n 张卡片按钮中心：y = 80 + 12 + 94*n + 24 + 17
CARD_ROW_Y = lambda n: 133 + 94 * n          # noqa: E731
CARD_LOAD_X = 906                            # 220 + 10 + 632 + 44


def build_script_load(load_card_index: int):
    """载入分支那一帧的目标卡片序号必须按真实列表顺序算，不能写死"""
    return [
        frame((0, 0)),                                       # 0
        frame(TAB_BACKUP, btn()),                            # 1
        frame(BTN_NEW, btn()),                               # 2
        frame((640, 360), text("_E2E_测试分支")),             # 3
        frame((640, 360), key(pygame.K_RETURN)),             # 4  建备份
        frame(CARD0_RENAME, btn()),                          # 5
        frame((640, 360), key(pygame.K_BACKSPACE)),          # 6
        frame((640, 360), text("_E2E_改名后")),              # 7
        frame((640, 360), key(pygame.K_RETURN)),             # 8  重命名
        frame((CARD_LOAD_X, CARD_ROW_Y(load_card_index)), btn()),   # 9  打开载入确认
        frame(DLG_CONFIRM, btn()),                           # 10 确认载入 -> 应自动退出
        frame((0, 0)),                                       # 11 空转探测帧
        frame((0, 0)),                                       # 12
        frame(BTN_BACK, btn()),                              # 13 不该被消费
    ]

# 第二轮：软删除 + 清空记录
SCRIPT_CLEAN = [
    frame((0, 0)),                                       # 0
    frame(TAB_BACKUP, btn()),                            # 1
    frame(CARD0_DEL, btn()),                             # 2
    frame(DLG_CONFIRM, btn()),                           # 3  确认删除
    frame(TAB_HIST, btn()),                              # 4
    frame(BTN_CLEAR, btn()),                             # 5
    frame(DLG_CONFIRM, btn()),                           # 6  确认清空
    frame(BTN_BACK, btn()),                              # 7  返回
]

SNAPSHOT = {}
PROBES = {}


def run_menu(app, script, probes=None, max_label=""):
    """注入帧脚本驱动一次 history_menu，返回 (消耗帧数, 异常)"""
    state = {"i": 0, "mouse": script[0][0]}
    orig_get, orig_pos, orig_exit = pygame.event.get, pygame.mouse.get_pos, Screen.exit
    trace = []

    def fake_get(*_a, **_kw):
        orig_get()
        i = state["i"]
        state["i"] = i + 1
        if probes and i in probes:
            probes[i]()
        mouse, events = script[i] if i < len(script) else ((0, 0), [])
        # 下一轮 get_pos() 用的坐标必须提前写入（循环是先读鼠标再取事件）
        state["mouse"] = script[i + 1][0] if i + 1 < len(script) else (0, 0)
        trace.append((i, mouse, [e.type for e in events], len(hm.list_backups())))
        return list(events)

    pygame.event.get = fake_get
    pygame.mouse.get_pos = lambda: state["mouse"]
    Screen.exit = lambda self: None
    err = None
    try:
        app.history_menu()
    except Exception:
        err = traceback.format_exc()
    finally:
        pygame.event.get, pygame.mouse.get_pos, Screen.exit = orig_get, orig_pos, orig_exit

    print(f"  -- {max_label} 消耗 {state['i']} 帧 --", flush=True)
    for i, mouse, types, nb in trace:
        print(f"     frame {i:>2} mouse={mouse} ev={types} backups={nb}", flush=True)
    return state["i"], err


def main():
    print("[setup] temp dir =", TMP, flush=True)

    DaisyMo.load_favorites()
    DaisyMo.favorites.clear()   # 清空珍藏，保证珍藏页断言不受本地数据干扰

    # 预置：一个普通分支（标记「旧分支」）+ 一个够长的自动快照
    hm.create_backup(make_mem(3, "旧分支"), is_auto=False, title="_E2E_旧分支")
    hm.create_backup(make_mem(3, "自动快照"), is_auto=True)
    print("[setup] seeded =", [b["title"] for b in hm.list_backups()], flush=True)

    app = Screen()
    app.conversation.clear()
    app.conversation.replace_with(make_mem(3, "主线"))
    print("[setup] active rounds =", len(app.conversation), flush=True)

    # ---- 数据层：同名自动快照只留一条 ----
    hm.create_backup(make_mem(3, "dup"), is_auto=True, title="_E2E_同名快照")
    first_id = hm.find_auto_backup_id("_E2E_同名快照")
    hm.create_backup(make_mem(3, "dup2"), is_auto=True, title="_E2E_同名快照")
    same = [b for b in hm.list_backups() if b["title"] == "_E2E_同名快照"]
    check("同名自动快照只保留一条", len(same) == 1, f"{len(same)} 条")
    check("同名自动快照复用原 backup_id", same and same[0]["backup_id"] == first_id,
          f"{first_id} -> {same[0]['backup_id'] if same else None}")

    # ---- 数据层：纯开场白不留自动快照 ----
    check("纯开场白（1 轮）不生成自动快照",
          hm.create_backup(make_mem(1, "开场白"), is_auto=True) is None)
    check("手动分支不受轮数门槛限制",
          hm.create_backup(make_mem(1, "短分支"), is_auto=False, title="_E2E_短分支") is not None)

    # ---- 缓存：停在历史页时不得再有任何折行计算 ----
    wrap_calls = {"n": 0}
    _orig_wrap = Screen.wrap_text

    def _counting_wrap(self, font, text, max_width):
        wrap_calls["n"] += 1
        return _orig_wrap(self, font, text, max_width)

    Screen.wrap_text = _counting_wrap

    # ---- 第一轮：新建 / 改名 / 载入分支 ----
    print("\n[run 1] 新建命名 + 改名 + 载入分支 ...", flush=True)

    def probe_after_create():
        SNAPSHOT["titles_after_create"] = [b["title"] for b in hm.list_backups()]

    # 载入目标卡片序号：新建的「测试分支」会插到列表最前，其余整体后移一位
    order_before = [b["title"] for b in hm.list_backups()]
    load_card_index = order_before.index("_E2E_旧分支") + 1
    SCRIPT_LOAD = build_script_load(load_card_index)
    print(f"[setup] 载入目标卡片序号 = {load_card_index}，y = {CARD_ROW_Y(load_card_index)}", flush=True)

    # 注意：载入成功会立刻置 running=False 退出，脚本不会再有下一帧的 get()，
    # 所以「载入后的内存状态」只能等 history_menu 返回后再读，不能用帧探针。
    frames1, err1 = run_menu(
        app, SCRIPT_LOAD,
        probes={5: probe_after_create},
        max_label="run1"
    )
    check("history_menu 全程无异常", err1 is None, err1 or "")
    check("载入分支后自动关闭回忆界面（脚本后半段未被消费）",
          frames1 <= 12, f"消耗 {frames1} 帧（脚本共 {len(SCRIPT_LOAD)} 帧）")

    titles_after_create = SNAPSHOT.get("titles_after_create", [])
    check("新建备份使用自定义名称", "_E2E_测试分支" in titles_after_create, str(titles_after_create))

    final_titles = [b["title"] for b in hm.list_backups()]
    check("卡片[改名]生效",
          "_E2E_改名后" in final_titles and "_E2E_测试分支" not in final_titles, str(final_titles))

    texts = assistant_texts(app.conversation.messages())
    check("确认弹窗真正执行了「载入分支」（action_context 回归）",
          any("[旧分支]" in t for t in texts), f"载入后对白={texts[:2]}")

    check("载入分支后自动快照已去重（同名只一条）",
          len([b for b in hm.list_backups() if b["title"] == "切换分支前自动快照"]) <= 1)

    # ---- 第三轮：全程停在历史页，验证脏标记缓存真的生效 ----
    print("\n[run 3] 停留历史页 16 帧，统计折行次数 ...", flush=True)
    SCRIPT_STAY = [frame((0, 0))] * 16 + [frame(BTN_BACK, btn())]
    wrap_at = {}

    def probe_start():
        wrap_at["start"] = wrap_calls["n"]

    frames3, err3 = run_menu(app, SCRIPT_STAY, probes={1: probe_start}, max_label="run3")
    wrap_during = wrap_calls["n"] - wrap_at.get("start", 0)
    check("第三轮无异常", err3 is None, err3 or "")
    check("停在历史页 16 帧期间零次折行计算（正文已缓存）", wrap_during == 0,
          f"{wrap_during} 次")

    Screen.wrap_text = _orig_wrap

    # ---- 第二轮：软删除 + 清空 ----
    print("\n[run 2] 删除备份 + 清空记录 ...", flush=True)
    frames2, err2 = run_menu(app, SCRIPT_CLEAN, max_label="run2")
    check("第二轮 history_menu 无异常", err2 is None, err2 or "")

    trash_files = os.listdir(hm.TRASH_DIR) if os.path.isdir(hm.TRASH_DIR) else []
    check("删除为软删除（.trash 中留有存档）", len(trash_files) >= 1, str(trash_files))
    check("清空记录后活跃对话被清空", len(app.conversation) == 0, f"len={len(app.conversation)}")
    auto_titles = [b["title"] for b in hm.list_backups() if b.get("is_auto_backup")]
    check("清空前生成了自动安全快照", "清空前自动安全快照" in auto_titles, str(auto_titles))

    # ---- 数据层其它边界 ----
    rec_long = hm.create_backup(make_mem(3), is_auto=False, title="很长的名字" * 10)
    check("超长名称被规整截断",
          rec_long is not None and len(rec_long["title"]) <= hm.TITLE_MAX_LEN,
          f"{len(rec_long['title']) if rec_long else -1} 字")

    rec_blank = hm.create_backup(make_mem(3), is_auto=False, title="   ")
    check("空白名称回退为默认标题",
          rec_blank is not None and rec_blank["title"].startswith("分支存档_"),
          rec_blank["title"] if rec_blank else "None")

    r3 = hm.create_backup(make_mem(3), is_auto=False, title="dup-a")
    r4 = hm.create_backup(make_mem(3), is_auto=False, title="dup-b")
    check("同一秒内两次备份不会互相覆盖",
          bool(r3 and r4) and r3["backup_id"] != r4["backup_id"],
          f"{r3['backup_id'] if r3 else None} / {r4['backup_id'] if r4 else None}")

    ok_empty, msg_empty = hm.rename_backup(r3["backup_id"], "   ")
    check("rename 拒绝空名称", (not ok_empty) and msg_empty == "名称不能为空", msg_empty)

    ok_missing, msg_missing = hm.rename_backup("__not_exist__", "abc")
    check("rename 正确处理不存在的存档", not ok_missing, msg_missing)

    ok_rename, _ = hm.rename_backup(r4["backup_id"], "重命名成功")
    after = {b["backup_id"]: b["title"] for b in hm.list_backups()}
    check("rename 正常路径生效", ok_rename and after.get(r4["backup_id"]) == "重命名成功",
          str(after.get(r4["backup_id"])))

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n==== {passed}/{total} PASSED ====", flush=True)
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAILED: {name}  {detail}", flush=True)

    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
