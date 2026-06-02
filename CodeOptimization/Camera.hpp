#ifndef CAMSETTINGS_HPP_
#define CAMSETTINGS_HPP_

// перед `#include "esp_camera.h"
#define CAMERA_MODEL_AI_THINKER

#include "soc/soc.h"           // Для отключения детектора понижения питания
#include "soc/rtc_cntl_reg.h"  // Для отключения детектора понижения питания
#include "esp_camera.h"

class Camera {
private:
  // Конфигурация пинов для AI Thinker ESP32-CAM
  #define PWDN_GPIO_NUM     32
  #define RESET_GPIO_NUM    -1
  #define XCLK_GPIO_NUM      0
  #define SIOD_GPIO_NUM     26
  #define SIOC_GPIO_NUM     27
  #define Y9_GPIO_NUM       35
  #define Y8_GPIO_NUM       34
  #define Y7_GPIO_NUM       39
  #define Y6_GPIO_NUM       36
  #define Y5_GPIO_NUM       21
  #define Y4_GPIO_NUM       19
  #define Y3_GPIO_NUM       18
  #define Y2_GPIO_NUM        5
  #define VSYNC_GPIO_NUM    25
  #define HREF_GPIO_NUM     23
  #define PCLK_GPIO_NUM     22

public:
  static const int captureInterval = 100; // Интервал между кадрами в мс (10 FPS)

public:
  // Конструктор класса Camera 
  Camera() 
  {
  }

  void cameraConfig()
  {
    // Настройка пинов и параметров камеры
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM; config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM; config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM; config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM; config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM; config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 10000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.fb_count = 2;
    
    // ПЕРЕХОДИМ НА ПОЛНОЕ РАЗРЕШЕНИЕ
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 12;          // 10-12 — хороший баланс четкости
    config.fb_count = 2;               // 2 буфера для VGA обязательны
    
    // Отключаем детектор понижения питания (важно!)
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
      Serial.printf("Camera init failed: 0x%x", err);
      return;
    }

    // Корректировки для OV3660
    sensor_t * s = esp_camera_sensor_get();
    if (s) {
      s->set_vflip(s, 1);   // Вертикальный переворот
      s->set_hmirror(s, 0); // Горизонтальное отзеркаливание (чтобы право было правом)
    }

    Serial.println("Camera initialized!");
  }
  
  // Получение изображения с камеры с помощью функции
  camera_fb_t* getCupture()
  {
    return esp_camera_fb_get();
  }
};

#endif /// CAMSETTINGS_HPP_