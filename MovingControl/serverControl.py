from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import cgi
import os
import json
import threading
import time
from urllib.parse import parse_qs, urlparse

SAVE_DIR = "captured_frames"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

class RobotController:
    """Класс для управления роботом"""
    def __init__(self):
        self.commands = {
            "left": 0,    # -1 назад, 0 стоп, 1 вперед
            "right": 0,
            "camera": 0,  # 1 вкл, 0 выкл
            "interval": 100  # мс между кадрами
        }
        self.lock = threading.Lock()
    
    def set_motors(self, left, right):
        """Установка скорости моторов"""
        with self.lock:
            self.commands["left"] = max(-1, min(1, left))
            self.commands["right"] = max(-1, min(1, right))
    
    def set_camera(self, enabled, interval=1000):
        """Управление камерой"""
        with self.lock:
            self.commands["camera"] = 1 if enabled else 0
            self.commands["interval"] = max(100, min(5000, interval))
    
    def get_commands_string(self):
        """Получение команд в формате для ESP32"""
        with self.lock:
            return f"LEFT:{self.commands['left']},RIGHT:{self.commands['right']},CAM:{self.commands['camera']},INTERVAL:{self.commands['interval']}"
    
    def get_commands_json(self):
        """Получение команд в JSON формате"""
        with self.lock:
            return json.dumps(self.commands)

