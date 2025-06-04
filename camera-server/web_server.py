from flask import Flask, Response, render_template, jsonify
import cv2
import numpy as np
from server import clients, lock, NUM_ROWS, NUM_COLS, TILE_WIDTH, TILE_HEIGHT
import threading
import time

app = Flask(__name__)

def generate_frames():
    while True:
        grid = []
        with lock:
            for i in range(len(clients)):
                client = clients[i]
                if client:
                    buffer = client['buffer']
                    if len(buffer) > 0:
                        frame = buffer[-1]  # Get the latest frame
                        frame = cv2.resize(frame, (TILE_WIDTH, TILE_HEIGHT))
                        addr_str = client['addr'][0]
                        cv2.putText(frame, addr_str, ((TILE_WIDTH - 100) // 2, TILE_HEIGHT - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    else:
                        frame = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
                        cv2.putText(frame, "Buffering...", (50, TILE_HEIGHT // 2),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 255), 2)
                else:
                    frame = np.zeros((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8)
                    cv2.putText(frame, "Camera is off", (50, TILE_HEIGHT // 2),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 255), 2)
                grid.append(frame)

        rows = [np.hstack(grid[r * NUM_COLS:(r + 1) * NUM_COLS]) for r in range(NUM_ROWS)]
        full_grid = np.vstack(rows)
        
        # Encode the frame
        ret, buffer = cv2.imencode('.jpg', full_grid)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        time.sleep(0.1)  # Control frame rate

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/client_list')
def client_list():
    with lock:
        active_clients = [
            {'address': client['addr'][0], 'slot': i}
            for i, client in enumerate(clients)
            if client is not None
        ]
    return jsonify(active_clients)

def run_web_server():
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

if __name__ == '__main__':
    run_web_server() 