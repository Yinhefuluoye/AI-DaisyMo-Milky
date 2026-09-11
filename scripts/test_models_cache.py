# -*- coding: utf-8 -*-
"""模型列表静默刷新与缓存的回归测试。不碰网络、不碰真实 assets。"""
import os
import sys
import time
import tempfile
import shutil

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import pygame
pygame.init()

import DaisyMo as daisy_module  # noqa: E402
from DaisyMo import DaisyMo  # noqa: E402
from daisymo_ai import AI_PROVIDERS  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(("  [PASS] " if cond else "  [FAIL] ") + name + (("  -> " + detail) if detail else ""), flush=True)


FAKE_MODELS = ["fake-model-a", "fake-model-b", "fake-model-c"]


def main():
    tmp = tempfile.mkdtemp(prefix="models_cache_")
    try:
        # 缓存路径指到临时目录，测试不污染真实 assets
        DaisyMo.models_cache_path = os.path.join(tmp, "fetched_models.json")
        prov = (DaisyMo.provider or "deepseek").strip().lower()
        if prov not in AI_PROVIDERS:
            prov = "deepseek"
        DaisyMo.provider = prov

        original_models = list(AI_PROVIDERS[prov]["models"])

        # 1. 静默刷新：mock fetch（patch 模块全局，worker 闭包引用的是它），线程跑完后更新预设 + 写缓存
        DaisyMo.api_key = "test-key"
        daisy_module.ai_fetch_models = lambda url, key, provider="", timeout=12: (True, FAKE_MODELS, "ok")
        DaisyMo.silent_refresh_models()

        deadline = time.time() + 3
        while time.time() < deadline and not os.path.exists(DaisyMo.models_cache_path):
            time.sleep(0.05)

        check("刷新后预设列表被更新", AI_PROVIDERS[prov]["models"] == FAKE_MODELS,
              f"models={AI_PROVIDERS[prov]['models'][:2]}...")
        check("缓存文件已写出", os.path.exists(DaisyMo.models_cache_path))

        # 2. 重启语义：把预设改回硬编码值，再 load_models_cache 应从缓存恢复
        AI_PROVIDERS[prov]["models"] = list(original_models)
        DaisyMo.load_models_cache()
        check("重启后从缓存恢复列表", AI_PROVIDERS[prov]["models"] == FAKE_MODELS,
              f"models={AI_PROVIDERS[prov]['models'][:2]}...")

        # 3. 无 Key 时静默刷新不动作
        if os.path.exists(DaisyMo.models_cache_path):
            os.remove(DaisyMo.models_cache_path)
        DaisyMo.api_key = ""
        DaisyMo.silent_refresh_models()
        time.sleep(0.3)
        check("无 Key 时不拉取不写缓存", not os.path.exists(DaisyMo.models_cache_path))

        # 4. 拉取失败静默：缓存不写、预设不动
        DaisyMo.api_key = "test-key"
        daisy_module.ai_fetch_models = lambda url, key, provider="", timeout=12: (False, [], "error")
        AI_PROVIDERS[prov]["models"] = list(original_models)
        DaisyMo.silent_refresh_models()
        time.sleep(0.3)
        check("拉取失败时缓存不写出", not os.path.exists(DaisyMo.models_cache_path))
        check("拉取失败时预设保持原样", AI_PROVIDERS[prov]["models"] == original_models)

        passed = sum(1 for _, ok, _ in RESULTS if ok)
        total = len(RESULTS)
        print(f"\n==== {passed}/{total} PASSED ====", flush=True)
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  FAILED: {name}  {detail}", flush=True)
        return 0 if passed == total else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
