# -*- coding: utf-8 -*-
"""從 C3_Battery_Backpack.kicad_pcb 產生手焊組裝圖 ASSEMBLY.svg（零件面、零件編號、數值、Pin 1）。

執行："D:\\Program Files\\KiCad\\bin\\python.exe" gen_assembly.py
"""
import os

import pcbnew

import geom as B

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "C3_Battery_Backpack.kicad_pcb")
OUT = os.path.join(HERE, "ASSEMBLY.svg")

S = 60                          # px / mm
MX, MY = 150, 110
EDGE_NAME = {"P1": "5V", "P2": "G", "P3": "IO1", "P4": "IO0", "P5": "VSYS", "P6": "B+", "P7": "B-"}
EDGE_TO = {"P1": "→ 5V 排針", "P2": "→ G 排針", "P3": "→ GPIO1", "P4": "→ GPIO0",
           "P5": "→ W5 A 端", "P6": "→ 電池 +", "P7": "→ 電池 −"}
PIN_NAME = {"Q1": {"1": "G", "2": "S", "3": "D"}}
BODY = {"U1": "#e3e3e3", "Q1": "#e3e3e3"}
CAP = "#f4e3c4"
RES = "#d6e4f5"


def X(x):
    return MX + x * S


def Y(y):
    return MY + y * S


board = pcbnew.LoadBoard(PCB)
out = []
add = out.append


def text(x, y, s, size, color="#222", anchor="middle", bold=False, rot=0):
    w = ' font-weight="bold"' if bold else ""
    t = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" dominant-baseline="central" '
        f'fill="{color}"{w}{t}>{s}</text>')


def mm_xy(v):
    return pcbnew.ToMM(v.x) - B.OX, pcbnew.ToMM(v.y) - B.OY


W, H = int(X(B.BW) + 190), int(Y(B.BH) + 130)
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="Microsoft JhengHei, PingFang TC, Noto Sans CJK TC, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#fff"/>')
text(W / 2, 32, "電池背板 v2.1 手焊組裝圖（零件面朝上，「5V」在左上 = USB 端）", 22, bold=True)
text(W / 2, 64, f"{B.BW:g} × {B.BH:g} mm；▲ / ● = Pin 1；藍 = 電阻、米色 = 陶瓷電容（無極性）", 15, "#555")
add(f'<rect x="{X(0)}" y="{Y(0)}" width="{B.BW * S}" height="{B.BH * S}" rx="6" fill="#2f6b3a" stroke="#1d4425" stroke-width="3"/>')

for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
    ref, val = fp.GetReference(), fp.GetValue()
    cx, cy = mm_xy(fp.GetPosition())
    pads = list(fp.Pads())
    for p in pads:
        bb = p.GetBoundingBox()
        x0, y0 = mm_xy(bb.GetOrigin())
        w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
        add(f'<rect x="{X(x0):.1f}" y="{Y(y0):.1f}" width="{w * S:.1f}" height="{h * S:.1f}" rx="4" '
            'fill="#d9d9d9" stroke="#8a8a8a" stroke-width="1.5"/>')
    if ref.startswith("P"):
        right = cx > B.BW / 2
        text(X(cx), Y(cy), ref, 15, "#333", bold=True)
        lx = X(B.BW) + 14 if right else X(0) - 14
        anchor = "start" if right else "end"
        text(lx, Y(cy) - 10, EDGE_NAME[ref], 17, "#b35c00", anchor, bold=True)
        text(lx, Y(cy) + 12, EDGE_TO[ref], 12, "#666", anchor)
        continue

    # 本體：以焊盤範圍為準，兩端各縮一點，蓋在焊盤之間
    bb = fp.GetBoundingBox(False)
    x0, y0 = mm_xy(bb.GetOrigin())
    w, h = pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())
    vertical = h > w
    if ref in BODY:
        bw, bh = (1.5, 2.9) if fp.GetOrientationDegrees() % 180 == 0 else (2.9, 1.5)
        if ref == "Q1":
            bw, bh = 1.3, 2.9
        if ref == "U1":
            bw, bh = 1.6, 2.9
        fill = BODY[ref]
    else:
        L = max(w, h) * 0.42
        bw, bh = (1.0, L) if vertical else (L, 1.0)
        fill = CAP if ref.startswith("C") else RES
    add(f'<rect x="{X(cx - bw / 2):.1f}" y="{Y(cy - bh / 2):.1f}" width="{bw * S:.1f}" height="{bh * S:.1f}" rx="5" '
        f'fill="{fill}" stroke="#333" stroke-width="2"/>')

    if ref in BODY:
        text(X(cx), Y(cy) - 14, ref, 22, "#000", bold=True)
        text(X(cx), Y(cy) + 14, val.split(" ")[0], 13, "#333")
        for p in pads:
            px, py = mm_xy(p.GetPosition())
            n = p.GetNumber()
            label = PIN_NAME.get(ref, {}).get(n, n)
            text(X(px), Y(py), label, 15, "#c00000" if n == "1" else "#333", bold=True)
            if n == "1":
                dx = 1 if px > cx else -1
                add(f'<circle cx="{X(cx + dx * (bw / 2 - 0.3)):.1f}" cy="{Y(py):.1f}" r="7" fill="#c00000"/>')
    else:
        rot = -90 if vertical else 0
        if vertical:
            text(X(cx) - 7, Y(cy), ref, 17, "#000", bold=True, rot=rot)
            text(X(cx) + 12, Y(cy), val, 12, "#333", rot=rot)
        else:
            text(X(cx), Y(cy) - 8, ref, 17, "#000", bold=True)
            text(X(cx), Y(cy) + 11, val, 12, "#333")

# 說明
ly = Y(B.BH) + 40
text(X(0), ly, "U1 TP4054：3 支腳那排朝右，Pin 1（CHRG）在右下", 14, "#222", "start")
text(X(0), ly + 24, "Q1 AO3401：單腳 D 朝左，Pin 1（G）在右下，S 在右上", 14, "#222", "start")
text(X(0), ly + 48, "背面印「SUPERMINI SIDE」，貼 SuperMini 背面", 14, "#222", "start")
add("</svg>")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print("saved", OUT, W, H)
