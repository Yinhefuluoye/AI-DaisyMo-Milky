# -*- coding: utf-8 -*-
"""
三色绘恋剧情记忆检索模块 (Scenario Memory Retrieval Engine)
100% 纯 Python 实现，零外部依赖，极速本地匹配。
核心特性：
1. 关键词加权倒排索引与语义特征匹配；
2. 严格阈值截断：日常闲聊（打招呼、天气等）返回空，0 Token 额外消耗；
3. 命中剧情时仅精准注入 1~2 条事实卡片（约 30~60 Token），彻底杜绝大模型瞎猜剧情；
4. 严格遵守零 Emoji 规范与自然语气。
"""

import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ScenarioFact:
    """剧情事实卡片实体"""
    id: str
    chapter: str
    title: str
    keywords: List[str]
    facts: str
    xiaoju_perspective: str


class ScenarioMemoryRetriever:
    """剧情记忆事实检索器（单例 / 缓存实例）"""

    _instance: Optional["ScenarioMemoryRetriever"] = None

    def __init__(self, json_path: Optional[str] = None) -> None:
        self.facts: List[ScenarioFact] = []
        self._load_database(json_path)

    @classmethod
    def get_instance(cls, json_path: Optional[str] = None) -> "ScenarioMemoryRetriever":
        if cls._instance is None:
            cls._instance = cls(json_path)
        return cls._instance

    def _load_database(self, json_path: Optional[str] = None) -> None:
        """从 JSON 文件加载剧情事实库。

        寻址语义（分两种，这是沙箱干净的关键）：
        - 显式传入 json_path：只用这一个路径，不存在就留空，绝不回退到真实库 ——
          测试/沙箱场景据此构造一个「不碰磁盘」的空检索器；
        - 传入 None（默认）：走多路径容错寻址，加载真实剧情库。
        """
        if json_path is not None:
            candidate_paths = [json_path]
        else:
            candidate_paths = [
                "assets/daisymo_scenario_memory.json",
                "daisymo_scenario_memory.json",
                os.path.join(os.path.dirname(__file__), "assets", "daisymo_scenario_memory.json"),
                os.path.join(os.path.dirname(__file__), "daisymo_scenario_memory.json")
            ]
        chosen_path = None
        for p in candidate_paths:
            if p and os.path.exists(p):
                chosen_path = p
                break

        if not chosen_path:
            return

        try:
            with open(chosen_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.facts = [
                ScenarioFact(
                    id=item.get("id", ""),
                    chapter=item.get("chapter", ""),
                    title=item.get("title", ""),
                    keywords=[k.lower() for k in item.get("keywords", [])],
                    facts=item.get("facts", "").strip(),
                    xiaoju_perspective=item.get("xiaoju_perspective", "").strip()
                )
                for item in data
            ]
        except Exception:
            self.facts = []

    def _calculate_score(self, query: str, fact: ScenarioFact) -> float:
        """
        计算查询与剧情事实的匹配得分
        融合精确关键词加权、标题命中与正文语义重叠
        """
        q = query.lower()
        score = 0.0

        # 1. 核心关键词命中（权重极高）
        keyword_hits = 0
        for kw in fact.keywords:
            if kw in q:
                keyword_hits += 1
                score += 3.0 + len(kw) * 0.5  # 越长的专业词汇权重越高

        # 若没有任何关键词命中，则直接降级
        if keyword_hits == 0:
            return 0.0

        # 2. 标题命中加分
        title_lower = fact.title.lower()
        if any(w in title_lower for w in re.findall(r"[\u4e00-\u9fa5a-zA-Z0-9]+", q)):
            score += 1.5

        # 3. 词频与长度综合归一化
        score += keyword_hits * 1.0
        return score

    def query_relevant_facts(
        self,
        query: str,
        top_k: int = 2,
        threshold: float = 3.0
    ) -> str:
        """
        检索与当前输入最相关的剧情客观事实
        若未命中剧情关键词或得分低于阈值，返回空字符串（保证日常对话 0 Token 开销）
        """
        if not query or not self.facts:
            return ""

        clean_query = query.strip()
        if len(clean_query) < 2:
            return ""

        scored_facts: List[Tuple[float, ScenarioFact]] = []
        for fact in self.facts:
            s = self._calculate_score(clean_query, fact)
            if s >= threshold:
                scored_facts.append((s, fact))

        if not scored_facts:
            return ""

        # 按得分从高到低排序，取 Top-K
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        selected = scored_facts[:top_k]

        lines = [
            "【记忆中的真实剧情事实（务必严格依据此客观事实回应，切勿随意凭空编造）】:"
        ]
        for _, fact in selected:
            lines.append(
                f"- 事件名：{fact.title}（剧本节点：{fact.chapter}）\n"
                f"  客观事实：{fact.facts}\n"
                f"  小菊心境：{fact.xiaoju_perspective}"
            )

        return "\n".join(lines)


def build_scenario_retriever(json_path: Optional[str] = None) -> ScenarioMemoryRetriever:
    """
    显式构造一个剧情事实检索器。由调用方（DaisyMo）持有，注入后自行管理生命周期，
    不再依赖 import 时的隐式单例 —— 这样测试能干净地造一个空检索器而不碰磁盘。
    """
    return ScenarioMemoryRetriever(json_path)
