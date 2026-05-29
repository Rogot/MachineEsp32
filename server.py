from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import random

class ESP32Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запросов (ESP32 запрашивает данные)"""
        if self.path == '/getdata':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            
            # Генерируем тестовые данные
            data = f"""СЕРВЕРНЫЕ ДАННЫЕ:
Время сервера: {datetime.now().strftime('%H:%M:%S')}
Дата: {datetime.now().strftime('%d.%m.%Y')}
Температура CPU: {random.randint(40, 60)}°C
Загрузка памяти: {random.randint(20, 80)}%
Состояние: нормальное
Последнее обновление: {datetime.now().strftime('%H:%M')}
"""
            
            self.wfile.write(data.encode('utf-8'))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Отправлены данные по запросу")
            
        elif self.path == '/':
            # Главная страница
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = "<h1>ESP32 Server</h1><p>Сервер работает</p>"
            self.wfile.write(html.encode('utf-8'))
    
    def do_POST(self):
        """Обработка POST запросов (ESP32 отправляет данные)"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            data = self.rfile.read(content_length).decode('utf-8')
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Данные от ESP32:")
            print(data)
        
        # Отправляем ответ с данными
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        response_text = '✅ Данные получены сервером\n'
        response_text = 'Ты справился!\n'
        response_text += f'Время: {datetime.now().strftime("%H:%M:%S")}\n'
        response_text += 'Статус: OK'
        
        self.wfile.write(response_text.encode('utf-8'))

def main():
    print("Сервер запущен на порту 8080")
    print("ESP32 может:")
    print("  1. Отправлять данные на POST /")
    print("  2. Запрашивать данные GET /getdata")
    
    server = HTTPServer(('', 8080), ESP32Handler)
    server.serve_forever()

if __name__ == '__main__':
    main()