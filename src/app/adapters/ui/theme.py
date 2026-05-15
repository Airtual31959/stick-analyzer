"""GUI 浅色主题与常用 CTk 组件。"""
from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

COLOR_BG = "#FFFFFF"
COLOR_PANEL = "#F9FAFB"
COLOR_LINE = "#E5E7EB"
COLOR_LINE_DARK = "#D1D5DB"
COLOR_TEXT = "#111827"
COLOR_MUTED = "#6B7280"
COLOR_ACCENT_MAGENTA = "#E81E63"
COLOR_ACCENT_MAGENTA_HOVER = "#FF3377"
COLOR_ACCENT_ORANGE = "#FF9800"
COLOR_HOVER_BG = "#F3F4F6"
COLOR_SUCCESS = "#059669"
COLOR_DANGER = "#DC2626"

FONT_FAMILY = "NSimSun"
FONT_TITLE = (FONT_FAMILY, 30, "bold")
FONT_SECTION = (FONT_FAMILY, 18, "bold")
FONT_BODY = (FONT_FAMILY, 15)
FONT_BODY_BOLD = (FONT_FAMILY, 15, "bold")
FONT_SMALL = (FONT_FAMILY, 13)
FONT_MONO = (FONT_FAMILY, 14)

SECTION_PAD_X = 10


def set_state(widget, state: str) -> None:
    """同时兼容 CTk 控件、ttk 控件和测试替身。"""
    try:
        widget.configure(state=state)
        return
    except Exception:
        pass
    try:
        widget["state"] = state
    except Exception:
        pass


def read_state(widget) -> str:
    try:
        return widget.cget("state")
    except Exception:
        try:
            return widget["state"]
        except Exception:
            return "normal"


def section(parent, title: str, subtitle: str | None = None):
    """创建线框风章节：标题 + 单线 + 透明内容容器。"""
    header = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
    header.pack(fill="x", padx=SECTION_PAD_X, pady=(18, 0))
    ctk.CTkLabel(
        header,
        text=title,
        font=FONT_SECTION,
        text_color=COLOR_TEXT,
        anchor="w",
    ).pack(side="left")
    if subtitle:
        ctk.CTkLabel(
            header,
            text=subtitle,
            font=FONT_SMALL,
            text_color=COLOR_MUTED,
            anchor="w",
        ).pack(side="left", padx=(12, 0), pady=(3, 0))
    ctk.CTkFrame(parent, height=1, fg_color=COLOR_LINE, corner_radius=0).pack(
        fill="x", padx=SECTION_PAD_X, pady=(6, 12))
    body = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
    body.pack(fill="x", padx=SECTION_PAD_X)
    return body


def body_label(parent, text: str, **kwargs):
    kwargs.setdefault("font", FONT_BODY)
    kwargs.setdefault("text_color", COLOR_TEXT)
    return ctk.CTkLabel(parent, text=text, **kwargs)


def hint_label(parent, text: str, **kwargs):
    kwargs.setdefault("font", FONT_SMALL)
    kwargs.setdefault("text_color", COLOR_MUTED)
    kwargs.setdefault("justify", "left")
    return ctk.CTkLabel(parent, text=text, **kwargs)


def line_button(parent, text: str, command=None, width: int = 120, **kwargs):
    kwargs.setdefault("height", 38)
    kwargs.setdefault("fg_color", "transparent")
    kwargs.setdefault("hover_color", COLOR_HOVER_BG)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("border_color", COLOR_LINE_DARK)
    kwargs.setdefault("text_color", COLOR_TEXT)
    kwargs.setdefault("corner_radius", 0)
    kwargs.setdefault("font", FONT_BODY_BOLD)
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        **kwargs,
    )


def solid_button(parent, text: str, command=None, width: int = 140, **kwargs):
    kwargs.setdefault("height", 40)
    kwargs.setdefault("fg_color", COLOR_ACCENT_MAGENTA)
    kwargs.setdefault("hover_color", COLOR_ACCENT_MAGENTA_HOVER)
    kwargs.setdefault("text_color", COLOR_BG)
    kwargs.setdefault("corner_radius", 0)
    kwargs.setdefault("font", FONT_BODY_BOLD)
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        **kwargs,
    )


