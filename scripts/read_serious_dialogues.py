# -*- coding: utf-8 -*-
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("corpus/moxiaoju_qiucheng_dialogues.jsonl", "r", encoding="utf-8") as f:
    convs = [json.loads(line) for line in f]

# Find specific serious conversations
target_keywords = ["原谅", "不甘心", "邱诚", "我喜欢你", "真诚", "绝交", "抱", "为什么"]

found = 0
for c in convs:
    text_corpus = " ".join(m["text"] for m in c)
    chap = c[0]["chapter"]
    scene = c[0]["scene"]
    if ("chapter4" in chap or "chapter5m" in chap or "chapter3" in chap) and any(k in text_corpus for k in ["不甘心", "原谅我", "绝交", "喜欢你", "瞒着我"]):
        print(f"=== [{chap} / {scene}] ({len(c)} turns) ===")
        for m in c:
            if "墨小菊" in m["speaker"] and len(m["text"]) > 10:
                print(f"  【{m['speaker']}】: {m['text']}")
        print("-" * 50)
        found += 1
        if found >= 5:
            break
