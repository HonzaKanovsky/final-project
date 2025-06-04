# Secure Multi-Camera Streaming System

A secure, web-based multi-camera streaming system that allows multiple clients to stream their cameras to a central server. The system features encryption, web interfaces, and real-time monitoring capabilities.

## Features

- **Secure Camera Streaming**: All video streams are encrypted using Fernet symmetric encryption
- **Web-Based Interfaces**: 
  - Server-side admin view with combined camera grid
  - Client-side preview of their own camera
- **Real-time Monitoring**: Server dashboard shows connected clients and their status
- **DNS Integration**: Custom DNS server for service discovery
- **Scalable Architecture**: Supports multiple simultaneous camera streams

## System Components

1. **Camera Server** (`camera-server/`)
   - Central hub for receiving and displaying camera streams
   - Web interface for monitoring all cameras
   - Handles encryption/decryption of video streams

2. **Client** (`client/`)
   - Web interface for camera preview
   - Streams encrypted video to server
   - Shows connection status and instructions

3. **DNS Server** (`dns-server/`)
   - Custom DNS implementation for service discovery
   - Maps domain names to IP addresses

## Prerequisites

- Python 3.7 or higher
- OpenCV
- Flask
- Cryptography
- DNS Python

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the system:
   - Set the encryption password in both `camera-server/server.py` and `client/web_client.py`
   - Update DNS settings in `client/client_config.py` if needed

## Usage

### Starting the System

1. **Start the DNS Server**:
   ```bash
   cd dns-server
   python sever.py
   ```

2. **Start the Camera Server**:
   ```bash
   cd camera-server
   python server.py
   python web_server.py
   ```

3. **Start Client Applications**:
   ```bash
   cd client
   python web_client.py
   ```

### Accessing the Interfaces

- **Server Admin View**: Open `http://<server_ip>:5000` in a web browser
- **Client View**: Open `http://<client_ip>:5001` in a web browser

## Security Features

- All video streams are encrypted using Fernet symmetric encryption
- Encryption keys are derived from passwords using PBKDF2
- Secure password handling and key derivation
- Encrypted communication between clients and server

## Network Configuration

- Camera Server: Port 12345 (TCP)
- Web Server: Port 5000 (HTTP)
- Client Web Interface: Port 5001 (HTTP)
- DNS Server: Port 5300 (UDP)

## Directory Structure

```
.
├── camera-server/
│   ├── server.py
│   ├── web_server.py
│   ├── crypto.py
│   └── templates/
│       └── index.html
├── client/
│   ├── web_client.py
│   ├── client_config.py
│   └── templates/
│       └── index.html
├── dns-server/
│   ├── sever.py
│   └── domains.py
└── requirements.txt
```

## Configuration

### Encryption Settings
- Update `ENCRYPTION_PASSWORD` in both server and client files
- The password must be the same on both ends

### DNS Configuration
- Update `domains.py` with your domain mappings
- Configure DNS resolver settings in `client_config.py`

## Troubleshooting

1. **Connection Issues**:
   - Check if all required ports are open
   - Verify DNS server is running
   - Ensure encryption passwords match

2. **Video Stream Problems**:
   - Check camera permissions
   - Verify network connectivity
   - Check server logs for errors

3. **Web Interface Issues**:
   - Clear browser cache
   - Check if ports 5000/5001 are available
   - Verify Flask server is running

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request


## Acknowledgments

- OpenCV for video processing
- Flask for web interface
- Cryptography library for security features 