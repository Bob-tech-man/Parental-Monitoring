import sqlite3
import shutil
import os
import socket
import winreg
import time
import threading
import CryptCode
import tkinter
import json
from tkinter import messagebox


SERVER_HOST = "192.168.1.191"
SERVER_PORT = 9000


class Child():
    def __init__(self, server_host, server_port):
        self.server_host = server_host
        self.server_port = server_port

        self.child_id = None
        self.child_name = None

        self.age = None

        self.check_new = ""

        # history path & path to copy
        self.chrome_history = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data\Default\History")
        self.copy_path = os.path.expanduser(r"~\chrome_history_copy.db")

    def connect_to_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, SERVER_PORT))
        return sock

    def receive_data(self, sock):
        while True:
            if "\n" in self.check_new:
                msg_encoded, self.check_new = self.check_new.split("\n", 1)
                # Decrypt here
                return CryptCode.decrypt_data(msg_encoded, CryptCode.CIPHER_KEY)

            data = sock.recv(4096).decode('utf-8')
            if not data:
                return None
            self.check_new += data

    def handle_data(self, response):
        """ Handle different types of data """

        data_type = response.get("type")
        if data_type == "SET_IDENTITY":
            data = response.get("data")
            self.child_id = data.get("id")
            self.child_name = data.get("name")
            self.age = data.get("age")
            print(f"Identity set: {self.child_name}, Age: {self.age}")
            # Start the history loop ONLY after we have an identity
            self.start_periodic_history_sender(connection)

        elif data_type == "BLOCK_WEBSITES":
            self.block_websites(response)
        elif data_type == "UNBLOCK_WEBSITE":
            self.unblock_website(response)
        elif data_type == "BLOCK_REGISTRIES":
            self.block_registries(response)
        elif data_type == "POPUP_MSG":
            self.show_popup(response)
        elif data_type == "LOCK_UN_PC":
            status = response.get("data")
            if status == 1:
                self.lock_pc()
            else:
                self.unlock_pc()
