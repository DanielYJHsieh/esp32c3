/*
 * ESP32-C3 SuperMini Battery Backpack v2 - battery monitor example
 *
 * Hardware: battery_management/docs/BACKPACK_V2_DESIGN.md
 *   GPIO0 : VBAT_SENSE = VBAT * R4 / (R3 + R4)  (1M / 1M + 100nF)
 *   GPIO1 : TP4054 CHRG, open-drain, external 100k pull-up to 3V3 (LOW = charging)
 */
#include <stdbool.h>
#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_sleep.h"
#include "esp_log.h"

static const char *TAG = "battery";

#define VBAT_ADC_UNIT       ADC_UNIT_1
#define VBAT_ADC_CHANNEL    ADC_CHANNEL_0           /* GPIO0 */
#define VBAT_ADC_ATTEN      ADC_ATTEN_DB_12         /* ~0-2.5V calibrated range on C3 */
#define VBAT_DIVIDER_RATIO  2.0f                    /* (R3 + R4) / R4 = (1M + 1M) / 1M */
#define VBAT_SAMPLES        16

#define CHRG_GPIO           GPIO_NUM_1

#define VBAT_LOW_WARN_MV    3400
#define VBAT_CUTOFF_MV      3300

#define SLEEP_INTERVAL_S    (12ULL * 60 * 60)       /* twice a day */

RTC_DATA_ATTR static uint32_t s_boot_count;

/* LiPo resting voltage -> state of charge (approximate) */
static const struct { int mv; int pct; } s_soc_table[] = {
    {4200, 100}, {4100, 90}, {4000, 80}, {3920, 70}, {3850, 60}, {3800, 50},
    {3750, 40},  {3710, 30}, {3680, 20}, {3600, 10}, {3450, 5},  {3300, 0},
};

static int vbat_to_percent(int mv)
{
    const int n = sizeof(s_soc_table) / sizeof(s_soc_table[0]);
    if (mv >= s_soc_table[0].mv) {
        return 100;
    }
    for (int i = 1; i < n; i++) {
        if (mv >= s_soc_table[i].mv) {
            int hi_mv = s_soc_table[i - 1].mv, hi_pct = s_soc_table[i - 1].pct;
            int lo_mv = s_soc_table[i].mv, lo_pct = s_soc_table[i].pct;
            return lo_pct + (mv - lo_mv) * (hi_pct - lo_pct) / (hi_mv - lo_mv);
        }
    }
    return 0;
}

static bool is_charging(void)
{
    return gpio_get_level(CHRG_GPIO) == 0;
}

/* Returns battery voltage in mV, or -1 on error. */
static int read_vbat_mv(void)
{
    adc_oneshot_unit_handle_t adc;
    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = VBAT_ADC_UNIT,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&unit_cfg, &adc));

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten = VBAT_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc, VBAT_ADC_CHANNEL, &chan_cfg));

    adc_cali_handle_t cali = NULL;
    adc_cali_curve_fitting_config_t cali_cfg = {
        .unit_id = VBAT_ADC_UNIT,
        .chan = VBAT_ADC_CHANNEL,
        .atten = VBAT_ADC_ATTEN,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    if (adc_cali_create_scheme_curve_fitting(&cali_cfg, &cali) != ESP_OK) {
        ESP_LOGW(TAG, "ADC calibration not available (eFuse not burnt?)");
        cali = NULL;
    }

    int sum_mv = 0;
    int valid = 0;
    for (int i = 0; i < VBAT_SAMPLES; i++) {
        int raw = 0;
        int mv = 0;
        if (adc_oneshot_read(adc, VBAT_ADC_CHANNEL, &raw) != ESP_OK) {
            continue;
        }
        if (cali) {
            adc_cali_raw_to_voltage(cali, raw, &mv);
        } else {
            mv = raw * 2500 / 4095;     /* rough fallback */
        }
        sum_mv += mv;
        valid++;
        /* 1M || 1M = 500k source impedance: give C4 time to recover between samples */
        vTaskDelay(pdMS_TO_TICKS(2));
    }

    if (cali) {
        adc_cali_delete_scheme_curve_fitting(cali);
    }
    adc_oneshot_del_unit(adc);

    if (valid == 0) {
        return -1;
    }
    return (int)((float)sum_mv / valid * VBAT_DIVIDER_RATIO);
}

static void do_work(int vbat_mv, bool charging)
{
    /* Put WiFi / E-Paper update here. */
    ESP_LOGI(TAG, "Working... (vbat=%d mV, charging=%d)", vbat_mv, charging);
    vTaskDelay(pdMS_TO_TICKS(1000));
}

static void enter_deep_sleep(bool timer_wakeup)
{
    if (timer_wakeup) {
        ESP_ERROR_CHECK(esp_sleep_enable_timer_wakeup(SLEEP_INTERVAL_S * 1000000ULL));
    }
    /* Wake when charging starts (CHRG goes LOW). Only arm it while not charging,
     * otherwise the level-triggered wakeup would fire immediately. */
    if (!is_charging()) {
        ESP_ERROR_CHECK(esp_deep_sleep_enable_gpio_wakeup(BIT64(CHRG_GPIO),
                                                          ESP_GPIO_WAKEUP_GPIO_LOW));
    }
    ESP_LOGI(TAG, "Deep sleep (timer=%d)", timer_wakeup);
    esp_deep_sleep_start();
}

void app_main(void)
{
    s_boot_count++;

    gpio_config_t io = {
        .pin_bit_mask = BIT64(CHRG_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,      /* external 100k pull-up */
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&io));

    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    bool charging = is_charging();
    int vbat_mv = read_vbat_mv();   /* measure before WiFi is turned on */

    ESP_LOGI(TAG, "boot #%lu, wake cause=%d, VBAT=%d mV (%d%%)%s",
             (unsigned long)s_boot_count, cause, vbat_mv, vbat_to_percent(vbat_mv),
             charging ? ", charging (reading is elevated)" : "");

    if (vbat_mv >= 0 && vbat_mv < VBAT_CUTOFF_MV && !charging) {
        ESP_LOGW(TAG, "Battery below cutoff, sleeping until charger is connected");
        enter_deep_sleep(false);
    }
    if (vbat_mv >= 0 && vbat_mv < VBAT_LOW_WARN_MV && !charging) {
        ESP_LOGW(TAG, "Battery low");
    }

    do_work(vbat_mv, charging);
    enter_deep_sleep(true);
}
