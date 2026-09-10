# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("corpus/moxiaoju_qiucheng_dialogues.jsonl", "r", encoding="utf-8") as f:
    convs = [json.loads(line) for line in f]

# Find chapter 5m serious scenes
for c in convs:
    chap = c[0]["chapter"]
    scene = c[0]["scene"]
    if "chapter5m" in chap and any("喜欢" in m["text"] or "害怕" in m["text"] or "对不起" in m["text"] for m in c):
        print(f"=== [{chap} / {scene}] ===")
        for m in c:
            if "墨小菊" in m["speaker"]:
                print(f"  【小菊】: {m['text']}")
        print("=" * 60)
        break
