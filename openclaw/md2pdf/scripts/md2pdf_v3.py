#!/usr/bin/env python3
"""
md2pdf v3 — Markdown to Professional PDF (high-performance CJK edition).

Key design: Global CJK font strategy eliminates _font_wrap() bottleneck.
Body text uses Songti (CJK TTC with Latin glyphs), no per-character scanning.
wordWrap='CJK' handles line breaking natively.

Usage:
  python3 md2pdf_v3.py --input input.md -o output.pdf --title "标题" --theme chinese-red
"""

import re, os, sys, argparse, time, subprocess, tempfile, shutil
from datetime import date
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import Color, HexColor, black, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
    Table, TableStyle, NextPageTemplate, Flowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ═══════════════════════════════════════════════════════════════════════
# FONTS — macOS system fonts, CJK-first registration
# ═══════════════════════════════════════════════════════════════════════

_FONT_PATHS = {
    "Songti":      ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),
    "SongtiBold":  ("/System/Library/Fonts/Supplemental/Songti.ttc", 1),
    "STHeiti":     ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    "STHeitiLight":("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", None),
    "Menlo":       ("/System/Library/Fonts/Menlo.ttc", 0),
    "MenloBold":   ("/System/Library/Fonts/Menlo.ttc", 1),
    "Palatino":    ("/System/Library/Fonts/Palatino.ttc", 0),
    "PalatinoBold":("/System/Library/Fonts/Palatino.ttc", 2),
}

_fonts_registered = False
_STHEITI_FALLBACK = False  # STHeiti fallback — disabled, H5 infinite loop was the real hang cause

def register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    missing = []
    for name, spec in _FONT_PATHS.items():
        path, subidx = spec
        if os.path.exists(path):
            try:
                kw = {}
                if subidx is not None:
                    kw['subfontIndex'] = subidx
                pdfmetrics.registerFont(TTFont(name, path, **kw))
                font_obj = pdfmetrics.getFont(name)
                if hasattr(font_obj, 'face') and hasattr(font_obj.face, 'familyName'):
                    raw = font_obj.face.familyName
                    font_obj.face.familyName = name.encode('utf-8') if isinstance(raw, bytes) else name
            except Exception as e:
                missing.append(name)
                print(f"Warning: Font {name} — {e}", file=sys.stderr)
        else:
            missing.append(name)
    if missing:
        print(f"Warning: Missing fonts: {', '.join(missing)}", file=sys.stderr)

    # Verify fonts work — fallback to Songti if STHeiti causes Paragraph hang
    try:
        _test_style = ParagraphStyle('_font_test', fontName='STHeiti', fontSize=12)
        _test_para = Paragraph('<b>测试</b>中文段落<font name="Menlo">code</font>', _test_style)
        _test_para.wrap(400, 600)
    except Exception:
        print("Warning: STHeiti Paragraph test failed, falling back to Songti for headings", file=sys.stderr)
        global _STHEITI_FALLBACK
        _STHEITI_FALLBACK = False

    _fonts_registered = True

# ═══════════════════════════════════════════════════════════════════════
# THEMES
# ═══════════════════════════════════════════════════════════════════════

_DEFAULT_LAYOUT = {
    "margins": (25, 22, 28, 25),
    "body_font": "Songti", "body_bold": "SongtiBold",
    "heading_font": "STHeiti", "heading_light": "STHeitiLight",
    "body_size": 11, "body_leading": 18,
    "h1_size": 28, "h2_size": 20, "h3_size": 12, "h4_size": 10.5,
    "heading_align": "center", "heading_decoration": "rules",
    "header_style": "full", "code_style": "bg",
    "cover_style": "centered", "page_decoration": "top-bar",
    "first_line_indent": True,
    "code_max_lines": 30,
}

THEMES = {
    "chinese-red": {
        "canvas":"#FFFDF5","canvas_sec":"#F8F0E0","ink":"#1A1009","ink_faded":"#8C7A5E",
        "accent":"#B22222","accent_light":"#D44040","border":"#E8DCC8",
        "watermark_rgba":(0.88,0.82,0.72,0.10),
        "layout": {"body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":11,"body_leading":18,"h1_size":28,"h2_size":20,
                   "heading_align":"center","heading_decoration":"rules",
                   "header_style":"full","code_style":"bg","cover_style":"centered",
                   "page_decoration":"top-bar","first_line_indent":True},
    },
    "warm-academic": {
        "canvas":"#F9F9F7","canvas_sec":"#F0EEE6","ink":"#181818","ink_faded":"#87867F",
        "accent":"#CC785C","accent_light":"#D99A82","border":"#E8E6DC",
        "watermark_rgba":(0.82,0.80,0.76,0.12),
        "layout": {"body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10.5,"body_leading":17,"h1_size":26,"h2_size":18,
                   "heading_align":"center","heading_decoration":"rules",
                   "header_style":"full","code_style":"bg","cover_style":"centered",
                   "page_decoration":"top-bar","first_line_indent":True},
    },
    "nord-frost": {
        "canvas":"#ECEFF4","canvas_sec":"#E5E9F0","ink":"#2E3440","ink_faded":"#4C566A",
        "accent":"#5E81AC","accent_light":"#81A1C1","border":"#D8DEE9",
        "watermark_rgba":(0.74,0.78,0.85,0.10),
        "layout": {"body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10,"body_leading":16,"h3_size":11,
                   "heading_align":"left","heading_decoration":"underline",
                   "header_style":"minimal","code_style":"border","cover_style":"left-aligned",
                   "page_decoration":"left-stripe","first_line_indent":True},
    },
    "github-light": {
        "canvas":"#FFFFFF","canvas_sec":"#F6F8FA","ink":"#1F2328","ink_faded":"#656D76",
        "accent":"#0969DA","accent_light":"#218BFF","border":"#D0D7DE",
        "watermark_rgba":(0.80,0.82,0.85,0.08),
        "layout": {"body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10,"body_leading":16.5,"h3_size":11,
                   "heading_align":"left","heading_decoration":"none",
                   "header_style":"minimal","code_style":"bg","cover_style":"left-aligned",
                   "page_decoration":"left-stripe","first_line_indent":False},
    },
    "paper-classic": {
        "canvas":"#FFFFFF","canvas_sec":"#FAFAFA","ink":"#000000","ink_faded":"#666666",
        "accent":"#CC0000","accent_light":"#FF3333","border":"#DDDDDD",
        "watermark_rgba":(0.85,0.85,0.85,0.08),
        "layout": {"body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "heading_align":"center","heading_decoration":"rules",
                   "first_line_indent":True},
    },
    "ocean-breeze": {
        "canvas":"#F0F7F4","canvas_sec":"#E0EDE8","ink":"#1A2E35","ink_faded":"#5A7D7C",
        "accent":"#2A9D8F","accent_light":"#64CCBF","border":"#C8DDD6",
        "watermark_rgba":(0.75,0.85,0.80,0.10),
        "layout": {"body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10.5,"body_leading":17,
                   "heading_align":"left","heading_decoration":"underline",
                   "header_style":"full","code_style":"bg","cover_style":"centered",
                   "page_decoration":"top-bar","first_line_indent":True},
    },
    "tufte": {
        "canvas":"#FFFFF8","canvas_sec":"#F7F7F0","ink":"#111111","ink_faded":"#999988",
        "accent":"#980000","accent_light":"#C04040","border":"#E0DDD0",
        "watermark_rgba":(0.88,0.87,0.82,0.08),
        "layout": {"margins":(30,55,25,25),
                   "body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":11,"body_leading":18,"h1_size":24,"h2_size":16,"h3_size":11,
                   "heading_align":"left","heading_decoration":"none",
                   "header_style":"none","code_style":"border","cover_style":"minimal",
                   "page_decoration":"side-rule","first_line_indent":True},
    },
    "classic-thesis": {
        "canvas":"#FEFEFE","canvas_sec":"#F5F2EB","ink":"#2B2B2B","ink_faded":"#7A7568",
        "accent":"#8B4513","accent_light":"#A0522D","border":"#D6CFC2",
        "watermark_rgba":(0.82,0.78,0.72,0.10),
        "layout": {"body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10.5,"body_leading":17,"h1_size":28,"h2_size":20,
                   "heading_align":"center","heading_decoration":"rules",
                   "header_style":"full","code_style":"bg","cover_style":"centered",
                   "page_decoration":"corner-marks","first_line_indent":True},
    },
    "elegant-book": {
        "canvas":"#F3F2EC","canvas_sec":"#E8E6DC","ink":"#1A1E24","ink_faded":"#6A6E78",
        "accent":"#2D6A5A","accent_light":"#4A9480","border":"#D2CFCA",
        "watermark_rgba":(0.60,0.72,0.68,0.10),
        "layout": {"margins":(28,24,30,28),
                   "body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10.5,"body_leading":18,"h1_size":28,"h2_size":20,
                   "heading_align":"center","heading_decoration":"dot",
                   "header_style":"full","code_style":"bg","cover_style":"centered",
                   "page_decoration":"double-rule","first_line_indent":True},
    },
    "ink-wash": {
        "canvas":"#F8F6F0","canvas_sec":"#EEEAE0","ink":"#2C2C2C","ink_faded":"#8A8A80",
        "accent":"#404040","accent_light":"#666660","border":"#D8D4C8",
        "watermark_rgba":(0.80,0.80,0.76,0.10),
        "layout": {"margins":(30,30,30,28),
                   "body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10.5,"body_leading":18,"h1_size":24,"h2_size":16,"h3_size":11,
                   "heading_align":"center","heading_decoration":"dot",
                   "header_style":"none","code_style":"border","cover_style":"minimal",
                   "page_decoration":"none","first_line_indent":True},
    },
    "ieee-journal": {
        "canvas":"#FFFFFF","canvas_sec":"#F5F5F5","ink":"#000000","ink_faded":"#555555",
        "accent":"#003366","accent_light":"#336699","border":"#CCCCCC",
        "watermark_rgba":(0.82,0.82,0.82,0.08),
        "layout": {"margins":(20,20,22,20),
                   "body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":9.5,"body_leading":14,"h1_size":22,"h2_size":14,"h3_size":11,
                   "heading_align":"left","heading_decoration":"underline",
                   "header_style":"minimal","code_style":"border","cover_style":"left-aligned",
                   "page_decoration":"top-band","first_line_indent":False},
    },
    "textbook-green": {
        "canvas":"#FEFEF9","canvas_sec":"#F8F9F4","ink":"#1A1009","ink_faded":"#6B7A6E",
        "accent":"#2D5F3E","accent_light":"#4A8C6F","border":"#C5D5CD",
        "watermark_rgba":(0.60,0.72,0.55,0.10),
        "layout": {"margins":(28,24,30,28),
                   "body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10.5,"body_leading":18,"h1_size":28,"h2_size":20,
                   "heading_align":"center","heading_decoration":"rules",
                   "header_style":"full","code_style":"bg","cover_style":"textbook-green",
                   "page_decoration":"top-bar","first_line_indent":True,
                   "code_accent":"#D4A843"},
    },
    "textbook-cyber": {
        "canvas":"#FFFFFF","canvas_sec":"#F8F9FA","ink":"#1A1A2E","ink_faded":"#5A5A7E",
        "accent":"#0F969C","accent_light":"#2CB5BB","border":"#E2E8F0",
        "watermark_rgba":(0.50,0.58,0.62,0.10),
        "layout": {"margins":(28,24,30,28),
                   "body_font":"Songti","body_bold":"SongtiBold",
                   "heading_font":"STHeiti","heading_light":"STHeitiLight",
                   "body_size":10.5,"body_leading":18,"h1_size":28,"h2_size":20,
                   "heading_align":"center","heading_decoration":"rules",
                   "header_style":"full","code_style":"bg","cover_style":"textbook-cyber",
                   "page_decoration":"top-bar","first_line_indent":True,
                   "code_accent":"#0F969C"},
    },
}

