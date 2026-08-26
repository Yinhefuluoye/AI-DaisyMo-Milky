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
DCOLOR      = (255, 155, 0)
QCOLOR      = (255, 255, 255)
BCOLOR      = (0, 0, 0)


def debug(err: str, txt: str) -> None:
    if __DEBUG__:
        print(f"@{err}: {txt}")


import os
import pygame
import requests
from pygame.locals import *
from shutil import (
    copyfile
)
from cv2 import (
    VideoCapture,
    cvtColor,
    COLOR_RGB2BGR
)
from collections import (
    deque
)
from threading import (
    Thread,
    Lock
)
from sys import (
    platform,
    exit as sys_exit
)
from json import (
    dumps as json_dumps,
    loads as json_loads
)
from os import (
    path as os_path,
    listdir,
    replace as os_replace
)
from random import (
    choice,
    randint,
    seed
)
from base64 import (
    b64encode,
    b64decode
)
from time import (
    time,
    localtime,
    strftime
)
from typing import (
    NoReturn,
    Self,
    Tuple,
    Deque,
    Dict,
    List,
    Callable
)


os.environ["PYGAME_FREETYPE"] = '1'
os.environ["SDL_IME_SHOW_UI"] = '1'


class DaisyMo(object):

    first_meet: bool              = not os_path.exists("assets/key")

    base_url: str                 = r"https://api.deepseek.com/v1/chat/completions"

    model_name: str               = "deepseek-chat"

    api_key: str                  = None

    memory: List[Dict[str, str]]  = []

    offset: List[int]             = [0, 0]

    ratio: float                  = 0.72

    default_size: Tuple[int, int] = None

    last_face_path: str           = ''

    last_body_path: str           = ''

    photos: Deque[Tuple[pygame.SurfaceType, pygame.SurfaceType]] = deque([])

    text: str              = ''

    default_save_path: str = ''

    random_face_cache: List[str] = []

    random_body_cache: List[str] = []

    random_back_cache: List[str] = []

    last_usage: Dict[str, int]  = {}

    total_usage: int            = 0

    save_lock: Lock             = Lock()

    def __init__(daisymo, ask_api_key: Callable[[], str]) -> NoReturn:
        if not DaisyMo.first_meet:
            with open("assets/key", 'r', encoding="utf-8") as api_key_file:
                DaisyMo.api_key = api_key_file.read().strip()

        else:
            DaisyMo.api_key = ask_api_key()

            if not __DEBUG__:
                with open("assets/key", 'w', encoding="utf-8") as api_key_file:
                    api_key_file.write(DaisyMo.api_key)


    def init(daisymo) -> Dict[str, str]:
        soul_file_path: str = "assets/DaisyMo.soul"

        if not os_path.exists(soul_file_path):
            copyfile("DaisyMo.soul", "assets/DaisyMo.soul")
            debug("致命错误", "assets/DaisyMo.soul不存在！")
            #sys_exit()

        daisymo_soul: str = ''
        with open(soul_file_path, 'r', encoding="utf-8") as daisymo_soul_file:
            daisymo_soul = daisymo_soul_file.read().strip()

        # if not __DEBUG__ and DaisyMo.first_meet:
        #     daisymo.save()

        try:
            if daisymo_soul[0] == '[':
                #daisymo.load(daisymo_soul)
                return daisymo.next(daisymo.last_chat(daisymo.parse(daisymo_soul)))

        except Exception as e:
            # 存档损坏（空文件/半截JSON）：备份坏档后回退模板重新开局，不再直接崩
            debug("存档损坏", f"in init with error: {e}")

            os_replace(soul_file_path, soul_file_path + ".corrupt.bak")
            copyfile("DaisyMo.soul", soul_file_path)

            with open(soul_file_path, 'r', encoding="utf-8") as daisymo_soul_file:
                daisymo_soul = daisymo_soul_file.read().strip()

        seed(BIRTH)

        return daisymo.chat_then_parse(daisymo_soul)


    def update_offset_center(daisymo) -> Self:
        DaisyMo.offset[0] = (DaisyMo.default_size[0] - Screen.default_size[0]) // 2
        #DaisyMo.offset[1] = (DaisyMo.default_size[1] - Screen.default_size[1]) // 2

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
        DaisyMo.memory.append({"role": "user", "content": text})

        response: requests.Response = requests.post(
            DaisyMo.base_url,
            headers={"Authorization": "Bearer {}".format(b64decode(DaisyMo.api_key.encode()).decode())},
            json={"model": DaisyMo.model_name, "messages": DaisyMo.memory}
        )

        #print({"Authorization": "Bearer {}".format(DaisyMo.api_key)})
        #print({"model": DaisyMo.model_name, "message": DaisyMo.memory})

        if response.status_code != 200:
            debug("回复失败", f"返回码{response.status_code}")
            DaisyMo.memory.pop()
            return ''
                
        response_json: Dict = response.json()

        respond: str = response_json["choices"][0]["message"]["content"].replace('```json', '').replace('```', '')
        DaisyMo.memory.append({"role": "assistant", "content": respond})

        DaisyMo.last_usage = response_json.get("usage", {})
        DaisyMo.total_usage += DaisyMo.last_usage.get("total_tokens", 0)

        if __DEBUG__:
            print('= ' * 10)
            print(respond)
            print('= ' * 10)

        return respond
    

    def chat_then_parse(daisymo, text: str) -> Dict[str, str]:
        if not text:
            debug("不能为空", "in chat_then_parse text")
            return {}

        respond_json: Dict[str, str] = {}
        raw: str = daisymo.chat(text)

        try:
            respond_json = json_loads(raw)

        except Exception as e:
            start = raw.find('{')
            end = raw.rfind('}') + 1

            if start == -1 or end == 0:
                return {}

            try:
                respond_json = json_loads(raw[start: end])
            except Exception as e:
                debug("解析失败", f"in chat_then_parse json_loads with error: {e}")
                return {}

        if not respond_json:
            debug("解释失败", "in chat_then_parse respond_json")
            return {}
        
        daisymo.next(respond_json)

        return respond_json
    

    def next(daisymo, respond_json: Dict[str, str]) -> Dict[str, str]:
        if DaisyMo.photos:
            last_face, last_body = DaisyMo.photos.pop()

        face_pic_path: str = "assets/daisymo/face/{}.png".format(respond_json.get("face", "温柔-说"))
        body_pic_path: str = "assets/daisymo/body/{}.png".format(respond_json.get("body", "便服单叉腰"))
        back_pic_path: str = "assets/bg/{}.jpg".format(respond_json.get("where", "学校门口白天"))

        face: pygame.SurfaceType = (
            pygame.image.load(face_pic_path).convert_alpha()
            if DaisyMo.last_face_path != face_pic_path
            else last_face
        )
        body: pygame.SurfaceType = (
            pygame.image.load(body_pic_path).convert_alpha()
            if DaisyMo.last_body_path != body_pic_path
            else last_body
        )
        back: pygame.SurfaceType = (
            pygame.image.load(back_pic_path).convert()
            if Screen.last_back_path != back_pic_path
            else Screen.default_back
        )

        if DaisyMo.ratio != 1.0:
            face = pygame.transform.rotozoom(face, 0.0, DaisyMo.ratio)
            body = pygame.transform.rotozoom(body, 0.0, DaisyMo.ratio)

        DaisyMo.photos.append((face, body))
        Screen.default_back = back
        DaisyMo.text = respond_json.get("text", "【回答失败！】")

        return respond_json
    

    def auto_save(daisymo) -> NoReturn:
        Thread(target=daisymo.save, name="daisymo_auto_save").start()


    def save(daisymo) -> bool:
        save_file_path: str = "assets/DaisyMo.soul"
        temp_file_path: str = "assets/DaisyMo.soul.tmp"

        # 加锁防 auto_save 线程与退出时的 save 并发写；快照防遍历途中主线程 append
        with DaisyMo.save_lock:
            soul: str = json_dumps(DaisyMo.memory[:])

            # 先写临时文件再原子替换：任何时刻被打断，磁盘上都是完整的旧档或新档
            with open(temp_file_path, 'w', encoding="utf-8") as save_file:
                save_file.write(soul)

            os_replace(temp_file_path, save_file_path)

        return 1


    def load(daisymo, soul: str) -> Self:
        DaisyMo.memory = json_loads(soul)

        #DaisyMo.default_save_path = load_file_path

        return daisymo
    

    def parse(daisymo, content: str) -> Dict[str, str] | List[Dict[str, str]]:
        return json_loads(content)
    

    def random_face(daisymo) -> NoReturn:
        random_face_path: str = ''

        if not DaisyMo.random_face_cache:
            DaisyMo.random_face_cache.extend(
                [
                    "assets/daisymo/face/{}".format(e)
                    for e in listdir("assets/daisymo/face")
                ]
            )

        random_face_path = choice(DaisyMo.random_face_cache)

        if DaisyMo.photos:
            _, last_body = DaisyMo.photos.pop()

        face: pygame.SurfaceType = pygame.image.load(random_face_path).convert_alpha()

        if DaisyMo.ratio != 1.0:
            face = pygame.transform.rotozoom(face, 0.0, DaisyMo.ratio)

        DaisyMo.photos.append((face, last_body))


    def random_body(daisymo) -> NoReturn:
        random_body_path: str = ''

        if not DaisyMo.random_body_cache:
            DaisyMo.random_body_cache.extend(
                [
                    "assets/daisymo/body/{}".format(e)
                    for e in listdir("assets/daisymo/body")
                ]
            )

        random_body_path = choice(DaisyMo.random_body_cache)

        if DaisyMo.photos:
            last_face, _ = DaisyMo.photos.pop()

        body: pygame.SurfaceType = pygame.image.load(random_body_path).convert_alpha()

        if DaisyMo.ratio != 1.0:
            body = pygame.transform.rotozoom(body, 0.0, DaisyMo.ratio)

        DaisyMo.photos.append((last_face, body))


    def random_back(daisymo) -> NoReturn:
        random_back_path: str = ''

        if not DaisyMo.random_back_cache:
            DaisyMo.random_back_cache.extend(
                [
                    "assets/bg/{}".format(e)
                    for e in listdir("assets/bg")
                ]
            )

        random_back_path = choice(DaisyMo.random_back_cache)

        Screen.default_back = pygame.image.load(random_back_path).convert_alpha()
    

    def last_chat(daisymo, response: List[Dict[str, str]]) -> Dict[str, str]:
        DaisyMo.memory.extend(response)
        return daisymo.parse(response[-1].get("content", '{}'))
    

    def random_change_time(daisymo) -> float:
        random_time: float = randint(6, 12)

        debug("log", f"random_change_time -> {random_time}s")

        return random_time
    

    def history_surface(daisymo, size: Tuple[int, int]) -> pygame.SurfaceType:
        hsurf: pygame.SurfaceType = pygame.surface.Surface(size)
        hfont: pygame.font.FontType = pygame.font.Font("assets/font/SIMYOU.TTF", 16)
        x: int = 0
        y: int = 0
        target: str = ''
        current_text: pygame.SurfaceType = None
        content: Dict[str, str] = {}

        hsurf.fill(QCOLOR)

        current_text = hfont.render("<点击屏幕最顶上返回；长按屏幕中上则上翻；中下则下翻>", True, DCOLOR)
        hsurf.blit(current_text, (x, y))
        y += current_text.get_height() + 5

        for e in DaisyMo.memory[1: ]:
            if e["role"] == "user":
                target = "邱诚(我)"
                content = e["content"]

                current_text = hfont.render("{}: {}".format(target, content), True, BCOLOR)
            else:
                target = "墨小菊"
                content = daisymo.parse(e["content"])
            
                current_text = hfont.render(
                    "{}[{} {} {}]: {}".format(target, content["where"], content["body"], content["face"], content["text"]),
                    True,
                    BCOLOR
                )

            hsurf.blit(current_text, (x, y))
            y += current_text.get_height() + 5

        return hsurf

