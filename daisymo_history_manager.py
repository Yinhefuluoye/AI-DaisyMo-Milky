# -*- coding: utf-8 -*-
"""
daisymo_history_manager.py
AI-DaisyMo 对话历史记录与多时间线分支管理器
核心职责：
1. 备份与归档：支持一键将当前会话打包归档至 assets/history_backups/；
2. 多时间线载入：支持从备份存档中读取历史对话并恢复为当前活跃对话；
3. 安全清空：清空活跃对话前强制触发自动安全快照，杜绝误操作丢数据；
4. 重命名与软删除：支持改写备份标题，删除时移入 .trash 回收目录而非物理抹除；
5. 100% 纯 Python 实现，零 GUI / pygame 依赖。
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any

from daisymo_reply import reply_text


BACKUP_DIR = "assets/history_backups"
TRASH_DIR = os.path.join(BACKUP_DIR, ".trash")
DEFAULT_HISTORY_FILE = "assets/DaisyMo_history.json"

# 备份标题长度上限（防止卡片排版溢出）
TITLE_MAX_LEN = 24

# 自动快照的最低轮数门槛：只有开场白的对话不值得留快照（清空后会自动重建开场白）
MIN_AUTO_SNAPSHOT_ROUNDS = 2

# list_backups 的目录签名缓存：避免每帧全量读盘解析 JSON
_list_cache_signature: Optional[Tuple[Any, ...]] = None
_list_cache_result: List[Dict[str, Any]] = []


def ensure_backup_dir() -> str:
    """确保备份存档目录存在"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return BACKUP_DIR


def ensure_trash_dir() -> str:
    """确保软删除回收目录存在"""
    os.makedirs(TRASH_DIR, exist_ok=True)
    return TRASH_DIR


def invalidate_cache() -> None:
    """显式作废备份列表缓存（任何写操作后调用）"""
    global _list_cache_signature, _list_cache_result
    _list_cache_signature = None
    _list_cache_result = []


def _scan_signature() -> Tuple[Any, ...]:
    """
    生成备份目录的轻量签名（文件名 + mtime_ns + size）。
    签名不变即列表内容不变，可直接命中缓存，无需读取任何 JSON。
    """
    try:
        entries = []
        with os.scandir(BACKUP_DIR) as it:
            for e in it:
                if not e.is_file() or not e.name.endswith(".json"):
                    continue
                try:
                    st = e.stat()
                except OSError:
                    continue
                entries.append((e.name, st.st_mtime_ns, st.st_size))
        entries.sort()
        return tuple(entries)
    except Exception:
        return ()


def normalize_title(raw: Any, fallback: str = "") -> str:
    """
    规整备份标题：剥离首尾空白、压缩换行、限制长度。
    标题为空时退回 fallback。
    """
    text = str(raw if raw is not None else "")
    text = " ".join(text.split()).strip()
    if len(text) > TITLE_MAX_LEN:
        text = text[:TITLE_MAX_LEN]
    return text if text else fallback


def default_backup_title(now: Optional[datetime] = None) -> str:
    """
    生成默认分支存档标题（与 create_backup 的兜底命名保持一致，供 UI 预填使用）
    :param now: 指定时间点，缺省取当前时刻
    """
    return f"分支存档_{(now or datetime.now()).strftime('%m-%d %H:%M')}"


def extract_preview(messages: List[Dict[str, Any]]) -> Tuple[str, str, int]:
    """
    从聊天记录中提取元数据摘要（只读，不修改传入的列表）
    :param messages: 聊天记录
    :return: (最后发言人, 最后发言内容摘要, 对话总轮数)
    """
    if not messages:
        return "无", "（空白对话）", 0

    valid_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    if not valid_msgs:
        return "无", "（无有效对话）", 0

    # 统计小菊回复的次数作为对话轮数
    rounds = sum(1 for m in valid_msgs if m.get("role") == "assistant")

    last_msg = valid_msgs[-1]
    role = last_msg.get("role", "")
    content = str(last_msg.get("content", "")).strip()

    if role == "user":
        speaker = "邱诚"
        text = content
    elif role == "assistant":
        speaker = "墨小菊"
        text = reply_text(content)
    else:
        speaker = "系统"
        text = content

    # 压缩为单行摘要
    clean_text = " ".join(text.split())
    if len(clean_text) > 40:
        clean_text = clean_text[:38] + "..."

    return speaker, clean_text, rounds