def load_theme(name):
    if name in THEMES:
        t = THEMES[name]
    else:
        print(f"Unknown theme '{name}', falling back to chinese-red", file=sys.stderr)
        t = THEMES["chinese-red"]
    layout = dict(_DEFAULT_LAYOUT)
    layout.update(t.get("layout", {}))
    return {
        "canvas":     HexColor(t["canvas"]),
        "canvas_sec": HexColor(t["canvas_sec"]),
        "ink":        HexColor(t["ink"]),
        "ink_faded":  HexColor(t["ink_faded"]),
        "accent":     HexColor(t["accent"]),
        "accent_light": HexColor(t.get("accent_light", t["accent"])),
        "border":     HexColor(t["border"]),
        "wm_color":   Color(*t.get("watermark_rgba", (0.85,0.82,0.75,0.10))),
        "layout":     layout,
    }

# ═══════════════════════════════════════════════════════════════════════
# MINIMAL CJK DETECTION — only for paragraph merging, not font wrapping
# ═══════════════════════════════════════════════════════════════════════

_CJK_RANGES = [
    (0x4E00,0x9FFF),(0x3400,0x4DBF),(0xF900,0xFAFF),(0x3000,0x303F),
    (0xFF00,0xFFEF),(0x2E80,0x2EFF),(0x2F00,0x2FDF),(0xFE30,0xFE4F),
    (0x20000,0x2A6DF),(0x2A700,0x2B73F),(0x2B740,0x2B81F),
]

def _is_cjk(ch):
    """Check if a single character is CJK. Used only for paragraph merging."""
    cp = ord(ch)
    if cp < 0x3000:
        return False
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)

# ═══════════════════════════════════════════════════════════════════════
# INLINE MARKDOWN — no _font_wrap() needed (global CJK font)
# ═══════════════════════════════════════════════════════════════════════

def esc(text):
    return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def esc_code(text):
    """Escape for code — wrap CJK characters in Songti font tag."""
    out = []
    for line in text.split('\n'):
        e = esc(line)
        # 对 CJK 字符用 Songti 字体包裹
        parts = re.split(r'([\u4e00-\u9fff\u3400-\u4dbf\u3000-\u303f\uff00-\uffef\u2e80-\u2eff]+)', e)
        segs = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # CJK 段落
                segs.append(f'<font name="STHeiti">{part}</font>')
            else:
                segs.append(part)
        e = ''.join(segs)
        stripped = e.lstrip(' ')
        indent = len(e) - len(stripped)
        out.append('&nbsp;' * indent + stripped)
    return '<br/>'.join(out)

def md_inline(text, accent_hex="#B22222"):
    """Convert inline markdown to reportlab Paragraph markup.
    No _font_wrap() — global CJK font handles everything."""
    text = esc(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`(.+?)`',
        rf"<font name='Menlo' size='8' color='{accent_hex}'>\1</font>", text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'<u>\1</u>', text)
    return text

# ═══════════════════════════════════════════════════════════════════════
# CUSTOM FLOWABLES
# ═══════════════════════════════════════════════════════════════════════

_anchor_counter = [0]
_outline_level = [-1]
_cur_chapter = [""]

class ChapterMark(Flowable):
    """PDF bookmark + outline entry."""
    width = height = 0
    def __init__(self, title, level=0):
        Flowable.__init__(self)
        self.title = title
        self.level = level
        _anchor_counter[0] += 1
        self.key = f"anchor_{_anchor_counter[0]}"
    def draw(self):
        _cur_chapter[0] = self.title
        self.canv.bookmarkPage(self.key)
        target = min(self.level, _outline_level[0] + 1)
        _outline_level[0] = target
        self.canv.addOutlineEntry(self.title, self.key, level=target, closed=(target == 0))

class HRule(Flowable):
    def __init__(self, w, thick=0.5, clr=None):
        Flowable.__init__(self)
        self.width = w; self.height = 4*mm; self._t = thick
        self._c = clr or HexColor("#E8E6DC")
    def draw(self):
        self.canv.setStrokeColor(self._c); self.canv.setLineWidth(self._t)
        self.canv.line(0, 2*mm, self.width, 2*mm)

class HRuleCentered(Flowable):
    def __init__(self, frame_w, rule_w, thick=0.5, clr=None):
        Flowable.__init__(self)
        self.width = frame_w; self.height = 4*mm
        self._rw = rule_w; self._t = thick
        self._c = clr or HexColor("#E8E6DC")
    def draw(self):
        self.canv.setStrokeColor(self._c); self.canv.setLineWidth(self._t)
        x0 = (self.width - self._rw) / 2
        self.canv.line(x0, 2*mm, x0 + self._rw, 2*mm)

class DiamondRule(Flowable):
    def __init__(self, w, clr=None):
        Flowable.__init__(self)
        self.width = w; self.height = 5*mm
        self._c = clr or HexColor("#2D6A5A")
    def draw(self):
        self.canv.setStrokeColor(self._c); self.canv.setLineWidth(0.6)
        cx = self.width / 2
        rw = 18*mm  # 每侧横线长度
        y = 2.5*mm
        # 两侧短横线
        self.canv.line(cx - rw, y, cx - 3*mm, y)
        self.canv.line(cx + 3*mm, y, cx + rw, y)
        # 中间小菱形
        ds = 1.2*mm  # 菱形半径
        p = self.canv.beginPath()
        p.moveTo(cx, y + ds)
        p.lineTo(cx + ds, y)
        p.lineTo(cx, y - ds)
        p.lineTo(cx - ds, y)
        p.close()
        self.canv.setFillColor(self._c); self.canv.drawPath(p, fill=1, stroke=0)

class LeftBorderParagraph(Flowable):
    """Paragraph with left accent border (for code 'border' style)."""
    def __init__(self, para, border_color, border_width=2):
        Flowable.__init__(self)
        self._para = para; self._bc = border_color; self._bw = border_width
    def wrap(self, aw, ah):
        w, h = self._para.wrap(aw, ah)
        self.width = w; self.height = h
        return w, h
    def draw(self):
        self._para.drawOn(self.canv, 0, 0)
        self.canv.setStrokeColor(self._bc); self.canv.setLineWidth(self._bw)
        self.canv.line(2, -2, 2, self.height + 2)

# ═══════════════════════════════════════════════════════════════════════
# PDF BUILDER
# ═══════════════════════════════════════════════════════════════════════

