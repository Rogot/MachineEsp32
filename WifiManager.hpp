#ifndef WIFIMANAGER_HPP_
#define WIFIMANAGER_HPP_

#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

#include "System.hpp"

class WifiManager {
private:
    // Настройки Wi-Fi сети
    // const char* ssid = "ИМЯ_ВАШЕЙ_СЕТИ";      // Название Wi-Fi сети
    // const char* password = "ПАРОЛЬ_СЕТИ";      // Пароль от Wi-Fi

    // const char* ssid = "techDesignPr";      // Название Wi-Fi сети
    // const char* password = "Vozneslab";      // Пароль от Wi-Fi
    const char* ssid = "Prokuratura";      // Название Wi-Fi сети
    const char* password = "femida19052002";      // Пароль от Wi-Fi

    // Адрес сервера
    // const char* serverIP = "192.168.14.183"; // Адрес вашего сервера
    const char* serverIP = "192.168.31.20";

public:
    // Переменные для хранения команд с сервера
    struct RobotCommands {
        int leftMotor = 0;   // -1 назад, 0 стоп, 1 вперед
        int rightMotor = 0;  // -1 назад, 0 стоп, 1 вперед
        bool cameraEnabled = false;
        int cameraInterval = 100; // мс между кадрами
    };

public:
    // Замена вида команд с чисел на перечисление (буквенное значение)
    enum class SendFormat {
      ESP_DATA,
      CAMERA_DATA  
    };

public:
    // Конструктор класса WifiManager 
    WifiManager() :
        commands{},
        needUpdate{false}
    {}

    // Обработчик событий wifi
    void process(SendFormat aFormat, camera_fb_t* aFb)
    {
        // проверка подключения
        if (WiFi.status() == WL_CONNECTED) {
            Serial.println("Все еще подключены к Wi-Fi");
            // Доступна ли камера?
            if (commands.cameraEnabled) {
                // Если да, то отправляем изображение
                send(aFormat, aFb);
            }

            // Читаем данные с сервера
            request();
        } else {
            Serial.println("Потеряно соединение с Wi-Fi");
            // Пытаемся пождключиться к WIFI
            connectToWiFi();
        }
    }

    // Обрабатываем сообщения с сервера
    void request()
    {
        Serial.println("\nЗАПРАШИВАЮ ДАННЫЕ С СЕРВЕРА...");
        // Получаем ответ с сервера
        String response =  requestDataFromServer();
        // Если ответ есть, то мы его обрабатываем
        if (response.length() > 0) {
            parseServerCommands(response);
            // и выставляем влаг об обновлении данных
            needUpdate = true;
        }
    }

    // Получить обработанную команду с сервера
    RobotCommands getCommand()
    {
        needUpdate = false;
        return commands;
    }

    // Проверка на наличие новых данных
    bool isNeedUpdate()
    {
        return needUpdate;
    }

    // Отправка данных на сервер (формат сообщения, изображение с камеры - по умолчанию нет)
    void send(SendFormat aFormat, camera_fb_t* aFb = nullptr)
    {
        Serial.println("ОТПРАВКА ДАННЫХ НА СЕРВЕР");
        switch (aFormat)
        {
        // Если отправляем данные об ESP, то один формат отправки
        case SendFormat::ESP_DATA:
            sendEspData();
            break;

        // Если отправляем данные с камеры, то другой
        case SendFormat::CAMERA_DATA:
            sendCapture(aFb);
            break;
        
        default:
            break;
        }
    }

    // Подключение к Wifi
    void connect()
    {
        connectToWiFi();
    }

public:
    // Переменная количества отправленных изображений
  int frameCount{0};


private:
    // Проверка подключения к WiFi
    bool wifiCheck()
    {
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("Ошибка: нет подключения к WiFi!");
            return false;
        }

        return true;
    }

    // Прием всех данных с сервера
    String requestDataFromServer()
    {
        // Проверка подключения к WiFi
        if (!wifiCheck()) {
            return String();
        }
        
        HTTPClient http;
        
        // Запрашиваем данные (GET запрос вместо POST)
        String url = "http://" + String(serverIP) + ":8080/getdata";
        http.begin(url);
        
        int httpCode = http.GET();  // GET запрос
        
        // Получаем ответ с сервера
        String response = http.getString();

        // Если ответ есть, то пишем об этом в консоль
        if(httpCode > 0) {
            Serial.print("Данные получены! Код: ");
            Serial.println(httpCode);
        // При отстутствии ответа тоже
        } else {
            Serial.print("Ошибка запроса: ");
            Serial.println(httpCode);
        }
        
        http.end();
        // Возвращаем запрос
        return response;
    }

    void sendCapture(camera_fb_t* aFb)
    {
        Serial.println("ОТПРАВКА ИЗОБРАЖЕНИЯ");
        if (!wifiCheck()) {
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
        
        // Проверка - смогли ли мы выделить память в ESP32 для запроса
        if (!payload) {
            Serial.println("Ошибка выделения памяти для отправки");
            http.end();
            return;
        }
        
        // Собираем пакет данных воедино
        memcpy(payload, bodyStart.c_str(), bodyStart.length());
        memcpy(payload + bodyStart.length(), aFb->buf, aFb->len);
        memcpy(payload + bodyStart.length() + aFb->len, bodyEnd.c_str(), bodyEnd.length());
        
        // Отправка
        Serial.printf("Отправка кадра #%d (%d байт)... ", frameCount, aFb->len);
        int httpCode = http.POST(payload, totalSize);
        
        // Освобождаем память ESP32
        free(payload);
        
        if (httpCode == 200) {
            String response = http.getString();
            Serial.printf("HTTP %d - %s\n", httpCode, response.c_str());
        } else {
            Serial.printf("HTTP %d\n", httpCode);
        }

        http.end();
        return;
    }

    // в прошлом sendDataToServer - отправка даных об ESP
    void sendEspData()
    {   
        // Проверяем подключение к WiFi
        if (!wifiCheck()) {
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

    // Парсинг команд с сервера
    void parseServerCommands(String response) {
        // Ожидаем формат: "LEFT:1,RIGHT:1,CAM:1,INTERVAL:500"
        int leftIdx = response.indexOf("LEFT:");
        int rightIdx = response.indexOf("RIGHT:");
        int camIdx = response.indexOf("CAM:");
        int intervalIdx = response.indexOf("INTERVAL:");
        
        // Обрабатываем данные, полученные от сервера и заполняем структуру "commands"
        if (leftIdx >= 0) {
            commands.leftMotor = response.substring(leftIdx + 5, response.indexOf(',', leftIdx)).toInt();
        }
        if (rightIdx >= 0) {
            int endIdx = response.indexOf(',', rightIdx);
            if (endIdx < 0) endIdx = response.length();
            commands.rightMotor = response.substring(rightIdx + 6, endIdx).toInt();
        }
        if (camIdx >= 0) {
            commands.cameraEnabled = (response.substring(camIdx + 4, response.indexOf(',', camIdx)).toInt() == 1);
        }
        if (intervalIdx >= 0) {
            commands.cameraInterval = response.substring(intervalIdx + 9).toInt();
        }
        
        Serial.printf("Команды: L=%d, R=%d, CAM=%d, INT=%d\n", 
                        commands.leftMotor, commands.rightMotor, 
                        commands.cameraEnabled, commands.cameraInterval);
    }

private:
    RobotCommands commands; // Хранение состояния команд
    bool needUpdate; // Хранение состояния обновления крманд управления системой
};

#endif /// WIFIMANAGER_HPP_