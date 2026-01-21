import sqlite3
import shutil
import os
import json
import socket

SERVER_HOST = "172.20.148.124"
SERVER_PORT = 9000


class Child():
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port

        self.age = int(input("Enter child age: "))

        self.buffer = ""

        # history path & path to copy
        self.chrome_history = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History")
        self.copy_path = os.path.expanduser(r"~\chrome_history_copy.db")


    def connect_to_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, SERVER_PORT))
        return sock

    def receive_data(self, sock):
        while True:
        # \n = new message
            if "\n" in self.buffer:
                msg, self.buffer = self.buffer.split("\n", 1)
                return json.loads(msg)

            data = sock.recv(4096).decode('utf-8')
            if not data:
                return None

            self.buffer += data

    def send_chrome_history(self, sock):
        history = self.get_chrome_history(50)
        data = {"age": self.age, "type": "HISTORY", "data": history}
        json_data = json.dumps(data)
        sock.sendall((json_data + "\n").encode('utf-8'))


    def get_chrome_history(self, limit):
        # make a copy of the db because it is locked
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

        history = []
        for url, title in rows:
            history.append({"url": url, "title": title})

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


if __name__ == "__main__":
    c1 = Child(SERVER_HOST, SERVER_PORT)
    connection = c1.connect_to_server()

    try:
        c1.send_chrome_history(connection)

        print("History sent, wait...")
        response = c1.receive_data(connection)

        if response:
            print(f"Server said to block: {response['data']}")
            c1.block_websites(response)

    except Exception as e:
        print(f"ErrorMAIN: {e}")
