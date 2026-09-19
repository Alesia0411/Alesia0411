"""Small, dependency-free SVG components for a GitHub-compatible profile.

Renderers return (SVG fragment, height). They measure wrapped text before placing
the next element, so new entries grow the cards rather than clipping content.
"""
from __future__ import annotations

import html
import math
import random
import re
import unicodedata


def esc(value):
    return html.escape(str(value), quote=True)


def text_width(value, size):
    return round(sum(0 if unicodedata.combining(c) else
               (1.04 if unicodedata.east_asian_width(c) in "WF" else .66)
               for c in str(value)) * size, 3)


def wrap(value, width, size):
    """Conservative Unicode wrapping; explicit newlines are preserved."""
    result = []
    for paragraph in str(value).split("\n"):
        line = ""
        for char in paragraph:
            if line and text_width(line + char, size) > width:
                result.append(line.rstrip())
                line = ""
            line += char
        result.append(line.rstrip())
    return result or [""]


class Canvas:
    def __init__(self, theme):
        self.t = theme
        self.parts = []

    def add(self, svg):
        self.parts.append(svg)

    def rect(self, x, y, w, h, fill="none", stroke="none", radius=0):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')

    def line(self, x1, y1, x2, y2, color=None, opacity=1):
        self.add(f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{color or self.t["border"]}" opacity="{opacity}" fill="none"/>')

    def text(self, value, x, y, size=20, color=None, weight=400, serif=False, spacing=0):
        family = "Georgia, Songti SC, SimSun, serif" if serif else "Segoe UI, PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif"
        self.add(f'<text x="{x}" y="{y}" fill="{color or self.t["ink"]}" font-family="{family}" font-size="{size}" font-weight="{weight}" letter-spacing="{spacing}">{esc(value)}</text>')

    def paragraph(self, value, x, y, width, size=20, color=None, weight=400):
        for line in wrap(value, width, size):
            self.text(line, x, y + size, size, color, weight)
            y += size * 1.55
        return y

    def star(self, x, y, r=8, color=None):
        color = color or self.t["gold"]
        self.add(f'<path d="M{x} {y-r}L{x+r*.23} {y-r*.23}L{x+r} {y}L{x+r*.23} {y+r*.23}L{x} {y+r}L{x-r*.23} {y+r*.23}L{x-r} {y}L{x-r*.23} {y-r*.23}Z" fill="{color}"/>')

    def compass(self, x, y, r, color=None):
        color = color or self.t["gold"]
        self.add(f'<g fill="none" stroke="{color}" stroke-width="1.2"><circle cx="{x}" cy="{y}" r="{r}"/><circle cx="{x}" cy="{y}" r="{r*.77}"/><path d="M{x-r*1.15} {y}H{x+r*1.15}M{x} {y-r*1.15}V{y+r*1.15}"/></g>')
        self.star(x, y, r*.68, color)
        for angle in (45, 135, 225, 315):
            theta = math.radians(angle)
            self.star(x + math.cos(theta)*r, y + math.sin(theta)*r, 4, color)

    def frame(self, w, h):
        self.rect(1, 1, w-2, h-2, "url(#paper)", self.t["border"], 3)
        self.rect(7, 7, w-14, h-14, "none", self.t["border"], 2)
        for x, y, sx, sy in ((12, 12, 1, 1), (w-12, 12, -1, 1),
                              (12, h-12, 1, -1), (w-12, h-12, -1, -1)):
            self.add(f'<path d="M{x} {y+sy*24}V{y}H{x+sx*24}M{x} {y+sy*12}L{x+sx*12} {y}" fill="none" stroke="{self.t["gold"]}"/>')
            self.star(x+sx*4, y+sy*4, 3)

    def header(self, data, w, size):
        self.compass(34, 36, 11)
        self.text(data["title"], 57, 44, size+6, weight=600, serif=True)
        self.text(data.get("subtitle", ""), 27, 72, 11, self.t["gold"], spacing=1.6)
        self.line(27, 88, w-27, 88)
        self.star(w-30, 36, 5)

    def tags(self, values, x, y, width, size=16):
        start = x
        for value in values:
            lines = wrap(value, max(20, width-24), size)
            for line in lines:
                tw = min(width, text_width(line, size)+24)
                if x > start and x+tw > start+width:
                    x = start
                    y += size+22
                self.rect(x, y, tw, size+14, "#fffdf7", self.t["border"], 6)
                self.text(line, x+12, y+size+3, size)
                x += tw+9
        return y+size+14

    def svg(self):
        return "".join(self.parts)


def facts(c, data, w, size):
    y = 106
    label_w = min(142, w*.29)
    for item in data["items"]:
        c.star(31, y+size*.65, 3)
        label_end = c.paragraph(item["label"], 45, y, label_w-38, size-2, c.t["muted"])
        value_end = c.paragraph(item["value"], label_w+22, y, w-label_w-52, size)
        y = max(label_end, value_end)+14
        c.line(29, y-4, w-29, y-4, opacity=.43)
    return y


def skills(c, data, w, size):
    y = 105
    for group in data["groups"]:
        label_end = c.paragraph(group["label"], 29, y+2, 117, size-2, c.t["muted"])
        tag_end = c.tags(group["tags"], 155, y, w-184, size-2)
        y = max(label_end, tag_end)+23
        c.line(29, y-10, w-29, y-10, opacity=.4)
    return y


def timeline(c, data, w, size):
    y = 105
    for item in data["items"]:
        c.star(32, y+12, 5)
        start = y
        y = c.paragraph(item["date"], 52, y, w-82, size-4, c.t["gold"])+6
        y = c.paragraph(item["title"], 52, y, w-82, size, weight=600)+5
        y = c.paragraph(item["body"], 52, y, w-82, size-2, c.t["muted"])+23
        c.line(32, start+23, 32, y-10, opacity=.65)
    return y


def links(c, data, w, size):
    return c.tags([i["label"] + (" ↗" if i.get("url") else " · 待填写")
                   for i in data["items"]], 29, 109, w-58, size-1)+14


def tiles(c, data, w, size):
    mobile = w <= 520
    columns = 1 if mobile else data.get("columns", 2)
    gap, outer = 16, 23
    tile_w = (w-outer*2-gap*(columns-1))/columns
    y = 105
    for start in range(0, len(data["items"]), columns):
        rendered = []
        for index, item in enumerate(data["items"][start:start+columns]):
            tile = Canvas(c.t)
            inner_w = tile_w-40
            kind = data["type"]
            ty = 23
            if kind == "games":
                accent = item.get("accent", c.t["gold"])
                tile.compass(tile_w/2, 58, 28, accent)
                ty = 104
            elif kind == "projects":
                tile.rect(1, 1, tile_w-2, 80, c.t["navy"], radius=4)
                tile.compass(tile_w-46, 40, 23, "#d6bd83")
                tile.text(f'ARCHIVE / {start+index+1:02d}', 20, 45, 13, "#e5d6b5", spacing=2)
                ty = 103
            else:
                tile.star(27, 30, 8)
                tile.text(item.get("label", ""), 45, 35, 11, c.t["gold"], spacing=1)
                ty = 52
            ty = tile.paragraph(item["title"], 20, ty, inner_w, size+2, weight=600)+12
            if kind == "games":
                for label, key in (("服务器", "server"), ("UID", "uid"), ("游玩状态", "status")):
                    ty = tile.paragraph(f'{label}：{item[key]}', 20, ty, inner_w, size-2, c.t["muted"])+5
            else:
                ty = tile.paragraph(item["body"], 20, ty, inner_w, size-1, c.t["muted"])+10
                if kind == "projects":
                    ty = tile.paragraph('我的贡献 / '+item["contribution"], 20, ty, inner_w, size-2, c.t["muted"])+12
                    ty = tile.tags(item.get("tags", []), 20, ty, inner_w, size-4)+12
            rendered.append((tile.svg(), ty+17))
        height = max(h for _, h in rendered)
        for index, (body, _) in enumerate(rendered):
            x = outer+index*(tile_w+gap)
            c.rect(x, y, tile_w, height, "#fffdf7", c.t["border"], 4)
            c.add(f'<g transform="translate({x},{y})">{body}</g>')
        y += height+gap
    return y


RENDERERS = {
    "facts": facts, "skills": skills, "timeline": timeline,
    "cards": tiles, "projects": tiles, "games": tiles, "links": links,
}


def module(data, w, theme, min_height=0):
    size = 21 if w <= 520 else 22
    content = Canvas(theme)
    content.header(data, w, size)
    y = RENDERERS[data["type"]](content, data, w, size)
    if data.get("note"):
        y = content.paragraph(data["note"], 29, y+5, w-58, size-3, theme["gold"])+12
    height = max(math.ceil(y+15), min_height)
    frame = Canvas(theme)
    frame.frame(w, height)
    return frame.svg()+content.svg(), height


def hero(profile, w):
    c = Canvas(profile["theme"])
    mobile = w <= 520
    left, content_width = (30, w-60) if mobile else (50, w-350)
    title_size = 40 if mobile else 52
    y = 65 if mobile else 76
    y = c.paragraph(profile["title"], left, y, content_width, title_size, "#f6ead1", 600)+6
    c.text(profile["subtitle"], left, y+13, 12 if mobile else 15, "#decdac", spacing=2)
    y += 42
    y = c.paragraph('你好，我是 '+profile["name"], left, y, content_width, 27, "#faf4e6", 600)+10
    y = c.paragraph(profile["bio"], left, y, content_width, 19, "#d6dce6")+30
    quote_lines = wrap(profile["motto"], w-100, 21)
    height = math.ceil(y+len(quote_lines)*33+53)
    bg = Canvas(profile["theme"])
    bg.rect(0, 0, w, height, "url(#sky)", radius=4)
    rng = random.Random(411)
    for _ in range(130 if not mobile else 65):
        x, sy = rng.uniform(15,w-15), rng.uniform(10,height-60)
        bg.add(f'<circle cx="{x:.1f}" cy="{sy:.1f}" r="{rng.uniform(.5,1.6):.1f}" fill="#eadcbf" opacity="{rng.uniform(.15,.6):.2f}"/>')
    bg.add(f'<path d="M0 {height-55} Q{w*.13} {height-155} {w*.32} {height-61} T{w*.65} {height-68}T{w} {height-100}V{height}H0Z" fill="#8893a1" opacity=".17"/>')
    bg.add(f'<path d="M0 {height-33}Q{w*.2} {height-96} {w*.4} {height-30}T{w} {height-50}V{height}H0Z" fill="#f0e6d2" opacity=".16"/>')
    bg.rect(8, 8, w-16, height-16, "none", "#a99162", 3)
    bg.rect(14, 14, w-28, height-28, "none", "#6e6d69", 2)
    for x in (22, w-22):
        for sy in (22, height-22):
            bg.star(x, sy, 7, "#ddc796")
    if not mobile:
        bg.compass(w-160, (height-70)/2, 84, "#d6bd83")
        bg.line(w-250, 56, w-97, 90, "#d6bd83", .4)
        bg.star(w-250, 56, 5, "#eadbb8")
    bg.rect(32, y-2, w-64, len(quote_lines)*33+20, "#f4ebd8", "#bfa775", 3)
    c.paragraph(profile["motto"], 50, y+5, w-100, 21, "#625037")
    return bg.svg()+c.svg(), height


def document(fragment, w, h, title, theme):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title">
<title id="title">{esc(title)}</title>
<defs>
  <linearGradient id="paper" x2="1" y2="1"><stop stop-color="{theme['paper']}"/><stop offset=".65" stop-color="#fffdf8"/><stop offset="1" stop-color="{theme['paper_deep']}"/></linearGradient>
  <linearGradient id="sky" x2="1" y2="1"><stop stop-color="#101e35"/><stop offset=".55" stop-color="{theme['navy']}"/><stop offset="1" stop-color="#36465e"/></linearGradient>
</defs>{fragment}</svg>\n'''


def avatar(theme):
    c = Canvas(theme)
    c.rect(0, 0, 400, 400, "url(#sky)", radius=200)
    rng = random.Random(411)
    for _ in range(75):
        x, y = rng.uniform(30, 370), rng.uniform(30, 370)
        if math.hypot(x-200,y-200) < 185:
            c.star(x, y, rng.uniform(1, 3), "#dac496")
    c.compass(200, 200, 124, "#d6bd83")
    return document(c.svg(), 400, 400, "星空罗盘 · 可选头像", theme)
