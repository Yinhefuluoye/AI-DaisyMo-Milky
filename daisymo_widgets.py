# -*- coding: utf-8 -*-
"""
DaisyMo Pygame 声明式自绘控件库 (Pygame Declarative UI Widgets Engine)
提供高度契合《三色绘恋》和纸风格的自绘控件，包含：
1. BlinkCursor: 呼吸光标节拍器
2. TextInputBox: 带选区高亮、鼠标拖拽划选、双击全选、剪贴板交互、平滑快速连删的自绘单行文本框
3. SliderBar: 平滑自绘滑块组件（支持点击、拖拽、步进调节）
4. DropdownMenu: 浮层下拉列表组件（支持气泡高亮、点击外部自动关闭、滚轮浏览）
5. TabGroup: 选项卡分组组件
6. DialogueScrollBar: 对白垂直滚动条
7. ConfirmDialog: 和风模态二次确认弹窗
8. InputDialog: 和风模态文本输入弹窗（内置单行文本域与空值校验）
"""

import time
from typing import Callable, Dict, List, Optional, Tuple, Any

import pygame
from pygame.locals import (
    K_a, K_c, K_v, K_x,
    K_BACKSPACE, K_DELETE,
    K_LEFT, K_RIGHT, K_HOME, K_END,
    K_RETURN, K_KP_ENTER, K_ESCAPE, K_TAB,
    KMOD_CTRL, KMOD_SHIFT,
    KEYDOWN, KEYUP,
    MOUSEBUTTONDOWN, MOUSEBUTTONUP, MOUSEMOTION,
    TEXTINPUT
)


class BlinkCursor:
    """光标呼吸节拍器"""
    BLINK_INTERVAL: float = 0.5

    def __init__(self, interval: float = 0.5) -> None:
        self.interval: float = interval
        self.visible: bool = True
        self.last_blink_time: float = time.time()

    def tick(self) -> bool:
        now = time.time()
        if now - self.last_blink_time >= self.interval:
            self.visible = not self.visible
            self.last_blink_time = now
        return self.visible

    def reset(self) -> None:
        self.visible = True
        self.last_blink_time = time.time()


