# -*- coding: utf-8 -*-
"""產生 24pin 電子紙轉接小板（DESPI-C02 縮小版，排線接 MCU）的 KiCad 電路圖（.kicad_sch）。

改自 D1mini_Fixture_Shield_HW/kicad/gen_sch.py：符號取自 KiCad 內建符號庫並嵌入檔案；
每支腳拉一小段線接網路標籤（同名即相連），網路與 build_pcb.py 的 NETS 相同。
電路照 Good Display DESPI-C02 原理圖（SCH V1.0），同 EPD24_SuperMini_Adapter_HW v1.0 的 e-paper 部分。
執行：python gen_sch.py   （一般 Python 即可，不需要 pcbnew）
"""
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SYMLIB = r"D:\Program Files\KiCad\share\kicad\symbols"
OUT = os.path.join(HERE, "EPD24_Mini_Adapter.kicad_sch")
PROJECT = "EPD24_Mini_Adapter"
ROOT_UUID = "8e4b2d17-6c3a-4f90-b5e1-2a7d9c0f4b63"


def uid():
    return str(uuid.uuid4())


# ------------------------------------------------------------ 讀符號庫
_lib_cache = {}


def lib_symbol(lib, name):
    """回傳 (嵌入用的 s-expr 文字, 腳位 dict{number: (x, y, angle, hidden)})。"""
    if lib not in _lib_cache:
        _lib_cache[lib] = open(os.path.join(SYMLIB, lib + ".kicad_sym"), encoding="utf-8").read()
    s = _lib_cache[lib]
    i = s.find(f'\t(symbol "{name}"')
    assert i >= 0, (lib, name)
    depth, j = 0, i + 1
    while True:
        c = s[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        elif c == '"':
            j = s.index('"', j + 1)
        j += 1
    blk = s[i + 1:j + 1]
    assert "(extends" not in blk[:400], f"{name} extends another symbol"
    blk = blk.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    pins = {}
    for m in re.finditer(r'\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length [\d.]+\)(.*?)\(number "([^"]+)"', blk, re.S):
        hidden = "(hide yes)" in m.group(4)
        pins[m.group(5)] = (float(m.group(1)), float(m.group(2)), int(m.group(3)), hidden)
    return blk, pins


# ------------------------------------------------------------ 建立內容
items = []
embedded = {}


def place(lib, name, ref, value, footprint, x, y, nets, nc=(), datasheet=""):
    """放一個符號；nets = {腳號: 網路名}；nc = 不接的腳號。"""
    key = f"{lib}:{name}"
    blk, pins = lib_symbol(lib, name)
    embedded[key] = blk
    pin_uuids = "".join(f'\n\t\t(pin "{n}" (uuid "{uid()}"))' for n in pins)
    ys = [y - py for (px, py, a_, h_) in pins.values()]
    if name in ("R", "C", "L"):                # 直立被動元件：代號、數值放右邊
        rpos, vpos, rj = (x + 2.54, y - 1.27), (x + 2.54, y + 1.27), " (justify left)"
    else:
        rpos, vpos, rj = (x, min(ys) - 3.81), (x, max(ys) + 3.81), ""
    items.append(f'''	(symbol
		(lib_id "{key}")
		(at {x:.2f} {y:.2f} 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(uuid "{uid()}")
		(property "Reference" "{ref}" (at {rpos[0]:.2f} {rpos[1]:.2f} 0) (effects (font (size 1.27 1.27)){rj}))
		(property "Value" "{value}" (at {vpos[0]:.2f} {vpos[1]:.2f} 0) (effects (font (size 1.27 1.27)){rj}))
		(property "Footprint" "{footprint}" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Datasheet" "{datasheet}" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes))){pin_uuids}
		(instances (project "{PROJECT}" (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))))
	)''')
    for num, (px, py, ang, hidden) in pins.items():
        cx, cy = x + px, y - py
        if num in nc:
            if not hidden:
                items.append(f'\t(no_connect (at {cx:.2f} {cy:.2f}) (uuid "{uid()}"))')
            continue
        if num not in nets:
            continue
        ox, oy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[ang]
        ex, ey = cx + ox * 2.54, cy + oy * 2.54
        items.append(f'\t(wire (pts (xy {cx:.2f} {cy:.2f}) (xy {ex:.2f} {ey:.2f})) (stroke (width 0) (type default)) (uuid "{uid()}"))')
        langle, just = {(-1, 0): (180, "right"), (1, 0): (0, "left"),
                        (0, -1): (90, "left"), (0, 1): (270, "right")}[(ox, oy)]
        items.append(f'\t(label "{nets[num]}" (at {ex:.2f} {ey:.2f} {langle}) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid "{uid()}"))')


def note(text, x, y, size=1.8):
    items.append(f'\t(text "{text}" (exclude_from_sim no) (at {x:.2f} {y:.2f} 0) (effects (font (size {size} {size})) (justify left bottom)) (uuid "{uid()}"))')


G = 2.54
FP_C0402 = "Capacitor_SMD:C_0402_1005Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_R0402 = "Resistor_SMD:R_0402_1005Metric"
FP_SOD = "Diode_SMD:D_SOD-323"

# ---- 面板 FPC
note("面板 FPC：24P 0.5mm 翻蓋（腳位同 DESPI-C02）", 16 * G, 12 * G)
FPC = {"2": "GDR", "3": "RESE", "4": "VGL", "5": "VGH", "8": "GND", "9": "BUSY", "10": "RES",
       "11": "DC", "12": "CS", "13": "SCLK", "14": "SDI", "15": "3V3", "16": "3V3", "17": "GND",
       "18": "VDD", "19": "VPP", "20": "VSH", "21": "PREVGH", "22": "VSL", "23": "PREVGL", "24": "VCOM"}
place("Connector_Generic_MountingPin", "Conn_01x24_MountingPin", "J1", "AFC07-S24FCA-00",
      "Connector_FFC-FPC:Jushuo_AFC07-S24FCA-00_1x24-1MP_P0.50_Horizontal", 26 * G, 34 * G, FPC,
      nc=("1", "6", "7", "MP"))
note("pin 1 NC、6 TSCL、7 TSDA 不接；pin 8 BS 接地 = 4 線 SPI", 16 * G, 58 * G, 1.27)

# ---- 排線座（接 MCU）
note("排線焊點 J2：1x8 穿孔、2.0mm 間距，排線直接焊；腳位順序同 DESPI-C02 的 8pin", 44 * G, 12 * G)
place("Connector_Generic", "Conn_01x08", "J2", "WIRE PADS", "Connector_PinHeader_2.00mm:PinHeader_1x08_P2.00mm_Vertical",
      50 * G, 22 * G, {"1": "3V3", "2": "GND", "3": "SDI", "4": "SCLK", "5": "CS", "6": "DC", "7": "RES", "8": "BUSY"})
note("ESP32-C3 Super Mini 接法（同 esp32c3_spi_display / epaper_driver.h）：", 44 * G, 34 * G, 1.27)
note("1 3V3 → 3.3   2 GND → G   3 SDI → IO3（照 PIN_MIGRATION.md 改腳位後為 IO7）   4 SCLK → IO2", 44 * G, 36 * G, 1.27)
note("5 CS → IO10   6 DC → IO4   7 RES → IO5   8 BUSY → IO6", 44 * G, 38 * G, 1.27)
note("J2 不貼片，排線手焊", 44 * G, 40 * G, 1.27)

# ---- 升壓電路
note("升壓 / 負壓泵（面板 IC 用 GDR、RESE 控制）", 44 * G, 46 * G)
place("Device", "L", "L1", "10uH Isat>=1A", "Inductor_SMD:L_1008_2520Metric", 50 * G, 56 * G, {"1": "3V3", "2": "SW"})
place("Transistor_FET", "Q_NMOS_GSD", "Q1", "AO3400A", "Package_TO_SOT_SMD:SOT-23", 60 * G, 56 * G,
      {"1": "GDR", "2": "RESE", "3": "SW"})
place("Device", "R", "R1", "10k", FP_R0402, 70 * G, 56 * G, {"1": "GDR", "2": "GND"})
place("Device", "R", "R2", "0.47R 1%", FP_R0402, 78 * G, 56 * G, {"1": "RESE", "2": "GND"})
place("Device", "D_Schottky", "D3", "B5819WS", FP_SOD, 50 * G, 68 * G, {"2": "SW", "1": "PREVGH"})
place("Device", "C", "C3", "4.7uF/25V", FP_C0805, 60 * G, 68 * G, {"1": "SW", "2": "NEG"})
place("Device", "D_Schottky", "D1", "B5819WS", FP_SOD, 70 * G, 68 * G, {"2": "PREVGL", "1": "NEG"})
place("Device", "D_Schottky", "D2", "B5819WS", FP_SOD, 80 * G, 68 * G, {"2": "NEG", "1": "GND"})
note("R2 = RESE 電流檢測，固定 0.47Ω（DESPI-C02 DIP 撥 0.47 那側，GDEQ0426T82 實測可用）", 64 * G, 76 * G, 1.27)
note("D1~D3 原廠 MBR0530（SOD-123）→ B5819WS（SOD-323，40V 1A）；Q1 原廠 Si1308EDL → AO3400A（SOT-23，JLC Basic）", 64 * G, 78 * G, 1.27)

# ---- 面板電源電容
note("面板電源電容（靠近 FPC 腳）", 16 * G, 66 * G)
CAPS = [("C1", "VGL", "4.7uF/25V", FP_C0805), ("C2", "VGH", "4.7uF/25V", FP_C0805),
        ("C5", "PREVGH", "4.7uF/25V", FP_C0805), ("C11", "PREVGL", "4.7uF/25V", FP_C0805),
        ("C9", "VSH", "4.7uF/25V", FP_C0805), ("C10", "VSL", "4.7uF/25V", FP_C0805),
        ("C7", "VDD", "1uF/25V", FP_C0402), ("C8", "VPP", "1uF/25V", FP_C0402),
        ("C12", "VCOM", "1uF/25V", FP_C0402), ("C6", "3V3", "1uF/25V", FP_C0402),
        ("C4", "3V3", "4.7uF/10V", FP_C0402)]
for k, (ref, n, val, fp) in enumerate(CAPS):
    place("Device", "C", ref, val, fp, (16 + (k % 6) * 8) * G, (74 + (k // 6) * 12) * G, {"1": n, "2": "GND"})
note("高壓腳（約 ±20V）用 0805 25V（JLC Basic）；低壓用 0402。原廠 1uF 為 50V，這裡腳位電壓都低於 10V，用 25V", 16 * G, 98 * G, 1.27)

# ------------------------------------------------------------ 寫檔
lib_syms = "\n".join("\t\t" + blk.replace("\n", "\n\t") for blk in embedded.values())
doc = f'''(kicad_sch
	(version 20250114)
	(generator "gen_sch.py")
	(generator_version "9.0")
	(uuid "{ROOT_UUID}")
	(paper "A3")
	(title_block
		(title "EPD24 Mini Adapter v1.1 (DESPI-C02 mini, wire pads)")
		(date "2026-10-30")
		(rev "1.0")
		(comment 1 "24-pin SPI e-paper adapter (GDEQ0426T82 / SSD1677), JST SH 8P cable to MCU")
		(comment 2 "Circuit per Good Display DESPI-C02 SCH V1.0; RESE fixed 0.47R, BS tied to GND")
	)
	(lib_symbols
{lib_syms}
	)
{chr(10).join(items)}
	(sheet_instances (path "/" (page "1")))
)
'''
open(OUT, "w", encoding="utf-8").write(doc)
print("saved", OUT)