class PDFBuilder:
    def __init__(self, config):
        self.cfg = config
        self.T = config["theme"]
        self.L = self.T["layout"]
        self.page_w, self.page_h = config["page_size"]
        lm, rm, tm, bm = self.L["margins"]
        self.lm, self.rm, self.tm, self.bm = lm*mm, rm*mm, tm*mm, bm*mm
        self.body_w = self.page_w - self.lm - self.rm
        self.body_h = self.page_h - self.tm - self.bm
        self.accent_hex = config.get("accent_hex", "#B22222")
        self.ST = self._build_styles()

    def _build_styles(self):
        T = self.T; L = self.L
        s = {}
        bf = L["body_font"]
        bb = L.get("body_bold", "SongtiBold")
        hf = "Songti" if _STHEITI_FALLBACK else L.get("heading_font", "STHeiti")
        hl = "SongtiBold" if _STHEITI_FALLBACK else L.get("heading_light", "STHeitiLight")
        bs, bl = L["body_size"], L["body_leading"]
        h1s = L.get("h1_size", 28)
        h2s = L.get("h2_size", 20)
        h3s = L.get("h3_size", 12)
        h4s = L.get("h4_size", 10.5)
        h_align = TA_CENTER if L["heading_align"] == "center" else TA_LEFT
        indent = L.get("first_line_indent", True)
        fli = int(bs * 2) if indent else 0  # 首行缩进两字符

        s['part'] = ParagraphStyle('Part', fontName=hf, fontSize=h1s,
            leading=h1s+10, textColor=T["ink"], alignment=h_align, spaceBefore=0, spaceAfter=0)
        s['chapter'] = ParagraphStyle('Ch', fontName=hf, fontSize=h2s,
            leading=h2s+8, textColor=T["ink"], alignment=h_align, spaceBefore=0, spaceAfter=0)
        s['h3'] = ParagraphStyle('H3', fontName=hf, fontSize=h3s,
            leading=h3s+5, textColor=T["accent"], alignment=TA_LEFT,
            spaceBefore=10, spaceAfter=4)
        s['h4'] = ParagraphStyle('H4', fontName=hl, fontSize=h4s,
            leading=h4s+4, textColor=T["accent_light"], alignment=TA_LEFT,
            spaceBefore=6, spaceAfter=2)
        s['body'] = ParagraphStyle('Body', fontName=bf, fontSize=bs, leading=bl,
            textColor=T["ink"], alignment=TA_JUSTIFY, spaceBefore=2, spaceAfter=4,
            firstLineIndent=fli, wordWrap='CJK')
        s['body_noi'] = ParagraphStyle('BodyNI', fontName=bf, fontSize=bs, leading=bl,
            textColor=T["ink"], alignment=TA_JUSTIFY, spaceBefore=2, spaceAfter=4,
            wordWrap='CJK')
        s['body_indent'] = ParagraphStyle('BI', parent=s['body'],
            leftIndent=14, rightIndent=14, textColor=T["ink_faded"],
            borderColor=T["accent"], borderWidth=0, borderPadding=4,
            firstLineIndent=0)
        s['bullet'] = ParagraphStyle('Bul', fontName=bf, fontSize=bs, leading=bl,
            textColor=T["ink"], alignment=TA_LEFT, spaceBefore=1, spaceAfter=1,
            leftIndent=18, bulletIndent=6, wordWrap='CJK')
        code_style = L["code_style"]
        code_bg = T["canvas_sec"] if code_style == "bg" else None
        s['code'] = ParagraphStyle('Code', fontName="Menlo", fontSize=7.5, leading=10.5,
            textColor=HexColor("#3D3D3A"), alignment=TA_LEFT, spaceBefore=4, spaceAfter=4,
            leftIndent=8, rightIndent=8, backColor=code_bg,
            borderColor=T["border"] if code_style == "bg" else None,
            borderWidth=0.5 if code_style == "bg" else 0, borderPadding=6)
        s['toc1'] = ParagraphStyle('T1', fontName=hf, fontSize=12, leading=20,
            textColor=T["ink"], leftIndent=0, spaceBefore=6, spaceAfter=2)
        s['toc2'] = ParagraphStyle('T2', fontName=bf, fontSize=10, leading=16,
            textColor=T["ink_faded"], leftIndent=16, spaceBefore=1, spaceAfter=1)
        s['th'] = ParagraphStyle('TH', fontName=hf, fontSize=8.5, leading=12,
            textColor=white, alignment=TA_CENTER)
        s['tc'] = ParagraphStyle('TC', fontName=bf, fontSize=8, leading=11,
            textColor=T["ink"], alignment=TA_LEFT)
        return s

    # ── Page callbacks ──
    def _draw_bg(self, c):
        c.setFillColor(self.T["canvas"])
        c.rect(0, 0, self.page_w, self.page_h, fill=1, stroke=0)

    def _cover_page(self, c, doc):
        c.saveState(); self._draw_bg(c)
        T = self.T; cx = self.page_w / 2
        cover = self.L["cover_style"]

        # Theme-specific cover rendering
        if cover == "textbook-green":
            self._cover_textbook_green(c, T, cx)
            c.restoreState()
            return
        elif cover == "textbook-cyber":
            self._cover_textbook_cyber(c, T, cx)
            c.restoreState()
            return

        # Top accent bar
        c.setFillColor(T["accent"])
        c.rect(0, self.page_h - 3*mm, self.page_w, 3*mm, fill=1, stroke=0)

        title = self.cfg.get("title", "Document")
        title_y = self.page_h * 0.62
        hf = self.L.get("heading_font", "STHeiti")
        title_size = 38
        c.setFillColor(T["ink"])
        # Draw title centered, shrink if needed
        tw = c.stringWidth(title, hf, title_size)
        if tw > self.page_w - 40*mm:
            for sz in range(38, 16, -1):
                tw = c.stringWidth(title, hf, sz)
                if tw <= self.page_w - 40*mm:
                    title_size = sz
                    break
        c.setFont(hf, title_size)
        tw = c.stringWidth(title, hf, title_size)
        c.drawString(cx - tw/2, title_y, title)
        btm = title_y

        ver = self.cfg.get("version", "")
        if ver:
            c.setFillColor(T["accent"]); c.setFont("STHeiti", 13)
            vw = c.stringWidth(ver, "STHeiti", 13)
            c.drawString(cx - vw/2, btm - 30, ver)

        rule_y = btm - 52
        c.setStrokeColor(T["accent"]); c.setLineWidth(1.5)
        c.line(cx - 17*mm, rule_y, cx + 17*mm, rule_y)

        stats = self.cfg.get("stats_line", "")
        stats2 = self.cfg.get("stats_line2", "")
        if stats or stats2:
            c.setFillColor(T["ink_faded"])
            sy = rule_y - 72
            if stats:
                c.setFont("Songti", 9.5)
                sw = c.stringWidth(stats, "Songti", 9.5)
                c.drawString(cx - sw/2, sy, stats)
            if stats2:
                c.setFont("Songti", 9.5)
                sw = c.stringWidth(stats2, "Songti", 9.5)
                c.drawString(cx - sw/2, sy - 18, stats2)

        author = self.cfg.get("author", "")
        if author:
            c.setFillColor(T["ink_faded"]); c.setFont("Songti", 10)
            aw = c.stringWidth(author, "Songti", 10)
            c.drawString(cx - aw/2, 38*mm, author)

        dt = self.cfg.get("date", str(date.today()))
        c.setFillColor(T["ink_faded"]); c.setFont("Songti", 9)
        dw = c.stringWidth(dt, "Songti", 9)
        c.drawString(cx - dw/2, 28*mm, dt)

        # Bottom accent bar
        c.setFillColor(T["accent"])
        c.rect(0, 0, self.page_w, 3*mm, fill=1, stroke=0)
        c.restoreState()

    def _cover_textbook_green(self, c, T, cx):
        """Textbook-green cover: large green color block + white title + geometric decorations."""
        main_color = HexColor("#2D5F3E")
        mint_color = HexColor("#4A8C6F")
        gold_color = HexColor("#D4A843")
        bg_color = HexColor("#FEFEF9")
        hf = self.L.get("heading_font", "STHeiti")

        # Background
        c.setFillColor(bg_color)
        c.rect(0, 0, self.page_w, self.page_h, fill=1, stroke=0)

        # Large main color block (top ~55%)
        block_h = self.page_h * 0.55
        c.setFillColor(main_color)
        c.rect(0, self.page_h - block_h, self.page_w, block_h, fill=1, stroke=0)

        # Decorative diagonal stripe in mint
        p = c.beginPath()
        p.moveTo(0, self.page_h - block_h + 15*mm)
        p.lineTo(self.page_w, self.page_h - block_h - 10*mm)
        p.lineTo(self.page_w, self.page_h - block_h + 5*mm)
        p.lineTo(0, self.page_h - block_h + 30*mm)
        p.close()
        c.setFillColor(mint_color)
        c.drawPath(p, fill=1, stroke=0)

        # Title in white on color block
        title = self.cfg.get("title", "Document")
        title_y = self.page_h * 0.70
        title_size = 38
        c.setFillColor(white)
        tw = c.stringWidth(title, hf, title_size)
        if tw > self.page_w - 50*mm:
            for sz in range(38, 16, -1):
                tw = c.stringWidth(title, hf, sz)
                if tw <= self.page_w - 50*mm:
                    title_size = sz; break
        c.setFont(hf, title_size)
        tw = c.stringWidth(title, hf, title_size)
        c.drawString(cx - tw/2, title_y, title)

        # Gold accent line below title
        line_y = title_y - 50
        c.setStrokeColor(gold_color); c.setLineWidth(2)
        c.line(cx - 25*mm, line_y, cx + 25*mm, line_y)

        # Version
        ver = self.cfg.get("version", "")
        if ver:
            c.setFillColor(gold_color); c.setFont("STHeiti", 12)
            vw = c.stringWidth(ver, "STHeiti", 12)
            c.drawString(cx - vw/2, line_y - 22, ver)

        # Author & date on lower white area
        author = self.cfg.get("author", "")
        if author:
            c.setFillColor(T["ink"]); c.setFont("Songti", 12)
            aw = c.stringWidth(author, "Songti", 12)
            c.drawString(cx - aw/2, self.page_h * 0.28, author)

        dt = self.cfg.get("date", str(date.today()))
        c.setFillColor(T["ink_faded"]); c.setFont("Songti", 10)
        dw = c.stringWidth(dt, "Songti", 10)
        c.drawString(cx - dw/2, self.page_h * 0.22, dt)

        # Bottom geometric decorations: triangles and lines in green tones
        deco_y = 20*mm
        # Horizontal thin lines
        c.setStrokeColor(mint_color); c.setLineWidth(0.6)
        for i, dy in enumerate([deco_y, deco_y + 5*mm, deco_y + 10*mm]):
            c.line(15*mm, dy, 15*mm + (35 - i*8)*mm, dy)
        # Small triangles
        c.setFillColor(main_color)
        for i, (tx, ty) in enumerate([(self.page_w - 30*mm, deco_y),
                                        (self.page_w - 22*mm, deco_y + 3*mm),
                                        (self.page_w - 35*mm, deco_y + 5*mm)]):
            p = c.beginPath()
            s = 3*mm - i*0.8*mm
            p.moveTo(tx, ty + s); p.lineTo(tx + s, ty - s*0.5); p.lineTo(tx - s, ty - s*0.5)
            p.close()
            c.drawPath(p, fill=1, stroke=0)
        # Gold dot accents
        c.setFillColor(gold_color)
        for gx in [cx - 8*mm, cx, cx + 8*mm]:
            c.circle(gx, deco_y + 2*mm, 1.2*mm, fill=1, stroke=0)

    def _cover_textbook_cyber(self, c, T, cx):
        """Textbook-cyber cover: dark gradient + white title + circuit board / grid decorations."""
        dark1 = HexColor("#1A1A2E")
        dark2 = HexColor("#16213E")
        cyan = HexColor("#0F969C")
        bg_color = HexColor("#FFFFFF")
        hf = self.L.get("heading_font", "STHeiti")

        # Background
        c.setFillColor(bg_color)
        c.rect(0, 0, self.page_w, self.page_h, fill=1, stroke=0)

        # Dark gradient block (top ~58%) - simulate gradient with horizontal bands
        block_h = self.page_h * 0.58
        bands = 40
        for i in range(bands):
            y0 = self.page_h - block_h + i * block_h / bands
            y1 = y0 + block_h / bands + 1
            frac = i / bands
            r = dark1.red + (dark2.red - dark1.red) * frac
            g = dark1.green + (dark2.green - dark1.green) * frac
            b = dark1.blue + (dark2.blue - dark1.blue) * frac
            c.setFillColor(Color(r, g, b))
            c.rect(0, y0, self.page_w, y1 - y0, fill=1, stroke=0)

        # Circuit board / grid line decorations on the dark block
        c.setStrokeColor(Color(0.06, 0.59, 0.61, 0.15))  # very faint cyan
        c.setLineWidth(0.4)
        # Vertical grid lines
        for gx in range(int(20*mm), int(self.page_w), int(15*mm)):
            c.line(gx, self.page_h - block_h + 5*mm, gx, self.page_h - 5*mm)
        # Horizontal grid lines
        for gy_i in range(int(8)):
            gy = self.page_h - 5*mm - gy_i * 18*mm
            if gy < self.page_h - block_h + 5*mm:
                break
            c.line(10*mm, gy, self.page_w - 10*mm, gy)

        # Circuit traces: random line segments with dots (nodes)
        import random
        rng = random.Random(42)  # deterministic seed
        c.setStrokeColor(Color(0.06, 0.59, 0.61, 0.25))
        c.setLineWidth(0.8)
        for _ in range(12):
            x1 = rng.randint(int(10*mm), int(self.page_w - 10*mm))
            y1 = rng.randint(int(self.page_h - block_h + 10*mm), int(self.page_h - 10*mm))
            # Horizontal then vertical trace
            x2 = x1 + rng.randint(int(-30*mm), int(30*mm))
            c.line(x1, y1, x2, y1)
            y2 = y1 + rng.randint(int(-15*mm), int(15*mm))
            c.line(x2, y1, x2, y2)
            # Node dot
            c.setFillColor(Color(0.06, 0.59, 0.61, 0.4))
            c.circle(x2, y2, 1.2*mm, fill=1, stroke=0)
            c.circle(x1, y1, 0.8*mm, fill=1, stroke=0)
            c.setStrokeColor(Color(0.06, 0.59, 0.61, 0.25))
            c.setLineWidth(0.8)

        # Title in white on dark block
        title = self.cfg.get("title", "Document")
        title_y = self.page_h * 0.72
        title_size = 38
        c.setFillColor(white)
        tw = c.stringWidth(title, hf, title_size)
        if tw > self.page_w - 50*mm:
            for sz in range(38, 16, -1):
                tw = c.stringWidth(title, hf, sz)
                if tw <= self.page_w - 50*mm:
                    title_size = sz; break
        c.setFont(hf, title_size)
        tw = c.stringWidth(title, hf, title_size)
        c.drawString(cx - tw/2, title_y, title)

        # Cyan accent line
        line_y = title_y - 50
        c.setStrokeColor(cyan); c.setLineWidth(2.5)
        c.line(cx - 25*mm, line_y, cx + 25*mm, line_y)
        # Small cyan endpoint squares
        c.setFillColor(cyan)
        c.rect(cx - 25*mm - 2*mm, line_y - 1*mm, 2*mm, 2*mm, fill=1, stroke=0)
        c.rect(cx + 25*mm, line_y - 1*mm, 2*mm, 2*mm, fill=1, stroke=0)

        # Version
        ver = self.cfg.get("version", "")
        if ver:
            c.setFillColor(cyan); c.setFont("STHeiti", 12)
            vw = c.stringWidth(ver, "STHeiti", 12)
            c.drawString(cx - vw/2, line_y - 22, ver)

        # Author & date on lower white area
        author = self.cfg.get("author", "")
        if author:
            c.setFillColor(T["ink"]); c.setFont("Songti", 12)
            aw = c.stringWidth(author, "Songti", 12)
            c.drawString(cx - aw/2, self.page_h * 0.28, author)

        dt = self.cfg.get("date", str(date.today()))
        c.setFillColor(T["ink_faded"]); c.setFont("Songti", 10)
        dw = c.stringWidth(dt, "Songti", 10)
        c.drawString(cx - dw/2, self.page_h * 0.22, dt)

        # Bottom decoration: circuit trace lines on white area
        c.setStrokeColor(Color(0.06, 0.59, 0.61, 0.3))
        c.setLineWidth(0.6)
        deco_y = 18*mm
        for i in range(5):
            x0 = 15*mm + i * 22*mm
            c.line(x0, deco_y, x0 + 12*mm, deco_y)
            c.line(x0 + 12*mm, deco_y, x0 + 12*mm, deco_y + 5*mm)
            c.setFillColor(Color(0.06, 0.59, 0.61, 0.35))
            c.circle(x0 + 12*mm, deco_y + 5*mm, 0.8*mm, fill=1, stroke=0)
            c.setStrokeColor(Color(0.06, 0.59, 0.61, 0.3))

    def _draw_page_decoration(self, c):
        T = self.T; deco = self.L.get("page_decoration", "none")
        if deco == "top-bar":
            c.setFillColor(T["accent"])
            c.rect(0, self.page_h - 2.5*mm, self.page_w, 2.5*mm, fill=1, stroke=0)
        elif deco == "left-stripe":
            c.setFillColor(T["accent"])
            c.rect(0, 0, 5*mm, self.page_h, fill=1, stroke=0)
        elif deco == "side-rule":
            c.setStrokeColor(T["border"]); c.setLineWidth(0.4)
            c.line(self.lm - 5*mm, self.bm, self.lm - 5*mm, self.page_h - self.tm + 5*mm)
        elif deco == "corner-marks":
            c.setStrokeColor(T["accent"]); c.setLineWidth(0.8)
            m = 12*mm; clen = 12*mm
            for (x,y,dx,dy) in [(m,self.page_h-m,clen,0),(m,self.page_h-m,0,-clen),
                                 (self.page_w-m,self.page_h-m,-clen,0),(self.page_w-m,self.page_h-m,0,-clen),
                                 (m,m,clen,0),(m,m,0,clen),
                                 (self.page_w-m,m,-clen,0),(self.page_w-m,m,0,clen)]:
                c.line(x,y,x+dx,y+dy)
        elif deco == "top-band":
            c.setFillColor(T["accent"])
            c.rect(0, self.page_h - 8*mm, self.page_w, 8*mm, fill=1, stroke=0)
            header_title = self.cfg.get("header_title", "")
            if header_title:
                c.setFillColor(white); c.setFont("Songti", 7.5)
                c.drawString(self.lm, self.page_h - 6*mm, header_title)
            ch = _cur_chapter[0]
            if ch:
                c.setFillColor(white); c.setFont("Songti", 7.5)
                c.drawRightString(self.page_w - self.rm, self.page_h - 6*mm, ch[:40])
        elif deco == "double-rule":
            c.setStrokeColor(T["accent"]); c.setLineWidth(0.6)
            yt = self.page_h - 14*mm
            c.line(self.lm, yt, self.page_w - self.rm, yt)
            c.line(self.lm, yt - 2*mm, self.page_w - self.rm, yt - 2*mm)
            yb = self.bm - 4*mm
            c.line(self.lm, yb, self.page_w - self.rm, yb)
            c.line(self.lm, yb + 2*mm, self.page_w - self.rm, yb + 2*mm)

    def _normal_page(self, c, doc):
        self._draw_bg(c); pg = c.getPageNumber()
        c.saveState()
        T = self.T; hs = self.L["header_style"]
        self._draw_page_decoration(c)

        # Watermark
        wm = self.cfg.get("watermark", "")
        if wm:
            c.setFont("Songti", 52); c.setFillColor(T["wm_color"])
            c.translate(self.page_w/2, self.page_h/2); c.rotate(35)
            for dy in range(-300, 400, 160):
                for dx in range(-400, 500, 220):
                    c.drawCentredString(dx, dy, wm)
            c.rotate(-35); c.translate(-self.page_w/2, -self.page_h/2)

        deco = self.L.get("page_decoration", "none")
        if hs == "full" and deco != "top-band":
            c.setStrokeColor(T["border"]); c.setLineWidth(0.5)
            c.line(self.lm, self.page_h - 20*mm, self.page_w - self.rm, self.page_h - 20*mm)
            c.setFillColor(T["ink_faded"]); c.setFont("Songti", 8)
            header_title = self.cfg.get("header_title", "")
            if header_title:
                c.drawString(self.lm, self.page_h - 18*mm, header_title)
            ch = _cur_chapter[0]
            if ch:
                c.drawRightString(self.page_w - self.rm, self.page_h - 18*mm, ch[:40])

        # Footer
        if hs != "none" and deco not in ("double-rule",):
            c.setStrokeColor(T["border"])
            c.line(self.lm, self.bm - 8*mm, self.page_w - self.rm, self.bm - 8*mm)
        if hs == "full":
            c.setFillColor(T["accent"]); c.setFont("Songti", 9)
            c.drawCentredString(self.page_w/2, self.bm - 16*mm, f"—  {pg}  —")
            fl = self.cfg.get("footer_left", self.cfg.get("author", ""))
            if fl:
                c.setFillColor(T["ink_faded"]); c.setFont("Songti", 8)
                c.drawString(self.lm, self.bm - 16*mm, fl)
            c.setFillColor(T["ink_faded"]); c.setFont("Songti", 8)
            dt = self.cfg.get("date", str(date.today()))
            c.drawRightString(self.page_w - self.rm, self.bm - 16*mm, dt)
        elif hs == "minimal":
            c.setFillColor(T["ink_faded"]); c.setFont("Songti", 8)
            c.drawCentredString(self.page_w/2, self.bm - 14*mm, str(pg))
        else:
            c.setFillColor(T["ink_faded"]); c.setFont("Songti", 8)
            c.drawCentredString(self.page_w/2, self.bm - 10*mm, str(pg))
        c.restoreState()

    def _toc_page(self, c, doc):
        self._draw_bg(c); pg = c.getPageNumber()
        c.saveState()
        T = self.T
        self._draw_page_decoration(c)
        c.setStrokeColor(T["border"]); c.setLineWidth(0.5)
        c.line(self.lm, self.page_h - 20*mm, self.page_w - self.rm, self.page_h - 20*mm)
        c.setFillColor(T["ink_faded"]); c.setFont("Songti", 8)
        header_title = self.cfg.get("header_title", "")
        if header_title:
            c.drawString(self.lm, self.page_h - 18*mm, header_title)
        c.setFont("Songti", 8)
        c.drawRightString(self.page_w - self.rm, self.page_h - 18*mm, "目  录")
        c.setStrokeColor(T["border"])
        c.line(self.lm, self.bm - 8*mm, self.page_w - self.rm, self.bm - 8*mm)
        c.setFillColor(T["accent"]); c.setFont("Songti", 9)
        c.drawCentredString(self.page_w/2, self.bm - 16*mm, f"—  {pg}  —")
        c.restoreState()

    def _backcover_page(self, c, doc):
        c.saveState(); self._draw_bg(c)
        T = self.T
        c.setFillColor(T["accent"])
        c.rect(0, self.page_h - 3*mm, self.page_w, 3*mm, fill=1, stroke=0)
        banner = self.cfg.get("banner", "")
        if banner and os.path.exists(banner):
            cx = self.page_w / 2; cy = self.page_h / 2
            try:
                c.drawImage(banner, cx - 75*mm, cy - 29*mm, width=150*mm, height=58*mm,
                            preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
        disclaimer = self.cfg.get("disclaimer", "")
        if disclaimer:
            c.setFillColor(T["ink_faded"]); c.setFont("Songti", 8.5)
            dw = c.stringWidth(disclaimer, "Songti", 8.5)
            c.drawString(cx - dw/2, 32*mm, disclaimer) if 'cx' in dir() else None
            # Safe: just draw centered
        copyright_text = self.cfg.get("copyright", "")
        if copyright_text:
            c.setFillColor(T["ink_faded"]); c.setFont("Songti", 8.5)
            c.drawCentredString(self.page_w/2, 20*mm, copyright_text)
        c.setFillColor(T["accent"])
        c.rect(0, 0, self.page_w, 3*mm, fill=1, stroke=0)
        c.restoreState()

    # ── Table parser ──
    def parse_table(self, lines):
        rows = []
        for l in lines:
            l = l.strip().strip('|')
            rows.append([c.strip() for c in l.split('|')])
        if len(rows) < 2: return None
        header = rows[0]
        data = [r for r in rows[1:] if not all(set(c.strip()) <= set('-: ') for c in r)]
        if not data: return None
        nc = len(header); ST = self.ST; ah = self.accent_hex
        td = [[Paragraph(md_inline(h, ah), ST['th']) for h in header]]
        for r in data:
            while len(r) < nc: r.append("")
            td.append([Paragraph(md_inline(c, ah), ST['tc']) for c in r[:nc]])
        avail = self.body_w - 4*mm
        max_lens = [max((len(r[ci]) if ci < len(r) else 0) for r in [header]+data) for ci in range(nc)]
        max_lens = [max(m, 2) for m in max_lens]
        total = sum(max_lens)
        cw = [avail * m / total for m in max_lens]
        min_w = 18*mm
        for ci in range(nc):
            if cw[ci] < min_w:
                deficit = min_w - cw[ci]; cw[ci] = min_w
                widest = sorted(range(nc), key=lambda x: -cw[x])
                for oi in widest:
                    if oi != ci: cw[oi] -= deficit; break
        T = self.T
        t = Table(td, colWidths=cw, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0), T["accent"]),
            ('TEXTCOLOR',(0,0),(-1,0), white),
            ('ROWBACKGROUNDS',(0,1),(-1,-1), [white, T["canvas_sec"]]),
            ('GRID',(0,0),(-1,-1), 0.5, T["border"]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
        ]))
        return t

    # ── Markdown → Story ──
    @staticmethod
    def _preprocess_md(md):
        """Normalize markdown: strip frontmatter, split merged headings."""
        lines = md.split('\n')
        # Strip YAML frontmatter
        if lines and lines[0].strip() == '---':
            for idx in range(1, len(lines)):
                if lines[idx].strip() == '---':
                    lines = lines[idx+1:]
                    break
        out = []
        in_code = False
        for line in lines:
            if line.strip().startswith('```'):
                in_code = not in_code
            if in_code:
                out.append(line); continue
            parts = re.split(r'(?<=[^#\s])\s*(?=#{1,3}\s)', line)
            if len(parts) > 1:
                for p in parts:
                    p = p.strip()
                    if p: out.append(p)
            else:
                out.append(line)
        return '\n'.join(out)

    def parse_md(self, md):
        story, toc = [], []
        md = self._preprocess_md(md)
        lines = md.split('\n')
        i = 0; in_code = False; code_buf = []
        ST = self.ST; ah = self.accent_hex
        code_max = self.L.get("code_max_lines", 30)

        while i < len(lines):
            line = lines[i]; stripped = line.strip()

            # Code blocks
            if stripped.startswith('```'):
                if in_code:
                    ct = '\n'.join(code_buf)
                    if ct.strip():
                        cl = ct.split('\n')
                        if len(cl) > code_max:
                            cl = cl[:code_max - 2] + ['  // ... (truncated)']
                            ct = '\n'.join(cl)
                        para = Paragraph(esc_code(ct), ST['code'])
                        if self.L["code_style"] == "border":
                            story.append(LeftBorderParagraph(para, self.T["accent"]))
                        else:
                            story.append(para)
                    code_buf = []; in_code = False
                else:
                    in_code = True; code_buf = []
                i += 1; continue
            if in_code:
                code_buf.append(line); i += 1; continue

            if stripped in ('---', '\\newpage') or not stripped:
                i += 1; continue

            # Skip YAML-like metadata
            if re.match(r'^(title|subtitle|author|date|tags|type|version):', stripped, re.I):
                i += 1; continue

            # H1 — Part heading
            if re.match(r'^# .+', stripped) and not stripped.startswith('## '):
                title = stripped.lstrip('#').strip()
                story.append(PageBreak())
                cm = ChapterMark(title, level=0); story.append(cm)
                hdeco = self.L["heading_decoration"]
                story.append(Spacer(1, self.body_h * 0.15))
                if hdeco == "rules":
                    story.append(HRuleCentered(self.body_w, 40*mm, 0.8, self.T["accent"]))
                    story.append(Spacer(1, 8*mm))
                story.append(Paragraph(md_inline(title, ah), ST['part']))
                if hdeco == "rules":
                    story.append(Spacer(1, 8*mm))
                    story.append(HRuleCentered(self.body_w, 25*mm, 0.8, self.T["accent"]))
                elif hdeco == "underline":
                    story.append(Spacer(1, 4*mm))
                    story.append(HRule(self.body_w, 1.0, self.T["accent"]))
                elif hdeco == "dot":
                    story.append(Spacer(1, 6*mm))
                    story.append(DiamondRule(self.body_w, self.T["accent"]))
                toc.append(('part', title, cm.key))
                i += 1; continue

            # H2 — Chapter heading
            if stripped.startswith('## ') and not stripped.startswith('### '):
                title = stripped[3:].strip()
                story.append(PageBreak())
                cm = ChapterMark(title, level=1); story.append(cm)
                hdeco = self.L["heading_decoration"]
                story.append(Spacer(1, self.body_h * 0.12))
                story.append(Paragraph(md_inline(title, ah), ST['chapter']))
                if hdeco == "rules":
                    story.append(Spacer(1, 5*mm))
                    story.append(HRuleCentered(self.body_w, 35*mm, 1.2, self.T["accent"]))
                elif hdeco == "underline":
                    story.append(Spacer(1, 3*mm))
                    story.append(HRule(self.body_w, 0.8, self.T["accent"]))
                elif hdeco == "dot":
                    story.append(Spacer(1, 5*mm))
                    story.append(DiamondRule(self.body_w, self.T["accent"]))
                toc.append(('chapter', title, cm.key))
                i += 1; continue

            # H3
            if stripped.startswith('### ') and not stripped.startswith('#### '):
                story.append(Spacer(1, 3*mm))
                story.append(Paragraph(md_inline(stripped[4:].strip(), ah), ST['h3']))
                story.append(Spacer(1, 1*mm))
                i += 1; continue

            # H4
            if stripped.startswith('#### '):
                story.append(Paragraph(md_inline(stripped[5:].strip(), ah), ST['h4']))
                i += 1; continue

            # H5 — 渲染为加粗段落
            if stripped.startswith('##### ') and not stripped.startswith('###### '):
                story.append(Paragraph(f'<b>{md_inline(stripped[6:].strip(), ah)}</b>', ST.get('h4', ST.get('body'))))
                i += 1; continue
            # H6 — 渲染为加粗段落（稍小）
            if stripped.startswith('###### '):
                story.append(Paragraph(f'<b>{md_inline(stripped[7:].strip(), ah)}</b>', ST.get('h4', ST.get('body'))))
                i += 1; continue

            # Tables
            if stripped.startswith('|'):
                tl = []
                while i < len(lines) and lines[i].strip().startswith('|'):
                    tl.append(lines[i]); i += 1
                t = self.parse_table(tl)
                if t:
                    story.append(Spacer(1, 2*mm)); story.append(t)
                    story.append(Spacer(1, 2*mm))
                continue

            # Bullets
            if stripped.startswith('- ') or stripped.startswith('* '):
                story.append(Paragraph(f"\u2022  {md_inline(stripped[2:].strip(), ah)}", ST['bullet']))
                i += 1; continue

            # Numbered list
            m = re.match(r'^(\d+)\.\s+(.+)', stripped)
            if m:
                story.append(Paragraph(f"{m.group(1)}.  {md_inline(m.group(2), ah)}", ST['bullet']))
                i += 1; continue

            # Blockquote — merge consecutive > lines into one block
            if stripped.startswith('>'):
                qlines = []
                while i < len(lines) and lines[i].strip().startswith('>'):
                    raw = lines[i].strip()
                    # Strip leading > and optional space(s)
                    content = re.sub(r'^>+\s*', '', raw)
                    qlines.append(content)
                    i += 1
                # Merge into paragraphs (split on empty lines within quote block)
                for qpara_text in '\n'.join(qlines).split('\n\n'):
                    merged = []
                    for pl in qpara_text.split('\n'):
                        pl = pl.strip()
                        if not pl:
                            continue
                        if merged and _is_cjk(merged[-1][-1]) and _is_cjk(pl[0]):
                            merged[-1] += pl
                        else:
                            merged.append(pl)
                    if merged:
                        qtext = ' '.join(merged)
                        story.append(Paragraph(md_inline(qtext, ah), ST['body_indent']))
                continue

            # Paragraph — join consecutive lines
            plines = []
            while i < len(lines):
                l = lines[i].strip()
                if not l or l.startswith('#') or l.startswith('```') or l.startswith('|') or \
                   l.startswith('- ') or l.startswith('* ') or l.startswith('>') or re.match(r'^\d+\.\s', l):
                    break
                plines.append(l); i += 1
            if plines:
                merged = plines[0]
                for pl in plines[1:]:
                    if merged and pl and _is_cjk(merged[-1]) and _is_cjk(pl[0]):
                        merged += pl
                    else:
                        merged += ' ' + pl
                story.append(Paragraph(md_inline(merged, ah), ST['body']))
            # 防止非识别的 # 行（H5/H6）陷入无限循环
            if not plines:
                i += 1
            continue

        return story, toc

    def build_toc(self, toc):
        ST = self.ST; ah = self.accent_hex
        ink = self.T["ink"]
        ink_hex = f"#{int(ink.red*255):02x}{int(ink.green*255):02x}{int(ink.blue*255):02x}"
        s = [Spacer(1, 15*mm)]
        s.append(Paragraph("目    录", ST['part']))
        s.append(HRule(self.body_w * 0.12, 1, self.T["accent"]))
        s.append(Spacer(1, 8*mm))
        for etype, title, key in toc:
            style = ST['toc1'] if etype == 'part' else ST['toc2']
            linked = f'<a href="#{key}" color="{ink_hex}">{esc(title)}</a>'
            s.append(Paragraph(linked, style))
        return s

    # ── Build PDF ──
    def build(self, md_text, output_path):
        register_fonts()
        print("Parsing markdown...")
        story_content, toc = self.parse_md(md_text)
        print(f"  {len(story_content)} elements, {len(toc)} TOC entries")

        body_frame = Frame(self.lm, self.bm, self.body_w, self.body_h, id='body')
        full_frame = Frame(0, 0, self.page_w, self.page_h, leftPadding=0,
                           rightPadding=0, topPadding=0, bottomPadding=0, id='full')

        doc = BaseDocTemplate(output_path, pagesize=(self.page_w, self.page_h),
                              leftMargin=self.lm, rightMargin=self.rm,
                              topMargin=self.tm, bottomMargin=self.bm,
                              title=self.cfg.get("title", ""),
                              author=self.cfg.get("author", ""))

        templates = [
            PageTemplate(id='normal', frames=[body_frame], onPage=self._normal_page),
        ]
        story = []
        has_banner = self.cfg.get("banner") and os.path.exists(self.cfg["banner"])
        has_toc = self.cfg.get("toc", True) and toc

        # Cover
        if self.cfg.get("cover", True):
            templates.insert(0, PageTemplate(id='cover', frames=[full_frame], onPage=self._cover_page))
            story.append(Spacer(1, self.page_h))
            if has_toc:
                templates.append(PageTemplate(id='toc', frames=[body_frame], onPage=self._toc_page))
                story.append(NextPageTemplate('toc'))
            else:
                story.append(NextPageTemplate('normal'))
            story.append(PageBreak())

        # TOC
        if has_toc:
            story.extend(self.build_toc(toc))
            story.append(NextPageTemplate('normal'))
            story.append(PageBreak())

        # Strip leading PageBreak from body
        while story_content and isinstance(story_content[0], (PageBreak, Spacer)):
            if isinstance(story_content[0], PageBreak):
                story_content.pop(0); break
            story_content.pop(0)

        story.extend(story_content)

        # Back cover
        if has_banner:
            templates.append(PageTemplate(id='backcover', frames=[full_frame], onPage=self._backcover_page))
            story.append(NextPageTemplate('backcover'))
            story.append(PageBreak())
            story.append(Spacer(1, 1))

        doc.addPageTemplates(templates)
        print("Building PDF...")
        doc.build(story)
        size = os.path.getsize(output_path)
        print(f"Done! {output_path} ({size/1024/1024:.1f} MB)")
        return size

