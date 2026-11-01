# EPD24 Mini 轉接板 v1.1（DESPI-C02 縮小版，排線接 MCU）

取代 Good Display DESPI-C02（41 × 22 mm）的獨立小轉接板，驅動 24pin SPI 電子紙（目前用 GDEQ0426T82，SSD1677），板子放在面板旁邊，用 **8 條線直接焊**到 J2，拉到 ESP32-C3 Super Mini（或任何 3.3V MCU）。

- 板子 **18.0 × 19.9 mm**（DESPI-C02 的約 40%）
- 雙層、零件全在單面（F 面）。**JLCPCB 只貼 Basic 料**（6 種 17 顆，不用換料費）；JLC 只有 Extended 料的 **J1 FPC 座、L1 電感、R2 0.47Ω 自己買料手焊**（見 `BOM.md` 第 2 節）
- e-paper 電路跟 `../EPD24_SuperMini_Adapter_HW` v1.0 相同（Q1、高壓電容換成 JLC Basic 料），只把 Super Mini 排針換成排線焊點；要直接疊在 Super Mini 上、或要電池電路，用那個專案

## 接頭

| 位置 | 接頭 | 說明 |
|---|---|---|
| 上緣 | J1：24P 0.5mm 翻蓋 FPC 座 | 面板排線從上緣插入 |
| 下緣 | J2：1×8 穿孔焊點，2.0mm 間距、孔徑 0.8mm（不貼片） | 線從孔穿過再焊，比表面焊盤耐拉；pin 1 方形焊墊，從零件面看在左邊 |

### J2 腳位與 Super Mini 接法

腳位順序同 DESPI-C02 的 8pin 排針，原本的接線說明可以直接沿用。Super Mini 這端的 GPIO 同 `esp32c3_spi_display`（`main/epaper_driver.h`）。

**注意**：`esp32c3_spi_display/PIN_MIGRATION.md` 已定案把 MOSI 從 IO3 改到 IO7（IO3 留給喚醒按鈕）。韌體改完後，J2 pin 3 SDI 要改接 **IO7**。

| J2 | 訊號 | ESP32-C3 Super Mini |
|---|---|---|
| 1 | 3.3V | 3.3 |
| 2 | GND | G |
| 3 | SDI (MOSI) | IO3（改腳位後 IO7） |
| 4 | SCLK | IO2 |
| 5 | CS | IO10 |
| 6 | D/C | IO4 |
| 7 | RES | IO5 |
| 8 | BUSY | IO6 |

板子背面印了腳位表，每個焊點上方也有標示（3V3 GND SDI SCK CS DC RES BSY）。

接線建議：
- 線長盡量 **20 cm 以內**；SCLK、SDI 旁邊最好有 GND 線（例如用 8 芯排線，GND 夾在中間），線長一點就把 SPI 時脈調低（例如 4 MHz）。
- 3V3、GND 用 26 AWG 以上；面板刷新時升壓電路瞬間電流較大。
- 焊好後用膠固定線材出口，避免拉扯焊點。

## 電路

照原廠原理圖 `DESPI-C02_SCH V1.0`（2018.07.06）。

| 項目 | DESPI-C02 | 本板 |
|---|---|---|
| RESE 電阻 | DIP 切 0.47Ω / 3Ω（新版 2.2Ω） | **固定 0.47Ω**（GDEQ0426T82 目前 DIP 撥 0.47） |
| BS | R4 3Ω 接地 + R5 10k 上拉 | 直接接地（4 線 SPI） |
| 二極體 | MBR0530（SOD-123） | B5819WS（SOD-323，40V 1A） |
| 電感 | 10µH 1A | 10µH、2520 封裝、Isat ≥ 1A |
| 高壓電容 | 4.7µF/25V | 4.7µF/25V **0805**（JLC Basic C1779） |
| 低壓電容 | 1µF/50V | 1µF/25V **0402**（VDD、VPP、VCOM、3V3 都在 10V 以下） |
| Q1 升壓開關 | Si1308EDL（SC-70） | **AO3400A**（SOT-23，30V 5.7A，JLC Basic） |
| 8pin 排針、DIP 開關、LDO | 有 | 拿掉；排針換成 8 個穿孔焊點 |

**換別的面板**要先查它規格書的 RESE 值；0.47Ω 不一定適用所有面板。

## 版本

