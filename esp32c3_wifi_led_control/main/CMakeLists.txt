idf_component_register(SRCS "wifi_led_control_main.c"
                       INCLUDE_DIRS "."
                       REQUIRES esp_http_server nvs_flash esp_wifi esp_driver_gpio esp_timer)
