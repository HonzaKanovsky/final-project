import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Network Configuration
LOCAL_IP = '127.0.0.1'  # For local testing
BIND_IP = '0.0.0.0'     # For server binding

# DNS Configuration
DNS_PORT = 5300
DNS_TTL = 300
CAMERA_DOMAIN_NAME = 'camera.local'

# Discovery Service
DISCOVERY_PORT = 5301

# Camera Server Configuration
CAMERA_SERVER_PORT = 12345
ENCRYPTION_PASSWORD = os.getenv('ENCRYPTION_PASSWORD', 'test_password_123')  # Default for testing

# Camera Settings
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# Grid Configuration
NUM_ROWS = 2
NUM_COLS = 3
TILE_WIDTH = 320
TILE_HEIGHT = 240
NUM_SLOTS = NUM_ROWS * NUM_COLS

# Performance Settings
BASE_DELAY_SEC = 3
TARGET_FPS = 24
MAX_BUFFER_SIZE = 100

# DNS Resolution Settings
DNS_TIMEOUT = 5
DNS_RETRIES = 3 