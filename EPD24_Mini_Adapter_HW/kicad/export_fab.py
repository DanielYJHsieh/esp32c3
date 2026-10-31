# -*- coding: utf-8 -*-
"""匯出生產檔：Gerber + 鑽孔（zip）、JLCPCB 貼片用 BOM / CPL、BOM.md、電路圖 PDF、預覽圖。
執行：python export_fab.py   （先跑過 build_pcb.py --route 與 gen_sch.py）"""
import csv
import os
import shutil
import subprocess
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
UP = os.path.dirname(HERE)
CLI = r"D:\Program Files\KiCad\bin\kicad-cli.exe"
NAME = "EPD24_Mini_Adapter"
PCB = os.path.join(HERE, NAME + ".kicad_pcb")
SCH = os.path.join(HERE, NAME + ".kicad_sch")
VER = "v1.0"

# 料號：2026-10-30 在 JLC 料庫挑，盡量用 Basic 料；換料前先確認封裝相同
PARTS = {  # 值 → (規格說明, 建議型號, LCSC)
    "4.7uF/25V": ("MLCC 0603 X5R 25V", "Samsung CL10A475KA8NQNC", "C69335"),
    "4.7uF/10V": ("MLCC 0402 X5R 10V", "Samsung CL05A475MP5NRNC", "C23733"),
    "1uF/25V": ("MLCC 0402 X5R 25V", "Samsung CL05A105KA5NQNC", "C52923"),
    "10k": ("0402 1%", "UNI-ROYAL 0402WGF1002TCE", "C25744"),
    "0.47R 1%": ("0402 1% 低阻（電流檢測）", "UNI-ROYAL 0402WGF470LTCE", "C423162"),
    "Si1308EDL": ("N-MOSFET SC-70-3（SOT-323）", "Vishay SI1308EDL-T1-GE3", "C469327"),
    "10uH Isat>=1A": ("功率電感 2520(1008) 10uH，Isat 1.1A、480mΩ", "Sunlord WPN252012H100MT", "C98353"),
    "B5819WS": ("蕭特基 SOD-323 40V 1A", "MDD B5819WS", "C64886"),
    "AFC07-S24FCA-00": ("FPC 0.5mm 24P 抽屜式 SMT，下接（Bottom Contact）", "JUSHUO AFC07-S24FCA-00", "C262567"),
    "SM08B-SRSS-TB": ("JST SH 1.0mm 8P 臥式 SMT（開口朝板邊）", "JST SM08B-SRSS-TB(LF)(SN)", "C160407"),
}
# JLC 料庫類型（2026-10-30 查 jlcpcb.com）：Basic 免換料費；Extended 每種約 $3，Preferred Extended 通常免
LIB = {"C69335": "Ext", "C23733": "Basic", "C52923": "Basic", "C25744": "Basic", "C423162": "Ext",
       "C469327": "Ext", "C98353": "Ext", "C64886": "Ext（Preferred）", "C262567": "Ext", "C160407": "Ext",
       "C32574": "Ext（Preferred）", "C15127": "Basic", "C19702": "Basic", "C59461": "Basic",
       "C25741": "Basic", "C26083": "Basic", "C1525": "Basic"}


def run(*args):
    subprocess.run([CLI, *args], check=True, capture_output=True)


# ---- Gerber + 鑽孔
gdir = os.path.join(HERE, "gerber")
shutil.rmtree(gdir, ignore_errors=True)
os.makedirs(gdir)
run("pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Paste,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts",
    "--subtract-soldermask", "--use-drill-file-origin", "-o", gdir + os.sep, PCB)
run("pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm", "--drill-origin", "plot",
    "--generate-map", "--map-format", "gerberx2", "-o", gdir + os.sep, PCB)
