idf_component_register(
    SRCS "spi_display_main.c" "epaper_driver.c"
    INCLUDE_DIRS "."
    REQUIRES driver esp_timer nvs_flash
)
