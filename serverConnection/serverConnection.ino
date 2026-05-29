#include "WifiManager.hpp"
#include "Camera.hpp"

WifiManager wifi;
Camera camera;

unsigned long lastCaptureTime = 0;
int frameCount = 0;

void setup() {
  // Инициализация последовательного порта для отладки
  Serial.begin(115200);
  Serial.println("Инициализация");
  // Настройка светодиода
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  camera.configure();
  wifi.connect();
}

void loop() 
{
  unsigned long currentTime = millis();

  if (currentTime - lastCaptureTime >= Camera::captureInterval) {
    lastCaptureTime = currentTime;

    camera_fb_t *fb = camera.getCapture();
    if (!fb) {
      Serial.println("Ошибка захвата кадра");
      return;
    }

    frameCount++;

    wifi.frameCount = frameCount;
    wifi.process(WifiManager::SendFormat::CAMERA_DATA, fb);

    camera.clearBuffer(fb);
  }

  delay(5000);
}


