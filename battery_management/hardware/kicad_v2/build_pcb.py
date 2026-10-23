# -*- coding: utf-8 -*-
"""用 KiCad pcbnew API 產生 ESP32-C3 SuperMini 電池背板 v2 的 PCB。

執行：  "D:\\Program Files\\KiCad\\bin\\python.exe" build_pcb.py [--route]
座標：  背板左上角為 (0, 0)，X 往右、Y 往下，單位 mm（= 從 SuperMini 背面看、USB 朝上）。
        背板左上角對應 SuperMini 背面座標 (2.2, 0.4)。
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
FPLIB = r"D:\Program Files\KiCad\share\kicad\footprints"
OUT = os.path.join(HERE, "C3_Battery_Backpack.kicad_pcb")

from geom import OX, OY, BW, BH, THICKNESS, NOTCHES, HOLES, CUT_R  # noqa: E402


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


board = pcbnew.BOARD()
nets = {}


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]


# ---------------------------------------------------------------- footprint
def fp_lib(lib, name):
    return pcbnew.FootprintLoad(os.path.join(FPLIB, lib + ".pretty"), name)


def fp_edge_pad():
    """接點：單一 SMD 焊墊 0.7 × 1.0（焊細線用）。"""
    fp = pcbnew.FOOTPRINT(board)
    fp.SetFPID(pcbnew.LIB_ID("C3_Backpack", "EdgePad_0.7x1.0"))
    p = pcbnew.PAD(fp)
    p.SetNumber("1")
    p.SetShape(pcbnew.PAD_SHAPE_ROUNDRECT)
    p.SetRoundRectRadiusRatio(0.15)
    p.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    p.SetLayerSet(p.SMDMask())
    p.SetSize(pcbnew.VECTOR2I(mm(0.7), mm(1.0)))
    p.SetPosition(pcbnew.VECTOR2I(0, 0))
    fp.Add(p)
    return fp


fps = {}


def place(fp, ref, value, x, y, rot=0.0):
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(pt(x, y))
    fp.SetOrientationDegrees(rot)
    fp.Reference().SetLayer(pcbnew.F_Fab)      # 零件代號不印（板子太小），對照組裝圖
    fp.Value().SetLayer(pcbnew.F_Fab)
    board.Add(fp)
    fps[ref] = fp
    return fp


R06 = ("Resistor_SMD", "R_0603_1608Metric")
C06 = ("Capacitor_SMD", "C_0603_1608Metric")
C08 = ("Capacitor_SMD", "C_0805_2012Metric")

place(fp_lib("Package_TO_SOT_SMD", "SOT-23-5"), "U1", "TP4054", 3.4, 10.5, 180)
place(fp_lib("Package_TO_SOT_SMD", "SOT-23"), "Q1", "AO3401", 7.4, 4.2, 180)
place(fp_lib(*C06), "C1", "1uF", 3.6, 7.9, 0)
place(fp_lib(*R06), "R1", "100k", 4.6, 4.0, 90)
place(fp_lib(*R06), "R2", "10k", 2.3, 13.8, -90)
place(fp_lib(*C08), "C2", "10uF", 6.6, 8.4, 90)
place(fp_lib(*C08), "C3", "22uF", 8.2, 1.3, 0)
place(fp_lib(*R06), "R3", "1M", 8.6, 12.0, -90)
place(fp_lib(*R06), "R4", "1M", 8.6, 15.2, -90)
place(fp_lib(*C06), "C4", "100nF", 6.8, 15.2, -90)

PADS = {"P1": (0.86, 3.6), "P2": (0.86, 7.6), "P3": (0.86, 15.9), "P4": (0.86, 17.5),
        "P5": (12.74, 3.6), "P6": (12.74, 15.9), "P7": (12.74, 17.5)}
for ref, (x, y) in PADS.items():
    place(fp_edge_pad(), ref, ref, x, y, 0)

# ---------------------------------------------------------------- 網路（與 gen_sch.py 相同）
NETS = {
    "VBUS": ["P1.1", "U1.4", "C1.1", "R1.1", "Q1.1"],
    "GND": ["P2.1", "U1.2", "C1.2", "R1.2", "R2.2", "C2.2", "C3.2", "R4.2", "C4.2", "P7.1"],
    "VBAT": ["U1.3", "Q1.3", "C2.1", "R3.1", "P6.1"],
    "VSYS": ["Q1.2", "C3.1", "P5.1"],
    "PROG": ["U1.5", "R2.1"],
    "CHRG": ["U1.1", "P3.1"],
    "VBAT_SENSE": ["R3.2", "R4.1", "C4.1", "P4.1"],
}
for name, members in NETS.items():
    n = net(name)
    for m in members:
        ref, num = m.split(".")
        pads = [p for p in fps[ref].Pads() if p.GetNumber() == num]
        assert len(pads) == 1, m
        pads[0].SetNet(n)


# ---------------------------------------------------------------- 板框
def edge_seg(a, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    s.SetStart(pt(*a))
    s.SetEnd(pt(*b))
    board.Add(s)


def edge_arc(a, mid, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    s.SetArcGeometry(pt(*a), pt(*mid), pt(*b))
    board.Add(s)


x = 0.0
for cx, cy in NOTCHES:
    edge_seg((x, 0), (cx - CUT_R, 0))
    edge_seg((cx - CUT_R, 0), (cx - CUT_R, cy))
    edge_arc((cx - CUT_R, cy), (cx, cy + CUT_R), (cx + CUT_R, cy))
    edge_seg((cx + CUT_R, cy), (cx + CUT_R, 0))
    x = cx + CUT_R
edge_seg((x, 0), (BW, 0))
edge_seg((BW, 0), (BW, BH))
edge_seg((BW, BH), (0, BH))
edge_seg((0, BH), (0, 0))
for cx, cy in HOLES:
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    s.SetCenter(pt(cx, cy))
    s.SetEnd(pt(cx + CUT_R, cy))
    board.Add(s)


# ---------------------------------------------------------------- 絲印（Top 面）
def silk(text, x, y, h=0.8, align="c", back=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetLayer(pcbnew.B_SilkS if back else pcbnew.F_SilkS)
    if back:
        t.SetMirrored(True)
    t.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h)))
    t.SetTextThickness(mm(0.15))
    t.SetPosition(pt(x, y))
    t.SetHorizJustify({"l": pcbnew.GR_TEXT_H_ALIGN_LEFT, "r": pcbnew.GR_TEXT_H_ALIGN_RIGHT,
                       "c": pcbnew.GR_TEXT_H_ALIGN_CENTER}[align])
    board.Add(t)


silk("5V", 1.45, 3.6, 0.8, "l")
silk("G", 1.45, 7.6, 0.8, "l")
silk("IO1", 1.45, 15.9, 0.8, "l")
silk("IO0", 1.45, 17.5, 0.8, "l")
silk("B+", 12.15, 15.9, 0.8, "r")
silk("B-", 12.15, 17.5, 0.8, "r")
silk("C3 BATT", 10.9, 9.6, 0.8)
silk("V2.0", 10.9, 10.7, 0.8)
silk("SUPERMINI SIDE", 6.8, 9.4, 0.8, back=True)

# ---------------------------------------------------------------- 設計規則（JLCPCB）
ds = board.GetDesignSettings()
ds.m_CopperEdgeClearance = mm(0.3)
ds.m_TrackMinWidth = mm(0.15)
ds.m_MinClearance = mm(0.15)
ds.m_ViasMinSize = mm(0.5)
ds.m_MinThroughDrill = mm(0.3)
ds.SetCopperLayerCount(2)
ds.SetBoardThickness(mm(THICKNESS))
ds.m_MinResolvedSpokes = 1


def dump():
    print("ref   pad  net          x       y")
    for ref in sorted(fps):
        for p in sorted(fps[ref].Pads(), key=lambda q: q.GetNumber()):
            pos = p.GetPosition()
            print(f"{ref:5s} {p.GetNumber():>3s}  {p.GetNetname():11s} {pcbnew.ToMM(pos.x) - OX:7.3f} {pcbnew.ToMM(pos.y) - OY:7.3f}")


if __name__ == "__main__":
    if "--route" in sys.argv:
        import route
        route.run(board, net, pt, mm)
    else:
        dump()
    board.Save(OUT)
    print("saved", OUT)
