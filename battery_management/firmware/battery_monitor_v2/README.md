# battery_monitor_v2

對應硬體：[`../../docs/BACKPACK_V2_DESIGN.md`](../../docs/BACKPACK_V2_DESIGN.md)

| GPIO | 功能 |
|------|------|
| GPIO0 | VBAT/2（ADC1_CH0，1M/1M 分壓 + 100nF） |
| GPIO1 | TP4054 CHRG（Low = 充電中，外部 100k 上拉） |

行為：
1. 喚醒後先量 VBAT（WiFi 開啟前的靜置電壓）。
2. VBAT < 3.30 V 且未充電 → 只開「開始充電喚醒」後 deep sleep，不做任何事。
3. 否則執行工作（此範例只印 log，把你的 WiFi / E-Paper 更新放在 `do_work()`），之後定時 deep sleep；未充電時同時開啟「插 USB 開始充電就喚醒」。

```bash
idf.py set-target esp32c3
idf.py build flash monitor
```
