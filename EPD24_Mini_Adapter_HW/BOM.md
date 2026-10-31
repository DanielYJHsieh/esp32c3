# EPD24 Mini 轉接板 v1.0 — BOM（零件清單）

由 `kicad/export_fab.py` 從 PCB 產生，和 `BOM_JLCPCB_v1.0.csv`、`CPL_JLCPCB_v1.0.csv` 同步；改零件請改程式後重新產生。

- 貼片零件：**10 種、21 顆**，全部在 F 面，可整片交 JLCPCB 貼片
- **LCSC 料號已填**（2026-10-30 查 JLC 料庫，盡量用 Basic 料）。庫存會變，下單時若缺料，照「規格」欄換同封裝的料

## 1. 貼片零件

| 編號 | 值 | 封裝 | 數量 | 規格 | 型號 | LCSC | 用途 |
|---|---|---|---|---|---|---|---|
| C1, C2, C3, C5, C9, C10, C11 | 4.7uF/25V | C 0603 1608Metric | 7 | MLCC 0603 X5R 25V | Samsung CL10A475KA8NQNC | C69335 Ext | VGL、VGH、負壓泵電容、PREVGH、VSH、VSL、PREVGL |
| C4 | 4.7uF/10V | C 0402 1005Metric | 1 | MLCC 0402 X5R 10V | Samsung CL05A475MP5NRNC | C23733 Basic | 3V3 升壓輸入 |
| C6, C7, C8, C12 | 1uF/25V | C 0402 1005Metric | 4 | MLCC 0402 X5R 25V | Samsung CL05A105KA5NQNC | C52923 Basic | VDDIO / VCI（3V3）、VDD、VPP、VCOM |
| D1, D2, D3 | B5819WS | D SOD-323 | 3 | 蕭特基 SOD-323 40V 1A | MDD B5819WS | C64886 Ext（Preferred） | 負壓泵（PREVGL）、負壓泵（到 GND）、升壓整流（PREVGH） |
| J1 | AFC07-S24FCA-00 | Jushuo AFC07-S24FCA-00 1x24-1MP P0.50 Horizontal | 1 | FPC 0.5mm 24P 抽屜式 SMT，下接（Bottom Contact） | JUSHUO AFC07-S24FCA-00 | C262567 Ext | 面板 FPC 座 |
| J2 | SM08B-SRSS-TB | JST SH SM08B-SRSS-TB 1x08-1MP P1.00mm Horizontal | 1 | JST SH 1.0mm 8P 臥式 SMT（開口朝板邊） | JST SM08B-SRSS-TB(LF)(SN) | C160407 Ext | 排線座（接 MCU） |
| L1 | 10uH Isat>=1A | L 1008 2520Metric | 1 | 功率電感 2520(1008) 10uH，Isat 1.1A、480mΩ | Sunlord WPN252012H100MT | C98353 Ext | 升壓電感 |
| Q1 | Si1308EDL | SOT-323 SC-70 | 1 | N-MOSFET SC-70-3（SOT-323） | Vishay SI1308EDL-T1-GE3 | C469327 Ext | 升壓開關（GDR 驅動） |
| R1 | 10k | R 0402 1005Metric | 1 | 0402 1% | UNI-ROYAL 0402WGF1002TCE | C25744 Basic | Q1 Gate 下拉 |
| R2 | 0.47R 1% | R 0402 1005Metric | 1 | 0402 1% 低阻（電流檢測） | UNI-ROYAL 0402WGF470LTCE | C423162 Ext | RESE 電流檢測 |

## 2. 另購

| 項目 | 規格 | 數量 | 備註 |
|---|---|---|---|
| 排線 | JST SH 1.0mm 8P 對杜邦母頭線（單頭 SH、另一頭 2.54 杜邦） | 1 | 接 ESP32-C3 Super Mini 排針；線序見 README |
| 電子紙 | GDEQ0426T82（4.26"，SSD1677，24pin 0.5mm FPC） | 1 | 換別的面板要先確認 RESE 值（本板固定 0.47Ω） |

## 3. 挑料注意

- **L1 電感**：選 Sunlord WPN252012H100MT（Isat 1.1A）。2520 的 10µH 很多款 Isat 不到 1A，缺料要換時要看規格書。
- **J1 FPC 座**：C262567 是**下接（Bottom Contact）**，要對照現有 DESPI-C02 的座子和面板金手指朝向，不合要換上接款；換別家要確認焊墊位置和 KiCad `Jushuo_AFC07-S24FCA-00` 一樣。
- **J2 排線座**：footprint 是 KiCad 內建的 `JST_SH_SM08B-SRSS-TB`；用相容座（例如「SH1.0 8P 臥貼」）要確認焊墊位置相同。
- **高壓電容（C1、C2、C3、C5、C9、C10、C11）**：腳位電壓約 ±20V，用 25V 以上；0603 的直流偏壓衰減比 0402 小。JLC 沒有 Basic 的 0603 4.7µF/25V，這顆是 Extended。
