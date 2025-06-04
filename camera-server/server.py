import socket
import threading
import cv2
import numpy as np
from collections import deque
import time
from crypto import VideoEncryption
from shared_config import *
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [Camera Server] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

clients = [None] * NUM_SLOTS  # Each slot holds {'buffer': deque, 'addr': addr, 'last_time': time}
lock = threading.Lock()
encryption = VideoEncryption(ENCRYPTION_PASSWORD)

def render_grid():
    logger.info("Starting grid rendering thread")
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
        cv2.imshow("All Camera Feeds", full_grid)
        if cv2.waitKey(40) == ord('q'):
            logger.info("Grid rendering stopped by user")
            break
    cv2.destroyAllWindows()

def handle_client(conn, addr, slot_index):
    logger.info(f"New client connected: {addr} -> slot {slot_index}")
    try:
        with lock:
            clients[slot_index] = {'buffer': deque(), 'addr': addr, 'last_time': time.time()}

        while True:
            size_data = conn.recv(2)
            if not size_data:
                logger.debug(f"Client {addr} disconnected")
                break
            frame_size = int.from_bytes(size_data, 'big')
            frame_data = b''
            while len(frame_data) < frame_size:
                packet = conn.recv(frame_size - len(frame_data))
                if not packet:
                    break
                frame_data += packet

            # Decrypt the frame data
            try:
                decrypted_data = encryption.decrypt_frame(frame_data)
                frame = cv2.imdecode(np.frombuffer(decrypted_data, np.uint8), cv2.IMREAD_COLOR)
            except Exception as e:
                logger.error(f"Decryption error for client {addr}: {e}", exc_info=True)
                continue

            if frame is not None:
                with lock:
                    client = clients[slot_index]
                    now = time.time()
                    delta = now - client['last_time']
                    client['last_time'] = now

                    fps = 1 / delta if delta > 0 else TARGET_FPS
                    dynamic_size = int(fps * BASE_DELAY_SEC)
                    client['dynamic_buffer_size'] = min(dynamic_size, MAX_BUFFER_SIZE)

                    buffer = client['buffer']
                    if len(buffer) < MAX_BUFFER_SIZE:
                        buffer.append(frame)
                        logger.debug(f"Frame added to buffer for client {addr}, buffer size: {len(buffer)}")

    except Exception as e:
        logger.error(f"Error handling client {addr} in slot {slot_index}: {e}", exc_info=True)
    finally:
        logger.info(f"Client disconnected: {addr}")
        with lock:
            clients[slot_index] = None
        conn.close()

def server_main():
    logger.info("Starting camera server...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((BIND_IP, CAMERA_SERVER_PORT))
    s.listen(NUM_SLOTS)
    logger.info(f"Camera server listening on {BIND_IP}:{CAMERA_SERVER_PORT}")
    threading.Thread(target=render_grid, daemon=True).start()
    
    while True:
        conn, addr = s.accept()
        with lock:
            try:
                slot_index = next(i for i, c in enumerate(clients) if c is None)
                logger.debug(f"Assigned slot {slot_index} to client {addr}")
            except StopIteration:
                logger.warning(f"All slots full. Rejecting connection from {addr}")
                conn.close()
                continue
        threading.Thread(target=handle_client, args=(conn, addr, slot_index), daemon=True).start()

if __name__ == "__main__":
    try:
        server_main()
    except KeyboardInterrupt:
        logger.info("Camera server shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in camera server: {e}", exc_info=True)
        raise
