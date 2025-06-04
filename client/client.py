import cv2
import socket
import dns.resolver
import client_config as cc
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import time
import threading
import requests
import json
from crypto import VideoEncryption
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [Client] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

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

class CameraClient:
    def __init__(self):
        self.encryption = VideoEncryption(cc.ENCRYPTION_PASSWORD)
        self.camera = None
        self.socket = None
        self.running = False
        self.server_ip = None
        self.server_port = cc.CAMERA_SERVER_PORT

    def discover_server(self):
        """Discover camera server using DNS or discovery service"""
        logger.info("Attempting to discover camera server...")
        
        if cc.DISCOVERY_ENABLED:
            try:
                # Try discovery service first
                discovery_url = f"http://{cc.DISCOVERY_SERVER_IP}:{cc.DISCOVERY_SERVER_PORT}/discover"
                logger.debug(f"Querying discovery service at {discovery_url}")
                response = requests.get(discovery_url, timeout=cc.DNS_TIMEOUT)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Discovery service response: {data}")
                    if cc.CAMERA_DOMAIN_NAME in data['domains']:
                        self.server_ip = data['domains'][cc.CAMERA_DOMAIN_NAME]
                        logger.info(f"Found server IP through discovery: {self.server_ip}")
                        return True
            except Exception as e:
                logger.warning(f"Discovery service failed: {e}")

        # Fallback to DNS resolution
        try:
            logger.debug(f"Attempting DNS resolution for {cc.CAMERA_DOMAIN_NAME}")
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [cc.DNS_RESOLVER_IP]
            resolver.port = cc.DNS_RESOLVER_PORT
            
            for _ in range(cc.DNS_RETRIES):
                try:
                    answer = resolver.resolve(cc.CAMERA_DOMAIN_NAME, 'A')
                    self.server_ip = answer[0].to_text()
                    logger.info(f"Found server IP through DNS: {self.server_ip}")
                    return True
                except dns.exception.DNSException as e:
                    logger.warning(f"DNS resolution attempt failed: {e}")
                    time.sleep(1)
        except Exception as e:
            logger.error(f"DNS resolution failed: {e}")

        # Use fallback IP
        logger.warning(f"Using fallback server IP: {cc.FALLBACK_SERVER_IP}")
        self.server_ip = cc.FALLBACK_SERVER_IP
        return True

    def connect(self):
        """Connect to the camera server"""
        if not self.discover_server():
            logger.error("Failed to discover server")
            return False

        try:
            logger.info(f"Connecting to server at {self.server_ip}:{self.server_port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            logger.info("Connected to server successfully")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def start_camera(self):
        """Start the camera capture"""
        try:
            logger.info(f"Starting camera with index {cc.CAMERA_INDEX}")
            self.camera = cv2.VideoCapture(cc.CAMERA_INDEX)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, cc.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, cc.CAMERA_HEIGHT)
            
            if not self.camera.isOpened():
                logger.error("Failed to open camera")
                return False
                
            logger.info("Camera started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting camera: {e}")
            return False

    def stream(self):
        """Stream video to the server"""
        if not self.connect() or not self.start_camera():
            return

        self.running = True
        logger.info("Starting video stream")
        
        try:
            while self.running:
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("Failed to read frame from camera")
                    break

                # Encrypt the frame
                try:
                    _, buffer = cv2.imencode('.jpg', frame)
                    encrypted_data = self.encryption.encrypt_frame(buffer.tobytes())
                    
                    # Send frame size and data
                    size = len(encrypted_data)
                    self.socket.sendall(size.to_bytes(2, 'big'))
                    self.socket.sendall(encrypted_data)
                    
                    logger.debug(f"Sent frame of size {size} bytes")
                except Exception as e:
                    logger.error(f"Error processing frame: {e}")
                    break

                time.sleep(1/cc.TARGET_FPS)  # Control frame rate
                
        except Exception as e:
            logger.error(f"Streaming error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources")
        self.running = False
        if self.camera:
            self.camera.release()
        if self.socket:
            self.socket.close()
        cv2.destroyAllWindows()

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
    try:
        client = CameraClient()
        client.stream()
    except KeyboardInterrupt:
        logger.info("Client shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise