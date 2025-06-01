import socket
import threading
import cv2
import numpy as np
from collections import deque
import time

HOST = '0.0.0.0'
PORT = 12345

NUM_ROWS, NUM_COLS = 2, 3
TILE_WIDTH, TILE_HEIGHT = 320, 240
NUM_SLOTS = NUM_ROWS * NUM_COLS

clients = [None] * NUM_SLOTS  # Each slot holds {'buffer': deque, 'addr': addr, 'last_time': time}
lock = threading.Lock()

BASE_DELAY_SEC = 3
TARGET_FPS = 24

def render_grid():
    while True:
        grid = []
        with lock:
            for i in range(NUM_SLOTS):
                client = clients[i]
                if client:
                    buffer = client['buffer']
                    min_required = int(client.get('dynamic_buffer_size', TARGET_FPS * BASE_DELAY_SEC))
                    if len(buffer) >= min_required:
                        frame = buffer.popleft()
                        frame = cv2.resize(frame, (TILE_WIDTH, TILE_HEIGHT))
                        addr_str = client['addr'][0]
                        cv2.putText(frame, addr_str, (TILE_WIDTH - 100, TILE_HEIGHT - 10),
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
        cv2.imshow("All Camera Feeds", full_grid)
        if cv2.waitKey(40) == ord('q'):
            break
    cv2.destroyAllWindows()

def handle_client(conn, addr, slot_index):
    print(f"[SERVER] Connected: {addr} -> slot {slot_index}")
    try:
        with lock:
            clients[slot_index] = {'buffer': deque(), 'addr': addr, 'last_time': time.time()}

        while True:
            size_data = conn.recv(2)
            if not size_data:
                break
            frame_size = int.from_bytes(size_data, 'big')
            frame_data = b''
            while len(frame_data) < frame_size:
                packet = conn.recv(frame_size - len(frame_data))
                if not packet:
                    break
                frame_data += packet

            frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                with lock:
                    client = clients[slot_index]
                    now = time.time()
                    delta = now - client['last_time']
                    client['last_time'] = now

                    fps = 1 / delta if delta > 0 else TARGET_FPS
                    dynamic_size = int(fps * BASE_DELAY_SEC)
                    client['dynamic_buffer_size'] = min(dynamic_size, 100)

                    buffer = client['buffer']
                    if len(buffer) < 100:
                        buffer.append(frame)

    except Exception as e:
        print(f"[SERVER] Error in slot {slot_index}: {e}")
    finally:
        print(f"[SERVER] Disconnected: {addr}")
        with lock:
            clients[slot_index] = None
        conn.close()

def server_main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(NUM_SLOTS)
    print(f"[SERVER] Listening on {HOST}:{PORT}")
    threading.Thread(target=render_grid, daemon=True).start()
    while True:
        conn, addr = s.accept()
        with lock:
            try:
                slot_index = next(i for i, c in enumerate(clients) if c is None)
            except StopIteration:
                print("[SERVER] All slots full. Rejecting connection.")
                conn.close()
                continue
        threading.Thread(target=handle_client, args=(conn, addr, slot_index), daemon=True).start()

if __name__ == "__main__":
    server_main()
