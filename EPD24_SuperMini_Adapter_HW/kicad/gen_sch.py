# -*- coding: utf-8 -*-
"""產生 ESP32-C3 Super Mini 24pin 電子紙轉接背板的 KiCad 電路圖（.kicad_sch）。

改自 D1mini_Fixture_Shield_HW/kicad/gen_sch.py：符號取自 KiCad 內建符號庫並嵌入檔案；
每支腳拉一小段線接網路標籤（同名即相連），網路與 build_pcb.py 的 NETS 相同。
電路照 Good Display DESPI-C02 原理圖（SCH V1.0）；v1.1 併入電池背板 v2.1 的充電 / 電源切換電路。
執行：python gen_sch.py   （一般 Python 即可，不需要 pcbnew）
"""
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SYMLIB = r"D:\Program Files\KiCad\share\kicad\symbols"
OUT = os.path.join(HERE, "EPD24_SuperMini_Adapter.kicad_sch")
PROJECT = "EPD24_SuperMini_Adapter"
ROOT_UUID = "3c1e7a90-5b2d-4f6e-8a14-9d2c0b7e5f31"


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
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
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

# ---- Super Mini
note("ESP32-C3 Super Mini（疊在背面；從零件面看左右鏡像）", 44 * G, 12 * G)
place("Connector_Generic", "Conn_01x08", "J2", "SuperMini 5V side", "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
      50 * G, 22 * G, {"1": "VBUS", "2": "GND", "3": "3V3", "4": "DC", "5": "BTN2", "6": "SCLK",
                       "7": "BTN1", "8": "VBAT_SENSE"})
place("Connector_Generic", "Conn_01x08", "J3", "SuperMini IO5 side", "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical",
      66 * G, 22 * G, {"1": "RES", "2": "BUSY", "3": "SDI", "6": "CS", "7": "CHRG"}, nc=("4", "5", "8"))
note("J2: 5V(VBUS) G 3V3 IO4(DC) IO3(BTN2) IO2(SCLK) IO1(BTN1) IO0(VBAT_SENSE)", 44 * G, 34 * G, 1.27)
note("J3: IO5(RES) IO6(BUSY) IO7(SDI) IO8 IO9 IO10(CS) IO20(CHRG) IO21", 44 * G, 36 * G, 1.27)
note("同 esp32c3_spi_display 的腳位定義（epaper_driver.h）；IO0~IO5 留給 ADC 與 deep sleep 喚醒", 44 * G, 38 * G, 1.27)

# ---- 升壓電路
note("升壓 / 負壓泵（面板 IC 用 GDR、RESE 控制）", 44 * G, 46 * G)
place("Device", "L", "L1", "10uH Isat>=1A", "Inductor_SMD:L_1008_2520Metric", 50 * G, 56 * G, {"1": "3V3", "2": "SW"})
place("Transistor_FET", "Q_NMOS_GSD", "Q1", "Si1308EDL", "Package_TO_SOT_SMD:SOT-323_SC-70", 60 * G, 56 * G,
      {"1": "GDR", "2": "RESE", "3": "SW"})
place("Device", "R", "R1", "10k", FP_R0402, 70 * G, 56 * G, {"1": "GDR", "2": "GND"})
place("Device", "R", "R2", "0.47R 1%", FP_R0402, 78 * G, 56 * G, {"1": "RESE", "2": "GND"})
place("Device", "D_Schottky", "D3", "B5819WS", FP_SOD, 50 * G, 68 * G, {"2": "SW", "1": "PREVGH"})
place("Device", "C", "C3", "4.7uF/25V", FP_C0603, 60 * G, 68 * G, {"1": "SW", "2": "NEG"})
place("Device", "D_Schottky", "D1", "B5819WS", FP_SOD, 70 * G, 68 * G, {"2": "PREVGL", "1": "NEG"})
place("Device", "D_Schottky", "D2", "B5819WS", FP_SOD, 80 * G, 68 * G, {"2": "NEG", "1": "GND"})
note("R2 = RESE 電流檢測，固定 0.47Ω（DESPI-C02 DIP 撥 0.47 那側，GDEQ0426T82 實測可用）", 64 * G, 76 * G, 1.27)
note("D1~D3 原廠 MBR0530（SOD-123）→ B5819WS（SOD-323，40V 1A）", 64 * G, 78 * G, 1.27)

# ---- 面板電源電容
note("面板電源電容（靠近 FPC 腳）", 16 * G, 66 * G)
CAPS = [("C1", "VGL", "4.7uF/25V", FP_C0603), ("C2", "VGH", "4.7uF/25V", FP_C0603),
        ("C5", "PREVGH", "4.7uF/25V", FP_C0603), ("C11", "PREVGL", "4.7uF/25V", FP_C0603),
        ("C9", "VSH", "4.7uF/25V", FP_C0603), ("C10", "VSL", "4.7uF/25V", FP_C0603),
        ("C7", "VDD", "1uF/25V", FP_C0402), ("C8", "VPP", "1uF/25V", FP_C0402),
        ("C12", "VCOM", "1uF/25V", FP_C0402), ("C6", "3V3", "1uF/25V", FP_C0402),
        ("C4", "3V3", "4.7uF/10V", FP_C0402)]
