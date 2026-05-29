from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import cgi
import os
import threading
import time
from io import BytesIO
from PIL import Image

# Создаем папки
SAVE_DIR = "captured_frames"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

class ESP32Handler(BaseHTTPRequestHandler):
    frame_count = 0
    start_time = time.time()
    lock = threading.Lock()
    
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            with self.lock:
                uptime = time.time() - self.start_time
                fps = self.frame_count / uptime if uptime > 0 else 0
            
            html = f"""
            <html>
            <head><meta http-equiv="refresh" content="1"></head>
            <body>
                <h1>ESP32-CAM Статистика</h1>
                <p>Получено кадров: {self.frame_count}</p>
                <p>Время работы: {uptime:.1f} сек</p>
                <p>Средний FPS: {fps:.2f}</p>
                <p>Последний кадр: {datetime.now().strftime('%H:%M:%S')}</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path == '/latest':
            # Отдает последний сохраненный кадр
            files = sorted(os.listdir(SAVE_DIR))
            if files:
                latest = files[-1]
                with open(f"{SAVE_DIR}/{latest}", 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-type', 'image/jpeg')
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.end_headers()
        
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <h1>ESP32-CAM Сервер</h1>
            <p>Эндпоинты:</p>
            <ul>
                <li>POST / - отправка кадров</li>
                <li>GET /stats - статистика</li>
                <li>GET /latest - последний кадр</li>
            </ul>
            """
            self.wfile.write(html.encode('utf-8'))
    
    def do_POST(self):
        """Прием кадров от ESP32-CAM"""
        content_type = self.headers.get('Content-Type')
        
        if content_type and 'multipart/form-data' in content_type:
            try:
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
                )
                
                if 'imageFile' in form:
                    file_item = form['imageFile']
                    filename = f"{SAVE_DIR}/frame_{datetime.now().strftime('%H%M%S_%f')}.jpg"
                    
                    with open(filename, 'wb') as f:
                        f.write(file_item.file.read())
                    
                    with self.lock:
                        self.frame_count += 1
                    
                    # Отправляем успешный ответ
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    
                    response = f"OK frame={self.frame_count}"
                    self.wfile.write(response.encode('utf-8'))
                    
                    # Выводим статистику каждые 100 кадров
                    if self.frame_count % 100 == 0:
                        with self.lock:
                            uptime = time.time() - self.start_time
                            fps = self.frame_count / uptime if uptime > 0 else 0
                        print(f"📊 Кадров: {self.frame_count}, FPS: {fps:.2f}")
                        
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"ERROR: No imageFile field")
                    
            except Exception as e:
                print(f"❌ Ошибка обработки: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"ERROR: {str(e)}".encode('utf-8'))

def cleanup_old_frames():
    """Очистка старых кадров (оставляем последние 1000)"""
    while True:
        time.sleep(60)  # Каждую минуту
        files = sorted(os.listdir(SAVE_DIR))
        if len(files) > 1000:
            for old_file in files[:-1000]:
                os.remove(f"{SAVE_DIR}/{old_file}")
            print(f"🧹 Очищено {len(files) - 1000} старых кадров")

def main():
    # Запускаем очистку в фоновом потоке
    cleanup_thread = threading.Thread(target=cleanup_old_frames, daemon=True)
    cleanup_thread.start()
    
    print("=" * 50)
    print("Сервер ESP32-CAM запущен на порту 8080")
    print("=" * 50)
    print("\nЭндпоинты:")
    print("  POST / - прием кадров от ESP32")
    print("  GET  /stats - статистика приема")
    print("  GET  /latest - последний полученный кадр")
    print("\nКадры сохраняются в папку:", SAVE_DIR)
    print("=" * 50)
    
    server = HTTPServer(('0.0.0.0', 8080), ESP32Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
        server.shutdown()

if __name__ == '__main__':
    main()