def find_auto_backup_id(title: str) -> Optional[str]:
    """
    查找是否已存在同标题的「自动快照」存档，返回其 backup_id。
    走 list_backups 的签名缓存，开销可忽略。
    """
    for b in list_backups():
        if b.get("is_auto_backup") and b.get("title") == title:
            return b.get("backup_id")
    return None


def create_backup(
    messages: List[Dict[str, Any]],
    is_auto: bool = False,
    title: str = ""
) -> Optional[Dict[str, Any]]:
    """
    把当前聊天记录打包归档到备份目录（只读 messages，不修改传入的列表）
    :param messages: 当前聊天记录
    :param is_auto: 是否为自动快照（清空前安全快照 / 切换分支前快照）
    :param title: 自定义标题或标签
    :return: 备份元数据字典；记录为空、或自动快照不值得留存时返回 None

    自动快照的两条特殊策略（避免每切一次分支就多堆一条存档）：
    1. 轮数不足 MIN_AUTO_SNAPSHOT_ROUNDS 时直接跳过 —— 只有开场白的话，清空后会自动重建，存了是纯垃圾；
    2. 同标题的自动快照只保留一条 —— 复用已有 backup_id 原地覆盖，不再追加新条目。
    手动命名的分支存档不受这两条约束，始终追加。
    """
    if not messages:
        return None

    valid_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
    if not valid_msgs:
        return None

    ensure_backup_dir()

    now = datetime.now()
    speaker, preview, rounds = extract_preview(valid_msgs)

    if is_auto and rounds < MIN_AUTO_SNAPSHOT_ROUNDS:
        return None

    default_title = "清空前自动安全快照" if is_auto else default_backup_title(now)
    backup_title = normalize_title(title, default_title)

    reused_id = find_auto_backup_id(backup_title) if is_auto else None
    if reused_id:
        backup_id = reused_id
    else:
        time_str = now.strftime("%Y%m%d_%H%M%S")
        prefix = "backup_autoclear" if is_auto else "backup"
        # 同秒内多次备份时追加序号，杜绝 backup_id 冲突互相覆盖
        base_id = f"{prefix}_{time_str}"
        backup_id = base_id
        suffix = 1
        while os.path.exists(os.path.join(BACKUP_DIR, f"{backup_id}.json")):
            backup_id = f"{base_id}_{suffix}"
            suffix += 1

    record = {
        "backup_id": backup_id,
        "title": backup_title,
        "backup_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": time.time(),
        "total_rounds": rounds,
        "last_speaker": speaker,
        "last_preview": preview,
        "is_auto_backup": is_auto,
        "memory": valid_msgs
    }

    file_path = os.path.join(BACKUP_DIR, f"{backup_id}.json")
    temp_path = f"{file_path}.tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, file_path)
        invalidate_cache()
        return record
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise e


