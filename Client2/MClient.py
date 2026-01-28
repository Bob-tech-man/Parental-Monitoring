import sqlite3
import shutil
import os
import json
import socket
import time
import threading

SERVER_HOST = "172.20.134.188"
SERVER_PORT = 9000
HISTORY_INTERVAL = 10 * 60  # 10 minutes in seconds


class Child():
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port

        self.name = input("Enter child name: ")
        self.age = int(input("Enter child age: "))

        self.buffer = "" # check new messages.

        # history path & path to copy
        self.chrome_history = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History")
        self.copy_path = os.path.expanduser(r"~\chrome_history_copy.db")

        self.sock = None # So I wont have to send the sock every into every function
        self.running = True

    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_host, self.server_port))
        print(f"Connected to server {self.server_host}:{self.server_port}")

    def receive_data(self):
        while self.running:
            if "\n" in self.buffer:
                # "\n" = new message
                line, self.buffer = self.buffer.split("\n", 1)
                self.handle_data(line)
            else:
                try:
                    data = self.sock.recv(4096).decode("utf-8")
                    if not data:
                        print("Server closed connection")
                        self.running = False
                        break
                    self.buffer += data
                except Exception as e:
                    print(f"Receive error: {e}")
                    self.running = False
                    break

    def handle_data(self, json_str):
        msg = json.loads(json_str)
        data_type = msg.get("type")
        recv_data = msg.get("data")

        if data_type == "BLOCK_WEBSITES":
            self.block_websites(recv_data)
        elif data_type == "BLOCK_REGISTRIES":
            pass
        elif data_type == "AUTH_OK":
            print("Auth CONFIRMED")
        else:
            print(f"Unknown message type: {data_type}")

    def send_auth(self):
        auth_packet = {
            "type": "AUTH",
            "name": self.name,
            "age": self.age,
            "data": {}
        }
        self.sock.sendall((json.dumps(auth_packet) + "\n").encode('utf-8'))

    def send_chrome_history(self):
        history = self.get_chrome_history(50)
        data = {"age": self.age, "type": "HISTORY", "data": history}
        self.sock.sendall((json.dumps(data) + "\n").encode('utf-8'))
        print("History sent")

    def get_chrome_history(self, limit):
        shutil.copy2(self.chrome_history, self.copy_path)
        conn = sqlite3.connect(self.copy_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT url, title
            FROM urls
            ORDER BY last_visit_time DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        history = [{"url": url, "title": title} for url, title in rows]
        return history

    def block_websites(self, response):
        data = response.get("data", {})
        website_list = data.get("blocked_websites", [])
        host_file_path = r"C:\Windows\System32\drivers\etc\hosts"

        try:
            with open(host_file_path, "r") as f:
                content = f.read()

            with open(host_file_path, "a") as f:
                for site in website_list:
                    if site not in content:
                        f.write(f"127.0.0.1 {site}\n")
                        print(f"Blocked {site}")
        except PermissionError:
            print("Run as administrator")
        except Exception as e:
            print(f"ERROR BLOCKING: {e}")

    def start_periodic_history(self):
        while self.running:
            self.send_chrome_history()
            time.sleep(HISTORY_INTERVAL)

    def start(self):
        self.connect_to_server()
        self.send_auth()
        # check if auth is confirmed
        self.receive_data()

        # Every 10 mins send history
        threading.Thread(target=self.start_periodic_history, daemon=True).start()
        # Check incoming messages
        while self.running:
            self.receive_data()


if __name__ == "__main__":
    child = Child(SERVER_HOST, SERVER_PORT)
    child.start()
