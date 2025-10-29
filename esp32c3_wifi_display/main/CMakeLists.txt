idf_component_register(SRCS "wifi_display_main.c" "epaper_driver.c"
                       INCLUDE_DIRS "."
                       REQUIRES esp_websocket_client esp_wifi esp_driver_spi esp_driver_gpio nvs_flash esp_netif esp_event)