def entry(parent, textvariable=None, width: int | None = None, **kwargs):
    if width is not None:
        kwargs["width"] = width
    kwargs.setdefault("height", 38)
    kwargs.setdefault("fg_color", COLOR_BG)
    kwargs.setdefault("border_color", COLOR_LINE_DARK)
    kwargs.setdefault("border_width", 1)
    kwargs.setdefault("text_color", COLOR_TEXT)
    kwargs.setdefault("corner_radius", 0)
    kwargs.setdefault("font", FONT_BODY)
    return ctk.CTkEntry(
        parent,
        textvariable=textvariable,
        **kwargs,
    )


def option_menu(parent, variable, values, command=None, width: int = 240, **kwargs):
    kwargs.setdefault("height", 38)
    kwargs.setdefault("fg_color", COLOR_BG)
    kwargs.setdefault("button_color", COLOR_BG)
    kwargs.setdefault("button_hover_color", COLOR_HOVER_BG)
    kwargs.setdefault("text_color", COLOR_TEXT)
    kwargs.setdefault("dropdown_fg_color", COLOR_BG)
    kwargs.setdefault("dropdown_hover_color", COLOR_HOVER_BG)
    kwargs.setdefault("dropdown_text_color", COLOR_TEXT)
    kwargs.setdefault("font", FONT_BODY)
    kwargs.setdefault("dropdown_font", FONT_BODY)
    kwargs.setdefault("corner_radius", 0)
    return ctk.CTkOptionMenu(
        parent,
        variable=variable,
        values=values,
        command=command,
        width=width,
        **kwargs,
    )


def outline_option_menu(parent, variable, values, command=None,
                        width: int = 240, **kwargs):
    """创建带 1px 线框的 CTkOptionMenu，统一下拉框外观。"""
    wrapper = ctk.CTkFrame(
        parent,
        border_width=1,
        border_color=COLOR_LINE_DARK,
        fg_color="transparent",
        corner_radius=0,
    )
    combo = option_menu(
        wrapper,
        variable=variable,
        values=values,
        command=command,
        width=width,
        **kwargs,
    )
    combo.pack(padx=1, pady=1)
    return wrapper, combo


def textbox(parent, **kwargs):
    kwargs.setdefault("font", FONT_MONO)
    kwargs.setdefault("wrap", "word")
    return ctk.CTkTextbox(
        parent,
        fg_color=COLOR_PANEL,
        border_width=1,
        border_color=COLOR_LINE,
        text_color=COLOR_TEXT,
        corner_radius=0,
        scrollbar_button_color=COLOR_LINE_DARK,
        scrollbar_button_hover_color=COLOR_ACCENT_MAGENTA,
        **kwargs,
    )


def notice(parent, text: str = ""):
    label = ctk.CTkLabel(
        parent,
        text=text,
        font=FONT_SMALL,
        text_color=COLOR_MUTED,
        anchor="w",
        justify="left",
    )
    return label


def configure_notice(label, text: str, level: str = "info") -> None:
    colors = {
        "info": COLOR_MUTED,
        "success": COLOR_SUCCESS,
        "warning": COLOR_ACCENT_ORANGE,
        "error": COLOR_DANGER,
    }
    try:
        label.configure(text=text, text_color=colors.get(level, COLOR_MUTED))
    except Exception:
        try:
            label.configure(text=text, foreground=colors.get(level, COLOR_MUTED))
        except Exception:
            pass


def show_message(kind: str, title: str, message: str, parent=None) -> bool | None:
    """统一系统提示入口，避免业务代码散落不同文案风格。"""
    if kind == "error":
        return messagebox.showerror(title, message, parent=parent)
    if kind == "warning":
        return messagebox.showwarning(title, message, parent=parent)
    if kind == "question":
        return messagebox.askyesno(title, message, parent=parent)
    return messagebox.showinfo(title, message, parent=parent)
