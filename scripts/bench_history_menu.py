# -*- coding: utf-8 -*-
"""量化 history_menu 每帧耗时，定位「点 log 很卡 / 切标签很卡」的瓶颈。只读，不写真实存档。"""
import os, sys, json, time, shutil, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame; pygame.init()

TMP = tempfile.mkdtemp(prefix="bench_")
import daisymo_history_manager as hm
hm.BACKUP_DIR = os.path.join(TMP, "hb")
hm.TRASH_DIR = os.path.join(hm.BACKUP_DIR, ".trash")
hm.invalidate_cache()

ROUNDS = 22  # 与用户截图里的「22 轮对话」对齐

def build_memory(rounds):
    mem = []
    for i in range(rounds):
        mem.append({"role": "user", "content": f"第{i}轮的邱诚台词，随便说点什么。"})
        mem.append({"role": "assistant", "content": json.dumps(
            {"where": "江汉路", "face": "温柔-笑", "body": "便服单叉腰",
             "text": f"第{i}轮小菊的回复，长度大概和真实对白接近，用来测试换行与渲染开销。"},
            ensure_ascii=False)})
    return mem

for _ in range(5):
    hm.create_backup(build_memory(ROUNDS), title="切换分支前自动快照", is_auto=True)
hm.create_backup(build_memory(ROUNDS), title="江汉路周边游")

from DaisyMo import Screen, DaisyMo
app = Screen()
app.conversation.clear()
app.conversation.replace_with(build_memory(ROUNDS))
print(f"memory rounds = {ROUNDS}, backups = {len(hm.list_backups())}", flush=True)

def frame(mouse, *ev):
    return (mouse, list(ev))

def btn():
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (0, 0)})

# 每个标签页各停留 20 帧，测稳态每帧耗时
SCRIPT = []
SCRIPT += [frame((0, 0))] * 20                       # 0..19   历史标签
SCRIPT += [frame((407, 57), btn())] + [frame((0, 0))] * 20   # 20 切分支存档, 21..41
SCRIPT += [frame((265, 57), btn())] + [frame((0, 0))] * 20   # 42 切珍藏, 43..63
SCRIPT += [frame((1203, 663), btn())]                        # 64 返回

def run_session(uncapped: bool):
    """跑一遍完整帧脚本，返回 (每帧耗时 ms 列表, 进入界面总耗时 ms)"""
    state = {"i": 0, "mouse": SCRIPT[0][0]}
    stamps = []
    orig_get, orig_pos, orig_exit = pygame.event.get, pygame.mouse.get_pos, Screen.exit
    orig_clock = pygame.time.Clock

    def fake_get(*a, **k):
        orig_get()
        stamps.append(time.perf_counter())
        i = state["i"]; state["i"] = i + 1
        mouse, events = SCRIPT[i] if i < len(SCRIPT) else ((0, 0), [])
        state["mouse"] = SCRIPT[i + 1][0] if i + 1 < len(SCRIPT) else (0, 0)
        return list(events)

    pygame.event.get = fake_get
    pygame.mouse.get_pos = lambda: state["mouse"]
    Screen.exit = lambda self: None
    if uncapped:
        # 去掉 30fps 锁帧，量真实 CPU 开销（否则 33.3ms 只是 sleep 出来的）
        class _NoTickClock:
            def __init__(self, *a, **k):
                pass

            def tick(self, *a, **k):
                return 0

            def get_fps(self):
                return 0.0

        pygame.time.Clock = _NoTickClock

    t0 = time.perf_counter()
    app.history_menu()
    total = time.perf_counter() - t0

    pygame.event.get, pygame.mouse.get_pos, Screen.exit = orig_get, orig_pos, orig_exit
    pygame.time.Clock = orig_clock
    deltas = [round((stamps[i+1]-stamps[i])*1000, 1) for i in range(len(stamps)-1)]
    return deltas, total * 1000


def report(title, deltas, total):
    def seg(name, a, b):
        xs = deltas[a:b]
        if not xs:
            return
        avg = sum(xs) / len(xs)
        print(f"  {name:<16} frames={len(xs):>3}  avg={avg:>7.1f} ms  max={max(xs):>7.1f} ms  -> {1000/avg:>6.1f} fps", flush=True)

    print(f"\n===== {title} =====", flush=True)
    print(f"  进入界面总耗时 = {total:.0f} ms / {len(deltas)+1} 帧", flush=True)
    seg("历史 tab", 1, 20)
    seg("切标签那一帧", 20, 21)
    seg("分支存档 tab", 21, 42)
    seg("珍藏 tab", 43, 63)
    print(f"  历史 tab 明细: {deltas[:6]}", flush=True)


capped, capped_total = run_session(uncapped=False)
uncapped, uncapped_total = run_session(uncapped=True)
report("锁帧 30fps（实际观感）", capped, capped_total)
report("不锁帧（真实 CPU 开销）", uncapped, uncapped_total)

shutil.rmtree(TMP, ignore_errors=True)
