/*
 * 電池背板 v2.1 實板測試（Arduino，ESP32-C3 SuperMini）
 *
 * 腳位（2026-10-31 起）：
 *   GPIO0  : VBAT/2（R3/R4 1M/1M + C4 100nF）
 *   GPIO20 : TP4054 CHRG，開漏，內部上拉（LOW = 充電中）
 *   GPIO8  : 板上藍色 LED（LOW = 亮），每秒閃一下表示還在跑
 *
 * 每 2 秒量一次，透過 USB 序列埠印出，同時存進 RAM 紀錄。
 * 拔掉 USB 改用電池時序列埠會斷，但程式繼續跑；插回 USB 後輸入 d 印出這段期間的紀錄。
 * 開機次數（boot）沒變、uptime 一直往上 = 拔插 USB 時沒有重開。
 *
 * 編譯 / 上傳：
 *   arduino-cli compile --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc -u -p <COM> battery_test_v2
 */
#include <Arduino.h>

#define VBAT_PIN      0
#define CHRG_PIN      20
#define LED_PIN       8
#define DIVIDER       2.0f
#define SAMPLES       16
#define PERIOD_MS     2000
#define LOG_LEN       600          // 2 s × 600 = 20 分鐘

struct Rec { uint32_t t; uint16_t mv; uint8_t chrg; };
static Rec logbuf[LOG_LEN];
static uint16_t log_head = 0, log_count = 0;
RTC_DATA_ATTR static uint32_t boot_count = 0;

static int read_vbat_mv()
{
  uint32_t sum = 0;
  for (int i = 0; i < SAMPLES; i++) sum += analogReadMilliVolts(VBAT_PIN);
  return (int)(sum / SAMPLES * DIVIDER);
}

static void print_rec(const Rec &r)
{
  Serial.printf("t=%6lus  VBAT=%4u mV  CHRG=%s\n", (unsigned long)r.t, r.mv,
                r.chrg ? "LOW (charging)" : "HIGH (not charging)");
}

static void dump_log()
{
  Serial.printf("---- log: %u records (boot #%lu) ----\n", log_count, (unsigned long)boot_count);
  uint16_t start = (log_head + LOG_LEN - log_count) % LOG_LEN;
  for (uint16_t i = 0; i < log_count; i++) print_rec(logbuf[(start + i) % LOG_LEN]);
  Serial.println("---- end ----");
}

void setup()
{
  boot_count++;
  Serial.begin(115200);
  pinMode(CHRG_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  analogSetPinAttenuation(VBAT_PIN, ADC_11db);
  delay(1500);  // 等 USB CDC 連上
  Serial.printf("\nbattery_test_v2  boot #%lu  reset reason=%d\n", (unsigned long)boot_count, (int)esp_reset_reason());
  Serial.println("指令：d = 印出紀錄，c = 清除紀錄");
}

void loop()
{
  static uint32_t last = 0;
  uint32_t now = millis();

  digitalWrite(LED_PIN, (now % 1000) < 100 ? LOW : HIGH);

  if (Serial.available()) {
    char c = Serial.read();
    if (c == 'd') dump_log();
    if (c == 'c') { log_count = 0; Serial.println("log cleared"); }
  }

  if (now - last >= PERIOD_MS) {
    last = now;
    Rec r = { now / 1000, (uint16_t)read_vbat_mv(), (uint8_t)(digitalRead(CHRG_PIN) == LOW) };
    logbuf[log_head] = r;
    log_head = (log_head + 1) % LOG_LEN;
    if (log_count < LOG_LEN) log_count++;
    if (Serial) print_rec(r);
  }
}
