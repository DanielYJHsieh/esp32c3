# -*- coding: utf-8 -*-
"""產生 ESP32-C3 SuperMini 電池背板 v2 的 KiCad 電路圖（.kicad_sch）。

做法同 switch_relay_Control 的 gen_sch.py：符號取自 KiCad 內建庫並嵌入檔案，
每支腳拉一小段線接網路標籤（同名即相連），網路與 build_pcb.py 的 NETS 相同。
執行：python gen_sch.py
"""
import os
import re
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SYMLIB = r"D:\Program Files\KiCad\share\kicad\symbols"
PROJECT = "C3_Battery_Backpack"
OUT = os.path.join(HERE, PROJECT + ".kicad_sch")
ROOT_UUID = "3b1c7e2a-5d4f-4c8e-9a1b-7f2e6d0c4a21"


def uid():
    return str(uuid.uuid4())


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


items = []
embedded = {}


def place(lib, name, ref, value, footprint, x, y, nets, nc=(), in_bom=True):
    key = f"{lib}:{name}"
    blk, pins = lib_symbol(lib, name)
    embedded[key] = blk
    pin_uuids = "".join(f'\n\t\t(pin "{n}" (uuid "{uid()}"))' for n in pins)
    ys = [y - py for (px, py, a_, h_) in pins.values()]
    if name in ("R", "C"):
        rpos, vpos, rj = (x + 2.54, y - 1.27), (x + 2.54, y + 1.27), " (justify left)"
    elif len(pins) == 1:        # TestPoint / PWR_FLAG：文字放在符號上方左右兩側，避開往下的網路標籤
        rpos, vpos, rj = (x - 1.27, y - 3.81), (x + 1.27, y - 3.81), None
    else:                       # IC / MOS：文字放在上下兩支腳的右側，避開網路標籤
        rpos, vpos, rj = (x + 2.54, min(ys) + 1.27), (x + 2.54, max(ys) - 0.64), " (justify left)"
    rj_ref, rj_val = (" (justify right)", " (justify left)") if rj is None else (rj, rj)
    hide_ref = " (hide yes)" if ref.startswith("#") else ""
    items.append(f'''	(symbol
		(lib_id "{key}")
		(at {x:.2f} {y:.2f} 0)
		(unit 1)
		(exclude_from_sim no)
		(in_bom {"yes" if in_bom else "no"})
		(on_board {"yes" if footprint else "no"})
		(dnp no)
		(uuid "{uid()}")
		(property "Reference" "{ref}" (at {rpos[0]:.2f} {rpos[1]:.2f} 0) (effects (font (size 1.27 1.27)){rj_ref}{hide_ref}))
		(property "Value" "{value}" (at {vpos[0]:.2f} {vpos[1]:.2f} 0) (effects (font (size 1.27 1.27)){rj_val}))
		(property "Footprint" "{footprint}" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes)))
		(property "Datasheet" "" (at {x:.2f} {y:.2f} 0) (effects (font (size 1.27 1.27)) (hide yes))){pin_uuids}
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
FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C6 = "Capacitor_SMD:C_0603_1608Metric"
FP_C8 = "Capacitor_SMD:C_0805_2012Metric"
FP_P = "C3_Backpack:EdgePad_0.7x1.0"

# ---- 充電
note("充電：TP4054", 20 * G, 13 * G)
note("符號借用 LTC4054ES5-4.2，腳位相同：1 CHRG / 2 GND / 3 BAT / 4 VCC / 5 PROG", 20 * G, 15 * G, 1.27)
place("Battery_Management", "LTC4054ES5-4.2", "U1", "TP4054", "Package_TO_SOT_SMD:SOT-23-5",
      34 * G, 26 * G, {"1": "CHRG", "2": "GND", "3": "VBAT", "4": "VBUS", "5": "PROG"})
place("Device", "C", "C1", "1uF", FP_C6, 22 * G, 26 * G, {"1": "VBUS", "2": "GND"})
place("Device", "R", "R2", "10k", FP_R, 22 * G, 36 * G, {"1": "PROG", "2": "GND"})
place("Device", "C", "C2", "10uF", FP_C8, 46 * G, 26 * G, {"1": "VBAT", "2": "GND"})
note("R2：10k = 100mA（I = 1000V / R2）；背面版不建議再加大", 20 * G, 42 * G, 1.27)

# ---- 電源路徑
note("電源路徑（load-sharing）", 62 * G, 13 * G)
note("Q1 D = 電池、S = VSYS、G = VBUS", 62 * G, 15 * G, 1.27)
place("Transistor_FET", "TP0610T", "Q1", "AO3401 (A19T)", "Package_TO_SOT_SMD:SOT-23",
      72 * G, 26 * G, {"1": "VBUS", "2": "VSYS", "3": "VBAT"})
place("Device", "R", "R1", "100k", FP_R, 62 * G, 32 * G, {"1": "VBUS", "2": "GND"})
place("Device", "C", "C3", "22uF", FP_C8, 84 * G, 26 * G, {"1": "VSYS", "2": "GND"})
note("插 USB：VSYS 由 USB 經 SuperMini 的 W5 供電，Q1 關閉；拔 USB：Q1 導通，電池供 VSYS", 62 * G, 42 * G, 1.27)

# ---- 電量偵測
note("電量偵測：VBAT / 2 → GPIO0（常駐約 2uA）", 20 * G, 50 * G)
place("Device", "R", "R3", "1M 1%", FP_R, 22 * G, 60 * G, {"1": "VBAT", "2": "VBAT_SENSE"})
place("Device", "R", "R4", "1M 1%", FP_R, 32 * G, 60 * G, {"1": "VBAT_SENSE", "2": "GND"})
place("Device", "C", "C4", "100nF", FP_C6, 42 * G, 60 * G, {"1": "VBAT_SENSE", "2": "GND"})

# ---- 接點
note("接點（邊緣焊墊）：P1–P4 跳線到 SuperMini 排針，P5 飛線到 W5 A 端，P6/P7 接電池", 62 * G, 50 * G)
pads = [("P1", "5V", "VBUS"), ("P2", "G", "GND"), ("P3", "GPIO1", "CHRG"), ("P4", "GPIO0", "VBAT_SENSE"),
        ("P5", "W5 A", "VSYS"), ("P6", "BAT+", "VBAT"), ("P7", "BAT-", "GND")]
for k, (ref, val, n) in enumerate(pads):
    place("Connector", "TestPoint", ref, val, FP_P, (64 + k * 7) * G, 58 * G, {"1": n}, in_bom=False)

# ---- PWR_FLAG（電源由板外供給）
for k, n in enumerate(("VBUS", "GND", "VSYS")):
    place("power", "PWR_FLAG", f"#FLG0{k + 1}", "PWR_FLAG", "", (22 + k * 10) * G, 72 * G, {"1": n}, in_bom=False)
note("PWR_FLAG：VBUS 來自 SuperMini USB、VSYS 由 Q1 / W5 供給（VBAT 由 U1 BAT 驅動）", 20 * G, 78 * G, 1.27)

lib_syms = "\n".join("\t\t" + blk.replace("\n", "\n\t") for blk in embedded.values())
doc = f'''(kicad_sch
	(version 20250114)
	(generator "gen_sch.py")
	(generator_version "9.0")
	(uuid "{ROOT_UUID}")
	(paper "A4")
	(title_block
		(title "ESP32-C3 SuperMini Battery Backpack v2.1")
		(date "2026-10-23")
		(rev "2.1")
		(comment 1 "TP4054 charger + AO3401 load-sharing + VBAT/2 sense")
		(comment 2 "Connect: P1 5V, P2 G, P3 GPIO1, P4 GPIO0, P5 W5 A end (VSYS), P6/P7 battery")
	)
	(lib_symbols
{lib_syms}
	)
{chr(10).join(items)}
	(sheet_instances (path "/" (page "1")))
)
'''
open(OUT, "w", encoding="utf-8").write(doc)
pro = os.path.join(HERE, PROJECT + ".kicad_pro")
if not os.path.exists(pro):  # 設計規則寫在 .kicad_pro，不要覆蓋
    open(pro, "w", encoding="utf-8").write("{}\n")
print("saved", OUT)
