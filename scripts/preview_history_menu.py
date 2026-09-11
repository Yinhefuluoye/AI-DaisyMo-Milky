# -*- coding: utf-8 -*-
"""
离屏渲染回忆界面三个分栏与命名弹窗的预览图。
只写系统临时目录，绝不触碰用户真实存档。

产出（写到项目根目录）：
  preview_history_tab.png    历史分栏（22 轮对话，走脏标记缓存渲染）
  preview_backups_tab.png    分支存档分栏（含同名自动快照去重效果）
  preview_rename_dialog.png  重命名输入弹窗
"""
import os, sys, json, shutil, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame; pygame.init()

TMP = tempfile.mkdtemp(prefix="preview_")
import daisymo_history_manager as hm
hm.BACKUP_DIR = os.path.join(TMP, "hb")
hm.TRASH_DIR = os.path.join(hm.BACKUP_DIR, ".trash")
hm.invalidate_cache()


def msg(rounds, where="中山公园", face="温柔-笑", body="便服单叉腰"):
    mem = []
    lines = [
        ("今天去哪玩？", "去中山公园看樱花怎么样？"),
        ("你上课认真点", "人家有在认真听邱诚讲话啦"),
        ("晚上吃什么", "邱诚做的番茄炒蛋最香了"),
        ("明天还来吗", "当然要来呀，说好了的事小菊从不反悔"),
    ]
    for i in range(rounds):
        u, d = lines[i % len(lines)]
        mem.append({"role": "user", "content": u})
        mem.append({"role": "assistant", "content": json.dumps(
            {"where": where, "face": face, "body": body, "text": d}, ensure_ascii=False)})
    return mem


# 自动快照连造 3 次、标题相同 —— 去重后只应留下 1 条
for _ in range(3):
    hm.create_backup(msg(22), is_auto=True)
hm.create_backup(msg(22), title="中山公园赏樱")
hm.create_backup(msg(11), title="放学后的教室")
print("backups after dedupe =", [b["title"] for b in hm.list_backups()], flush=True)

from DaisyMo import Screen, DaisyMo
app = Screen()
app.conversation.clear()
app.conversation.replace_with(msg(22))

OUT = ROOT


def frame(mouse, *ev):
    return (mouse, list(ev))


def btn():
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (0, 0)})


SCRIPT = [
    frame((0, 0)),                 # 0 渲染历史分栏
    frame((407, 57), btn()),       # 1 切到分支存档
    frame((0, 0)),                 # 2
    frame((817, 133), btn()),      # 3 点首卡[改名] -> 弹窗
    frame((0, 0)),                 # 4
    frame((1203, 663), btn()),     # 5 返回退出
]

# 探针在「取下一帧事件之前」执行，此时屏幕上是最新一轮已 flip 完的画面。
# 切标签那一帧正文仍属于旧标签（渲染早于事件处理），所以分支存档要取再下一帧。
SAVES = {
    1: ("preview_history_tab.png", "历史分栏（22 轮）"),
    3: ("preview_backups_tab.png", "分支存档分栏"),
    4: ("preview_rename_dialog.png", "重命名弹窗"),
}

state = {"i": 0, "mouse": SCRIPT[0][0]}
orig_get, orig_pos, orig_exit = pygame.event.get, pygame.mouse.get_pos, Screen.exit


def fake_get(*a, **k):
    orig_get()
    i = state["i"]; state["i"] = i + 1
    if i in SAVES:
        name, label = SAVES[i]
        pygame.image.save(app.screen, os.path.join(OUT, name))
        print(f"saved {name}  <- {label}", flush=True)
    mouse, events = SCRIPT[i] if i < len(SCRIPT) else ((0, 0), [])
    state["mouse"] = SCRIPT[i + 1][0] if i + 1 < len(SCRIPT) else (0, 0)
    return list(events)


pygame.event.get = fake_get
pygame.mouse.get_pos = lambda: state["mouse"]
Screen.exit = lambda self: None
app.history_menu()
pygame.event.get, pygame.mouse.get_pos, Screen.exit = orig_get, orig_pos, orig_exit

shutil.rmtree(TMP, ignore_errors=True)
print("done ->", OUT, flush=True)
