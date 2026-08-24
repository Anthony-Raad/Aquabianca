import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "aquabianca_pos.db"
DEFAULT_RATE = 89000.0
DEFAULT_LOW_STOCK_THRESHOLD = 5
INTEGRITY_ERRORS = (sqlite3.IntegrityError,)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = self._connect()
        self.setup()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _execute(self, cursor, query: str, params=()):
        cursor.execute(query, params)

    def _executemany(self, cursor, query: str, seq_of_params):
        cursor.executemany(query, seq_of_params)

    def setup(self) -> None:
        cursor = self.connection.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'cashier')),
                full_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price_lbp REAL NOT NULL,
                price_usd REAL NOT NULL,
                stock_qty INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS cash_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                opening_cash_lbp REAL NOT NULL DEFAULT 0,
                opening_cash_usd REAL NOT NULL DEFAULT 0,
                closing_cash_lbp REAL,
                closing_cash_usd REAL,
                status TEXT NOT NULL CHECK(status IN ('open', 'closed')),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                customer_no INTEGER NOT NULL DEFAULT 1,
                sold_at TEXT NOT NULL,
                total_lbp REAL NOT NULL,
                total_usd REAL NOT NULL,
                FOREIGN KEY(session_id) REFERENCES cash_sessions(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                qty INTEGER NOT NULL,
                unit_price_lbp REAL NOT NULL,
                unit_price_usd REAL NOT NULL,
                line_total_lbp REAL NOT NULL,
                line_total_usd REAL NOT NULL,
                FOREIGN KEY(sale_id) REFERENCES sales(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            """
        )
        sales_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(sales)").fetchall()}
        if "customer_no" not in sales_columns:
            cursor.execute("ALTER TABLE sales ADD COLUMN customer_no INTEGER NOT NULL DEFAULT 1")

        user_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(users)").fetchall()}
        if "active" not in user_columns:
            cursor.execute("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")

        self.connection.commit()
        self.seed_defaults()

    def seed_defaults(self) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO NOTHING
            """,
            ("exchange_rate", str(DEFAULT_RATE)),
        )
        self._execute(
            cursor,
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO NOTHING
            """,
            ("low_stock_threshold", str(DEFAULT_LOW_STOCK_THRESHOLD)),
        )

        default_users = [
            ("admin", hash_password("admin123"), "admin", "System Admin"),
            ("cashier", hash_password("cashier123"), "cashier", "Main Cashier"),
        ]
        self._executemany(
            cursor,
            """
            INSERT INTO users (username, password_hash, role, full_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username) DO NOTHING
            """,
            default_users,
        )

        self.connection.commit()

    # -- Auth / users -----------------------------------------------------

    def authenticate_user(self, username: str, password: str):
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            SELECT * FROM users
            WHERE username = ? AND password_hash = ? AND active = 1
            """,
            (username.strip(), hash_password(password)),
        )
        return cursor.fetchone()

    def get_all_users(self):
        cursor = self.connection.cursor()
        self._execute(cursor, "SELECT * FROM users ORDER BY username")
        return cursor.fetchall()

    def get_user_by_id(self, user_id: int):
        cursor = self.connection.cursor()
        self._execute(cursor, "SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()

    def add_user(self, username: str, full_name: str, role: str, password: str) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            INSERT INTO users (username, password_hash, role, full_name, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (username.strip(), hash_password(password), role, full_name.strip()),
        )
        self.connection.commit()

    def update_user(self, user_id: int, full_name: str, role: str) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            "UPDATE users SET full_name = ?, role = ? WHERE id = ?",
            (full_name.strip(), role, user_id),
        )
        self.connection.commit()

    def set_user_active(self, user_id: int, active: bool) -> None:
        cursor = self.connection.cursor()
        self._execute(cursor, "UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))
        self.connection.commit()

    def change_password(self, user_id: int, new_password: str) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id),
        )
        self.connection.commit()

    def verify_password(self, user_id: int, password: str) -> bool:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            "SELECT 1 FROM users WHERE id = ? AND password_hash = ?",
            (user_id, hash_password(password)),
        )
        return cursor.fetchone() is not None

    # -- Products -----------------------------------------------------------

    def get_active_products(self):
        cursor = self.connection.cursor()
        self._execute(cursor, "SELECT * FROM products WHERE active = 1 ORDER BY name")
        return cursor.fetchall()

    def get_all_products(self):
        cursor = self.connection.cursor()
        self._execute(cursor, "SELECT * FROM products ORDER BY name")
        return cursor.fetchall()

    def update_product(self, product_id: int, name: str, price_lbp: float, price_usd: float, stock_qty: int) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            UPDATE products
            SET name = ?, price_lbp = ?, price_usd = ?, stock_qty = ?
            WHERE id = ?
            """,
            (name.strip(), price_lbp, price_usd, stock_qty, product_id),
        )
        self.connection.commit()

    def add_product(self, name: str, price_lbp: float, price_usd: float, stock_qty: int) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            INSERT INTO products (name, price_lbp, price_usd, stock_qty, active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (name.strip(), price_lbp, price_usd, stock_qty),
        )
        self.connection.commit()

    def delete_product(self, product_id: int) -> None:
        cursor = self.connection.cursor()
        self._execute(cursor, "DELETE FROM products WHERE id = ?", (product_id,))
        self.connection.commit()

    # -- Settings -------------------------------------------------------------

    def get_exchange_rate(self) -> float:
        cursor = self.connection.cursor()
        self._execute(cursor, "SELECT value FROM settings WHERE key = 'exchange_rate'")
        row = cursor.fetchone()
        return float(row["value"]) if row else DEFAULT_RATE

    def set_exchange_rate(self, rate: float) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            INSERT INTO settings (key, value) VALUES ('exchange_rate', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(rate),),
        )
        self.connection.commit()

    def get_low_stock_threshold(self) -> int:
        cursor = self.connection.cursor()
        self._execute(cursor, "SELECT value FROM settings WHERE key = 'low_stock_threshold'")
        row = cursor.fetchone()
        return int(float(row["value"])) if row else DEFAULT_LOW_STOCK_THRESHOLD

    def set_low_stock_threshold(self, threshold: int) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            INSERT INTO settings (key, value) VALUES ('low_stock_threshold', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(threshold),),
        )
        self.connection.commit()

    # -- Cash sessions --------------------------------------------------------

    def get_open_session(self, user_id: int):
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            SELECT * FROM cash_sessions
            WHERE user_id = ? AND status = 'open'
            ORDER BY opened_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        return cursor.fetchone()

    def get_latest_session(self, user_id: int):
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            SELECT * FROM cash_sessions
            WHERE user_id = ?
            ORDER BY opened_at DESC
            LIMIT 1
            """,
            (user_id,),
        )
        return cursor.fetchone()

    def open_session(self, user_id: int, opening_cash_lbp: float, opening_cash_usd: float) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            INSERT INTO cash_sessions (
                user_id, opened_at, opening_cash_lbp, opening_cash_usd, status
            )
            VALUES (?, ?, ?, ?, 'open')
            """,
            (user_id, datetime.now().isoformat(timespec="seconds"), opening_cash_lbp, opening_cash_usd),
        )
        self.connection.commit()

    def update_session_opening(self, session_id: int, opening_cash_lbp: float, opening_cash_usd: float) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            UPDATE cash_sessions
            SET opening_cash_lbp = ?, opening_cash_usd = ?
            WHERE id = ?
            """,
            (opening_cash_lbp, opening_cash_usd, session_id),
        )
        self.connection.commit()

    def close_session(self, session_id: int, closing_cash_lbp: float, closing_cash_usd: float) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            UPDATE cash_sessions
            SET closed_at = ?, closing_cash_lbp = ?, closing_cash_usd = ?, status = 'closed'
            WHERE id = ?
            """,
            (datetime.now().isoformat(timespec="seconds"), closing_cash_lbp, closing_cash_usd, session_id),
        )
        self.connection.commit()

    def update_session_closing(self, session_id: int, closing_cash_lbp: float, closing_cash_usd: float) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            UPDATE cash_sessions
            SET closing_cash_lbp = ?, closing_cash_usd = ?
            WHERE id = ?
            """,
            (closing_cash_lbp, closing_cash_usd, session_id),
        )
        self.connection.commit()

    # -- Sales ------------------------------------------------------------------

    def create_sale(self, session_id: int, user_id: int, customer_no: int, items: list) -> None:
        cursor = self.connection.cursor()
        total_lbp = sum(item.total_lbp for item in items)
        total_usd = sum(item.total_usd for item in items)
        sold_at = datetime.now().isoformat(timespec="seconds")

        self._execute(
            cursor,
            """
            INSERT INTO sales (session_id, user_id, customer_no, sold_at, total_lbp, total_usd)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, customer_no, sold_at, total_lbp, total_usd),
        )
        sale_id = cursor.lastrowid

        for item in items:
            self._execute(
                cursor,
                """
                INSERT INTO sale_items (
                    sale_id, product_id, product_name, qty, unit_price_lbp,
                    unit_price_usd, line_total_lbp, line_total_usd
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    item.product_id,
                    item.name,
                    item.qty,
                    item.price_lbp,
                    item.price_usd,
                    item.total_lbp,
                    item.total_usd,
                ),
            )
            self._execute(
                cursor,
                "UPDATE products SET stock_qty = stock_qty - ? WHERE id = ?",
                (item.qty, item.product_id),
            )

        self.connection.commit()

    def get_daily_report(self, date_value: str):
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            SELECT
                COUNT(*) AS sale_count,
                COALESCE(SUM(sales.total_lbp), 0) AS total_lbp,
                COALESCE(SUM(sales.total_usd), 0) AS total_usd,
                COALESCE(
                    (
                        SELECT SUM(sale_items.qty)
                        FROM sale_items
                        INNER JOIN sales AS s2 ON s2.id = sale_items.sale_id
                        WHERE DATE(s2.sold_at) = ?
                    ),
                    0
                ) AS items_sold
            FROM sales
            WHERE DATE(sales.sold_at) = ?
            """,
            (date_value, date_value),
        )
        sales_summary = cursor.fetchone()

        self._execute(
            cursor,
            """
            SELECT
                COALESCE(SUM(opening_cash_lbp), 0) AS opening_lbp,
                COALESCE(SUM(opening_cash_usd), 0) AS opening_usd,
                COALESCE(SUM(closing_cash_lbp), 0) AS closing_lbp,
                COALESCE(SUM(closing_cash_usd), 0) AS closing_usd
            FROM cash_sessions
            WHERE DATE(opened_at) = ?
            """,
            (date_value,),
        )
        cash_summary = cursor.fetchone()

        self._execute(
            cursor,
            """
            SELECT
                sales.id,
                sales.customer_no,
                sales.sold_at,
                users.username,
                sales.total_lbp,
                sales.total_usd,
                COALESCE(SUM(sale_items.qty), 0) AS items_count,
                GROUP_CONCAT(sale_items.product_name || ' x' || CAST(sale_items.qty AS TEXT), ', ') AS items_text
            FROM sales
            LEFT JOIN sale_items ON sale_items.sale_id = sales.id
            LEFT JOIN users ON users.id = sales.user_id
            WHERE DATE(sales.sold_at) = ?
            GROUP BY sales.id, sales.customer_no, sales.sold_at, users.username, sales.total_lbp, sales.total_usd
            ORDER BY sales.sold_at DESC
            """,
            (date_value,),
        )
        order_rows = cursor.fetchall()
        return sales_summary, cash_summary, order_rows

    def delete_sale(self, sale_id: int) -> None:
        cursor = self.connection.cursor()
        self._execute(
            cursor,
            """
            SELECT product_id, qty
            FROM sale_items
            WHERE sale_id = ?
            """,
            (sale_id,),
        )
        sale_items = cursor.fetchall()

        for item in sale_items:
            self._execute(
                cursor,
                "UPDATE products SET stock_qty = stock_qty + ? WHERE id = ?",
                (item["qty"], item["product_id"]),
            )

        self._execute(cursor, "DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
        self._execute(cursor, "DELETE FROM sales WHERE id = ?", (sale_id,))
        self.connection.commit()