# ═══════════════════════════════════════════════════════════════════════
# VAULT LINK EXPANSION
# ═══════════════════════════════════════════════════════════════════════

def expand_vault_links(md_text, vault_dir=None):
    """Expand ![[filename]] and [[filename|display]] in list items with file contents from vault.
    For ![[...]]: replace inline with file content.
    For [[...|...]] in list items: replace the list item with file content under the display name as heading."""
    if vault_dir is None:
        return md_text, 0
    vault = os.path.expanduser(vault_dir)
    if not os.path.isdir(vault):
        return md_text, 0

    expanded = 0

    def find_file(target):
        """Find a file in the vault by name (without extension)."""
        filepath = os.path.join(vault, target + ".md")
        if os.path.exists(filepath):
            return filepath
        for root, dirs, files in os.walk(vault):
            if target + ".md" in files:
                return os.path.join(root, target + ".md")
        return None

    def read_note(filepath):
        """Read file and strip frontmatter."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2].strip()
        return content

    def replace_embed(match):
        """Replace ![[target]] with file content."""
        nonlocal expanded
        target = match.group(1).strip()
        if '|' in target:
            target = target.split('|')[0].strip()
        filepath = find_file(target)
        if not filepath:
            return f"\n> [!missing] {target}\n"
        content = read_note(filepath)
        expanded += 1
        return '\n' + content + '\n'

    # First pass: ![[embeds]]
    result = re.sub(r'!\[\[([^\]]+)\]\]', replace_embed, md_text)

    # Second pass: [[wikilinks]] in list items (e.g. MOC format)
    # Pattern: - [[target|display]] or * [[target|display]]
    def replace_wikilink_item(match):
        """Replace a list item with a wikilink by embedding the file content."""
        nonlocal expanded
        indent = match.group(1) or ''
        bullet = match.group(2)
        target = match.group(3).strip()
        display = match.group(4).strip() if match.group(4) else target

        # Skip pending items
        if '[待补充]' in display or '[missing]' in display:
            return match.group(0)

        filepath = find_file(target)
        if not filepath:
            return f"{indent}{bullet} *{display}* （文件缺失）\n"

        content = read_note(filepath)
        expanded += 1
        # Use display name as an H2 heading (triggers chapter page break), then the content
        return f"\n## {display}\n\n{content}\n"

    result = re.sub(
        r'^([ \t]*)([-*])\s*\[\[([^|\]]+)(?:\|([^\]]+))?\]\]',
        replace_wikilink_item,
        result,
        flags=re.MULTILINE
    )

    # Third pass: strip remaining [[wikilinks]] that weren't expanded
    # Pattern: [[target]] or [[target|display]] anywhere in text
    def strip_wikilink(match):
        target = match.group(1).strip()
        display = match.group(2).strip() if match.group(2) else target
        return display
    result = re.sub(r'\[\[([^|\]]+)(?:\|([^\]]+))?\]\]', strip_wikilink, result)

    return result, expanded

# ═══════════════════════════════════════════════════════════════════════
# MARKDOWN CLEANUP (--clean)
# ═══════════════════════════════════════════════════════════════════════

def clean_markdown(md_text):
    """Optional markdown cleanup using markdowncleaner and mdformat.
    Falls back gracefully if libraries are not installed."""
    # Try markdowncleaner
    try:
        import markdowncleaner
        md_text = markdowncleaner.clean(md_text)
        print("  ✓ markdowncleaner applied")
    except ImportError:
        print("  ⚠ markdowncleaner not installed, skipping (pip install markdowncleaner)", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠ markdowncleaner error: {e}, skipping", file=sys.stderr)
    # Try mdformat + gfm
    try:
        import mdformat
        md_text = mdformat.text(md_text, extensions=["gfm"])
        print("  ✓ mdformat + gfm applied")
    except ImportError:
        print("  ⚠ mdformat/mdformat-gfm not installed, skipping (pip install mdformat mdformat-gfm)", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠ mdformat error: {e}, skipping", file=sys.stderr)
    # Extra cleanup: fix headings without spaces, remove HTML noise
    md_text = re.sub(r'^(#{1,6})([^ #\n])', r'\1 \2', md_text, flags=re.MULTILINE)
    md_text = re.sub(r'<\/?[a-zA-Z][^>]*>', '', md_text)  # strip residual HTML tags
    md_text = re.sub(r'\n{3,}', '\n\n', md_text)  # collapse multiple blank lines
    return md_text

# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="md2pdf v3 — Markdown to Professional PDF")
    parser.add_argument("--input", "-i", required=True, help="Input markdown file")
    parser.add_argument("--output", "-o", default="output.pdf", help="Output PDF path")
    parser.add_argument("--title", default="", help="Cover page title")
    parser.add_argument("--subtitle", default="", help="Cover page subtitle")
    parser.add_argument("--author", default="", help="Author name")
    parser.add_argument("--date", default=str(date.today()), help="Date string")
    parser.add_argument("--version", default="", help="Version on cover")
    parser.add_argument("--watermark", default="", help="Watermark text")
    parser.add_argument("--theme", default="chinese-red", help="Theme name")
    parser.add_argument("--toc", default=True, action='store_true', help="Generate TOC")
    parser.add_argument("--no-toc", dest='toc', action='store_false', help="Disable TOC")
    parser.add_argument("--cover", default=True, action='store_true', help="Generate cover")
    parser.add_argument("--no-cover", dest='cover', action='store_false', help="Disable cover")
    parser.add_argument("--clean", action="store_true", help="Clean markdown with markdowncleaner + mdformat")
    parser.add_argument("--vault", default="", help="Obsidian vault dir for ![[link]] expansion")
    parser.add_argument("--header-title", default="", help="Page header title")
    parser.add_argument("--footer-left", default="", help="Footer left text")
    parser.add_argument("--stats-line", default="", help="Cover stats line 1")
    parser.add_argument("--stats-line2", default="", help="Cover stats line 2")
    parser.add_argument("--banner", default="", help="Back cover banner image")
    parser.add_argument("--disclaimer", default="", help="Back cover disclaimer")
    parser.add_argument("--copyright", default="", help="Back cover copyright")
    parser.add_argument("--engine", default="python", choices=["python", "typst"],
                        help="PDF engine: python (reportlab) or typst (default: python)")
    args = parser.parse_args()

    with open(args.input, encoding='utf-8') as f:
        md_text = f.read()

    # Vault link expansion
    if args.vault:
        md_text, expanded = expand_vault_links(md_text, args.vault)
        print(f"Expanded {expanded} vault links")
    else:
        # Auto-detect vault: if input is inside a Zettels/ or vault dir, scan upward
        input_dir = os.path.dirname(os.path.abspath(args.input))
        for candidate in [input_dir, os.path.dirname(input_dir), os.path.dirname(os.path.dirname(input_dir))]:
            if os.path.isdir(os.path.join(candidate, 'Zettels')) or os.path.isdir(os.path.join(candidate, '.obsidian')):
                args.vault = os.path.join(candidate, 'Zettels')
                md_text, expanded = expand_vault_links(md_text, args.vault)
                print(f"Auto-detected vault, expanded {expanded} links")
                break

    # Markdown cleanup
    if args.clean:
        print("Cleaning markdown...")
        md_text = clean_markdown(md_text)

    # Extract title
    title = args.title
    if not title:
        m = re.search(r'^# (.+)$', md_text, re.MULTILINE)
        title = m.group(1).strip() if m else "Document"

    t0 = time.time()

    if args.engine == "typst":
        _run_typst_engine(md_text, args, title)
    else:
        _run_python_engine(md_text, args, title)

    elapsed = time.time() - t0
    print(f"Total time: {elapsed:.1f}s (engine={args.engine})")


def _run_python_engine(md_text, args, title):
    theme = load_theme(args.theme)
    a = theme['accent']
    accent_hex = f"#{int(a.red*255):02x}{int(a.green*255):02x}{int(a.blue*255):02x}"

    config = {
        "title": title,
        "subtitle": args.subtitle,
        "author": args.author,
        "date": args.date,
        "version": args.version,
        "watermark": args.watermark,
        "theme": theme,
        "accent_hex": accent_hex,
        "cover": args.cover,
        "toc": args.toc,
        "page_size": A4,
        "header_title": args.header_title or title,
        "footer_left": args.footer_left or args.author,
        "stats_line": args.stats_line,
        "stats_line2": args.stats_line2,
        "banner": args.banner,
        "disclaimer": args.disclaimer,
        "copyright": args.copyright,
    }

    builder = PDFBuilder(config)
    builder.build(md_text, args.output)


# ═══════════════════════════════════════════════════════════════════════
# TYPST ENGINE
# ═══════════════════════════════════════════════════════════════════════

# Theme color/size mapping from v3 themes → Typst syntax
_TYPST_THEME_MAP = {
    "chinese-red": {
        "accent": "#B22222", "accent_light": "#D44040",
        "ink": "#1A1009", "ink_faded": "#8C7A5E",
        "canvas": "#FFFDF5", "canvas_sec": "#F8F0E0",
        "border": "#E8DCC8",
    },
    "warm-academic": {
        "accent": "#CC785C", "accent_light": "#D99A82",
        "ink": "#181818", "ink_faded": "#87867F",
        "canvas": "#F9F9F7", "canvas_sec": "#F0EEE6",
        "border": "#E8E6DC",
    },
    "nord-frost": {
        "accent": "#5E81AC", "accent_light": "#81A1C1",
        "ink": "#2E3440", "ink_faded": "#4C566A",
        "canvas": "#ECEFF4", "canvas_sec": "#E5E9F0",
        "border": "#D8DEE9",
    },
    "github-light": {
        "accent": "#0969DA", "accent_light": "#218BFF",
        "ink": "#1F2328", "ink_faded": "#656D76",
        "canvas": "#FFFFFF", "canvas_sec": "#F6F8FA",
        "border": "#D0D7DE",
    },
    "paper-classic": {
        "accent": "#CC0000", "accent_light": "#FF3333",
        "ink": "#000000", "ink_faded": "#666666",
        "canvas": "#FFFFFF", "canvas_sec": "#FAFAFA",
        "border": "#DDDDDD",
    },
    "ocean-breeze": {
        "accent": "#2A9D8F", "accent_light": "#64CCBF",
        "ink": "#1A2E35", "ink_faded": "#5A7D7C",
        "canvas": "#F0F7F4", "canvas_sec": "#E0EDE8",
        "border": "#C8DDD6",
    },
    "tufte": {
        "accent": "#980000", "accent_light": "#C04040",
        "ink": "#111111", "ink_faded": "#999988",
        "canvas": "#FFFFF8", "canvas_sec": "#F7F7F0",
        "border": "#E0DDD0",
    },
    "classic-thesis": {
        "accent": "#8B4513", "accent_light": "#A0522D",
        "ink": "#2B2B2B", "ink_faded": "#7A7568",
        "canvas": "#FEFEFE", "canvas_sec": "#F5F2EB",
        "border": "#D6CFC2",
    },
    "elegant-book": {
        "accent": "#5B3A29", "accent_light": "#7D5642",
        "ink": "#1A1A1A", "ink_faded": "#6E6B5E",
        "canvas": "#FBF9F1", "canvas_sec": "#F0ECE0",
        "border": "#DDD8C8",
    },
    "ink-wash": {
        "accent": "#404040", "accent_light": "#666660",
        "ink": "#2C2C2C", "ink_faded": "#8A8A80",
        "canvas": "#F8F6F0", "canvas_sec": "#EEEAE0",
        "border": "#D8D4C8",
    },
    "ieee-journal": {
        "accent": "#003366", "accent_light": "#336699",
        "ink": "#000000", "ink_faded": "#555555",
        "canvas": "#FFFFFF", "canvas_sec": "#F5F5F5",
        "border": "#CCCCCC",
    },
    "textbook-green": {
        "accent": "#2D5F3E", "accent_light": "#4A8C6F",
        "ink": "#1A1009", "ink_faded": "#6B7A6E",
        "canvas": "#FEFEF9", "canvas_sec": "#F8F9F4",
        "border": "#C5D5CD",
    },
    "textbook-cyber": {
        "accent": "#0F969C", "accent_light": "#2CB5BB",
        "ink": "#1A1A2E", "ink_faded": "#5A5A7E",
        "canvas": "#FFFFFF", "canvas_sec": "#F8F9FA",
        "border": "#E2E8F0",
    },
}


def _typst_generate_template(args, title, tc):
    """Generate Typst template string with theme colors and layout.
    All colors wrapped in rgb() for Typst 0.14 compatibility."""
    wm = args.watermark or ""
    cover = args.cover
    toc = args.toc
    header_title = args.header_title or title
    author = args.author
    date_str = args.date
    subtitle = args.subtitle

    # Helper: color string → Typst rgb() call
    def c(hex_color):
        return f'rgb("{hex_color}")'

    lines = []
    lines.append("""#set page(
  paper: "a4",
  margin: (top: 25mm, bottom: 25mm, left: 28mm, right: 25mm),
)""")

    # Text & paragraph
    lines.append("""#set text(
  font: ("Songti SC", "STSong", "New Computer Modern", "Times New Roman"),
  size: 11pt,
  lang: "zh",
)""")
    lines.append("""#set par(
  justify: true,
  first-line-indent: 2em,
  leading: 1.6em,
  spacing: 0.6em,
)""")
    lines.append("""#set heading(numbering: none)""")

    # Heading styling
    lines.append(f"""#show heading.where(level: 1): it => {{
  set text(size: 28pt, font: ("STHeiti", "Heiti SC", "PingFang SC"), weight: "bold")
  set block(above: 20mm, below: 6mm)
  align(center, {{
    it
    v(-2mm)
    line(length: 40%, stroke: 0.8pt + {c(tc['accent'])})
  }})
}}""")
    lines.append(f"""#show heading.where(level: 2): it => {{
  set text(size: 20pt, font: ("STHeiti", "Heiti SC", "PingFang SC"), weight: "bold")
  set block(above: 14mm, below: 5mm)
  pagebreak(weak: true)
  align(center, {{
    it
    v(-2mm)
    line(length: 35%, stroke: 1.0pt + {c(tc['accent'])})
  }})
}}""")
    lines.append(f"""#show heading.where(level: 3): it => {{
  set text(size: 12pt, font: ("STHeiti", "Heiti SC"), weight: "bold")
  set text(fill: {c(tc['accent'])})
  set block(above: 5mm, below: 3mm)
  it
}}""")

    # Header & Footer
    lines.append(f"""#set page(header: context {{
  if counter(page).get().first() > 1 {{
    line(length: 100%, stroke: 0.4pt + {c(tc['border'])})
    v(-6mm)
    grid(
      columns: (1fr, 1fr),
      align(left, text(size: 8pt, fill: {c(tc['ink_faded'])}, "{header_title}")),
      align(right, text(size: 8pt, fill: {c(tc['ink_faded'])}, context {{
        let sel = query(heading.where(level: 1))
        if sel.len() > 0 {{ sel.last().body }}
      }})),
    )
  }}
}})""")
    lines.append(f"""#set page(footer: context {{
  line(length: 100%, stroke: 0.4pt + {c(tc['border'])})
  v(4mm)
  grid(
    columns: (1fr, 1fr, 1fr),
    align(left, text(size: 8pt, fill: {c(tc['ink_faded'])}, "{author}")),
    align(center, text(size: 9pt, fill: {c(tc['accent'])}, weight: "bold", {{ "—  " + str(counter(page).display()) + "  —" }})),
    align(right, text(size: 8pt, fill: {c(tc['ink_faded'])}, "{date_str}")),
  )
}})""")

    # Cover page
    if cover:
        lines.append("""#set page(margin: 0pt)""")
        lines.append(f"""#set text(fill: {c(tc['ink'])})""")
        lines.append(f"""
#block(
  height: 100%,
  width: 100%,
  fill: {c(tc['canvas'])},
  {{
    // Top accent bar
    rect(width: 100%, height: 3mm, fill: {c(tc['accent'])})
    v(1fr)
    align(center, {{
      text(size: 38pt, font: ("STHeiti", "Heiti SC"), weight: "bold", "{title}")
    }})
""")
        if subtitle:
            lines.append(f"""    v(8mm)
    align(center, text(size: 20pt, fill: {c(tc['ink_faded'])}, font: ("Songti SC", "STSong"), "{subtitle}"))""")
        lines.append(f"""    v(8mm)
    align(center, line(length: 34mm, stroke: 1.5pt + {c(tc['accent'])}))
""")
        if author:
            lines.append(f"""    v(30mm)
    align(center, text(size: 10pt, fill: {c(tc['ink_faded'])}, font: ("Songti SC", "STSong"), "{author}"))""")
        lines.append(f"""    v(6mm)
    align(center, text(size: 9pt, fill: {c(tc['ink_faded'])}, font: ("Songti SC", "STSong"), "{date_str}"))
    v(1fr)
    // Bottom accent bar
    rect(width: 100%, height: 3mm, fill: {c(tc['accent'])})
  }}
)
""")
        # Reset page margins after cover
        lines.append("""#set page(margin: (top: 25mm, bottom: 25mm, left: 28mm, right: 25mm))""")
        # Re-apply watermark on body pages
        if wm:
            lines.append(f"""#set page(background: {{
  place(dx: 20%, dy: 25%, text(size: 42pt, fill: luma(215), weight: "bold", rotate(35deg, "{wm}")))
  place(dx: 60%, dy: 45%, text(size: 42pt, fill: luma(215), weight: "bold", rotate(35deg, "{wm}")))
  place(dx: 35%, dy: 65%, text(size: 42pt, fill: luma(215), weight: "bold", rotate(35deg, "{wm}")))
  place(dx: 70%, dy: 20%, text(size: 42pt, fill: luma(215), weight: "bold", rotate(35deg, "{wm}")))
  place(dx: 10%, dy: 55%, text(size: 42pt, fill: luma(215), weight: "bold", rotate(35deg, "{wm}")))
  place(dx: 50%, dy: 80%, text(size: 42pt, fill: luma(215), weight: "bold", rotate(35deg, "{wm}")))
}})""")

    # TOC
    if toc:
        lines.append(f"""
#pagebreak()
#set par(first-line-indent: 0em)
#heading(outlined: false)[目    录]
#line(length: 12%, stroke: 1pt + {c(tc['accent'])})
#v(8mm)
#outline(title: none, depth: 3, indent: 2em)
#set par(first-line-indent: 2em)
#pagebreak()
""")

    return '\n'.join(lines)


