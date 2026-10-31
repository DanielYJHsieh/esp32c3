# battery_monitor_v2

對應硬體：[`../../docs/BACKPACK_V2_DESIGN.md`](../../docs/BACKPACK_V2_DESIGN.md)

| GPIO | 功能 |
|------|------|
| GPIO0 | VBAT/2（ADC1_CH0，1M/1M 分壓 + 100nF） |
| GPIO20 | TP4054 CHRG（Low = 充電中，內部上拉；R5 選配）。2026-10-31 由 GPIO1 改過來，GPIO1 留給 deep sleep 喚醒按鈕 |

行為：
1. 喚醒後先量 VBAT（WiFi 開啟前的靜置電壓）。
2. VBAT < 3.30 V 且未充電 → 不做任何事，deep sleep 1 小時後再檢查。
3. 否則執行工作（此範例只印 log，把你的 WiFi / E-Paper 更新放在 `do_work()`），之後 deep sleep 12 小時。

只用計時器喚醒：C3 只有 GPIO0–5 能從 deep sleep 喚醒，CHRG 改到 GPIO20 後就不能「插 USB 開始充電就喚醒」。

實板測試（不需要 ESP-IDF）：[`../battery_test_v2`](../battery_test_v2)，Arduino，每 2 秒印 VBAT 與 CHRG，拔 USB 期間的紀錄存在 RAM。

```bash
idf.py set-target esp32c3
idf.py build flash monitor
```
