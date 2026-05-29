// Подключаем необходимые библиотеки
#include "DriverManager.hpp"
#include "Camera.hpp"
#include "WifiManager.hpp"

WifiManager wifi;
Camera camera;
DriverManager driver;

unsigned long lastCaptureTime = 0;
int frameCount = 0;

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

  camera.cameraConfig();

  Serial.println("=== Инициализация Wi-Fi ===");
  wifi.connect();

  Serial.println("=== Инициализация двигателей ===");
  driver.init();
}

void cameraHandler()
{
  unsigned long currentTime = millis();

  // Захват кадра по таймеру
  if (currentTime - lastCaptureTime >= Camera::captureInterval) {
    lastCaptureTime = currentTime;
    
    camera_fb_t* fb = camera.getCupture();
    if (!fb) {
      Serial.println("Ошибка захвата кадра");
      return;
    }
    
    frameCount++;

    wifi.frameCount = frameCount;
    wifi.process(WifiManager::SendFormat::CAMERA_DATA, fb);
    
    // ОБЯЗАТЕЛЬНО освобождаем буфер
    esp_camera_fb_return(fb);
    
    // Статистика
    if (frameCount % 50 == 0) {
      Serial.printf("\nСтатистика: отправлено %d кадров\n", frameCount);
      Serial.printf("Свободная куча: %d байт\n", ESP.getFreeHeap());
      Serial.printf("Свободная PSRAM: %d байт\n\n", ESP.getFreePsram());
    }
  }
}

void driverHandler()
{
  if (wifi.isNeedUpdate()) {
    WifiManager::RobotCommands commands = wifi.getCommand();
    driver.move(commands.leftMotor, commands.rightMotor);
  }
}

void loop() {

  cameraHandler();
  driverHandler();
}