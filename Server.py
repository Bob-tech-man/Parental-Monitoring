import socket
import threading
import json
import AiLogic

host = "172.20.148.124"
port = 9000
class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.agent = AiLogic.AiModule(AiLogic.key)

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"Listening...")

        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client,args=(conn, addr),daemon=True).start()

    def handle_client(self, conn, addr):
        print(f"Conn: {addr}")
        check_new = ""

        try:
            while True:
                chunk = conn.recv(4096).decode('utf-8')
                if not chunk:
                    break
                check_new += chunk
                while "\n" in check_new:
                    line, check_new = check_new.split("\n", 1)
                    if line.strip():
                        self.handle_data(line, conn)

        except Exception as e:
            print(f"Error {addr}: {e}")
        finally:
            print(f"Closing conn: {addr}")
            conn.close()

    def handle_data(self, json_str, conn):
        msg = json.loads(json_str)

        data_type = msg.get("type")
        recv_data = msg.get("data")
        child_age = msg.get("age")

        if data_type == "HISTORY":
            result = self.process_history(recv_data, child_age)
            response = {
                "type": "BLOCK",
                "data": result
            }
            conn.sendall((json.dumps(response) + "\n").encode('utf-8'))

    def process_history(self, data, age):
        history_sites = []

        for item in data:
            url = item.get("url", "")
            if url:
                domain = url.split("//")[-1].split("/")[0]
                history_sites.append(domain)

        raw_response = self.agent.check_history(age, history_sites)

        parsed = AiLogic.parse_ai_json(raw_response)
        return parsed



if __name__ == "__main__":
    server = Server(host,port)
    server.start()
