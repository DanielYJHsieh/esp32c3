# -*- coding: utf-8 -*-
"""用 KiCad pcbnew API 產生 24pin 電子紙轉接小板（DESPI-C02 縮小版，排線接 MCU）。

執行：  "D:\Program Files\KiCad\bin\python.exe" build_pcb.py [--route]
座標：  從零件面（F 面）看，FPC 座在上緣為 (0, 0)，X 往右、Y 往下，單位 mm；實際放在 (OX, OY) 位移後的位置。
電路：  照 Good Display DESPI-C02 原理圖（SCH V1.0）；RESE 固定 0.47Ω、BS 直接接地（4 線 SPI）。
        跟 ../../EPD24_SuperMini_Adapter_HW v1.0 的 e-paper 電路相同，只把 Super Mini 排針換成排線焊點。
接頭：  J2 1x8 穿孔焊點（2.0mm 間距），排線直接焊；腳位順序同 DESPI-C02 的 8pin：
        1 3.3V、2 GND、3 SDI、4 SCLK、5 CS、6 D/C、7 RES、8 BUSY。
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
FPLIB = r"D:\Program Files\KiCad\share\kicad\footprints"
OUT = os.path.join(HERE, "EPD24_Mini_Adapter.kicad_pcb")

OX, OY = 100.0, 100.0          # 板子左上角在 KiCad 頁面上的位置
BW, BH = 18.0, 19.9            # 寬由 24P FPC 座決定；長 = FPC 座 + 零件 + 排線焊點

board = pcbnew.BOARD()
nets = {}


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]


_io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)


def fp_lib(lib, name):
    return _io.FootprintLoad(os.path.join(FPLIB, lib + ".pretty"), name)


def place(fp, ref, value, x, y, rot=0.0):
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(pt(x, y))
    fp.SetOrientationDegrees(rot)
    board.Add(fp)
    return fp


fps = {}

# ---------------------------------------------------------------- 接頭
# J1：24P 0.5mm 翻蓋 FPC 座，轉 180° 讓排線從上緣插入；pin 1 在右邊
fps["J1"] = place(fp_lib("Connector_FFC-FPC", "Jushuo_AFC07-S24FCA-00_1x24-1MP_P0.50_Horizontal"),
                  "J1", "AFC07-S24FCA-00", 9.0, 4.2, 180)
# J2：1x8 穿孔焊點，間距 2.0mm，排線直接焊（不貼片）；pin 1 在左邊
fps["J2"] = place(fp_lib("Connector_PinHeader_2.00mm", "PinHeader_1x08_P2.00mm_Vertical"),
                  "J2", "WIRE PADS", 2.0, BH - 1.55, 90)
fps["J2"].Models().clear()   # 只是焊點，不畫排針 3D 模型

# ---------------------------------------------------------------- 零件
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C0805 = ("Capacitor_SMD", "C_0805_2012Metric")   # 高壓電容用 0805：JLC 有 Basic 料（4.7uF/25V C1779）
R0402 = ("Resistor_SMD", "R_0402_1005Metric")
SOD = ("Diode_SMD", "D_SOD-323")

# 左半：面板電源腳的電容（FPC pin 15~24 在左邊）
for ref, fpn, val, x, y, rot in (
        ("C12", C0402, "1uF/25V", 1.4, 7.85, 0),      # VCOM (pin 24)
        ("C8", C0402, "1uF/25V", 3.4, 7.85, 0),       # VPP (pin 19)
        ("C7", C0402, "1uF/25V", 5.4, 7.85, 0),       # VDD (pin 18)
        ("C6", C0402, "1uF/25V", 7.4, 7.85, 0),       # VDDIO/VCI 3V3 (pin 15/16)
        ("C10", C0805, "4.7uF/25V", 1.85, 9.4, 0),     # VSL (pin 22)
        ("C9", C0805, "4.7uF/25V", 5.35, 9.4, 0),      # VSH (pin 20)
        ("C4", C0402, "4.7uF/10V", 8.15, 9.4, 90),     # 3V3 升壓輸入（GND 腳朝上靠 C6）
        ("C11", C0805, "4.7uF/25V", 1.85, 11.5, 0),    # PREVGL (pin 23)
        ("C5", C0805, "4.7uF/25V", 5.35, 11.5, 0),     # PREVGH (pin 21)
):
    fps[ref] = place(fp_lib(*fpn), ref, val, x, y, rot)

# 右半：VGH / VGL 電容與升壓電路（FPC pin 2~5 在右邊）
for ref, fpn, val, x, y, rot in (
        ("C2", C0805, "4.7uF/25V", 11.2, 8.05, 0),    # VGH (pin 5)
        ("C1", C0805, "4.7uF/25V", 14.8, 8.05, 0),    # VGL (pin 4)
        ("R1", R0402, "10k", 14.4, 9.65, 0),           # GDR 下拉
        ("R2", R0402, "0.47R 1%", 14.4, 10.75, 0),     # RESE 電流檢測
        ("C3", C0805, "4.7uF/25V", 7.3, 13.6, 180),  # 負壓泵電容（移到左下空位；pin 1 SW 朝右）
):
    fps[ref] = place(fp_lib(*fpn), ref, val, x, y, rot)
fps["Q1"] = place(fp_lib("Package_TO_SOT_SMD", "SOT-23"), "Q1", "AO3400A", 11.2, 10.87, 0)   # JLC Basic（C20917）
fps["L1"] = place(fp_lib("Inductor_SMD", "L_1008_2520Metric"), "L1", "10uH Isat>=1A", 15.6, 12.7, 0)
fps["D3"] = place(fp_lib(*SOD), "D3", "B5819WS", 11.0, 13.66, 180)   # SW → PREVGH（pin 1 = 陰極）
fps["D1"] = place(fp_lib(*SOD), "D1", "B5819WS", 11.0, 15.75, 0)    # PREVGL → NEG（pin 1 NEG 朝左）
fps["D2"] = place(fp_lib(*SOD), "D2", "B5819WS", 15.6, 15.75, 180)  # NEG → GND（pin 2 NEG 朝左）

for fp in fps.values():
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Value().SetLayer(pcbnew.F_Fab)


def silk(text, x, y, h=0.8, align="c", rot=0, back=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(pcbnew.B_SilkS if back else pcbnew.F_SilkS)
    if back:
        t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h)))
    t.SetTextThickness(mm(max(0.15, h * 0.15)))
    t.SetPosition(pt(x, y))
    t.SetTextAngleDegrees(rot)
    t.SetHorizJustify({"l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT,
                       "c": pcbnew.GR_TEXT_H_ALIGN_CENTER}[align])
    board.Add(t)


# 背面：板名與 J2 腳位（正面空間不夠，印在背面）
silk("EPD24 MINI V1.1", 9.0, 5.5, 1.0, back=True)
silk("J2 PINOUT", 9.0, 8.0, 0.8, back=True)
silk("1 3V3   2 GND", 9.0, 9.6, 0.8, back=True)
silk("3 SDI   4 SCK", 9.0, 11.0, 0.8, back=True)
silk("5 CS    6 DC", 9.0, 12.4, 0.8, back=True)
silk("7 RES   8 BUSY", 9.0, 13.8, 0.8, back=True)
for i, lab in enumerate(("3V3", "GND", "SDI", "SCK", "CS", "DC", "RES", "BSY")):   # 背面焊點上方逐腳標示
    silk(lab, 2.0 + 2.0 * i, BH - 3.25, 0.6, back=True)

# ---------------------------------------------------------------- 網路
NETS = {
    "3V3": ["J2.1", "C4.1", "C6.1", "L1.1", "J1.15", "J1.16"],
    "GND": ["J2.2", "J1.8", "J1.17", "R1.2", "R2.2", "D2.1",
            "C1.2", "C2.2", "C4.2", "C5.2", "C6.2", "C7.2", "C8.2", "C9.2", "C10.2", "C11.2", "C12.2"],
    "GDR": ["J1.2", "Q1.1", "R1.1"],
    "RESE": ["J1.3", "Q1.2", "R2.1"],
    "SW": ["L1.2", "Q1.3", "D3.2", "C3.1"],
    "NEG": ["C3.2", "D1.1", "D2.2"],
    "PREVGH": ["D3.1", "C5.1", "J1.21"],
    "PREVGL": ["D1.2", "C11.1", "J1.23"],
    "VGL": ["J1.4", "C1.1"],
    "VGH": ["J1.5", "C2.1"],
    "VDD": ["J1.18", "C7.1"],
    "VPP": ["J1.19", "C8.1"],
    "VSH": ["J1.20", "C9.1"],
    "VSL": ["J1.22", "C10.1"],
    "VCOM": ["J1.24", "C12.1"],
    "SDI": ["J1.14", "J2.3"],
    "SCLK": ["J1.13", "J2.4"],
    "CS": ["J1.12", "J2.5"],
    "DC": ["J1.11", "J2.6"],
    "RES": ["J1.10", "J2.7"],
    "BUSY": ["J1.9", "J2.8"],
}
for name, members in NETS.items():
    n = net(name)
    for m in members:
        ref, num = m.split(".")
        pads = [p for p in fps[ref].Pads() if p.GetNumber() == num]
        assert len(pads) == 1, m
        pads[0].SetNet(n)

# 接地過孔：每個 GND 的 SMD 焊墊旁邊找空位打一個過孔到底層鋪銅，避免小電容的 GND 腳被訊號線圍成孤島
def auto_stitch(via_d=0.5, gap=0.2, dist=(0.6, 0.75, 0.9, 1.2)):
    import math
    obstacles = []                       # (x0, y0, x1, y1, net)：所有焊墊的外框
    for fp in fps.values():
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            x0, y0 = pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY
            obstacles.append((x0, y0, x0 + pcbnew.ToMM(bb.GetWidth()), y0 + pcbnew.ToMM(bb.GetHeight()), p.GetNetname()))
    vias = []
    out = []
    r = via_d / 2

    def free(x, y):
        if x < 0.3 + r or x > BW - 0.3 - r or y < 0.3 + r or y > BH - 0.3 - r:
            return False
        for x0, y0, x1, y1, n in obstacles:
            dx = max(x0 - x, 0, x - x1)
            dy = max(y0 - y, 0, y - y1)
            if n == "GND":                   # 同網路焊墊可以貼著，但過孔不能壓在焊墊上
                if math.hypot(dx, dy) < r + 0.1:
                    return False
                continue
            if math.hypot(dx, dy) < r + gap + 0.05:   # 多留 0.05 給格點佈線誤差
                return False
        return all(math.hypot(x - vx, y - vy) >= via_d + 0.25 for vx, vy in vias)

    for ref in sorted(fps):
        for p in fps[ref].Pads():
            if p.GetNetname() != "GND" or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            c = p.GetPosition()
            px, py = pcbnew.ToMM(c.x) - OX, pcbnew.ToMM(c.y) - OY
            for d in dist:
                for ang in (90, 270, 0, 180, 45, 135, 225, 315):
                    vx = round(px + d * math.cos(math.radians(ang)), 2)
                    vy = round(py + d * math.sin(math.radians(ang)), 2)
                    if free(vx, vy):
                        vias.append((vx, vy))
                        out.append(("GND", (px, py), (vx, vy)))
                        break
                else:
                    continue
                break
            else:
                print("no stitch via for", ref, p.GetNumber())
    return out


STITCH = auto_stitch()

# ---------------------------------------------------------------- 板框
for (x0, y0), (x1, y1) in (((0, 0), (BW, 0)), ((BW, 0), (BW, BH)), ((BW, BH), (0, BH)), ((0, BH), (0, 0))):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    s.SetStart(pt(x0, y0))
    s.SetEnd(pt(x1, y1))
    board.Add(s)

# ---------------------------------------------------------------- 設計規則（JLCPCB 2 層標準製程）
ds = board.GetDesignSettings()
ds.m_CopperEdgeClearance = mm(0.3)
ds.m_TrackMinWidth = mm(0.127)
ds.m_MinClearance = mm(0.127)
ds.m_ViasMinSize = mm(0.5)
ds.m_MinThroughDrill = mm(0.3)
ds.SetCopperLayerCount(2)
ds.m_MinResolvedSpokes = 1
ds.SetAuxOrigin(pt(0, BH))   # 鑽孔 / 座標檔原點 = 板子左下角（給 JLCPCB 貼片座標用）


def dump():
    print("ref   pad  net        x       y")
    for ref in sorted(fps):
        for p in sorted(fps[ref].Pads(), key=lambda q: q.GetNumber()):
            pos = p.GetPosition()
            print(f"{ref:5s} {p.GetNumber():>3s}  {p.GetNetname():9s} {pcbnew.ToMM(pos.x) - OX:7.3f} {pcbnew.ToMM(pos.y) - OY:7.3f}")


def overlaps():
    """列出 courtyard 互相重疊的零件（擺件時自己先檢查）。"""
    boxes = {ref: fp.GetCourtyard(pcbnew.F_CrtYd).BBox() for ref, fp in fps.items()}
    refs = sorted(boxes)
    bad = []
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            if boxes[a].Intersects(boxes[b]):
                bad.append((a, b))
    print("courtyard overlaps:", bad or "none")


if __name__ == "__main__":
    board.BuildListOfNets()
    for fp in fps.values():
        fp.BuildCourtyardCaches()
    if "--route" in sys.argv:
        import route  # noqa: F401

        def pad_xy(ref, num):
            c = [q for q in fps[ref].Pads() if q.GetNumber() == num][0].GetPosition()
            return (pcbnew.ToMM(c.x) - OX, pcbnew.ToMM(c.y) - OY)
        route.PRE_TRACKS = [("3V3", pad_xy("J1", "15"), pad_xy("J1", "16"))]   # VDDIO / VCI 相鄰，直接連
        # 依序佈線；哪條網路走不通，就把它移到最前面重來（失敗時還沒寫回板子，可以直接重跑）
        order = list(route.ORDER)
        for attempt in range(8):
            try:
                route.run(board, net, pt, mm, STITCH, order)
                break
            except route.RouteFailed as e:
                print(f"attempt {attempt + 1}: {e.net} failed, move to front")
                order.remove(e.net)
                order.insert(0, e.net)
        else:
            raise SystemExit("routing failed after 8 attempts")
        print("final order:", order)
    else:
        dump()
        overlaps()
    board.Save(OUT)
    print("saved", OUT)
