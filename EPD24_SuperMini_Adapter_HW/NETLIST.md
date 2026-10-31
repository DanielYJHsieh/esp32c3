# 網路表（v1.1）

與 `kicad/build_pcb.py` 的 `NETS`、`kicad/gen_sch.py` 一致（`kicad/compare_nets.py` 已比對）。

## 面板 FPC（J1，24P 0.5mm）

| Pin | 名稱 | 網路 | 接到 |
|---|---|---|---|
| 1 | NC | — | 不接 |
| 2 | GDR | GDR | Q1 G、R1 10k 到 GND |
| 3 | RESE | RESE | Q1 S、R2 0.47Ω 到 GND |
| 4 | VGL | VGL | C1 4.7µF |
| 5 | VGH | VGH | C2 4.7µF |
| 6 | TSCL | — | 不接 |
| 7 | TSDA | — | 不接 |
| 8 | BS | GND | 4 線 SPI |
| 9 | BUSY | BUSY | Super Mini IO6 |
| 10 | RES | RES | Super Mini IO5 |
| 11 | D/C | DC | Super Mini IO4 |
| 12 | CS | CS | Super Mini IO10 |
| 13 | SCLK | SCLK | Super Mini IO2 |
| 14 | SDI | SDI | Super Mini IO7 |
| 15 | VDDIO | 3V3 | Super Mini 3V3、C6 1µF |
| 16 | VCI | 3V3 | 同上 |
| 17 | VSS | GND | |
| 18 | VDD | VDD | C7 1µF |
| 19 | VPP | VPP | C8 1µF |
| 20 | VSH | VSH | C9 4.7µF |
| 21 | PREVGH | PREVGH | D3 陰極、C5 4.7µF |
| 22 | VSL | VSL | C10 4.7µF |
| 23 | PREVGL | PREVGL | D1 陽極、C11 4.7µF |
| 24 | VCOM | VCOM | C12 1µF |

## 升壓 / 負壓泵

| 網路 | 接點 |
|---|---|
| 3V3 | L1.1、C4 4.7µF、C6、J1.15/16、J2.3、R7、R8 |
| SW | L1.2、Q1 D、D3 陽極、C3.1 |
| NEG | C3.2、D1 陰極、D2 陽極 |
| GND | D2 陰極、R1、R2、所有電容另一端、J1.8/17、J2.2、U2.2、R3、R4、R6、TP2（電池 −）、TP6（按鍵 G） |

## 電池（v1.1，同電池背板 v2.1）

| 網路 | 接點 |
|---|---|
| VBUS | J2.1（Super Mini 5V）、U2.4 VCC、C13 1µF、R3 100k、Q2 G |
| VBAT | U2.3 BAT、Q2 D、C14 10µF、R5 上端、TP1（電池 +） |
| VSYS | Q2 S、C15 22µF、TP3（飛線到 Super Mini 正面 W5 的 A 端） |
| PROG | U2.5、R4 5.1k 到 GND（196 mA） |
| CHRG | U2.1、J3.7（IO20） |
| VBAT_SENSE | R5 / R6 中點、C16 100nF、J2.8（IO0） |

## 喚醒按鍵（2026-10-31 新增）

| 網路 | 接點 |
|---|---|
| BTN1 | J2.7（IO1）、R7 100k 到 3V3、TP4（K1 焊墊） |
| BTN2 | J2.5（IO3）、R8 100k 到 3V3、TP5（K2 焊墊） |

## Super Mini（J2 / J3，從零件面看）

| J2 腳 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Super Mini | 5V | G | 3V3 | IO4 | IO3 | IO2 | IO1 | IO0 |
| 網路 | VBUS | GND | 3V3 | DC | BTN2 | SCLK | BTN1 | VBAT_SENSE |

| J3 腳 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Super Mini | IO5 | IO6 | IO7 | IO8 | IO9 | IO10 | IO20 | IO21 |
| 網路 | RES | BUSY | SDI | — | — | CS | CHRG | — |
