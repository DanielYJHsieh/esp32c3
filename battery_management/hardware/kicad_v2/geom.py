# -*- coding: utf-8 -*-
"""板子幾何（build_pcb.py 與 route.py 共用）。座標：背板左上角 (0, 0)，單位 mm。"""
OX, OY = 100.0, 100.0          # 背板左上角在 KiCad 頁面上的位置
BW, BH = 12.0, 12.8            # 背板大小
THICKNESS = 0.6                # 板厚 mm

# 背板左上角對應 SuperMini 背面座標（USB 朝上、板子左上角為原點）
SM_X, SM_Y = 3.0, 0.5

# USB-C 固定腳在 SuperMini 背面是平的（2026-10-23 實板確認），不需要缺口或圓孔
NOTCHES = []
HOLES = []
CUT_R = 1.3
