import re
with open("services/database.py", "r", encoding="utf-8") as f:
    code = f.read()

init_code = """
    def __init__(self, db_url=None):
        self.db_url = db_url or DATABASE_URL
        self.is_postgres = self.db_url.startswith("postgresql://") or self.db_url.startswith("postgres://")
        self.sqlite_conn = None
        self.pg_pool = None

    def get_connection(self):
        if self.is_postgres:
            if self.pg_pool is None:
                import psycopg2
                from psycopg2.pool import ThreadedConnectionPool
                from psycopg2.extras import RealDictCursor
                self.pg_pool = ThreadedConnectionPool(1, 20, self.db_url, cursor_factory=RealDictCursor)
            return self.pg_pool.getconn()
        else:
            if self.sqlite_conn is None:
                if self.db_url.startswith("sqlite:///"):
                    from pathlib import Path
                    db_path = Path(self.db_url.replace("sqlite:///", ""))
                else:
                    db_path = BASE_DIR / "spotbot.db"
                import sqlite3
                self.sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
                self.sqlite_conn.row_factory = sqlite3.Row
            return self.sqlite_conn

    def release_connection(self, conn):
        if self.is_postgres and self.pg_pool is not None and conn is not None:
            self.pg_pool.putconn(conn)
"""

code = re.sub(r"    def __init__\(self, db_url=None\):.*?    def connect\(self\):", init_code.strip("\n") + "\n\n    def connect(self):", code, flags=re.DOTALL)

code = code.replace("self.connect()\n        cursor = self.conn.cursor()", "conn = self.get_connection()\n        try:\n            cursor = conn.cursor()")
code = code.replace("cursor.execute(create_table_sql)\n        self.conn.commit()\n        self.close()", "cursor.execute(create_table_sql)\n            conn.commit()\n        finally:\n            self.release_connection(conn)")
code = code.replace("cursor.execute(sql, values)\n        self.conn.commit()\n        self.close()", "cursor.execute(sql, values)\n            conn.commit()\n        finally:\n            self.release_connection(conn)")

code = code.replace("self.connect()\n            query = f\"SELECT * FROM trades ORDER BY id DESC LIMIT {limit}\"\n            df = pd.read_sql_query(query, self.conn)\n            self.close()", "conn = self.get_connection()\n            try:\n                query = f\"SELECT * FROM trades ORDER BY id DESC LIMIT {limit}\"\n                df = pd.read_sql_query(query, conn)\n            finally:\n                self.release_connection(conn)")

code = code.replace("self.connect()\n            cursor = self.conn.cursor()\n            cursor.execute(\"SELECT COUNT(*) as total FROM trades\")", "conn = self.get_connection()\n            try:\n                cursor = conn.cursor()\n                cursor.execute(\"SELECT COUNT(*) as total FROM trades\")")
code = code.replace("_last_stats_time = now\n            return _stats_cache\n        except Exception:", "_last_stats_time = now\n                return _stats_cache\n            finally:\n                self.release_connection(conn)\n        except Exception:")

code = code.replace("self.connect()\n        cursor = self.conn.cursor()\n        \n        placeholder = \"%s\" if self.is_postgres else \"?\"\n        sql = f\"SELECT trade_result_net, oco_result FROM trades WHERE oco_timestamp LIKE {placeholder}\"\n        cursor.execute(sql, (f\"%{date_str}%\",))\n        rows = cursor.fetchall()\n        self.close()", "conn = self.get_connection()\n        try:\n            cursor = conn.cursor()\n            placeholder = \"%s\" if self.is_postgres else \"?\"\n            sql = f\"SELECT trade_result_net, oco_result FROM trades WHERE oco_timestamp LIKE {placeholder}\"\n            cursor.execute(sql, (f\"%{date_str}%\",))\n            rows = cursor.fetchall()\n        finally:\n            self.release_connection(conn)")

code = code.replace("self.connect()\n        cursor = self.conn.cursor()\n        \n        sql = \"SELECT order_index, symbol, quantity, buy_price, oco_result, oco_timestamp, trade_result_net, final_balance_usdt FROM trades\"", "conn = self.get_connection()\n        try:\n            cursor = conn.cursor()\n            sql = \"SELECT order_index, symbol, quantity, buy_price, oco_result, oco_timestamp, trade_result_net, final_balance_usdt FROM trades\"")
code = code.replace("cursor.execute(sql, tuple(params))\n        rows = cursor.fetchall()\n        self.close()", "cursor.execute(sql, tuple(params))\n            rows = cursor.fetchall()\n        finally:\n            self.release_connection(conn)")

with open("services/database.py", "w", encoding="utf-8") as f:
    f.write(code)
