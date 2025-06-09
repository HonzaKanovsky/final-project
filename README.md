# Video Streaming Platform with Local DNS

A complete video streaming solution that combines a real-time video streaming web application with a local DNS server for easy access within a local network.

## Project Components

### 1. Video Streaming Web Application (`/webapp`)
A real-time video streaming platform that allows multiple cameras to stream video to multiple viewers within a local network.

**Key Features:**
- Real-time video streaming using WebSocket
- Support for up to 6 simultaneous camera streams
- Secure HTTPS/WSS communication
- Responsive web interface
- Camera and viewer roles
- IP address display for each camera

**Setup:**
```bash
cd webapp
npm install
npm start
```
Access at: `https://localhost:8443`

### 2. Local DNS Server (`/dns-server`)
A DNS server implementation that handles local domain resolution and forwards other queries to Google DNS.

**Key Features:**
- Local domain resolution
- DNS caching
- Upstream DNS forwarding
- Multi-threaded request handling
- Logging support

**Setup:**
```bash
cd dns-server
pip install -r requirements.txt
sudo python3 dns_server.py
```

## Complete Setup Guide

1. **Install Dependencies**
   - Node.js (v14 or higher) for the web application
   - Python 3.6 or higher for the DNS server
   - Root/Administrator privileges (for DNS server)

2. **Configure DNS Server**
   - Edit `dns-server/dns_server.py` to add your local domains
   - Set your webapp server's IP address
   - Configure your router to use the DNS server

3. **Setup Web Application**
   - Generate SSL certificates if not present
   - Install Node.js dependencies
   - Start the web server

4. **Network Configuration**
   - Ensure all devices are on the same network
   - Configure router's DNS settings
   - Access the application using the local domain

## Usage

1. **Accessing the Application**
   - Use the configured local domain (e.g., `stream.local`)
   - Or access directly via IP: `https://<server-ip>:8443`

2. **Streaming Video**
   - Choose camera or viewer role
   - Start streaming or view available streams
   - Monitor active connections and IP addresses

## Security Notes

- Use proper SSL certificates in production
- Keep SSL keys secure
- Monitor DNS server logs
- Implement rate limiting if needed

## Troubleshooting

1. **Web Application Issues**
   - Check camera permissions
   - Verify network connectivity
   - Check browser console for errors

2. **DNS Server Issues**
   - Verify port 53 availability
   - Check local domain configuration
   - Ensure proper router settings

## License

This project is licensed under the MIT License - see the LICENSE file for details. 