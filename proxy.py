import socket
import threading
import select
import os
from datetime import datetime

# CONFIG #

CONFIG_FILE = "config/proxy.conf"
BLOCKED_FILE = "config/blocked_domains.txt"
LOG_FILE = "logs/proxy.log"

CONFIG = {
    "LISTEN_HOST": "127.0.0.1",
    "LISTEN_PORT": 8888,
    "BUFFER_SIZE": 4096,
    "SOCKET_TIMEOUT": 10
}


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return
    with open(CONFIG_FILE) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                CONFIG[k] = int(v) if v.isdigit() else v


def load_blocked_domains():
    try:
        with open(BLOCKED_FILE) as f:
            return set(line.strip().lower() for line in f if line.strip())
    except FileNotFoundError:
        return set()


def log(msg):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} {msg}\n")


# HTTP PARSING #

def recv_until(sock, delimiter):
    data = b""
    while delimiter not in data:
        chunk = sock.recv(CONFIG["BUFFER_SIZE"])
        if not chunk:
            break
        data += chunk
    return data


def parse_headers(header_bytes):
    headers = {}
    lines = header_bytes.decode(errors="ignore").split("\r\n")
    request_line = lines[0]
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.lower()] = v.strip()
    return request_line, headers


# HTTPS TUNNEL #

def tunnel(client, server):
    sockets = [client, server]
    while True:
        r, _, _ = select.select(sockets, [], [], CONFIG["SOCKET_TIMEOUT"])
        if not r:
            break
        for s in r:
            data = s.recv(CONFIG["BUFFER_SIZE"])
            if not data:
                return
            (server if s is client else client).sendall(data)


# CLIENT HANDLER  #

def handle_client(client, addr):
    client.settimeout(CONFIG["SOCKET_TIMEOUT"])
    blocked = load_blocked_domains()

    try:
        header_data = recv_until(client, b"\r\n\r\n")
        if not header_data:
            return

        request_line, headers = parse_headers(header_data)
        parts = request_line.split()
        if len(parts) < 3:
            return

        method, target, version = parts
        method = method.upper()

        # HTTPS CONNECT #
        if method == "CONNECT":
            dest_host, dest_port = target.split(":")
            dest_host = dest_host.lower()
            dest_port = int(dest_port)

            if dest_host in blocked:
                client.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\nBlocked by proxy")
                log(f"{addr} BLOCKED {dest_host}")
                return

            server = socket.create_connection((dest_host, dest_port))
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            log(f"{addr} CONNECT {dest_host}:{dest_port}")
            tunnel(client, server)
            server.close()
            return

        # HTTP FORWARDING #
        host = headers.get("host", "")
        port = 80

        if ":" in host:
            host, port = host.split(":")
            port = int(port)

        host = host.lower()

        if host in blocked:
            client.sendall(b"HTTP/1.1 403 Forbidden\r\n\r\nBlocked by proxy")
            log(f"{addr} BLOCKED {host}")
            return

        server = socket.create_connection((host, port))
        server.settimeout(CONFIG["SOCKET_TIMEOUT"])

        # Rewrite absolute URI → origin-form
        if target.startswith("http://"):
            path = "/" + target.split("/", 3)[3] if "/" in target[7:] else "/"
            request_line = f"{method} {path} {version}"

        forward = request_line + "\r\n"
        for k, v in headers.items():
            forward += f"{k}: {v}\r\n"
        forward += "\r\n"

        server.sendall(forward.encode())

        
        log(f"{addr} ALLOWED {host}:{port} {request_line}")

        # Forward request body if present
        if "content-length" in headers:
            length = int(headers["content-length"])
            body = client.recv(length)
            server.sendall(body)

        while True:
            try:
                data = server.recv(CONFIG["BUFFER_SIZE"])
                if not data:
                    break
                client.sendall(data)
            except socket.timeout:
                break

        server.close()

    except socket.timeout:
        # Timeout after successful transfer → ignore
        pass

    except Exception as e:
        log(f"{addr} ERROR {e}")

    finally:
        client.close()


# SERVER LOOP #

def start_proxy():
    load_config()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((CONFIG["LISTEN_HOST"], CONFIG["LISTEN_PORT"]))
    server.listen(50)

    print(f"Proxy running on {CONFIG['LISTEN_HOST']}:{CONFIG['LISTEN_PORT']}")

    try:
        while True:
            client, addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(client, addr),
                daemon=True
            ).start()
    except KeyboardInterrupt:
        print("\nShutting down proxy...")
    finally:
        server.close()


if __name__ == "__main__":
    start_proxy()
