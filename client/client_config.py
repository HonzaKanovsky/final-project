# DNS Configuration
DNS_RESOLVER_IP = '127.0.0.1'  # Local DNS server IP
DNS_RESOLVER_PORT = 5300       # Custom DNS server port
CAMERA_DOMAIN_NAME = 'camera.local'  # Default domain name for camera server
CAMERA_SERVER_PORT = 12345

# Discovery Configuration
DISCOVERY_SERVER_IP = '127.0.0.1'  # DNS server's IP (same as DNS_RESOLVER_IP)
DISCOVERY_SERVER_PORT = 5301      # Discovery service port
DISCOVERY_ENABLED = True          # Enable/disable discovery

# Fallback server IP (in case DNS fails)
FALLBACK_SERVER_IP = '127.0.0.1'  # Change this to your server's IP

# Camera Configuration
CAMERA_INDEX = 0  # Try different indices (0, 1, 2) if camera not found
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# DNS Resolution Settings
DNS_TIMEOUT = 5  # Timeout in seconds for DNS queries
DNS_RETRIES = 3  # Number of retries for DNS queries
