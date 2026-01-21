import socket

def get_local_ip():
    try:
        # Create a dummy socket to find the preferred interface
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # We don't actually connect, but this identifies the local IP
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return f"Error: {e}"

print(f"Local IP: {get_local_ip()}")