class ESP32Handler(BaseHTTPRequestHandler):
    frame_count = 0
    start_time = time.time()
    lock = threading.Lock()
    
    # Создаем глобальный контроллер робота
    robot = RobotController()
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/getdata':
            # ESP32 запрашивает команды
            commands = self.robot.get_commands_string()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(commands.encode('utf-8'))
            
        elif path == '/status':
            # Статус робота
            with self.lock:
                uptime = time.time() - self.start_time
                fps = self.frame_count / uptime if uptime > 0 else 0
            
            status = {
                "frames_received": self.frame_count,
                "uptime_seconds": round(uptime, 1),
                "average_fps": round(fps, 2),
                "robot_commands": json.loads(self.robot.get_commands_json())
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode('utf-8'))
            
        elif path == '/control':
            # Веб-интерфейс управления
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_control_page().encode('utf-8'))
            
        elif path == '/latest':
            # Последний кадр
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
                
        elif path == '/api/move':
            # API для движения: /api/move?left=1&right=1
            params = parse_qs(parsed_path.query)
            left = int(params.get('left', [0])[0])
            right = int(params.get('right', [0])[0])
            
            self.robot.set_motors(left, right)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "left": left, "right": right}).encode('utf-8'))
            
        elif path == '/api/camera':
            # API для камеры: /api/camera?enabled=1&interval=500
            params = parse_qs(parsed_path.query)
            enabled = int(params.get('enabled', [1])[0])
            interval = int(params.get('interval', [1000])[0])
            
            self.robot.set_camera(enabled, interval)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "camera": enabled, "interval": interval}).encode('utf-8'))
            
        else:
            # Главная страница
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <h1>ESP32-CAM Robot Server</h1>
            <ul>
                <li><a href="/control">Панель управления</a></li>
                <li><a href="/status">Статус робота (JSON)</a></li>
                <li><a href="/latest">Последний кадр</a></li>
            </ul>
            <h2>API:</h2>
            <ul>
                <li>GET /api/move?left=1&right=1</li>
                <li>GET /api/camera?enabled=1&interval=500</li>
                <li>GET /getdata - команды для ESP32</li>
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
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f"OK frame={self.frame_count}".encode('utf-8'))
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"ERROR: No imageFile field")
                    
            except Exception as e:
                print(f"Ошибка обработки: {e}")
                self.send_response(500)
                self.end_headers()
                
        else:
            # Обработка текстовых данных (телеметрия)
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                data = self.rfile.read(content_length).decode('utf-8')
                print(f"\n📡 Телеметрия от ESP32:\n{data}")
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK data received")
    
    def get_control_page(self):
        """HTML страница для управления роботом"""
        commands = json.loads(self.robot.get_commands_json())
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Управление роботом</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
                h1 {{ color: #333; }}
                .controls {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
                .control-group {{ background: #f9f9f9; padding: 15px; border-radius: 5px; }}
                button {{ 
                    padding: 10px 20px; margin: 5px; font-size: 16px; 
                    border: none; border-radius: 5px; cursor: pointer; 
                    background: #007bff; color: white; 
                }}
                button:hover {{ background: #0056b3; }}
                button.stop {{ background: #dc3545; }}
                button.stop:hover {{ background: #c82333; }}
                .status {{ margin-top: 20px; padding: 10px; background: #e9ecef; border-radius: 5px; }}
                .camera-view {{ margin-top: 20px; text-align: center; }}
                .camera-view img {{ max-width: 100%; border: 2px solid #ddd; border-radius: 5px; }}
                .slider {{ width: 100%; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Управление роботом ESP32-CAM</h1>
                
                <div class="controls">
                    <div class="control-group">
                        <h3>Движение</h3>
                        <button onclick="sendCommand('move?left=1&right=1')">⬆️ Вперед</button><br>
                        <button onclick="sendCommand('move?left=-1&right=1')">↪️ Влево</button>
                        <button onclick="sendCommand('move?left=0&right=0')" class="stop">⏹️ Стоп</button>
                        <button onclick="sendCommand('move?left=1&right=-1')">↩️ Вправо</button><br>
                        <button onclick="sendCommand('move?left=-1&right=-1')">⬇️ Назад</button>
                    </div>
                    
                    <div class="control-group">
                        <h3>Камера</h3>
                        <label>
                            <input type="checkbox" id="cameraToggle" 
                                   {'checked' if commands['camera'] == 1 else ''} 
                                   onchange="toggleCamera()">
                            Включить камеру
                        </label>
                        <br><br>
                        <label>Интервал кадров (мс):</label>
                        <input type="range" class="slider" id="intervalSlider" 
                               min="100" max="5000" value="{commands['interval']}" 
                               onchange="updateInterval(this.value)">
                        <span id="intervalValue">{commands['interval']} мс</span>
                    </div>
                </div>
                
                <div class="status">
                    <h3>Текущее состояние:</h3>
                    <p id="status">Левый мотор: {commands['left']}, Правый мотор: {commands['right']}</p>
                    <p>Камера: {'Включена' if commands['camera'] == 1 else 'Выключена'}</p>
                </div>
                
                <div class="camera-view">
                    <h3>Видео с камеры:</h3>
                    <img id="cameraFeed" src="/latest" alt="Camera feed">
                </div>
            </div>
            
            <script>
                // Обновление изображения с камеры
                setInterval(() => {{
                    document.getElementById('cameraFeed').src = '/latest?' + new Date().getTime();
                }}, {commands['interval']});
                
                // Отправка команд движения
                async function sendCommand(cmd) {{
                    try {{
                        const response = await fetch('/api/' + cmd);
                        const data = await response.json();
                        document.getElementById('status').innerHTML = 
                            `Левый мотор: ${{data.left}}, Правый мотор: ${{data.right}}`;
                    }} catch (error) {{
                        console.error('Error:', error);
                    }}
                }}
                
                // Управление камерой
                async function toggleCamera() {{
                    const enabled = document.getElementById('cameraToggle').checked ? 1 : 0;
                    const interval = document.getElementById('intervalSlider').value;
                    await fetch(`/api/camera?enabled=${{enabled}}&interval=${{interval}}`);
                }}
                
                async function updateInterval(value) {{
                    document.getElementById('intervalValue').textContent = value + ' мс';
                    const enabled = document.getElementById('cameraToggle').checked ? 1 : 0;
                    await fetch(`/api/camera?enabled=${{enabled}}&interval=${{value}}`);
                }}
                
                // Управление с клавиатуры
                document.addEventListener('keydown', (event) => {{
                    switch(event.key) {{
                        case 'ArrowUp': sendCommand('move?left=1&right=1'); break;
                        case 'ArrowDown': sendCommand('move?left=-1&right=-1'); break;
                        case 'ArrowLeft': sendCommand('move?left=-1&right=1'); break;
                        case 'ArrowRight': sendCommand('move?left=1&right=-1'); break;
                        case ' ': 
                            event.preventDefault();
                            sendCommand('move?left=0&right=0'); 
                            break;
                    }}
                }});
            </script>
        </body>
        </html>
        """

def cleanup_old_frames():
    """Очистка старых кадров"""
    while True:
        time.sleep(60)
        files = sorted(os.listdir(SAVE_DIR))
        if len(files) > 100:
            for old_file in files[:-100]:
                os.remove(f"{SAVE_DIR}/{old_file}")
            print(f"🧹 Очищено {len(files) - 100} старых кадров")

def main():
    cleanup_thread = threading.Thread(target=cleanup_old_frames, daemon=True)
    cleanup_thread.start()
    
    print("=" * 60)
    print("🤖 Сервер управления роботом ESP32-CAM")
    print("=" * 60)
    print("\nУправление:")
    print("  Веб-интерфейс: http://localhost:8080/control")
    print("  API движения:  http://localhost:8080/api/move?left=1&right=1")
    print("  API камеры:    http://localhost:8080/api/camera?enabled=1&interval=500")
    print("  Статус:        http://localhost:8080/status")
    print("\nУправление с клавиатуры на странице /control:")
    print("  Стрелки - движение")
    print("  Пробел - стоп")
    print("=" * 60)
    
    server = HTTPServer(('0.0.0.0', 8080), ESP32Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")
        server.shutdown()

if __name__ == '__main__':
    main()