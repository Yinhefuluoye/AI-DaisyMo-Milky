# -*- coding: utf-8 -*-
"""
daisymo_conversation.py
聊天记录（Conversation）的唯一所有者。

之前这段记录是挂在 DaisyMo 类上的公共变量：
界面直接赋值、直接清空；history_manager 还能拿到列表的引用就地清空它。
改了没记录，想测它必须先启动整个程序（开窗口、加载素材树）。

现在只有这一个所有者。门外露四个动作：
    messages()                    读（只读视图，不拷贝）
    append(role, content)         写：追加一条
    replace_with(messages)        写：整段替换（载入分支）
    clear()                       写：清空

设计边界：
- 纯内存。不碰 pygame，不碰磁盘。落盘由调用方走 daisymo_history_manager。
- messages() 返回内部列表本身（实测拷贝对帧率无影响，见 2026-09-11 微基准），
  约定调用方只读；要改一律走上面三个写动作。
- 只认 role ∈ {user, assistant} 的记录，其余在入口处就被滤掉，
  这样"磁盘上存了什么形状"这件事不会泄漏给调用方。
"""

from typing import Any, Dict, Iterable, List

VALID_ROLES = ("user", "assistant")


def normalize_messages(messages: Any) -> List[Dict[str, str]]:
    """把任意来源的记录列表规整成 [{"role": ..., "content": ...}, ...]"""
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
    """聊天记录的所有者。一个实例管一段回忆。"""

    def __init__(self, messages: Any = None) -> None:
        self._messages: List[Dict[str, str]] = normalize_messages(messages)

    def messages(self) -> List[Dict[str, str]]:
        """
        只读视图：返回内部列表本身，不做拷贝。
        调用方不得修改它 —— 要改请走 append / replace_with / clear。
        """
        return self._messages

    def append(self, role: str, content: str) -> bool:
        """
        追加一条记录。
        :return: 写入成功返回 True；role 非法或 content 为空返回 False
        """
        if role not in VALID_ROLES:
            return False
        if not isinstance(content, str) or not content:
            return False
        self._messages.append({"role": role, "content": content})
        return True

    def replace_with(self, messages: Any) -> int:
        """
        整段替换（载入分支、从磁盘恢复时用）。
        :return: 替换后实际留下的记录条数
        """
        self._messages = normalize_messages(messages)
        return len(self._messages)

    def clear(self) -> None:
        """清空。原地清空而非重新绑定，避免外部若持有旧引用看到过期内容。"""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)
