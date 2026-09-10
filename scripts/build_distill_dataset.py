# -*- coding: utf-8 -*-
"""
将提取的 654 组对白与 6,397 句墨小菊原案台词，转化为用于大模型微调与知识蒸馏的标准训练数据集。
支持两种业界通用格式：
1. ShareGPT 格式 (多轮对话格式，适用于 LLaMA-Factory, Axolotl, Swift)
2. Alpaca 格式 (单轮/问答指令微调格式)
"""

import os
import json
import re

SYSTEM_PROMPT = """你是墨小菊，17岁高二女生，留着琥珀色双马尾，邱诚的青梅竹马。
性格傲娇要强，自诩为邱诚的姐姐，有强烈的保护欲和依赖感。
三个月前因画集被烧而宣布单方面绝交，表面冷淡挖苦，但内心极在乎对方。
绝对零容忍谎言，擅长电脑修图与游戏，极爱新鲜番茄与红烧肉，厌恶番茄酱。
说话多用省略号（……），常带“……啊”、“……吧”、“……啦”、“嘛”，称邱诚为笨蛋。
请以JSON格式输出：
{"where": "场景", "face": "表情", "body": "动作", "text": "话语", "bgm": "", "sfx": ""}"""

# 映射表情到游戏项目现有的白名单表情
FACE_MAPPING = {
    "f111": "狡猾-说",
    "f115": "狡猾-笑",
    "f122": "笑-说",
    "f155": "害羞-说",
    "f162": "温柔-说",
    "f175": "温柔-轻笑",
    "f315": "闭眼-笑-说",
    "f335": "担心-笑",
    "f338": "害羞-流泪-笑",
    "f411": "狡猾-说",
    "f412": "笑-说",
    "f415": "狡猾-说",
    "f416": "笑-说",
    "f422": "害羞-说",
    "f455": "闭眼-笑-说",
    "f471": "害羞-说",
    "f475": "闭眼-笑-说",
}

BODY_MAPPING = {
    "pose1": "便服单叉腰",
    "pose2": "便服双叉腰",
    "pose3": "校服单叉腰",
}

def map_face(face_code):
    return FACE_MAPPING.get(face_code, "狡猾-说")

def map_body(pose_code):
    return BODY_MAPPING.get(pose_code, "便服单叉腰")

def build_distillation_datasets():
    input_file = "corpus/moxiaoju_qiucheng_dialogues.jsonl"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found!")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        conversations = [json.loads(line) for line in f]

    sharegpt_data = []
    alpaca_data = []

    for conv_idx, conv in enumerate(conversations):
        # 过滤出适合训练的多轮对话：必须由邱诚提问/说话，小菊回答
        messages = []
        i = 0
        while i < len(conv):
            msg = conv[i]
            speaker = msg["speaker"]
            text = msg["text"].strip()
            if not text:
                i += 1
                continue

            if "邱诚" in speaker:
                messages.append({"role": "user", "content": text})
            elif "墨小菊" in speaker:
                # 构造小菊的标准 JSON 输出
                face_val = map_face(msg.get("face", ""))
                body_val = map_body(msg.get("pose", ""))
                output_obj = {
                    "where": "学校走廊白天" if "chapter1" in msg.get("chapter", "") else "小区下午",
                    "face": face_val,
                    "body": body_val,
                    "text": text,
                    "bgm": "",
                    "sfx": ""
                }
                messages.append({"role": "assistant", "content": json.dumps(output_obj, ensure_ascii=False)})
            i += 1

        # 确保以 user 开始，以 assistant 结束，且包含至少一对问答
        clean_turns = []
        for m in messages:
            if not clean_turns:
                if m["role"] == "user":
                    clean_turns.append(m)
            else:
                if m["role"] != clean_turns[-1]["role"]:
                    clean_turns.append(m)
                else:
                    # 合并同角色连续发言
                    if m["role"] == "user":
                        clean_turns[-1]["content"] += "\n" + m["content"]
                    else:
                        # assistant如果是json，只保留最新或者合并话语
                        try:
                            prev_json = json.loads(clean_turns[-1]["content"])
                            curr_json = json.loads(m["content"])
                            prev_json["text"] += " " + curr_json["text"]
                            clean_turns[-1]["content"] = json.dumps(prev_json, ensure_ascii=False)
                        except:
                            clean_turns[-1]["content"] += " " + m["content"]

        if clean_turns and clean_turns[-1]["role"] == "user":
            clean_turns.pop()

        if len(clean_turns) >= 2:
            # 1. ShareGPT item
            sharegpt_item = {
                "id": f"daisymo_conv_{conv_idx+1:04d}",
                "system": SYSTEM_PROMPT,
                "conversations": [
                    {"from": "human" if t["role"] == "user" else "gpt", "value": t["content"]}
                    for t in clean_turns
                ]
            }
            sharegpt_data.append(sharegpt_item)

            # 2. Alpaca pairs (每对问答拆分一个独立指令样本)
            history = []
            for t_idx in range(0, len(clean_turns), 2):
                u_msg = clean_turns[t_idx]["content"]
                if t_idx + 1 < len(clean_turns):
                    a_msg = clean_turns[t_idx + 1]["content"]
                    alpaca_item = {
                        "instruction": "请以墨小菊的身份与邱诚对话，遵守性格设定并以指定JSON格式输出。",
                        "input": u_msg,
                        "output": a_msg,
                        "history": list(history)
                    }
                    alpaca_data.append(alpaca_item)
                    history.append([u_msg, a_msg])

    os.makedirs("dataset", exist_ok=True)

    sharegpt_path = "dataset/daisymo_distill_sharegpt.json"
    alpaca_path = "dataset/daisymo_distill_alpaca.json"

    with open(sharegpt_path, "w", encoding="utf-8") as f:
        json.dump(sharegpt_data, f, ensure_ascii=False, indent=2)

    with open(alpaca_path, "w", encoding="utf-8") as f:
        json.dump(alpaca_data, f, ensure_ascii=False, indent=2)

    print(f"Distillation dataset generation complete!")
    print(f"- ShareGPT format: {len(sharegpt_data)} multi-turn conversations -> {sharegpt_path}")
    print(f"- Alpaca format: {len(alpaca_data)} instruction-response pairs -> {alpaca_path}")

if __name__ == "__main__":
    build_distillation_datasets()
