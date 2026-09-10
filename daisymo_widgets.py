# -*- coding: utf-8 -*-
"""
DaisyMo Pygame 声明式自绘控件库 (Pygame Declarative UI Widgets Engine)
提供高度契合《三色绘恋》和纸风格的自绘控件，包含：
1. BlinkCursor: 呼吸光标节拍器
2. TextInputBox: 带选区高亮、鼠标拖拽划选、双击全选、剪贴板交互、平滑快速连删的自绘单行文本框
3. SliderBar: 平滑自绘滑块组件（支持点击、拖拽、步进调节）
4. DropdownMenu: 浮层下拉列表组件（支持气泡高亮、点击外部自动关闭、滚轮浏览）
5. TabGroup: 选项卡分组组件
"""

import time
from typing import Callable, Dict, List, Optional, Tuple, Any

import pygame
from pygame.locals import (
    K_a, K_c, K_v, K_x,
    K_BACKSPACE, K_DELETE,
    K_LEFT, K_RIGHT, K_HOME, K_END,
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
        if self.max_length and len(self._text) + len(new_chars) > self.max_length:
            new_chars = new_chars[:max(0, self.max_length - len(self._text))]
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
