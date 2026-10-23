# -*- coding: utf-8 -*-
"""產生 docs/BACKPACK_V2_PCB_OUTLINE.svg：SuperMini 背面視圖上的背板位置與接點。

執行：python gen_outline.py
座標：SuperMini 背面、USB 朝上、板子左上角為原點，單位 mm（排針與 USB-C 固定腳位置為 2026-10-23 實板照片推算）。
"""
import os

import geom as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "docs", "BACKPACK_V2_PCB_OUTLINE.svg")

S = 30                      # px / mm
MX, MY = 170, 90            # 圖面左上留白
SM_W, SM_H = 18.0, 22.5
ROW_X = (1.38, 16.62)
PIN_Y0, PITCH = 1.4, 2.54
LEFT = ["5V", "G", "3.3", "4", "3", "2", "1", "0"]
RIGHT = ["5", "6", "7", "8", "9", "10", "20", "21"]
USB_LEGS = [(4.7, 1.0), (13.3, 1.0), (4.7, 5.2), (13.3, 5.2)]

# 背板接點（背板座標）→ 名稱、接到哪裡
PADS = {
    "P1": (0.7, 0.9, "5V", "5V"),
    "P2": (0.7, 3.4, "G", "G"),
    "P3": (0.7, B.BH - 2.3, "IO1", "1"),
    "P4": (0.7, B.BH - 0.8, "IO0", "0"),
    "P5": (B.BW - 0.7, 0.9, "VSYS", None),
    "P6": (B.BW - 0.7, B.BH - 2.3, "B+", None),
    "P7": (B.BW - 0.7, B.BH - 0.8, "B-", None),
}


def X(x):
    return MX + x * S


def Y(y):
    return MY + y * S


out = []


def add(s):
    out.append(s)


def text(x, y, s, size=13, anchor="middle", color="#222", bold=False):
    w = ' font-weight="bold"' if bold else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{color}"{w}>{s}</text>')


def dim_h(x0, x1, y, label, color):
    add(f'<line x1="{X(x0):.1f}" y1="{Y(y):.1f}" x2="{X(x1):.1f}" y2="{Y(y):.1f}" stroke="{color}" stroke-width="1" '
        f'marker-start="url(#a)" marker-end="url(#a)"/>')
    text((X(x0) + X(x1)) / 2, Y(y) - 5, label, 12, color=color)


def dim_v(y0, y1, x, label, color):
    add(f'<line x1="{X(x):.1f}" y1="{Y(y0):.1f}" x2="{X(x):.1f}" y2="{Y(y1):.1f}" stroke="{color}" stroke-width="1" '
        f'marker-start="url(#a)" marker-end="url(#a)"/>')
    cx, cy = X(x) - 6, (Y(y0) + Y(y1)) / 2
    add(f'<text x="{cx:.1f}" y="{cy:.1f}" font-size="12" text-anchor="middle" fill="{color}" '
        f'transform="rotate(-90 {cx:.1f} {cy:.1f})">{label}</text>')


W = int(X(SM_W) + 330)
H = int(Y(SM_H) + 70)
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="Microsoft JhengHei, PingFang TC, Noto Sans CJK TC, sans-serif">')
add('<defs><marker id="a" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
    '<path d="M0,2 L10,5 L0,8 z" fill="context-stroke"/></marker></defs>')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
text(W / 2, 30, f"電池背板 v2.1 外形與位置（{B.BW:g} × {B.BH:g} mm、{B.THICKNESS:g} mm FR4）— SuperMini 背面視圖，USB 朝上", 19, bold=True)
text(W / 2, 54, "座標原點 = SuperMini 背面左上角（mm）；灰色 = SuperMini（排針、USB-C 固定腳依實板照片推算）；藍色 = 背板", 13, color="#555")

# SuperMini
add(f'<rect x="{X(4.4):.1f}" y="{Y(-1.2):.1f}" width="{9.2 * S:.1f}" height="{1.4 * S:.1f}" rx="6" fill="#ddd" stroke="#999"/>')
text(X(9), Y(-0.25), "USB-C", 12, color="#777")
add(f'<rect x="{X(0)}" y="{Y(0)}" width="{SM_W * S}" height="{SM_H * S}" rx="8" fill="#f2f2f2" stroke="#888" stroke-width="1.5"/>')
add(f'<rect x="{X(0)}" y="{Y(SM_H - 3):.1f}" width="{SM_W * S}" height="{3 * S}" fill="#fde9e9" stroke="none"/>')
text(X(9), Y(SM_H - 1.3), "天線區（電池盡量不要蓋到）", 12, color="#b55")
for cx, cy in USB_LEGS:
    add(f'<rect x="{X(cx - 0.55):.1f}" y="{Y(cy - 0.8):.1f}" width="{1.1 * S:.1f}" height="{1.6 * S:.1f}" rx="15" '
        'fill="#e8e8e8" stroke="#aaa" stroke-dasharray="3 2"/>')
