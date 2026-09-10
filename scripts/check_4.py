# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("corpus/moxiaoju_qiucheng_dialogues.jsonl", "r", encoding="utf-8") as f:
    convs = [json.loads(line) for line in f]

for c in convs:
    chap = c[0]["chapter"]
    scene = c[0]["scene"]
    if "chapter4" in chap and any(k in m["text"] for m in c for k in ["骗我", "画集", "自私", "难过"]):
        print(f"=== [{chap} / {scene}] ===")
        for m in c:
            if "墨小菊" in m["speaker"]:
                print(f"  【小菊】: {m['text']}")
        print("=" * 60)
        break
