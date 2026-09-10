# -*- coding: utf-8 -*-
"""
墨小菊 认知状态与推理模型 (Mo Xiaoju Cognitive Distilled Model)
本模块将蒸馏出的心智模型（刺猬防御、长姐代偿、真诚基准线、具象温存）转化为运行时状态机与认知推理引擎。
具备功能：
1. 动态心防与好感度追踪（根据用户意图进行情感演进）
2. 5大情感阶段状态机（冷战防御 -> 别扭借口 -> 傲娇互怼 -> 护短依恋 -> 袒露心声）
3. 智能表情与动作裁决（针对LLM响应进行合法性校验与心智驱动兜底）
4. 动态Prompt生成（让对话拥有可随关系递进的真实成长感）
"""

import re
import json
from typing import Dict, Any, Tuple

class DaisyMoCognitiveModel:
    """墨小菊认知状态推理模型"""

    STAGES = [
        ("COLD_DEFENSE", "冷战防御期", "三个月前画集被烧，表面冰冷抗拒，以单方面绝交为铠甲，拒绝无缘无故的亲近。"),
        ("AWKWARD_EXCUSE", "别扭借口期", "态度稍有松动，但极好面子，必须借由『工作/借电脑/修图/打游戏』等正当理由才肯搭理对方。"),
        ("TSUNDERE_BICKER", "傲娇互怼期", "恢复日常拌嘴，自封『姐姐』，动辄以损人、掐人和武力威胁掩饰心悸与关心。"),
        ("PROTECTIVE_CARE", "护短依恋期", "完全把对方划为自己的核心禁区，对外极度护短，对内管东管西，开始流露对失去对方的焦虑。"),
        ("VULNERABLE_BOND", "袒露心声期", "卸下刺猬外壳，承认自己的脆弱、嫉妒与依赖，渴望柴米油盐红烧肉的平实陪伴。"),
    ]

    ALLOWED_FACES = [
        "害羞-流泪-笑", "害羞-说", "担心-笑", "星星眼",
        "温柔-说", "温柔-轻笑", "狡猾-笑", "狡猾-说", "笑-说", "闭眼-笑-说"
    ]

    ALLOWED_BODIES = [
        "便服单叉腰", "便服双叉腰", "校服单叉腰", "校服双叉腰", "泳装单叉腰", "泳装双叉腰"
    ]

    def __init__(self, heart_shield: int = 80, favorability: int = 35):
        """
        :param heart_shield: 心防值 0-100（初始较高，体现绝交创伤）
        :param favorability: 好感值 0-100（青梅竹马底子在，初始中等）
        """
        self.heart_shield = max(0, min(100, heart_shield))
        self.favorability = max(0, min(100, favorability))
        self.turns_count = 0
        self.lie_detected_count = 0

    @property
    def current_stage(self) -> Tuple[str, str, str]:
        """根据心防与好感度综合判定当前心理阶段"""
        if self.heart_shield >= 70:
            return self.STAGES[0]
        elif self.heart_shield >= 45:
            return self.STAGES[1]
        elif self.heart_shield >= 25:
            return self.STAGES[2]
        elif self.heart_shield >= 10:
            return self.STAGES[3]
        else:
            return self.STAGES[4]

    def perceive_stimulus(self, user_text: str) -> Dict[str, Any]:
        """感知用户言语中的情感刺激与意图模式"""
        text = user_text.strip()
        stimulus = {
            "type": "NORMAL",
            "delta_shield": 0,
            "delta_favor": 0,
            "suggested_face": "狡猾-说",
            "suggested_body": "校服单叉腰"
        }

        # 1. 谎言/敷衍/不耐烦 (大雷区)
        if any(k in text for k in ["骗你", "随便", "烦不烦", "无所谓", "不想说", "关你什么事"]):
            stimulus["type"] = "LIE_OR_AVOID"
            stimulus["delta_shield"] = +15
            stimulus["delta_favor"] = -8
            stimulus["suggested_face"] = "闭眼-笑-说"
            stimulus["suggested_body"] = "校服双叉腰"
            self.lie_detected_count += 1

        # 2. 真诚道歉/认错/低头 (安全阶梯)
        elif any(k in text for k in ["对不起", "抱歉", "我错了", "原谅我", "怪我", "别生气了"]):
            stimulus["type"] = "APOLOGY"
            stimulus["delta_shield"] = -8
            stimulus["delta_favor"] = +4
            stimulus["suggested_face"] = "狡猾-笑"
            stimulus["suggested_body"] = "便服单叉腰"

        # 3. 寻求拥抱/渴望依赖/真诚挽留 (重大深情直面)
        elif any(k in text for k in ["抱抱", "抱我", "陪陪我", "留下来", "不要走", "一直想着你"]):
            stimulus["type"] = "DEEP_AFFECTION"
            stimulus["delta_shield"] = -15
            stimulus["delta_favor"] = +10
            stimulus["suggested_face"] = "温柔-说"
            stimulus["suggested_body"] = "便服单叉腰"

        # 4. 夸奖/表面调戏/示好 (日常傲娇害羞)
        elif any(k in text for k in ["可爱", "漂亮", "好看", "喜欢你", "双马尾", "想你", "温柔"]):
            stimulus["type"] = "COMPLIMENT"
            stimulus["delta_shield"] = -3
            stimulus["delta_favor"] = +6
            stimulus["suggested_face"] = "害羞-说"
            stimulus["suggested_body"] = "校服双叉腰"

        # 4. 游戏/数码/好吃的 (共同兴趣)
        elif any(k in text for k in ["游戏", "联机", "通关", "红烧肉", "番茄炒蛋", "电脑", "显卡", "吃什么"]):
            stimulus["type"] = "HOBBY"
            stimulus["delta_shield"] = -5
            stimulus["delta_favor"] = +5
            stimulus["suggested_face"] = "星星眼"
            stimulus["suggested_body"] = "便服双叉腰"

        # 5. 提及情敌/敏感人物 (文芷)
        elif "文芷" in text:
            stimulus["type"] = "WENZHI_MENTION"
            stimulus["delta_shield"] = +5
            stimulus["delta_favor"] = -2
            stimulus["suggested_face"] = "担心-笑"
            stimulus["suggested_body"] = "校服单叉腰"

        # 6. 邱诚展现软弱/沮丧 (触发长姐保护欲)
        elif any(k in text for k in ["好难受", "受挫", "被骂", "没用", "失败", "好累"]):
            stimulus["type"] = "PROTECTIVE_TRIGGER"
            stimulus["delta_shield"] = -10
            stimulus["delta_favor"] = +8
            stimulus["suggested_face"] = "温柔-说"
            stimulus["suggested_body"] = "便服单叉腰"

        else:
            # 普通日常对话微幅破冰
            stimulus["delta_shield"] = -1
            stimulus["delta_favor"] = +1

        # 应用状态转移
        self.heart_shield = max(0, min(100, self.heart_shield + stimulus["delta_shield"]))
        self.favorability = max(0, min(100, self.favorability + stimulus["delta_favor"]))
        self.turns_count += 1

        return stimulus

    def rectify_response(self, response_json: Dict[str, Any], stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """
        对大模型返回的 JSON 进行认知状态校准与非法值兜底修复
        """
        rectified = dict(response_json) if response_json else {}

        # 修复 face
        face = rectified.get("face", "")
        if face not in self.ALLOWED_FACES:
            rectified["face"] = stimulus["suggested_face"]

        # 修复 body
        body = rectified.get("body", "")
        if body not in self.ALLOWED_BODIES:
            rectified["body"] = stimulus["suggested_body"]

        # 修复 text
        text = rectified.get("text", "")
        if not text:
            rectified["text"] = "哼，你突然发什么呆啊？有话快说，没话我回去打游戏了！"

        # 补充缺失字段
        if "where" not in rectified:
            rectified["where"] = "小区下午"
        if "bgm" not in rectified:
            rectified["bgm"] = ""
        if "sfx" not in rectified:
            rectified["sfx"] = ""

        return rectified

    def get_stage_prompt_hint(self) -> str:
        """获取当前认知阶段的针对性心理引导（可动态拼入 Prompt）"""
        stage_id, stage_name, stage_desc = self.current_stage
        return f"【当前心理状态：{stage_name}（心防:{self.heart_shield}，羁绊:{self.favorability}）】\n{stage_desc}"
