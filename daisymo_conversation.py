# -*- coding: utf-8 -*-
"""
聊天记录的唯一所有者。

门外四个动作：messages() / append(role, content) / replace_with(messages) / clear()。
纯内存，不碰 pygame 和磁盘；落盘由调用方走 daisymo_history_manager。
"""

from typing import Any, Dict, Iterable, List

VALID_ROLES = ("user", "assistant")


def normalize_messages(messages: Any) -> List[Dict[str, str]]:
    """把任意来源的记录列表规整成 [{"role": ..., "content": ...}, ...]，滤掉非法项"""
    if not messages:
        return []
    if not isinstance(messages, Iterable):
        return []

    result: List[Dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in VALID_ROLES:
            continue
        content = item.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        result.append({"role": role, "content": content})
    return result


class Conversation:
    """一段回忆的聊天记录。"""

    def __init__(self, messages: Any = None) -> None:
        self._messages: List[Dict[str, str]] = normalize_messages(messages)

    def messages(self) -> List[Dict[str, str]]:
        """返回内部列表本身，调用方只读，别改。"""
        return self._messages

    def append(self, role: str, content: str) -> bool:
        if role not in VALID_ROLES:
            return False
        if not isinstance(content, str) or not content:
            return False
        self._messages.append({"role": role, "content": content})
        return True

    def replace_with(self, messages: Any) -> int:
        """整段替换，返回替换后的条数。"""
        self._messages = normalize_messages(messages)
        return len(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
