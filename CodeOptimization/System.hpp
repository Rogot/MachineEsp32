#ifndef SYSTEM_HPP_
#define SYSTEM_HPP_

// Пины для светодиода (для индикации)
#define LED_PIN 4  // Встроенный светодиод на ESP32-CAM

// Функция управления светодиодом (количество раз в период, период)
void blinkLED(int count, int delayTime) 
{
  for (int i = 0; i < count * 2; i++) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    delay(delayTime);
  }
}

#endif /// SYSTEM_HPP_