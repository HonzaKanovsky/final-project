from flask import Flask, Response, render_template
import cv2
import socket
import dns.resolver
import client_config as cc
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import threading
import time
import os
import requests
import json
import numpy as np

app = Flask(__name__)

HOSTNAME = cc.CAMERA_DOMAIN_NAME  # Default domain name
SERVER_PORT = cc.CAMERA_SERVER_PORT
ENCRYPTION_PASSWORD = "your_secure_password_here"  # Must match server password

def discover_domain():
    """Discover available domains from the DNS server"""
    if not cc.DISCOVERY_ENABLED:
        print("[DISCOVERY] Discovery disabled, using default domain")
        return cc.CAMERA_DOMAIN_NAME

    try:
        discovery_url = f"http://{cc.DISCOVERY_SERVER_IP}:{cc.DISCOVERY_SERVER_PORT}/discover"
        print(f"[DISCOVERY] Attempting to discover domains from {discovery_url}")
        
        # Add timeout and retry logic
        for attempt in range(3):
            try:
                response = requests.get(discovery_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"[DISCOVERY] Available domains: {data['domains']}")
                    return data['default_domain']
            except requests.exceptions.RequestException as e:
                print(f"[DISCOVERY] Attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:  # Don't sleep on last attempt
                    time.sleep(1)
                continue
    except Exception as e:
        print(f"[DISCOVERY] Error discovering domains: {e}")
    
    print("[DISCOVERY] Using default domain due to discovery failure")
    return cc.CAMERA_DOMAIN_NAME

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
    """Resolve the server hostname using our custom DNS server with retries"""
    global HOSTNAME
    
    # Try to discover the domain first
    HOSTNAME = discover_domain()
    print(f"[DNS] Using domain: {HOSTNAME}")
    
    for attempt in range(cc.DNS_RETRIES):
        try:
            # Try our DNS server with specific settings
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [cc.DNS_RESOLVER_IP]
            resolver.port = cc.DNS_RESOLVER_PORT
            resolver.lifetime = cc.DNS_TIMEOUT
            print(f"[DNS] Attempting to resolve {HOSTNAME} using custom DNS server {cc.DNS_RESOLVER_IP}:{cc.DNS_RESOLVER_PORT}")
            answer = resolver.resolve(HOSTNAME, 'A')
            resolved_ip = str(answer[0])
            print(f"[DNS] Successfully resolved {HOSTNAME} to {resolved_ip}")
            return resolved_ip
        except Exception as e:
            print(f"[DNS] Attempt {attempt + 1}/{cc.DNS_RETRIES} failed: {e}")
            if attempt < cc.DNS_RETRIES - 1:
                time.sleep(1)  # Wait before retrying
            continue
    
    print(f"[DNS] All resolution attempts failed. Using fallback IP: {cc.FALLBACK_SERVER_IP}")
    return cc.FALLBACK_SERVER_IP

def find_working_camera():
    """Try different camera indices until finding a working one"""
    for i in range(3):  # Try first 3 indices
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Found working camera at index {i}")
                return i
            cap.release()
    return None

def stream_to_server():
    cipher_suite = setup_encryption()
    SERVER_IP = resolve_hostname()
    
    if not SERVER_IP:
        print("[ERROR] IP not found")
        return

    # Try to find a working camera
    camera_index = find_working_camera()
    if camera_index is None:
        print("[ERROR] No working camera found")
        return

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera")
        return

    # Set camera properties
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cc.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cc.CAMERA_HEIGHT)

    while True:  # Outer loop for reconnection attempts
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"[CONNECTION] Attempting to connect to {SERVER_IP}:{SERVER_PORT}")
            sock.settimeout(5)
            sock.connect((SERVER_IP, SERVER_PORT))
            print("[CONNECTION] Connection established!")

            while True:  # Inner loop for streaming
                ret, frame = cap.read()
                if not ret:
                    print("[ERROR] Failed to grab frame")
                    break

                frame = cv2.resize(frame, (cc.CAMERA_WIDTH, cc.CAMERA_HEIGHT))
                _, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                
                encrypted_data = cipher_suite.encrypt(jpeg.tobytes())
                try:
                    sock.sendall(len(encrypted_data).to_bytes(2, 'big'))
                    sock.sendall(encrypted_data)
                except (socket.error, ConnectionResetError) as e:
                    print(f"[ERROR] Connection lost: {e}")
                    break
                
                time.sleep(0.1)  # Control frame rate

        except (socket.error, ConnectionRefusedError) as e:
            print(f"[ERROR] Connection failed: {e}")
            time.sleep(5)  # Wait before reconnecting
        finally:
            sock.close()
            print("[CONNECTION] Connection closed, attempting to reconnect...")
            time.sleep(1)  # Brief pause before reconnection attempt

def generate_preview():
    # Try to find a working camera
    camera_index = find_working_camera()
    if camera_index is None:
        # Return a black frame with error message
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(frame, "No camera found", (50, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        return

    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cc.CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cc.CAMERA_HEIGHT)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (320, 240))
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)
    cap.release()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/preview')
def preview():
    return Response(generate_preview(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def run_web_client():
    # Start the streaming thread
    stream_thread = threading.Thread(target=stream_to_server, daemon=True)
    stream_thread.start()
    
    # Start the web server
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)

if __name__ == '__main__':
    run_web_client() 