for i in range(8):
    y = PIN_Y0 + i * PITCH
    for x, names, anchor, dx in ((ROW_X[0], LEFT, "end", -26), (ROW_X[1], RIGHT, "start", 26)):
        add(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{0.75 * S:.1f}" fill="#d9c27a" stroke="#a88f3e"/>')
        text(X(x) + dx * 1.6, Y(y) + 5, names[i], 14, anchor, "#666")

# 背板
bx, by = B.SM_X, B.SM_Y
add(f'<rect x="{X(bx):.1f}" y="{Y(by):.1f}" width="{B.BW * S:.1f}" height="{B.BH * S:.1f}" fill="#dbe9fb" '
    'stroke="#1f5fbf" stroke-width="2.5" fill-opacity="0.85"/>')
text(X(bx + B.BW / 2), Y(by + B.BH / 2) - 4, "背板（零件面朝外）", 15, color="#1f5fbf", bold=True)
text(X(bx + B.BW / 2), Y(by + B.BH / 2) + 16, "無缺口、無挖孔", 12, color="#1f5fbf")
for ref, (px, py, name, pin) in PADS.items():
    x, y = bx + px, by + py
    add(f'<rect x="{X(x - 0.35):.1f}" y="{Y(y - 0.5):.1f}" width="{0.7 * S:.1f}" height="{1.0 * S:.1f}" rx="2" '
        'fill="#c87533" stroke="#7a4410"/>')
    right = px > B.BW / 2
    text(X(x) + (-16 if right else 16), Y(y) + 4, f"{ref} {name}", 11, "end" if right else "start", "#7a4410")
    if pin is not None:
        hy = PIN_Y0 + LEFT.index(pin) * PITCH
        add(f'<line x1="{X(x):.1f}" y1="{Y(y):.1f}" x2="{X(ROW_X[0]):.1f}" y2="{Y(hy):.1f}" stroke="#c0392b" '
            'stroke-width="1.6" stroke-dasharray="5 3"/>')

# 尺寸
dim_h(0, bx, by + B.BH + 1.2, f"{bx:g}", "#1f5fbf")
dim_h(bx, bx + B.BW, by + B.BH + 1.2, f"{B.BW:g}", "#1f5fbf")
dim_v(0, by, bx - 0.6, f"{by:g}", "#1f5fbf")
dim_v(by, by + B.BH, -3.2, f"{B.BH:g}", "#1f5fbf")
dim_h(0, SM_W, SM_H + 1.2, f"{SM_W:g}（SuperMini）", "#888")
dim_v(0, SM_H, SM_W + 3.2, f"{SM_H:g}（SuperMini）", "#888")

# 圖例
lx, ly = X(SM_W) + 130, Y(1)
for i, (sw, label) in enumerate([
        ('<rect width="16" height="16" fill="#dbe9fb" stroke="#1f5fbf" stroke-width="2"/>', "背板外形"),
        ('<rect x="4" width="8" height="16" rx="2" fill="#c87533"/>', "背板接點 0.7 × 1.0"),
        ('<line x1="0" y1="8" x2="16" y2="8" stroke="#c0392b" stroke-width="2" stroke-dasharray="5 3"/>', "跳線到排針焊墊"),
        ('<circle cx="8" cy="8" r="8" fill="#d9c27a"/>', "SuperMini 排針焊墊"),
        ('<rect x="3" width="10" height="16" rx="5" fill="#e8e8e8" stroke="#aaa" stroke-dasharray="3 2"/>', "USB-C 固定腳（平的）")]):
    add(f'<g transform="translate({lx - 40:.1f},{ly + i * 30 - 12:.1f})">{sw}</g>')
    text(lx - 16, ly + i * 30, label, 12, "start")
text(lx - 40, ly + 170, "P5 VSYS：飛線繞到正面 W5 的 A 端", 12, "start", "#7a4410")
text(lx - 40, ly + 192, "P6 / P7：電池 pigtail → J1", 12, "start", "#7a4410")
add("</svg>")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print("saved", os.path.normpath(OUT))
