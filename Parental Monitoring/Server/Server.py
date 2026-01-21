import socket
import threading
import json
import AiLogic
import FetchMyIP

host = f"{FetchMyIP.get_local_ip()}"
port = 9000
class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.active_clients = {} # SAVES CLIENTS THAT ARE ACTIVE: (NAME,AGE,IP)
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
        client_ip = addr[0]
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
                        self.handle_data(line, conn, client_ip)

        except Exception as e:
            print(f"Error {addr}: {e}")
        finally:
            if conn in self.active_clients:
                user = self.active_clients[conn]["name"]
                print(f"[DISCONNECT] {user} ({client_ip}) disconnected.")
                del self.active_clients[conn]

            conn.close()

    def handle_data(self, json_str, conn, client_ip):
        msg = json.loads(json_str)

        data_type = msg.get("type")
        recv_data = msg.get("data")
        child_name = msg.get("name")
        child_age = msg.get("age")

        if data_type == "AUTHENTICATION":
            self.active_clients[conn] = {"name": child_name,"age": child_age,"ip": client_ip}
            # Active clinet with the connection, saved his name blah blah blah
            print(f"[AUTH] User '{child_name}' (Age: {child_age}) authenticated from {client_ip}")

        elif data_type == "HISTORY":
            result = self.process_history(recv_data, child_age)
            response = {
                "type": "BLOCK_WEBSITES",
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