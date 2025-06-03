# mock_dns_server.py
import socket
import threading
import domains as d

#dns config
DNS_HOST = '0.0.0.0'
DNS_PORT = 5300
DNS_TTL = 300

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

        # Find matching domain (supports subdomains too)
        resolved_ip = None
        for domain, ip in d.DOMAINS.items():
            if queried_domain == domain or queried_domain.endswith('.' + domain):
                resolved_ip = ip
                break

        if not resolved_ip:
            print(f"[DNS] No record found for: {queried_domain}")
            return

        print(f"[DNS] Resolving {queried_domain} -> {resolved_ip}")

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
    except Exception as e:
        print(f"[DNS] Error handling query: {e}")

def dns_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((DNS_HOST, DNS_PORT))
    print(f"[DNS] Server running on {DNS_HOST}:{DNS_PORT}")
    print("Configured domains:")
    for domain, ip in d.DOMAINS.items():
        print(f"  {domain} -> {ip}")
    
    while True:
        data, addr = sock.recvfrom(512)
        threading.Thread(target=handle_dns_query, args=(data, addr, sock)).start()

if __name__ == "__main__":
    dns_server()