class TextInputBox:
    """
    自绘和纸风格单行文本输入框
    - 支持点击定焦、鼠标拖选、双击词选、全选 (Ctrl+A)
    - 支持剪切、复制、粘贴 (Ctrl+X, Ctrl+C, Ctrl+V)
    - 支持长按 Backspace / Delete 快速平滑连删
    - 支持密码掩码显示 (is_password)
    - 超长文字水平自动平移与选区高亮渲染
    """

    def __init__(
        self,
        rect: pygame.Rect,
        text: str = "",
        font: Optional[pygame.font.Font] = None,
        is_password: bool = False,
        placeholder: str = "",
        max_length: Optional[int] = None,
        border_radius: int = 6,
        bg_color: Optional[Tuple[int, int, int]] = (242, 238, 231),
        border_color: Optional[Tuple[int, int, int]] = (220, 213, 200),
        active_border_color: Optional[Tuple[int, int, int]] = (215, 120, 10),
        text_color: Tuple[int, int, int] = (31, 35, 43),
        placeholder_color: Tuple[int, int, int] = (160, 160, 160),
        sel_color: Tuple[int, int, int] = (255, 200, 120),
        cursor_color: Tuple[int, int, int] = (215, 120, 10),
        max_lines: int = 1
    ) -> None:
        self.rect: pygame.Rect = pygame.Rect(rect)
        self._text: str = text
        self.font: Optional[pygame.font.Font] = font
        self.is_password: bool = is_password
        self.placeholder: str = placeholder
        self.max_length: Optional[int] = max_length
        self.border_radius: int = border_radius
        self.max_lines: int = max_lines

        # 颜色样式
        self.bg_color: Tuple[int, int, int] = bg_color
        self.border_color: Tuple[int, int, int] = border_color
        self.active_border_color: Tuple[int, int, int] = active_border_color
        self.text_color: Tuple[int, int, int] = text_color
        self.placeholder_color: Tuple[int, int, int] = placeholder_color
        self.sel_color: Tuple[int, int, int] = sel_color
        self.cursor_color: Tuple[int, int, int] = cursor_color

        # 交互状态
        self.is_active: bool = False
        self.cursor: int = len(text)
        self.sel_start: int = 0
        self.sel_end: int = 0
        self.is_dragging: bool = False
        self.last_click_time: float = 0.0

        # 快速连删状态
        self.backspace_held: bool = False
        self.backspace_start_time: float = 0.0
        self.backspace_last_fire: float = 0.0

        self.delete_held: bool = False
        self.delete_start_time: float = 0.0
        self.delete_last_fire: float = 0.0

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, val: str) -> None:
        self._text = val
        self.cursor = min(self.cursor, len(val))
        self.sel_start = min(self.sel_start, len(val))
        self.sel_end = min(self.sel_end, len(val))

    def get_display_text(self) -> str:
        if self.is_password:
            return "•" * len(self._text)
        return self._text

    def set_font(self, font: pygame.font.Font) -> None:
        self.font = font

    def select_all(self) -> None:
        self.sel_start = 0
        self.sel_end = len(self._text)
        self.cursor = len(self._text)

    def clear(self) -> None:
        self._text = ""
        self.cursor = 0
        self.sel_start = 0
        self.sel_end = 0

    def get_selected_text(self) -> str:
        lo = min(self.sel_start, self.sel_end)
        hi = max(self.sel_start, self.sel_end)
        if lo != hi and lo < len(self._text):
            return self._text[lo:hi]
        return ""

    def insert_text(self, new_chars: str) -> bool:
        if not new_chars:
            return False
        # 选区会被本次输入整体替换，先扣除其长度再判断上限，
        # 否则「全选后直接输入」会被 max_length 误截断（实际长度并未超限）。
        sel_len = abs(self.sel_end - self.sel_start)
        effective_len = len(self._text) - sel_len
        if self.max_length and effective_len + len(new_chars) > self.max_length:
            new_chars = new_chars[:max(0, self.max_length - effective_len)]
            if not new_chars:
                return False

        lo = min(self.sel_start, self.sel_end)
        hi = max(self.sel_start, self.sel_end)
        if lo != hi:
            self._text = self._text[:lo] + new_chars + self._text[hi:]
            self.cursor = lo + len(new_chars)
        else:
            self._text = self._text[:self.cursor] + new_chars + self._text[self.cursor:]
            self.cursor += len(new_chars)
        self.sel_start = self.sel_end = self.cursor
        return True

    def delete_selection_or_char(self, is_backspace: bool = True) -> bool:
        lo = min(self.sel_start, self.sel_end)
        hi = max(self.sel_start, self.sel_end)
        if lo != hi:
            self._text = self._text[:lo] + self._text[hi:]
            self.cursor = lo
            self.sel_start = self.sel_end = lo
            return True
        else:
            if is_backspace:
                if self.cursor > 0:
                    self._text = self._text[:self.cursor - 1] + self._text[self.cursor:]
                    self.cursor -= 1
                    self.sel_start = self.sel_end = self.cursor
                    return True
            else:
                if self.cursor < len(self._text):
                    self._text = self._text[:self.cursor] + self._text[self.cursor + 1:]
                    self.sel_start = self.sel_end = self.cursor
                    return True
        return False

    def _get_char_idx_at_x(self, mouse_x: int, mouse_y: Optional[int] = None) -> int:
        if not self.font:
            return 0
        disp = self.get_display_text()
        # 多行模式：先按 y 定行，再按 x 定列
        if self.max_lines > 1 and mouse_y is not None:
            if not disp:
                return 0
            wrap_w = self.rect.width - 20
            all_lines, cur = [], ''
            for ch in disp:
                if self.font.size(cur + ch)[0] > wrap_w and cur:
                    all_lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            if cur:
                all_lines.append(cur)
            offsets, off = [], 0
            for ln in all_lines:
                offsets.append(off)
                off += len(ln)
            line_h = self.font.get_height() + 2
            total_h = line_h * len(all_lines)
            y0 = self.rect.y + max(4, (self.rect.height - total_h) // 2)
            rel_y = mouse_y - y0
            if rel_y < 0:
                return 0
            li = min(len(all_lines) - 1, int(rel_y // line_h))
            ln = all_lines[li]
            rel_x = mouse_x - (self.rect.x + 10)
            if rel_x <= 0:
                return offsets[li]
            for i in range(1, len(ln) + 1):
                w = self.font.size(ln[:i])[0]
                if w >= rel_x:
                    pw = self.font.size(ln[:i - 1])[0]
                    return offsets[li] + (i - 1 if (rel_x - pw < w - rel_x) else i)
            return offsets[li] + len(ln)
        # 单行模式（原逻辑）
        tw = self.font.size(disp)[0]
        clip_w = self.rect.width - 20
        start_x = (self.rect.right - 10 - tw) if tw > clip_w else (self.rect.x + 10)
        rel_x = mouse_x - start_x
        if rel_x <= 0:
            return 0
        for i in range(1, len(disp) + 1):
            w = self.font.size(disp[:i])[0]
            if w >= rel_x:
                pw = self.font.size(disp[:i - 1])[0]
                return i - 1 if (rel_x - pw < w - rel_x) else i
        return len(disp)

    def tick_continuous_delete(self, now_time: float) -> bool:
        """处理按住 Backspace 或 Delete 键时的连续平滑连删"""
        changed = False
        if self.backspace_held:
            if now_time - self.backspace_start_time > 0.30:
                if now_time - self.backspace_last_fire > 0.035:
                    changed = self.delete_selection_or_char(is_backspace=True)
                    self.backspace_last_fire = now_time
        if self.delete_held:
            if now_time - self.delete_start_time > 0.30:
                if now_time - self.delete_last_fire > 0.035:
                    changed = self.delete_selection_or_char(is_backspace=False) or changed
                    self.delete_last_fire = now_time
        return changed

    def handle_event(
        self,
        event: pygame.event.Event,
        mx: Optional[int] = None,
        my: Optional[int] = None,
        clipboard_getter: Optional[Callable[[], str]] = None,
        clipboard_setter: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        处理组件事件
        返回: 是否产生了文本变化 (bool)
        """
        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        changed = False
        now_time = time.time()

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(mx, my):
                self.is_active = True
                # 双击全选判定
                if now_time - self.last_click_time < 0.30:
                    self.select_all()
                    self.last_click_time = 0.0
                else:
                    idx = self._get_char_idx_at_x(mx, my)
                    self.cursor = idx
                    self.sel_start = self.sel_end = idx
                    self.is_dragging = True
                    self.last_click_time = now_time
            else:
                self.is_active = False
                self.is_dragging = False

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            self.is_dragging = False

        elif event.type == MOUSEMOTION and self.is_dragging and self.is_active:
            idx = self._get_char_idx_at_x(mx, my)
            self.cursor = idx
            self.sel_end = idx

        elif event.type == KEYUP and self.is_active:
            if event.key == K_BACKSPACE:
                self.backspace_held = False
            elif event.key == K_DELETE:
                self.delete_held = False

        elif event.type == KEYDOWN and self.is_active:
            mods = pygame.key.get_mods()
            ctrl = bool(mods & KMOD_CTRL)
            shift = bool(mods & KMOD_SHIFT)

            if ctrl and event.key == K_a:
                self.select_all()

            elif ctrl and event.key == K_c:
                sel = self.get_selected_text()
                if not sel and self._text:
                    sel = self._text
                if sel and clipboard_setter:
                    clipboard_setter(sel)

            elif ctrl and event.key == K_x:
                sel = self.get_selected_text()
                if sel:
                    if clipboard_setter:
                        clipboard_setter(sel)
                    self.delete_selection_or_char()
                    changed = True

            elif ctrl and event.key == K_v:
                pasted = clipboard_getter() if clipboard_getter else ""
                if pasted:
                    changed = self.insert_text(pasted)

            elif event.key == K_BACKSPACE:
                self.backspace_held = True
                self.backspace_start_time = now_time
                self.backspace_last_fire = now_time
                changed = self.delete_selection_or_char(is_backspace=True)

            elif event.key == K_DELETE:
                self.delete_held = True
                self.delete_start_time = now_time
                self.delete_last_fire = now_time
                changed = self.delete_selection_or_char(is_backspace=False)

            elif event.key == K_LEFT:
                if shift:
                    self.cursor = max(0, self.cursor - 1)
                    self.sel_end = self.cursor
                else:
                    if self.sel_start != self.sel_end:
                        self.cursor = min(self.sel_start, self.sel_end)
                        self.sel_start = self.sel_end = self.cursor
                    else:
                        self.cursor = max(0, self.cursor - 1)
                        self.sel_start = self.sel_end = self.cursor

            elif event.key == K_RIGHT:
                txt_len = len(self._text)
                if shift:
                    self.cursor = min(txt_len, self.cursor + 1)
                    self.sel_end = self.cursor
                else:
                    if self.sel_start != self.sel_end:
                        self.cursor = max(self.sel_start, self.sel_end)
                        self.sel_start = self.sel_end = self.cursor
                    else:
                        self.cursor = min(txt_len, self.cursor + 1)
                        self.sel_start = self.sel_end = self.cursor

            elif event.key == K_HOME:
                self.cursor = 0
                if shift:
                    self.sel_end = 0
                else:
                    self.sel_start = self.sel_end = 0

            elif event.key == K_END:
                self.cursor = len(self._text)
                if shift:
                    self.sel_end = len(self._text)
                else:
                    self.sel_start = self.sel_end = len(self._text)

        elif event.type == TEXTINPUT and self.is_active:
            if event.text:
                changed = self.insert_text(event.text)

        return changed

    def render(self, surface: pygame.Surface, cursor_visible: bool = True) -> None:
        """自绘单行输入框 (带选区背景高亮与裁剪)"""
        border_col = self.active_border_color if self.is_active else self.border_color
        if self.bg_color is not None:
            pygame.draw.rect(surface, self.bg_color, self.rect, border_radius=self.border_radius)
        if border_col is not None:
            pygame.draw.rect(surface, border_col, self.rect, width=1, border_radius=self.border_radius)

        if not self.font:
            return

        clip_rect = pygame.Rect(self.rect.x + 10, self.rect.y + 4, self.rect.width - 20, self.rect.height - 8)
        orig_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        disp = self.get_display_text()
        if not disp and self.placeholder and not self.is_active:
            ph_surf = self.font.render(self.placeholder, True, self.placeholder_color)
            ty = self.rect.y + (self.rect.height - ph_surf.get_height()) // 2
            surface.blit(ph_surf, (self.rect.x + 10, ty))
            surface.set_clip(orig_clip)
            return

        if self.max_lines > 1:
            wrap_w = clip_rect.width
            all_lines, cur = [], ''
            for ch in disp:
                if self.font.size(cur + ch)[0] > wrap_w and cur:
                    all_lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            if cur:
                all_lines.append(cur)
            if not all_lines:
                # 空文本也要保证有一行，否则光标行的推导会落在 -1，光标画不出来
                all_lines = ['']
            offsets, off = [], 0
            for ln in all_lines:
                offsets.append(off)
                off += len(ln)
            safe_cur = max(0, min(self.cursor, len(disp)))
            cur_line = len(all_lines) - 1
            for i, o in enumerate(offsets):
                if o <= safe_cur <= o + len(all_lines[i]):
                    cur_line = i
                    break
            show_start = max(0, min(cur_line, len(all_lines) - self.max_lines))
            disp_lines = all_lines[show_start:show_start + self.max_lines]
            disp_offsets = offsets[show_start:show_start + self.max_lines]
            line_h = self.font.get_height() + 2
            total_h = line_h * len(disp_lines)
            y0 = self.rect.y + 4
            start_x = self.rect.x + 10
            lo = max(0, min(min(self.sel_start, self.sel_end), len(disp)))
            hi = max(0, min(max(self.sel_start, self.sel_end), len(disp)))
            if self.is_active and lo != hi:
                for li, ln in enumerate(disp_lines):
                    ofs = disp_offsets[li]
                    seg_lo = max(lo, ofs)
                    seg_hi = min(hi, ofs + len(ln))
                    if seg_lo < seg_hi:
                        x_lo = start_x + self.font.size(ln[:seg_lo - ofs])[0]
                        x_hi = start_x + self.font.size(ln[:seg_hi - ofs])[0]
                        pygame.draw.rect(surface, self.sel_color, pygame.Rect(x_lo, y0 + li * line_h, max(2, x_hi - x_lo), line_h), border_radius=2)
            for li, ln in enumerate(disp_lines):
                ts = self.font.render(ln, True, self.text_color)
                surface.blit(ts, (start_x, y0 + li * line_h))
            if self.is_active and cursor_visible:
                li_local = cur_line - show_start
                if 0 <= li_local < len(disp_lines):
                    ln = disp_lines[li_local]
                    ofs = disp_offsets[li_local]
                    ci = safe_cur - ofs
                    cx = start_x + self.font.size(ln[:ci])[0]
                    pygame.draw.line(surface, self.cursor_color, (cx, y0 + li_local * line_h + 2), (cx, y0 + li_local * line_h + line_h - 2), 2)
            surface.set_clip(orig_clip)
            return
        txt_surf = self.font.render(disp, True, self.text_color)
        ty = self.rect.y + (self.rect.height - txt_surf.get_height()) // 2

        if txt_surf.get_width() > clip_rect.width:
            start_x = clip_rect.right - txt_surf.get_width()
        else:
            start_x = self.rect.x + 10

        # 绘制选区高亮
        lo = min(self.sel_start, self.sel_end)
        hi = max(self.sel_start, self.sel_end)
        if self.is_active and lo != hi:
            lo = max(0, min(lo, len(disp)))
            hi = max(0, min(hi, len(disp)))
            x_lo = start_x + self.font.size(disp[:lo])[0]
            x_hi = start_x + self.font.size(disp[:hi])[0]
            sel_rect = pygame.Rect(x_lo, self.rect.y + 4, max(2, x_hi - x_lo), self.rect.height - 8)
            pygame.draw.rect(surface, self.sel_color, sel_rect, border_radius=2)

        # 绘制正文
        surface.blit(txt_surf, (start_x, ty))

        # 绘制呼吸光标
        if self.is_active and cursor_visible:
            safe_cur = max(0, min(self.cursor, len(disp)))
            cx = start_x + self.font.size(disp[:safe_cur])[0]
            pygame.draw.line(surface, self.cursor_color, (cx, ty + 2), (cx, ty + txt_surf.get_height() - 2), 2)

        surface.set_clip(orig_clip)

    # 规范契约别名
    draw = render


class SliderBar:
    """自绘平滑滑块条组件"""

    def __init__(
        self,
        rect: pygame.Rect,
        value: float = 0.5,
        min_val: float = 0.0,
        max_val: float = 1.0,
        step: Optional[float] = None,
        track_color: Tuple[int, int, int] = (220, 213, 200),
        fill_color: Tuple[int, int, int] = (215, 120, 10),
        thumb_color: Tuple[int, int, int] = (255, 255, 255),
        thumb_border_color: Tuple[int, int, int] = (215, 120, 10),
        border_radius: int = 6
    ) -> None:
        self.rect: pygame.Rect = pygame.Rect(rect)
        self.min_val: float = min_val
        self.max_val: float = max_val
        self.step: Optional[float] = step
        self._value: float = max(min_val, min(max_val, value))
        self.is_dragging: bool = False

        self.track_color: Tuple[int, int, int] = track_color
        self.fill_color: Tuple[int, int, int] = fill_color
        self.thumb_color: Tuple[int, int, int] = thumb_color
        self.thumb_border_color: Tuple[int, int, int] = thumb_border_color
        self.border_radius: int = border_radius

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val: float) -> None:
        val = max(self.min_val, min(self.max_val, val))
        if self.step:
            val = round(val / self.step) * self.step
        self._value = val

    def _update_from_mouse(self, mx: int) -> bool:
        ratio = (mx - self.rect.x) / max(1, self.rect.width)
        ratio = max(0.0, min(1.0, ratio))
        new_val = self.min_val + ratio * (self.max_val - self.min_val)
        if self.step:
            new_val = round(new_val / self.step) * self.step
        if abs(new_val - self._value) > 1e-4:
            self._value = new_val
            return True
        return False

    def handle_event(self, event: pygame.event.Event, mx: Optional[int] = None, my: Optional[int] = None) -> bool:
        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        hit_box = pygame.Rect(self.rect.x - 6, self.rect.y - 6, self.rect.width + 12, self.rect.height + 12)

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if hit_box.collidepoint(mx, my):
                self.is_dragging = True
                return self._update_from_mouse(mx)

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            self.is_dragging = False

        elif event.type == MOUSEMOTION and self.is_dragging:
            return self._update_from_mouse(mx)

        return False

    def render(self, surface: pygame.Surface) -> None:
        # 底轨
        pygame.draw.rect(surface, self.track_color, self.rect, border_radius=self.border_radius)
        # 激活填充轨
        val_ratio = (self._value - self.min_val) / max(1e-5, self.max_val - self.min_val)
        fill_w = max(0, min(self.rect.width, int(self.rect.width * val_ratio)))
        if fill_w > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_w, self.rect.height)
            pygame.draw.rect(surface, self.fill_color, fill_rect, border_radius=self.border_radius)

        # 游标圆点
        thumb_x = self.rect.x + fill_w
        thumb_y = self.rect.centery
        pygame.draw.circle(surface, self.thumb_color, (thumb_x, thumb_y), 7)
        pygame.draw.circle(surface, self.thumb_border_color, (thumb_x, thumb_y), 7, width=2)

    def step_up(self, delta: Optional[float] = None) -> float:
        """向上步进微调滑块数值"""
        d = delta if delta is not None else (self.step if self.step is not None else 0.05)
        self.value = min(self.max_val, round(self._value + d, 2))
        return self.value

    def step_down(self, delta: Optional[float] = None) -> float:
        """向下步进微调滑块数值"""
        d = delta if delta is not None else (self.step if self.step is not None else 0.05)
        self.value = max(self.min_val, round(self._value - d, 2))
        return self.value

    # 规范契约别名
    draw = render


class DropdownMenu:
    """自绘浮层下拉菜单组件"""

    def __init__(
        self,
        trigger_rect: pygame.Rect,
        items: Optional[List[str]] = None,
        selected_value: str = "",
        max_visible: int = 9,
        item_height: int = 28,
        menu_width: int = 280,
        bg_color: Tuple[int, int, int] = (250, 248, 244),
        border_color: Tuple[int, int, int] = (220, 213, 200),
        hover_color: Tuple[int, int, int] = (255, 235, 200),
        text_color: Tuple[int, int, int] = (31, 35, 43),
        active_text_color: Tuple[int, int, int] = (215, 120, 10)
    ) -> None:
        self.trigger_rect: pygame.Rect = pygame.Rect(trigger_rect)
        self.items: List[str] = list(items or [])
        self.selected_value: str = selected_value
        self.max_visible: int = max_visible
        self.item_height: int = item_height
        self.menu_width: int = menu_width
        self.is_open: bool = False

        self.bg_color: Tuple[int, int, int] = bg_color
        self.border_color: Tuple[int, int, int] = border_color
        self.hover_color: Tuple[int, int, int] = hover_color
        self.text_color: Tuple[int, int, int] = text_color
        self.active_text_color: Tuple[int, int, int] = active_text_color

    def get_menu_rect(self) -> pygame.Rect:
        visible_count = min(len(self.items), self.max_visible)
        h = max(32, visible_count * self.item_height + 6)
        x = self.trigger_rect.right - self.menu_width
        y = self.trigger_rect.bottom + 4
        return pygame.Rect(x, y, self.menu_width, h)

    def handle_event(self, event: pygame.event.Event, mx: Optional[int] = None, my: Optional[int] = None) -> Tuple[bool, str]:
        """
        处理下拉组件交互
        返回: (是否选中新项, 选中的文本值)
        """
        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.trigger_rect.collidepoint(mx, my):
                self.is_open = not self.is_open
                return False, ""

            if self.is_open:
                m_rect = self.get_menu_rect()
                if m_rect.collidepoint(mx, my):
                    visible_items = self.items[:self.max_visible]
                    rel_y = my - (m_rect.y + 3)
                    idx = rel_y // self.item_height
                    if 0 <= idx < len(visible_items):
                        self.selected_value = visible_items[idx]
                        self.is_open = False
                        return True, self.selected_value
                else:
                    self.is_open = False

        return False, ""

    def render_popup(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """在顶层渲染下拉弹出框"""
        if not self.is_open or not self.items:
            return

        m_rect = self.get_menu_rect()
        mx, my = pygame.mouse.get_pos()

        # 阴影与和纸底框
        shadow_rect = pygame.Rect(m_rect.x + 2, m_rect.y + 2, m_rect.width, m_rect.height)
        pygame.draw.rect(surface, (200, 195, 185), shadow_rect, border_radius=6)
        pygame.draw.rect(surface, self.bg_color, m_rect, border_radius=6)
        pygame.draw.rect(surface, self.border_color, m_rect, width=1, border_radius=6)

        visible_items = self.items[:self.max_visible]
        for idx, item in enumerate(visible_items):
            item_rect = pygame.Rect(m_rect.x + 4, m_rect.y + 3 + idx * self.item_height, m_rect.width - 8, self.item_height)
            is_hover = item_rect.collidepoint(mx, my)
            is_sel = (item == self.selected_value)

            if is_hover:
                pygame.draw.rect(surface, self.hover_color, item_rect, border_radius=4)

            color = self.active_text_color if is_sel else self.text_color
            t_surf = font.render(item, True, color)
            ty = item_rect.y + (self.item_height - t_surf.get_height()) // 2
            surface.blit(t_surf, (item_rect.x + 10, ty))

    # 规范契约别名
    render = render_popup
    draw = render_popup


class TabGroup:
    """自绘选项卡组组件"""

    def __init__(self, tabs: List[Tuple[str, str, pygame.Rect]], active_tab: str = "") -> None:
        """tabs 格式: [(tab_id, label, rect), ...]"""
        self.tabs: List[Tuple[str, str, pygame.Rect]] = list(tabs)
        self.active_tab: str = active_tab if active_tab else (tabs[0][0] if tabs else "")

    def handle_event(self, event: pygame.event.Event, mx: Optional[int] = None, my: Optional[int] = None) -> Optional[str]:
        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            for tab_id, _, rect in self.tabs:
                if rect.collidepoint(mx, my):
                    if self.active_tab != tab_id:
                        self.active_tab = tab_id
                        return tab_id
        return None

    def render(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        active_bg: Tuple[int, int, int] = (215, 120, 10),
        active_fg: Tuple[int, int, int] = (255, 255, 255),
        inactive_bg: Tuple[int, int, int] = (242, 238, 231),
        inactive_fg: Tuple[int, int, int] = (140, 147, 164),
        border_color: Tuple[int, int, int] = (220, 213, 200)
    ) -> None:
        for tab_id, label, rect in self.tabs:
            is_act = (tab_id == self.active_tab)
            bg = active_bg if is_act else inactive_bg
            fg = active_fg if is_act else inactive_fg
            pygame.draw.rect(surface, bg, rect, border_radius=6)
            if not is_act:
                pygame.draw.rect(surface, border_color, rect, width=1, border_radius=6)
            t_surf = font.render(label, True, fg)
            tx = rect.centerx - t_surf.get_width() // 2
            ty = rect.centery - t_surf.get_height() // 2
            surface.blit(t_surf, (tx, ty))

    # 规范契约别名
    draw = render


class DialogueScrollBar:
    """
    自绘和风微型垂直滚动条组件 (Dialogue Vertical ScrollBar)
    专为剧情对话框长文本设计：
    1. 仅在 total_lines > visible_lines 时显示，短文本保持优雅静默；
    2. 支持鼠标滚轮滚动（光标悬停在对话框区域即可直接滚屏）；
    3. 支持鼠标左键拖拽滑块以及点击轨道上下翻页；
    4. 支持打字机自动跟手追光（auto_pin_bottom）：打出第4、5行时视口自动贴底，用户向上滚轮查阅时暂停追光，滚回最底部后自动恢复追光；
    5. 和风半透明轨道与琥珀橙滑块，悬停微扩，完全契合 GAL 游戏界面。
    """

    def __init__(
        self,
        rect: pygame.Rect,
        visible_lines: int = 3,
        track_color: Tuple[int, int, int, int] = (20, 20, 25, 90),
        thumb_color: Tuple[int, int, int, int] = (225, 225, 230, 130),
        thumb_hover_color: Tuple[int, int, int, int] = (255, 175, 50, 220),
        thumb_drag_color: Tuple[int, int, int, int] = (255, 150, 25, 240)
    ) -> None:
        self.rect: pygame.Rect = pygame.Rect(rect)
        self.visible_lines: int = visible_lines
        self.total_lines: int = 0
        self.scroll_index: int = 0  # 当前可视区域第一行的行号 (0-based)

        self.is_dragging: bool = False
        self.drag_start_y: int = 0
        self.drag_start_index: int = 0
        self.auto_pin_bottom: bool = True
        self.is_hovered: bool = False

        self.track_color = track_color
        self.thumb_color = thumb_color
        self.thumb_hover_color = thumb_hover_color
        self.thumb_drag_color = thumb_drag_color

    @property
    def max_scroll(self) -> int:
        return max(0, self.total_lines - self.visible_lines)

    @property
    def is_visible(self) -> bool:
        return self.total_lines > self.visible_lines

    def reset(self) -> None:
        """在新的一句对话开始时重置状态"""
        self.scroll_index = 0
        self.auto_pin_bottom = True
        self.is_dragging = False

    def update_lines(self, total_lines: int) -> None:
        """更新总行数，若开启了自动追光且行数增加，视口自动钉在底部"""
        self.total_lines = total_lines
        if self.auto_pin_bottom and self.total_lines > self.visible_lines:
            self.scroll_index = self.max_scroll
        else:
            self.scroll_index = max(0, min(self.scroll_index, self.max_scroll))

    def scroll_by(self, delta: int) -> bool:
        """按行数相对滚动 (delta: +1 向下滚，-1 向上滚)"""
        if not self.is_visible:
            return False

        new_idx = max(0, min(self.max_scroll, self.scroll_index + delta))
        if new_idx != self.scroll_index:
            self.scroll_index = new_idx
            # 如果滚到了最底行，自动恢复打字追光；否则暂停追光
            self.auto_pin_bottom = (self.scroll_index >= self.max_scroll)
            return True
        return False

    def _get_thumb_rect(self) -> pygame.Rect:
        """计算当前滑块在屏幕上的绝对 Rect"""
        if not self.is_visible:
            return pygame.Rect(self.rect.x, self.rect.y, self.rect.width, self.rect.height)

        track_h = self.rect.height
        # 滑块高度自适应，最小 18 像素
        thumb_h = max(18, int(track_h * (self.visible_lines / self.total_lines)))
        avail_h = track_h - thumb_h

        if self.max_scroll > 0:
            thumb_y = self.rect.y + int(avail_h * (self.scroll_index / self.max_scroll))
        else:
            thumb_y = self.rect.y

        # 悬停或拖拽时宽度微增 2px
        w = self.rect.width + (2 if (self.is_hovered or self.is_dragging) else 0)
        x = self.rect.centerx - w // 2
        return pygame.Rect(x, thumb_y, w, thumb_h)

    def handle_event(
        self,
        event: pygame.event.Event,
        mx: Optional[int] = None,
        my: Optional[int] = None,
        in_dialogue_area: bool = False
    ) -> bool:
        """
        处理鼠标事件
        :param event: pygame 事件
        :param mx: 鼠标 X
        :param my: 鼠标 Y
        :param in_dialogue_area: 鼠标是否落在整个对话框区域内（落在对话框即可响应滚轮）
        :return: 是否消耗/响应了事件
        """
        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        thumb_rect = self._get_thumb_rect()
        hit_track = self.rect.collidepoint(mx, my) or thumb_rect.collidepoint(mx, my)
        self.is_hovered = self.is_visible and hit_track

        # 1. 现代 Pygame MOUSEWHEEL 滚轮事件
        if event.type == pygame.MOUSEWHEEL:
            if in_dialogue_area or hit_track:
                if self.is_visible:
                    if event.y > 0:
                        self.scroll_by(-1)
                    elif event.y < 0:
                        self.scroll_by(1)
                return True  # 滚轮落在对话框或滚动条上，必须无条件消费，绝不泄露穿透！

        # 2. 传统 Pygame 滚轮 (button 4 向上，button 5 向下)
        if event.type == MOUSEBUTTONDOWN:
            if (in_dialogue_area or hit_track) and event.button in (4, 5):
                if self.is_visible:
                    if event.button == 4:
                        self.scroll_by(-1)
                    elif event.button == 5:
                        self.scroll_by(1)
                return True  # 无论是否已触碰滚动边界，滚轮事件必须无条件消费，绝不让点击误判！

            # 鼠标左键点击滚动条区域
            if event.button == 1 and self.is_visible and hit_track:
                if thumb_rect.collidepoint(mx, my):
                    self.is_dragging = True
                    self.drag_start_y = my
                    self.drag_start_index = self.scroll_index
                    return True
                else:
                    # 点击了滑块上方或下方的轨道：快速翻页
                    if my < thumb_rect.y:
                        self.scroll_by(-2)
                    elif my > thumb_rect.bottom:
                        self.scroll_by(2)
                    return True

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self.is_dragging = False
                return True

        elif event.type == MOUSEMOTION:
            if self.is_dragging and self.is_visible:
                track_h = self.rect.height
                thumb_h = max(18, int(track_h * (self.visible_lines / self.total_lines)))
                avail_h = track_h - thumb_h
                if avail_h > 0 and self.max_scroll > 0:
                    delta_y = my - self.drag_start_y
                    delta_idx = int(round((delta_y / avail_h) * self.max_scroll))
                    new_idx = max(0, min(self.max_scroll, self.drag_start_index + delta_idx))
                    if new_idx != self.scroll_index:
                        self.scroll_index = new_idx
                        self.auto_pin_bottom = (self.scroll_index >= self.max_scroll)
                        return True

        return False

    def render(self, surface: pygame.Surface) -> None:
        """自绘半透明和风轨道与圆角滑块"""
        if not self.is_visible:
            return

        # 1. 绘制半透明轨道
        track_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        track_surf.fill(self.track_color)
        surface.blit(track_surf, (self.rect.x, self.rect.y))

        # 2. 绘制滑块
        thumb_rect = self._get_thumb_rect()
        if self.is_dragging:
            cur_color = self.thumb_drag_color
        elif self.is_hovered:
            cur_color = self.thumb_hover_color
        else:
            cur_color = self.thumb_color

        thumb_surf = pygame.Surface((thumb_rect.width, thumb_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            thumb_surf,
            cur_color,
            pygame.Rect(0, 0, thumb_rect.width, thumb_rect.height),
            border_radius=3
        )
        surface.blit(thumb_surf, (thumb_rect.x, thumb_rect.y))

    # 规范别名
    draw = render


class ModalShell:
    """
    和风模态弹窗的外壳：暗场遮罩 + 投影 + 和纸卡片 + 按钮对 + 模态拦截。

    ConfirmDialog 与 InputDialog 以前各自把这套外壳画了一遍（约 28–30 行逐字重复）。
    现在下沉到这里：外壳只负责「框」和「按钮」，弹窗内容区由调用方各自填。

    外壳承担（凡跟这两个弹窗长得一样的部分）：
    - render_frame(surface)：暗场 + 投影 + 卡片 + 标题 + 取消/确认按钮
    - rect_cancel / rect_confirm：按钮热区几何
    - is_open / open / close：开关状态与 action_context
    - modal_block(event)：是否该把事件拦在弹窗内（滚轮、鼠标）

    它不关心内容区（ConfirmDialog 的两行说明、InputDialog 的输入框）长什么样。
    """

    def __init__(
        self,
        title: str = "",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        width: int = 460,
        height: int = 210,
        screen_size: Tuple[int, int] = (1280, 720)
    ) -> None:
        self.title: str = title
        self.confirm_text: str = confirm_text
        self.cancel_text: str = cancel_text
        self.width: int = width
        self.height: int = height
        self.screen_size: Tuple[int, int] = screen_size

        self._is_open: bool = False
        self.action_context: Any = None

        self._update_geometry()

    def _update_geometry(self) -> None:
        sw, sh = self.screen_size
        self.x = (sw - self.width) // 2
        self.y = (sh - self.height) // 2
        btn_w, btn_h = 140, 36
        btn_y = self.y + self.height - btn_h - 22
        self.rect_cancel = pygame.Rect(self.x + 55, btn_y, btn_w, btn_h)
        self.rect_confirm = pygame.Rect(self.x + self.width - btn_w - 55, btn_y, btn_w, btn_h)

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open(self) -> None:
        self._is_open = True

    def close(self) -> None:
        self._is_open = False
        self.action_context = None

    def modal_block(self, event: pygame.event.Event) -> bool:
        """打开时滚轮与鼠标事件是否要拦在弹窗内（不往下穿透）"""
        return event.type in (pygame.MOUSEWHEEL, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)

    def render_frame(
        self,
        surface: pygame.Surface,
        mx: int,
        my: int,
        title_font: Optional[pygame.font.Font] = None,
        btn_font: Optional[pygame.font.Font] = None
    ) -> None:
        """画遮罩、投影、卡片、标题、按钮对（不含内容区）"""
        sw, sh = self.screen_size

        # 1. 暗场遮罩
        dark_mask = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dark_mask.fill((0, 0, 0, 195))
        surface.blit(dark_mask, (0, 0))

        # 2. 投影
        dia_shadow = pygame.Surface((self.width + 24, self.height + 24), pygame.SRCALPHA)
        pygame.draw.rect(dia_shadow, (0, 0, 0, 120), (12, 12, self.width, self.height), border_radius=12)
        surface.blit(dia_shadow, (self.x - 12, self.y - 12))

        # 3. 和纸主卡片
        dia_card = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(dia_card, (250, 248, 245), (0, 0, self.width, self.height), border_radius=12)
        pygame.draw.rect(dia_card, (215, 120, 10, 60), (0, 0, self.width, self.height), width=1, border_radius=12)
        surface.blit(dia_card, (self.x, self.y))

        # 4. 标题
        t_font = title_font or pygame.font.Font(None, 24)
        dt_s = t_font.render(self.title, True, (31, 35, 43))
        surface.blit(dt_s, (self.x + (self.width - dt_s.get_width()) // 2, self.y + 26))

        b_font = btn_font or pygame.font.Font(None, 18)

        # 5. 取消按钮
        is_can_hover = self.rect_cancel.collidepoint(mx, my)
        pygame.draw.rect(surface, (226, 221, 211) if is_can_hover else (237, 232, 223), self.rect_cancel, border_radius=6)
        pygame.draw.rect(surface, (190, 180, 165) if is_can_hover else (208, 200, 184), self.rect_cancel, width=1, border_radius=6)
        bc_txt = b_font.render(self.cancel_text, True, (31, 35, 43) if is_can_hover else (45, 50, 62))
        surface.blit(bc_txt, (self.rect_cancel.x + (self.rect_cancel.width - bc_txt.get_width()) // 2, self.rect_cancel.y + (self.rect_cancel.height - bc_txt.get_height()) // 2))

        # 6. 确认按钮
        is_conf_hover = self.rect_confirm.collidepoint(mx, my)
        pygame.draw.rect(surface, (255, 155, 0) if is_conf_hover else (215, 120, 10), self.rect_confirm, border_radius=6)
        pygame.draw.rect(surface, (255, 200, 100) if is_conf_hover else (255, 155, 0), self.rect_confirm, width=1, border_radius=6)
        bcf_txt = b_font.render(self.confirm_text, True, (255, 255, 255))
        surface.blit(bcf_txt, (self.rect_confirm.x + (self.rect_confirm.width - bcf_txt.get_width()) // 2, self.rect_confirm.y + (self.rect_confirm.height - bcf_txt.get_height()) // 2))


class ConfirmDialog:
    """
    和风通用模态二次确认弹窗控件
    - 模态遮罩 (半透明背景) + 和纸风圆角投影卡片
    - 支持自定义标题、主说明、次说明、确认按键与取消按键文案
    - 模态事件严格拦截：打开时下层任何控件与事件不可穿透
    - 键盘交互支持：Enter 确认，Esc 取消
    - 返回 'confirm' | 'cancel' | 'block' | None
    """

    def __init__(
        self,
        title: str = "确认操作",
        sub1: str = "请确认是否继续此操作？",
        sub2: str = "",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        width: int = 460,
        height: int = 210,
        screen_size: Tuple[int, int] = (1280, 720),
        title_font: Optional[pygame.font.Font] = None,
        sub_font: Optional[pygame.font.Font] = None,
        sub2_font: Optional[pygame.font.Font] = None,
        btn_font: Optional[pygame.font.Font] = None
    ) -> None:
        self.sub1: str = sub1
        self.sub2: str = sub2
        self.screen_size: Tuple[int, int] = screen_size

        self.title_font = title_font
        self.sub_font = sub_font
        self.sub2_font = sub2_font
        self.btn_font = btn_font

        # 外壳：遮罩/投影/卡片/标题/按钮对/模态拦截，全部下沉
        self.shell: ModalShell = ModalShell(
            title=title,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
            width=width,
            height=height,
            screen_size=screen_size
        )

    # ---- 转发给外壳，保持原有调用方无感 ----
    @property
    def is_open(self) -> bool:
        return self.shell.is_open

    @property
    def action_context(self) -> Any:
        return self.shell.action_context

    @action_context.setter
    def action_context(self, val: Any) -> None:
        self.shell.action_context = val

    @property
    def rect_cancel(self) -> pygame.Rect:
        return self.shell.rect_cancel

    @property
    def rect_confirm(self) -> pygame.Rect:
        return self.shell.rect_confirm

    def open(
        self,
        title: Optional[str] = None,
        sub1: Optional[str] = None,
        sub2: Optional[str] = None,
        confirm_text: Optional[str] = None,
        cancel_text: Optional[str] = None,
        context: Any = None
    ) -> None:
        if title is not None:
            self.shell.title = title
        if sub1 is not None:
            self.sub1 = sub1
        if sub2 is not None:
            self.sub2 = sub2
        if confirm_text is not None:
            self.shell.confirm_text = confirm_text
        if cancel_text is not None:
            self.shell.cancel_text = cancel_text
        self.shell.action_context = context
        self.shell.open()

    def close(self) -> None:
        self.shell.close()

    def handle_event(
        self,
        event: pygame.event.Event,
        mx: Optional[int] = None,
        my: Optional[int] = None
    ) -> Optional[str]:
        if not self.shell.is_open:
            return None

        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        # 键盘快捷键
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.close()
                return "confirm"
            elif event.key == pygame.K_ESCAPE:
                self.close()
                return "cancel"

        # 鼠标点击
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.shell.rect_confirm.collidepoint(mx, my):
                self.close()
                return "confirm"
            elif self.shell.rect_cancel.collidepoint(mx, my):
                self.close()
                return "cancel"
            return "block"

        # 滚轮与点击全面阻断，杜绝穿透
        if self.shell.modal_block(event):
            return "block"

        return None

    def render(self, surface: pygame.Surface, mx: Optional[int] = None, my: Optional[int] = None) -> None:
        if not self.shell.is_open:
            return

        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        # 外壳：遮罩 + 投影 + 卡片 + 标题 + 按钮
        self.shell.render_frame(surface, mx, my, self.title_font, self.btn_font)

        # 内容区：两行说明
        s_font = self.sub_font or pygame.font.Font(None, 18)
        s2_font = self.sub2_font or pygame.font.Font(None, 16)

        if self.sub1:
            ds1 = s_font.render(self.sub1, True, (92, 98, 112))
            surface.blit(ds1, (self.shell.x + (self.shell.width - ds1.get_width()) // 2, self.shell.y + 68))

        if self.sub2:
            ds2 = s2_font.render(self.sub2, True, (118, 124, 138))
            surface.blit(ds2, (self.shell.x + (self.shell.width - ds2.get_width()) // 2, self.shell.y + 94))

    draw = render


class InputDialog:
    """
    和风通用模态文本输入弹窗控件

    - 复用 ConfirmDialog 的和纸卡片、投影、暗场遮罩与模态拦截几何
    - 内嵌一个 TextInputBox 单行文本域，支持中文输入法（TEXTINPUT）、选区、剪贴板
    - 键盘交互：Enter 确认，Esc 取消，Tab 切换文本域焦点
    - 空值校验：规整后为空时拒绝确认，并在提示行红字说明
    - 返回 'confirm' | 'cancel' | 'block' | None
    """

    def __init__(
        self,
        title: str = "重命名",
        label: str = "",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        placeholder: str = "",
        max_length: Optional[int] = 24,
        width: int = 520,
        height: int = 250,
        screen_size: Tuple[int, int] = (1280, 720),
        title_font: Optional[pygame.font.Font] = None,
        label_font: Optional[pygame.font.Font] = None,
        hint_font: Optional[pygame.font.Font] = None,
        btn_font: Optional[pygame.font.Font] = None,
        input_font: Optional[pygame.font.Font] = None
    ) -> None:
        self.label: str = label
        self.screen_size: Tuple[int, int] = screen_size
        self.max_length: Optional[int] = max_length
        self.error_text: str = ""

        self.title_font = title_font
        self.label_font = label_font
        self.hint_font = hint_font
        self.btn_font = btn_font
        # 文本域必须持有可用字体，否则 TextInputBox.render 会提前返回导致完全看不到文字
        self.input_font = input_font or pygame.font.Font(None, 20)

        self._blink: BlinkCursor = BlinkCursor(0.5)

        # 外壳：遮罩/投影/卡片/标题/按钮对/模态拦截，全部下沉
        self.shell: ModalShell = ModalShell(
            title=title,
            confirm_text=confirm_text,
            cancel_text=cancel_text,
            width=width,
            height=height,
            screen_size=screen_size
        )

        self._update_geometry()
        self.box: TextInputBox = TextInputBox(
            rect=self.rect_input,
            text="",
            font=self.input_font,
            placeholder=placeholder,
            max_length=max_length,
            border_radius=6,
            bg_color=(255, 253, 250),
            border_color=(214, 206, 193),
            active_border_color=(255, 155, 0),
            text_color=(31, 35, 43),
            placeholder_color=(163, 163, 163),
            sel_color=(255, 200, 120),
            cursor_color=(215, 120, 10),
            max_lines=1
        )

    def _update_geometry(self) -> None:
        self.x = self.shell.x
        self.y = self.shell.y
        self.width = self.shell.width
        self.height = self.shell.height

        pad = 40
        self.rect_input = pygame.Rect(self.x + pad, self.y + 96, self.width - pad * 2, 42)
        self.hint_y = self.y + 152

    # ---- 转发给外壳，保持原有调用方无感 ----
    @property
    def is_open(self) -> bool:
        return self.shell.is_open

    @property
    def action_context(self) -> Any:
        return self.shell.action_context

    @action_context.setter
    def action_context(self, val: Any) -> None:
        self.shell.action_context = val

    @property
    def rect_cancel(self) -> pygame.Rect:
        return self.shell.rect_cancel

    @property
    def rect_confirm(self) -> pygame.Rect:
        return self.shell.rect_confirm

    @property
    def value(self) -> str:
        """规整后的当前输入值（压缩空白、去首尾）"""
        return " ".join(self.box.text.split()).strip()

    def open(
        self,
        title: Optional[str] = None,
        label: Optional[str] = None,
        default_text: str = "",
        confirm_text: Optional[str] = None,
        cancel_text: Optional[str] = None,
        context: Any = None
    ) -> None:
        if title is not None:
            self.shell.title = title
        if label is not None:
            self.label = label
        if confirm_text is not None:
            self.shell.confirm_text = confirm_text
        if cancel_text is not None:
            self.shell.cancel_text = cancel_text

        self.box.text = default_text or ""
        self.box.is_active = True
        self.box.select_all()
        self.box.is_dragging = False
        self._blink.reset()
        self.error_text = ""
        self.shell.action_context = context
        self.shell.open()

    def close(self) -> None:
        self.shell.close()
        self.box.is_active = False
        self.box.is_dragging = False
        self.error_text = ""

    def handle_event(
        self,
        event: pygame.event.Event,
        mx: Optional[int] = None,
        my: Optional[int] = None,
        clipboard_getter: Optional[Callable[[], str]] = None,
        clipboard_setter: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        if not self.shell.is_open:
            return None

        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        if event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                self.close()
                return "cancel"
            if event.key in (K_RETURN, K_KP_ENTER):
                if not self.value:
                    self.error_text = "名称不能为空"
                    return "block"
                self.close()
                return "confirm"
            if event.key == K_TAB:
                self.box.is_active = True
                self._blink.reset()
                return "block"

        if event.type == MOUSEBUTTONDOWN and event.button == 1:
            if self.shell.rect_confirm.collidepoint(mx, my):
                if not self.value:
                    self.error_text = "名称不能为空"
                    return "block"
                self.close()
                return "confirm"
            if self.shell.rect_cancel.collidepoint(mx, my):
                self.close()
                return "cancel"
            if self.rect_input.collidepoint(mx, my):
                self.error_text = ""
                self.box.handle_event(event, mx, my, clipboard_getter, clipboard_setter)
                self._blink.reset()
                return "block"
            return "block"

        # 文本域自身的键盘 / 滚轮 / 拖选交互
        changed = self.box.handle_event(event, mx, my, clipboard_getter, clipboard_setter)
        if changed:
            self.error_text = ""
            self._blink.reset()

        if self.shell.modal_block(event) or event.type == MOUSEMOTION:
            return "block"
        return None

    def render(self, surface: pygame.Surface, mx: Optional[int] = None, my: Optional[int] = None) -> None:
        if not self.shell.is_open:
            return

        if mx is None or my is None:
            mx, my = pygame.mouse.get_pos()

        # 外壳：遮罩 + 投影 + 卡片 + 标题 + 按钮
        self.shell.render_frame(surface, mx, my, self.title_font, self.btn_font)

        l_font = self.label_font or pygame.font.Font(None, 18)
        h_font = self.hint_font or pygame.font.Font(None, 16)

        # 内容区：标签行 + 字数计数
        if self.label:
            lb_s = l_font.render(self.label, True, (92, 98, 112))
            surface.blit(lb_s, (self.shell.x + 40, self.shell.y + 70))

        if self.max_length:
            cnt_s = h_font.render(f"{len(self.box.text)}/{self.max_length}", True, (150, 154, 164))
            surface.blit(cnt_s, (self.shell.x + self.shell.width - 40 - cnt_s.get_width(), self.shell.y + 72))

        # 文本域
        self.box.render(surface, self._blink.tick())

        # 提示 / 校验行
        if self.error_text:
            er_s = h_font.render(self.error_text, True, (190, 50, 50))
            surface.blit(er_s, (self.shell.x + 40, self.hint_y))
        else:
            ph_s = h_font.render("输入完成后按 Enter 确认，按 Esc 取消", True, (140, 147, 164))
            surface.blit(ph_s, (self.shell.x + 40, self.hint_y))

    draw = render

