import cv2
import socket
import time

SERVER_IP = '192.168.35.67'  # Change to your server IP
SERVER_PORT = 12345

def main():
    cap = cv2.VideoCapture(0)  # Open default camera

    if not cap.isOpened():
        print("Cannot open camera")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((SERVER_IP, SERVER_PORT))
        print(f"Connected to server at {SERVER_IP}:{SERVER_PORT}")

        while True:
            start_time = time.time()

            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            frame = cv2.resize(frame, (640, 480))
            ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            if not ret:
                print("Failed to encode frame")
                break

            jpeg_bytes = jpeg.tobytes()
            size = len(jpeg_bytes)

            sock.sendall(size.to_bytes(2, 'big'))
            sock.sendall(jpeg_bytes)

            cv2.imshow('Client Webcam', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break



    except Exception as e:
        print(f"Error: {e}")
    finally:
        cap.release()
        sock.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
