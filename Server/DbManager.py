import sqlite3
from datetime import datetime
import json


class DbHandler:
    def __init__(self, db_name="history.db"):
        self.db_name = db_name
        conn = sqlite3.connect(self.db_name)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS web_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id TEXT,
                child_name TEXT,
                domain TEXT,
                visit_time TEXT,
                UNIQUE(child_id, domain, visit_time)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS blocked_history (
                child_id TEXT,
                child_name TEXT,
                domain TEXT,
                reason TEXT,
                block_time TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save_history(self, child_id, child_name, history_data):
        if isinstance(history_data, str):
            try:
                history_data = json.loads(history_data)
            except:
                print("Failed to parse history_data string")
                return

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        for item in history_data:
            if not isinstance(item, dict):
                continue

            url = item.get("url", "")
            domain = url.split("//")[-1].split("/")[0] if "//" in url else url

            if domain.startswith("www."):
                domain = domain[4:]

            visit_time_raw = item.get("visit_time", "Unknown")

            if isinstance(visit_time_raw, dict):
                visit_time_str = json.dumps(visit_time_raw)
            else:
                visit_time_str = str(visit_time_raw)

            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO web_history
                    (child_id, child_name, domain, visit_time)
                    VALUES (?, ?, ?, ?)
                    """,
                    (str(child_id), str(child_name), str(domain), visit_time_str)
                )
            except Exception as e:
                print(f"Database row insert error: {e}")

        conn.commit()
        conn.close()

    def save_blocked_sites(self, child_id, child_name, blocked_data):

        if isinstance(blocked_data, str):
            blocked_data = json.loads(blocked_data)

        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sites = blocked_data.get("blocked_websites", [])
        reasons = blocked_data.get("reason_for_each", [])

        for i in range(len(sites)):
            reason = reasons[i] if i < len(reasons) else "No reason provided"

            cursor.execute(
                "INSERT INTO blocked_history VALUES (?, ?, ?, ?, ?)",
                (child_id, child_name, sites[i], reason, now)
            )

        conn.commit()
        conn.close()


    def delete_blocked_site(self, child_id, domain):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM blocked_history WHERE child_id = ? AND domain = ?",
            (str(child_id), str(domain))
        )
        conn.commit()
        conn.close()

    def get_history(self, child_id=None):
        """Fetches the history from the database, newest entries first."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        if child_id:
            query = """
                SELECT domain, visit_time 
                FROM web_history 
                WHERE child_id = ? 
                ORDER BY visit_time DESC
            """
            cursor.execute(query, (str(child_id),))
        else:
            query = "SELECT domain, visit_time FROM web_history ORDER BY visit_time DESC"
            cursor.execute(query)

        rows = cursor.fetchall()
        conn.close()
        return rows