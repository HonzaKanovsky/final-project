import cv2
import socket
import dns.resolver
import client_config as cc
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

HOSTNAME = cc.CAMERA_DOMAIN_NAME
SERVER_PORT = cc.CAMERA_SERVER_PORT
ENCRYPTION_PASSWORD = "your_secure_password_here"  # Must match server password

def setup_encryption():
    salt = b'fixed_salt'  # Must match server salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(ENCRYPTION_PASSWORD.encode()))
    return Fernet(key)

def resolve_hostname():
    try:
        # Try direct system resolution first (checks /etc/hosts)
        return socket.gethostbyname(HOSTNAME)
    except socket.gaierror:
        try:
            # Try our DNS server with specific settings
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [cc.DNS_RESOLVER_IP] 
            resolver.port = cc.DNS_RESOLVER_PORT
            resolver.lifetime = 2
            print(resolver.port)
            print(resolver.nameservers)
            answer = resolver.resolve(HOSTNAME, 'A')
            return str(answer[0])
        except Exception as e:
            print(f"DNS resolution error details: {e}")
            return None

def main():
    # Setup encryption
    cipher_suite = setup_encryption()
    
    # Resolve server IP with fallback
    SERVER_IP = resolve_hostname()
    if not SERVER_IP:
        print("IP not found")
        return
    
    print(f"Connecting to server at {SERVER_IP}:{SERVER_PORT}")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(5)  # Set connection timeout
        sock.connect((SERVER_IP, SERVER_PORT))
        print("Connection established!")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            frame = cv2.resize(frame, (640, 480))
            _, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
            
            # Encrypt the frame data
            encrypted_data = cipher_suite.encrypt(jpeg.tobytes())
            
            # Send encrypted frame size then encrypted frame
            sock.sendall(len(encrypted_data).to_bytes(2, 'big'))
            sock.sendall(encrypted_data)

            cv2.imshow('Client Webcam', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except socket.timeout:
        print("Connection timeout - is the server running?")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        cap.release()
        sock.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()