# ----------------Websites Related---------------------

    def send_chrome_history(self, sock):
        history = self.get_chrome_history(50)

        data = {
            "child_id": self.child_id,
            "child_name": self.child_name,
            "age": self.age,
            "type": "HISTORY",
            "data": history
        }

        print("History Sent")
        encrypted_msg = CryptCode.encrypt_data(data, CryptCode.CIPHER_KEY)
        sock.sendall((encrypted_msg + "\n").encode('utf-8'))

    def get_chrome_history(self, limit):
        shutil.copy2(self.chrome_history, self.copy_path)

        conn = sqlite3.connect(self.copy_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT url, title, datetime((last_visit_time/1000000)-11644473600, 'unixepoch', 'localtime') as visit_time
            FROM urls
            ORDER BY last_visit_time DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        history = []
        for url, title, visit_time in rows:
            history.append({"url": url, "title": title, "visit_time": visit_time})

        return history

    def block_websites(self, response):
        data = response.get("data", {})
        website_list = data.get("blocked_websites", [])

        host_file_path = r"C:\Windows\System32\drivers\etc\hosts"
        try:
            with open(host_file_path, "r") as f:
                content = f.read()

            with open(host_file_path, "a") as f:

                # make sure it doesnt write in the "comments" section of the host file
                if content and not content.endswith('\n'):
                    f.write('\n')

                for site in website_list:
                    # Safety incase server sends www. link
                    clean_site = site.lower().replace("www.", "")

                    base_domain = clean_site
                    www_domain = f"www.{clean_site}"

                    if base_domain not in content:
                        f.write(f"127.0.0.1 {base_domain}\n")
                        print(f"Blocked {base_domain}")

                    if www_domain not in content:
                        f.write(f"127.0.0.1 {www_domain}\n")
                        print(f"Blocked {www_domain}")

        except PermissionError:
            print("Run as administrator")
        except Exception as e:
            print(f"ERROR BLOCKING: {e}")

    def unblock_website(self, response):
        domain_to_remove = response.get("data", {}).get("domain", "").lower().replace("www.", "")
        www_domain = f"www.{domain_to_remove}"
        host_file_path = r"C:\Windows\System32\drivers\etc\hosts"

        try:
            with open(host_file_path, "r") as f:
                lines = f.readlines()

            with open(host_file_path, "w") as f:
                for line in lines:
                    keep_line = True
                    stripped_line = line.strip().lower()

                    # skip empty lines and comment lines
                    if stripped_line and not stripped_line.startswith("#"):
                        # Split the line into ['127.0.0.1', '[example].com'])
                        parts = stripped_line.split()

                        # if domain in line = dont keep the line
                        if len(parts) >= 2 and (domain_to_remove in parts[1:] or www_domain in parts[1:]):
                            keep_line = False

                    # If it didn't match our exact domains, write it back to the file
                    if keep_line:
                        f.write(line)

            print(f"Successfully unblocked {domain_to_remove}")
        except PermissionError:
            print("Unblock failed: Need Admin Privileges")
        except Exception as e:
            print(f"Error unblocking: {e}")

# -----------------------------------------------------

# ----------------Registries Related-------------------
    def block_registries(self, response):
        data = response.get("data", {})

        name = data.get("name")
        path = data.get("path")
        key_name = data.get("key")
        value_type = data.get("type")
        value = data.get("value")

        if not all([path, key_name, value_type]):
            return {"status": "error", "message": "Missing required fields"}

        type_map = {
            "REG_DWORD": winreg.REG_DWORD,
            "REG_SZ": winreg.REG_SZ,
            "REG_BINARY": winreg.REG_BINARY
        }

        reg_type = type_map.get(value_type)
        if reg_type is None:
            return {"status": "error", "message": "Unsupported registry type"}

        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as registry_key:
                winreg.SetValueEx(registry_key, key_name, 0, reg_type, value)

            return {"status": "success", "message": f"{name} applied"}

        except Exception as e:
             return {"status": "error", "message": str(e)}

# -----------------------------------------------------

# -------------------GUI Related-----------------------
    def lock_pc(self):
        # If window doesn't exist, create it once
        if not hasattr(self, 'lock_window') or self.lock_window is None:
            def start_lock_thread():
                self.lock_window = tkinter.Tk()
                self.lock_window.title("Parental Control")
                self.lock_window.overrideredirect(True)

                # Set geometry and attributes
                screen_width = self.lock_window.winfo_screenwidth()
                screen_height = self.lock_window.winfo_screenheight()
                self.lock_window.geometry(f"{screen_width}x{screen_height}+0+0")
                self.lock_window.configure(bg="#1a1a1a")
                self.lock_window.attributes("-topmost", True)

                message_label = tkinter.Label(
                    self.lock_window,
                    text="Blocked by Parent\n\nPlease wait for permission.",
                    font=("Helvetica", 32, "bold"),
                    fg="#e74c3c",
                    bg="#1a1a1a",
                    justify="center"
                )
                message_label.pack(expand=True)

                self.lock_window.mainloop()

            lock_thread = threading.Thread(target=start_lock_thread, daemon=True)
            lock_thread.start()


            time.sleep(0.5)


        try:
            self.lock_window.after(0, self.lock_window.deiconify)
            self.lock_window.after(0, lambda: self.lock_window.attributes("-topmost", True))
            print("Device locked.")
        except Exception as e:
            print(f"Lock error: {e}")

    def unlock_pc(self):
        if hasattr(self, 'lock_window') and self.lock_window:
            try:
                # withdraw() hides the window without destroying the screen
                self.lock_window.after(0, self.lock_window.withdraw)
                print("Device unlocked by parent.")
            except Exception as e:
                print(f"Error during unlock: {e}")


    def show_popup(self, response):
        # data = msg from server
        msg_content = response.get("data", "No message provided")

        def render_window():
            root = tkinter.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo("Message from Parent", msg_content)
            root.destroy()

        # theard to prevent socket failure
        popup_thread = threading.Thread(target=render_window)
        popup_thread.start()

# -----------------------------------------------------


# ---------------Periodic Send-------------------------
    def periodic_history_loop(self, sock):
        while True:
            try:
                self.send_chrome_history(sock)
                print("History sent to server.")
            except Exception as e:
                print(f"Error sending history: {e}")

            time.sleep(600)

    def start_periodic_history_sender(self, sock):
        thread = threading.Thread(target=self.periodic_history_loop,args=(sock,),daemon=True)
        thread.start()

# -----------------------------------------------------


if __name__ == "__main__":
    c1 = Child(SERVER_HOST, SERVER_PORT)
    connection = c1.connect_to_server()

    try:

        print("Connected. Listening for server commands...")

        while True:
            response = c1.receive_data(connection)
            if not response:
                break

            print(f"Server command: {response}")
            c1.handle_data(response)

    except Exception as e:
        print(f"ErrorMAIN: {e}")

    finally:
        print("Closing connection...")
        connection.close()