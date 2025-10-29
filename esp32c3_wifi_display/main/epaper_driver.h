/*
 * GDEQ0426T82 E-Paper Display Driver
 * 4.26" 800x480 Black/White E-Paper Display
 * 
 * Hardware Connection:
 * - SCLK: GPIO 2
 * - MOSI: GPIO 3
 * - CS:   GPIO 10
 * - DC:   GPIO 4
 * - RST:  GPIO 5
 * - BUSY: GPIO 6
 */

#ifndef EPAPER_DRIVER_H
#define EPAPER_DRIVER_H

#include <stdint.h>
#include <stdbool.h>
#include "driver/spi_master.h"
#include "driver/gpio.h"

// Display specifications
#define EPAPER_WIDTH        800
#define EPAPER_HEIGHT       480
#define EPAPER_BUFFER_SIZE  (EPAPER_WIDTH * EPAPER_HEIGHT / 8)  // 48000 bytes

// GPIO Pin definitions
#define PIN_SCLK            2
#define PIN_MOSI            3
#define PIN_MISO            5   // Not used but required for SPI configuration
#define PIN_CS              10
#define PIN_DC              4
#define PIN_RST             5
#define PIN_BUSY            6

// SPI Configuration
#define SPI_HOST_ID         SPI2_HOST
#define SPI_CLOCK_SPEED     (4 * 1000 * 1000)  // 4 MHz

// E-Paper Commands (based on GDEQ0426T82 datasheet)
#define CMD_PANEL_SETTING           0x00
#define CMD_POWER_SETTING           0x01
#define CMD_POWER_OFF               0x02
#define CMD_POWER_ON                0x04
#define CMD_BOOSTER_SOFT_START      0x06
#define CMD_DEEP_SLEEP              0x07
#define CMD_DATA_START_TRANSMISSION 0x10
#define CMD_DATA_STOP                0x11
#define CMD_DISPLAY_REFRESH         0x12
#define CMD_PARTIAL_IN              0x91
#define CMD_PARTIAL_OUT             0x92
#define CMD_PARTIAL_WINDOW          0x90
#define CMD_VCOM_AND_DATA           0x50
#define CMD_TCON_SETTING            0x60
#define CMD_RESOLUTION_SETTING      0x61
#define CMD_GET_STATUS              0x71

// Color definitions
#define COLOR_WHITE         0xFF
#define COLOR_BLACK         0x00

// E-Paper driver structure
typedef struct {
    spi_device_handle_t spi;
    uint8_t *framebuffer;
    bool initialized;
} epaper_t;

// Initialization and control functions
esp_err_t epaper_init(epaper_t *epaper);
esp_err_t epaper_deinit(epaper_t *epaper);
void epaper_reset(void);
void epaper_sleep(epaper_t *epaper);
void epaper_wait_busy(void);

// Low-level communication functions
void epaper_send_command(epaper_t *epaper, uint8_t cmd);
void epaper_send_data(epaper_t *epaper, uint8_t data);
void epaper_send_data_bulk(epaper_t *epaper, const uint8_t *data, size_t len);

// Display update functions
void epaper_clear_screen(epaper_t *epaper, uint8_t color);
void epaper_display_full(epaper_t *epaper);
void epaper_display_partial(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h);

// Framebuffer functions
void epaper_set_pixel(epaper_t *epaper, uint16_t x, uint16_t y, uint8_t color);
uint8_t epaper_get_pixel(epaper_t *epaper, uint16_t x, uint16_t y);
void epaper_fill_rect(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t color);
void epaper_draw_rect(epaper_t *epaper, uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t color);

// Text drawing functions
void epaper_draw_char_8x16(epaper_t *epaper, uint16_t x, uint16_t y, char c, uint8_t color);
void epaper_draw_chinese_16x16(epaper_t *epaper, uint16_t x, uint16_t y, const char *utf8_char, uint8_t color);
void epaper_draw_string(epaper_t *epaper, uint16_t x, uint16_t y, const char *str, uint8_t color);

#endif // EPAPER_DRIVER_H
