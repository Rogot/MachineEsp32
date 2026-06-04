// Подключаем необходимые библиотеки
#include "DriverManager.hpp"
#include "Camera.hpp"
#include "WifiManager.hpp"
#include <esp_task_wdt.h> // Для работы с потоками

// Объявление переменных управление WiFi, камерой и двигателем
WifiManager wifi;
Camera camera;
DriverManager driver;

TickType_t frameInterval = pdMS_TO_TICKS(Camera::captureInterval);
int frameCount = 0;

// Мьютекс для доступа к WiFi (разделяемый ресурс)
SemaphoreHandle_t wifiMutex = NULL;

// Задача управления моторами (ядро 0, приоритет 3)
void taskDriver(void *pvParameters) {
  while (true) {
    // Если Wi-Fi подключен
    if (wifi.wifiCheck()) {
      // Захватываем мьютекс с таймаутом 1 секунда
      if (xSemaphoreTake(wifiMutex, pdMS_TO_TICKS(1000)) == pdTRUE) {
        // Считываем запрос сервера
        wifi.request();
        // Проверяем, пришла ли новая команда с сервера на управление двигателем
        if (wifi.isNeedUpdate()) {
          // Получаем команду
          WifiManager::RobotCommands commands = wifi.getCommand();
          // Управляем моторами
          driver.move(commands.leftMotor, commands.rightMotor);
        }
        
        xSemaphoreGive(wifiMutex);
      }
    }
    vTaskDelay(pdMS_TO_TICKS(200));          // опрос каждые 200 мс
  }
}

// Задача камеры и отправки кадров (ядро 1, приоритет 1)
void taskCamera(void *pvParameters) {
  while (true) {
    // Получение изображения с камеры
    camera_fb_t* fb = camera.getCupture();
    // Если изображения нет, то выходим из функции
    if (!fb) {
      Serial.println("Ошибка захвата кадра");
      return;
    }

    // Увеличение счетчика кадров
    frameCount++;
    wifi.frameCount = frameCount;
    
    // Отправка изображения
    if (wifi.wifiCheck()) {
      if (wifi.isNeedUpdate()) {
          // Получаем команду
          WifiManager::RobotCommands commands = wifi.getCommand();
          frameInterval = pdMS_TO_TICKS(commands.cameraInterval);
      }
      // Захватываем мьютекс перед отправкой
      if (xSemaphoreTake(wifiMutex, pdMS_TO_TICKS(2000)) == pdTRUE) {
        wifi.send(WifiManager::SendFormat::CAMERA_DATA, fb);
        xSemaphoreGive(wifiMutex);
      }
    }
    // ОБЯЗАТЕЛЬНО освобождаем буфер
    esp_camera_fb_return(fb);
    // Задержка между кадрами (10 fps)
    vTaskDelay(frameInterval);
  }
}

void setup() {
  // Инициализация последовательного порта для отладки
  Serial.begin(115200);
  Serial.println("Инициализация");
  // Настройка светодиода
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("\n=== ESP32-CAM Потоковая передача ===");
  Serial.println("Разрешение: 640x480 VGA");
  Serial.printf("FPS: примерно %d\n", 1000 / Camera::captureInterval);

  // Конфигурация камеры
  camera.cameraConfig();

  Serial.println("=== Инициализация Wi-Fi ===");
  // Подключение к Wi-Fi
  wifi.connect();

  Serial.println("=== Инициализация двигателей ===");
  // Инициализация двигателей (пинов, отвечающих за их управление)
  driver.init();

  // Создаём мьютекс для защиты WiFi
  wifiMutex = xSemaphoreCreateMutex();
  if (wifiMutex == NULL) {
    Serial.println("Не удалось создать мьютекс");
    return;
  }

  // Задача управления моторами (ядро 0, приоритет 2 – чуть выше камеры)
  xTaskCreatePinnedToCore(
    taskDriver,
    "MotorDriver",
    4096,          // стек (байт)
    NULL,
    2,             // приоритет
    NULL,
    0              // ядро 0
  );

  // Задача отправки кадров (ядро 1, приоритет 1)
  xTaskCreatePinnedToCore(
    taskCamera,
    "CameraSend",
    8192,          // увеличенный стек для работы с буфером кадра
    NULL,
    1,             // приоритет
    NULL,
    1              // ядро 1
  );
  esp_task_wdt_config_t wdt_config = {
      .timeout_ms = 10000,
      .trigger_panic = false,   // не вызывать панику, просто перезагрузить
  };
  esp_task_wdt_init(&wdt_config);
  esp_task_wdt_add(NULL);
}

void loop() {
  esp_task_wdt_reset(); // сообщаем, что всё работает

  // Пусто – всё обрабатывается в задачах
  vTaskDelay(pdMS_TO_TICKS(1000));
}