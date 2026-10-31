# EPD24 Super Mini 轉接背板 v1.1 — BOM（零件清單）

由 `kicad/export_fab.py` 從 PCB 產生，和 `BOM_JLCPCB_v1.1.csv`、`CPL_JLCPCB_v1.1.csv` 同步；改零件請改程式後重新產生。

- 貼片零件：**18 種、32 顆**，全部在 F 面，可整片交 JLCPCB 貼片
- **LCSC 料號已填**（2026-10-30 查 JLC 料庫，盡量用 Basic 料）。庫存會變，下單時若缺料，照「規格」欄換同封裝的料

## 1. 貼片零件 — e-paper 驅動（同 DESPI-C02）

| 編號 | 值 | 封裝 | 數量 | 規格 | 型號 | LCSC | 用途 |
|---|---|---|---|---|---|---|---|
| C1, C2, C3, C5, C9, C10, C11 | 4.7uF/25V | C 0603 1608Metric | 7 | MLCC 0603 X5R 25V | Samsung CL10A475KA8NQNC | C69335 Ext | VGL、VGH、負壓泵電容、PREVGH、VSH、VSL、PREVGL |
| C4 | 4.7uF/10V | C 0402 1005Metric | 1 | MLCC 0402 X5R 10V | Samsung CL05A475MP5NRNC | C23733 Basic | 3V3 升壓輸入 |
| C6, C7, C8, C12 | 1uF/25V | C 0402 1005Metric | 4 | MLCC 0402 X5R 25V | Samsung CL05A105KA5NQNC | C52923 Basic | VDDIO / VCI（3V3）、VDD、VPP、VCOM |
| D1, D2, D3 | B5819WS | D SOD-323 | 3 | 蕭特基 SOD-323 40V 1A | MDD B5819WS | C64886 Ext（Preferred） | 負壓泵（PREVGL）、負壓泵（到 GND）、升壓整流（PREVGH） |
| J1 | AFC07-S24FCA-00 | Jushuo AFC07-S24FCA-00 1x24-1MP P0.50 Horizontal | 1 | FPC 0.5mm 24P 抽屜式 SMT，下接（Bottom Contact） | JUSHUO AFC07-S24FCA-00 | C262567 Ext | 面板 FPC 座 |
| L1 | 10uH Isat>=1A | L 1008 2520Metric | 1 | 功率電感 2520(1008) 10uH，Isat 1.1A、480mΩ | Sunlord WPN252012H100MT | C98353 Ext | 升壓電感 |
| Q1 | Si1308EDL | SOT-323 SC-70 | 1 | N-MOSFET SC-70-3（SOT-323） | Vishay SI1308EDL-T1-GE3 | C469327 Ext | 升壓開關（GDR 驅動） |
| R1 | 10k | R 0402 1005Metric | 1 | 0402 1% | UNI-ROYAL 0402WGF1002TCE | C25744 Basic | Q1 Gate 下拉 |
| R2 | 0.47R 1% | R 0402 1005Metric | 1 | 0402 1% 低阻（電流檢測） | UNI-ROYAL 0402WGF470LTCE | C423162 Ext | RESE 電流檢測 |

## 2. 貼片零件 — 電池充電 / 電源切換（v1.1，同電池背板 v2.1）

| 編號 | 值 | 封裝 | 數量 | 規格 | 型號 | LCSC | 用途 |
|---|---|---|---|---|---|---|---|
| C13 | 1uF/10V | C 0402 1005Metric | 1 | MLCC 0402 X5R 10V 以上 | Samsung CL05A105KA5NQNC（25V，同 C6~C8） | C52923 Basic | TP4054 VCC（不要加大） |
| C14 | 10uF/10V | C 0603 1608Metric | 1 | MLCC 0603 X5R 10V | Samsung CL10A106KP8NNNC | C19702 Basic | VBAT |
| C15 | 22uF/10V | C 0603 1608Metric | 1 | MLCC 0603 X5R 6.3V 以上（VSYS ≤ 5V） | Samsung CL10A226MQ8NRNC（6.3V） | C59461 Basic | VSYS（WiFi 尖峰補強） |
| C16 | 100nF | C 0402 1005Metric | 1 | MLCC 0402 X7R 16V | Samsung CL05B104KO5NNNC | C1525 Basic | ADC 取樣 |
| Q2 | AO3401A | SOT-23 | 1 | P-MOSFET SOT-23（印字 A19T） | AO3401A（替代 SI2301CDS、DMG2305UX） | C15127 Basic | 電池 / USB 切換（load-sharing） |
| R3 | 100k | R 0402 1005Metric | 1 | 0402 1% | UNI-ROYAL 0402WGF1003TCE | C25741 Basic | Q2 Gate 下拉 |
| R4 | 5.1k | R 0402 1005Metric | 1 | 0402 1%（充電電流 I = 1000V / R4） | UNI-ROYAL 0402WGF5101TCE | C25905 Basic | 充電電流設定（5.1k = 196 mA） |
| R5, R6 | 1M 1% | R 0402 1005Metric | 2 | 0402 1%（分壓精度影響電量讀數） | UNI-ROYAL 0402WGF1004TCE | C26083 Basic | VBAT 分壓（上）、VBAT 分壓（下） |
| U2 | TP4054 | SOT-23-5 | 1 | 鋰電池線性充電 IC SOT-23-5，4.2V（腳位 CHRG/GND/BAT/VCC/PROG 已對過） | TOPPOWER TP4054-42-SOT25R | C32574 Ext（Preferred） | 鋰電池充電 |

