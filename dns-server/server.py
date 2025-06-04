# mock_dns_server.py
import socket
import threading
import domains as d
from flask import Flask, jsonify
import logging
from shared_config import *
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [DNS Server] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/discover')
def discover():
    """Return available domains and their IPs"""
    logger.info("Discovery request received")
    return jsonify({
        'domains': d.DOMAINS,
        'default_domain': CAMERA_DOMAIN_NAME
    })

def handle_dns_query(data, addr, sock):
    try:
        # Extract the queried domain name (simplified parsing)
        query = data[12:]
        domain_parts = []
        pos = 0
        while True:
            length = query[pos]
            if length == 0:
                break
            domain_parts.append(query[pos+1:pos+1+length])
            pos += 1 + length
        queried_domain = b'.'.join(domain_parts).decode('ascii').lower()

        logger.debug(f"Received DNS query for domain: {queried_domain} from {addr}")

        # Find matching domain (supports subdomains too)
        resolved_ip = None
        for domain, ip in d.DOMAINS.items():
            if queried_domain == domain or queried_domain.endswith('.' + domain):
                resolved_ip = ip
                break

        if not resolved_ip:
            logger.warning(f"No record found for domain: {queried_domain}")
            return

        logger.info(f"Resolving {queried_domain} -> {resolved_ip}")

        # Build response
        transaction_id = data[:2]
        flags = b'\x81\x80'  # Standard response, no error
        questions = b'\x00\x01'  # 1 question
        answers = b'\x00\x01'  # 1 answer
        authority = b'\x00\x00'
        additional = b'\x00\x00'
        
        # Answer section
        name = b'\xc0\x0c'  # Pointer to domain name in question
        type_a = b'\x00\x01'  # A record
        class_in = b'\x00\x01'  # IN class
        ttl = DNS_TTL.to_bytes(4, 'big')
        rdlength = b'\x00\x04'  # 4 bytes for IPv4
        rdata = socket.inet_aton(resolved_ip)
        
        response = (
            transaction_id + flags + questions + answers + 
            authority + additional + query + name + 
            type_a + class_in + ttl + rdlength + rdata
        )
        
        sock.sendto(response, addr)
        logger.debug(f"Sent DNS response to {addr}")
    except Exception as e:
        logger.error(f"Error handling DNS query: {e}", exc_info=True)

def dns_server():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((BIND_IP, DNS_PORT))
        logger.info(f"DNS Server running on {BIND_IP}:{DNS_PORT}")
        logger.info("Configured domains:")
        for domain, ip in d.DOMAINS.items():
            logger.info(f"  {domain} -> {ip}")
        
        while True:
            data, addr = sock.recvfrom(512)
            logger.debug(f"Received DNS query from {addr}")
            threading.Thread(target=handle_dns_query, args=(data, addr, sock)).start()
    except Exception as e:
        logger.error(f"DNS Server error: {e}", exc_info=True)
        raise

def run_web_server():
    try:
        logger.info(f"Discovery service running on {BIND_IP}:{DISCOVERY_PORT}")
        app.run(host=BIND_IP, port=DISCOVERY_PORT, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Web Server error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        logger.info("Starting DNS Server...")
        # Start DNS server in a separate thread
        dns_thread = threading.Thread(target=dns_server, daemon=True)
        dns_thread.start()
        
        # Start web server in main thread
        run_web_server()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise