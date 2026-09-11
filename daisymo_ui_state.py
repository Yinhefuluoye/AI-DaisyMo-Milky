# -*- coding: utf-8 -*-
"""
界面运行时状态（UiState）：跨屏幕共享、随运行变化的那批标量。

Screen 只持有一个 self.ui 命名空间，屏幕方法经 self.ui.xxx 访问。
字体、Surface 等素材缓存，以及 screen/mixer/player_box 等句柄，都不属于这里。
纯 stdlib（voice_channel 用 Any 避免引入 pygame 依赖）。
"""

from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Optional


@dataclass
class UiState:
    # 对话状态机
    mode: int = 1                 # DAISYMO (1) | PLAYER (0)
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

    # 异步线程通信队列
    chat_queue: Any = field(default_factory=Queue)