- v1.0（2026-10-30）：JST SH 8P 座、Si1308EDL、0603 高壓電容，18 × 21.5 mm。沒有打樣，檔案在 git 歷史。
- v1.1（2026-11-01）：為了降低 JLC 換料費，J2 改成手焊焊點，Q1 改 AO3400A、高壓電容改 0805，Extended 料從 6 種降到 3 種；板長縮到 19.9 mm。剩下的 J1、L1、R2 也不給 JLC 貼，改手焊，貼片全部是 Basic 料。

## 驗證結果

- **DRC：0 違規、0 未連接**（JLCPCB 2 層標準製程：線寬／線距 ≥ 0.127 mm、過孔 0.5／0.3 mm、銅箔到板邊 ≥ 0.3 mm）
- **ERC：0 違規**
- **電路圖與 PCB 的 21 條網路逐條比對，完全一致**（`kicad/compare_nets.py`）
- 二極體方向已在 3D 預覽核對（D3 陰極接 PREVGH、D1 陰極接 NEG、D2 陰極接 GND）
- DRC 剩 1 個 connection_width **警告**（FPC pin 15/16 兩個 3V3 焊墊之間），實際銅寬 0.3 mm，判斷為 KiCad 誤判；不是錯誤
- 還沒打樣，沒有實際上電驗證

## 下單前要確認

1. **FPC 座的接觸面（上接 / 下接）**：BOM 選的 C262567（AFC07-S24FCA-00）是**下接**。拿現在那塊 DESPI-C02 對照，排線金手指朝哪面、FPC 座是哪一型。選錯的話腳位會整排反過來。
2. **FPC 座外形**：footprint 用 KiCad 內建的 `Jushuo_AFC07-S24FCA-00`。
3. **電感**：已選 Sunlord WPN252012H100MT（C98353，Isat 1.1A）。
4. **LCSC 料號已填**（2026-10-30 查 JLC 料庫）。上傳 BOM 後看缺料和 Basic / Extended 標示，缺料時照「規格」欄換同封裝。
5. JLCPCB 貼片預覽要檢查 **D1~D3 的方向**（陰極色帶）、**Q1 的旋轉角度**。J1、L1、R2、J2 不貼片，不會出現在 BOM / CPL（鋼網照樣會在這些焊墊上錫膏，回來是預上錫的狀態，手焊比較好焊）。
6. **手焊料**：J1（C262567）、L1（C98353）、R2（C423162）自己買，可以跟板子同一張 LCSC 訂單一起買，多買幾顆備用。

## 檔案

| 檔案 | 內容 |
|---|---|
| `EPD24_Mini_Adapter_v1.1_Gerber.zip` | Gerber + 鑽孔，直接上傳板廠 |
| `BOM.md` | 零件清單（貼片零件、另購料、挑料注意） |
| `BOM_JLCPCB_v1.1.csv` / `CPL_JLCPCB_v1.1.csv` | JLCPCB 貼片用 BOM、座標檔 |
| `EPD24_Mini_Adapter_schematic.pdf` | 電路圖 |
| `pcb_3d_top.png` / `pcb_3d_bottom.png` | 3D 預覽 |
| `kicad/` | KiCad 專案與產生程式 |

下單參數：2 層、FR-4、板厚 1.0mm 或 1.6mm 皆可、1oz、無鉛噴錫。

## 重新產生

在 `kicad/` 資料夾：

```bash
"D:\Program Files\KiCad\bin\python.exe" build_pcb.py --route
```

| 檔案 | 用途 |
|---|---|
| `build_pcb.py` | 放零件、網路、板框、絲印、設計規則、接地過孔（加 `--route` 會接著佈線；某條網路走不通會自動移到最前面重試） |
| `route.py` | 格點自動佈線（格點 0.05mm）、GND 縫合過孔、鋪銅 |
| `gen_sch.py` | 產生電路圖（`python gen_sch.py`） |
| `drc_summary.py` | 跑 DRC 並印摘要 |
| `compare_nets.py` | 電路圖網路表 vs PCB 比對（先 `kicad-cli sch export netlist -o sch.net`） |
| `export_fab.py` | 匯出 Gerber zip、BOM（CSV + `BOM.md`）、CPL、電路圖 PDF、3D 預覽 |

## 韌體備註

- `esp32c3_spi_display/main/epaper_driver.h` 的 `PIN_MISO` 和 `PIN_RST` 都設成 GPIO5。面板不需要 MISO，建議 SPI 設定改成 `miso_io_num = -1`，免得干擾 RES。
