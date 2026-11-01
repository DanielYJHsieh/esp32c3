# EPD24 Mini 轉接板 v1.1 — BOM（零件清單）

由 `kicad/export_fab.py` 從 PCB 產生，和 `BOM_JLCPCB_v1.1.csv`、`CPL_JLCPCB_v1.1.csv` 同步；改零件請改程式後重新產生。

- 貼片零件：**6 種、17 顆**，全部在 F 面，**都是 Basic 料（B5819WS 為 Preferred），不用付換料費**
- **J1、L1、R2 不貼片、自己手焊**（JLC 只有 Extended 料，每種換料費約 $3）；J2 是排線焊點
- **LCSC 料號已填**（2026-10-30 查 JLC 料庫，盡量用 Basic 料）。庫存會變，下單時若缺料，照「規格」欄換同封裝的料

## 1. 貼片零件

| 編號 | 值 | 封裝 | 數量 | 規格 | 型號 | LCSC | 用途 |
|---|---|---|---|---|---|---|---|
| C1, C2, C3, C5, C9, C10, C11 | 4.7uF/25V | C 0805 2012Metric | 7 | MLCC 0805 X5R 25V | Samsung CL21A475KAQNNNE | C1779 Basic | VGL、VGH、負壓泵電容、PREVGH、VSH、VSL、PREVGL |
| C4 | 4.7uF/10V | C 0402 1005Metric | 1 | MLCC 0402 X5R 10V | Samsung CL05A475MP5NRNC | C23733 Basic | 3V3 升壓輸入 |
| C6, C7, C8, C12 | 1uF/25V | C 0402 1005Metric | 4 | MLCC 0402 X5R 25V | Samsung CL05A105KA5NQNC | C52923 Basic | VDDIO / VCI（3V3）、VDD、VPP、VCOM |
| D1, D2, D3 | B5819WS | D SOD-323 | 3 | 蕭特基 SOD-323 40V 1A | MDD B5819WS | C64886 Ext（Preferred） | 負壓泵（PREVGL）、負壓泵（到 GND）、升壓整流（PREVGH） |
| Q1 | AO3400A | SOT-23 | 1 | N-MOSFET SOT-23 30V 5.7A（取代原廠 Si1308EDL） | AO3400A | C20917 Basic | 升壓開關（GDR 驅動） |
| R1 | 10k | R 0402 1005Metric | 1 | 0402 1% | UNI-ROYAL 0402WGF1002TCE | C25744 Basic | Q1 Gate 下拉 |

## 2. 手焊零件（自己買料）

| 編號 | 值 | 封裝 | 規格 | 型號 | LCSC（自購參考） | 用途 |
|---|---|---|---|---|---|---|
| J1 | AFC07-S24FCA-00 | Jushuo AFC07-S24FCA-00 1x24-1MP P0.50 Horizontal | FPC 0.5mm 24P 抽屜式 SMT，下接（Bottom Contact） | JUSHUO AFC07-S24FCA-00 | C262567 | 面板 FPC 座 |
| L1 | 10uH Isat>=1A | L 1008 2520Metric | 功率電感 2520(1008) 10uH，Isat 1.1A、480mΩ | Sunlord WPN252012H100MT | C98353 | 升壓電感 |
| R2 | 0.47R 1% | R 0402 1005Metric | 0402 1% 低阻（電流檢測） | UNI-ROYAL 0402WGF470LTCE | C423162 | RESE 電流檢測 |

焊接順序建議：先焊 **J1 FPC 座**（最難，0.5mm 間距：上助焊劑、對位後先固定兩端，再拖焊，用放大鏡檢查短路），再焊 R2、L1。

## 3. 另購

| 項目 | 規格 | 數量 | 備註 |
|---|---|---|---|
| 排線 | 8 芯細線（26–28 AWG），或剪一段 8P 杜邦線 | 1 | 手焊到 J2 焊點（2.0mm 間距穿孔，孔徑 0.8mm），另一端接 ESP32-C3；線序見 README |
| 電子紙 | GDEQ0426T82（4.26"，SSD1677，24pin 0.5mm FPC） | 1 | 換別的面板要先確認 RESE 值（本板固定 0.47Ω） |

## 4. 挑料注意

- **L1 電感**：選 Sunlord WPN252012H100MT（Isat 1.1A）。2520 的 10µH 很多款 Isat 不到 1A，缺料要換時要看規格書。
- **J1 FPC 座**：C262567 是**下接（Bottom Contact）**，要對照現有 DESPI-C02 的座子和面板金手指朝向，不合要換上接款；換別家要確認焊墊位置和 KiCad `Jushuo_AFC07-S24FCA-00` 一樣。
- **J2**：只是穿孔焊點，不貼片；想改插拔也可以焊 2.0mm 間距排針。
- **高壓電容（C1、C2、C3、C5、C9、C10、C11）**：腳位電壓約 ±20V，用 25V 以上；用 0805 是因為 JLC 的 4.7µF/25V 只有 0805 有 Basic 料（C1779），直流偏壓衰減也比 0603 小。
- **Q1**：原廠 Si1308EDL（SOT-323）換成 AO3400A（SOT-23，30V 5.7A），JLC Basic 料、電氣規格更寬裕。