zpath = os.path.join(UP, f"{NAME}_{VER}_Gerber.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(gdir)):
        z.write(os.path.join(gdir, f), f)
print("saved", zpath)

# ---- 座標檔 → JLCPCB CPL
pos = os.path.join(HERE, "pos_front.csv")
run("pcb", "export", "pos", "--side", "front", "--format", "csv", "--units", "mm", "--use-drill-file-origin", "-o", pos, PCB)
with open(pos, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
os.remove(pos)
# 全部零件都貼片（J2 JST 座也是 SMT）
with open(os.path.join(UP, f"CPL_JLCPCB_{VER}.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        w.writerow([r["Ref"], f'{float(r["PosX"]):.3f}mm', f'{float(r["PosY"]):.3f}mm', "Top", f'{float(r["Rot"]) % 360:.0f}'])

# ---- BOM（同值合併）
groups = {}
for r in rows:
    groups.setdefault((r["Val"], r["Package"]), []).append(r["Ref"])


def refkey(ref):
    return (ref.rstrip("0123456789"), int(ref[len(ref.rstrip("0123456789")):]))


with open(os.path.join(UP, f"BOM_JLCPCB_{VER}.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["Comment", "Designator", "Footprint", "Qty", "Spec", "MPN", "LCSC Part #"])
    by_lcsc = {}                             # 同料號併成一行，JLC 對 BOM 裡重複的料號會標警示
    for (val, pkg), refs in groups.items():
        by_lcsc.setdefault(PARTS[val][2], (val, pkg, []))[2].extend(refs)
    for lcsc, (val, pkg, refs) in sorted(by_lcsc.items(), key=lambda kv: refkey(min(kv[1][2], key=refkey))):
        refs = sorted(refs, key=refkey)
        spec, mpn, _ = PARTS[val]
        w.writerow([val, ",".join(refs), pkg, len(refs), spec, mpn, lcsc])
print("saved BOM / CPL")

# ---- BOM.md（給人看的完整清單：貼片零件 + 另購料）
FUNC = {  # 編號 → 用途
    "J1": "面板 FPC 座", "J2": "排線座（接 MCU）", "Q1": "升壓開關（GDR 驅動）", "L1": "升壓電感",
    "D1": "負壓泵（PREVGL）", "D2": "負壓泵（到 GND）", "D3": "升壓整流（PREVGH）",
    "R1": "Q1 Gate 下拉", "R2": "RESE 電流檢測", "C1": "VGL", "C2": "VGH", "C3": "負壓泵電容",
    "C4": "3V3 升壓輸入", "C5": "PREVGH", "C6": "VDDIO / VCI（3V3）", "C7": "VDD", "C8": "VPP",
    "C9": "VSH", "C10": "VSL", "C11": "PREVGL", "C12": "VCOM",
}
items = []
for (val, pkg), refs in groups.items():
    items.append((sorted(refs, key=refkey), val, pkg))
table = ["| 編號 | 值 | 封裝 | 數量 | 規格 | 型號 | LCSC | 用途 |", "|---|---|---|---|---|---|---|---|"]
for refs, val, pkg in sorted(items, key=lambda it: refkey(it[0][0])):
    spec, mpn, lcsc = PARTS[val]
    funcs = "、".join(dict.fromkeys(FUNC[r] for r in refs))
    table.append(f"| {', '.join(refs)} | {val} | {pkg.replace('_', ' ')} | {len(refs)} | {spec} | {mpn or '—'} | {lcsc} {LIB[lcsc]} | {funcs} |")
n_parts = sum(len(r) for r, _, _ in items)
lines = [
    f"# EPD24 Mini 轉接板 {VER} — BOM（零件清單）",
    "",
    f"由 `kicad/export_fab.py` 從 PCB 產生，和 `BOM_JLCPCB_{VER}.csv`、`CPL_JLCPCB_{VER}.csv` 同步；改零件請改程式後重新產生。",
    "",
    f"- 貼片零件：**{len(items)} 種、{n_parts} 顆**，全部在 F 面，可整片交 JLCPCB 貼片",
    "- **LCSC 料號已填**（2026-10-30 查 JLC 料庫，盡量用 Basic 料）。庫存會變，下單時若缺料，照「規格」欄換同封裝的料",
    "",
    "## 1. 貼片零件",
    "",
    *table,
    "",
    "## 2. 另購",
    "",
    "| 項目 | 規格 | 數量 | 備註 |",
    "|---|---|---|---|",
    "| 排線 | JST SH 1.0mm 8P 對杜邦母頭線（單頭 SH、另一頭 2.54 杜邦） | 1 | 接 ESP32-C3 Super Mini 排針；線序見 README |",
    "| 電子紙 | GDEQ0426T82（4.26\"，SSD1677，24pin 0.5mm FPC） | 1 | 換別的面板要先確認 RESE 值（本板固定 0.47Ω） |",
    "",
    "## 3. 挑料注意",
    "",
    "- **L1 電感**：選 Sunlord WPN252012H100MT（Isat 1.1A）。2520 的 10µH 很多款 Isat 不到 1A，缺料要換時要看規格書。",
    "- **J1 FPC 座**：C262567 是**下接（Bottom Contact）**，要對照現有 DESPI-C02 的座子和面板金手指朝向，不合要換上接款；換別家要確認焊墊位置和 KiCad `Jushuo_AFC07-S24FCA-00` 一樣。",
    "- **J2 排線座**：footprint 是 KiCad 內建的 `JST_SH_SM08B-SRSS-TB`；用相容座（例如「SH1.0 8P 臥貼」）要確認焊墊位置相同。",
    "- **高壓電容（C1、C2、C3、C5、C9、C10、C11）**：腳位電壓約 ±20V，用 25V 以上；0603 的直流偏壓衰減比 0402 小。JLC 沒有 Basic 的 0603 4.7µF/25V，這顆是 Extended。",
    "",
]
with open(os.path.join(UP, "BOM.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("saved BOM.md")

# ---- 電路圖 PDF、預覽圖
run("sch", "export", "pdf", "-o", os.path.join(UP, f"{NAME}_schematic.pdf"), SCH)
for side in ("top", "bottom"):
    run("pcb", "render", "--side", side, "--width", "900", "--height", "1075", "--quality", "basic",   # 同板子長寬比
        "-o", os.path.join(UP, f"pcb_3d_{side}.png"), PCB)
print("done")
