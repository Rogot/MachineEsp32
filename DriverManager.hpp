#ifndef DRIVERMANAGER_HPP_
#define DRIVERMANAGER_HPP_

class DriverManager {
private:
  // ── Пины моторов
  #define RIGHT_IN1  12
  #define RIGHT_IN2  13
  #define LEFT_IN3   14
  #define LEFT_IN4   15
  #define STATUS_LED 33 

public:
  DriverManager()
  {
  }

  void init()
  {
    pinMode(RIGHT_IN1, OUTPUT); 
    pinMode(RIGHT_IN2, OUTPUT);
    pinMode(LEFT_IN3,  OUTPUT); 
    pinMode(LEFT_IN4,  OUTPUT);
    move(0, 0);
  }

  void move(int leftDir, int rightDir)
  {
    // 1) больше 1 - движение вперед
    // 2) меньше 1 - движение назад
    // 3) 0 - остановка

    // Движение вперед (ЛЕВЫЙ)
    digitalWrite(LEFT_IN3,  leftDir > 0 ? HIGH : LOW);
    // Движение назад (ЛЕВЫЙ)
    digitalWrite(LEFT_IN4,  leftDir < 0 ? HIGH : LOW);
    // Движение вперед (Правый)
    digitalWrite(RIGHT_IN1, rightDir > 0 ? HIGH : LOW);
    // Движение назад (Правый)
    digitalWrite(RIGHT_IN2, rightDir < 0 ? HIGH : LOW);
    
    // Остановка
    if (leftDir == 0)  { 
      digitalWrite(LEFT_IN3, LOW); digitalWrite(LEFT_IN4, LOW); 
    }
    if (rightDir == 0) { 
      digitalWrite(RIGHT_IN1, LOW); digitalWrite(RIGHT_IN2, LOW); 
    }
  }
};

#endif /// DRIVERMANAGER_HPP_