# -*- coding: utf-8 -*-
"""
墨小菊回复内容的解析，全项目唯一入口。

parse_scene(content)  还原成场景 dict，解析失败降级为默认场景。
reply_text(content)   只取小菊说的话，失败原串兜底。
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
    """从可能夹带 Markdown/多余文字 的字符串里还原 dict，失败返回 {}"""
    if not raw:
        return {}

    # 整段直接是 JSON
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 夹带了前后缀：取最外层 { ... }
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
    """把一条 assistant 记录还原成场景 dict，解析失败返回 text=原串 的默认场景。"""
    content = str(content if content is not None else "")
    _clean = clean_text or (lambda s: s)

    scene = _extract_json_object(content)

    if not scene and content.strip():
        # 模型偶尔输出纯文本（无 JSON 结构）：降级为默认场景
        raw_text = content.strip()
        if raw_text.startswith('"') and raw_text.endswith('"'):
            raw_text = raw_text[1:-1].strip()
        scene = dict(DEFAULT_SCENE, text=raw_text)

    if scene and scene.get("text"):
        scene["text"] = _clean(scene["text"])

    return scene


def reply_text(content: str) -> str:
    """只取小菊说的那段话，解析失败用原串兜底。"""
    content = str(content if content is not None else "")
    scene = _extract_json_object(content)
    if scene and scene.get("text"):
        return scene["text"]
    return content
