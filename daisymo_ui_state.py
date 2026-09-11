# -*- coding: utf-8 -*-
"""
daisymo_ui_state.py
界面运行时状态（UiState）—— 跨屏幕共享、随运行变化的那批标量状态的所有者。

以前这些字段散落在 Screen 实例上（self.mode / self.is_thinking / self.voice_channel /
self.toast_* / self.typewriter_* / self.fade_* 等 28 个），四个屏幕方法直接伸手摸。
抽出后 Screen 只持有一个 self.ui 命名空间，屏幕方法经 self.ui.xxx 访问。

边界（哪些不在这里）：
- 字体与 pygame.image.load 出的 Surface —— 素材缓存，不是状态
- screen / mixer / chat_queue / conversation / daisymo / player_box —— 句柄与控件对象

纯 stdlib，零 pygame（voice_channel 用 Any 类型避免引入 pygame 依赖）。
"""

from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Optional


@dataclass
class UiState:
    # 对话状态机
    mode: int = 1                 # DAISYMO (1) | PLAYER (0)，由 DaisyMo 侧常量注入
    ui_hidden: bool = False
    is_auto: bool = False
    is_thinking: bool = False
    thinking_start_time: float = 0.0
    current_req_id: int = 0

    # 玩家输入
    player_input: str = ""
    player_cursor: int = 0
    player_sel_start: int = 0
    player_sel_end: int = 0
    player_dragging: bool = False
    player_last_click_time: float = 0.0

    # TTS 语音与珍藏浮动提示
    is_voice_playing: bool = False
    is_tts_loading: bool = False
    current_playing_text: str = ""
    tts_req_id: int = 0
    voice_channel: Any = None
    toast_text: str = ""
    toast_time: float = 0.0
    ui_hidden_time: float = 0.0

    # 打字机动效
    current_text: str = ""
    display_text: str = ""
    current_text_index: int = 0
    typewriter_interval: float = 0.028
    last_type_time: float = 0.0
    typewriter_done: bool = False

    # 全屏淡入过渡
    fade_alpha: float = 0.0
    fade_start_time: float = 0.0
    fade_duration: float = 0.0

    # 异步线程通信队列（由 Screen 挂到 ui 上，避免单独 init）
    chat_queue: Any = field(default_factory=Queue)
