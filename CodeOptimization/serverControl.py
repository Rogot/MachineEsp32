from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import cgi
import json
import threading
import time
from urllib.parse import parse_qs, urlparse
from io import BytesIO

class RobotController:
    """Класс для управления роботом"""
    def __init__(self):
        self.commands = {
            "left": 0,
            "right": 0,
            "camera": 1,
            "interval": 1000
        }
        self.lock = threading.Lock()
    
    def set_motors(self, left, right):
        with self.lock:
            self.commands["left"] = max(-1, min(1, left))
            self.commands["right"] = max(-1, min(1, right))
    
    def set_camera(self, enabled, interval=1000):
        with self.lock:
            self.commands["camera"] = 1 if enabled else 0
            self.commands["interval"] = max(100, min(5000, interval))
    
    def get_commands_string(self):
        with self.lock:
            return f"LEFT:{self.commands['left']},RIGHT:{self.commands['right']},CAM:{self.commands['camera']},INTERVAL:{self.commands['interval']}"
    
    def get_commands_json(self):
        with self.lock:
            return json.dumps(self.commands)

class ESP32Handler(BaseHTTPRequestHandler):
    frame_count = 0
    start_time = time.time()
    lock = threading.Lock()
    robot = RobotController()
    
    # Храним последний кадр в памяти
    latest_frame = None
    latest_frame_time = None
    frame_lock = threading.Lock()
    
    def do_GET(self):
        print(f"DEBUG: Запрошен путь: {self.path}")
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if self.path.startswith('/latest') or self.path.startswith('/video'):
            with ESP32Handler.frame_lock:
                if ESP32Handler.latest_frame is not None:
                    self.send_response(200)
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.end_headers()
                    self.wfile.write(ESP32Handler.latest_frame)
                    print("📷 Кадр отправлен")
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"No frame")
                    print("❌ Кадра нет")
            return

        # Обработка команды для ESP32
        if path == '/getdata':
            commands = self.robot.get_commands_string()
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(commands.encode('utf-8'))
            return
        
        # Статус
        if path == '/status':
            with self.lock:
                uptime = time.time() - self.start_time
                fps = self.frame_count / uptime if uptime > 0 else 0
            with self.frame_lock:
                has_frame = self.latest_frame is not None
                frame_time = self.latest_frame_time
            status = {
                "frames_received": self.frame_count,
                "uptime_seconds": round(uptime, 1),
                "average_fps": round(fps, 2),
                "latest_frame": {
                    "available": has_frame,
                    "timestamp": frame_time.strftime('%H:%M:%S.%f') if frame_time else None,
                    "size_bytes": len(self.latest_frame) if has_frame else 0
                },
                "robot_commands": json.loads(self.robot.get_commands_json())
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status, indent=2).encode('utf-8'))
            return
        
        # Веб-интерфейс управления
        if path == '/control':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_control_page().encode('utf-8'))
            return
        
        # API движения
        if path == '/api/move':
            params = parse_qs(parsed_path.query)
            left = int(params.get('left', [0])[0])
            right = int(params.get('right', [0])[0])
            self.robot.set_motors(left, right)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "left": left, "right": right}).encode('utf-8'))
            return
        
        # API камеры
        if path == '/api/camera':
            params = parse_qs(parsed_path.query)
            enabled = int(params.get('enabled', [1])[0])
            interval = int(params.get('interval', [1000])[0])
            self.robot.set_camera(enabled, interval)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "camera": enabled, "interval": interval}).encode('utf-8'))
            return
        
        # Главная страница (если ничего не подошло)
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = """<!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>ESP32-CAM Robot Server</title></head>
        <body>
            <h1>🤖 ESP32-CAM Robot Server</h1>
            <ul>
                <li><a href="/control">🎮 Панель управления</a></li>
                <li><a href="/status">📊 Статус</a></li>
                <li><a href="/latest">📷 Последний кадр</a></li>
            </ul>
        </body>
        </html>"""
        self.wfile.write(html.encode('utf-8'))
    
    def do_POST(self):
        print(f"=== POST от {self.client_address} ===")
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length)

        start = raw.find(b'\xff\xd8')
        if start == -1:
            self.send_response(400)
            self.end_headers()
            return
        end = raw.find(b'\xff\xd9', start)
        if end == -1:
            self.send_response(400)
            self.end_headers()
            return
        jpeg = raw[start:end+2]

        # Используем переменные КЛАССА, а не экземпляра
        with ESP32Handler.frame_lock:
            ESP32Handler.latest_frame = jpeg
            ESP32Handler.latest_frame_time = datetime.now()
        with ESP32Handler.lock:
            ESP32Handler.frame_count += 1
            count = ESP32Handler.frame_count

        print(f"✅ Извлечён JPEG размером {len(jpeg)} байт, кадр #{count}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"OK frame={count}".encode())
    
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
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{ 
                    max-width: 900px; 
                    margin: 0 auto; 
                    background: white; 
                    padding: 30px; 
                    border-radius: 15px; 
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }}
                h1 {{ color: #333; margin-bottom: 20px; text-align: center; }}
                .controls {{ 
                    display: grid; 
                    grid-template-columns: 1fr 1fr; 
                    gap: 20px; 
                    margin: 20px 0; 
                }}
                .control-group {{ 
                    background: #f8f9fa; 
                    padding: 20px; 
                    border-radius: 10px; 
                    border: 1px solid #dee2e6;
                }}
                .control-group h3 {{ margin-bottom: 15px; color: #495057; }}
                
                /* Джойстик управления */
                .joystick {{
                    display: grid;
                    grid-template-columns: 80px 80px 80px;
                    grid-template-rows: 80px 80px 80px;
                    gap: 5px;
                    justify-content: center;
                    margin: 10px 0;
                }}
                .joy-btn {{
                    width: 80px;
                    height: 80px;
                    border: 2px solid #007bff;
                    background: #e7f1ff;
                    color: #007bff;
                    font-size: 28px;
                    border-radius: 12px;
                    cursor: pointer;
                    transition: all 0.2s;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .joy-btn:hover {{ background: #007bff; color: white; transform: scale(1.05); }}
                .joy-btn:active {{ transform: scale(0.95); }}
                .joy-btn.stop {{ 
                    background: #dc3545; 
                    color: white; 
                    border-color: #dc3545;
                    font-size: 20px;
                    font-weight: bold;
                }}
                .joy-btn.stop:hover {{ background: #c82333; }}
                .joy-center {{ grid-column: 2; grid-row: 2; }}
                
                /* Слайдеры и переключатели */
                .camera-controls {{
                    display: flex;
                    flex-direction: column;
                    gap: 15px;
                }}
                .toggle-label {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    cursor: pointer;
                    font-size: 16px;
                }}
                .toggle-label input[type="checkbox"] {{
                    width: 20px;
                    height: 20px;
                    cursor: pointer;
                }}
                .slider-container {{
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                }}
                .slider {{
                    width: 100%;
                    height: 8px;
                    border-radius: 5px;
                    background: #ddd;
                    outline: none;
                    -webkit-appearance: none;
                }}
                .slider::-webkit-slider-thumb {{
                    -webkit-appearance: none;
                    appearance: none;
                    width: 22px;
                    height: 22px;
                    border-radius: 50%;
                    background: #007bff;
                    cursor: pointer;
                }}
                
                /* Видео */
                .camera-view {{
                    margin-top: 20px;
                    text-align: center;
                    background: #000;
                    border-radius: 10px;
                    overflow: hidden;
                    min-height: 300px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .camera-view img {{
                    max-width: 100%;
                    max-height: 500px;
                }}
                .no-signal {{
                    color: #666;
                    font-size: 18px;
                    padding: 50px;
                }}
                
                /* Статус */
                .status {{
                    margin-top: 20px;
                    padding: 15px;
                    background: #e9ecef;
                    border-radius: 8px;
                    font-family: monospace;
                    font-size: 14px;
                }}
                
                /* Индикатор FPS */
                .fps-counter {{
                    display: inline-block;
                    background: #28a745;
                    color: white;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin-left: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 Управление роботом ESP32-CAM</h1>
                
                <div class="controls">
                    <div class="control-group">
                        <h3>🎮 Джойстик движения</h3>
                        <div class="joystick">
                            <div></div>
                            <button class="joy-btn" onclick="move(1, 1)" title="Вперед (↑)">⬆️</button>
                            <div></div>
                            
                            <button class="joy-btn" onclick="move(-1, 1)" title="Влево (←)">⬅️</button>
                            <button class="joy-btn stop joy-center" onclick="move(0, 0)" title="Стоп (Пробел)">■</button>
                            <button class="joy-btn" onclick="move(1, -1)" title="Вправо (→)">➡️</button>
                            
                            <div></div>
                            <button class="joy-btn" onclick="move(-1, -1)" title="Назад (↓)">⬇️</button>
                            <div></div>
                        </div>
                    </div>
                    
                    <div class="control-group">
                        <h3>📷 Настройки камеры</h3>
                        <div class="camera-controls">
                            <label class="toggle-label">
                                <input type="checkbox" id="cameraToggle" 
                                       {'checked' if commands['camera'] == 1 else ''} 
                                       onchange="toggleCamera()">
                                <strong>Камера {'включена' if commands['camera'] == 1 else 'выключена'}</strong>
                            </label>
                            
                            <div class="slider-container">
                                <label>Интервал кадров: <strong><span id="intervalValue">{commands['interval']}</span> мс</strong></label>
                                <input type="range" class="slider" id="intervalSlider" 
                                       min="100" max="5000" value="{commands['interval']}" 
                                       oninput="updateInterval(this.value)">
                                <small style="color: #666;">100 мс ≈ 10 FPS | 1000 мс = 1 FPS</small>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="camera-view">
                    <img id="cameraFeed" src="/latest" alt="Видео с камеры" 
                         onerror="this.style.display='none'; document.getElementById('noSignal').style.display='block';"
                         onload="this.style.display='block'; document.getElementById('noSignal').style.display='none';">
                    <div id="noSignal" class="no-signal" style="display: none;">
                        📡 Ожидание видеосигнала...
                    </div>
                </div>
                
                <div class="status">
                    <strong>Состояние:</strong> 
                    Левый мотор: <span id="leftMotor">{commands['left']}</span> | 
                    Правый мотор: <span id="rightMotor">{commands['right']}</span>
                    <span class="fps-counter" id="fpsCounter">FPS: --</span>
                </div>
            </div>
            
            <script>
                let lastFrameTime = Date.now();
                let frameCount = 0;
                
                // Обновление видео с камеры
                function updateCamera() {{
                    const img = document.getElementById('cameraFeed');
                    img.src = '/latest?' + new Date().getTime();
                    
                    // Подсчет FPS
                    frameCount++;
                    const now = Date.now();
                    if (now - lastFrameTime >= 1000) {{
                        const fps = Math.round(frameCount / ((now - lastFrameTime) / 1000));
                        document.getElementById('fpsCounter').textContent = 'FPS: ' + fps;
                        frameCount = 0;
                        lastFrameTime = now;
                    }}
                }}
                
                // Запускаем обновление камеры
                const cameraInterval = {commands['interval']};
                setInterval(updateCamera, cameraInterval);
                
                // Функция движения
                async function move(left, right) {{
                    try {{
                        const response = await fetch(`/api/move?left=${{left}}&right=${{right}}`);
                        const data = await response.json();
                        document.getElementById('leftMotor').textContent = data.left;
                        document.getElementById('rightMotor').textContent = data.right;
                    }} catch (error) {{
                        console.error('Ошибка:', error);
                    }}
                }}
                
                // Управление камерой
                async function toggleCamera() {{
                    const enabled = document.getElementById('cameraToggle').checked ? 1 : 0;
                    const interval = document.getElementById('intervalSlider').value;
                    await fetch(`/api/camera?enabled=${{enabled}}&interval=${{interval}}`);
                }}
                
                async function updateInterval(value) {{
                    document.getElementById('intervalValue').textContent = value;
                    const enabled = document.getElementById('cameraToggle').checked ? 1 : 0;
                    await fetch(`/api/camera?enabled=${{enabled}}&interval=${{value}}`);
                }}
                
                // Управление с клавиатуры
                document.addEventListener('keydown', (event) => {{
                    switch(event.key) {{
                        case 'ArrowUp': 
                            event.preventDefault();
                            move(1, 1); 
                            break;
                        case 'ArrowDown': 
                            event.preventDefault();
                            move(-1, -1); 
                            break;
                        case 'ArrowLeft': 
                            event.preventDefault();
                            move(-1, 1); 
                            break;
                        case 'ArrowRight': 
                            event.preventDefault();
                            move(1, -1); 
                            break;
                        case ' ': 
                            event.preventDefault();
                            move(0, 0); 
                            break;
                    }}
                }});
                
                // Отпускание клавиш - стоп
                document.addEventListener('keyup', (event) => {{
                    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {{
                        event.preventDefault();
                        move(0, 0);
                    }}
                }});
            </script>
        </body>
        </html>
        """

def main():
    print("=" * 60)
    print("🤖 Сервер управления роботом ESP32-CAM")
    print("=" * 60)
    print("\n⚡ Изображения НЕ сохраняются на диск (только в RAM)")
    print("\nУправление:")
    print("  🎮 Веб-интерфейс: http://localhost:8080/control")
    print("  📷 Видеопоток:    http://localhost:8080/latest")
    print("  📊 Статус:        http://localhost:8080/status")
    print("\nAPI команды:")
    print("  GET /api/move?left=1&right=1")
    print("  GET /api/camera?enabled=1&interval=500")
    print("\nГорячие клавиши на странице /control:")
    print("  ↑↓←→ - движение")
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