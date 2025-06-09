#!/usr/bin/env python3
import socket
import struct
import time
import threading
import logging
from typing import Dict, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DNSServer:
    def __init__(self, port: int = 53):
        self.port = port
        self.cache: Dict[str, Tuple[str, float]] = {}  # domain -> (ip, expiry)
        self.upstream_dns = "8.8.8.8"  # Google DNS
        self.local_domains = {
            "home.stream": "172.30.1.58",  # Replace with your webapp server IP
        }
        self.cache_ttl = 300  # 5 minutes
        logger.info("Cache initialized empty at startup.")

    def start(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('0.0.0.0', self.port))
            logger.info(f"DNS Server started on port {self.port}")

            while True:
                try:
                    data, addr = sock.recvfrom(512)
                    threading.Thread(target=self.handle_request, args=(sock, data, addr)).start()
                except Exception as e:
                    logger.error(f"Error receiving data: {e}")

        except Exception as e:
            logger.error(f"Failed to start DNS server: {e}")
            raise

    def handle_request(self, sock: socket.socket, data: bytes, addr: Tuple[str, int]):
        try:
            domain = self.parse_domain(data)
            if not domain:
                logger.warning(f"Malformed DNS query from {addr[0]}")
                return

            logger.info(f"DNS query from {addr[0]} for domain: {domain}")

            # Local match
            if domain in self.local_domains:
                ip = self.local_domains[domain]
                response = self.create_response(data, ip)
                sock.sendto(response, addr)
                logger.info(f"Routed to local IP {ip} for domain {domain}")
                return

            logger.info(f"Domain {domain} not found in local DNS list. Forwarding to upstream.")

            # Cache
            if domain in self.cache:
                ip, expiry = self.cache[domain]
                if time.time() < expiry:
                    response = self.create_response(data, ip)
                    sock.sendto(response, addr)
                    logger.info(f"Served from cache: {domain} -> {ip}")
                    return
                else:
                    del self.cache[domain]

            # Upstream DNS
            upstream_response = self.query_upstream(data)
            if upstream_response:
                ip = self.extract_ip_from_response(upstream_response)
                if ip:
                    self.cache[domain] = (ip, time.time() + self.cache_ttl)
                    logger.info(f"Upstream resolved: {domain} -> {ip}")
                else:
                    logger.warning(f"Upstream returned no IP for domain: {domain}")
                sock.sendto(upstream_response, addr)
            else:
                logger.error(f"Failed to resolve {domain} via upstream DNS")

        except Exception as e:
            logger.error(f"Error handling request: {e}")

    def parse_domain(self, data: bytes) -> Optional[str]:
        try:
            domain = ""
            pos = 12
            while pos < len(data):
                length = data[pos]
                if length == 0:
                    break
                domain += data[pos+1:pos+1+length].decode() + "."
                pos += length + 1
            return domain.rstrip(".")
        except Exception as e:
            logger.error(f"Error parsing domain: {e}")
            return None

    def create_response(self, query: bytes, ip: str) -> bytes:
        """Create DNS response with the given IP (A record)"""
        try:
            response = bytearray(query[:2])      # Transaction ID
            response.extend(b'\x84\x80')         # Flags: response, recursion available, no error
            response.extend(b'\x00\x01')         # Questions = 1
            response.extend(b'\x00\x01')         # Answer RRs = 1
            response.extend(b'\x00\x00')         # Authority RRs = 0
            response.extend(b'\x00\x00')         # Additional RRs = 0

            # Copy the question section
            q_end = 12
            while query[q_end] != 0:
                q_end += query[q_end] + 1
            q_end += 5  # Null byte + QTYPE + QCLASS
            question_section = query[12:q_end]
            response.extend(question_section)

            # Answer section
            response.extend(b'\xc0\x0c')             # Name pointer to offset 12
            response.extend(b'\x00\x01')             # Type A
            response.extend(b'\x00\x01')             # Class IN
            response.extend(b'\x00\x00\x00\x3c')     # TTL = 60 seconds
            response.extend(b'\x00\x04')             # Data length = 4
            response.extend(struct.pack('!BBBB', *[int(o) for o in ip.split('.')]))

            return bytes(response)
        except Exception as e:
            logger.error(f"Error creating response: {e}")
            return query

    def query_upstream(self, query: bytes) -> Optional[bytes]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)
            sock.sendto(query, (self.upstream_dns, 53))
            response, _ = sock.recvfrom(512)
            return response
        except Exception as e:
            logger.error(f"Error querying upstream DNS: {e}")
            return None

    def extract_ip_from_response(self, response: bytes) -> Optional[str]:
        try:
            pos = 12
            while pos < len(response):
                length = response[pos]
                if length == 0:
                    pos += 5  # Null + QTYPE + QCLASS
                    break
                pos += length + 1
            if pos + 10 < len(response):
                return ".".join(str(b) for b in response[pos+10:pos+14])
        except Exception as e:
            logger.error(f"Error extracting IP: {e}")
        return None

if __name__ == "__main__":
    dns_server = DNSServer()
    dns_server.start()
