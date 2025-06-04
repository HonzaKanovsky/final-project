# Camera Network Project

This project implements a distributed camera system with a custom DNS server, a central camera server, and multiple clients. The server arranges incoming video feeds into a grid and can display or stream them via a web interface.

## Features
- Custom DNS server for camera hostname resolution
- Central server for aggregating and displaying video feeds
- Multiple clients (cameras) streaming video
- Web interfaces for admin and clients (can run on any device in the hotspot)

## Project Structure
- `camera-server/`: Central server code
- `client/`: Client code for cameras
- `dns-server/`: Custom DNS server
- `web_admin/`: Admin web interface (Flask app)
- `web_client/`: Client web interface (Flask app)
- `UML/`: Diagrams
- `shared_config.py`: Shared configuration

## Setup
1. Clone the repository.
2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv_cn
   source venv_cn/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env` and set your environment variables as needed.

## Usage
- Start the DNS server (on the hotspot host):
  ```bash
  python dns-server/sever.py
  ```
- Start the camera server (on any device):
  ```bash
  python camera-server/server.py
  ```
- Start one or more clients (on any device):
  ```bash
  python client/client.py
  ```
- Start the admin web interface (on any device):
  ```bash
  python web_admin/app.py
  # Accessible at http://<device-ip>:5001/
  ```
- Start the client web interface (on any device):
  ```bash
  python web_client/app.py
  # Accessible at http://<device-ip>:5002/
  ```

## Running Web Interfaces on a Different Device
- Connect the device to the Windows hotspot.
- Find its local IP address (e.g., 192.168.137.101).
- Run the web interface as above, making sure to use `--host=0.0.0.0`.
- Access from any device on the hotspot using the device's IP and port.

## Requirements
- Python 3.8+
- OpenCV
- Flask
- dnspython
- numpy

## License
MIT 