## 3. 貼片零件 — 喚醒按鍵上拉（IO1 / IO3）

| 編號 | 值 | 封裝 | 數量 | 規格 | 型號 | LCSC | 用途 |
|---|---|---|---|---|---|---|---|
| R7, R8 | 100k | R 0402 1005Metric | 2 | 0402 1% | UNI-ROYAL 0402WGF1003TCE | C25741 Basic | 喚醒按鍵 K1（IO1）上拉、喚醒按鍵 K2（IO3）上拉 |

## 4. 手焊 / 不貼片

| 編號 | 項目 | 規格 | 數量 | 備註 |
|---|---|---|---|---|
| J2、J3 | Super Mini 排針 | 1×8 2.54mm 排針 | 2 | 或直接用 Super Mini 附的排針；Super Mini 疊在本板 B 面 |
| TP1、TP2 | 電池連接線 | 1.25mm 2P 公母對插線（MX1.25 / PicoBlade 相容） | 1 組 | 板端焊 B+ / B−。**每顆電池插上前先量極性** |
| TP3 | VSYS 飛線 | 28–30 AWG 絕緣線，約 20mm | 1 | 繞過板邊焊到 Super Mini 正面 **W5 的 A 端** |
| TP4、TP5、TP6 | 喚醒按鍵線 | 30 AWG 絕緣線 + 常開輕觸按鍵 ×2 | 1 組 | K1（IO1）、K2（IO3）各一顆按鍵接到 G；按鍵裝在外殼上（零件面會被電池蓋住） |

## 5. 另購

| 項目 | 規格 | 數量 | 備註 |
|---|---|---|---|
| 主控板 | ESP32-C3 Super Mini（2×8 腳、22.5 × 18mm） | 1 | 要先**拆掉電源 LED**，W5 保持完整 |
| 電子紙 | GDEQ0426T82（4.26"，SSD1677，24pin 0.5mm FPC） | 1 | 換別的面板要先確認 RESE 值（本板固定 0.47Ω） |
| 電池 | 單節 LiPo，**帶保護板**，**≥ 400 mAh**（例如 500 mAh）。用 402020（約 110 mAh）、502020（約 150 mAh）這類小電池時 R4 要改 10k | 1 | 充電 196 mA；保護板出線朝右（IO5–21 那側） |
| 絕緣 / 固定 | Kapton 膠帶、0.5–1mm 泡棉雙面膠 | 少量 | 電池和零件面之間一定要隔 Kapton |

## 6. 挑料注意

- **L1 電感**：選 Sunlord WPN252012H100MT（Isat 1.1A）。2520 的 10µH 很多款 Isat 不到 1A，缺料要換時要看規格書。
- **J1 FPC 座**：C262567 是**下接（Bottom Contact）**，要對照現有 DESPI-C02 的座子和面板金手指朝向，不合要換上接款；換別家要確認焊墊位置和 KiCad `Jushuo_AFC07-S24FCA-00` 一樣。
- **高壓電容（C1、C2、C3、C5、C9、C10、C11）**：腳位電壓約 ±20V，用 25V 以上；0603 的直流偏壓衰減比 0402 小。JLC 沒有 Basic 的 0603 4.7µF/25V，這顆是 Extended。
- **R5、R6**：用 1%，精度直接影響電量讀數。
- **R4**：預設 5.1k = 196 mA，給 ≥ 400 mAh 電池（同電池背板 v2.1）；小電池（100–400 mAh）改 10k（100 mA，C25744）。背板壓在電池下面，R4 不要小於 5.1k。
- **C13**：1µF 不要加大，會拖慢拔 USB 後的電源切換。
- **R7、R8**：100k 上拉，deep sleep 時待機電流只有按住按鍵才會流（33 µA）；韌體不用再開內部上拉。
