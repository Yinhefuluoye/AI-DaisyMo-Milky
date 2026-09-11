# -*- coding: utf-8    -*-
# -*- file: DaisyMo.py -*-
# -*- CSDN: Daisy-Mo   -*-
# -*- GitHub: Rosysuki -*-
# -*- 贴吧: Daisy-Mo   -*-

__DEBUG__   = 0
BIRTH       = 8.10
DAISYMO     = 1
PLAYER      = 0
RANDOM_FACE = 0

# 界面主色调
DCOLOR         = (255, 155, 0)      # 小菊琥珀橙
QCOLOR         = (255, 255, 255)    # 纯白
BCOLOR         = (0, 0, 0)          # 纯黑
GOLD_COLOR     = (255, 212, 128)    # 邱诚淡金色
MUTED_COLOR    = (140, 147, 164)    # 次要灰色
CHARCOAL_COLOR = (28, 31, 40)       # 回忆信纸深炭黑
BG_DARK        = (18, 22, 32)       # 弹窗深色背景


def debug(err: str, txt: str) -> None:
    if __DEBUG__:
        print(f"@{err}: {txt}")


import os
import re
import math
import json
import hashlib
import pygame
# 静默 libpng 的 iCCP sRGB 警告（PNG 已修复但 SDL2_image 可能仍输出）
_orig_image_load = pygame.image.load
def _silent_image_load(path):
    import os as _os
    _old = _os.dup(2)
    _null = _os.open("nul", _os.O_WRONLY)
    _os.dup2(_null, 2)
    try:
        return _orig_image_load(path)
    finally:
        _os.dup2(_old, 2)
        _os.close(_null)
        _os.close(_old)
pygame.image.load = _silent_image_load
import requests
from pygame.locals import *
from shutil import copyfile
from cv2 import VideoCapture, cvtColor, COLOR_RGB2BGR
from collections import deque
from threading import Thread, Lock
from queue import Queue
import sys
from sys import platform, exit as sys_exit

# 独立打包运行时安全锚定工作目录至 exe 同级路径
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
from os import path as os_path, listdir, replace as os_replace
from random import choice, randint, seed
from base64 import b64encode, b64decode
from time import time, localtime, strftime
from typing import NoReturn, Self, Tuple, Deque, Dict, List, Callable, Optional, Any


if platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

os.environ["PYGAME_FREETYPE"] = '1'
os.environ["SDL_IME_SHOW_UI"] = '1'



# 深度模块解耦导入：大模型协议引擎与自绘控件库
from daisymo_ai import (
    AI_PROVIDERS,
    AIConfig,
    TTSConfig,
    ChatResult,
    remove_emojis,
    chat as ai_chat,
    check_thinking_support as ai_check_thinking_support,
    build_chat_request as ai_build_chat_request,
    chat_completion as ai_chat_completion,
    test_llm_connection as ai_test_llm_connection,
    fetch_models as ai_fetch_models,
    fetch_tts_voices as ai_fetch_tts_voices,
    synthesize_tts_to_file as ai_synthesize_tts_to_file
)
from daisymo_widgets import (
    BlinkCursor,
    TextInputBox,
    SliderBar,
    DropdownMenu,
    TabGroup,
    DialogueScrollBar,
    ConfirmDialog,
    InputDialog
)
import daisymo_history_manager as history_mgr
from daisymo_conversation import Conversation
from daisymo_reply import parse_scene, reply_text
from daisymo_ui_state import UiState
from daisymo_memory import build_scenario_retriever

