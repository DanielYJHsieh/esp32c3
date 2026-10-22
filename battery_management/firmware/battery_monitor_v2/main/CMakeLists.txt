idf_component_register(SRCS "battery_monitor_main.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES esp_adc esp_driver_gpio)
