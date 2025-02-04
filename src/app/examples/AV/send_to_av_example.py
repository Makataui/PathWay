import socket

CLAMAV_HOST = "clamav"  # The container name from Docker Compose
CLAMAV_PORT = 3310

def scan_file(file_path: str) -> str:
    """Send a file to ClamAV for scanning and return the response."""
    with open(file_path, "rb") as f:
        file_data = f.read()

    try:
        # Connect to ClamAV daemon
        with socket.create_connection((CLAMAV_HOST, CLAMAV_PORT), timeout=10) as sock:
            sock.sendall(b"zINSTREAM\0")
            sock.sendall(file_data + b"\0")
            response = sock.recv(4096).decode()
        
        return response
    except Exception as e:
        return f"Error scanning file: {e}"