# 音乐播放组件
class Mixer(object):

    pointer: int = -1

    music_list: str = ["assets/bgm/bgm10_Ora.ogg"]

    def __init__(self) -> NoReturn:
        pygame.mixer.init()
        

    def air(self) -> NoReturn:
        Mixer.pointer = (Mixer.pointer + 1) % len(Mixer.music_list)

        pygame.mixer.music.load(Mixer.music_list[Mixer.pointer])
        pygame.mixer.music.play(-1)


    def exit(self) -> NoReturn:
        pygame.mixer.music.stop()

# 闪烁光标组件
class BlinkCursor(object):

    BLINK_INTERVAL: float = 0.5

    def __init__(self) -> NoReturn:
        self.visible: bool      = True
        self.last_blink_time: float = time()


    def tick(self) -> NoReturn:
        if time() - self.last_blink_time >= BlinkCursor.BLINK_INTERVAL:
            self.visible = not self.visible
            self.last_blink_time = time()

            # 渲染闪烁光标 | ：紧贴 player_input 末尾
    def draw(self, surface: pygame.SurfaceType, font: pygame.font.FontType, color: Tuple[int, int, int], rects: List[Tuple[pygame.SurfaceType, Tuple[int, int]]], fallback_rect: Tuple[int, int]) -> NoReturn:
        if not self.visible:
            return

        if rects:
            last_surf, (lx, ly) = rects[-1]
            cursor_x: int = lx + last_surf.get_width()
            cursor_y: int = ly
        else:
            # 输入为空时光标显示在 fallback_rect 位置
            cursor_x, cursor_y = fallback_rect

        cursor_surf: pygame.SurfaceType = font.render('|', True, color)
        surface.blit(cursor_surf, (cursor_x, cursor_y))

