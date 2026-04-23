import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("dark")
# UI Constants
COLOR_BG_DARK = "#121212"
COLOR_ACCENT = "#3498db"
COLOR_DANGER = "#e74c3c"
COLOR_SUCCESS = "#2ecc71"


class ParentalGUI(ctk.CTk):
    def __init__(self, server_instance):
        super().__init__()

        self.server = server_instance
        self.db = server_instance.db
        self.selected_child_id = None

        self.title("Smart Parental Guard")
        self.geometry("1200x800")
        self.configure(fg_color=COLOR_BG_DARK)

        # Main Layout: Sidebar and Content Area
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT SIDEBAR (Navigation & System Controls) ---
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(self.sidebar, text="🛡️ GUARD PRO", font=("Inter", 22, "bold"), text_color=COLOR_ACCENT).grid(row=0, column=0, padx=20, pady=30)

        # Registry Controls Group
        ctk.CTkLabel(self.sidebar, text="SYSTEM TOOLS", font=("Inter", 12, "bold"), text_color="gray").grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")

        reg_configs = [
            ("Disable CMD", "cmd"),
            ("Disable TaskMgr", "taskmgr"),
            ("Disable RegEdit", "regedit"),
            ("Disable Settings", "cpcontrol"),
            ("Disable USB", "usb")
        ]

        for i, (name, cmd_key) in enumerate(reg_configs):
            btn = ctk.CTkButton(self.sidebar, text=name, fg_color="transparent", border_width=1, anchor="w",
                                hover_color="#2c3e50", command=lambda k=cmd_key: self.send_registry_block(k))
            btn.grid(row=i + 2, column=0, padx=20, pady=5, sticky="ew")

        # Master Lock at Bottom
        self.lock_btn = ctk.CTkButton(self.sidebar, text="SELECT DEVICE", state="disabled", fg_color="#333",
                                      height=45, font=("Inter", 13, "bold"), command=self.toggle_lock)
        self.lock_btn.grid(row=11, column=0, padx=20, pady=20, sticky="ew")

        # --- RIGHT CONTENT AREA ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)

        # 1. Device Selector Bar
        self.device_frame = ctk.CTkScrollableFrame(self.content_frame, height=60, orientation="horizontal",
                                                   fg_color="#1a1a1a", label_text="Connected Devices")
        self.device_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.client_buttons_frame = self.device_frame

        # 2. History and Blocking Card
        self.monitor_card = ctk.CTkFrame(self.content_frame)
        self.monitor_card.grid(row=1, column=0, sticky="nsew", pady=(0, 20))
        self.monitor_card.grid_columnconfigure(0, weight=3)
        self.monitor_card.grid_columnconfigure(1, weight=2)
        self.monitor_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.monitor_card, text="Recent Web Activity", font=("Inter", 16, "bold")).grid(row=0, column=0,
                                                                                                     padx=20, pady=10,
                                                                                                     sticky="w")
        self.history_display = ctk.CTkTextbox(self.monitor_card, font=("Consolas", 12), fg_color="#0a0a0a")
        self.history_display.grid(row=1, column=0, padx=(20, 10), pady=(0, 20), sticky="nsew")

        ctk.CTkLabel(self.monitor_card, text="Blocked Sites (AI/Manual)", font=("Inter", 16, "bold")).grid(row=0,
                                                                                                           column=1,
                                                                                                           padx=10,
                                                                                                           pady=10,
                                                                                                           sticky="w")
        self.blocked_scrollable = ctk.CTkScrollableFrame(self.monitor_card, fg_color="#0a0a0a")
        self.blocked_scrollable.grid(row=1, column=1, padx=(10, 20), pady=(0, 20), sticky="nsew")

        # 3. Action Bar (Manual Block & Message)
        self.action_card = ctk.CTkFrame(self.content_frame, height=150)
        self.action_card.grid(row=2, column=0, sticky="ew")
        self.action_card.grid_columnconfigure((0, 1), weight=1)

        # Manual Block Sub-frame
        block_sub = ctk.CTkFrame(self.action_card, fg_color="transparent")
        block_sub.grid(row=0, column=0, padx=20, pady=15, sticky="nsew")
        self.url_entry = ctk.CTkEntry(block_sub, placeholder_text="Enter URL to block...")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(block_sub, text="Block", width=80, command=self.manual_block).pack(side="right")

        # Messaging Sub-frame
        msg_sub = ctk.CTkFrame(self.action_card, fg_color="transparent")
        msg_sub.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")
        self.msg_entry = ctk.CTkEntry(msg_sub, placeholder_text="Send remote message...")
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(msg_sub, text="Send", width=80, fg_color=COLOR_SUCCESS, hover_color="#27ae60",
                      command=self.send_message_to_child).pack(side="right")

        self.update_ui_loop()
    def update_ui_loop(self):
        """ Refresh the client list and db data every 30 seconds """

        self.refresh_client_list()
        if self.selected_child_id:
            self.load_data_from_db()
        self.after(30000, self.update_ui_loop)  # Refresh every 30 seconds


    def clear_dashboard(self):
        """Wipes the main content area when a child disconnects."""

        # Remove search history from gui
        self.history_display.delete("0.0", "end")
        # Remove blocked websites from gui
        for widget in self.blocked_scrollable.winfo_children():
            widget.destroy()
        # Set Lock button to default
        self.lock_btn.configure(state="disabled", text="SELECT DEVICE", fg_color="#333")



    def refresh_client_list(self):
        """ Refreshes client list to show connected clients """

        for child in self.client_buttons_frame.winfo_children():
            child.destroy()

        for child_id, info in self.server.clients.items():
            color = "#1f538d" if child_id == self.selected_child_id else "transparent"
            btn = ctk.CTkButton(self.client_buttons_frame, text=f"👤 {info['name']}",
                                fg_color=color, width=120,
                                command=lambda cid=child_id: self.select_child(cid))
            btn.pack(side="left", padx=5)


    def select_child(self, child_id):
        self.selected_child_id = child_id
        is_locked = self.server.clients[child_id].get("is_locked", False)
        self.update_lock_button_ui(is_locked)
        self.load_data_from_db()

    def load_data_from_db(self):
        if not self.selected_child_id:
            return

        # Update History Box

        history = self.db.get_history(self.selected_child_id)
        history = history[:30]

        # Formatting the strings for the display
        new_content = "".join([f"[{vtime}] {domain}\n" for domain, vtime in history])
        current_content = self.history_display.get("0.0", "end-1c")

        if new_content.strip() != current_content.strip():
            self.history_display.delete("0.0", "end")
            self.history_display.insert("0.0", new_content)

        # Update Blocked Table
        import sqlite3
        conn = sqlite3.connect("history.db")
        cursor = conn.cursor()
        # Getting the blocked sites & reasons
        cursor.execute("SELECT domain, reason FROM blocked_history WHERE child_id=? ORDER BY block_time DESC",
                       (self.selected_child_id,))
        blocks = cursor.fetchall()

        # redraw if needed
        if len(blocks) != len(self.blocked_scrollable.winfo_children()):
            for widget in self.blocked_scrollable.winfo_children():
                widget.destroy()

            for site, reason in blocks:

                card = ctk.CTkFrame(self.blocked_scrollable, fg_color="#252525", corner_radius=8)
                card.pack(fill="x", pady=5, padx=5)

                # Container for Site Name and X Button
                header_frame = ctk.CTkFrame(card, fg_color="transparent")
                header_frame.pack(fill="x", padx=10, pady=(5, 0))

                ctk.CTkLabel(header_frame, text=site, anchor="w", text_color="#3498db",
                             font=("Inter", 12, "bold")).pack(side="left")

                # The "X" Button
                unblock_btn = ctk.CTkButton(header_frame, text="X", width=20, height=20,
                                            fg_color=COLOR_DANGER, hover_color="#c0392b",
                                            command=lambda s=site: self.request_unblock(s))
                unblock_btn.pack(side="right")

                # Reason (Wrappable text so it doesn't cut off)
                reason_label = ctk.CTkLabel(card, text=reason, anchor="w", font=("Inter", 11), text_color="#bbb", justify="left", wraplength=400)
                reason_label.pack(side="top", padx=10, pady=(2, 8), fill="x")

        conn.close()

    def request_unblock(self, domain):
        if self.selected_child_id:
            if self.server.unblock_site(self.selected_child_id, domain):
                self.load_data_from_db()  # Refresh GUI

    def send_registry_block(self, b_type):

        if not self.selected_child_id:
            print("No child selected!")
            return

        conn = self.server.clients[self.selected_child_id]["conn"]
        if b_type == "cmd":
            self.server.block_cmd(conn)
        elif b_type == "taskmgr":
            self.server.block_tsk(conn)
        elif b_type == "regedit":
            self.server.block_regedit(conn)
        elif b_type == "cpcontrol":
            self.server.block_cp_settings(conn)
        elif b_type == "usb":
            self.server.block_usb_drivers(conn)

        print(f"Sent {b_type} block to {self.selected_child_id}")


    def manual_block(self):
        raw_input = self.url_entry.get().strip()

        if not raw_input or not self.selected_child_id:
            return

        clean_domain = raw_input.lower()

        if clean_domain.startswith("https://"):
            clean_domain = clean_domain.replace("https://", "", 1)
        elif clean_domain.startswith("http://"):
            clean_domain = clean_domain.replace("http://", "", 1)

        # Chop off any paths after the domain (e.g., youtube.com/watch -> youtube.com)
        clean_domain = clean_domain.split('/')[0]

        # Check if it has atleast 1 dot and no spaces
        if "." not in clean_domain or " " in clean_domain:
            # Trigger the popup window
            messagebox.showerror(
                title="Invalid Input",
                message=f"'{raw_input}' is not a valid website domain.\n\nPlease enter a valid URL (e.g., youtube.com)."
            )
            self.url_entry.delete(0, 'end')
            return

        # 3. Send the cleaned domain to the server
        success = self.server.manual_block_site(self.selected_child_id, clean_domain)

        if success:
            self.url_entry.delete(0, 'end')
            self.load_data_from_db()
        else:
            print("Server failed to block the site manually.")



    def toggle_lock(self):
        if not self.selected_child_id:
            return

        child_info = self.server.clients.get(self.selected_child_id)


        if child_info is None:
            print(f"Error: Child {self.selected_child_id} is no longer connected.")
            self.selected_child_id = None
            self.refresh_client_list()
            return


        is_locked = child_info.get("is_locked", False)

        # Flip the state
        new_state = not is_locked
        self.server.lock_child_pc(child_info["conn"], 1 if new_state else 0) # send 1 if TRUE, send 0 if FALSE

        # Update state
        child_info["is_locked"] = new_state
        self.update_lock_button_ui(new_state)
    def update_lock_button_ui(self, is_locked):
        if is_locked:
            self.lock_btn.configure(text="🔓 UNLOCK DEVICE", fg_color="#2ecc71", hover_color="#27ae60")
        else:
            self.lock_btn.configure(text="🔒 LOCK DEVICE", fg_color="#d90429", hover_color="#8d0801")
        self.lock_btn.configure(state="normal")


    def send_message_to_child(self):
        msg = self.msg_entry.get().strip()

        if not self.selected_child_id:
            print("Select a child first!")
            return


        child_id = str(self.selected_child_id)

        if msg:
            if child_id in self.server.clients:
                conn = self.server.clients[child_id]["conn"]
                self.server.send_popup(conn, msg)
                self.msg_entry.delete(0, 'end')
            else:
                print(f"Error: Child ID {child_id} not found in connected clients!")
                print(f"Current clients: {list(self.server.clients.keys())}")




    def prompt_registration(self, conn, addr):
        """Creates a popup window for new connections"""
        reg_window = ctk.CTkToplevel(self)
        reg_window.title("New Connection Detected")
        reg_window.geometry("300x400")
        reg_window.attributes("-topmost", True)

        ctk.CTkLabel(reg_window, text=f"New Device: {addr[0]}", font=("Inter", 14, "bold")).pack(pady=10)

        name_entry = ctk.CTkEntry(reg_window, placeholder_text="Enter Child Name")
        name_entry.pack(pady=10, padx=20, fill="x")

        age_entry = ctk.CTkEntry(reg_window, placeholder_text="Enter Child Age")
        age_entry.pack(pady=10, padx=20, fill="x")

        id_entry = ctk.CTkEntry(reg_window, placeholder_text="Enter Unique ID")
        id_entry.pack(pady=10, padx=20, fill="x")

        def submit():
            name = name_entry.get()
            age = age_entry.get().strip()
            cid = id_entry.get().strip()
            if name and age and cid:
                if not age.isdigit():
                    messagebox.showerror(
                        title="Invalid Age",
                        message="Please enter a valid number for the Child Age."
                    )
                    age_entry.delete(0, 'end')  # Clear the wrong input
                    return
                # Tell the server to register this client formally
                self.server.register_new_child(conn, cid, name, int(age))

                # Update CONNECTED list after sign up
                self.refresh_client_list()

                reg_window.destroy()

        ctk.CTkButton(reg_window, text="Register & Start Monitoring", command=submit).pack(pady=20)