def list_backups() -> List[Dict[str, Any]]:
    """
    扫描备份目录并按时间倒序返回所有备份的元数据卡片列表（不载入具体完整 memory，保持极速）。

    带目录签名缓存：签名（文件名 + mtime_ns + size）未变时直接返回上次结果，
    避免在 30fps 的主循环里每帧把所有备份 JSON 全量读盘解析。
    """
    global _list_cache_signature, _list_cache_result

    ensure_backup_dir()

    signature = _scan_signature()
    if signature == _list_cache_signature and _list_cache_result:
        return list(_list_cache_result)

    results = []

    for fn, _mtime, _size in signature:
        fp = os.path.join(BACKUP_DIR, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "backup_id" in data:
                summary = {
                    "backup_id": data.get("backup_id", fn[:-5]),
                    "title": data.get("title", fn[:-5]),
                    "backup_time": data.get("backup_time", ""),
                    "timestamp": data.get("timestamp", 0.0),
                    "total_rounds": data.get("total_rounds", 0),
                    "last_speaker": data.get("last_speaker", ""),
                    "last_preview": data.get("last_preview", ""),
                    "is_auto_backup": data.get("is_auto_backup", False),
                    "file_path": fp
                }
                results.append(summary)
        except Exception:
            continue

    # 按时间戳从新到旧排序
    results.sort(key=lambda x: x.get("timestamp", 0.0), reverse=True)

    _list_cache_signature = signature
    _list_cache_result = list(results)
    return results


def load_backup(backup_id: str) -> Tuple[bool, List[Dict[str, Any]], str]:
    """
    读取指定备份的完整对话列表
    :param backup_id: 备份ID或文件名
    :return: (成功与否, 消息列表, 提示信息)
    """
    ensure_backup_dir()
    clean_id = backup_id if not backup_id.endswith(".json") else backup_id[:-5]
    file_path = os.path.join(BACKUP_DIR, f"{clean_id}.json")

    if not os.path.exists(file_path):
        return False, [], f"备份文件不存在: {clean_id}"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "memory" in data:
            raw_mem = data["memory"]
            valid_mem = [m for m in raw_mem if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
            return True, valid_mem, "载入成功"
        elif isinstance(data, list):
            valid_mem = [m for m in data if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
            return True, valid_mem, "载入成功"
        return False, [], "备份文件格式不兼容"
    except Exception as e:
        return False, [], f"读取备份失败: {str(e)}"


def delete_backup(backup_id: str) -> Tuple[bool, str]:
    """
    删除指定的备份存档。

    采用软删除：文件被移入 assets/history_backups/.trash/，不再出现在分支存档列表中，
    但仍保留在磁盘上，误删时可手工从 .trash 目录找回。
    :param backup_id: 备份ID
    :return: (成功与否, 提示信息)
    """
    ensure_backup_dir()
    clean_id = backup_id if not backup_id.endswith(".json") else backup_id[:-5]
    file_path = os.path.join(BACKUP_DIR, f"{clean_id}.json")

    if not os.path.exists(file_path):
        return False, f"备份文件不存在: {clean_id}"

    try:
        ensure_trash_dir()
        trash_name = f"{clean_id}.json"
        trash_path = os.path.join(TRASH_DIR, trash_name)
        # 同名回收文件加序号，避免同一存档反复删除时互相覆盖
        dup = 1
        while os.path.exists(trash_path):
            trash_path = os.path.join(TRASH_DIR, f"{clean_id}_{dup}.json")
            dup += 1
        os.replace(file_path, trash_path)
        invalidate_cache()
        return True, "已移入回收站"
    except Exception as e:
        return False, f"删除备份失败: {str(e)}"


def rename_backup(backup_id: str, new_title: str) -> Tuple[bool, str]:
    """
    重命名指定的备份存档（仅修改标题，不动对话内容）。
    :param backup_id: 备份ID
    :param new_title: 新标题，为空时视为无效
    :return: (成功与否, 提示信息)
    """
    ensure_backup_dir()
    clean_id = backup_id if not backup_id.endswith(".json") else backup_id[:-5]
    file_path = os.path.join(BACKUP_DIR, f"{clean_id}.json")

    if not os.path.exists(file_path):
        return False, f"备份文件不存在: {clean_id}"

    title = normalize_title(new_title)
    if not title:
        return False, "名称不能为空"

    temp_path = f"{file_path}.tmp"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False, "备份文件格式不兼容"

        data["title"] = title
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, file_path)
        invalidate_cache()
        return True, "已重命名分支存档"
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return False, f"重命名失败: {str(e)}"


def clear_active_history(
    messages: List[Dict[str, Any]],
    history_file_path: str = DEFAULT_HISTORY_FILE
) -> Tuple[bool, Optional[str]]:
    """
    清空前的安全动作：先为当前记录留一份自动快照，然后把主历史文件清空。

    **本函数只读 messages，不会修改它。**（旧版本会拿到这个列表的引用就地 clear()，
    把调用方自己也清空了 —— 那是个很难排查的别名坑，已拆掉。）
    清空内存里的记录是所有者 `Conversation.clear()` 的事，由调用方在拿到快照后再做。

    :param messages: 当前聊天记录（只读）
    :param history_file_path: 主历史记录文件路径
    :return: (成功与否, 自动快照ID或None)
    """
    auto_backup_id = None
    valid_msgs = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")] if messages else []
    if valid_msgs:
        try:
            rec = create_backup(valid_msgs, is_auto=True, title="清空前自动安全快照")
            if rec:
                auto_backup_id = rec.get("backup_id")
        except Exception:
            pass

    # 清空本地文件
    try:
        temp_file = f"{history_file_path}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        os.replace(temp_file, history_file_path)
    except Exception:
        pass

    return True, auto_backup_id


def save_active_history(
    messages: List[Dict[str, Any]],
    history_file_path: str = DEFAULT_HISTORY_FILE
) -> bool:
    """
    将当前聊天记录写入主历史文件（只读 messages，不做任何修改）。
    这是整个程序里唯一写这个文件的路径。
    """
    try:
        valid_mem = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
        temp_file = f"{history_file_path}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(valid_mem, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, history_file_path)
        return True
    except Exception:
        return False