# 屏幕组件
class Screen(object):

    default_size: Tuple[int, int]         = (1280, 720)

    default_back: pygame.SurfaceType      = None

    font: pygame.font.FontType            = None

    fast_text: pygame.SurfaceType         = None

    text_rect: Tuple[int, int]            = None

    player_input_text: pygame.SurfaceType = None

    player_input_rect: Tuple[int, int]    = None

    last_back_path: str                   = ''

    FPS: int                              = 20

    current_text: str                     = ''

    display_text: str                     = ''

    current_text_index: int               = 0

    fast_text_lines: List[pygame.SurfaceType] = []

    fast_text_rects: List[Tuple[pygame.SurfaceType, Tuple[int, int]]] = []

    player_input_lines: List[pygame.SurfaceType] = []

    player_input_rects: List[Tuple[pygame.SurfaceType, Tuple[int, int]]] = []

    typewriter_interval: float            = 0.03

    last_type_time: float                 = 0.0

    def __init__(self) -> NoReturn:
        not pygame.get_init() and pygame.init()

        if platform == "linux":
            self.screen = pygame.display.set_mode(self.default_size, FULLSCREEN | DOUBLEBUF)
            Screen.default_size = self.screen.get_size()
        else:
            self.screen = pygame.display.set_mode(Screen.default_size, vsync=1)
        
        pygame.display.set_caption("AI墨小菊")
        pygame.display.set_icon(pygame.image.load("icon.png").convert_alpha())

        self.init()


    def init(self) -> NoReturn:
        Screen.font = pygame.font.Font("assets/font/SourceHanSansCN-Medium.otf", 28)
        Screen.dfont = pygame.font.Font("assets/font/SourceHanSansCN-Regular.otf", 18)
        Screen.qfont = pygame.font.Font("assets/font/SourceHanSansCN-Medium.otf", 18)
        self.main_botm: pygame.SurfaceType  = pygame.image.load("assets/ui/main_botm_demo.png").convert_alpha()
        self.main_botm_pos: Tuple[int, int] = (
            (self.screen.get_width() - self.main_botm.get_width()) // 2,
            self.screen.get_height() - self.main_botm.get_height()
        )

        # self.daisymo: DaisyMo = DaisyMo(self.ask_api_key)
        self.mixer: Mixer = Mixer()
        self.mixer.air()


    # 标题开场动画与点击进入提示
    def title(self) -> Self:
        player: VideoCapture = VideoCapture("assets/ui/title_end_m.wmv")
        is_opened: bool = player.isOpened()
        clock: pygame.time.Clock = pygame.time.Clock()
        is_running: bool = True
        back: pygame.SurfaceType = pygame.image.load("assets/ui/title_end_m.jpg").convert()
        hint: pygame.SurfaceType = Screen.font.render("<点击任意处进入对话>", 1, DCOLOR)
        hint_alpha: int = 255
        hint_pos: Tuple[int, int] = (
            (self.screen.get_width() - hint.get_width()) // 2,
            (self.screen.get_height() - hint.get_height()) // 2 + 100
        )
        hint_forward: bool = False
        # white: pygame.SurfaceType = pygame.image.load("assets/ui/white.png").convert_alpha()
        # white_alpha: int = 0

        while is_opened:
            clock.tick(30)

            is_opened, frame = player.read()

            if not is_opened:
                break

            frame = pygame.surfarray.make_surface(cvtColor(frame, COLOR_RGB2BGR).swapaxes(0, 1))
            frame = pygame.transform.scale(frame, self.screen.get_size())

            self.screen.blit(frame, (0, 0))

            pygame.display.flip()


        pygame.event.clear()
        while is_running:

            for event in pygame.event.get():

                if event.type == QUIT:
                    self.mixer.exit()
                    pygame.quit()
                    sys_exit()

                if event.type == MOUSEBUTTONDOWN or event.type == KEYDOWN:
                    is_running = False

            self.screen.blits(
                (
                    (back, (0, 0)),
                    (hint, hint_pos)
                )
            )
            pygame.display.flip()

            if not hint_forward:
                hint_alpha -= 0.66
                if hint_alpha <= 0:
                    hint_forward = not hint_forward
                    hint_alpha = 0
            
            else:
                hint_alpha += 0.66
                if hint_alpha >= 255:
                    hint_forward = not hint_forward
                    hint_alpha = 255

            hint.set_alpha(hint_alpha)

        # pygame.event.set_blocked([MOUSEMOTION])
        # while white_alpha < 255:
        #     # back.set_alpha(white_alpha := white_alpha + 0.8)
        #     # self.screen.blit(back, (0, 0))
        #     self.screen.fill([0, 0, 0, ])
        #     pygame.display.flip()

        self.daisymo: DaisyMo = DaisyMo(lambda : self.ask_api_key(back))

        pygame.event.clear()

        return self


    def wrap_text(self, text: str, max_width: int) -> List[str]:
        lines: List[str] = []
        current_line: str = ''

        for ch in text:
            test_line = current_line + ch
            if Screen.font.size(test_line)[0] > max_width and current_line:
                lines.append(current_line)
                current_line = ch
            else:
                current_line = test_line

        if current_line:
            lines.append(current_line)

        return lines


    def start_typewriter(self, text: str) -> NoReturn:
        self.current_text = text
        self.display_text = ''
        self.current_text_index = 0
        self.last_type_time = time()
        self.update_fast_text_rect()


    def step_typewriter(self) -> NoReturn:
        if self.current_text_index < len(self.current_text) and time() - self.last_type_time >= self.typewriter_interval:
            self.current_text_index += 1
            self.display_text = self.current_text[: self.current_text_index]
            self.last_type_time = time()
            self.update_fast_text_rect()


    def update(self) -> NoReturn:
        if Screen.default_back:
            self.screen.blit(Screen.default_back, (0, 0))

        if self.daisymo.photos:
            for each in DaisyMo.photos:
                self.screen.blits(
                    (
                        (each[1], DaisyMo.offset),
                        (each[0], DaisyMo.offset)
                    )
                )

        self.screen.blit(self.main_botm, self.main_botm_pos)

        for surf, rect in Screen.fast_text_rects:
            self.screen.blit(surf, rect)

        for surf, rect in Screen.player_input_rects:
            self.screen.blit(surf, rect)


    def unsafe_update(self) -> NoReturn: #deserted!
        self.screen.blits(
            (
                (Screen.default_back, (0, 0)),
                (DaisyMo.photos[0][1], DaisyMo.offset),
                (DaisyMo.photos[0][0], DaisyMo.offset),
                *Screen.fast_text_rects,
                *Screen.player_input_rects
            )
        )


    def update_fast_text_rect(self) -> NoReturn:
        text_to_render = self.display_text
        Screen.fast_text_lines = self.wrap_text(text_to_render, Screen.default_size[0] - 100)
        Screen.fast_text_rects = []

        base_y = (Screen.default_size[1] - len(Screen.fast_text_lines) * Screen.font.get_height()) - 100

        for index, line in enumerate(Screen.fast_text_lines):
            #surf = Screen.font.render(line, True, DCOLOR)
            surf = Screen.dfont.render(line, True, DCOLOR)
            rect = (
                (Screen.default_size[0] - surf.get_width()) // 2,
                base_y + index * Screen.font.get_height()
            )
            Screen.fast_text_rects.append((surf, rect))

        Screen.text_rect = Screen.fast_text_rects[0][1] if Screen.fast_text_rects else ((Screen.default_size[0]) // 2, base_y)


    def update_player_input_rect(self, player_input: str) -> NoReturn:
        Screen.player_input_lines = []
        Screen.player_input_rects = []

        lines = self.wrap_text(player_input, Screen.default_size[0] - 100)
        base_y = Screen.default_size[1] - (len(lines) if lines else 1) * Screen.font.get_height() - 20
        x = Screen.text_rect[0]

        for index, line in enumerate(lines):
            #surf = Screen.font.render(line, True, QCOLOR)
            surf = Screen.qfont.render(line, True, QCOLOR)
            rect = (
                x,
                base_y + index * Screen.font.get_height()
            )
            Screen.player_input_rects.append((surf, rect))

        Screen.player_input_text = Screen.player_input_lines[0] if Screen.player_input_lines else None
        Screen.player_input_rect = Screen.player_input_rects[0][1] if Screen.player_input_rects else (x, base_y)


    def parse(self) -> NoReturn:
        self.start_typewriter(DaisyMo.text)
        self.update_player_input_rect('')


    # 主对话界面（含立绘、文本逐字显示、玩家输入与主循环）
    def main(self) -> NoReturn:
        run: bool                 = True
        script: Dict[str, str]    = None
        player_input: str         = ''
        root: int                 = DAISYMO
        input_active: bool        = True
        clock: pygame.time.Clock  = pygame.time.Clock()
        # last_chat_time: float     = 0.0
        # random_change_time: float = 1000
        x = y = 0

        # 光标组件
        blink: BlinkCursor = BlinkCursor()

        script = self.daisymo.init()
        self.daisymo.update_default_size().update_offset_center()
        self.parse()

        bug_normal: pygame.SurfaceType = pygame.image.load("assets/ui/title_btn_bug_normal.png").convert_alpha()
        bug_over: pygame.SurfaceType = pygame.image.load("assets/ui/title_btn_bug_over.png").convert_alpha()
        bug_rect: Tuple[4] = (
            0,
            self.screen.get_height() // 4,
            0 + bug_normal.get_width(),
            self.screen.get_height() // 4 + bug_normal.get_height()
        )
        hint: pygame.SurfaceType = pygame.image.load("assets/ui/YorN_botm_exit.bmp").convert()
        hint_pos: Tuple[2] = (
            (self.screen.get_width() - hint.get_width()) // 2,
            (self.screen.get_height() - hint.get_height()) // 2
        )

        history_normal: pygame.SurfaceType = pygame.image.load("assets/ui/main_btn_backlog_normal.png").convert_alpha()
        history_over: pygame.SurfaceType = pygame.image.load("assets/ui/main_btn_backlog_over.png").convert_alpha()
        history_rect: Tuple[4] = (
            0,
            self.screen.get_height() - history_normal.get_height(),
            (0, history_normal.get_width()),
            (self.screen.get_height() - history_normal.get_height(), self.screen.get_height())
        )

        t = localtime()
        other_font: pygame.font.FontType = pygame.font.Font("assets/font/SIMYOU.TTF", 15)
        other_font.set_underline(1)
        other_text: pygame.SurfaceType = other_font.render(
            #"时间: {}".format(strftime("%Y年%m月%d日%H时%M分%S秒", localtime())),
            "时间: {}".format(
                f"{t.tm_year}年{t.tm_mon:02d}月{t.tm_mday:02d}日"
                f"{t.tm_hour:02d}时{t.tm_min:02d}分{t.tm_sec:02d}秒"
            ),
            True,
            DCOLOR
        )
        other_pos: Tuple[2] = (
            hint_pos[0],
            self.screen.get_height() - other_text.get_height()
        )

        while run:
            
            t = localtime()
            other_text = other_font.render(
                "时间: {}".format(
                    f"{t.tm_year}年{t.tm_mon:02d}月{t.tm_mday:02d}日"
                    f"{t.tm_hour:02d}时{t.tm_min:02d}分{t.tm_sec:02d}秒"
                ),
                True,
                DCOLOR
            )

            # Token 用量：上次请求的上下文长度（本次消耗 / 会话累计）
            token_text = Screen.dfont.render(
                "上下文: {} tokens（本次 +{} / 累计 {}）".format(
                    DaisyMo.last_usage.get("prompt_tokens", 0),
                    DaisyMo.last_usage.get("total_tokens", 0),
                    DaisyMo.total_usage
                ),
                True,
                DCOLOR
            )
            token_pos = (
                self.screen.get_width() - token_text.get_width() - 10,
                self.screen.get_height() - token_text.get_height() - 5
            )

            clock.tick(Screen.FPS)
            self.step_typewriter()

            for event in pygame.event.get():

                if event.type == QUIT:
                    run = not run
                    break

                elif event.type == MOUSEBUTTONDOWN:
                    x, y = event.pos

                    if history_rect[2][0] <= x <= history_rect[2][1] and history_rect[3][0] <= y <= history_rect[3][1]:
                        self.history_menu()
                        break

                    if platform == "linux":
                        pygame.key.start_text_input()
                    input_active = True

                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        run = not run

                    elif event.key == K_RETURN:
                        debug("log", "key return for chat")
                        if platform == "linux":
                            pygame.key.stop_text_input()

                        self.daisymo.chat_then_parse(player_input)
                        self.start_typewriter(DaisyMo.text)
                        self.update_player_input_rect('')
                        player_input = ''
                        # last_chat_time = time()
                        # random_change_time = self.daisymo.random_change_time()
                        self.daisymo.auto_save()

                    elif event.key in (K_BACKSPACE, K_DELETE):
                        player_input = player_input[: -1]
                        self.update_player_input_rect(player_input)
                        debug("log", f"DELETE current player_input: {player_input}")

                    elif __DEBUG__ and event.key == K_s and not self.daisymo.save():
                        debug("保存失败", "save in K_s")

                    elif event.key == K_1:
                        self.daisymo.random_face()

                    elif event.key == K_2:
                        self.daisymo.random_body()

                    elif event.key == K_3:
                        self.daisymo.random_back()

                elif event.type == TEXTINPUT:
                    player_input += event.text
                    self.update_player_input_rect(player_input)
                    debug("log", f"TEXTINPUT current player_input: {player_input}")

                elif event.type == MOUSEMOTION:
                    x, y = event.pos

            # if RANDOM_FACE and  time() - last_chat_time >= random_change_time:
            #     debug("log", "random_change_time is over!")
            #     self.daisymo.random_face()
            #     last_chat_time = time()
            #     random_change_time = self.daisymo.random_change_time()

            #self.unsafe_update()
            self.update()

            # 光标闪烁
            blink.tick()

            # 渲染闪烁光标 | ：紧贴 player_input 末尾
            blink.draw(self.screen, Screen.qfont, QCOLOR, Screen.player_input_rects, Screen.player_input_rect)

            if bug_rect[0] <= x <= bug_rect[2] and bug_rect[1] <= y <= bug_rect[3]:
                self.screen.blits(
                    (
                        (bug_over, bug_rect[: 2]),
                        (hint, hint_pos)
                    )
                )
            else:
                self.screen.blits(
                    (
                        (bug_normal, bug_rect[: 2]),
                        (other_text, other_pos)
                    )
                )

            if history_rect[2][0] <= x <= history_rect[2][1] and history_rect[3][0] <= y <= history_rect[3][1]:
                self.screen.blit(history_normal, history_rect[: 2])
            else:
                self.screen.blit(history_over, history_rect[: 2])

            self.screen.blit(token_text, token_pos)

            pygame.display.flip()

        self.exit()


    def exit(self) -> NoReturn:
        self.daisymo.save()
        self.mixer.exit()
        pygame.quit()


    # 页面：首次进入时输入 API-Key 的弹窗
    def ask_api_key(self, back: pygame.SurfaceType, title: str = "初次进入，需输入Api-Key") -> str:
        asking: bool = True
        inputing: bool = False
        api_key: str = ''

        Screen.font.set_bold(1)

        # 顶部提示文字 - 屏幕 1/3 高度
        hint_text: pygame.SurfaceType = Screen.font.render(title, True, BCOLOR)
        hint_pos: List[int, int] = [
            (self.screen.get_width() - hint_text.get_width()) // 2,
            self.screen.get_height() // 3
        ]
        # 唤醒键盘提示 - 紧贴在提示文字下方
        click_text: pygame.SurfaceType = Screen.font.render("<点击屏幕唤醒键盘>", True, BCOLOR)
        click_pos: Tuple[2] = (
            (self.screen.get_width() - click_text.get_width()) // 2,
            self.screen.get_height() // 3 + hint_text.get_height() + 10
        )

        # API Key 文字渲染在主对话框 main_botm 内部（按宽度自动换行）
        api_key_rects: List[Tuple[pygame.SurfaceType, Tuple[int, int]]] = []
        def _refresh_api_key() -> None:
            nonlocal api_key_rects
            lines: List[str] = self.wrap_text(api_key, self.main_botm.get_width() - 40)
            total_h: int = len(lines) * Screen.font.get_height()
            base_y: int = self.main_botm_pos[1] + (self.main_botm.get_height() - total_h) // 2
            api_key_rects = [
                (
                    Screen.font.render(line, True, DCOLOR),
                    (self.main_botm_pos[0] + 20, base_y + i * Screen.font.get_height())
                )
                for i, line in enumerate(lines)
            ]
        _refresh_api_key()

        # 长按删除：首次按下立即删一格；超过延迟后按间隔连续删
        backspace_held: bool         = False
        backspace_hold_start: float  = 0.0
        backspace_last_delete: float = 0.0
        BS_REPEAT_DELAY: float       = 0.5     # 长按 500ms 后开始连删
        BS_REPEAT_INTERVAL: float    = 0.05    # 连删时每 50ms 删一格

        # 闪烁光标 |：inputing 时显示，0.5s 切换一次可见性
        blink: BlinkCursor = BlinkCursor()

        while asking:

            for event in pygame.event.get():

                if event.type == QUIT:
                    self.mixer.exit()
                    pygame.quit()
                    sys_exit()

                if event.type == MOUSEBUTTONDOWN:
                    if platform == "linux":
                        pygame.key.start_text_input()
                    if not inputing:
                        inputing = True
                        hint_text = Screen.font.render("请在下方对话框内输入Api-Key后回车（可使用Ctrl+V粘贴）", True, BCOLOR)
                        hint_pos[0] = (self.screen.get_width() - hint_text.get_width()) // 2
                        hint_pos[1] = self.main_botm_pos[1] - hint_text.get_height() - 50

                elif event.type == TEXTINPUT and inputing:
                    api_key += event.text
                    _refresh_api_key()

                elif event.type == KEYDOWN:
                    if event.key in (K_DELETE, K_BACKSPACE):
                        # 首次按下立即删一格，并标记进入长按状态
                        if not backspace_held and api_key:
                            api_key = api_key[: -1]
                            _refresh_api_key()
                            backspace_held = True
                            backspace_hold_start = time()
                            backspace_last_delete = time()

                    elif (pygame.key.get_mods() & KMOD_CTRL) and event.key == K_v:
                        pasted: str = ''
                        try:
                            import tkinter as tk
                            _tk: tk.Tk = tk.Tk()
                            _tk.withdraw()
                            _tk.update()
                            pasted = _tk.clipboard_get()
                            _tk.destroy()
                        except Exception as e:
                            debug("粘贴失败", f"clipboard_get: {e}")
                        if pasted:
                            pasted = pasted.strip().replace('\n', '').replace('\r', '').replace('\t', '')
                            api_key += pasted
                            _refresh_api_key()

                    elif event.key == K_RETURN:
                        if platform == "linux":
                            pygame.key.stop_text_input()
                        inputing = asking = False

                elif event.type == KEYUP and event.key in (K_DELETE, K_BACKSPACE):
                    backspace_held = False

            # 长按连删：过了初始延迟后按 BS_REPEAT_INTERVAL 持续删
            if backspace_held and inputing and api_key:
                now: float = time()
                if now - backspace_hold_start >= BS_REPEAT_DELAY:
                    if now - backspace_last_delete >= BS_REPEAT_INTERVAL:
                        api_key = api_key[: -1]
                        _refresh_api_key()
                        backspace_last_delete = now
                # 兜底：KEYUP 事件不可靠时，用键盘状态自检
                keys = pygame.key.get_pressed()
                if not (keys[K_BACKSPACE] or keys[K_DELETE]):
                    backspace_held = False

            # 光标闪烁
            blink.tick()

            self.screen.blits(
                (
                    (back, (0, 0)),
                    (self.main_botm, self.main_botm_pos),
                    (hint_text, hint_pos),
                    *api_key_rects
                )
            )

            # 渲染闪烁光标 | ：紧贴 api_key 末尾
            if inputing:
                cursor_fallback: Tuple[int, int] = (
                    self.main_botm_pos[0] + 20,
                    self.main_botm_pos[1] + (self.main_botm.get_height() - Screen.font.get_height()) // 2
                )
                blink.draw(self.screen, Screen.font, DCOLOR, api_key_rects, cursor_fallback)

            if not inputing:
                self.screen.blit(click_text, click_pos)

            pygame.display.flip()

        Screen.font.set_bold(0)

        return b64encode(api_key.encode()).decode()
    

    # 历史对话回顾
    def history_menu(self) -> NoReturn:
        screen_width, screen_height = self.screen.get_size()

        history_surf: pygame.SurfaceType = self.daisymo.history_surface((screen_width, screen_height))
        history_surf_pos: List[2] = [0, 0]
        history_board: pygame.SurfaceType = pygame.image.load("assets/ui/backlog_botm.png").convert_alpha()
        history_board_pos: Tuple[2] = (0, 0)

        last_x = last_y = 0

        running: bool = True
        rolling_up: bool = False
        rolling_down: bool = False
        while running:

            for event in pygame.event.get():

                if event.type == QUIT:
                    self.daisymo.save()
                    self.mixer.exit()
                    pygame.quit()
                    sys_exit()

                elif event.type == MOUSEBUTTONDOWN:
                    x, y = event.pos
                    if 0 <= x <= screen_width and 0 <= y <= screen_height // 8:
                        running = False
                    if 0 <= x <= screen_width and screen_height // 8 <= y <= screen_height // 2:
                        rolling_up = True
                    if 0 <= x <= screen_width and screen_height // 2 <= y <= screen_height:
                        rolling_down = True
                    # if 0 <= x <= screen_width // 2 and 0 <= y <= screen_height:
                    #     rolling_left = True
                    # if screen_width // 2 <= x <= screen_width and 0 <= y <= screen_height:
                    #     rolling_right = True

                elif event.type == MOUSEBUTTONUP:
                    rolling_down = rolling_up = rolling_left = rolling_right = False

            if rolling_down:
                history_surf_pos[1] -= 0.5
            if rolling_up:
                history_surf_pos[1] += 0.5
            # if rolling_left:
            #     history_surf_pos[0] -= 0.5
            # if rolling_right:
            #     history_surf_pos[0] += 0.5

            self.screen.fill(QCOLOR)
            self.screen.blit(history_surf, history_surf_pos)
            # self.screen.blits(
            #     (
            #         #(history_board, history_board_pos),
            #         (history_surf, history_surf_pos)
            #     )
            # )
            pygame.display.update()


if __name__ == "__main__":
    (
        Screen()
        .title()
        .main()
    )