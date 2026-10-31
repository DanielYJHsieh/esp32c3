# -*- coding: utf-8 -*-
"""用 KiCad pcbnew API 產生 ESP32-C3 Super Mini 的 24pin 電子紙轉接背板（取代 DESPI-C02）。

執行：  "D:\\Program Files\\KiCad\\bin\\python.exe" build_pcb.py [--route]
座標：  從零件面（F 面）看，FPC 座在上緣（USB 端）為 (0, 0)，X 往右、Y 往下，單位 mm；
        實際放在 (OX, OY) 位移後的位置。
疊法：  零件全在 F 面；Super Mini 疊在 B 面（晶片朝外），所以從 F 面看 Super Mini 的腳位左右鏡像：
        左排 = 5V G 3V3 IO4 IO3 IO2 IO1 IO0，右排 = IO5 IO6 IO7 IO8 IO9 IO10 IO20 IO21（上到下）。
電路：  照 Good Display DESPI-C02 原理圖（SCH V1.0）；RESE 固定 0.47Ω、BS 直接接地（4 線 SPI）。
v1.1：  併入電池背板 v2.1 的電路（battery_management/hardware/kicad_v2）：TP4054 充電、AO3401 load-sharing、
        1M/1M 分壓 → GPIO0、CHRG → GPIO20；電池焊墊 B+ / B−，VSYS 焊墊飛線到 Super Mini 正面 W5 的 A 端。
腳位：  GPIO0~5 留給 ADC 與 deep sleep 喚醒：VBAT/2 → IO0，喚醒按鍵 K1 → IO1、K2 → IO3（100k 上拉、按下接地）；
        SDI 改走 IO7（C3 原生 FSPID），CHRG 改走 IO20。
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
FPLIB = r"D:\Program Files\KiCad\share\kicad\footprints"
OUT = os.path.join(HERE, "EPD24_SuperMini_Adapter.kicad_pcb")

OX, OY = 100.0, 100.0          # 板子左上角在 KiCad 頁面上的位置
BW, BH = 18.0, 26.8            # 寬同 Super Mini；長 = FPC 座 + 排針
SM_TOP = 6.3                   # Super Mini 上緣（USB 端）在本板的 Y
PIN1_Y = SM_TOP + 1.6          # Super Mini 第一支腳距上緣 1.6mm
ROW_X = (1.38, 16.62)          # 兩排中心距 15.24mm

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


def rect(fp, layer, x0, y0, x1, y1, w=0.05):
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        s = pcbnew.PCB_SHAPE(fp)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(layer)
        s.SetWidth(mm(w))
        s.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
        s.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
        fp.Add(s)


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

# J2 / J3：Super Mini 排針孔（焊墊 Ø1.5 / 孔 1.0）；原本的大 courtyard 會壓到 FPC 座，改成貼著焊墊
for ref, x, val in (("J2", ROW_X[0], "SuperMini 5V side"), ("J3", ROW_X[1], "SuperMini IO5 side")):
    fp = fp_lib("Connector_PinHeader_2.54mm", "PinHeader_1x08_P2.54mm_Vertical")
    for p in fp.Pads():
        p.SetSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
        p.SetDrillSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    for it in fp.GraphicalItems():          # 刪掉會讓 swig 釋放記憶體出錯，改搬到 Fab 層
        if it.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd, pcbnew.F_SilkS):
            it.SetLayer(pcbnew.F_Fab)
    rect(fp, pcbnew.F_CrtYd, -0.85, -0.85, 0.85, 7 * 2.54 + 0.85)
    fp.Models().clear()                     # 排針實際在背面（Super Mini 那側），3D 不畫，免得誤導
    fps[ref] = place(fp, ref, val, x, PIN1_Y, 0)

# ---------------------------------------------------------------- 零件
C0402 = ("Capacitor_SMD", "C_0402_1005Metric")
C0603 = ("Capacitor_SMD", "C_0603_1608Metric")
R0402 = ("Resistor_SMD", "R_0402_1005Metric")

# 左半：面板電源腳的電容（FPC pin 15~24 在左邊）
for ref, fpn, val, x, y, rot in (
        ("C12", C0402, "1uF/25V", 3.5, 8.2, 0),       # VCOM (pin 24)
        ("C8", C0402, "1uF/25V", 5.45, 8.2, 0),       # VPP (pin 19)
        ("C6", C0402, "1uF/25V", 7.4, 8.2, 0),        # VDDIO/VCI 3V3 (pin 15/16)
        ("C10", C0603, "4.7uF/25V", 4.0, 9.9, 0),     # VSL (pin 22)
        ("C7", C0402, "1uF/25V", 6.6, 9.9, 0),        # VDD (pin 18)
        ("C9", C0603, "4.7uF/25V", 4.0, 11.6, 0),     # VSH (pin 20)
        ("C11", C0603, "4.7uF/25V", 4.0, 13.3, 0),    # PREVGL (pin 23)
        ("C5", C0603, "4.7uF/25V", 4.0, 15.0, 0),     # PREVGH (pin 21)
        ("C4", C0402, "4.7uF/10V", 6.6, 11.6, 0),     # 3V3 升壓輸入
):
    fps[ref] = place(fp_lib(*fpn), ref, val, x, y, rot)

# 右半：VGH / VGL 電容與升壓電路（FPC pin 2~5 在右邊）
for ref, fpn, val, x, y, rot in (
        ("C2", C0603, "4.7uF/25V", 12.3, 8.9, -90),    # VGH (pin 5)
        ("C1", C0603, "4.7uF/25V", 14.1, 8.9, -90),    # VGL (pin 4)
        ("R1", R0402, "10k", 14.4, 11.6, 0),          # GDR 下拉
        ("R2", R0402, "0.47R 1%", 14.4, 13.0, 0),     # RESE 電流檢測
        ("C3", C0603, "4.7uF/25V", 12.5, 20.2, 0),    # 負壓泵電容
):
    fps[ref] = place(fp_lib(*fpn), ref, val, x, y, rot)
fps["Q1"] = place(fp_lib("Package_TO_SOT_SMD", "SOT-323_SC-70"), "Q1", "Si1308EDL", 11.9, 12.3, 0)
fps["L1"] = place(fp_lib("Inductor_SMD", "L_1008_2520Metric"), "L1", "10uH Isat>=1A", 12.5, 15.6, 0)
SOD = ("Diode_SMD", "D_SOD-323")
fps["D3"] = place(fp_lib(*SOD), "D3", "B5819WS", 12.5, 18.3, 180)   # SW → PREVGH（pin 1 = 陰極）
fps["D1"] = place(fp_lib(*SOD), "D1", "B5819WS", 12.5, 22.1, 0)     # PREVGL → NEG
fps["D2"] = place(fp_lib(*SOD), "D2", "B5819WS", 12.5, 24.1, 180)   # NEG → GND


# 左下：電池電路（同電池背板 v2.1，只把電阻電容縮成 0402 / 0603）
def fp_pad(name, w, h):
    """單一 SMD 焊墊（電池線、VSYS 飛線用），courtyard 貼著焊墊。"""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("EPD24_SuperMini", name))
    p = pcbnew.PAD(fp)
    p.SetNumber("1")
    p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    p.SetRoundRectRadiusRatio(0.15)
    p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    p.SetLayerSet(p.SMDMask())
    p.SetSize(pcbnew.VECTOR2I(mm(w), mm(h)))
    p.SetPosition(pcbnew.VECTOR2I(0, 0))
    fp.Add(p)
    rect(fp, pcbnew.F_CrtYd, -w / 2 - 0.1, -h / 2 - 0.1, w / 2 + 0.1, h / 2 + 0.1)
    return fp


# 擺在左下角（IO1 / IO0 旁），讓出 IO2~IO4 前方給 e-paper 訊號線；電池線焊墊在右側（同電池背板 v2，從 GPIO5~21 那側出線）
fps["U2"] = place(fp_lib("Package_TO_SOT_SMD", "SOT-23-5"), "U2", "TP4054", 4.6, 22.7, 0)
fps["Q2"] = place(fp_lib("Package_TO_SOT_SMD", "SOT-23"), "Q2", "AO3401A", 8.7, 22.7, 0)
for ref, fpn, val, x, y, rot in (
        ("R4", R0402, "5.1k", 6.0, 20.2, 0),          # PROG：充電 196mA，≥ 400mAh 電池；小電池改 10k（貼著 U2 pin 5）
        ("C13", C0402, "1uF/10V", 8.85, 17.9, 90),    # TP4054 VCC（不要加大，會拖慢切換）
        ("R3", R0402, "100k", 9.95, 17.9, 90),        # Q2 Gate 下拉
        ("C15", C0603, "22uF/10V", 8.6, 20.0, 0),     # VSYS，WiFi 尖峰補強
        ("R5", R0402, "1M 1%", 2.85, 25.6, 90),        # VBAT 分壓上
        ("R6", R0402, "1M 1%", 3.95, 25.6, 90),        # VBAT 分壓下
        ("C16", C0402, "100nF", 5.05, 25.6, 90),       # ADC 取樣
        ("C14", C0603, "10uF/10V", 7.2, 25.6, 0),   # VBAT
):
    fps[ref] = place(fp_lib(*fpn), ref, val, x, y, rot)
fps["TP3"] = place(fp_pad("Pad_1.0x1.2", 1.0, 1.2), "TP3", "VSYS", 15.0, 21.6)   # 飛線到 W5 A 端
fps["TP1"] = place(fp_pad("Pad_1.0x1.2", 1.0, 1.2), "TP1", "BAT+", 15.0, 23.2)
fps["TP2"] = place(fp_pad("Pad_1.0x1.2", 1.0, 1.2), "TP2", "BAT-", 15.0, 24.8)

# 左側 IO1~IO3 旁：喚醒按鍵上拉電阻與外接按鍵焊墊（按鍵本體裝在外殼上，零件面會被電池蓋住）
for ref, val, x in (("R7", "100k", 3.4), ("R8", "100k", 5.5)):
    fps[ref] = place(fp_lib(*R0402), ref, val, x, 16.6, 0)
for ref, val, x in (("TP4", "K1", 3.1), ("TP5", "K2", 4.4), ("TP6", "G", 5.7)):
    fps[ref] = place(fp_pad("Pad_0.9x1.1", 0.9, 1.1), ref, val, x, 18.3)

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


# 正面（零件面）：版本、方向
for txt, x in (("K1", 3.1), ("K2", 4.4), ("G", 5.7)):   # 喚醒按鍵焊墊
    silk(txt, x, 19.4, 0.6)
silk("VSYS/B+/B-", 12.6, 25.95, 0.6)          # 右側三個焊墊由上到下：VSYS（飛線到 W5）、電池 +、電池 −
# 背面（Super Mini 那面）：腳位提示，背面字是從背面看的正常方向
silk("5V", 3.7, PIN1_Y, 0.7, back=True)              # 背面字鏡像：從背面看在 5V 腳旁邊
silk("G", 3.7, PIN1_Y + 2.54, 0.7, back=True)
silk("3V3", 3.7, PIN1_Y + 5.08, 0.7, back=True)
silk("USB", 9.0, 8.6, 0.8, back=True)
silk("CHIP SIDE UP", 9.0, 14.0, 0.8, back=True)
silk("EPD24 C3 V1.1", 9.0, 16.0, 0.7, back=True)

# ---------------------------------------------------------------- 網路
NETS = {
    "3V3": ["J2.3", "C4.1", "C6.1", "L1.1", "J1.15", "J1.16", "R7.1", "R8.1"],
    "GND": ["J2.2", "J1.8", "J1.17", "R1.2", "R2.2", "D2.1",
            "C1.2", "C2.2", "C4.2", "C5.2", "C6.2", "C7.2", "C8.2", "C9.2", "C10.2", "C11.2", "C12.2",
            "U2.2", "R3.2", "R4.2", "R6.2", "C13.2", "C14.2", "C15.2", "C16.2", "TP2.1", "TP6.1"],
    # 電池電路（網路名同電池背板 v2.1）
    "VBUS": ["J2.1", "U2.4", "C13.1", "R3.1", "Q2.1"],          # Super Mini 5V 排針
    "VBAT": ["U2.3", "Q2.3", "C14.1", "R5.1", "TP1.1"],
    "VSYS": ["Q2.2", "C15.1", "TP3.1"],
    "PROG": ["U2.5", "R4.1"],
    "CHRG": ["U2.1", "J3.7"],                                    # IO20，Low = 充電中
    "BTN1": ["J2.7", "R7.2", "TP4.1"],                           # IO1，喚醒按鍵 K1
    "BTN2": ["J2.5", "R8.2", "TP5.1"],                           # IO3，喚醒按鍵 K2
    "VBAT_SENSE": ["R5.2", "R6.1", "C16.1", "J2.8"],             # IO0 (ADC1_CH0)
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
    "BUSY": ["J1.9", "J3.2"],     # IO6
    "RES": ["J1.10", "J3.1"],     # IO5
    "DC": ["J1.11", "J2.4"],      # IO4
    "CS": ["J1.12", "J3.6"],      # IO10
    "SCLK": ["J1.13", "J2.6"],    # IO2
    "SDI": ["J1.14", "J3.3"],     # IO7（FSPID）
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
            if n == "GND":                   # 同網路焊墊可以貼著
                continue
            dx = max(x0 - x, 0, x - x1)
            dy = max(y0 - y, 0, y - y1)
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
STITCH.append(("GND", (ROW_X[0], PIN1_Y + 2.54), (2.55, PIN1_Y + 2.85)))   # Super Mini G 腳（穿孔）旁也補一個，避免被走線圍住

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