for k, (ref, n, val, fp) in enumerate(CAPS):
    place("Device", "C", ref, val, fp, (16 + (k % 6) * 8) * G, (74 + (k // 6) * 12) * G, {"1": n, "2": "GND"})
note("高壓腳（約 ±20V）用 0603 25V；低壓用 0402。原廠 1uF 為 50V，這裡腳位電壓都低於 10V，用 25V", 16 * G, 98 * G, 1.27)

# ---- 電池電路（v1.1，同 battery_management/hardware/kicad_v2 電池背板 v2.1）
note("電池充電與電源切換（v1.1，同電池背板 v2.1）", 96 * G, 12 * G)
note("TP4054 符號借用 LTC4054ES5-4.2，腳位相同：1 CHRG / 2 GND / 3 BAT / 4 VCC / 5 PROG", 96 * G, 14 * G, 1.27)
place("Battery_Management", "LTC4054ES5-4.2", "U2", "TP4054", "Package_TO_SOT_SMD:SOT-23-5",
      110 * G, 26 * G, {"1": "CHRG", "2": "GND", "3": "VBAT", "4": "VBUS", "5": "PROG"})
place("Device", "C", "C13", "1uF/10V", FP_C0402, 98 * G, 26 * G, {"1": "VBUS", "2": "GND"})
place("Device", "R", "R4", "5.1k", FP_R0402, 98 * G, 36 * G, {"1": "PROG", "2": "GND"})
place("Device", "C", "C14", "10uF/10V", FP_C0603, 122 * G, 26 * G, {"1": "VBAT", "2": "GND"})
note("R4：5.1k = 充電 196mA，給 ≥ 400mAh 電池；小電池改 10k = 100mA（I = 1000V / R4）；C13 不要加大，會拖慢拔 USB 後的切換", 96 * G, 42 * G, 1.27)
note("電源路徑（load-sharing）：Q2 D = 電池、S = VSYS、G = VBUS", 136 * G, 12 * G)
place("Transistor_FET", "TP0610T", "Q2", "AO3401A", "Package_TO_SOT_SMD:SOT-23",
      146 * G, 26 * G, {"1": "VBUS", "2": "VSYS", "3": "VBAT"})
place("Device", "R", "R3", "100k", FP_R0402, 136 * G, 32 * G, {"1": "VBUS", "2": "GND"})
place("Device", "C", "C15", "22uF/10V", FP_C0603, 156 * G, 26 * G, {"1": "VSYS", "2": "GND"})
note("插 USB：VSYS 由 USB 經 Super Mini 的 W5 供電，Q2 關閉；拔 USB：Q2 導通，電池供 VSYS", 136 * G, 42 * G, 1.27)
note("電量偵測：VBAT / 2 → IO0（常駐約 2uA）；CHRG → IO20（Low = 充電中）", 96 * G, 50 * G)
place("Device", "R", "R5", "1M 1%", FP_R0402, 98 * G, 60 * G, {"1": "VBAT", "2": "VBAT_SENSE"})
place("Device", "R", "R6", "1M 1%", FP_R0402, 108 * G, 60 * G, {"1": "VBAT_SENSE", "2": "GND"})
place("Device", "C", "C16", "100nF", FP_C0402, 118 * G, 60 * G, {"1": "VBAT_SENSE", "2": "GND"})
note("焊墊：TP1 / TP2 接電池線，TP3 飛線到 Super Mini 正面 W5 的 A 端（VSYS）", 136 * G, 50 * G)
for k, (ref, val, n) in enumerate((("TP1", "BAT+", "VBAT"), ("TP2", "BAT-", "GND"), ("TP3", "VSYS (W5 A)", "VSYS"))):
    place("Connector", "TestPoint", ref, val, "EPD24_SuperMini:Pad_1.0x1.2", (140 + k * 8) * G, 58 * G, {"1": n})
for k, n in enumerate(("VBUS", "GND", "VSYS")):
    place("power", "PWR_FLAG", f"#FLG0{k + 1}", "PWR_FLAG", "", (98 + k * 10) * G, 72 * G, {"1": n})
note("PWR_FLAG：VBUS 來自 Super Mini USB、VSYS 由 Q2 / W5 供給、GND 來自 Super Mini", 96 * G, 78 * G, 1.27)

# ---- 喚醒按鍵（v1.1：IO1 / IO3 可從 deep sleep 喚醒；按鍵接 GND，100k 上拉到 3V3）
note("喚醒按鍵：外接按鍵焊在 K1 / K2 與 G 焊墊之間（按下 = Low，IO1 / IO3 可喚醒 deep sleep）", 16 * G, 104 * G)
place("Device", "R", "R7", "100k", FP_R0402, 98 * G, 98 * G, {"1": "3V3", "2": "BTN1"})
place("Device", "R", "R8", "100k", FP_R0402, 108 * G, 98 * G, {"1": "3V3", "2": "BTN2"})
for k, (ref, val, n) in enumerate((("TP4", "K1 (IO1)", "BTN1"), ("TP5", "K2 (IO3)", "BTN2"), ("TP6", "G", "GND"))):
    place("Connector", "TestPoint", ref, val, "EPD24_SuperMini:Pad_0.9x1.1", (122 + k * 8) * G, 96 * G, {"1": n})

# ------------------------------------------------------------ 寫檔
lib_syms = "\n".join("\t\t" + blk.replace("\n", "\n\t") for blk in embedded.values())
doc = f'''(kicad_sch
	(version 20250114)
	(generator "gen_sch.py")
	(generator_version "9.0")
	(uuid "{ROOT_UUID}")
	(paper "A3")
	(title_block
		(title "EPD24 Super Mini Adapter v1.1 (DESPI-C02 mini + battery)")
		(date "2026-10-31")
		(rev "1.1")
		(comment 1 "ESP32-C3 Super Mini backpack for 24-pin SPI e-paper (GDEQ0426T82 / SSD1677)")
		(comment 2 "Circuit per Good Display DESPI-C02 SCH V1.0; RESE fixed 0.47R, BS tied to GND")
		(comment 3 "v1.1: battery charger / load-sharing per C3 Battery Backpack v2.1 (TP4054 + AO3401)")
		(comment 4 "Pins: CHRG IO20, SDI IO7, wake buttons IO1 / IO3, VBAT/2 IO0")
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
