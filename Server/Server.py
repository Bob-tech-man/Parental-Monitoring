import socket
import threading
import json
import AiLogic
import DbManager
import CryptCode
from dotenv import load_dotenv
load_dotenv()

host = "172.20.138.140"
port = 9000


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.agent = AiLogic.AiModule()
        self.db = DbManager.DbHandler()

        self.clients = {}


    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"Server started on {self.host}:{self.port}")

        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

    def register_new_child(self, conn, child_id, name, age):
        """Called by GUI to finalize the connection"""
        self.clients[child_id] = {
            "name": name,
            "conn": conn,
            "age": age,
            "is_locked": False
        }

        # Inform the client of its new identity
        identity_msg = {
            "type": "SET_IDENTITY",
            "data": {"id": child_id, "name": name, "age": age}
        }
        encrypted = CryptCode.encrypt_data(identity_msg, CryptCode.CIPHER_KEY)
        conn.sendall((encrypted + "\n").encode('utf-8'))
        print(f"Registered {name} from Server side.")

    def handle_client(self, conn, addr):
        if hasattr(self, 'gui_app'):
            self.gui_app.after(0, self.gui_app.prompt_registration(conn, addr))

        check_new = ""
        try:
            while True:
                chunk = conn.recv(4096).decode('utf-8')
                if not chunk: break

                check_new += chunk
                while "\n" in check_new:
                    line, check_new = check_new.split("\n", 1)
                    line = line.strip()
                    if line:
                        try:
                            decrypted_msg = CryptCode.decrypt_data(line, CryptCode.CIPHER_KEY)

                            if decrypted_msg:
                                self.handle_data(decrypted_msg, conn)
                            else:
                                print("Failed to decrypt line. Ignoring...")

                        except Exception as inner_e:
                            print(f"Data processing error: {inner_e}")


        except Exception as e:
            print(f"Error {addr}: {e} HANDLECLIENT")

        finally:

            for cid, info in list(self.clients.items()):
                if info["conn"] == conn:
                    print(f"Removing child {cid} ({info['name']})")
                    del self.clients[cid]

                    # Force GUI update safely from the server thread
                    if hasattr(self, 'gui_app'):
                        # deselect the disconnected client
                        if self.gui_app.selected_child_id == cid:
                            self.gui_app.selected_child_id = None

                            # Wipe the center dashboard clean
                            self.gui_app.after(0, self.gui_app.clear_dashboard)

                            # Trigger the UI refresh immediately on the main GUI thread
                        self.gui_app.after(0, self.gui_app.refresh_client_list)



            print(f"Closing conn: {addr}")
            conn.close()

    def handle_data(self, msg, conn):

        data_type = msg.get("type")
        recv_data = msg.get("data")
        child_age = msg.get("age")
        child_id = msg.get("child_id")
        child_name = msg.get("child_name")
        print(child_id, child_name)

        if child_id and child_name:
            self.clients[child_id] = {
                "name": child_name,
                "conn": conn
            }
            print(f"Registered child: {child_name} (ID: {child_id})")

        if data_type == "HISTORY":
            self.db.save_history(child_id, child_name, recv_data)

            result = self.process_history(recv_data, child_age)

            if result and result.get("blocked_websites"):
                self.db.save_blocked_sites(child_id, child_name, result)

            response = {
                "type": "BLOCK_WEBSITES",
                "data": result
            }

            encrypted_resp = CryptCode.encrypt_data(response, CryptCode.CIPHER_KEY)
            conn.sendall((encrypted_resp + "\n").encode('utf-8'))

    # -----------------------------GUI STUFF-----------------------------
    def send_popup(self, conn, msg):
        """ Sends pop up client pc with message """

        response = {
            "type": "POPUP_MSG",
            "data": msg
        }
        encrypted_resp = CryptCode.encrypt_data(response, CryptCode.CIPHER_KEY)
        conn.sendall((encrypted_resp + "\n").encode('utf-8'))

    def lock_child_pc(self, conn, lock_state):
        """ Sends command to lock/unlock client pc based on state """
        # lock_state: 1 for lock, 0 for unlock

        response = {
            "type": "LOCK_UN_PC",
            "data": lock_state
        }
        encrypted_resp = CryptCode.encrypt_data(response, CryptCode.CIPHER_KEY)
        conn.sendall((encrypted_resp + "\n").encode('utf-8'))
    # -------------------------------------------------------------------
    def process_history(self, data, age):
        """ Send client history to AI and return the result """

        history_sites = []
        for item in data:
            url = item.get("url", "")
            if url:
                domain = url.split("//")[-1].split("/")[0]
                if domain.startswith("www."):
                    domain = domain[4:]
                history_sites.append(domain)

        raw_response = self.agent.check_history(age, list(history_sites))
        parsed = AiLogic.parse_ai_json(raw_response)
        return parsed

    def manual_block_site(self, id, url):
        if id in self.clients:
            child_name = self.clients[id]["name"]
            conn = self.clients[id]["conn"]

            block_data = {
                 "blocked_websites": [url],
                 "reason_for_each": ["נחסם ידנית על ידי ההורה"]
             }
            self.db.save_blocked_sites(id, child_name, block_data)

            response = {
                "type": "BLOCK_WEBSITES",
                "data": {"blocked_websites": [url], "reason_for_each": ["נחסם ידנית על ידי ההורה"]}
            }

            try:
                encrypted = CryptCode.encrypt_data(response, CryptCode.CIPHER_KEY)
                conn.sendall((encrypted + "\n").encode('utf-8'))
                print(f"Manually blocked {url} for {child_name}")
                return True
            except Exception as e:
                print(f"Failed to send manual block to {child_name}: {e}")
                return False
        else:
            print(f"Cannot block: Child ID {id} is not connected.")
            return False

    def unblock_site(self, child_id, domain):
        if child_id in self.clients:

            self.db.delete_blocked_site(child_id, domain)

            conn = self.clients[child_id]["conn"]
            unblock_msg = {
                "type": "UNBLOCK_WEBSITE",
                "data": {"domain": domain}
            }
            encrypted = CryptCode.encrypt_data(unblock_msg, CryptCode.CIPHER_KEY)
            conn.sendall((encrypted + "\n").encode('utf-8'))
            print("YAY")
            return True

        print("NAY")
        return False

    # -----------------------------REGISTRY BLOCKS-----------------------------
    def block_tsk(self, conn):
       block = {
        "name": "Disable Task Manager",
        "description": "Prevents the child from killing the monitoring agent process.",
        "path": "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
        "key": "DisableTaskMgr",
        "type": "REG_DWORD",
        "value": 1
        }
       output = {"type": "BLOCK_REGISTRIES","data": block}
       encrypted_resp = CryptCode.encrypt_data(output, CryptCode.CIPHER_KEY)
       conn.sendall((encrypted_resp + "\n").encode('utf-8'))

    def block_cmd(self,conn):
        block = {
            "name": "Disable Command Prompt (CMD)",
            "description": "Prevents running scripts or advanced commands. Value 2 blocks CMD but allows .bat files; Value 1 blocks both.",
            "path": "Software\\Policies\\Microsoft\\Windows\\System",
            "key": "DisableCMD",
            "type": "REG_DWORD",
            "value": 1
        }
        output = {"type": "BLOCK_REGISTRIES", "data": block}
        encrypted_resp = CryptCode.encrypt_data(output, CryptCode.CIPHER_KEY)
        conn.sendall((encrypted_resp + "\n").encode('utf-8'))

    def block_regedit(self,conn):
        block = {
            "name": "Disable Registry Editor",
            "description": "Prevents the child from undoing these registry blocks.",
            "path": "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
            "key": "DisableRegistryTools",
            "type": "REG_DWORD",
            "value": 1
        }
        output = {"type": "BLOCK_REGISTRIES", "data": block}
        encrypted_resp = CryptCode.encrypt_data(output, CryptCode.CIPHER_KEY)
        conn.sendall((encrypted_resp + "\n").encode('utf-8'))

    def block_usb_drivers(self,conn):
        block = {
            "name": "Disable USB Storage",
            "description": "Prevents the system from mounting USB mass storage devices.",
            "path": "SYSTEM\\CurrentControlSet\\Services\\USBSTOR",
            "key": "Start",
            "type": "REG_DWORD",
            "value": 4
        }
        output = {"type": "BLOCK_REGISTRIES", "data": block}
        encrypted_resp = CryptCode.encrypt_data(output, CryptCode.CIPHER_KEY)
        conn.sendall((encrypted_resp + "\n").encode('utf-8'))

    def block_cp_settings(self,conn):
        block = {
            "name": "Disable Control Panel & Settings",
            "description": "Blocks access to system settings, Wi-Fi changes, and uninstallation.",
            "path": "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer",
            "key": "NoControlPanel",
            "type": "REG_DWORD",
            "value": 1
        }
        output = {"type": "BLOCK_REGISTRIES", "data": block}
        encrypted_resp = CryptCode.encrypt_data(output, CryptCode.CIPHER_KEY)
        conn.sendall((encrypted_resp + "\n").encode('utf-8'))


if __name__ == "__main__":
    import GUI

    server = Server(host, port)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    app = GUI.ParentalGUI(server)
    server.gui_app = app  # Link the app to the server
    app.mainloop()