class DaisyMo(object):

    config_path: str              = "assets/config.json"
    key_legacy_path: str          = "assets/key"
    first_meet: bool              = True

    provider: str                 = "deepseek"
    base_url: str                 = "https://api.deepseek.com/v1"
    model_name: str               = "deepseek-v4-pro"
    api_key: str                  = ""

    tts_base_url: str             = "http://localhost:9880"
    tts_model: str                = "tts-1"
    tts_api_key: str              = ""
    tts_voice: str                = "alloy"
    bgm_volume: float             = 0.6
    voice_volume: float           = 1.0
    enable_thinking: bool         = False

    favorites_path: str           = "assets/favorites.json"
    favorites: List[Dict[str, str]] = []

    # 聊天记录已交给 daisymo_conversation.Conversation 拥有，不再挂在类上。
    # 实例创建时注入：DaisyMo(conversation)
    offset: List[int]             = [0, 0]
    ratio: float                  = 0.72
    default_size: Tuple[int, int] = None

    last_face_path: str           = ''
    last_body_path: str           = ''
    # 背景缓存：只有 next() 与 random_back() 会写。以前挂 Screen 上（模型反向写 UI 的状态），现在归 DaisyMo 自己。
    default_back: pygame.SurfaceType = None
    last_back_path: str           = ''
    photos: Deque[Tuple[pygame.SurfaceType, pygame.SurfaceType]] = deque([])
    text: str                     = ''
    default_save_path: str        = ''

    random_face_cache: List[str]  = []
    random_body_cache: List[str]  = []
    random_back_cache: List[str]  = []

    last_usage: Dict[str, int]    = {}
    total_usage: int              = 0
    save_lock: Lock               = Lock()

    def __init__(
        daisymo,
        conversation: Conversation,
        on_first_meet: Optional[Callable[[], None]] = None,
        scenario_retriever=None
    ) -> NoReturn:
        # 依赖注入：聊天记录与剧情检索器的所有者都由调用方创建后传进来，这里不自己造
        daisymo.conversation: Conversation = conversation
        daisymo.scenario_retriever = scenario_retriever or build_scenario_retriever()
        daisymo.load_config()
        if DaisyMo.first_meet and on_first_meet:
            on_first_meet()

    @classmethod
    def load_favorites(cls) -> None:
        """从 assets/favorites.json 加载珍藏对白列表"""
        if os_path.exists(cls.favorites_path):
            try:
                with open(cls.favorites_path, 'r', encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        cls.favorites = data
            except Exception as e:
                debug("读取珍藏对白失败", str(e))
                cls.favorites = []
        else:
            cls.favorites = []

    @classmethod
    def save_favorites(cls) -> None:
        """保存珍藏对白列表到 assets/favorites.json"""
        os.makedirs("assets", exist_ok=True)
        try:
            with open(cls.favorites_path, 'w', encoding="utf-8") as f:
                json.dump(cls.favorites, f, ensure_ascii=False, indent=2)
        except Exception as e:
            debug("保存珍藏对白失败", str(e))

    @classmethod
    def is_favorited(cls, text: str) -> bool:
        """检查某句台词是否已加入珍藏"""
        t = text.strip()
        if not t:
            return False
        return any(fav.get("text", "").strip() == t for fav in cls.favorites)

    @classmethod
    def toggle_favorite(cls, text: str, role: str = "墨小菊") -> bool:
        """切换珍藏状态，返回新状态（True: 已珍藏，False: 已取消珍藏）"""
        t = text.strip()
        if not t:
            return False
        for i, fav in enumerate(cls.favorites):
            if fav.get("text", "").strip() == t:
                cls.favorites.pop(i)
                cls.save_favorites()
                return False
        timestamp = strftime("%Y-%m-%d %H:%M", localtime())
        cls.favorites.append({
            "text": t,
            "role": role,
            "time": timestamp
        })
        cls.save_favorites()
        return True

    @classmethod
    def load_config(cls) -> None:
        """加载配置，兼容从 assets/key 自动平滑迁移"""
        cls.load_favorites()
        if os_path.exists(cls.config_path):
            try:
                with open(cls.config_path, 'r', encoding="utf-8") as f:
                    cfg = json.load(f)
                    cls.provider = cfg.get("provider", "deepseek")
                    prov_info = AI_PROVIDERS.get(cls.provider, AI_PROVIDERS["deepseek"])
                    cls.base_url = cfg.get("base_url", prov_info["base_url"])
                    cls.model_name = cfg.get("model", prov_info["default_model"])
                    cls.api_key = cfg.get("api_key", "").strip()

                    cls.tts_base_url = cfg.get("tts_base_url", "http://localhost:9880").strip()
                    cls.tts_model = cfg.get("tts_model", "tts-1").strip()
                    cls.tts_api_key = cfg.get("tts_api_key", "").strip()
                    cls.tts_voice = cfg.get("tts_voice", "alloy").strip()

                    cls.bgm_volume = float(cfg.get("bgm_volume", 0.6))
                    cls.voice_volume = float(cfg.get("voice_volume", 1.0))
                    cls.enable_thinking = bool(cfg.get("enable_thinking", False))
                    Mixer.set_volume(cls.bgm_volume)

                    cls.first_meet = not bool(cls.api_key)
                    return
            except Exception as e:
                debug("读取配置失败", str(e))

        # 检查旧版 assets/key
        if os_path.exists(cls.key_legacy_path):
            try:
                with open(cls.key_legacy_path, 'r', encoding="utf-8") as f:
                    raw_key = f.read().strip()
                try:
                    cls.api_key = b64decode(raw_key.encode()).decode().strip()
                except Exception:
                    cls.api_key = raw_key
                cls.provider = "deepseek"
                cls.base_url = AI_PROVIDERS["deepseek"]["base_url"]
                cls.model_name = AI_PROVIDERS["deepseek"]["default_model"]
                cls.first_meet = not bool(cls.api_key)
                cls.save_config(cls.provider, cls.base_url, cls.model_name, cls.api_key)
                return
            except Exception as e:
                debug("读取旧Key失败", str(e))

        cls.first_meet = True

    @classmethod
    def save_config(cls, provider: str, base_url: str, model: str, api_key: str,
                    tts_base_url: Optional[str] = None, tts_model: Optional[str] = None,
                    tts_api_key: Optional[str] = None, tts_voice: Optional[str] = None,
                    bgm_volume: Optional[float] = None,
                    voice_volume: Optional[float] = None,
                    enable_thinking: Optional[bool] = None) -> None:
        """保存 API 配置到 assets/config.json"""
        cls.provider = provider
        cls.base_url = base_url.strip()
        cls.model_name = model.strip()
        cls.api_key = api_key.strip()

        if tts_base_url is not None:
            cls.tts_base_url = tts_base_url.strip()
        if tts_model is not None:
            cls.tts_model = tts_model.strip()
        if tts_api_key is not None:
            cls.tts_api_key = tts_api_key.strip()
        if tts_voice is not None:
            cls.tts_voice = tts_voice.strip()
        if bgm_volume is not None:
            cls.bgm_volume = max(0.0, min(1.0, float(bgm_volume)))
            Mixer.set_volume(cls.bgm_volume)
        if voice_volume is not None:
            cls.voice_volume = max(0.0, min(1.0, float(voice_volume)))
        if enable_thinking is not None:
            cls.enable_thinking = bool(enable_thinking)

        cls.first_meet = not bool(cls.api_key)

        cfg = {
            "provider": cls.provider,
            "base_url": cls.base_url,
            "model": cls.model_name,
            "api_key": cls.api_key,
            "tts_base_url": cls.tts_base_url,
            "tts_model": cls.tts_model,
            "tts_api_key": cls.tts_api_key,
            "tts_voice": cls.tts_voice,
            "bgm_volume": cls.bgm_volume,
            "voice_volume": cls.voice_volume,
            "enable_thinking": cls.enable_thinking
        }
        os.makedirs("assets", exist_ok=True)
        with open(cls.config_path, 'w', encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    @classmethod
    def check_thinking_support(cls, provider: str, base_url: str, model: str, api_key: str = "") -> bool:
        """检测当前大模型是否具备并支持深度思考 (Reasoning / Thinking) 能力 (委托至 daisymo_ai 核心引擎)"""
        return ai_check_thinking_support(provider, base_url, model, api_key)

    # 人格设定缓存：加载一次持有，后续请求不再碰磁盘
    _soul_cache: Optional[str] = None

    @classmethod
    def invalidate_soul_cache(cls) -> None:
        """清空人格设定缓存（测试或运行时热重载人格文件时用）"""
        cls._soul_cache = None

    @classmethod
    def get_soul(cls) -> str:
        """获取墨小菊核心人格设定与JSON输出约束（优先读取根目录原案定义，加载一次后缓存）"""
        if cls._soul_cache is not None:
            return cls._soul_cache
        for path in ("DaisyMo.soul", "assets/DaisyMo_prompt.soul", "assets/DaisyMo.soul"):
            if os_path.exists(path):
                try:
                    with open(path, 'r', encoding="utf-8") as f:
                        c = f.read().strip()
                        if c and not c.startswith('['):
                            cls._soul_cache = c
                            return c
                except Exception:
                    pass
        cls._soul_cache = (
            "你是墨小菊（Daisy Mo），17岁高二女生，留着标志性的琥珀色双马尾，琥珀色眼瞳。\n"
            "你是邱诚7岁相识至今的邻居与青梅竹马。自幼以“姐姐”自居保护怯懦的邱诚，对他有强烈的保护欲与依赖感。\n"
            "平日语速利落轻快、元气傲娇，叫邱诚“笨蛋”，自称“姐姐”。\n"
            "必须严格以合法JSON格式输出，禁止任何多余文字或Markdown标记，格式如下：\n"
            '{"where": "小菊卧室白天","face": "温柔-说","body": "便服单叉腰","text": "说话内容","bgm": "","sfx": ""}'
        )
        return cls._soul_cache

    def init(daisymo) -> Dict[str, str]:
        # 保护并还原 assets/DaisyMo.soul 设定文件
        soul_file_path: str = "assets/DaisyMo.soul"
        hist_path: str = "assets/DaisyMo_history.json"

        if os_path.exists(soul_file_path):
            try:
                with open(soul_file_path, 'r', encoding="utf-8") as f:
                    c = f.read().strip()
                if c.startswith('['):
                    # 旧版本将历史写入了 soul 文件，迁移并恢复
                    if not os_path.exists(hist_path):
                        with open(hist_path, 'w', encoding="utf-8") as hf:
                            hf.write(c)
                    if os_path.exists("DaisyMo.soul"):
                        copyfile("DaisyMo.soul", soul_file_path)
            except Exception:
                pass
        elif os_path.exists("DaisyMo.soul"):
            copyfile("DaisyMo.soul", soul_file_path)

        # 加载历史对话
        if os_path.exists(hist_path):
            try:
                with open(hist_path, 'r', encoding="utf-8") as f:
                    saved_mem = json.load(f)
                if isinstance(saved_mem, list) and saved_mem:
                    daisymo.conversation.replace_with(saved_mem)
                    for m in reversed(daisymo.conversation.messages()):
                        if m.get("role") == "assistant":
                            p = parse_scene(m.get("content", ""), clean_text=remove_emojis)
                            if p and p.get("text"):
                                return daisymo.next(p)
            except Exception as e:
                debug("读取历史记录失败", str(e))

        res: Dict[str, str] = {}
        if DaisyMo.api_key:
            try:
                seed(BIRTH)
                res = daisymo.chat_then_parse("（邱诚站在你面前，静静地看着你）")
            except Exception as e:
                debug("初始化联网失败", str(e))

        if not res:
            # 离线保底引导状态（确保立绘、背景、对白全部就绪，避免未配Key退出时黑屏与残影）
            res = {
                "where": "小菊卧室白天",
                "face": "狡猾-说",
                "body": "便服单叉腰",
                "text": "哼，笨蛋邱诚，你还没在设置里填 API Key 呢！点击右下角的 SYSTEM 按钮或者按 F1 打开设置，填好 Key 姐姐才能陪你说话！",
                "bgm": "",
                "sfx": ""
            }
            daisymo.next(res)

        return res

    def update_offset_center(daisymo) -> Self:
        DaisyMo.offset[0] = (DaisyMo.default_size[0] - Screen.default_size[0]) // 2
        return daisymo

    def update_default_size(daisymo, size: Tuple[int, int] = None) -> Self:
        if size is not None:
            DaisyMo.default_size = size
        elif DaisyMo.photos:
            DaisyMo.default_size = DaisyMo.photos[0][1].get_size()
        else:
            DaisyMo.default_size = (1405 * DaisyMo.ratio, 2500 * DaisyMo.ratio)
        return daisymo

    def chat(daisymo, text: str) -> str:
        conversation: Conversation = daisymo.conversation
        conversation.append("user", text)

        # 动态检索三色绘恋客观剧情事实（结合近几轮上下文避免代词指代，未命中则返回空，0 Token 增量）
        query_text = text
        if len(conversation) >= 3:
            prev_user_msgs = [m["content"] for m in conversation.messages()[-3:] if m.get("role") == "user"]
            query_text = " ".join(prev_user_msgs)
        scenario_context = daisymo.scenario_retriever.query_relevant_facts(query_text)

        cfg = AIConfig(
            provider=DaisyMo.provider,
            base_url=DaisyMo.base_url,
            model_name=DaisyMo.model_name,
            api_key=DaisyMo.api_key,
            enable_thinking=DaisyMo.enable_thinking
        )
        res = ai_chat_completion(
            messages=conversation.messages(),
            system_prompt=daisymo.get_soul(),
            config=cfg,
            scenario_context=scenario_context
        )
        if res.is_success:
            respond = res.content
            DaisyMo.last_usage = res.usage
            DaisyMo.total_usage += res.total_tokens
            if respond:
                conversation.append("assistant", respond)
            if __DEBUG__:
                print('= ' * 10)
                print(respond)
                print('= ' * 10)
            return respond
        else:
            debug("回复失败", res.error_message)
            # 失败回滚：把刚才追加的那条 user 记录撤掉，不留痕
            msgs = conversation.messages()
            if msgs and msgs[-1].get("role") == "user":
                conversation.replace_with(msgs[:-1])
            return ''

    def chat_then_parse(daisymo, text: str) -> Dict[str, str]:
        if not text:
            debug("不能为空", "in chat_then_parse text")
            return {}

        respond_json: Dict[str, str] = {}
        raw: str = daisymo.chat(text)

        if not raw:
            return {}

        respond_json = parse_scene(raw, clean_text=remove_emojis)

        if not respond_json:
            debug("解释失败", "in chat_then_parse respond_json")
            return {}

        # next（角色立绘加载）移至主线程执行，避免子线程 SDL2 Surface 锁争用
        return respond_json

    def next(daisymo, respond_json: Dict[str, str]) -> Dict[str, str]:
        last_face = last_body = None
        if DaisyMo.photos:
            last_face, last_body = DaisyMo.photos.pop()

        face_name = respond_json.get("face", "温柔-说")
        body_name = respond_json.get("body", "便服单叉腰")
        where_name = respond_json.get("where", "学校门口白天")

        face_pic_path = f"assets/daisymo/face/{face_name}.png"
        body_pic_path = f"assets/daisymo/body/{body_name}.png"
        back_pic_path = f"assets/bg/{where_name}.jpg"

        # 容错 fallback
        if not os_path.exists(face_pic_path):
            face_pic_path = "assets/daisymo/face/温柔-说.png"
        if not os_path.exists(body_pic_path):
            body_pic_path = "assets/daisymo/body/便服单叉腰.png"
        if not os_path.exists(back_pic_path):
            back_pic_path = "assets/bg/学校门口白天.jpg"

        need_scale_face = False
        need_scale_body = False

        if DaisyMo.last_face_path != face_pic_path or last_face is None:
            face = pygame.image.load(face_pic_path).convert_alpha()
            need_scale_face = True
        else:
            face = last_face

        if DaisyMo.last_body_path != body_pic_path or last_body is None:
            body = pygame.image.load(body_pic_path).convert_alpha()
            need_scale_body = True
        else:
            body = last_body

        back = (
            pygame.image.load(back_pic_path).convert()
            if DaisyMo.last_back_path != back_pic_path or DaisyMo.default_back is None
            else DaisyMo.default_back
        )

        DaisyMo.last_face_path = face_pic_path
        DaisyMo.last_body_path = body_pic_path
        DaisyMo.last_back_path = back_pic_path

        if DaisyMo.ratio != 1.0:
            if need_scale_face:
                face = pygame.transform.rotozoom(face, 0.0, DaisyMo.ratio)
            if need_scale_body:
                body = pygame.transform.rotozoom(body, 0.0, DaisyMo.ratio)

        DaisyMo.photos.clear()
        DaisyMo.photos.append((face, body))
        DaisyMo.default_back = back
        DaisyMo.text = remove_emojis(respond_json.get("text", "【回答失败！】"))

        return respond_json

    def auto_save(daisymo) -> NoReturn:
        Thread(target=daisymo.save, name="daisymo_auto_save").start()

    def save(daisymo) -> bool:
        """
        落盘只此一条路径：临时文件 + 原子替换的实现收在 history_mgr 里，
        这里不再自己拼一份 JSON（否则同一个存档文件会有两个写入者）。
        锁保留在这里，因为 auto_save 是放到线程里跑的。
        """
        with DaisyMo.save_lock:
            return history_mgr.save_active_history(daisymo.conversation.messages())

    def parse(daisymo, content: str) -> Dict[str, str] | List[Dict[str, str]]:
        return json.loads(content)

    def random_face(daisymo) -> NoReturn:
        if not DaisyMo.random_face_cache:
            DaisyMo.random_face_cache.extend(
                [f"assets/daisymo/face/{e}" for e in listdir("assets/daisymo/face")]
            )
        random_face_path = choice(DaisyMo.random_face_cache)
        last_body = DaisyMo.photos.pop()[1] if DaisyMo.photos else None
        face = pygame.image.load(random_face_path).convert_alpha()
        if DaisyMo.ratio != 1.0:
            face = pygame.transform.rotozoom(face, 0.0, DaisyMo.ratio)
        DaisyMo.last_face_path = random_face_path
        DaisyMo.photos.clear()
        DaisyMo.photos.append((face, last_body))

    def random_body(daisymo) -> NoReturn:
        if not DaisyMo.random_body_cache:
            DaisyMo.random_body_cache.extend(
                [f"assets/daisymo/body/{e}" for e in listdir("assets/daisymo/body")]
            )
        random_body_path = choice(DaisyMo.random_body_cache)
        last_face = DaisyMo.photos.pop()[0] if DaisyMo.photos else None
        body = pygame.image.load(random_body_path).convert_alpha()
        if DaisyMo.ratio != 1.0:
            body = pygame.transform.rotozoom(body, 0.0, DaisyMo.ratio)
        DaisyMo.last_body_path = random_body_path
        DaisyMo.photos.clear()
        DaisyMo.photos.append((last_face, body))

    def random_back(daisymo) -> NoReturn:
        if not DaisyMo.random_back_cache:
            DaisyMo.random_back_cache.extend(
                [f"assets/bg/{e}" for e in listdir("assets/bg")]
            )
        random_back_path = choice(DaisyMo.random_back_cache)
        DaisyMo.default_back = pygame.image.load(random_back_path).convert()


class Mixer(object):
    pointer: int = -1
    music_list: List[str] = ["assets/bgm/bgm10_Ora.ogg"]
    volume: float = 0.6

    def __init__(self) -> NoReturn:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()

    @classmethod
    def set_volume(cls, vol: float) -> None:
        cls.volume = max(0.0, min(1.0, float(vol)))
        try:
            pygame.mixer.music.set_volume(cls.volume)
        except Exception as e:
            debug("设置音量失败", str(e))

    def air(self) -> NoReturn:
        if not Mixer.music_list:
            return
        Mixer.pointer = (Mixer.pointer + 1) % len(Mixer.music_list)
        try:
            pygame.mixer.music.load(Mixer.music_list[Mixer.pointer])
            pygame.mixer.music.set_volume(Mixer.volume)
            pygame.mixer.music.play(-1)
        except Exception as e:
            debug("播放音乐失败", str(e))

    def exit(self) -> NoReturn:
        pygame.mixer.music.stop()


class Screen(object):

    default_size: Tuple[int, int]         = (1280, 720)
    FPS: int                              = 30

    font: pygame.font.FontType            = None   # 对白字体 22px
    name_font: pygame.font.FontType       = None   # 姓名框字体 17px
    dfont: pygame.font.FontType           = None   # 系统次要字体 14px
    qfont: pygame.font.FontType           = None   # 邱诚输入字体 21px
    card_font: pygame.font.FontType       = None   # 设置面板字体 15px

    def __init__(self) -> NoReturn:
        not pygame.get_init() and pygame.init()
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
        except Exception:
            pass
        DaisyMo.load_config()
        self.intro_played = False

        if platform == "linux":
            self.screen = pygame.display.set_mode(self.default_size, FULLSCREEN | DOUBLEBUF)
            Screen.default_size = self.screen.get_size()
        else:
            self.screen = pygame.display.set_mode(Screen.default_size, vsync=1)

        pygame.display.set_caption("AI墨小菊")
        if os_path.exists("icon.png"):
            pygame.display.set_icon(pygame.image.load("icon.png").convert_alpha())

        self.init()

    def init(self) -> NoReturn:
        # 聊天记录的所有者：整个程序只造这一个，注入给 DaisyMo
        self.conversation: Conversation = Conversation()

        # 字体加载
        font_cn_med = "assets/font/SourceHanSansCN-Medium.otf"
        font_cn_reg = "assets/font/SourceHanSansCN-Regular.otf"

        Screen.font = pygame.font.Font(font_cn_med, 23)
        Screen.name_font = pygame.font.Font(font_cn_med, 19)
        Screen.dfont = pygame.font.Font(font_cn_med, 15)
        Screen.qfont = pygame.font.Font(font_cn_med, 22)
        Screen.card_font = pygame.font.Font(font_cn_med, 15)

        # 官方原版底框分层资产
        self.main_botm = pygame.image.load("assets/ui/main_botm.png").convert_alpha()
        self.main_botm_word = pygame.image.load("assets/ui/main_botm_word.png").convert_alpha()
        self.main_botm_line = pygame.image.load("assets/ui/main_botm_line.png").convert_alpha()
        self.main_botm_name = pygame.image.load("assets/ui/main_botm_name.png").convert_alpha()

        # 官方跳动三角光标与铭牌图标
        self.main_triangle_raw = pygame.image.load("assets/ui/main_triangle.png").convert_alpha()
        self.main_triangle = pygame.transform.smoothscale(self.main_triangle_raw, (24, 24))
        self.icon_favorite_normal = pygame.image.load("assets/ui/main_btn_favorite_normal.png").convert_alpha()
        self.icon_favorite_over = pygame.image.load("assets/ui/main_btn_favorite_over.png").convert_alpha()
        self.icon_voice_normal = pygame.image.load("assets/ui/main_btn_voice_normal.png").convert_alpha()
        self.icon_voice_over = pygame.image.load("assets/ui/main_btn_voice_over.png").convert_alpha()
        self.icon_revoice_normal = pygame.image.load("assets/ui/main_btn_revoice_normal.png").convert_alpha()
        self.icon_revoice_over = pygame.image.load("assets/ui/main_btn_revoice_over.png").convert_alpha()
        self.icon_revoice_unuseable = pygame.image.load("assets/ui/main_btn_revoice_unuseable.png").convert_alpha()

        # 官方底部通用按钮
        self.btn_auto_normal = pygame.image.load("assets/ui/main_btn_auto_normal.png").convert_alpha()
        self.btn_auto_over = pygame.image.load("assets/ui/main_btn_auto_over.png").convert_alpha()
        self.btn_auto_on = pygame.image.load("assets/ui/main_btn_auto_on.png").convert_alpha()
        self.btn_skip_normal = pygame.image.load("assets/ui/main_btn_skip_normal.png").convert_alpha()
        self.btn_skip_over = pygame.image.load("assets/ui/main_btn_skip_over.png").convert_alpha()
        self.btn_log_normal = pygame.image.load("assets/ui/main_btn_backlog_normal.png").convert_alpha()
        self.btn_log_over = pygame.image.load("assets/ui/main_btn_backlog_over.png").convert_alpha()
        self.btn_sys_normal = pygame.image.load("assets/ui/main_btn_SYS_normal.png").convert_alpha()
        self.btn_sys_over = pygame.image.load("assets/ui/main_btn_SYS_over.png").convert_alpha()
        self.btn_lock_normal = pygame.image.load("assets/ui/main_btn_locked_normal.png").convert_alpha()
        self.btn_lock_over = pygame.image.load("assets/ui/main_btn_locked_over.png").convert_alpha()

        # ---- 回忆界面 (history_menu) 静态素材：加载一次缓存，避免每次进界面重新解析 ----
        # OTF 字体 Font() 解析 ~150ms/个，8 个字号 = 1.25s，是「点 log 卡」的元凶
        self.bg_backlog = pygame.image.load("assets/ui/backlog_botm.png").convert()
        self.btn_slider = pygame.image.load("assets/ui/backlog_slider.png").convert_alpha()
        self.btn_back_normal = pygame.image.load("assets/ui/common_btn_back_normal.png").convert_alpha()
        self.btn_back_over = pygame.image.load("assets/ui/common_btn_back_over.png").convert_alpha()
        self.btn_fav_normal = pygame.image.load("assets/ui/common_btn_favorite_normal.png").convert_alpha()
        self.btn_fav_over = pygame.image.load("assets/ui/common_btn_favorite_over.png").convert_alpha()
        self.btn_voice_normal = pygame.image.load("assets/ui/common_btn_voice_normal.png").convert_alpha()
        self.card_title_font = pygame.font.Font(font_cn_med, 16)
        self.card_sub_font = pygame.font.Font(font_cn_med, 12)
        self.card_tag_font = pygame.font.Font(font_cn_med, 11)
        self.dia_title_font = pygame.font.Font(font_cn_med, 18)
        self.dia_sub_font = pygame.font.Font(font_cn_med, 13)
        self.dia_sub2_font = pygame.font.Font(font_cn_med, 12)
        self.dia_btn_font = pygame.font.Font(font_cn_med, 14)
        self.dia_input_font = pygame.font.Font(font_cn_med, 17)

        # ---- 标题屏 (title) 静态素材：同样缓存，避免每次进标题屏重新解析 11 个字体 ----
        self.title_end_m = pygame.image.load("assets/ui/title_end_m.jpg").convert()
        self.hero_title_font = pygame.font.Font(font_cn_med, 20)
        self.hero_sub_font = pygame.font.Font(font_cn_med, 10)
        self.dock_cn_font = pygame.font.Font(font_cn_med, 13)
        self.dock_en_font = pygame.font.Font(font_cn_med, 9)
        self.meta_en_font = pygame.font.Font(font_cn_med, 11)
        self.meta_sub_font = pygame.font.Font(font_cn_med, 9)
        self.meta_version_font = pygame.font.Font(font_cn_med, 12)
        self.dialog_title_font = pygame.font.Font(font_cn_med, 17)
        self.dialog_sub_font = pygame.font.Font(font_cn_med, 13)
        self.dialog_sub2_font = pygame.font.Font(font_cn_med, 12)
        self.btn_font = pygame.font.Font(font_cn_med, 13)

        # 对话框状态机与自治文本输入控件
        self.ui: UiState = UiState(mode=DAISYMO)

        self.player_box: TextInputBox = TextInputBox(
            rect=pygame.Rect(230, 604, 760, 64),
            text="",
            font=Screen.qfont,
            bg_color=None,
            border_color=None,
            active_border_color=None,
            text_color=QCOLOR,
            sel_color=(200, 110, 20),
            cursor_color=GOLD_COLOR,
            max_lines=2
        )

        # 异步线程通信队列
        self.chat_queue: Queue = Queue()

        # 全屏淡入过渡（如从回忆界面返回主界面时）
        self._fade_mask: Optional[pygame.SurfaceType] = None

        self.mixer: Mixer = Mixer()
        self.mixer.air()

    def show_toast(self, text: str) -> None:
        """显示纯文本轻量浮动提示（无 Emoji）"""
        self.ui.toast_text = remove_emojis(text).strip()
        self.ui.toast_time = time()

    def start_fade_in(self, duration: float = 0.35) -> None:
        """启动一次全屏淡入：从纯黑遮罩渐变到透明"""
        self.ui.fade_alpha = 255.0
        self.ui.fade_start_time = time()
        self.ui.fade_duration = max(0.05, duration)

    def render_fade_overlay(self) -> None:
        """按时间推进淡入并在屏幕上叠加遮罩，alpha 归零后自动停用"""
        if self.ui.fade_alpha <= 0.0:
            return

        elapsed = time() - self.ui.fade_start_time
        if elapsed >= self.ui.fade_duration:
            self.ui.fade_alpha = 0.0
            return

        self.ui.fade_alpha = 255.0 * (1.0 - elapsed / self.ui.fade_duration)

        size = self.screen.get_size()
        if self._fade_mask is None or self._fade_mask.get_size() != size:
            self._fade_mask = pygame.Surface(size, pygame.SRCALPHA)
        self._fade_mask.fill((0, 0, 0, int(self.ui.fade_alpha)))
        self.screen.blit(self._fade_mask, (0, 0))

    @staticmethod
    def synthesize_tts_to_file(base_url: str, model_name: str, api_key: str, voice_name: str, text: str, output_path: str) -> Tuple[bool, str]:
        """双协议自适应 TTS 合成：委托至 daisymo_ai 核心引擎"""
        return ai_synthesize_tts_to_file(base_url, model_name, api_key, voice_name, text, output_path)

    def play_tts_voice(self, text: str, force_refresh: bool = False) -> None:
        """异步调用自定义 TTS 语音合成并播放（支持本地音频缓存、强制重新生成与点击独占打断）"""
        if not DaisyMo.tts_base_url.strip():
            self.show_toast("尚未配置 TTS API，请在 SYSTEM 中设置")
            return

        clean_text = remove_emojis(text).strip()
        if not clean_text:
            return

        is_same_text = (getattr(self, "current_playing_text", "") == clean_text)

        # 每次发起新语音或打断时，独占递增全局请求版本号
        self.ui.tts_req_id += 1
        my_req_id = self.ui.tts_req_id

        # 主线程立即切断当前通道上的任何旧声音，避免与新音频重叠
        if self.ui.voice_channel:
            try:
                self.ui.voice_channel.stop()
            except Exception:
                pass

        # 独占打断机制：
        # 若点击的是正在播放/解析的【同一条】语音，执行暂停打断并恢复常态；
        # 若点击的是【另一条不同】语音，上一条已在上方被停掉，直接继续启动新语音播放！
        if (self.ui.is_tts_loading or self.ui.is_voice_playing) and is_same_text and not force_refresh:
            self.ui.is_tts_loading = False
            self.ui.is_voice_playing = False
            self.ui.current_playing_text = ""
            self.show_toast("语音已停止")
            return

        # 计算本地缓存路径（基于文本、模型与音色的 md5 摘要）
        try:
            os.makedirs("assets/tts_cache", exist_ok=True)
        except Exception:
            pass
        cache_seed = f"{clean_text}_{DaisyMo.tts_model.strip()}_{DaisyMo.tts_voice.strip()}"
        cache_hash = hashlib.md5(cache_seed.encode("utf-8")).hexdigest()
        is_m = ("mimo" in DaisyMo.tts_model.lower()) or ("xiaomimimo" in DaisyMo.tts_base_url.lower())
        cache_ext = ".wav" if is_m else ".mp3"
        cache_file = os_path.join("assets/tts_cache", f"{cache_hash}{cache_ext}")

        # 缓存命中机制：若已存在缓存且非强制重新生成，则直接秒播（0 Token 消耗与 0 网络延迟）
        if os_path.exists(cache_file) and os_path.getsize(cache_file) > 100 and not force_refresh:
            try:
                sound = pygame.mixer.Sound(cache_file)
                if not self.ui.voice_channel:
                    self.ui.voice_channel = pygame.mixer.Channel(1)
                self.ui.voice_channel.set_volume(DaisyMo.voice_volume)
                self.ui.is_tts_loading = False
                self.ui.is_voice_playing = True
                self.ui.current_playing_text = clean_text
                self.ui.voice_channel.play(sound)

                def _monitor_cached():
                    while self.ui.voice_channel and self.ui.voice_channel.get_busy():
                        if my_req_id != self.ui.tts_req_id:
                            # 关键：新请求已接管通道，旧线程静默退出，严禁调用 self.ui.voice_channel.stop()
                            break
                        pygame.time.wait(30)
                    # 只有当前线程仍然持有最新有效请求版本时，才重置全局状态
                    if my_req_id == self.ui.tts_req_id:
                        self.ui.is_voice_playing = False
                        self.ui.current_playing_text = ""

                Thread(target=_monitor_cached, daemon=True).start()
                self.show_toast("播放语音 (本地缓存)")
                return
            except Exception:
                # 若缓存文件加载异常，安全降级至重新在线合成
                pass

        # 重新生成或缓存未命中：发起异步 API 合成并写入本地缓存
        self.ui.is_tts_loading = True
        self.ui.is_voice_playing = False
        self.ui.current_playing_text = clean_text
        self.show_toast("正在重新生成语音..." if force_refresh else "正在合成语音...")

        def _tts_worker():
            try:
                tmp_audio = cache_file
                ok, msg = Screen.synthesize_tts_to_file(
                    base_url=DaisyMo.tts_base_url,
                    model_name=DaisyMo.tts_model,
                    api_key=DaisyMo.tts_api_key,
                    voice_name=DaisyMo.tts_voice,
                    text=clean_text,
                    output_path=tmp_audio
                )
                # 检查等待期间是否已被用户切换或打断
                if my_req_id != self.ui.tts_req_id:
                    return

                if ok:
                    sound = pygame.mixer.Sound(tmp_audio)
                    if not self.ui.voice_channel:
                        self.ui.voice_channel = pygame.mixer.Channel(1)
                    self.ui.voice_channel.set_volume(DaisyMo.voice_volume)

                    self.ui.is_tts_loading = False
                    self.ui.is_voice_playing = True
                    self.ui.current_playing_text = clean_text
                    self.ui.voice_channel.play(sound)
                    while self.ui.voice_channel and self.ui.voice_channel.get_busy():
                        if my_req_id != self.ui.tts_req_id:
                            # 关键：新请求已接管通道，旧线程静默退出，严禁调用 self.ui.voice_channel.stop()
                            break
                        pygame.time.wait(30)
                else:
                    if my_req_id == self.ui.tts_req_id:
                        self.show_toast(msg)
            except Exception as ex:
                if my_req_id == self.ui.tts_req_id:
                    err_str = str(ex)
                    if "Connection" in err_str:
                        self.show_toast("TTS 错误: 无法连接服务")
                    else:
                        self.show_toast(f"TTS 错误: {err_str[:16]}")
            finally:
                if my_req_id == self.ui.tts_req_id:
                    self.ui.is_tts_loading = False
                    self.ui.is_voice_playing = False
                    self.ui.current_playing_text = ""

        Thread(target=_tts_worker, daemon=True).start()

    def title(self) -> Self:
        """开场动画与高保真标题屏（图4定版：白色便签主键 + 图1轻量圆角功能坞 + 图3和纸退出弹窗 + 平滑暗转）"""
        self._in_game_mode = False
        pygame.event.clear()
        clock: pygame.time.Clock = pygame.time.Clock()
        is_running: bool = True
        # 背景与全套字体已在 Screen.init 缓存，这里只做别名引用，避免每次进标题屏重新解析
        back: pygame.SurfaceType = self.title_end_m

        hero_title_font = self.hero_title_font
        hero_sub_font = self.hero_sub_font
        dock_cn_font = self.dock_cn_font
        dock_en_font = self.dock_en_font
        meta_en_font = self.meta_en_font
        meta_sub_font = self.meta_sub_font
        meta_version_font = self.meta_version_font
        dialog_title_font = self.dialog_title_font
        dialog_sub_font = self.dialog_sub_font
        dialog_sub2_font = self.dialog_sub2_font
        btn_font = self.btn_font

        def _render_spaced_text(font: pygame.font.Font, text: str, color: Tuple[int, int, int], spacing: int = 0) -> pygame.Surface:
            if not text:
                return pygame.Surface((0, 0), pygame.SRCALPHA)
            glyphs = [font.render(ch, True, color) for ch in text]
            tot_w = sum(g.get_width() for g in glyphs) + spacing * (len(glyphs) - 1)
            max_h = max(g.get_height() for g in glyphs)
            surf = pygame.Surface((tot_w, max_h), pygame.SRCALPHA)
            cx = 0
            for g in glyphs:
                surf.blit(g, (cx, (max_h - g.get_height()) // 2))
                cx += g.get_width() + spacing
            return surf

        # 官方三角精灵小图标
        triangle_small = pygame.transform.smoothscale(self.main_triangle_raw, (20, 20))

        # 交互矩形热区定义 (白色便签主键 224x68，2x SSAA 超采样去毛刺，居中呼吸动效)
        hero_w, hero_h = 224, 68
        hero_x = (1280 - hero_w) // 2
        hero_y = 580
        rect_hero = pygame.Rect(hero_x, hero_y - 6, hero_w, hero_h + 8)

        # 功能坞外框与 3 个按钮热区 (精简音乐项，只留设置/回忆/离开)
        dock_w, dock_h = 255, 48
        dock_x = 1280 - 32 - dock_w
        dock_y = 720 - 28 - dock_h
        rect_dock = pygame.Rect(dock_x, dock_y, dock_w, dock_h)
        item_w = dock_w // 3
        rect_dock_items = [
            pygame.Rect(dock_x + i * item_w, dock_y, item_w, dock_h)
            for i in range(3)
        ]

        # 退出确认弹窗热区与状态 (图3定版)
        exit_dialog_open: bool = False
        dia_w, dia_h = 440, 200
        dia_x = (1280 - dia_w) // 2
        dia_y = (720 - dia_h) // 2
        rect_dia_cancel = pygame.Rect(dia_x + 55, dia_y + 132, 140, 36)
        rect_dia_confirm = pygame.Rect(dia_x + 245, dia_y + 132, 140, 36)

        # 窗边暖阳浮尘微粒 (丁达尔微动)
        particles = [
            {"x": 1000.0, "y": 380.0, "r": 3.0, "a": 130, "vx": -0.25, "vy": -0.4, "ox": 1000.0, "oy": 380.0},
            {"x": 880.0, "y": 280.0, "r": 2.0, "a": 110, "vx": -0.18, "vy": -0.3, "ox": 880.0, "oy": 280.0},
            {"x": 1060.0, "y": 520.0, "r": 3.5, "a": 150, "vx": -0.3, "vy": -0.5, "ox": 1060.0, "oy": 520.0},
            {"x": 750.0, "y": 240.0, "r": 2.0, "a": 120, "vx": -0.15, "vy": -0.25, "ox": 750.0, "oy": 240.0},
            {"x": 950.0, "y": 440.0, "r": 2.2, "a": 130, "vx": -0.2, "vy": -0.35, "ox": 950.0, "oy": 440.0},
        ]
        p_layer = pygame.Surface((1280, 720), pygame.SRCALPHA)

        # 左下角版本印记微透和风胶囊底衬 (2x SSAA 抗锯齿，316x42，确保高亮杂色背景下清晰锐利)
        capsule_w, capsule_h = 316, 42
        capsule_x, capsule_y = 26, 660
        capsule_2x = pygame.Surface((capsule_w * 2, capsule_h * 2), pygame.SRCALPHA)
        pygame.draw.rect(capsule_2x, (15, 18, 25, 140), (0, 0, capsule_w * 2, capsule_h * 2), border_radius=14)
        pygame.draw.rect(capsule_2x, (255, 255, 255, 36), (0, 0, capsule_w * 2, capsule_h * 2), width=2, border_radius=14)
        capsule_surf = pygame.transform.smoothscale(capsule_2x, (capsule_w, capsule_h))
        meta_version_surf = meta_version_font.render("AI-DAISYMO V0.1", True, (255, 255, 255))
        meta_sub_surf = meta_sub_font.render("TRICOLOUR LOVESTORY FANMADE COMPANION SYSTEM", True, (215, 220, 230))

        # 提取渲染完整主标题静帧的基础函数（用于平滑消融目标图与主事件循环）
        def _render_title_base(target_surface: pygame.Surface, hover_h = 0.0, hover_d: int = -1, anim_time: float = 0.0) -> None:
            hover_val = float(hover_h)
            target_surface.blit(back, (0, 0))
            target_surface.blit(p_layer, (0, 0))

            # 右上角极简英文副标
            top_meta = meta_en_font.render("TRICOLOUR LOVESTORY // 2005.10", True, (255, 255, 255))
            top_meta_shadow = meta_en_font.render("TRICOLOUR LOVESTORY // 2005.10", True, (0, 0, 0))
            target_surface.blit(top_meta_shadow, (1280 - 32 - top_meta.get_width() + 1, 24 + 1))
            target_surface.blit(top_meta, (1280 - 32 - top_meta.get_width(), 24))

            # 左下角版本印记（微透和风胶囊底衬 + 锐利清晰排印）
            target_surface.blit(capsule_surf, (capsule_x, capsule_y))
            target_surface.blit(meta_version_surf, (capsule_x + 10, capsule_y + 5))
            target_surface.blit(meta_sub_surf, (capsule_x + 10, capsule_y + 24))

            # Hero 便签主按钮（白色便签质感 · 224x68 黄金尺寸 · 2x SSAA 超采样去毛刺 · Letter-spacing 高级排版）
            cur_hero_y = hero_y - (hover_val * 3.0)

            # 阴影随抬升加深扩散
            shadow_lift = int(hover_val * 3)
            shadow_alpha = int(70 + hover_val * 45)
            shadow_surf = pygame.Surface((hero_w + 24, hero_h + 24), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, shadow_alpha), (12, 12 + shadow_lift, hero_w, hero_h), border_radius=10)
            target_surface.blit(shadow_surf, (hero_x - 12, cur_hero_y - 12))

            # 便签主体 (2x SSAA 超采样抗锯齿，彻底消除圆角与描边毛刺)
            bg_r = int(252 + (255 - 252) * hover_val)
            bg_g = int(250 + (255 - 250) * hover_val)
            bg_b = int(246 + (255 - 246) * hover_val)
            border_r = int(215 + (255 - 215) * hover_val)
            border_g = int(120 + (155 - 120) * hover_val)
            border_b = int(10 + (0 - 10) * hover_val)
            border_a = int(55 + (160 - 55) * hover_val)

            hero_surf_2x = pygame.Surface((hero_w * 2, hero_h * 2), pygame.SRCALPHA)
            pygame.draw.rect(hero_surf_2x, (bg_r, bg_g, bg_b), (0, 0, hero_w * 2, hero_h * 2), border_radius=20)
            border_w = 4 if hover_val > 0.35 else 2
            pygame.draw.rect(hero_surf_2x, (border_r, border_g, border_b, border_a), (0, 0, hero_w * 2, hero_h * 2), width=border_w, border_radius=20)
            hero_surf = pygame.transform.smoothscale(hero_surf_2x, (hero_w, hero_h))
            target_surface.blit(hero_surf, (hero_x, cur_hero_y))

            # 顶部和纸胶带 (2x SSAA 居中)
            tape_w, tape_h = 76, 14
            tape_x = hero_x + (hero_w - tape_w) // 2
            tape_a = int(195 + 35 * hover_val)
            tape_surf_2x = pygame.Surface((tape_w * 2, tape_h * 2), pygame.SRCALPHA)
            pygame.draw.rect(tape_surf_2x, (255, 224, 150, tape_a), (0, 0, tape_w * 2, tape_h * 2), border_radius=4)
            pygame.draw.rect(tape_surf_2x, (215, 120, 10, 90), (0, 0, tape_w * 2, tape_h * 2), width=2, border_radius=4)
            tape_surf = pygame.transform.smoothscale(tape_surf_2x, (tape_w, tape_h))
            target_surface.blit(tape_surf, (tape_x, cur_hero_y - 7))

            # 文字渲染与平滑过渡色 (Letter-spacing 高级字距排版，告别假粗体粘连)
            tr = int(31 + (215 - 31) * hover_val)
            tg = int(35 + (120 - 35) * hover_val)
            tb = int(43 + (10 - 43) * hover_val)
            title_col = (tr, tg, tb)

            ht_surf = _render_spaced_text(hero_title_font, "进入对话", title_col, spacing=6)
            hs_surf = _render_spaced_text(hero_sub_font, "· START STORY ·", (192, 104, 0), spacing=2)
            tw, th = ht_surf.get_size()
            sw, sh = hs_surf.get_size()

            # 核心：内容组绝对居中排版与副标对齐
            text_col_w = max(tw, sw)
            icon_w, icon_h = 20, 20
            gap = 14
            total_content_w = icon_w + gap + text_col_w

            content_x = hero_x + (hero_w - total_content_w) // 2
            text_col_x = content_x + icon_w + gap

            # 三角精灵小图标 (悬浮时完全静止锁定，无晃动与多余位移)
            tri_x = content_x
            tri_y = cur_hero_y + (hero_h - icon_h) // 2
            target_surface.blit(triangle_small, (tri_x, tri_y))

            # 主副标垂直居中，且副标在主标中轴线上严格水平居中
            text_block_h = th + 4 + sh
            text_y = cur_hero_y + (hero_h - text_block_h) // 2

            ht_x = text_col_x + (text_col_w - tw) // 2
            hs_x = text_col_x + (text_col_w - sw) // 2

            target_surface.blit(ht_surf, (ht_x, text_y))
            target_surface.blit(hs_surf, (hs_x, text_y + th + 4))

            # 右下方功能坞（图1定版：圆角矩形 + 白色和纸风格 · 3 项精简版）
            dock_shadow = pygame.Surface((dock_w + 14, dock_h + 14), pygame.SRCALPHA)
            pygame.draw.rect(dock_shadow, (0, 0, 0, 75), (7, 7, dock_w, dock_h), border_radius=8)
            target_surface.blit(dock_shadow, (dock_x - 7, dock_y - 7))

            dock_bg = pygame.Surface((dock_w, dock_h), pygame.SRCALPHA)
            pygame.draw.rect(dock_bg, (253, 251, 247, 246), (0, 0, dock_w, dock_h), border_radius=8)
            pygame.draw.rect(dock_bg, (200, 195, 185), (0, 0, dock_w, dock_h), width=1, border_radius=8)
            target_surface.blit(dock_bg, (dock_x, dock_y))

            dock_items = [
                ("设置", "CONFIG"),
                ("回忆", "LOG"),
                ("离开", "EXIT")
            ]

            for i, (cn, en) in enumerate(dock_items):
                r_item = rect_dock_items[i]
                is_item_hover = (hover_d == i)

                if is_item_hover:
                    hover_surf = pygame.Surface((r_item.width, r_item.height), pygame.SRCALPHA)
                    pygame.draw.rect(hover_surf, (255, 155, 0, 38), (0, 0, r_item.width, r_item.height))
                    target_surface.blit(hover_surf, (r_item.x, r_item.y))
                    pygame.draw.rect(target_surface, (215, 120, 10), (r_item.x + 12, r_item.y + dock_h - 2, r_item.width - 24, 2))

                cn_col = (215, 120, 10) if is_item_hover else (45, 50, 62)
                en_col = (215, 120, 10) if is_item_hover else (118, 124, 138)

                cn_s = dock_cn_font.render(cn, True, cn_col)
                en_s = dock_en_font.render(en, True, en_col)

                target_surface.blit(cn_s, (r_item.x + (r_item.width - cn_s.get_width()) // 2, r_item.y + 9))
                target_surface.blit(en_s, (r_item.x + (r_item.width - en_s.get_width()) // 2, r_item.y + 28))

                if i < 2:
                    pygame.draw.line(target_surface, (220, 215, 205), (r_item.right, r_item.y + 14), (r_item.right, r_item.y + dock_h - 14), 1)

        # 开场动画视频完整播放（严格禁止任何点击或按键跳过，仅首次启动播放，返回主界面直接呈现静帧）
        _skipped_intro = getattr(self, "intro_played", False)
        if not _skipped_intro:
            self.intro_played = True
            pygame.event.clear()
            player: VideoCapture = VideoCapture("assets/ui/title_end_m.wmv")
            is_opened: bool = player.isOpened()
            played_frames = 0
            while is_opened:
                clock.tick(30)
                for event in pygame.event.get():
                    if event.type == QUIT:
                        player.release()
                        self.exit()
                        sys_exit()
                    # 无论任何按键或鼠标点击，均直接忽略并消耗，确保动画无论如何不会被跳过
                is_opened, frame = player.read()
                if not is_opened:
                    break
                frame = pygame.surfarray.make_surface(cvtColor(frame, COLOR_RGB2BGR).swapaxes(0, 1))
                frame = pygame.transform.scale(frame, self.screen.get_size())
                self.screen.blit(frame, (0, 0))
                pygame.display.flip()
                played_frames += 1

            player.release()
            pygame.event.clear()

            # 视频自然播毕后，平滑消融 (Crossfade) 直接过渡至完整标题主页（包含进入对话按钮与完整布局，0 顿挫 0 掉帧）
            if played_frames > 0:
                last_frame = self.screen.copy()
                target_title = pygame.Surface((1280, 720))
                _render_title_base(target_title, hover_h=0.0, hover_d=-1, anim_time=0.0)
                fade_overlay = target_title.copy()
                for alpha in range(0, 256, 18):
                    clock.tick(50)
                    self.screen.blit(last_frame, (0, 0))
                    fade_overlay.set_alpha(alpha)
                    self.screen.blit(fade_overlay, (0, 0))
                    pygame.display.flip()

        pygame.event.clear()

        # 非首次启动时从全黑淡入标题页（首次启动已有视频→crossfade衔接）
        if _skipped_intro:
            _fade_in = pygame.Surface((1280, 720))
            _fade_in.fill((0, 0, 0))
            for _a in range(255, -1, -8):
                clock.tick(30)
                _render_title_base(self.screen, 0.0, -1, 0.0)
                _fade_in.set_alpha(_a)
                self.screen.blit(_fade_in, (0, 0))
                pygame.display.flip()

        hero_hover_anim: float = 0.0

        while is_running:
            clock.tick(30)
            cur_t = time()
            mx, my = pygame.mouse.get_pos()

            # 悬停判定与平滑动效插值
            hover_hero = (not exit_dialog_open) and rect_hero.collidepoint(mx, my)
            target_hero_hover = 1.0 if hover_hero else 0.0
            hero_hover_anim += (target_hero_hover - hero_hover_anim) * 0.22

            hover_dock = -1
            if not exit_dialog_open:
                for idx, r in enumerate(rect_dock_items):
                    if r.collidepoint(mx, my):
                        hover_dock = idx
                        break

            for event in pygame.event.get():
                if event.type == QUIT:
                    self.exit()
                    sys_exit()

                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        if exit_dialog_open:
                            exit_dialog_open = False
                        else:
                            exit_dialog_open = True
                    elif event.key in (K_RETURN, K_SPACE):
                        if not exit_dialog_open:
                            is_running = False

                elif event.type == MOUSEBUTTONDOWN:
                    mx, my = event.pos
                    if event.button == 1:
                        if exit_dialog_open:
                            if rect_dia_confirm.collidepoint(mx, my):
                                self.exit()
                                sys_exit()
                            elif rect_dia_cancel.collidepoint(mx, my):
                                exit_dialog_open = False
                            else:
                                if not pygame.Rect(dia_x, dia_y, dia_w, dia_h).collidepoint(mx, my):
                                    exit_dialog_open = False
                        else:
                            if rect_hero.collidepoint(mx, my):
                                is_running = False
                            elif rect_dock_items[0].collidepoint(mx, my):
                                self.system_menu()
                            elif rect_dock_items[1].collidepoint(mx, my):
                                # 从标题屏进回忆：载入分支或清空记录后（返回 True）才同步并开始游戏；
                                # 仅浏览不操作（返回 False）则留在标题屏
                                if self.history_menu():
                                    self.sync_after_history_reload()
                                    is_running = False
                            elif rect_dock_items[2].collidepoint(mx, my):
                                exit_dialog_open = True

            # 窗边浮尘更新与微动
            p_layer.fill((0, 0, 0, 0))
            for p in particles:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                if p["x"] < 580 or p["y"] < 120:
                    p["x"] = p["ox"] + randint(-30, 30)
                    p["y"] = p["oy"] + randint(-30, 30)
                pygame.draw.circle(p_layer, (255, 215, 120, int(p["a"] * 0.4)), (int(p["x"]), int(p["y"])), int(p["r"] * 2.0))
                pygame.draw.circle(p_layer, (255, 245, 200, int(p["a"])), (int(p["x"]), int(p["y"])), int(p["r"]))

            # 绘制主场景底板与 UI
            _render_title_base(self.screen, hero_hover_anim, hover_dock, cur_t)

            # ---------------- 退出确认弹窗（图3定版） ----------------
            if exit_dialog_open:
                dark_mask = pygame.Surface((1280, 720), pygame.SRCALPHA)
                pygame.draw.rect(dark_mask, (0, 0, 0, 195), (0, 0, 1280, 720))
                self.screen.blit(dark_mask, (0, 0))

                dia_shadow = pygame.Surface((dia_w + 24, dia_h + 24), pygame.SRCALPHA)
                pygame.draw.rect(dia_shadow, (0, 0, 0, 120), (12, 12, dia_w, dia_h), border_radius=12)
                self.screen.blit(dia_shadow, (dia_x - 12, dia_y - 12))

                dia_card = pygame.Surface((dia_w, dia_h), pygame.SRCALPHA)
                pygame.draw.rect(dia_card, (250, 248, 245), (0, 0, dia_w, dia_h), border_radius=12)
                pygame.draw.rect(dia_card, (215, 120, 10, 60), (0, 0, dia_w, dia_h), width=1, border_radius=12)
                self.screen.blit(dia_card, (dia_x, dia_y))

                dt_s = dialog_title_font.render("要结束与墨小菊的相处吗？", True, (31, 35, 43))
                self.screen.blit(dt_s, (dia_x + (dia_w - dt_s.get_width()) // 2, dia_y + 28))

                ds1 = dialog_sub_font.render("当前的对话记忆与亲密度已自动存盘。", True, (92, 98, 112))
                ds2 = dialog_sub2_font.render("随时可以重新启动应用继续相处。", True, (118, 124, 138))
                self.screen.blit(ds1, (dia_x + (dia_w - ds1.get_width()) // 2, dia_y + 68))
                self.screen.blit(ds2, (dia_x + (dia_w - ds2.get_width()) // 2, dia_y + 92))

                is_can_hover = rect_dia_cancel.collidepoint(mx, my)
                pygame.draw.rect(self.screen, (226, 221, 211) if is_can_hover else (237, 232, 223), rect_dia_cancel, border_radius=6)
                pygame.draw.rect(self.screen, (190, 180, 165) if is_can_hover else (208, 200, 184), rect_dia_cancel, width=1, border_radius=6)
                bc_txt = btn_font.render("继续相处", True, (31, 35, 43) if is_can_hover else (45, 50, 62))
                self.screen.blit(bc_txt, (rect_dia_cancel.x + (rect_dia_cancel.width - bc_txt.get_width()) // 2, rect_dia_cancel.y + (rect_dia_cancel.height - bc_txt.get_height()) // 2))

                is_conf_hover = rect_dia_confirm.collidepoint(mx, my)
                pygame.draw.rect(self.screen, (255, 155, 0) if is_conf_hover else (215, 120, 10), rect_dia_confirm, border_radius=6)
                pygame.draw.rect(self.screen, (255, 200, 100) if is_conf_hover else (255, 155, 0), rect_dia_confirm, width=1, border_radius=6)
                bcf_txt = btn_font.render("确认离开", True, (255, 255, 255))
                self.screen.blit(bcf_txt, (rect_dia_confirm.x + (rect_dia_confirm.width - bcf_txt.get_width()) // 2, rect_dia_confirm.y + (rect_dia_confirm.height - bcf_txt.get_height()) // 2))

            pygame.display.flip()

        # ---------------- 电影级平滑暗转 (Fade to Black) ----------------
        fade_black = pygame.Surface((1280, 720))
        fade_black.fill((0, 0, 0))
        last_screen = self.screen.copy()

        for alpha in range(0, 256, 14):
            clock.tick(40)
            self.screen.blit(last_screen, (0, 0))
            fade_black.set_alpha(alpha)
            self.screen.blit(fade_black, (0, 0))
            pygame.display.flip()

        self.screen.fill((0, 0, 0))
        pygame.display.flip()

        if not hasattr(self, 'daisymo') or self.daisymo is None:
            self.daisymo = DaisyMo(self.conversation, on_first_meet=None)
        pygame.event.clear()
        return self

    def wrap_text(self, font: pygame.font.FontType, text: str, max_width: int) -> List[str]:
        """将长文本按照指定像素宽度折行（二分查找断点，O(n log n)）

        旧实现逐字符拼串调 font.size()，是 O(n²)；中文 OTF 的 size() ~143µs/次，
        长对白会在「进回忆界面折行」与「打字机每帧折行」两处造成明显卡顿。
        """
        if not text:
            return []

        lines: List[str] = []
        n = len(text)
        lo = 0
        while lo < n:
            # 二分查找 [lo, n] 内能放下的最大前缀末尾
            low, high = lo, n
            best = lo
            while low <= high:
                mid = (low + high) // 2
                if font.size(text[lo:mid])[0] <= max_width:
                    best = mid
                    low = mid + 1
                else:
                    high = mid - 1
            if best <= lo:
                # 连一个字符都放不下，强制放一个，避免死循环
                lines.append(text[lo:lo + 1])
                lo += 1
            else:
                lines.append(text[lo:best])
                lo = best
        return lines

    def start_typewriter(self, text: str) -> None:
        """启动打字机"""
        self.ui.current_text = text
        self.ui.display_text = ""
        self.ui.current_text_index = 0
        self.ui.last_type_time = time()
        self.ui.typewriter_done = False
        if hasattr(self, 'dialogue_scrollbar') and self.dialogue_scrollbar:
            self.dialogue_scrollbar.reset()

    def step_typewriter(self) -> None:
        """更新打字机字数"""
        if self.ui.current_text_index < len(self.ui.current_text):
            if time() - self.ui.last_type_time >= self.ui.typewriter_interval:
                self.ui.current_text_index += 1
                self.ui.display_text = self.ui.current_text[: self.ui.current_text_index]
                self.ui.last_type_time = time()
        else:
            self.ui.typewriter_done = True

    def skip_typewriter(self) -> None:
        """快速显示全部对白"""
        self.ui.current_text_index = len(self.ui.current_text)
        self.ui.display_text = self.ui.current_text
        self.ui.typewriter_done = True

    def draw_text_shadow(self, surface: pygame.SurfaceType, font: pygame.font.FontType,
                         text: str, pos: Tuple[int, int], color: Tuple[int, int, int],
                         shadow_color: Tuple[int, int, int] = (0, 0, 0)) -> None:
        """绘制带柔和文字阴影的正文字"""
        x, y = pos
        shadow_surf = font.render(text, True, shadow_color)
        surface.blit(shadow_surf, (x + 1, y + 1))
        text_surf = font.render(text, True, color)
        surface.blit(text_surf, (x, y))

    def set_mode(self, new_mode: int) -> None:
        """切换发言与对白模式，并统一输入法与键盘长按重复状态"""
        self.ui.mode = new_mode
        if hasattr(self, 'player_box'):
            self.player_box.is_active = (self.ui.mode == PLAYER)
            if self.ui.mode == PLAYER:
                self.player_box.cursor = len(self.player_box.text)
                self.player_box.sel_start = self.player_box.cursor
                self.player_box.sel_end = self.player_box.cursor
        if self.ui.mode == PLAYER:
            pygame.key.start_text_input()
            pygame.key.set_repeat(300, 35)
            self.ui.player_cursor = len(self.ui.player_input)
            self.ui.player_sel_start = self.ui.player_cursor
            self.ui.player_sel_end = self.ui.player_cursor
            self.ui.player_dragging = False
        else:
            pygame.key.stop_text_input()
            pygame.key.set_repeat(0)
            self.ui.player_dragging = False

    def sync_after_history_reload(self) -> None:
        """从回忆界面清空或载入新分支后，实时热同步小菊立绘、背景、对白与视口状态"""
        if not hasattr(self, 'daisymo') or self.daisymo is None:
            self.daisymo = DaisyMo(self.conversation, on_first_meet=None)

        # 1. 若聊天记录被清空
        if not self.conversation:
            init_res = {
                "where": "小菊卧室白天",
                "face": "狡猾-说",
                "body": "便服单叉腰",
                "text": "呼……笨蛋邱诚，发什么呆呢？有什么想跟姐姐说的吗？",
                "bgm": "",
                "sfx": ""
            }
            self.daisymo.next(init_res)
            self.set_mode(DAISYMO)
            self.start_typewriter(DaisyMo.text)
            if hasattr(self, "dialogue_scrollbar") and self.dialogue_scrollbar:
                self.dialogue_scrollbar.reset()
            if hasattr(self, "player_box") and self.player_box:
                self.player_box.text = ""
                self.player_box.cursor = 0
                self.player_box.sel_start = 0
                self.player_box.sel_end = 0
            return

        # 2. 若载入了历史分支，恢复最后一条小菊发言的立绘与场景
        for m in reversed(self.conversation.messages()):
            if m.get("role") == "assistant":
                p = parse_scene(m.get("content", ""), clean_text=remove_emojis)
                if p and p.get("text"):
                    self.daisymo.next(p)
                    break

        self.set_mode(DAISYMO)
        self.start_typewriter(DaisyMo.text)
        self.skip_typewriter()
        if hasattr(self, "dialogue_scrollbar") and self.dialogue_scrollbar:
            self.dialogue_scrollbar.reset()
        if hasattr(self, "player_box") and self.player_box:
            self.player_box.text = ""
            self.player_box.cursor = 0
            self.player_box.sel_start = 0
            self.player_box.sel_end = 0

    def main(self) -> str:
        """主游戏对话循环"""
        run: bool = True
        clock: pygame.time.Clock = pygame.time.Clock()
        blink: BlinkCursor = BlinkCursor()

        # 输入法与长按计时已由 self.player_box 内聚自治接管

        # 初始化小菊（立绘、背景、对白全部预加载就绪）
        self.daisymo.init()
        self.daisymo.update_default_size().update_offset_center()
        self.start_typewriter(DaisyMo.text)

        # 首次启动且无 API Key，唤醒设置
        if DaisyMo.first_meet:
            # 预绘一帧游戏底图，供弹窗获取高质量静态快照背景
            if DaisyMo.default_back:
                self.screen.blit(DaisyMo.default_back, (0, 0))
            if self.daisymo.photos:
                for each in DaisyMo.photos:
                    self.screen.blits(((each[1], DaisyMo.offset), (each[0], DaisyMo.offset)))
            res = self.system_menu()
            if res == "title":
                return "title"

        # 按钮热区定义 (1280x720 坐标系)
        rect_auto    = pygame.Rect(924, 680, 29, 29)
        rect_skip    = pygame.Rect(960, 680, 29, 29)
        rect_log     = pygame.Rect(996, 680, 29, 29)

        rect_sys     = pygame.Rect(1032, 685, 74, 21)
        rect_lock    = pygame.Rect(1115, 685, 29, 29)

        rect_favorite = pygame.Rect(133, 564, 28, 28)
        rect_voice    = pygame.Rect(165, 564, 28, 28)
        rect_revoice  = pygame.Rect(197, 564, 28, 28)

        rect_mode_toggle = pygame.Rect(425, 567, 130, 25)
        rect_dialogue_box = pygame.Rect(232, 600, 840, 70)
        rect_send_btn    = pygame.Rect(1005, 602, 65, 28)

        # 自绘和风微型垂直滚动条（位于对话框右边缘内侧：x=1064, y=604, w=6, h=74）
        self.dialogue_scrollbar = DialogueScrollBar(pygame.Rect(1064, 604, 6, 74), visible_lines=3)

        fade_in_alpha: int = 255
        _fade_surf: pygame.SurfaceType = pygame.Surface((1280, 720))
        _fade_surf.fill((0, 0, 0))
        self._in_game_mode = True

        while run:
            clock.tick(Screen.FPS)
            blink.tick()
            mouse_x, mouse_y = pygame.mouse.get_pos()

            # 检查异步回复与思考超时（1分钟超时保护）
            if self.ui.is_thinking:
                if not self.chat_queue.empty():
                    q_item = self.chat_queue.get()
                    if isinstance(q_item, tuple):
                        req_id, res = q_item
                    else:
                        req_id, res = getattr(self, "current_req_id", 0), q_item

                    # 仅接收当前请求的最新响应，抛弃超时的旧响应
                    if req_id == getattr(self, "current_req_id", 0):
                        self.ui.is_thinking = False
                        if not res:
                            self.start_typewriter("……唔，网络或者API配置好像有点问题，没连上。你去检查一下设置吧！")
                        else:
                            self.daisymo.next(res)
                            if not DaisyMo.text:
                                self.start_typewriter("……唔，网络或者API配置好像有点问题，没连上。你去检查一下设置吧！")
                            else:
                                self.start_typewriter(DaisyMo.text)
                                self.daisymo.auto_save()

                elif time() - getattr(self, "thinking_start_time", time()) > 60.0:
                    # 1 分钟超时未响应保护
                    self.ui.is_thinking = False
                    self.ui.current_req_id = getattr(self, "current_req_id", 0) + 1
                    while not self.chat_queue.empty():
                        try:
                            self.chat_queue.get_nowait()
                        except Exception:
                            break
                    self.start_typewriter("……唔，大模型超过1分钟都没有响应呢。可能是网络不稳定或者服务商暂时堵车了，你去检查一下设置或稍后再试吧！")
                else:
                    # 思考中的动态提示动效（点动循环：. -> .. -> ...）
                    dots = int((time() * 2.5) % 3) + 1
                    self.ui.display_text = f"『 墨小菊正在思考{'.' * dots} 』"

            if not self.ui.is_thinking:
                self.step_typewriter()

            # 事件循环
            for event in pygame.event.get():
                if event.type == QUIT:
                    run = False
                    break

                # UI 隐藏时，任意键/点击均唤回
                if self.ui.ui_hidden:
                    if event.type == MOUSEBUTTONDOWN or event.type == KEYDOWN:
                        self.ui.ui_hidden = False
                    continue

                in_dialogue = rect_dialogue_box.collidepoint(mouse_x, mouse_y) or self.dialogue_scrollbar.rect.collidepoint(mouse_x, mouse_y)

                # 滚轮事件（现代 Pygame MOUSEWHEEL，光标在对话区即可触发，绝不向下穿透为点击）
                if event.type == pygame.MOUSEWHEEL:
                    if self.ui.mode == DAISYMO and in_dialogue:
                        self.dialogue_scrollbar.handle_event(event, mouse_x, mouse_y, in_dialogue_area=True)
                    continue

                if event.type == MOUSEBUTTONDOWN:
                    mx, my = event.pos

                    # 传统滚轮事件分流（Button 4 向上，Button 5 向下，无条件阻断，绝不穿透为点击）
                    if event.button in (4, 5):
                        if self.ui.mode == DAISYMO and in_dialogue:
                            self.dialogue_scrollbar.handle_event(event, mx, my, in_dialogue_area=True)
                        continue

                    # 滚动条滑块拖拽与轨道点击（仅左键点击滚动条区域时拦截）
                    if self.ui.mode == DAISYMO and self.dialogue_scrollbar.is_visible:
                        thumb_rect = self.dialogue_scrollbar._get_thumb_rect()
                        if self.dialogue_scrollbar.rect.collidepoint(mx, my) or thumb_rect.collidepoint(mx, my):
                            self.dialogue_scrollbar.handle_event(event, mx, my, in_dialogue_area=in_dialogue)
                            continue

                    # 仅响应鼠标左键点击 (Button 1)，右键与中键绝不触发按钮与跳转
                    if event.button != 1:
                        continue

                    # 1. 底部功能栏点击
                    if rect_auto.collidepoint(mx, my):
                        self.ui.is_auto = not self.ui.is_auto
                    elif rect_skip.collidepoint(mx, my):
                        if self.ui.is_thinking:
                            continue  # 思考保护：思考中禁止快进
                        if not self.ui.typewriter_done:
                            self.skip_typewriter()
                        else:
                            self.set_mode(PLAYER)
                    elif rect_log.collidepoint(mx, my):
                        if self.history_menu():
                            self.sync_after_history_reload()
                        # 从回忆界面回到主界面时做一次全屏淡入
                        self.start_fade_in()
                    elif rect_sys.collidepoint(mx, my):
                        res = self.system_menu()
                        if res == "title":
                            return "title"
                    elif rect_lock.collidepoint(mx, my):
                        self.ui.ui_hidden = True
                        self.ui.ui_hidden_time = time()

                    # 2. 铭牌珍藏、语音播放与重新生成按钮
                    elif rect_favorite.collidepoint(mx, my):
                        cur_dialogue = self.ui.display_text if self.ui.mode == DAISYMO else DaisyMo.text
                        if cur_dialogue and not self.ui.is_thinking:
                            is_fav = DaisyMo.toggle_favorite(cur_dialogue)
                            self.show_toast("已加入珍藏" if is_fav else "已移出珍藏")

                    elif rect_voice.collidepoint(mx, my):
                        cur_dialogue = self.ui.display_text if self.ui.mode == DAISYMO else DaisyMo.text
                        # 若当前正在加载解析或正在朗读，点击即可独占打断！空闲时则播放(优先读取本地缓存)
                        if (self.ui.is_tts_loading or self.ui.is_voice_playing) or (cur_dialogue and not self.ui.is_thinking):
                            self.play_tts_voice(cur_dialogue, force_refresh=False)

                    elif rect_revoice.collidepoint(mx, my):
                        cur_dialogue = self.ui.display_text if self.ui.mode == DAISYMO else DaisyMo.text
                        # 重新生成语音：绕过缓存并强制重新请求 API 合成新音频
                        if cur_dialogue and not self.ui.is_thinking:
                            self.play_tts_voice(cur_dialogue, force_refresh=True)

                    # 2. 发言模式切换按钮
                    elif rect_mode_toggle.collidepoint(mx, my):
                        if self.ui.is_thinking:
                            continue  # 思考保护：思考中禁止切换发言模式
                        self.set_mode(PLAYER if self.ui.mode == DAISYMO else DAISYMO)

                    # 3. 对话框主区域点击
                    elif rect_dialogue_box.collidepoint(mx, my):
                        if self.ui.is_thinking:
                            continue  # 思考保护：思考中点击对话框不能继续、不能跳过、不能切入输入模式！
                        if self.ui.mode == DAISYMO:
                            if not self.ui.typewriter_done:
                                self.skip_typewriter()
                            else:
                                self.set_mode(PLAYER)
                        elif self.ui.mode == PLAYER:
                            if rect_send_btn.collidepoint(mx, my):
                                self._submit_player_message()
                            else:
                                if self.player_box.handle_event(event, mx, my, self._get_clipboard_text, self._set_clipboard_text):
                                    self.ui.player_input = self.player_box.text

                elif event.type == MOUSEMOTION:
                    if self.ui.mode == DAISYMO:
                        self.dialogue_scrollbar.handle_event(event, event.pos[0], event.pos[1], in_dialogue_area=in_dialogue)
                    elif self.ui.mode == PLAYER:
                        if self.player_box.handle_event(event, event.pos[0], event.pos[1], self._get_clipboard_text, self._set_clipboard_text):
                            self.ui.player_input = self.player_box.text

                elif event.type == MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.ui.mode == DAISYMO:
                            self.dialogue_scrollbar.handle_event(event, event.pos[0], event.pos[1], in_dialogue_area=in_dialogue)
                        elif self.ui.mode == PLAYER:
                            if self.player_box.handle_event(event, event.pos[0], event.pos[1], self._get_clipboard_text, self._set_clipboard_text):
                                self.ui.player_input = self.player_box.text

                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        run = False

                    elif event.key == K_F1:
                        res = self.system_menu()
                        if res == "title":
                            return "title"

                    elif event.key == K_TAB:
                        if self.ui.is_thinking:
                            continue  # 思考保护：思考中禁止 Tab 切换
                        self.set_mode(PLAYER if self.ui.mode == DAISYMO else DAISYMO)

                    elif event.key == K_SPACE and self.ui.mode == DAISYMO:
                        if self.ui.is_thinking:
                            continue  # 思考保护：思考中按空格禁止跳过或切入输入模式
                        if not self.ui.typewriter_done:
                            self.skip_typewriter()
                        else:
                            self.set_mode(PLAYER)

                    elif self.ui.mode == PLAYER:
                        if event.key == K_RETURN:
                            self._submit_player_message()
                        else:
                            if self.player_box.handle_event(event, mx, my, self._get_clipboard_text, self._set_clipboard_text):
                                self.ui.player_input = self.player_box.text

                    elif self.ui.mode == DAISYMO and event.key == K_1:
                        self.daisymo.random_face()
                    elif self.ui.mode == DAISYMO and event.key == K_2:
                        self.daisymo.random_body()
                    elif self.ui.mode == DAISYMO and event.key == K_3:
                        self.daisymo.random_back()

                elif event.type == KEYUP and self.ui.mode == PLAYER:
                    self.player_box.handle_event(event, mx, my, self._get_clipboard_text, self._set_clipboard_text)

                elif event.type == TEXTINPUT and self.ui.mode == PLAYER:
                    if self.player_box.handle_event(event, mx, my, self._get_clipboard_text, self._set_clipboard_text):
                        self.ui.player_input = self.player_box.text

            # 长按退格与 Delete 快速连删由 player_box 自治响应
            if self.ui.mode == PLAYER:
                if self.player_box.tick_continuous_delete(time()):
                    self.ui.player_input = self.player_box.text

            # ----------------- 绘制渲染 -----------------
            # 1. 场景背景与立绘
            if DaisyMo.default_back:
                self.screen.blit(DaisyMo.default_back, (0, 0))
            else:
                self.screen.fill(BG_DARK)

            if self.daisymo.photos:
                for each in DaisyMo.photos:
                    self.screen.blits(((each[1], DaisyMo.offset), (each[0], DaisyMo.offset)))

            # UI 隐藏模式（提示仅在进入前 0.5 秒内显示，超时自动隐去以呈现纯净全屏画面）
            if self.ui.ui_hidden:
                if time() - getattr(self, "ui_hidden_time", 0.0) < 0.5:
                    hint_surf = Screen.dfont.render("〈 点击屏幕任意处恢复界面 〉", True, GOLD_COLOR)
                    hx = (1280 - hint_surf.get_width()) // 2
                    pygame.draw.rect(self.screen, (16, 20, 28), (hx - 16, 20, hint_surf.get_width() + 32, 28), border_radius=14)
                    pygame.draw.rect(self.screen, DCOLOR, (hx - 16, 20, hint_surf.get_width() + 32, 28), width=1, border_radius=14)
                    self.screen.blit(hint_surf, (hx, 25))
                pygame.display.flip()
                continue

            # 2. 官方底框分层资产
            self.screen.blit(self.main_botm, (0, 360))
            self.screen.blit(self.main_botm_word, (0, 360))
            self.screen.blit(self.main_botm_line, (0, 360))

            # 3. 姓名框与图标 (左侧紧凑三联排: 珍藏 133, 播放 165, 重新生成 197)
            cur_dialogue = self.ui.display_text if self.ui.mode == DAISYMO else DaisyMo.text
            is_fav = DaisyMo.is_favorited(cur_dialogue)
            fav_hover = rect_favorite.collidepoint(mouse_x, mouse_y)
            self.screen.blit(self.icon_favorite_over if (is_fav or fav_hover) else self.icon_favorite_normal, (133, 564))

            # 语音播放图标 (165, 564)：未配置时绝不点亮；解析中显示呼吸加载态；播放中稳定点亮
            is_tts_configured = bool(DaisyMo.tts_base_url.strip())
            voice_hover = rect_voice.collidepoint(mouse_x, mouse_y)
            if self.ui.is_voice_playing:
                # 正在发音朗读中：稳定点亮态
                self.screen.blit(self.icon_voice_over, (165, 564))
            elif self.ui.is_tts_loading:
                # 正在解析合成中：动态平滑呼吸加载动效 (alpha 100~255)
                b_alpha = int(100 + 155 * (0.5 + 0.5 * math.sin(time() * 8.0)))
                tmp_icon = self.icon_voice_over.copy()
                tmp_icon.set_alpha(b_alpha)
                self.screen.blit(tmp_icon, (165, 564))
            elif is_tts_configured and voice_hover:
                # 已配置且悬停：高亮预览
                self.screen.blit(self.icon_voice_over, (165, 564))
            else:
                # 未配置或未悬停：普通图标（未配置时绝不点亮）
                self.screen.blit(self.icon_voice_normal, (165, 564))

            # 重新生成语音图标 (197, 564)：未配置时显示不可用态；解析中呼吸动效；悬停高亮
            revoice_hover = rect_revoice.collidepoint(mouse_x, mouse_y)
            if not is_tts_configured:
                self.screen.blit(self.icon_revoice_unuseable, (197, 564))
            elif self.ui.is_tts_loading:
                b_alpha = int(100 + 155 * (0.5 + 0.5 * math.sin(time() * 8.0)))
                tmp_icon = self.icon_revoice_over.copy()
                tmp_icon.set_alpha(b_alpha)
                self.screen.blit(tmp_icon, (197, 564))
            elif revoice_hover:
                self.screen.blit(self.icon_revoice_over, (197, 564))
            else:
                self.screen.blit(self.icon_revoice_normal, (197, 564))

            self.screen.blit(self.main_botm_name, (232, 564))

            # 姓名文字居中排印 (DAISYMO: 墨小菊; PLAYER: 邱诚)
            name_text = "墨小菊" if self.ui.mode == DAISYMO else "邱诚"
            name_color = QCOLOR if self.ui.mode == DAISYMO else GOLD_COLOR
            nw, nh = Screen.name_font.size(name_text)
            nx = 232 + (180 - nw) // 2
            ny = 564 + (30 - nh) // 2
            self.draw_text_shadow(self.screen, Screen.name_font, name_text, (nx, ny), name_color)

            # 模式切换小胶囊 [Tab]
            mode_btn_bg = (35, 45, 60) if self.ui.mode == PLAYER else (45, 32, 18)
            mode_btn_border = (78, 205, 196) if self.ui.mode == PLAYER else (255, 180, 60)
            mode_btn_text = "[Tab] 查看小菊" if self.ui.mode == PLAYER else "[Tab] 我要发言"
            pygame.draw.rect(self.screen, mode_btn_bg, rect_mode_toggle, border_radius=4)
            pygame.draw.rect(self.screen, mode_btn_border, rect_mode_toggle, width=1, border_radius=4)
            mode_txt_surf = Screen.dfont.render(mode_btn_text, True, mode_btn_border)
            self.screen.blit(mode_txt_surf, (rect_mode_toggle.x + 8, rect_mode_toggle.y + 4))

            # 4. 对话内容区 (复用同一区域)
            if self.ui.mode == DAISYMO:
                # 状态 A: 墨小菊对白 (逐字打字机 + 滚动条视口切片 + 跳动倒三角)
                lines = self.wrap_text(Screen.font, self.ui.display_text, 818)
                self.dialogue_scrollbar.update_lines(len(lines))

                start_y = 604
                scroll_start = self.dialogue_scrollbar.scroll_index
                visible_slice = lines[scroll_start : scroll_start + 3]

                for i, line in enumerate(visible_slice):
                    self.draw_text_shadow(self.screen, Screen.font, line, (232, start_y + i * 32), QCOLOR)

                # 绘制自绘和风微型垂直滚动条（超出 3 行时自动渲染）
                self.dialogue_scrollbar.render(self.screen)

                # 打字完成后跳动光标：仅在当前视口包含最后一行时显示在行尾
                if self.ui.typewriter_done and not self.ui.is_thinking and lines:
                    last_line_idx = len(lines) - 1
                    if scroll_start <= last_line_idx < scroll_start + 3:
                        disp_line_idx = last_line_idx - scroll_start
                        last_line = visible_slice[disp_line_idx]
                        lw, _ = Screen.font.size(last_line)
                        tx = 232 + lw + 6
                        ty = start_y + disp_line_idx * 32 + int(math.sin(time() * 7.5) * 3)
                        self.screen.blit(self.main_triangle, (tx, ty))

            else:
                # 状态 B: 邱诚输入 (复用自治 TextInputBox 控件)
                if not self.player_box.text:
                    holder = Screen.dfont.render("想对小菊说些什么…… (按 Enter 发送，Tab 切换回对白)", True, MUTED_COLOR)
                    self.screen.blit(holder, (232, 604 + 4))
                else:
                    self.player_box.render(self.screen, blink.visible)

                # 发送按钮（纯文字居中，杜绝特殊符号方块乱码）
                send_bg = (255, 158, 27) if rect_send_btn.collidepoint(mouse_x, mouse_y) else (200, 110, 15)
                pygame.draw.rect(self.screen, send_bg, rect_send_btn, border_radius=4)
                pygame.draw.rect(self.screen, (255, 255, 255), rect_send_btn, width=1, border_radius=4)
                send_txt = Screen.dfont.render("发送", True, QCOLOR)
                self.screen.blit(send_txt, (rect_send_btn.x + (rect_send_btn.width - send_txt.get_width()) // 2,
                                            rect_send_btn.y + (rect_send_btn.height - send_txt.get_height()) // 2))

            # 5. 官方底部功能栏 (右侧精简：仅保留 SYSTEM 与 隐藏UI锁)
            self._draw_btn(rect_auto, self.btn_auto_on if self.ui.is_auto else (self.btn_auto_over if rect_auto.collidepoint(mouse_x, mouse_y) else self.btn_auto_normal))
            self._draw_btn(rect_skip, self.btn_skip_over if rect_skip.collidepoint(mouse_x, mouse_y) else self.btn_skip_normal)
            self._draw_btn(rect_log, self.btn_log_over if rect_log.collidepoint(mouse_x, mouse_y) else self.btn_log_normal)

            self._draw_btn(rect_sys, self.btn_sys_over if rect_sys.collidepoint(mouse_x, mouse_y) else self.btn_sys_normal)
            self._draw_btn(rect_lock, self.btn_lock_over if rect_lock.collidepoint(mouse_x, mouse_y) else self.btn_lock_normal)

            # 浮动提示 Toast (纯文本，无 Emoji)
            if self.ui.toast_text and (time() - self.ui.toast_time < 2.0):
                t_surf = Screen.card_font.render(self.ui.toast_text, True, GOLD_COLOR)
                tw, th = t_surf.get_size()
                tx = (1280 - tw) // 2
                ty = 510
                pygame.draw.rect(self.screen, (20, 24, 32), (tx - 16, ty - 6, tw + 32, th + 12), border_radius=6)
                pygame.draw.rect(self.screen, DCOLOR, (tx - 16, ty - 6, tw + 32, th + 12), width=1, border_radius=6)
                self.screen.blit(t_surf, (tx, ty))
            elif self.ui.toast_text and (time() - self.ui.toast_time >= 2.0):
                self.ui.toast_text = ""

            # 6. 右上角 Token 消耗与状态 HUD 模块（纯文字，无 Emoji）
            self._render_token_hud()

            # 7. 开局平滑暗转淡入 (Fade in from Black，约 0.4 秒平滑呈现)
            if fade_in_alpha > 0:
                _fade_surf.set_alpha(fade_in_alpha)
                self.screen.blit(_fade_surf, (0, 0))
                fade_in_alpha = max(0, fade_in_alpha - 5)

            # 8. 从回忆界面返回时的全屏淡入（按时间推进，与上面的开局淡入互不干扰）
            self.render_fade_overlay()

            pygame.display.flip()

        self.exit()
        return "exit"

    def _render_token_hud(self) -> None:
        """在游戏右上角渲染精致半透明磨砂 Token 与状态 HUD 模块（纯文字，无 Emoji）"""
        t = localtime()
        time_str = f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}"
        last_tok = DaisyMo.last_usage.get('total_tokens', 0)
        total_tok = DaisyMo.total_usage

        hud_w, hud_h = 340, 34
        hud_x = 1280 - hud_w - 20
        hud_y = 16

        # 半透明磨砂深色底框
        hud_surf = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        pygame.draw.rect(hud_surf, (16, 20, 28, 200), (0, 0, hud_w, hud_h), border_radius=8)
        pygame.draw.rect(hud_surf, (70, 80, 100, 180), (0, 0, hud_w, hud_h), width=1, border_radius=8)
        self.screen.blit(hud_surf, (hud_x, hud_y))

        # 横向精致排版：Token: xxx | 累计: xxx | HH:MM:SS
        t1 = Screen.dfont.render("Token: ", True, MUTED_COLOR)
        v1 = Screen.card_font.render(f"{last_tok:,}", True, GOLD_COLOR)
        div1 = Screen.dfont.render(" | ", True, (70, 80, 100))
        t2 = Screen.dfont.render("累计: ", True, MUTED_COLOR)
        v2 = Screen.card_font.render(f"{total_tok:,}", True, QCOLOR)
        div2 = Screen.dfont.render(" | ", True, (70, 80, 100))
        t3 = Screen.dfont.render(time_str, True, MUTED_COLOR)

        items = [t1, v1, div1, t2, v2, div2, t3]
        total_w = sum(it.get_width() for it in items)
        cur_x = hud_x + (hud_w - total_w) // 2
        for it in items:
            self.screen.blit(it, (cur_x, hud_y + (hud_h - it.get_height()) // 2))
            cur_x += it.get_width()

    def _draw_btn(self, rect: pygame.Rect, surf: pygame.SurfaceType) -> None:
        self.screen.blit(surf, (rect.x, rect.y))

    def _submit_player_message(self) -> None:
        """提交玩家发言给小菊并转入异步思考"""
        sent_text = self.player_box.text.strip() if hasattr(self, 'player_box') else self.ui.player_input.strip()
        if not sent_text or self.ui.is_thinking:
            return

        if hasattr(self, 'player_box'):
            self.player_box.text = ""
            self.player_box.cursor = 0
            self.player_box.sel_start = 0
            self.player_box.sel_end = 0
        self.ui.player_input = ""
        self.ui.player_cursor = 0
        self.ui.player_sel_start = 0
        self.ui.player_sel_end = 0

        if not DaisyMo.api_key:
            self.set_mode(DAISYMO)
            self.ui.is_thinking = False
            self.start_typewriter("哼，你连 API Key 都没填，姐姐听不见你说话！快去 SYSTEM 设置里填好！")
            return

        self.set_mode(DAISYMO)
        self.ui.is_thinking = True
        self.ui.thinking_start_time = time()
        self.ui.current_req_id = getattr(self, "current_req_id", 0) + 1
        req_id = self.ui.current_req_id
        self.ui.display_text = "『 墨小菊正在思考... 』"

        def _worker():
            res = self.daisymo.chat_then_parse(sent_text)
            self.chat_queue.put((req_id, res))

        Thread(target=_worker, daemon=True).start()

    def _get_clipboard_text(self) -> str:
        """安全读取 Windows 操作系统全局剪贴板文本（支持跨软件复制粘贴）"""
        if platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                user32.OpenClipboard.argtypes = [ctypes.c_void_p]
                user32.OpenClipboard.restype = ctypes.c_bool
                user32.CloseClipboard.argtypes = []
                user32.CloseClipboard.restype = ctypes.c_bool
                user32.GetClipboardData.argtypes = [ctypes.c_uint]
                user32.GetClipboardData.restype = ctypes.c_void_p
                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.restype = ctypes.c_bool

                CF_UNICODETEXT = 13
                if user32.OpenClipboard(None):
                    try:
                        h_data = user32.GetClipboardData(CF_UNICODETEXT)
                        if h_data:
                            p_str = kernel32.GlobalLock(h_data)
                            if p_str:
                                try:
                                    val = ctypes.c_wchar_p(p_str).value
                                    if val:
                                        return val.strip().replace('\r', '').replace('\n', '')
                                finally:
                                    kernel32.GlobalUnlock(h_data)
                    finally:
                        user32.CloseClipboard()
            except Exception:
                pass

        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            txt = root.clipboard_get()
            root.destroy()
            return txt.strip().replace('\r', '').replace('\n', '')
        except Exception:
            return ""

    def _set_clipboard_text(self, text: str) -> None:
        """安全写入 Windows 操作系统全局剪贴板文本"""
        if platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                user32.OpenClipboard.argtypes = [ctypes.c_void_p]
                user32.OpenClipboard.restype = ctypes.c_bool
                user32.CloseClipboard.argtypes = []
                user32.CloseClipboard.restype = ctypes.c_bool
                user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
                user32.SetClipboardData.restype = ctypes.c_void_p
                user32.EmptyClipboard.argtypes = []
                user32.EmptyClipboard.restype = ctypes.c_bool

                kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
                kernel32.GlobalAlloc.restype = ctypes.c_void_p
                kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalLock.restype = ctypes.c_void_p
                kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
                kernel32.GlobalUnlock.restype = ctypes.c_bool

                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 0x0002

                data = text.encode('utf-16le') + b'\x00\x00'
                if user32.OpenClipboard(None):
                    try:
                        user32.EmptyClipboard()
                        h_glb = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                        if h_glb:
                            p_buf = kernel32.GlobalLock(h_glb)
                            if p_buf:
                                ctypes.memmove(p_buf, data, len(data))
                                kernel32.GlobalUnlock(h_glb)
                                user32.SetClipboardData(CF_UNICODETEXT, h_glb)
                    finally:
                        user32.CloseClipboard()
                return
            except Exception:
                pass

        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(text)
            root.update()
            root.destroy()
        except Exception:
            pass

    def history_menu(self) -> bool:
        """全屏官方回忆界面 (Backlog，支持「历史」、「珍藏」与「分支存档」三标签分栏，支持一键备份与安全清空)"""
        # 静态素材已在 Screen.init 里加载并缓存，这里只做局部别名引用，避免每次进界面重新解析字体/图片
        bg_backlog = self.bg_backlog
        btn_slider = self.btn_slider
        btn_back_normal = self.btn_back_normal
        btn_back_over = self.btn_back_over
        btn_fav_normal = self.btn_fav_normal
        btn_fav_over = self.btn_fav_over
        btn_voice_normal = self.btn_voice_normal
        card_title_font = self.card_title_font
        card_sub_font = self.card_sub_font
        card_tag_font = self.card_tag_font
        dia_title_font = self.dia_title_font
        dia_sub_font = self.dia_sub_font
        dia_sub2_font = self.dia_sub2_font
        dia_btn_font = self.dia_btn_font
        dia_input_font = self.dia_input_font

        rect_back = pygame.Rect(1165, 625, 76, 76)
        rect_tab_hist = pygame.Rect(165, 42, 68, 30)
        rect_tab_fav = pygame.Rect(245, 42, 95, 30)
        rect_tab_backup = pygame.Rect(350, 42, 115, 30)

        # 顶部操作按钮 (位于右侧空白安全区，避免遮挡中央水印)
        rect_btn_backup = pygame.Rect(830, 42, 105, 30)
        rect_btn_clear = pygame.Rect(945, 42, 90, 30)
        rect_btn_new_backup = pygame.Rect(930, 42, 105, 30)

        confirm_dialog = ConfirmDialog(
            title_font=dia_title_font,
            sub_font=dia_sub_font,
            sub2_font=dia_sub2_font,
            btn_font=dia_btn_font
        )

        # 分支存档自定义命名 / 新建备份命名弹窗
        input_dialog = InputDialog(
            title_font=dia_title_font,
            label_font=dia_sub_font,
            hint_font=dia_sub2_font,
            btn_font=dia_btn_font,
            input_font=dia_input_font,
            max_length=history_mgr.TITLE_MAX_LEN
        )

        # 官方右侧滑道与圆纽扣滑块几何定义 (滑槽居中 x=1090.5, y=87~682, 行程 569px)
        track_top = 87
        track_bottom = 684
        track_h = 597
        slider_w, slider_h = btn_slider.get_size()
        travel = track_bottom - slider_h - track_top  # 569
        slider_x = 1076
        rect_track = pygame.Rect(1074, track_top, 32, track_h)
        is_dragging_slider: bool = False
        paper_rect = pygame.Rect(220, 80, 840, 540)

        # 确保历史对话与珍藏数据均已加载
        DaisyMo.load_favorites()
        if not self.conversation and os_path.exists("assets/DaisyMo_history.json"):
            try:
                with open("assets/DaisyMo_history.json", 'r', encoding="utf-8") as f:
                    saved_mem = json.load(f)
                if isinstance(saved_mem, list) and saved_mem:
                    self.conversation.replace_with(saved_mem)
            except Exception:
                pass

        hist_entries = []
        curr_calc_y = 10

        def refresh_hist_entries() -> None:
            """
            重新折行全部对白并缓存成行布局，同时算出内容总高度。
            只在数据变化时调用 —— 折行结果与 y 坐标随行一起缓存，渲染时不再重算。
            """
            nonlocal hist_entries, curr_calc_y
            hist_entries = []
            y = 10
            for msg in self.conversation.messages():
                role = msg.get("role")
                if role == "system":
                    continue
                content = msg.get("content", "")
                if role == "user":
                    speaker, color, text = "邱诚", (18, 100, 90), remove_emojis(content).strip()
                elif role == "assistant":
                    speaker, color, text = "墨小菊", (190, 95, 0), remove_emojis(reply_text(content)).strip()
                else:
                    continue

                lines = self.wrap_text(Screen.dfont, text, 810)
                hist_entries.append({
                    "speaker": speaker,
                    "text": text,
                    "color": color,
                    "y": y,
                    "lines": lines,
                })
                y += Screen.font.size(speaker)[1] + 4
                for line in lines:
                    y += Screen.dfont.size(line)[1] + 3
                y += 18
            y += 16
            curr_calc_y = y

        refresh_hist_entries()
        initial_max_scroll = max(0.0, curr_calc_y - paper_rect.height)

        active_tab = "history"  # "history" | "favorites" | "backups"
        scroll_y: float = -initial_max_scroll
        max_scroll: float = initial_max_scroll
        hist_dirty: bool = False
        running = True
        clock = pygame.time.Clock()

        # ---- 标签页正文缓存 ----
        # 每一帧画出来的正文其实完全一样，滚动只是最后那次 blit 的裁剪区在变。
        # 所以折行与正文表面只在数据变化时重建（dirty 标记），每帧只做 1 次带 clip 的 blit；
        # 随帧变化的部分（语音喇叭高亮、卡片 hover、按钮态）一律挪出缓存、每帧现画。
        body_cache: Dict[str, Dict[str, Any]] = {
            "history": {"surf": None, "max_scroll": 0.0, "rows": [], "dirty": True},
            "favorites": {"surf": None, "max_scroll": 0.0, "rows": [], "dirty": True},
            "backups": {"surf": None, "max_scroll": 0.0, "rows": [], "dirty": True},
        }

        def mark_dirty(*tabs: str) -> None:
            """置脏：没有参数时全部标签页作废"""
            for t in (tabs if tabs else tuple(body_cache.keys())):
                body_cache[t]["dirty"] = True

        # 备份列表的轻量签名：外部（或本界面）任何增删改名都会让签名变化，自动置脏
        backup_signature: Tuple[Any, ...] = ()

        def sync_backup_signature() -> None:
            nonlocal backup_signature
            sig = tuple((b.get("backup_id", ""), b.get("title", "")) for b in history_mgr.list_backups())
            if sig != backup_signature:
                backup_signature = sig
                body_cache["backups"]["dirty"] = True

        def handle_confirm_action(act: str, payload: Any) -> None:
            nonlocal scroll_y, hist_dirty, running
            if act == "clear":
                # 先让数据层读一遍当前记录去生成安全快照（它只读、不再动传入的列表），
                # 再让所有者自己清空 —— 以前是数据层拿到列表引用就地 clear 的，那个别名坑拆掉了。
                ok, auto_id = history_mgr.clear_active_history(self.conversation.messages())
                self.conversation.clear()
                self.show_toast("对话记录已重置（已自动生成安全快照）" if auto_id
                                else "对话记录已重置（此前仅是开场白，未留快照）")
                hist_dirty = True
                refresh_hist_entries()
                mark_dirty()
                scroll_y = 0.0
            elif act == "load_backup":
                backup_id = str(payload)
                if self.conversation:
                    # 自动快照：同名只保留一条（数据层负责覆盖），且开场白不会留档
                    history_mgr.create_backup(self.conversation.messages(), is_auto=True, title="切换分支前自动快照")
                ok, loaded_mem, msg = history_mgr.load_backup(backup_id)
                if ok:
                    self.conversation.replace_with(loaded_mem)
                    history_mgr.save_active_history(self.conversation.messages())
                    self.show_toast("已成功载入该时间线分支")
                    hist_dirty = True
                    refresh_hist_entries()
                    mark_dirty()
                    scroll_y = -max_scroll
                    # 载入完成即自动收起回忆界面，回到主界面（由主循环热同步小菊状态）
                    running = False
                else:
                    self.show_toast(msg)
            elif act == "delete_backup":
                backup_id = str(payload)
                ok, msg = history_mgr.delete_backup(backup_id)
                self.show_toast("已删除分支存档（可从 .trash 找回）" if ok else msg)

        def open_input_dialog(title: str, label: str, default_text: str, context: Any) -> None:
            """打开命名弹窗，并同步开启文本输入与输入法候选框锚点"""
            input_dialog.open(
                title=title,
                label=label,
                default_text=default_text,
                confirm_text="确认",
                cancel_text="取消",
                context=context
            )
            pygame.key.start_text_input()
            pygame.key.set_text_input_rect(input_dialog.rect_input)

        def handle_input_action(act: str, payload: Any) -> None:
            if act == "rename_backup":
                b_id, new_title = payload
                ok, msg = history_mgr.rename_backup(b_id, new_title)
                self.show_toast(f"已重命名为「{new_title}」" if ok else msg)
            elif act == "new_backup":
                if not self.conversation:
                    self.show_toast("当前暂无对话记录可备份")
                    return
                rec = history_mgr.create_backup(self.conversation.messages(), is_auto=False, title=str(payload or ""))
                if rec:
                    self.show_toast(f"已创建新分支存档：{rec['title']}")

        def _abs(x: int, y: int, w: int, h: int) -> pygame.Rect:
            """正文面内坐标 -> 屏幕坐标（供点击热区使用）"""
            return pygame.Rect(paper_rect.x + x, paper_rect.y + y + int(scroll_y), w, h)

        while running:
            clock.tick(30)
            mx, my = pygame.mouse.get_pos()
            click_actions = []

            backup_list = history_mgr.list_backups()
            sync_backup_signature()

            # 每帧现画的动态层：卡片底/边框要画在缓存正文之下，图标与按钮画在其上
            icon_blits: List[Tuple[pygame.SurfaceType, pygame.Rect]] = []
            backup_chrome: List[Tuple[int, bool]] = []
            backup_buttons: List[Dict[str, Any]] = []

            if active_tab == "history":
                cache = body_cache["history"]
                if cache["dirty"]:
                    text_surf = pygame.Surface((paper_rect.width, max(2000, curr_calc_y + 100)), pygame.SRCALPHA)
                    text_surf.fill((0, 0, 0, 0))
                    rows: List[Dict[str, Any]] = []

                    if not hist_entries:
                        empty_hint = "当前暂无对话记录。可返回主界面与墨小菊交谈，或在「分支存档」中载入历史。"
                        eh_surf = Screen.dfont.render(empty_hint, True, MUTED_COLOR)
                        text_surf.blit(eh_surf, ((paper_rect.width - eh_surf.get_width()) // 2, 200))
                        cache["max_scroll"] = 0.0
                    else:
                        for item in hist_entries:
                            spk_surf = Screen.font.render(item["speaker"], True, item["color"])
                            text_surf.blit(spk_surf, (10, item["y"]))
                            line_y = item["y"] + spk_surf.get_height() + 4
                            for line in item["lines"]:
                                line_surf = Screen.dfont.render(line, True, CHARCOAL_COLOR)
                                text_surf.blit(line_surf, (10, line_y))
                                line_y += line_surf.get_height() + 3
                            if item["speaker"] == "墨小菊" and item["text"]:
                                rows.append({"y": item["y"], "text": item["text"]})
                        cache["max_scroll"] = max(0.0, curr_calc_y - paper_rect.height)

                    cache["surf"] = text_surf
                    cache["rows"] = rows
                    cache["dirty"] = False

                text_surf = cache["surf"]
                max_scroll = cache["max_scroll"]
                scroll_y = max(-max_scroll, min(0.0, scroll_y))

                # 语音高亮与珍藏星标随帧变化，不进缓存
                for row in cache["rows"]:
                    rel_y = row["y"] + int(scroll_y)
                    if rel_y < -80 or rel_y > paper_rect.height + 20:
                        continue
                    text = row["text"]
                    rect_v = pygame.Rect(paper_rect.width - 70, row["y"] + 2, 22, 21)
                    rect_f = pygame.Rect(paper_rect.width - 36, row["y"] + 1, 24, 23)
                    if self.ui.is_voice_playing and getattr(self, "current_playing_text", "") == text:
                        v_icon = btn_voice_normal.copy()
                        v_icon.fill((255, 155, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    else:
                        v_icon = btn_voice_normal
                    icon_blits.append((v_icon, rect_v))
                    icon_blits.append((btn_fav_over if DaisyMo.is_favorited(text) else btn_fav_normal, rect_f))
                    click_actions.append((_abs(rect_v.x - 5, rect_v.y - 4, rect_v.width + 10, rect_v.height + 8), "voice", text))
                    click_actions.append((_abs(rect_f.x - 4, rect_f.y - 4, rect_f.width + 8, rect_f.height + 8), "fav", text))

            elif active_tab == "favorites":
                # 珍藏分栏
                cache = body_cache["favorites"]
                if cache["dirty"]:
                    fav_list = list(reversed(DaisyMo.favorites))
                    text_surf = pygame.Surface((paper_rect.width, max(2000, len(fav_list) * 140 + 100)), pygame.SRCALPHA)
                    text_surf.fill((0, 0, 0, 0))
                    rows: List[Dict[str, Any]] = []

                    if not fav_list:
                        empty_hint = "当前暂无珍藏对白，可在主界面点击名字旁边的星号加入珍藏。"
                        eh_surf = Screen.dfont.render(empty_hint, True, MUTED_COLOR)
                        text_surf.blit(eh_surf, ((paper_rect.width - eh_surf.get_width()) // 2, 200))
                        cache["max_scroll"] = 0.0
                    else:
                        curr_y = 10
                        for itm in fav_list:
                            spk = itm.get("role", "墨小菊")
                            f_text = itm.get("text", "")
                            f_time = itm.get("time", "")

                            spk_surf = Screen.font.render(spk, True, (190, 95, 0))
                            text_surf.blit(spk_surf, (10, curr_y))

                            if f_time:
                                time_surf = Screen.dfont.render(f"[{f_time}]", True, MUTED_COLOR)
                                text_surf.blit(time_surf, (10 + spk_surf.get_width() + 12, curr_y + 4))

                            line_y = curr_y + spk_surf.get_height() + 4
                            for line in self.wrap_text(Screen.dfont, f_text, 810):
                                line_surf = Screen.dfont.render(line, True, CHARCOAL_COLOR)
                                text_surf.blit(line_surf, (10, line_y))
                                line_y += line_surf.get_height() + 3

                            rows.append({"y": curr_y, "text": f_text})
                            curr_y = line_y + 18
                        cache["max_scroll"] = max(0.0, curr_y - paper_rect.height)

                    cache["surf"] = text_surf
                    cache["rows"] = rows
                    cache["dirty"] = False

                text_surf = cache["surf"]
                max_scroll = cache["max_scroll"]
                scroll_y = max(-max_scroll, min(0.0, scroll_y))

                for row in cache["rows"]:
                    rel_y = row["y"] + int(scroll_y)
                    if rel_y < -80 or rel_y > paper_rect.height + 20:
                        continue
                    f_text = row["text"]
                    rect_v = pygame.Rect(paper_rect.width - 70, row["y"] + 2, 22, 21)
                    rect_f = pygame.Rect(paper_rect.width - 36, row["y"] + 1, 24, 23)
                    if self.ui.is_voice_playing and getattr(self, "current_playing_text", "") == f_text:
                        v_icon = btn_voice_normal.copy()
                        v_icon.fill((255, 155, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    else:
                        v_icon = btn_voice_normal
                    icon_blits.append((v_icon, rect_v))
                    icon_blits.append((btn_fav_over, rect_f))
                    click_actions.append((_abs(rect_v.x - 5, rect_v.y - 4, rect_v.width + 10, rect_v.height + 8), "voice", f_text))
                    click_actions.append((_abs(rect_f.x - 4, rect_f.y - 4, rect_f.width + 8, rect_f.height + 8), "unfav", f_text))

            else:
                # 分支存档分栏 (active_tab == "backups")
                cache = body_cache["backups"]
                if cache["dirty"]:
                    text_surf = pygame.Surface((paper_rect.width, max(2000, len(backup_list) * 100 + 100)), pygame.SRCALPHA)
                    text_surf.fill((0, 0, 0, 0))
                    rows: List[Dict[str, Any]] = []

                    if not backup_list:
                        empty_hint = "当前暂无分支存档。可在「历史」页点击右上角「备份当前」创建新时间线。"
                        eh_surf = Screen.dfont.render(empty_hint, True, MUTED_COLOR)
                        text_surf.blit(eh_surf, ((paper_rect.width - eh_surf.get_width()) // 2, 200))
                        cache["max_scroll"] = 0.0
                    else:
                        card_x = 10
                        curr_y = 12
                        for itm in backup_list:
                            # 只画静态文字；卡片底/边框/按钮随 hover 变化，交由每帧现画
                            t_s = card_title_font.render(itm.get("title", ""), True, (31, 35, 43))
                            text_surf.blit(t_s, (card_x + 14, curr_y + 12))
                            cur_tx = card_x + 14 + t_s.get_width() + 10

                            if itm.get("is_auto_backup"):
                                tag_s = card_tag_font.render("[自动快照]", True, (215, 120, 10))
                                text_surf.blit(tag_s, (cur_tx, curr_y + 16))
                                cur_tx += tag_s.get_width() + 8

                            rnd_s = card_sub_font.render(f"{itm.get('total_rounds', 0)} 轮对话", True, (110, 115, 128))
                            text_surf.blit(rnd_s, (cur_tx, curr_y + 15))
                            cur_tx += rnd_s.get_width() + 12

                            time_s = card_sub_font.render(f"[{itm.get('backup_time', '')}]", True, MUTED_COLOR)
                            text_surf.blit(time_s, (cur_tx, curr_y + 15))

                            # 对白摘要行（按可用宽度比例截断，避免与右侧按钮组重叠）
                            preview_txt = f"{itm.get('last_speaker', '对白')}: {itm.get('last_preview', '')}"
                            preview_max_w = 524
                            if Screen.dfont.size(preview_txt)[0] > preview_max_w:
                                keep = max(6, int(len(preview_txt) * preview_max_w / Screen.dfont.size(preview_txt)[0]) - 1)
                                preview_txt = preview_txt[:keep] + "..."
                            text_surf.blit(Screen.dfont.render(preview_txt, True, CHARCOAL_COLOR), (card_x + 14, curr_y + 45))

                            rows.append({"y": curr_y, "itm": itm})
                            curr_y += 94
                        cache["max_scroll"] = max(0.0, curr_y + 16 - paper_rect.height)

                    cache["surf"] = text_surf
                    cache["rows"] = rows
                    cache["dirty"] = False

                text_surf = cache["surf"]
                max_scroll = cache["max_scroll"]
                scroll_y = max(-max_scroll, min(0.0, scroll_y))

                for row in cache["rows"]:
                    rel = row["y"] + int(scroll_y)
                    if rel < -94 or rel > paper_rect.height + 10:
                        continue
                    itm = row["itm"]
                    b_id = str(itm.get("backup_id", ""))
                    backup_chrome.append((
                        rel,
                        _abs(10, row["y"], 820, 82).collidepoint(mx, my) and paper_rect.collidepoint(mx, my)
                    ))
                    for rel_x, btn_w, act, payload in (
                        (562, 70, "rename_backup", (b_id, str(itm.get("title", "")))),
                        (642, 88, "load_backup", b_id),
                        (740, 70, "delete_backup", b_id),
                    ):
                        btn_rect = pygame.Rect(rel_x, row["y"] + 24, btn_w, 34)
                        backup_buttons.append({"rect": btn_rect, "kind": act})
                        click_actions.append((_abs(btn_rect.x, btn_rect.y, btn_rect.width, btn_rect.height), act, payload))

            # 记录本帧正文实际属于哪个标签。
            # 标签点击是在下面的事件处理里改 active_tab 的，而正文已经在这之前渲染完了；
            # 若渲染标签栏时直接用 active_tab，会出现「高亮已切、正文还是旧的那一帧」的错位闪烁。
            drawn_tab = active_tab

            # 计算当前滑块坐标与热区 (滑道居中 x=1090.5, y=87~684, 行程 travel=569)
            if max_scroll > 0:
                ratio = max(0.0, min(1.0, -scroll_y / max_scroll))
                slider_y = track_top + ratio * travel
            else:
                slider_y = track_top
            rect_slider = pygame.Rect(slider_x, int(slider_y), slider_w, slider_h)

            # 事件处理
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.exit()
                    sys_exit()

                # 模态命名弹窗优先拦截全事件
                if input_dialog.is_open:
                    # close() 会清空 action_context，必须在 handle_event 之前取出
                    pending_ctx = input_dialog.action_context
                    in_res = input_dialog.handle_event(
                        event, mx, my, self._get_clipboard_text, self._set_clipboard_text
                    )
                    if in_res == "confirm" and pending_ctx:
                        act_type, payload = pending_ctx
                        if act_type == "rename_backup":
                            handle_input_action("rename_backup", (payload, input_dialog.value))
                        else:
                            handle_input_action(act_type, input_dialog.value)
                    if not input_dialog.is_open and self.ui.mode != PLAYER:
                        pygame.key.stop_text_input()
                    continue

                # 模态确认弹窗次优先拦截全事件
                if confirm_dialog.is_open:
                    # 同上：close() 会清空 action_context，先取出再处理
                    pending_ctx = confirm_dialog.action_context
                    dia_res = confirm_dialog.handle_event(event, mx, my)
                    if dia_res == "confirm" and pending_ctx:
                        act_type, payload = pending_ctx
                        handle_confirm_action(act_type, payload)
                    continue

                if event.type == KEYDOWN:
                    if event.key in (K_ESCAPE, K_RETURN, K_SPACE):
                        running = False
                    elif event.key == K_UP:
                        scroll_y = min(0.0, scroll_y + 40.0)
                    elif event.key == K_DOWN:
                        scroll_y = max(-max_scroll, scroll_y - 40.0)
                    elif event.key == K_PAGEUP:
                        scroll_y = min(0.0, scroll_y + 250.0)
                    elif event.key == K_PAGEDOWN:
                        scroll_y = max(-max_scroll, scroll_y - 250.0)

                elif event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:
                        scroll_y = min(0.0, scroll_y + 50.0)
                    elif event.y < 0:
                        scroll_y = max(-max_scroll, scroll_y - 50.0)

                elif event.type == MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if rect_back.collidepoint(mx, my):
                            running = False
                        elif rect_tab_hist.collidepoint(mx, my):
                            active_tab = "history"
                            scroll_y = -max_scroll
                            is_dragging_slider = False
                        elif rect_tab_fav.collidepoint(mx, my):
                            active_tab = "favorites"
                            scroll_y = 0.0
                            is_dragging_slider = False
                        elif rect_tab_backup.collidepoint(mx, my):
                            active_tab = "backups"
                            scroll_y = 0.0
                            is_dragging_slider = False

                        elif drawn_tab == "history" and rect_btn_backup.collidepoint(mx, my):
                            if not self.conversation:
                                self.show_toast("当前暂无对话记录可备份")
                            else:
                                open_input_dialog(
                                    title="创建分支存档",
                                    label="为这段回忆起一个名字",
                                    default_text=history_mgr.default_backup_title(),
                                    context=("new_backup", None)
                                )

                        elif drawn_tab == "history" and rect_btn_clear.collidepoint(mx, my):
                            if not self.conversation:
                                self.show_toast("当前对话记录已是空白")
                            else:
                                confirm_dialog.open(
                                    title="重置当前对话",
                                    sub1="确定要清空与墨小菊的全部当前对话吗？",
                                    sub2="系统将自动为你生成一份安全快照，随时可在分支存档中恢复。",
                                    confirm_text="确认清空",
                                    cancel_text="保留回忆",
                                    context=("clear", None)
                                )

                        elif drawn_tab == "backups" and rect_btn_new_backup.collidepoint(mx, my):
                            if not self.conversation:
                                self.show_toast("当前暂无对话记录可备份")
                            else:
                                open_input_dialog(
                                    title="新建分支存档",
                                    label="为这段回忆起一个名字",
                                    default_text=history_mgr.default_backup_title(),
                                    context=("new_backup", None)
                                )

                        elif rect_slider.collidepoint(mx, my):
                            is_dragging_slider = True
                        elif rect_track.collidepoint(mx, my):
                            if max_scroll > 0:
                                ratio = max(0.0, min(1.0, (my - track_top - slider_h / 2) / travel))
                                scroll_y = -ratio * max_scroll
                            is_dragging_slider = True
                        elif paper_rect.collidepoint(mx, my):
                            for s_rect, act_type, content in click_actions:
                                if s_rect.collidepoint(mx, my):
                                    if act_type == "voice":
                                        self.play_tts_voice(content)
                                    elif act_type in ("fav", "unfav"):
                                        now_is_fav = DaisyMo.toggle_favorite(content)
                                        self.show_toast("已加入珍藏" if now_is_fav else "已移出珍藏")
                                        mark_dirty("history", "favorites")
                                    elif act_type == "rename_backup":
                                        b_id, b_title = content
                                        open_input_dialog(
                                            title="重命名分支存档",
                                            label="修改这条时间线的名称",
                                            default_text=str(b_title),
                                            context=("rename_backup", str(b_id))
                                        )
                                    elif act_type == "load_backup":
                                        b_id = str(content)
                                        b_title = next((b["title"] for b in backup_list if b["backup_id"] == b_id), "此分支")
                                        confirm_dialog.open(
                                            title="载入时间线分支",
                                            sub1=f"确定载入「{b_title}」吗？",
                                            sub2="当前对话将自动快照归档，随后切换至该时间线。",
                                            confirm_text="确认载入",
                                            cancel_text="取消",
                                            context=("load_backup", b_id)
                                        )
                                    elif act_type == "delete_backup":
                                        b_id = str(content)
                                        b_title = next((b["title"] for b in backup_list if b["backup_id"] == b_id), "此分支")
                                        confirm_dialog.open(
                                            title="删除分支存档",
                                            sub1=f"确定删除「{b_title}」吗？",
                                            sub2="存档将被移入 .trash 回收目录，可从本地存储中找回。",
                                            confirm_text="确认删除",
                                            cancel_text="取消",
                                            context=("delete_backup", b_id)
                                        )
                                    break
                    elif event.button == 4:   # 传统滚轮向上
                        scroll_y = min(0.0, scroll_y + 50.0)
                    elif event.button == 5:   # 传统滚轮向下
                        scroll_y = max(-max_scroll, scroll_y - 50.0)

                elif event.type == MOUSEMOTION:
                    if is_dragging_slider and max_scroll > 0:
                        ratio = max(0.0, min(1.0, (my - track_top - slider_h / 2) / travel))
                        scroll_y = -ratio * max_scroll

                elif event.type == MOUSEBUTTONUP:
                    if event.button == 1:
                        is_dragging_slider = False

            # 绘制底图
            self.screen.blit(bg_backlog, (0, 0))

            # 绘制顶部三标签栏 (信纸素描和纸刻印风格)
            tabs = [
                (rect_tab_hist, "历史", drawn_tab == "history"),
                (rect_tab_fav, f"珍藏 ({len(DaisyMo.favorites)})", drawn_tab == "favorites"),
                (rect_tab_backup, f"分支存档 ({len(backup_list)})", drawn_tab == "backups")
            ]
            for r_tab, txt, is_act in tabs:
                is_hover = r_tab.collidepoint(mx, my)
                if is_act:
                    txt_color = (215, 120, 10)  # 小菊琥珀橙
                    pygame.draw.line(self.screen, (255, 155, 0), (r_tab.x + 8, r_tab.bottom - 3), (r_tab.right - 8, r_tab.bottom - 3), 2)
                elif is_hover:
                    txt_color = (45, 50, 60)    # 悬停深炭黑
                    pygame.draw.line(self.screen, (180, 185, 195), (r_tab.x + 12, r_tab.bottom - 3), (r_tab.right - 12, r_tab.bottom - 3), 1)
                else:
                    txt_color = (120, 125, 135)  # 未选铅灰色

                txt_surf = Screen.card_font.render(txt, True, txt_color)
                self.screen.blit(txt_surf, (r_tab.x + (r_tab.width - txt_surf.get_width()) // 2, r_tab.y + (r_tab.height - txt_surf.get_height()) // 2))

            # 绘制顶部右侧操作按钮（跟随正文实际所属的标签，避免与正文错位一帧）
            if drawn_tab == "history":
                # 1. 备份当前回忆按钮
                is_b_hover = rect_btn_backup.collidepoint(mx, my)
                pygame.draw.rect(self.screen, (255, 246, 232) if is_b_hover else (255, 255, 255, 210), rect_btn_backup, border_radius=5)
                pygame.draw.rect(self.screen, (255, 155, 0) if is_b_hover else (210, 204, 194), rect_btn_backup, width=1, border_radius=5)
                b_txt = dia_btn_font.render("备份当前", True, (215, 120, 10) if is_b_hover else (75, 80, 92))
                self.screen.blit(b_txt, (rect_btn_backup.x + (rect_btn_backup.width - b_txt.get_width()) // 2, rect_btn_backup.y + (rect_btn_backup.height - b_txt.get_height()) // 2))

                # 2. 清空记录按钮
                is_c_hover = rect_btn_clear.collidepoint(mx, my)
                pygame.draw.rect(self.screen, (255, 236, 236) if is_c_hover else (255, 255, 255, 210), rect_btn_clear, border_radius=5)
                pygame.draw.rect(self.screen, (225, 90, 90) if is_c_hover else (210, 204, 194), rect_btn_clear, width=1, border_radius=5)
                c_txt = dia_btn_font.render("清空记录", True, (190, 50, 50) if is_c_hover else (120, 95, 95))
                self.screen.blit(c_txt, (rect_btn_clear.x + (rect_btn_clear.width - c_txt.get_width()) // 2, rect_btn_clear.y + (rect_btn_clear.height - c_txt.get_height()) // 2))

            elif drawn_tab == "backups":
                # 新建备份按钮
                is_nb_hover = rect_btn_new_backup.collidepoint(mx, my)
                pygame.draw.rect(self.screen, (255, 246, 232) if is_nb_hover else (255, 255, 255, 210), rect_btn_new_backup, border_radius=5)
                pygame.draw.rect(self.screen, (255, 155, 0) if is_nb_hover else (210, 204, 194), rect_btn_new_backup, width=1, border_radius=5)
                nb_txt = dia_btn_font.render("新建备份", True, (215, 120, 10) if is_nb_hover else (75, 80, 92))
                self.screen.blit(nb_txt, (rect_btn_new_backup.x + (rect_btn_new_backup.width - nb_txt.get_width()) // 2, rect_btn_new_backup.y + (rect_btn_new_backup.height - nb_txt.get_height()) // 2))

            # ---- 正文绘制：唯一一次正文 blit（内容已缓存，滚动只改裁剪区）----
            prev_clip = self.screen.get_clip()
            self.screen.set_clip(paper_rect)

            # 分支存档的卡片底与边框随 hover 变化，必须垫在缓存正文之下
            for rel, hovered in backup_chrome:
                cy = paper_rect.y + rel
                pygame.draw.rect(self.screen, (255, 252, 246) if hovered else (248, 245, 239),
                                 (paper_rect.x + 10, cy, 820, 82), border_radius=8)
                pygame.draw.rect(self.screen, (255, 155, 0, 160) if hovered else (218, 212, 202, 180),
                                 (paper_rect.x + 10, cy, 820, 82), width=1, border_radius=8)

            clip_rect = pygame.Rect(0, int(-scroll_y), paper_rect.width, paper_rect.height)
            self.screen.blit(text_surf, (paper_rect.x, paper_rect.y), area=clip_rect)

            # 每帧现画的动效层：语音高亮、珍藏星标（画在缓存正文之上）
            for icon_surf, icon_rect in icon_blits:
                self.screen.blit(icon_surf, (paper_rect.x + icon_rect.x, paper_rect.y + icon_rect.y + int(scroll_y)))

            # 分支存档的三个按钮（hover 态每帧重算）
            for btn in backup_buttons:
                r = btn["rect"]
                sr = pygame.Rect(paper_rect.x + r.x, paper_rect.y + r.y + int(scroll_y), r.width, r.height)
                hovered = sr.collidepoint(mx, my) and paper_rect.collidepoint(mx, my)
                kind = btn["kind"]
                if kind == "rename_backup":
                    pygame.draw.rect(self.screen, (255, 246, 232) if hovered else (240, 236, 229), sr, border_radius=6)
                    pygame.draw.rect(self.screen, (255, 155, 0) if hovered else (206, 199, 188), sr, width=1, border_radius=6)
                    label, txt_color = "改名", ((215, 120, 10) if hovered else (75, 80, 92))
                elif kind == "load_backup":
                    pygame.draw.rect(self.screen, (255, 155, 0) if hovered else (215, 120, 10), sr, border_radius=6)
                    label, txt_color = "载入分支", (255, 255, 255)
                else:
                    pygame.draw.rect(self.screen, (246, 226, 226) if hovered else (234, 230, 224), sr, border_radius=6)
                    label, txt_color = "删除", ((190, 50, 50) if hovered else (90, 95, 105))
                lbl = dia_btn_font.render(label, True, txt_color)
                self.screen.blit(lbl, (sr.x + (sr.width - lbl.get_width()) // 2,
                                       sr.y + (sr.height - lbl.get_height()) // 2))

            self.screen.set_clip(prev_clip)

            # 绘制右侧滑道中的官方原生圆纽扣滑块 (assets/ui/backlog_slider.png)
            self.screen.blit(btn_slider, (slider_x, int(slider_y)))

            # 返回按钮
            back_btn = btn_back_over if rect_back.collidepoint(mx, my) else btn_back_normal
            self.screen.blit(back_btn, (rect_back.x, rect_back.y))

            # 二次确认模态弹窗
            if confirm_dialog.is_open:
                confirm_dialog.render(self.screen, mx, my)

            # 命名输入模态弹窗
            if input_dialog.is_open:
                input_dialog.render(self.screen, mx, my)

            # 浮动提示 Toast
            if self.ui.toast_text and (time() - self.ui.toast_time < 2.0):
                t_surf = Screen.card_font.render(self.ui.toast_text, True, GOLD_COLOR)
                tw, th = t_surf.get_size()
                tx = (1280 - tw) // 2
                ty = 510
                pygame.draw.rect(self.screen, (20, 24, 32), (tx - 16, ty - 6, tw + 32, th + 12), border_radius=6)
                pygame.draw.rect(self.screen, DCOLOR, (tx - 16, ty - 6, tw + 32, th + 12), width=1, border_radius=6)
                self.screen.blit(t_surf, (tx, ty))
            elif self.ui.toast_text and (time() - self.ui.toast_time >= 2.0):
                self.ui.toast_text = ""

            pygame.display.flip()

        # 退出回忆界面时按当前发言模式还原输入法状态，避免残留中文输入法候选窗
        if input_dialog.is_open:
            input_dialog.close()
        if self.ui.mode == PLAYER:
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()

        return hist_dirty

    def system_menu(self) -> str:
        """极简 AI 核心设置面板 (采用声明式自绘控件库 daisymo_widgets 驱动，支持双分栏与动效无损保全)"""
        DaisyMo.load_config()
        running: bool = True
        clock: pygame.time.Clock = pygame.time.Clock()
        blink: BlinkCursor = BlinkCursor()

        # 抓取当前屏幕底图作为单次静态背景，彻底消除每帧半透明叠加变纯黑及文字重叠发虚的 bug
        bg_snapshot = self.screen.copy()

        active_system_tab: str = "llm"  # "llm" | "tts"

        # LLM 参数
        provider = DaisyMo.provider
        base_url = DaisyMo.base_url
        model = DaisyMo.model_name
        api_key = DaisyMo.api_key
        enable_thinking: bool = DaisyMo.enable_thinking
        thinking_supported: bool = DaisyMo.check_thinking_support(provider, base_url, model, api_key)
        if not thinking_supported:
            enable_thinking = False

        # TTS 参数
        tts_base_url = DaisyMo.tts_base_url
        tts_model = DaisyMo.tts_model
        tts_api_key = DaisyMo.tts_api_key
        tts_voice = DaisyMo.tts_voice

        # 状态指示
        llm_status_text = "就绪"
        llm_status_color = MUTED_COLOR
        tts_status_text = "就绪"
        tts_status_color = MUTED_COLOR

        # 弹窗尺寸与居中布局 (760 x 605)
        modal_rect = pygame.Rect(260, 55, 760, 605)
        rect_close = pygame.Rect(modal_rect.right - 36, modal_rect.y + 14, 22, 22)

        # 顶部标签栏
        rect_tab_llm = pygame.Rect(modal_rect.x + 28, modal_rect.y + 14, 130, 30)
        rect_tab_tts = pygame.Rect(modal_rect.x + 168, modal_rect.y + 14, 140, 30)
        tab_group = TabGroup([("llm", "大模型 API", rect_tab_llm), ("tts", "语音 TTS API", rect_tab_tts)], active_tab=active_system_tab)

        # 1. LLM 控件布局
        prov_keys = list(AI_PROVIDERS.keys())
        prov_rects: Dict[str, pygame.Rect] = {}
        grid_x = modal_rect.x + 28
        grid_y = modal_rect.y + 80
        chip_w = 224
        chip_h = 30
        for idx, k in enumerate(prov_keys):
            r = idx // 3
            c = idx % 3
            prov_rects[k] = pygame.Rect(grid_x + c * (chip_w + 16), grid_y + r * (chip_h + 8), chip_w, chip_h)

        rect_input_url = pygame.Rect(modal_rect.x + 28, modal_rect.y + 224, 704, 32)
        rect_input_model = pygame.Rect(modal_rect.x + 28, modal_rect.y + 290, 430, 32)
        rect_btn_fetch = pygame.Rect(modal_rect.x + 468, modal_rect.y + 290, 114, 32)
        rect_btn_dropdown = pygame.Rect(modal_rect.x + 590, modal_rect.y + 290, 142, 32)
        rect_input_key = pygame.Rect(modal_rect.x + 28, modal_rect.y + 356, 430, 32)
        rect_btn_eye = pygame.Rect(modal_rect.x + 468, modal_rect.y + 356, 70, 32)
        rect_btn_thinking = pygame.Rect(modal_rect.x + 548, modal_rect.y + 356, 184, 32)

        # 声明式 TextInputBox 控件
        box_url = TextInputBox(rect_input_url, text=base_url, font=Screen.card_font)
        box_model = TextInputBox(rect_input_model, text=model, font=Screen.card_font)
        box_key = TextInputBox(rect_input_key, text=api_key, font=Screen.card_font, is_password=True)
        if not api_key:
            box_key.is_active = True
            box_key.select_all()

        current_models = AI_PROVIDERS.get(provider, {}).get("models", [model])
        dd_model = DropdownMenu(rect_btn_dropdown, items=current_models, selected_value=model)

        # 2. TTS 控件布局
        rect_input_tts_url = pygame.Rect(modal_rect.x + 28, modal_rect.y + 110, 704, 32)
        rect_input_tts_model = pygame.Rect(modal_rect.x + 28, modal_rect.y + 176, 430, 32)
        rect_btn_tts_fetch = pygame.Rect(modal_rect.x + 468, modal_rect.y + 176, 114, 32)
        rect_btn_tts_model_dd = pygame.Rect(modal_rect.x + 590, modal_rect.y + 176, 142, 32)
        rect_input_tts_key = pygame.Rect(modal_rect.x + 28, modal_rect.y + 242, 626, 32)
        rect_btn_tts_eye = pygame.Rect(modal_rect.x + 664, modal_rect.y + 242, 68, 32)
        rect_input_tts_voice = pygame.Rect(modal_rect.x + 28, modal_rect.y + 308, 430, 32)
        rect_btn_tts_vfetch = pygame.Rect(modal_rect.x + 468, modal_rect.y + 308, 114, 32)
        rect_btn_tts_voice_dd = pygame.Rect(modal_rect.x + 590, modal_rect.y + 308, 142, 32)

        box_tts_url = TextInputBox(rect_input_tts_url, text=tts_base_url, font=Screen.card_font)
        box_tts_model = TextInputBox(rect_input_tts_model, text=tts_model, font=Screen.card_font)
        box_tts_key = TextInputBox(rect_input_tts_key, text=tts_api_key, font=Screen.card_font, is_password=True)
        box_tts_voice = TextInputBox(rect_input_tts_voice, text=tts_voice, font=Screen.card_font)

        fetched_tts_models = [tts_model] if tts_model else ["tts-1", "tts-1-hd", "mimo-v2.5-tts", "mimo-v2.5-tts-voicedesign"]
        if "mimo-v2.5-tts" not in fetched_tts_models:
            fetched_tts_models.append("mimo-v2.5-tts")
        common_tts_voices = [
            "冰糖", "茉莉", "苏打", "白桦", "Mia", "Chloe", "alloy", "echo", "fable", "onyx", "nova", "shimmer", "xiaoxiao", "yunxi"
        ]
        dd_tts_model = DropdownMenu(rect_btn_tts_model_dd, items=fetched_tts_models, selected_value=tts_model)
        dd_tts_voice = DropdownMenu(rect_btn_tts_voice_dd, items=common_tts_voices, selected_value=tts_voice)

        # 3. 底部公共区域控件 (BGM 与语音音量)
        is_in_game: bool = getattr(self, '_in_game_mode', False)

        rect_vol_down = pygame.Rect(modal_rect.x + 120, modal_rect.y + 404, 30, 26)
        rect_vol_up = pygame.Rect(modal_rect.x + 208, modal_rect.y + 404, 30, 26)
        rect_vol_bar = pygame.Rect(modal_rect.x + 254, modal_rect.y + 411, 200, 12)
        slider_bgm = SliderBar(rect_vol_bar, value=DaisyMo.bgm_volume, track_color=(229, 224, 214), fill_color=(255, 155, 0), thumb_color=(255, 255, 255), thumb_border_color=(215, 120, 10))

        rect_vvol_down = pygame.Rect(modal_rect.x + 120, modal_rect.y + 448, 30, 26)
        rect_vvol_up = pygame.Rect(modal_rect.x + 208, modal_rect.y + 448, 30, 26)
        rect_vvol_bar = pygame.Rect(modal_rect.x + 254, modal_rect.y + 455, 200, 12)
        slider_voice = SliderBar(rect_vvol_bar, value=DaisyMo.voice_volume, track_color=(229, 224, 214), fill_color=(255, 155, 0), thumb_color=(255, 255, 255), thumb_border_color=(215, 120, 10))

        rect_btn_title = pygame.Rect(modal_rect.x + 296, modal_rect.y + 538, 140, 38)
        rect_btn_test = pygame.Rect(modal_rect.x + 448, modal_rect.y + 538, 120, 38)
        rect_btn_save = pygame.Rect(modal_rect.x + 580, modal_rect.y + 538, 152, 38)

        # 开启键盘事件连续重复与文本输入
        pygame.key.start_text_input()
        pygame.key.set_repeat(300, 35)

        def do_save_config() -> None:
            DaisyMo.save_config(
                provider=provider,
                base_url=box_url.text,
                model=box_model.text,
                api_key=box_key.text,
                tts_base_url=box_tts_url.text,
                tts_model=box_tts_model.text,
                tts_api_key=box_tts_key.text,
                tts_voice=box_tts_voice.text,
                bgm_volume=slider_bgm.value,
                voice_volume=slider_voice.value,
                enable_thinking=enable_thinking
            )

        def refresh_thinking_support(probe: bool = False) -> None:
            nonlocal thinking_supported, enable_thinking
            thinking_supported = DaisyMo.check_thinking_support(provider, box_url.text, box_model.text, box_key.text if probe else "")
            if not thinking_supported:
                enable_thinking = False

        llm_boxes = [box_url, box_model, box_key]
        tts_boxes = [box_tts_url, box_tts_model, box_tts_key, box_tts_voice]

        while running:
            clock.tick(30)
            blink.tick()
            mx, my = pygame.mouse.get_pos()
            now_time = time()

            # 处理长按连删
            current_boxes = llm_boxes if active_system_tab == "llm" else tts_boxes
            for b in current_boxes:
                if b.is_active:
                    b.tick_continuous_delete(now_time)

            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.key.set_repeat(0)
                    self.exit()
                    sys_exit()

                # ESC 退出与关闭下拉
                if event.type == KEYDOWN and event.key == K_ESCAPE:
                    if dd_model.is_open or dd_tts_model.is_open or dd_tts_voice.is_open:
                        dd_model.is_open = False
                        dd_tts_model.is_open = False
                        dd_tts_voice.is_open = False
                    else:
                        do_save_config()
                        running = False
                        break

                # TAB 切换输入框焦点
                if event.type == KEYDOWN and event.key == K_TAB:
                    active_boxes = current_boxes
                    cur_idx = -1
                    for i, b in enumerate(active_boxes):
                        if b.is_active:
                            cur_idx = i
                            b.is_active = False
                    next_idx = (cur_idx + 1) % len(active_boxes)
                    active_boxes[next_idx].is_active = True
                    active_boxes[next_idx].select_all()
                    continue

                # 选项卡切换
                new_tab = tab_group.handle_event(event, mx, my)
                if new_tab:
                    active_system_tab = new_tab
                    dd_model.is_open = False
                    dd_tts_model.is_open = False
                    dd_tts_voice.is_open = False
                    for b in llm_boxes + tts_boxes:
                        b.is_active = False
                    if active_system_tab == "llm":
                        llm_status_text = "大模型配置就绪"
                        llm_status_color = MUTED_COLOR
                    else:
                        tts_status_text = "TTS配置就绪"
                        tts_status_color = MUTED_COLOR
                    continue

                # 下拉菜单交互
                if active_system_tab == "llm":
                    sel, val = dd_model.handle_event(event, mx, my)
                    if sel:
                        box_model.text = val
                        refresh_thinking_support(probe=False)
                        llm_status_text = f"已选择: {val}"
                        llm_status_color = GOLD_COLOR
                        continue
                else:
                    sel, val = dd_tts_model.handle_event(event, mx, my)
                    if sel:
                        box_tts_model.text = val
                        tts_status_text = f"已选择: {val}"
                        tts_status_color = GOLD_COLOR
                        continue
                    sel_v, val_v = dd_tts_voice.handle_event(event, mx, my)
                    if sel_v:
                        box_tts_voice.text = val_v
                        tts_status_text = f"已选择音色: {val_v}"
                        tts_status_color = GOLD_COLOR
                        continue

                # 音量滑块交互
                if slider_bgm.handle_event(event, mx, my):
                    DaisyMo.bgm_volume = slider_bgm.value
                    Mixer.set_volume(slider_bgm.value)
                if slider_voice.handle_event(event, mx, my):
                    DaisyMo.voice_volume = slider_voice.value
                    if self.ui.voice_channel:
                        self.ui.voice_channel.set_volume(slider_voice.value)

                # 输入框事件派发
                for b in current_boxes:
                    if b.handle_event(event, mx, my, self._get_clipboard_text, self._set_clipboard_text):
                        if b == box_model:
                            refresh_thinking_support(probe=False)

                # 鼠标点击按钮判定
                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    # 互斥激活：点击某个输入框时取消其余输入框激活
                    for b in current_boxes:
                        if b.rect.collidepoint(mx, my):
                            for other in current_boxes:
                                if other != b:
                                    other.is_active = False
                            break

                    # 关闭按钮
                    if rect_close.collidepoint(mx, my):
                        do_save_config()
                        running = False
                        break

                    # 游戏内专属：返回主界面 (原版三阶段动效无损保全)
                    if is_in_game and rect_btn_title.collidepoint(mx, my):
                        do_save_config()
                        if hasattr(self, 'daisymo') and self.daisymo:
                            self.daisymo.save()
                        if self.ui.voice_channel:
                            self.ui.voice_channel.fadeout(200)
                        pygame.key.set_repeat(0)
                        pygame.key.stop_text_input()

                        # Phase 1: 触控反馈——按钮即刻渲染琥珀橙激活按下态
                        pygame.draw.rect(self.screen, (255, 155, 0), rect_btn_title, border_radius=6)
                        pygame.draw.rect(self.screen, (255, 190, 80), rect_btn_title, width=1, border_radius=6)
                        title_txt_active = Screen.card_font.render("返回主界面", True, (255, 255, 255))
                        self.screen.blit(title_txt_active, (rect_btn_title.x + (rect_btn_title.width - title_txt_active.get_width()) // 2, rect_btn_title.y + (rect_btn_title.height - title_txt_active.get_height()) // 2))
                        pygame.display.flip()
                        pygame.time.delay(50)

                        # Phase 2: 弹窗平滑消融（Dissolve），优雅揭开被遮罩的游戏对话主场景
                        modal_snap = self.screen.copy()
                        for step in range(8, -1, -1):
                            clock.tick(60)
                            alpha = int(255 * (step / 8))
                            self.screen.blit(bg_snapshot, (0, 0))
                            if alpha > 0:
                                modal_snap.set_alpha(alpha)
                                self.screen.blit(modal_snap, (0, 0))
                            pygame.display.flip()

                        # Phase 3: 电影级平滑暗转（Fade to Black），从对话场景平滑遁入全黑
                        fade_black = pygame.Surface((1280, 720))
                        fade_black.fill((0, 0, 0))
                        for alpha in range(0, 256, 16):
                            clock.tick(50)
                            self.screen.blit(bg_snapshot, (0, 0))
                            fade_black.set_alpha(alpha)
                            self.screen.blit(fade_black, (0, 0))
                            pygame.display.flip()

                        # 确保转场终态为纯黑屏幕，平滑衔接标题屏明转
                        self.screen.fill((0, 0, 0))
                        pygame.display.flip()
                        return "title"

                    # 保存配置按钮
                    if rect_btn_save.collidepoint(mx, my):
                        do_save_config()
                        running = False
                        break

                    # 音量加减微调键 (委托至 SliderBar 封装步进方法)
                    if rect_vol_down.collidepoint(mx, my):
                        DaisyMo.bgm_volume = slider_bgm.step_down()
                        Mixer.set_volume(slider_bgm.value)
                    elif rect_vol_up.collidepoint(mx, my):
                        DaisyMo.bgm_volume = slider_bgm.step_up()
                        Mixer.set_volume(slider_bgm.value)
                    elif rect_vvol_down.collidepoint(mx, my):
                        DaisyMo.voice_volume = slider_voice.step_down()
                        if self.ui.voice_channel:
                            self.ui.voice_channel.set_volume(slider_voice.value)
                    elif rect_vvol_up.collidepoint(mx, my):
                        DaisyMo.voice_volume = slider_voice.step_up()
                        if self.ui.voice_channel:
                            self.ui.voice_channel.set_volume(slider_voice.value)

                    # LLM 专有按钮
                    if active_system_tab == "llm":
                        # 服务商选择
                        for k, r in prov_rects.items():
                            if r.collidepoint(mx, my):
                                if not hasattr(self, "_provider_key_cache"):
                                    self._provider_key_cache = {}
                                self._provider_key_cache[provider] = box_key.text
                                provider = k
                                p_info = AI_PROVIDERS[k]
                                box_url.text = p_info["base_url"]
                                box_model.text = p_info["default_model"]
                                box_key.text = self._provider_key_cache.get(k, "")
                                dd_model.items = p_info.get("models", [box_model.text])
                                dd_model.selected_value = box_model.text
                                dd_model.is_open = False
                                refresh_thinking_support(probe=False)
                                break

                        # 显隐眼睛
                        if rect_btn_eye.collidepoint(mx, my):
                            box_key.is_password = not box_key.is_password

                        # 深度思考切换
                        if rect_btn_thinking.collidepoint(mx, my):
                            if thinking_supported:
                                enable_thinking = not enable_thinking
                                DaisyMo.enable_thinking = enable_thinking
                                llm_status_text = "深度思考: 已开启" if enable_thinking else "深度思考: 已关闭"
                                llm_status_color = (215, 120, 10) if enable_thinking else MUTED_COLOR
                            else:
                                llm_status_text = "当前模型不支持深度思考"
                                llm_status_color = (255, 100, 100)

                        # 获取模型 (委托至 daisymo_ai)
                        if rect_btn_fetch.collidepoint(mx, my):
                            dd_model.is_open = False
                            for b in llm_boxes: b.is_active = False
                            llm_status_text = "获取模型列表中..."
                            llm_status_color = DCOLOR
                            pygame.display.flip()

                            def _fetch_models_task():
                                nonlocal llm_status_text, llm_status_color
                                ok, fetched, msg = ai_fetch_models(box_url.text, box_key.text, provider=provider)
                                if ok and fetched:
                                    if provider in AI_PROVIDERS:
                                        AI_PROVIDERS[provider]["models"] = fetched
                                    dd_model.items = fetched
                                    if box_model.text not in fetched:
                                        box_model.text = fetched[0]
                                    llm_status_text = f"成功获取 {len(fetched)} 个模型"
                                    llm_status_color = (120, 230, 160)
                                    dd_model.is_open = True
                                elif ok:
                                    llm_status_text = "成功但模型列表为空"
                                    llm_status_color = GOLD_COLOR
                                else:
                                    llm_status_text = msg
                                    llm_status_color = (255, 100, 100)

                            Thread(target=_fetch_models_task, daemon=True).start()

                        # 测试连接 (委托至 daisymo_ai)
                        if rect_btn_test.collidepoint(mx, my):
                            for b in llm_boxes: b.is_active = False
                            llm_status_text = "测试连接中..."
                            llm_status_color = DCOLOR
                            pygame.display.flip()

                            def _test_llm_task():
                                nonlocal llm_status_text, llm_status_color
                                ok, msg = ai_test_llm_connection(box_url.text, box_key.text, box_model.text)
                                if ok:
                                    llm_status_text = "连接成功"
                                    llm_status_color = (120, 230, 160)
                                    refresh_thinking_support(probe=True)
                                else:
                                    llm_status_text = msg
                                    llm_status_color = (255, 100, 100)

                            Thread(target=_test_llm_task, daemon=True).start()

                    # TTS 专有按钮
                    else:
                        if rect_btn_tts_eye.collidepoint(mx, my):
                            box_tts_key.is_password = not box_tts_key.is_password

                        # 获取 TTS 模型 (委托至 daisymo_ai)
                        if rect_btn_tts_fetch.collidepoint(mx, my):
                            dd_tts_model.is_open = False
                            dd_tts_voice.is_open = False
                            for b in tts_boxes: b.is_active = False
                            tts_status_text = "获取TTS模型中..."
                            tts_status_color = DCOLOR
                            pygame.display.flip()

                            def _fetch_tts_models_task():
                                nonlocal tts_status_text, tts_status_color, fetched_tts_models
                                ok, fetched, msg = ai_fetch_models(box_tts_url.text, box_tts_key.text)
                                u = box_tts_url.text.lower()
                                if "xiaomimimo.com" in u or any("mimo" in m.lower() for m in fetched):
                                    for m_opt in ["mimo-v2.5-tts", "mimo-v2.5-tts-voicedesign"]:
                                        if m_opt not in fetched:
                                            fetched.insert(0, m_opt)
                                if ok and fetched:
                                    fetched_tts_models = fetched
                                    dd_tts_model.items = fetched
                                    if box_tts_model.text not in fetched:
                                        box_tts_model.text = fetched[0]
                                    tts_status_text = f"成功获取 {len(fetched)} 个TTS模型"
                                    tts_status_color = (120, 230, 160)
                                    dd_tts_model.is_open = True
                                elif ok:
                                    tts_status_text = "成功但模型列表为空"
                                    tts_status_color = GOLD_COLOR
                                else:
                                    tts_status_text = msg
                                    tts_status_color = (255, 100, 100)

                            Thread(target=_fetch_tts_models_task, daemon=True).start()

                        # 获取 TTS 音色 (委托至 daisymo_ai)
                        if rect_btn_tts_vfetch.collidepoint(mx, my):
                            dd_tts_model.is_open = False
                            dd_tts_voice.is_open = False
                            for b in tts_boxes: b.is_active = False
                            tts_status_text = "获取TTS音色中..."
                            tts_status_color = DCOLOR
                            pygame.display.flip()

                            def _fetch_tts_voices_task():
                                nonlocal tts_status_text, tts_status_color, common_tts_voices
                                ok, fetched, msg = ai_fetch_tts_voices(box_tts_url.text, box_tts_key.text, box_tts_model.text)
                                if ok and fetched:
                                    common_tts_voices = fetched
                                    dd_tts_voice.items = fetched
                                    if not box_tts_voice.text or box_tts_voice.text not in fetched:
                                        box_tts_voice.text = fetched[0]
                                    tts_status_text = f"成功获取 {len(fetched)} 个TTS音色"
                                    tts_status_color = (120, 230, 160)
                                    dd_tts_voice.is_open = True
                                else:
                                    tts_status_text = msg
                                    tts_status_color = (255, 100, 100)

                            Thread(target=_fetch_tts_voices_task, daemon=True).start()

                        # 测试发音 (委托至 daisymo_ai)
                        if rect_btn_test.collidepoint(mx, my):
                            for b in tts_boxes: b.is_active = False
                            tts_status_text = "正在合成并测试发音..."
                            tts_status_color = DCOLOR
                            pygame.display.flip()

                            def _test_tts_task():
                                nonlocal tts_status_text, tts_status_color
                                try:
                                    is_m = ("mimo" in box_tts_model.text.lower()) or ("xiaomimimo" in box_tts_url.text.lower())
                                    tmp_audio = "assets/temp_tts.wav" if is_m else "assets/temp_tts.mp3"
                                    test_phrase = "你好，我是墨小菊，笨蛋邱诚！"
                                    ok, msg = Screen.synthesize_tts_to_file(
                                        base_url=box_tts_url.text,
                                        model_name=box_tts_model.text,
                                        api_key=box_tts_key.text,
                                        voice_name=box_tts_voice.text,
                                        text=test_phrase,
                                        output_path=tmp_audio
                                    )
                                    if ok:
                                        snd = pygame.mixer.Sound(tmp_audio)
                                        if not self.ui.voice_channel:
                                            self.ui.voice_channel = pygame.mixer.Channel(1)
                                        self.ui.voice_channel.set_volume(slider_voice.value)
                                        self.ui.voice_channel.play(snd)
                                        tts_status_text = "发音测试成功"
                                        tts_status_color = (120, 230, 160)
                                    else:
                                        tts_status_text = msg
                                        tts_status_color = (255, 100, 100)
                                except Exception as ex:
                                    tts_status_text = f"TTS错误: {str(ex)[:16]}"
                                    tts_status_color = (255, 100, 100)

                            Thread(target=_test_tts_task, daemon=True).start()

            # ------------- 渲染弹窗 (白色和纸圆角风格) -------------
            self.screen.blit(bg_snapshot, (0, 0))
            overlay = pygame.Surface((1280, 720), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            self.screen.blit(overlay, (0, 0))

            # 弹窗卡片阴影与白色和纸底板 (760x605, 圆角 12px)
            shadow_surf = pygame.Surface((modal_rect.width + 24, modal_rect.height + 24), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 110), (12, 12, modal_rect.width, modal_rect.height), border_radius=12)
            self.screen.blit(shadow_surf, (modal_rect.x - 12, modal_rect.y - 12))

            pygame.draw.rect(self.screen, (250, 248, 245), modal_rect, border_radius=12)
            pygame.draw.rect(self.screen, (215, 120, 10), modal_rect, width=1, border_radius=12)

            # 顶部 Tab 切换渲染
            tab_group.render(self.screen, Screen.card_font)

            # 关闭 X 按钮
            close_col = (31, 35, 43) if rect_close.collidepoint(mx, my) else (110, 117, 133)
            pad = 5
            pygame.draw.line(self.screen, close_col, (rect_close.x + pad, rect_close.y + pad), (rect_close.right - pad, rect_close.bottom - pad), 2)
            pygame.draw.line(self.screen, close_col, (rect_close.x + pad, rect_close.bottom - pad), (rect_close.right - pad, rect_close.y + pad), 2)

            if active_system_tab == "llm":
                # 服务商 3x3
                lbl_prov = Screen.dfont.render("服务商预设:", True, (92, 98, 112))
                self.screen.blit(lbl_prov, (modal_rect.x + 28, modal_rect.y + 58))
                for k, r in prov_rects.items():
                    is_active = (k == provider)
                    is_hover = r.collidepoint(mx, my)
                    chip_bg = (255, 247, 237) if is_active else (255, 255, 255)
                    chip_border = (255, 155, 0) if is_active else ((255, 180, 80) if is_hover else (216, 210, 198))
                    chip_txt_col = (215, 120, 10) if is_active else ((215, 120, 10) if is_hover else (45, 50, 62))
                    pygame.draw.rect(self.screen, chip_bg, r, border_radius=6)
                    pygame.draw.rect(self.screen, chip_border, r, width=1, border_radius=6)
                    chip_txt = Screen.card_font.render(AI_PROVIDERS[k]["name"], True, chip_txt_col)
                    self.screen.blit(chip_txt, (r.x + (r.width - chip_txt.get_width()) // 2, r.y + (r.height - chip_txt.get_height()) // 2))

                # Base URL
                lbl_url = Screen.dfont.render("Base URL:", True, (92, 98, 112))
                self.screen.blit(lbl_url, (modal_rect.x + 28, modal_rect.y + 204))
                box_url.render(self.screen, blink.visible)

                # 模型
                lbl_model = Screen.dfont.render("模型 (可直接输入或在右侧下拉选择):", True, (92, 98, 112))
                self.screen.blit(lbl_model, (modal_rect.x + 28, modal_rect.y + 270))
                box_model.render(self.screen, blink.visible)

                # 获取模型按钮
                is_fetch_hover = rect_btn_fetch.collidepoint(mx, my)
                btn_fetch_bg = (244, 240, 233) if is_fetch_hover else (237, 232, 223)
                btn_fetch_border = (255, 155, 0) if is_fetch_hover else (208, 200, 184)
                pygame.draw.rect(self.screen, btn_fetch_bg, rect_btn_fetch, border_radius=6)
                pygame.draw.rect(self.screen, btn_fetch_border, rect_btn_fetch, width=1, border_radius=6)
                fetch_txt = Screen.card_font.render("获取模型", True, (215, 120, 10) if is_fetch_hover else (45, 50, 62))
                self.screen.blit(fetch_txt, (rect_btn_fetch.x + (rect_btn_fetch.width - fetch_txt.get_width()) // 2, rect_btn_fetch.y + (rect_btn_fetch.height - fetch_txt.get_height()) // 2))

                # 下拉分栏按钮
                btn_dd_bg = (255, 247, 237) if dd_model.is_open else ((244, 240, 233) if rect_btn_dropdown.collidepoint(mx, my) else (237, 232, 223))
                btn_dd_border = (255, 155, 0) if dd_model.is_open else ((255, 180, 80) if rect_btn_dropdown.collidepoint(mx, my) else (208, 200, 184))
                pygame.draw.rect(self.screen, btn_dd_bg, rect_btn_dropdown, border_radius=6)
                pygame.draw.rect(self.screen, btn_dd_border, rect_btn_dropdown, width=1, border_radius=6)
                dd_btn_txt = Screen.card_font.render("预设模型", True, (215, 120, 10) if dd_model.is_open else (45, 50, 62))
                self.screen.blit(dd_btn_txt, (rect_btn_dropdown.x + 14, rect_btn_dropdown.y + (rect_btn_dropdown.height - dd_btn_txt.get_height()) // 2))
                arrow_cx = rect_btn_dropdown.right - 18
                arrow_cy = rect_btn_dropdown.centery
                arrow_col = (215, 120, 10) if dd_model.is_open else (110, 117, 133)
                if dd_model.is_open:
                    pts = [(arrow_cx - 5, arrow_cy + 3), (arrow_cx + 5, arrow_cy + 3), (arrow_cx, arrow_cy - 4)]
                else:
                    pts = [(arrow_cx - 5, arrow_cy - 3), (arrow_cx + 5, arrow_cy - 3), (arrow_cx, arrow_cy + 4)]
                pygame.draw.polygon(self.screen, arrow_col, pts)

                # API Key
                lbl_key = Screen.dfont.render("API Key:", True, (92, 98, 112))
                self.screen.blit(lbl_key, (modal_rect.x + 28, modal_rect.y + 336))
                box_key.render(self.screen, blink.visible)

                # 显隐眼睛
                is_eye_hover = rect_btn_eye.collidepoint(mx, my)
                eye_bg = (244, 240, 233) if is_eye_hover else (237, 232, 223)
                eye_border = (255, 155, 0) if is_eye_hover else (208, 200, 184)
                pygame.draw.rect(self.screen, eye_bg, rect_btn_eye, border_radius=6)
                pygame.draw.rect(self.screen, eye_border, rect_btn_eye, width=1, border_radius=6)
                eye_cx = rect_btn_eye.centerx
                eye_cy = rect_btn_eye.centery
                eye_col = (215, 120, 10) if is_eye_hover else ((45, 50, 62) if not box_key.is_password else (110, 117, 133))
                pygame.draw.ellipse(self.screen, eye_col, pygame.Rect(eye_cx - 10, eye_cy - 6, 20, 12), width=2)
                pygame.draw.circle(self.screen, eye_col, (eye_cx, eye_cy), 3)
                if box_key.is_password:
                    pygame.draw.line(self.screen, eye_col, (eye_cx - 10, eye_cy + 7), (eye_cx + 10, eye_cy - 7), 2)

                # 深度思考切换按钮
                is_th_hover = rect_btn_thinking.collidepoint(mx, my)
                if not thinking_supported:
                    th_bg = (235, 233, 230)
                    th_border = (216, 212, 206)
                    th_txt_str = "深度思考: 不支持"
                    th_txt_col = (168, 164, 158)
                    th_dot_col = (175, 171, 165)
                elif enable_thinking:
                    th_bg = (255, 243, 230) if is_th_hover else (255, 247, 237)
                    th_border = (255, 155, 0)
                    th_txt_str = "深度思考: 开启"
                    th_txt_col = (215, 120, 10)
                    th_dot_col = (255, 155, 0)
                else:
                    th_bg = (245, 242, 236) if is_th_hover else (237, 232, 223)
                    th_border = (255, 180, 80) if is_th_hover else (208, 200, 184)
                    th_txt_str = "深度思考: 关闭"
                    th_txt_col = (215, 120, 10) if is_th_hover else (60, 65, 76)
                    th_dot_col = (130, 136, 148)

                pygame.draw.rect(self.screen, th_bg, rect_btn_thinking, border_radius=6)
                pygame.draw.rect(self.screen, th_border, rect_btn_thinking, width=1, border_radius=6)
                th_txt = Screen.card_font.render(th_txt_str, True, th_txt_col)
                content_w = 8 + 6 + th_txt.get_width()
                start_x = rect_btn_thinking.x + (rect_btn_thinking.width - content_w) // 2
                dot_cy = rect_btn_thinking.centery
                pygame.draw.circle(self.screen, th_dot_col, (start_x + 4, dot_cy), 4)
                self.screen.blit(th_txt, (start_x + 14, rect_btn_thinking.y + (rect_btn_thinking.height - th_txt.get_height()) // 2))

            else:
                # TTS Tab 绘制
                lbl_sub = Screen.dfont.render("自定义语音 TTS API (兼容 OpenAI /audio/speech 与小米 MiMo 官方规范):", True, (92, 98, 112))
                self.screen.blit(lbl_sub, (modal_rect.x + 28, modal_rect.y + 60))

                # TTS Base URL
                lbl_tts_url = Screen.dfont.render("TTS Base URL (如 https://api.xiaomimimo.com/v1):", True, (92, 98, 112))
                self.screen.blit(lbl_tts_url, (modal_rect.x + 28, modal_rect.y + 90))
                box_tts_url.render(self.screen, blink.visible)

                # TTS 模型
                lbl_tts_m = Screen.dfont.render("TTS 模型 (如 mimo-v2.5-tts 或 tts-1):", True, (92, 98, 112))
                self.screen.blit(lbl_tts_m, (modal_rect.x + 28, modal_rect.y + 156))
                box_tts_model.render(self.screen, blink.visible)

                is_tfetch_hover = rect_btn_tts_fetch.collidepoint(mx, my)
                btn_tfetch_bg = (244, 240, 233) if is_tfetch_hover else (237, 232, 223)
                btn_tfetch_border = (255, 155, 0) if is_tfetch_hover else (208, 200, 184)
                pygame.draw.rect(self.screen, btn_tfetch_bg, rect_btn_tts_fetch, border_radius=6)
                pygame.draw.rect(self.screen, btn_tfetch_border, rect_btn_tts_fetch, width=1, border_radius=6)
                tfetch_txt = Screen.card_font.render("获取模型", True, (215, 120, 10) if is_tfetch_hover else (45, 50, 62))
                self.screen.blit(tfetch_txt, (rect_btn_tts_fetch.x + (rect_btn_tts_fetch.width - tfetch_txt.get_width()) // 2, rect_btn_tts_fetch.y + (rect_btn_tts_fetch.height - tfetch_txt.get_height()) // 2))

                # TTS 模型下拉按钮
                btn_tm_dd_bg = (255, 247, 237) if dd_tts_model.is_open else ((244, 240, 233) if rect_btn_tts_model_dd.collidepoint(mx, my) else (237, 232, 223))
                btn_tm_dd_border = (255, 155, 0) if dd_tts_model.is_open else ((255, 180, 80) if rect_btn_tts_model_dd.collidepoint(mx, my) else (208, 200, 184))
                pygame.draw.rect(self.screen, btn_tm_dd_bg, rect_btn_tts_model_dd, border_radius=6)
                pygame.draw.rect(self.screen, btn_tm_dd_border, rect_btn_tts_model_dd, width=1, border_radius=6)
                tm_dd_txt = Screen.card_font.render("预设模型", True, (215, 120, 10) if dd_tts_model.is_open else (45, 50, 62))
                self.screen.blit(tm_dd_txt, (rect_btn_tts_model_dd.x + 14, rect_btn_tts_model_dd.y + (rect_btn_tts_model_dd.height - tm_dd_txt.get_height()) // 2))
                arrow_cx = rect_btn_tts_model_dd.right - 18
                arrow_cy = rect_btn_tts_model_dd.centery
                arrow_col = (215, 120, 10) if dd_tts_model.is_open else (110, 117, 133)
                if dd_tts_model.is_open:
                    pts = [(arrow_cx - 5, arrow_cy + 3), (arrow_cx + 5, arrow_cy + 3), (arrow_cx, arrow_cy - 4)]
                else:
                    pts = [(arrow_cx - 5, arrow_cy - 3), (arrow_cx + 5, arrow_cy - 3), (arrow_cx, arrow_cy + 4)]
                pygame.draw.polygon(self.screen, arrow_col, pts)

                # TTS Key
                lbl_tkey = Screen.dfont.render("TTS API Key (本地服务无需鉴权可留空):", True, (92, 98, 112))
                self.screen.blit(lbl_tkey, (modal_rect.x + 28, modal_rect.y + 222))
                box_tts_key.render(self.screen, blink.visible)

                is_teye_hover = rect_btn_tts_eye.collidepoint(mx, my)
                teye_bg = (244, 240, 233) if is_teye_hover else (237, 232, 223)
                teye_border = (255, 155, 0) if is_teye_hover else (208, 200, 184)
                pygame.draw.rect(self.screen, teye_bg, rect_btn_tts_eye, border_radius=6)
                pygame.draw.rect(self.screen, teye_border, rect_btn_tts_eye, width=1, border_radius=6)
                teye_cx = rect_btn_tts_eye.centerx
                teye_cy = rect_btn_tts_eye.centery
                teye_col = (215, 120, 10) if is_teye_hover else ((45, 50, 62) if not box_tts_key.is_password else (110, 117, 133))
                pygame.draw.ellipse(self.screen, teye_col, pygame.Rect(teye_cx - 10, teye_cy - 6, 20, 12), width=2)
                pygame.draw.circle(self.screen, teye_col, (teye_cx, teye_cy), 3)
                if box_tts_key.is_password:
                    pygame.draw.line(self.screen, teye_col, (teye_cx - 10, teye_cy + 7), (teye_cx + 10, teye_cy - 7), 2)

                # TTS Voice
                lbl_tvoice = Screen.dfont.render("TTS 音色 Voice (如 冰糖, 茉莉, alloy 或自定义标识):", True, (92, 98, 112))
                self.screen.blit(lbl_tvoice, (modal_rect.x + 28, modal_rect.y + 288))
                box_tts_voice.render(self.screen, blink.visible)

                # 获取音色按钮
                is_tvfetch_hover = rect_btn_tts_vfetch.collidepoint(mx, my)
                btn_tvfetch_bg = (244, 240, 233) if is_tvfetch_hover else (237, 232, 223)
                btn_tvfetch_border = (255, 155, 0) if is_tvfetch_hover else (208, 200, 184)
                pygame.draw.rect(self.screen, btn_tvfetch_bg, rect_btn_tts_vfetch, border_radius=6)
                pygame.draw.rect(self.screen, btn_tvfetch_border, rect_btn_tts_vfetch, width=1, border_radius=6)
                tvfetch_txt = Screen.card_font.render("获取音色", True, (215, 120, 10) if is_tvfetch_hover else (45, 50, 62))
                self.screen.blit(tvfetch_txt, (rect_btn_tts_vfetch.x + (rect_btn_tts_vfetch.width - tvfetch_txt.get_width()) // 2, rect_btn_tts_vfetch.y + (rect_btn_tts_vfetch.height - tvfetch_txt.get_height()) // 2))

                # TTS 音色下拉按钮
                btn_tv_dd_bg = (255, 247, 237) if dd_tts_voice.is_open else ((244, 240, 233) if rect_btn_tts_voice_dd.collidepoint(mx, my) else (237, 232, 223))
                btn_tv_dd_border = (255, 155, 0) if dd_tts_voice.is_open else ((255, 180, 80) if rect_btn_tts_voice_dd.collidepoint(mx, my) else (208, 200, 184))
                pygame.draw.rect(self.screen, btn_tv_dd_bg, rect_btn_tts_voice_dd, border_radius=6)
                pygame.draw.rect(self.screen, btn_tv_dd_border, rect_btn_tts_voice_dd, width=1, border_radius=6)
                tv_dd_txt = Screen.card_font.render("预设音色", True, (215, 120, 10) if dd_tts_voice.is_open else (45, 50, 62))
                self.screen.blit(tv_dd_txt, (rect_btn_tts_voice_dd.x + 14, rect_btn_tts_voice_dd.y + (rect_btn_tts_voice_dd.height - tv_dd_txt.get_height()) // 2))
                arrow_cx = rect_btn_tts_voice_dd.right - 18
                arrow_cy = rect_btn_tts_voice_dd.centery
                arrow_col = (215, 120, 10) if dd_tts_voice.is_open else (110, 117, 133)
                if dd_tts_voice.is_open:
                    pts = [(arrow_cx - 5, arrow_cy + 3), (arrow_cx + 5, arrow_cy + 3), (arrow_cx, arrow_cy - 4)]
                else:
                    pts = [(arrow_cx - 5, arrow_cy - 3), (arrow_cx + 5, arrow_cy - 3), (arrow_cx, arrow_cy + 4)]
                pygame.draw.polygon(self.screen, arrow_col, pts)

            # ----------------- 公共底部：BGM 音量控制 -----------------

            lbl_bgm = Screen.dfont.render("BGM 音量", True, (45, 50, 62))
            self.screen.blit(lbl_bgm, (modal_rect.x + 28, modal_rect.y + 408))

            is_vd_hover = rect_vol_down.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (244, 240, 233) if is_vd_hover else (237, 232, 223), rect_vol_down, border_radius=6)
            pygame.draw.rect(self.screen, (255, 155, 0) if is_vd_hover else (208, 200, 184), rect_vol_down, width=1, border_radius=6)
            vd_txt = Screen.card_font.render("-", True, (215, 120, 10) if is_vd_hover else (45, 50, 62))
            self.screen.blit(vd_txt, (rect_vol_down.x + (rect_vol_down.width - vd_txt.get_width()) // 2, rect_vol_down.y + (rect_vol_down.height - vd_txt.get_height()) // 2))

            pct_txt = Screen.card_font.render(f"{int(slider_bgm.value * 100)}%", True, (31, 35, 43))
            self.screen.blit(pct_txt, (modal_rect.x + 160, modal_rect.y + 408))

            is_vu_hover = rect_vol_up.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (244, 240, 233) if is_vu_hover else (237, 232, 223), rect_vol_up, border_radius=6)
            pygame.draw.rect(self.screen, (255, 155, 0) if is_vu_hover else (208, 200, 184), rect_vol_up, width=1, border_radius=6)
            vu_txt = Screen.card_font.render("+", True, (215, 120, 10) if is_vu_hover else (45, 50, 62))
            self.screen.blit(vu_txt, (rect_vol_up.x + (rect_vol_up.width - vu_txt.get_width()) // 2, rect_vol_up.y + (rect_vol_up.height - vu_txt.get_height()) // 2))

            slider_bgm.render(self.screen)

            # ----------------- 公共底部：语音音量控制 -----------------
            lbl_vvol = Screen.dfont.render("语音音量", True, (45, 50, 62))
            self.screen.blit(lbl_vvol, (modal_rect.x + 28, modal_rect.y + 452))

            is_vvd_hover = rect_vvol_down.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (244, 240, 233) if is_vvd_hover else (237, 232, 223), rect_vvol_down, border_radius=6)
            pygame.draw.rect(self.screen, (255, 155, 0) if is_vvd_hover else (208, 200, 184), rect_vvol_down, width=1, border_radius=6)
            vvd_txt = Screen.card_font.render("-", True, (215, 120, 10) if is_vvd_hover else (45, 50, 62))
            self.screen.blit(vvd_txt, (rect_vvol_down.x + (rect_vvol_down.width - vvd_txt.get_width()) // 2, rect_vvol_down.y + (rect_vvol_down.height - vvd_txt.get_height()) // 2))

            vpct_txt = Screen.card_font.render(f"{int(slider_voice.value * 100)}%", True, (31, 35, 43))
            self.screen.blit(vpct_txt, (modal_rect.x + 160, modal_rect.y + 452))

            is_vvu_hover = rect_vvol_up.collidepoint(mx, my)
            pygame.draw.rect(self.screen, (244, 240, 233) if is_vvu_hover else (237, 232, 223), rect_vvol_up, border_radius=6)
            pygame.draw.rect(self.screen, (255, 155, 0) if is_vvu_hover else (208, 200, 184), rect_vvol_up, width=1, border_radius=6)
            vvu_txt = Screen.card_font.render("+", True, (215, 120, 10) if is_vvu_hover else (45, 50, 62))
            self.screen.blit(vvu_txt, (rect_vvol_up.x + (rect_vvol_up.width - vvu_txt.get_width()) // 2, rect_vvol_up.y + (rect_vvol_up.height - vvu_txt.get_height()) // 2))

            slider_voice.render(self.screen)

            # ----------------- 底部状态与操作按钮 -----------------
            cur_stat_txt = llm_status_text if active_system_tab == "llm" else tts_status_text
            cur_stat_col = (118, 124, 138) if (active_system_tab == "llm" and llm_status_color == MUTED_COLOR) else llm_status_color
            stat_surf = Screen.dfont.render(cur_stat_txt, True, cur_stat_col)
            self.screen.blit(stat_surf, (modal_rect.x + 28, modal_rect.y + 546))

            test_label = "测试连接" if active_system_tab == "llm" else "测试发音"
            is_test_hover = rect_btn_test.collidepoint(mx, my)
            btn_test_bg = (244, 240, 233) if is_test_hover else (237, 232, 223)
            btn_test_border = (255, 155, 0) if is_test_hover else (208, 200, 184)
            pygame.draw.rect(self.screen, btn_test_bg, rect_btn_test, border_radius=6)
            pygame.draw.rect(self.screen, btn_test_border, rect_btn_test, width=1, border_radius=6)
            test_txt = Screen.card_font.render(test_label, True, (215, 120, 10) if is_test_hover else (45, 50, 62))
            self.screen.blit(test_txt, (rect_btn_test.x + (rect_btn_test.width - test_txt.get_width()) // 2, rect_btn_test.y + (rect_btn_test.height - test_txt.get_height()) // 2))

            if is_in_game:
                is_title_hover = rect_btn_title.collidepoint(mx, my)
                btn_title_bg = (244, 240, 233) if is_title_hover else (237, 232, 223)
                btn_title_border = (255, 155, 0) if is_title_hover else (208, 200, 184)
                pygame.draw.rect(self.screen, btn_title_bg, rect_btn_title, border_radius=6)
                pygame.draw.rect(self.screen, btn_title_border, rect_btn_title, width=1, border_radius=6)
                title_txt = Screen.card_font.render("返回主界面", True, (215, 120, 10) if is_title_hover else (45, 50, 62))
                self.screen.blit(title_txt, (rect_btn_title.x + (rect_btn_title.width - title_txt.get_width()) // 2, rect_btn_title.y + (rect_btn_title.height - title_txt.get_height()) // 2))

            is_save_hover = rect_btn_save.collidepoint(mx, my)
            btn_save_bg = (255, 155, 0) if is_save_hover else (215, 120, 10)
            pygame.draw.rect(self.screen, btn_save_bg, rect_btn_save, border_radius=6)
            pygame.draw.rect(self.screen, (255, 190, 80) if is_save_hover else (255, 155, 0), rect_btn_save, width=1, border_radius=6)
            save_txt = Screen.card_font.render("保存配置", True, (255, 255, 255))
            self.screen.blit(save_txt, (rect_btn_save.x + (rect_btn_save.width - save_txt.get_width()) // 2, rect_btn_save.y + (rect_btn_save.height - save_txt.get_height()) // 2))

            # 下拉菜单置顶弹出层渲染
            if active_system_tab == "llm":
                dd_model.render_popup(self.screen, Screen.card_font)
            else:
                dd_tts_model.render_popup(self.screen, Screen.card_font)
                dd_tts_voice.render_popup(self.screen, Screen.card_font)

            pygame.display.flip()

        pygame.key.set_repeat(0)
        if self.ui.mode == PLAYER:
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()
        return ""

    def _render_input_box(self, rect: pygame.Rect, text: str, is_active: bool, cursor_vis: bool, sel_start: int = 0, sel_end: int = 0, cursor_idx: int = 0) -> None:
        """渲染带选区高亮与光标的原生文本输入框 (兼容封装：直接委托至 TextInputBox 自绘引擎)"""
        box = TextInputBox(rect, text, Screen.card_font)
        box.is_active = is_active
        box.cursor = cursor_idx
        box.sel_start = sel_start
        box.sel_end = sel_end
        box.render(self.screen, cursor_vis)

    def exit(self) -> NoReturn:
        if hasattr(self, 'daisymo') and self.daisymo:
            try:
                self.daisymo.save()
            except Exception as e:
                debug("退出存盘失败", str(e))
        if hasattr(self, 'mixer') and self.mixer:
            self.mixer.exit()
        pygame.quit()


if __name__ == "__main__":
    app = Screen()
    while True:
        app.title()
        ret = app.main()
        if ret != "title":
            break
