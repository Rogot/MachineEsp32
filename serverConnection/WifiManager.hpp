#ifndef WIFIMANAGER_HPP_
#define WIFIMANAGER_HPP_

// Подключаем необходимые библиотеки
#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

#include "System.hpp"

class WifiManager {
private:
    // Настройки Wi-Fi сети
    // const char* ssid = "ИМЯ_ВАШЕЙ_СЕТИ";      // Название Wi-Fi сети
    // const char* password = "ПАРОЛЬ_СЕТИ";      // Пароль от Wi-Fi

    const char* ssid = "techDesignPr";      // Название Wi-Fi сети
    const char* password = "Vozneslab";      // Пароль от Wi-Fi

    // Адрес сервера
    const char* serverIP = "192.168.14.183"; // Адрес вашего сервера

public:
    enum class SendFormat {
        ESP_DATA = 0,
        CAMERA_DATA
    };

    int frameCount{0};

public:
    WifiManager()
    {

    }

    void process(SendFormat aFormat, camera_fb_t* aFb = nullptr)
    {
        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("Все еще подключены к Wi-Fi");
            send(aFormat, aFb);

            requset();
        } else {
            Serial.println("Потеряно соединение с Wi-Fi");
            connect();
        }
    }

    void requset()
    {
        Serial.println("\nЗАПРАШИВАЮ ДАННЫЕ С СЕРВЕРА...");
        requestDataFromServer();
    }

    void send(SendFormat aFormat, camera_fb_t* aFb = nullptr)
    {
        Serial.println("ОТПРАВКА ДАННЫХ НА СЕРВЕР");

        switch (aFormat)
        {
        case SendFormat::ESP_DATA:
            sendEspData();
            break;

        case SendFormat::CAMERA_DATA:
            sendCapture(aFb);
            break;

        default:
            break;
        }

    }

    void connect()
    {
        connectToWiFi();
    }

private:
    void sendCapture(camera_fb_t* aFb)
    {
        Serial.println("ОТПРАВКА ИЗОБРАЖЕНИЯ");
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("Ошибка: нет подключения к WiFi!");
            return;
        }

        HTTPClient http;

        String url = "http://" + String(serverIP) + ":8080";
        http.begin(url);
        http.setTimeout(5000); // Таймаут 5 секунд
       
        // Подготовка multipart/form-data
        String boundary = "ESP32CAM-" + String(millis());
        String contentType = "multipart/form-data; boundary=" + boundary;
        http.addHeader("Content-Type", contentType);
       
        // Формирование тела запроса
        String bodyStart = "--" + boundary + "\r\n";
        bodyStart += "Content-Disposition: form-data; name=\"imageFile\"; filename=\"frame_" +
                    String(frameCount) + ".jpg\"\r\n";
        bodyStart += "Content-Type: image/jpeg\r\n\r\n";
       
        String bodyEnd = "\r\n--" + boundary + "--\r\n";
       
        // Сборка полного пакета
        size_t totalSize = bodyStart.length() + aFb->len + bodyEnd.length();
        uint8_t* payload = (uint8_t*)malloc(totalSize);
       
        if (!payload) {
            Serial.println("Ошибка выделения памяти для отправки");
            http.end();
            return;
        }
       
        memcpy(payload, bodyStart.c_str(), bodyStart.length());
        memcpy(payload + bodyStart.length(), aFb->buf, aFb->len);
        memcpy(payload + bodyStart.length() + aFb->len, bodyEnd.c_str(), bodyEnd.length());
       
        // Отправка
        Serial.printf("Отправка кадра #%d (%d байт)... ", frameCount, aFb->len);
        int httpCode = http.POST(payload, totalSize);
       
        free(payload);
       
        if (httpCode == 200) {
            String response = http.getString();
            Serial.printf("HTTP %d - %s\n", httpCode, response.c_str());
            http.end();
            return;
        } else {
            Serial.printf("HTTP %d\n", httpCode);
            http.end();
            return;
        }
    }

    void requestDataFromServer()
    {
        if(WiFi.status() != WL_CONNECTED) {
            Serial.println("Нет WiFi!");
            return;
        }
        
        HTTPClient http;
        
        // Запрашиваем данные (GET запрос вместо POST)
        String url = "http://" + String(serverIP) + ":8080/getdata";
        http.begin(url);
        
        int httpCode = http.GET();  // GET запрос
        
        if(httpCode > 0) {
            Serial.print("Данные получены! Код: ");
            Serial.println(httpCode);
            
            String response = http.getString();
            
            Serial.println("\nДАННЫЕ С СЕРВЕРА:");
            Serial.println("=====================");
            
            // Выводим красиво
            Serial.println(response);
            
        } else {
            Serial.print("Ошибка запроса: ");
            Serial.println(httpCode);
        }
        
        http.end();
    }

    void sendEspData()
    {
        // Проверяем подключение к WiFi
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("Ошибка: нет подключения к WiFi!");
            return;
        }
        
        // Создаем объект HTTPClient
        HTTPClient http;
        
        // Формируем URL сервера
        String url = "http://" + String(serverIP) + ":8080";
        
        // Начинаем соединение
        http.begin(url);
        
        // Устанавливаем заголовки
        http.addHeader("Content-Type", "text/plain");
        http.addHeader("Connection", "close");
        
        // Собираем данные для отправки
        String postData = "";
        postData += "========= ДАННЫЕ ESP32-CAM =========\n";
        postData += "Устройство: ESP32-CAM\n";
        postData += "MAC адрес: " + WiFi.macAddress() + "\n";
        postData += "IP адрес: " + WiFi.localIP().toString() + "\n";
        postData += "Время работы: " + String(millis() / 1000) + " сек\n";
        postData += "===================================\n";
        
        // Выводим данные в Serial для отладки
        Serial.println("Отправляемые данные:");
        Serial.println(postData);
        
        // Отправляем POST запрос
        Serial.print("Отправка... ");
        int httpCode = http.POST(postData);
        
        // Проверяем результат
        if (httpCode > 0) {
            Serial.print("Успешно! Код: ");
            Serial.println(httpCode);
            
            // Получаем ответ сервера
            String response = http.getString();
            Serial.print("Ответ сервера: ");
            Serial.println(response);

        } else {
            Serial.print("Ошибка! Код: ");
            Serial.println(httpCode);
            Serial.print("Сообщение: ");
            Serial.println(http.errorToString(httpCode));
        }
        
        // Закрываем соединение
        http.end();
    }

    // Функция подключения к Wi-Fi
    void connectToWiFi() 
    {
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
            digitalWrite(LED_PIN, LOW); // Включаем светодиод
        } else {
            Serial.println("");
            Serial.println("Не удалось подключиться к Wi-Fi!");
            digitalWrite(LED_PIN, LOW); // Выключаем светодиод
        }
    }

};

#endif /// WIFIMANAGER_HPP_