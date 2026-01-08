# Design and Implementation of a Custom Network Proxy Server

## 1. Overview

This project implements a forward HTTP/HTTPS proxy server using Python and TCP sockets. The proxy acts as an intermediary between clients and destination servers by accepting client requests, applying domain-based filtering rules, forwarding permitted requests, and relaying responses back to clients. HTTPS traffic is supported using the CONNECT tunneling mechanism. The implementation has been done using python .

---

## 2. High-Level Architecture

```
Client
  |
  |  HTTP / HTTPS (CONNECT)
  v
+-------------------------+
|     Proxy Server        |
|-------------------------|
|  Listener Socket        |
|  Thread Manager         |
|  Request Parser         |
|  Filtering Engine       |
|  Forwarding Engine      |
|  HTTPS Tunnel Handler   |
|  Logger                 |
+-------------------------+
  |
  |  TCP
  v
Destination Server
```

The proxy listens on a configurable address and port, accepts incoming client connections, and handles each connection independently.

---

## 3. Component Descriptions

### 3.1 Listener

* Creates a TCP socket bound to a configurable IP address and port
* Listens for incoming client connections
* Accepts connections and passes them to the concurrency manager

### 3.2 Concurrency Manager

* Uses a **thread-per-connection** model
* Creates a new thread for each accepted client connection
* Allows multiple clients to be served concurrently

### 3.3 Request Parser

* Reads incoming data until the HTTP header terminator (`\r\n\r\n`) is received
* Extracts:

  * HTTP method (GET, POST, CONNECT, etc.)
  * Request target (absolute URI or relative path)
  * HTTP version
  * Request headers (Host, Content-Length, etc.)

### 3.4 Filtering Engine

* Loads blocked domains from an external configuration file (`blocked_domains.txt`)
* Canonicalizes hostnames (lowercase, trimmed)
* Blocks requests to listed domains by returning HTTP 403 Forbidden

### 3.5 Forwarding Engine (HTTP)

* Establishes a TCP connection to the destination server
* Rewrites proxy-form requests into origin-form
* Forwards request headers and body (if present)
* Streams the server response back to the client without buffering the entire response

### 3.6 HTTPS Tunnel Handler (CONNECT)

* Handles HTTPS requests using the CONNECT method
* Establishes a TCP connection to the requested host and port
* Returns `HTTP/1.1 200 Connection Established` to the client
* Forwards encrypted data bidirectionally without inspection

### 3.7 Logger

* Records proxy activity in a log file
* Log entries include:

  * Timestamp
  * Client IP and port
  * Destination host and port
  * Request type (HTTP or CONNECT)
  * Action taken (ALLOWED / BLOCKED)
  * Bytes transferred (when applicable)

---

## 4. Concurrency Model
### Model Used: Thread-per-Connection

* Each client connection is handled by a dedicated thread

### Reason for using this method for this project:

* Simple and easy to understand
* Provides clear demonstration of concurrent network handling

Thread pools and event-driven models were not implemented, as they are optimizations typically required for high-load production systems.

---

## 5. Data Flow Description

### 5.1 HTTP Request Flow

1. Client establishes a TCP connection to the proxy
2. Proxy reads and parses the HTTP request
3. Host is checked against the blocklist
4. If blocked, proxy returns HTTP 403 Forbidden
5. If allowed:

   * Proxy connects to destination server
   * Forwards request
   * Streams response back to client
6. Transaction is logged

### 5.2 HTTPS CONNECT Flow

1. Client sends `CONNECT host:port HTTP/1.1`
2. Proxy checks the host against the blocklist
3. If blocked, returns HTTP 403 Forbidden
4. If allowed:

   * Proxy establishes TCP connection to host:port
   * Returns `200 Connection Established`
   * Enters tunnel mode
5. Encrypted data is forwarded bidirectionally

---

## 6. Error Handling

* Malformed HTTP requests are rejected
* Socket timeouts prevent indefinite blocking
* All sockets are closed on errors
* Exceptions are logged for debugging
* Graceful shutdown is supported via keyboard interrupt handling

---

## 7. Limitations

* No response caching
* No authentication mechanism
* No wildcard domain blocking (e.g., `*.example.com`)
* No HTTP/2 support
* Persistent connections (keep-alive) are not maintained

---

## 8. Security Considerations

* HTTPS traffic is not decrypted or inspected
* Proxy does not modify request or response payloads
* Intended for educational and experimental use only
* Not hardened for production deployment

---

## 9. Build & Run Instructions:
* This project is implemented in Python and requires no compilation.
To run the proxy server:
```python proxy.py```

---

## 10. Testing
When `blocked_domains.txt` is empty ,i.e., `example.com` is not present and if :
* `http` based : we try to run `curl.exe -i -x localhost:8888 http://example.com`, 
  * the terminal shows `HTTP/1.1 200 OK` and
  * in logs `2026-01-08 20:21:48.373966 ('127.0.0.1', 59332) ALLOWED example.com:80 GET / HTTP/1.1`
* `https` based : we try to run `curl.exe -i -x localhost:8888 https://example.com`,
  *  the terminal shows these two messages:  `HTTP/1.1 200 Connection Established` and `HTTP/1.1 200 OK` and 
  *  in logs `2026-01-08 20:30:36.632356 ('127.0.0.1', 56304) CONNECT example.com:443`
  

Now if we put `example.com` in `blocked_domains.txt` this is how results appear in terminal :
* `http` based : we run `curl.exe -i -x localhost:8888 http://example.com`, 
  * the terminal shows `HTTP/1.1 403 Forbidden` and `Blocked by proxy` and 
  * in logs `2026-01-08 20:22:43.945040 ('127.0.0.1', 52260) BLOCKED example.com`
* `https` based : we run `curl.exe -i -x localhost:8888 https://example.com`, 
  * the terminal shows `HTTP/1.1 403 Forbidden` and `curl: (56) CONNECT tunnel failed, response 403` and
  *  in logs `2026-01-08 20:31:10.051704 ('127.0.0.1', 64872) BLOCKED example.com`
  

## 11. Conclusion

The implemented proxy server satisfies all the necesaary deliverables, including HTTP forwarding, HTTPS tunneling, domain-based filtering, concurrency, and logging. The modular design allows for future extensions such as caching, authentication, or more advanced concurrency models.

## 12. Video link 
https://drive.google.com/file/d/1ec7Zn1YXj06h9sO-NWPttJlM-AQp5l03/view?usp=drive_link

