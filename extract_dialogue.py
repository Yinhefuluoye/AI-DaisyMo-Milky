# -*- coding: utf-8 -*-
import os
import glob
import re
import json

scenario_dir = r"Scenario Data/scenario"
output_dir = r"corpus"
os.makedirs(output_dir, exist_ok=True)

all_mxj_lines = []
conversations = []  # paired dialogues with Qiu Cheng

for chapter_dir in sorted(glob.glob(os.path.join(scenario_dir, "*"))):
    if not os.path.isdir(chapter_dir):
        continue
    chapter_name = os.path.basename(chapter_dir)
    ks_files = sorted(glob.glob(os.path.join(chapter_dir, "*.ks")))
    for ks_file in ks_files:
        scene_name = os.path.splitext(os.path.basename(ks_file))[0]
        with open(ks_file, "r", encoding="utf-16-le", errors="ignore") as f:
            lines = f.readlines()
        
        current_pose = ""
        current_face = ""
        current_voice = ""
        dialog_buffer = []  # list of (speaker, text, meta)
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # check voice
            voice_match = re.search(r"\[(?:墨小菊|#Voice-墨小菊)\s+voice=(\d+)\]", line_str)
            if voice_match:
                current_voice = voice_match.group(1)
            
            # check pose / face tags for Mo Xiaoju
            if "墨小菊" in line_str and line_str.startswith("["):
                # extract pose
                pose_m = re.search(r"pose(\d+)", line_str)
                if pose_m:
                    current_pose = f"pose{pose_m.group(1)}"
                # extract face
                face_m = re.search(r"f(\d+)", line_str)
                if face_m:
                    current_face = f"f{face_m.group(1)}"
            
            # dialogue line
            speaker_match = re.match(r"【(.*?)】『(.*?)』", line_str)
            if speaker_match:
                speaker = speaker_match.group(1)
                raw_content = speaker_match.group(2)
                # strip embedded KAG tags from speech text
                clean_content = re.sub(r"\[.*?\]", "", raw_content).strip()
                
                item = {
                    "chapter": chapter_name,
                    "scene": scene_name,
                    "speaker": speaker,
                    "text": clean_content,
                    "raw_text": raw_content,
                    "voice": current_voice if "墨小菊" in speaker else "",
                    "pose": current_pose if "墨小菊" in speaker else "",
                    "face": current_face if "墨小菊" in speaker else ""
                }
                
                if "墨小菊" in speaker:
                    all_mxj_lines.append(item)
                    current_voice = ""  # reset voice
                
                dialog_buffer.append(item)
        
        # Extract conversational turns (Qiu Cheng <-> Mo Xiaoju)
        i = 0
        while i < len(dialog_buffer):
            turn = []
            while i < len(dialog_buffer) and ("邱诚" in dialog_buffer[i]["speaker"] or "墨小菊" in dialog_buffer[i]["speaker"]):
                turn.append(dialog_buffer[i])
                i += 1
            if len(turn) >= 2 and any("墨小菊" in x["speaker"] for x in turn) and any("邱诚" in x["speaker"] for x in turn):
                conversations.append(turn)
            i += 1

print(f"Extracted total Mo Xiaoju lines: {len(all_mxj_lines)}")
print(f"Extracted dialogues/conversations: {len(conversations)}")

# Save all lines
with open(os.path.join(output_dir, "moxiaoju_lines.jsonl"), "w", encoding="utf-8") as f:
    for item in all_mxj_lines:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

# Save plain text version for easy reading
with open(os.path.join(output_dir, "moxiaoju_lines.txt"), "w", encoding="utf-8") as f:
    for item in all_mxj_lines:
        f.write(f"[{item['chapter']} - {item['scene']}] 墨小菊: {item['text']}\n")

# Save conversations
with open(os.path.join(output_dir, "moxiaoju_qiucheng_dialogues.jsonl"), "w", encoding="utf-8") as f:
    for conv in conversations:
        f.write(json.dumps(conv, ensure_ascii=False) + "\n")

# Save readable conversations
with open(os.path.join(output_dir, "moxiaoju_qiucheng_dialogues.txt"), "w", encoding="utf-8") as f:
    for idx, conv in enumerate(conversations):
        f.write(f"=== 对话片段 #{idx+1} ({conv[0]['chapter']}/{conv[0]['scene']}) ===\n")
        for msg in conv:
            f.write(f"  【{msg['speaker']}】: {msg['text']}\n")
        f.write("\n")

print("All saved successfully to corpus/ !")
