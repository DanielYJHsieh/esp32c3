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
NAME = "EPD24_SuperMini_Adapter"
PCB = os.path.join(HERE, NAME + ".kicad_pcb")
SCH = os.path.join(HERE, NAME + ".kicad_sch")
VER = "v1.1"

# 料號：2026-10-30 在 JLC 料庫挑，盡量用 Basic 料；換料前先確認封裝相同
PARTS = {  # 值 → (規格說明, 建議型號, LCSC)
    "4.7uF/25V": ("MLCC 0603 X5R 25V", "Samsung CL10A475KA8NQNC", "C69335"),
    "4.7uF/10V": ("MLCC 0402 X5R 10V", "Samsung CL05A475MP5NRNC", "C23733"),
    "1uF/25V": ("MLCC 0402 X5R 25V", "Samsung CL05A105KA5NQNC", "C52923"),
    "10k": ("0402 1%", "UNI-ROYAL 0402WGF1002TCE", "C25744"),
    "5.1k": ("0402 1%（充電電流 I = 1000V / R4）", "UNI-ROYAL 0402WGF5101TCE", "C25905"),
    "0.47R 1%": ("0402 1% 低阻（電流檢測）", "UNI-ROYAL 0402WGF470LTCE", "C423162"),
    "Si1308EDL": ("N-MOSFET SC-70-3（SOT-323）", "Vishay SI1308EDL-T1-GE3", "C469327"),
    "10uH Isat>=1A": ("功率電感 2520(1008) 10uH，Isat 1.1A、480mΩ", "Sunlord WPN252012H100MT", "C98353"),
    "B5819WS": ("蕭特基 SOD-323 40V 1A", "MDD B5819WS", "C64886"),
    "AFC07-S24FCA-00": ("FPC 0.5mm 24P 抽屜式 SMT，下接（Bottom Contact）", "JUSHUO AFC07-S24FCA-00", "C262567"),
    # v1.1 電池電路（同電池背板 v2.1）
    "TP4054": ("鋰電池線性充電 IC SOT-23-5，4.2V（腳位 CHRG/GND/BAT/VCC/PROG 已對過）", "TOPPOWER TP4054-42-SOT25R", "C32574"),
    "AO3401A": ("P-MOSFET SOT-23（印字 A19T）", "AO3401A（替代 SI2301CDS、DMG2305UX）", "C15127"),
    "1uF/10V": ("MLCC 0402 X5R 10V 以上", "Samsung CL05A105KA5NQNC（25V，同 C6~C8）", "C52923"),
    "10uF/10V": ("MLCC 0603 X5R 10V", "Samsung CL10A106KP8NNNC", "C19702"),
    "22uF/10V": ("MLCC 0603 X5R 6.3V 以上（VSYS ≤ 5V）", "Samsung CL10A226MQ8NRNC（6.3V）", "C59461"),
    "100k": ("0402 1%", "UNI-ROYAL 0402WGF1003TCE", "C25741"),
    "1M 1%": ("0402 1%（分壓精度影響電量讀數）", "UNI-ROYAL 0402WGF1004TCE", "C26083"),
    "100nF": ("MLCC 0402 X7R 16V", "Samsung CL05B104KO5NNNC", "C1525"),
}
# JLC 料庫類型（2026-10-30 查 jlcpcb.com）：Basic 免換料費；Extended 每種約 $3，Preferred Extended 通常免
LIB = {"C69335": "Ext", "C23733": "Basic", "C52923": "Basic", "C25744": "Basic", "C25905": "Basic", "C423162": "Ext",
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

# ---- 座標檔 → JLCPCB CPL（排針孔 J2/J3、焊墊 TP1~TP6 不貼片）
pos = os.path.join(HERE, "pos_front.csv")
run("pcb", "export", "pos", "--side", "front", "--format", "csv", "--units", "mm", "--use-drill-file-origin", "-o", pos, PCB)
with open(pos, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
os.remove(pos)
rows = [r for r in rows if r["Ref"] not in ("J2", "J3") and not r["Ref"].startswith("TP")]   # 排針孔、電池/飛線/按鍵焊墊不貼片
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

# ---- BOM.md（給人看的完整清單：貼片零件 + 手焊 / 另購料）
FUNC = {  # 編號 → 用途
    "J1": "面板 FPC 座", "Q1": "升壓開關（GDR 驅動）", "L1": "升壓電感",
    "D1": "負壓泵（PREVGL）", "D2": "負壓泵（到 GND）", "D3": "升壓整流（PREVGH）",
    "R1": "Q1 Gate 下拉", "R2": "RESE 電流檢測", "C1": "VGL", "C2": "VGH", "C3": "負壓泵電容",
    "C4": "3V3 升壓輸入", "C5": "PREVGH", "C6": "VDDIO / VCI（3V3）", "C7": "VDD", "C8": "VPP",
    "C9": "VSH", "C10": "VSL", "C11": "PREVGL", "C12": "VCOM",
    "U2": "鋰電池充電", "Q2": "電池 / USB 切換（load-sharing）", "R3": "Q2 Gate 下拉",
    "R4": "充電電流設定（5.1k = 196 mA）", "R5": "VBAT 分壓（上）", "R6": "VBAT 分壓（下）",
    "C13": "TP4054 VCC（不要加大）", "C14": "VBAT", "C15": "VSYS（WiFi 尖峰補強）", "C16": "ADC 取樣",
    "R7": "喚醒按鍵 K1（IO1）上拉", "R8": "喚醒按鍵 K2（IO3）上拉",
}
BATTERY = {"U2", "Q2", "R3", "R4", "R5", "R6", "C13", "C14", "C15", "C16"}
BUTTON = {"R7", "R8"}


def md_rows(refset):
    items = []                               # 同值同封裝合併；只取這一節的編號，再依這一節的第一個編號排序
    for (val, pkg), refs in groups.items():
        refs = sorted((r for r in refs if r in refset), key=refkey)
        if refs:
            items.append((refs, val, pkg))
    out = []
    for refs, val, pkg in sorted(items, key=lambda it: refkey(it[0][0])):
        spec, mpn, lcsc = PARTS[val]
        funcs = "、".join(dict.fromkeys(FUNC[r] for r in refs))
        out.append(f"| {', '.join(refs)} | {val} | {pkg.replace('_', ' ')} | {len(refs)} | {spec} | {mpn or '—'} | {lcsc} {LIB[lcsc]} | {funcs} |")
    return out


all_refs = {r for refs in groups.values() for r in refs}
epd, bat, btn = all_refs - BATTERY - BUTTON, all_refs & BATTERY, all_refs & BUTTON
head = ["| 編號 | 值 | 封裝 | 數量 | 規格 | 型號 | LCSC | 用途 |", "|---|---|---|---|---|---|---|---|"]
lines = [
    f"# EPD24 Super Mini 轉接背板 {VER} — BOM（零件清單）",
    "",
    f"由 `kicad/export_fab.py` 從 PCB 產生，和 `BOM_JLCPCB_{VER}.csv`、`CPL_JLCPCB_{VER}.csv` 同步；改零件請改程式後重新產生。",
    "",
    f"- 貼片零件：**{len(groups)} 種、{len(all_refs)} 顆**，全部在 F 面，可整片交 JLCPCB 貼片",
    "- **LCSC 料號已填**（2026-10-30 查 JLC 料庫，盡量用 Basic 料）。庫存會變，下單時若缺料，照「規格」欄換同封裝的料",
    "",
    "## 1. 貼片零件 — e-paper 驅動（同 DESPI-C02）",
    "",
    *head, *md_rows(epd),
    "",
    "## 2. 貼片零件 — 電池充電 / 電源切換（v1.1，同電池背板 v2.1）",
    "",
    *head, *md_rows(bat),
    "",
    "## 3. 貼片零件 — 喚醒按鍵上拉（IO1 / IO3）",
    "",
    *head, *md_rows(btn),
    "",
    "## 4. 手焊 / 不貼片",
    "",
    "| 編號 | 項目 | 規格 | 數量 | 備註 |",
    "|---|---|---|---|---|",
    "| J2、J3 | Super Mini 排針 | 1×8 2.54mm 排針 | 2 | 或直接用 Super Mini 附的排針；Super Mini 疊在本板 B 面 |",
    "| TP1、TP2 | 電池連接線 | 1.25mm 2P 公母對插線（MX1.25 / PicoBlade 相容） | 1 組 | 板端焊 B+ / B−。**每顆電池插上前先量極性** |",
    "| TP3 | VSYS 飛線 | 28–30 AWG 絕緣線，約 20mm | 1 | 繞過板邊焊到 Super Mini 正面 **W5 的 A 端** |",
    "| TP4、TP5、TP6 | 喚醒按鍵線 | 30 AWG 絕緣線 + 常開輕觸按鍵 ×2 | 1 組 | K1（IO1）、K2（IO3）各一顆按鍵接到 G；按鍵裝在外殼上（零件面會被電池蓋住） |",
    "",
    "## 5. 另購",
    "",
    "| 項目 | 規格 | 數量 | 備註 |",
    "|---|---|---|---|",
    "| 主控板 | ESP32-C3 Super Mini（2×8 腳、22.5 × 18mm） | 1 | 要先**拆掉電源 LED**，W5 保持完整 |",
    "| 電子紙 | GDEQ0426T82（4.26\"，SSD1677，24pin 0.5mm FPC） | 1 | 換別的面板要先確認 RESE 值（本板固定 0.47Ω） |",
    "| 電池 | 單節 LiPo，**帶保護板**，**≥ 400 mAh**（例如 500 mAh）。用 402020（約 110 mAh）、502020（約 150 mAh）這類小電池時 R4 要改 10k | 1 | 充電 196 mA；保護板出線朝右（IO5–21 那側） |",
    "| 絕緣 / 固定 | Kapton 膠帶、0.5–1mm 泡棉雙面膠 | 少量 | 電池和零件面之間一定要隔 Kapton |",
    "",
    "## 6. 挑料注意",
    "",
    "- **L1 電感**：選 Sunlord WPN252012H100MT（Isat 1.1A）。2520 的 10µH 很多款 Isat 不到 1A，缺料要換時要看規格書。",
    "- **J1 FPC 座**：C262567 是**下接（Bottom Contact）**，要對照現有 DESPI-C02 的座子和面板金手指朝向，不合要換上接款；換別家要確認焊墊位置和 KiCad `Jushuo_AFC07-S24FCA-00` 一樣。",
    "- **高壓電容（C1、C2、C3、C5、C9、C10、C11）**：腳位電壓約 ±20V，用 25V 以上；0603 的直流偏壓衰減比 0402 小。JLC 沒有 Basic 的 0603 4.7µF/25V，這顆是 Extended。",
    "- **R5、R6**：用 1%，精度直接影響電量讀數。",
    "- **R4**：預設 5.1k = 196 mA，給 ≥ 400 mAh 電池（同電池背板 v2.1）；小電池（100–400 mAh）改 10k（100 mA，C25744）。背板壓在電池下面，R4 不要小於 5.1k。",
    "- **C13**：1µF 不要加大，會拖慢拔 USB 後的電源切換。",
    "- **R7、R8**：100k 上拉，deep sleep 時待機電流只有按住按鍵才會流（33 µA）；韌體不用再開內部上拉。",
    "",
]
with open(os.path.join(UP, "BOM.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("saved BOM.md")

# ---- 電路圖 PDF、預覽圖
run("sch", "export", "pdf", "-o", os.path.join(UP, f"{NAME}_schematic.pdf"), SCH)
for side in ("top", "bottom"):
    run("pcb", "render", "--side", side, "--width", "900", "--height", "1300", "--quality", "basic",
        "-o", os.path.join(UP, f"pcb_3d_{side}.png"), PCB)
print("done")
