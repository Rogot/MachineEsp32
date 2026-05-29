// Подключаем необходимые библиотеки
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "Prokuratura";      // Название Wi-Fi сети
const char* password = "femida19052002";      // Пароль от Wi-Fi

// Пины для светодиода (для индикации)
#define LED_PIN 4  // Встроенный светодиод на ESP32-CAM

void setup() {
  // Инициализация последовательного порта для отладки
  Serial.begin(115200);
  Serial.println("Инициализация");
  // Настройка светодиода
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  connectToWiFi();
}

void loop() {

}

// Функция подключения к Wi-Fi
void connectToWiFi() {
  Serial.println();
  Serial.print("Подключаемся к Wi-Fi сети: ");
  Serial.println(ssid);
  
  // Включаем Wi-Fi
  WiFi.begin(ssid, password);
  
  // Ждем подключения (максимум 20 секунд)
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    digitalWrite(LED_PIN, !digitalRead(LED_PIN)); // Мигаем светодиодом
    attempts++;
  }
  
  // Проверяем результат
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("Wi-Fi подключен!");
    Serial.print("IP адрес: ");
    Serial.println(WiFi.localIP());
    // digitalWrite(LED_PIN, HIGH); // Включаем светодиод
  } else {
    Serial.println("");
    Serial.println("Не удалось подключиться к Wi-Fi!");
    // digitalWrite(LED_PIN, LOW); // Выключаем светодиод
  }
}
