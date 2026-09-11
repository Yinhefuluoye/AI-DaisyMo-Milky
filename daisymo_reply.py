# -*- coding: utf-8 -*-
"""
daisymo_reply.py
墨小菊回复内容的解析 —— 全项目唯一的入口。

以前这段逻辑复制了 5 份（DaisyMo.init / chat_then_parse / sync_after_history_reload /
extract_preview / 历史页正文），改一次响应结构要动 5 处，而且降级策略已经在各写各的。

现在只有两个接口，覆盖两类需求：

1. parse_scene(content) -> Dict
   把一条 assistant 记录还原成「场景」dict（where/face/body/text/bgm/sfx）。
   JSON 解析失败 → 大括号切片再试 → 仍失败时降级成默认场景，text 取原串。
   给 init / chat_then_parse / sync_after_history_reload 用，它们拿到场景后交给 next()。

2. reply_text(content) -> str
   只取「小菊说的话」这段文本，解析失败就原串兜底。
   给 extract_preview / 历史页正文用，它们只要文字、不需要场景。

纯 stdlib，零 pygame、零磁盘、零状态。
"""

import json
from typing import Any, Dict

DEFAULT_SCENE = {
    "where": "小菊卧室白天",
    "face": "温柔-说",
    "body": "便服单叉腰",
    "text": "",
    "bgm": "",
    "sfx": ""
}


def _extract_json_object(raw: str) -> Dict[str, Any]:
    """把一段可能夹带 Markdown/多余文字的字符串还原成 dict；失败返回 {}"""
    if not raw:
        return {}

    # 1. 整段直接是 JSON
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 2. 夹带了前后缀：取最外层 { ... }
    start = raw.find('{')
    end = raw.rfind('}') + 1
    if start != -1 and end > start:
        try:
            obj = json.loads(raw[start:end])
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    return {}


def parse_scene(content: str, *, clean_text=None) -> Dict[str, Any]:
    """
    把一条 assistant 记录还原成场景 dict。
    :param content: assistant 记录的 content 字段
    :param clean_text: 可选的文本清洗函数（默认不洗，由调用方传入 remove_emojis 之类）
    :return: 场景 dict；解析失败时返回 text=原串 的默认场景
    """
    content = str(content if content is not None else "")
    _clean = clean_text or (lambda s: s)

    scene = _extract_json_object(content)

    if not scene and content.strip():
        # 模型偶尔输出纯文本（没有 JSON 结构）—— 降级为默认场景，text 取原串
        raw_text = content.strip()
        if raw_text.startswith('"') and raw_text.endswith('"'):
            raw_text = raw_text[1:-1].strip()
        scene = dict(DEFAULT_SCENE, text=raw_text)

    if scene and scene.get("text"):
        scene["text"] = _clean(scene["text"])

    return scene


def reply_text(content: str) -> str:
    """
    只取小菊说的那段话。解析失败就用原串兜底（不强行套默认场景）。
    """
    content = str(content if content is not None else "")
    scene = _extract_json_object(content)
    if scene and scene.get("text"):
        return scene["text"]
    return content