def _run_typst_engine(md_text, args, title):
    """Typst engine: md → pandoc → .typ → inject template → typst compile → PDF."""
    # Check dependencies
    for cmd in ['pandoc', 'typst']:
        if not shutil.which(cmd):
            print(f"Error: '{cmd}' not found. Please install it first.", file=sys.stderr)
            sys.exit(1)

    # Get theme colors
    tc = _TYPST_THEME_MAP.get(args.theme, _TYPST_THEME_MAP["chinese-red"])

    # Step 1: Preprocess markdown for pandoc (strip YAML frontmatter)
    lines = md_text.split('\n')
    if lines and lines[0].strip() == '---':
        for idx in range(1, len(lines)):
            if lines[idx].strip() == '---':
                lines = lines[idx+1:]
                break
    md_clean = '\n'.join(lines)

    # Step 2: pandoc md → typst
    print("Converting markdown → Typst via pandoc...")
    result = subprocess.run(
        ['pandoc', '--from', 'markdown', '--to', 'typst', '--wrap=none'],
        input=md_clean.encode('utf-8'),
        capture_output=True, timeout=60
    )
    if result.returncode != 0:
        print(f"pandoc error: {result.stderr.decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    typst_body = result.stdout.decode('utf-8')

    # Step 2.5: Post-process pandoc output for Typst 0.14 compat
    typst_body = typst_body.replace('#horizontalrule', '#line(length: 100%)')
    # Fix stray --- inside body (not frontmatter)
    typst_body = re.sub(r'^---\s*$', '', typst_body, flags=re.MULTILINE)

    # Step 3: Generate template + combine
    print("Generating Typst template...")
    template = _typst_generate_template(args, title, tc)
    full_typ = template + '\n' + typst_body

    # Step 4: Write to temp file and compile
    tmpdir = tempfile.mkdtemp(prefix='md2pdf_typst_')
    typ_path = os.path.join(tmpdir, 'output.typ')
    try:
        with open(typ_path, 'w', encoding='utf-8') as f:
            f.write(full_typ)

        print(f"Compiling with Typst...")
        result = subprocess.run(
            ['typst', 'compile', typ_path, args.output],
            capture_output=True, timeout=120
        )
        if result.returncode != 0:
            print(f"Typst compile error:\n{result.stderr.decode('utf-8')}", file=sys.stderr)
            sys.exit(1)

        size = os.path.getsize(args.output)
        print(f"Done! {args.output} ({size/1024/1024:.1f} MB)")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
