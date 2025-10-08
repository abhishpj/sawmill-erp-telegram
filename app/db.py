import sqlite3
from contextlib import contextmanager
from typing import Iterator
from .config import settings

USE_POSTGRES = bool(settings.DATABASE_URL)

if USE_POSTGRES:
    import psycopg2

    def _pg_conn():
        return psycopg2.connect(settings.DATABASE_URL)
else:
    def _sqlite_conn():
        return sqlite3.connect(settings.DB_PATH, check_same_thread=False)


@contextmanager
def db_conn() -> Iterator:
    if USE_POSTGRES:
        conn = _pg_conn()
    else:
        conn = _sqlite_conn()
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()


def init_db():
    with db_conn() as conn:
        c = conn.cursor()
        # core tables
        c.execute("""CREATE TABLE IF NOT EXISTS suppliers(
            supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE, phone TEXT, address TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS customers(
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE, phone TEXT, address TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS stock_in(
            batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER, qty_logs INTEGER, volume_cft REAL, date TEXT,
            FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS stock_out(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER, thickness_mm REAL, width_mm REAL, length_mm REAL,
            qty INTEGER, date TEXT,
            FOREIGN KEY(batch_id) REFERENCES stock_in(batch_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER, status TEXT, date TEXT,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, thickness_mm REAL, width_mm REAL, length_mm REAL,
            size_label TEXT, qty INTEGER,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS deliveries(
            delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, lorry_number TEXT, status TEXT, date TEXT,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS payments(
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, amount REAL, method TEXT, date TEXT,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )""")
        # idempotency table to record processed Telegram update_id's
        c.execute("""CREATE TABLE IF NOT EXISTS updates_processed(
            update_id INTEGER PRIMARY KEY,
            ts TEXT DEFAULT (datetime('now'))
        )""")
        conn.commit()


def upsert_supplier(name: str) -> int:
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO suppliers(name) VALUES(?)", (name,))
        c.execute("SELECT supplier_id FROM suppliers WHERE name=?", (name,))
        row = c.fetchone()
        sid = row[0] if row else None
        return sid


def upsert_customer(name: str) -> int:
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO customers(name) VALUES(?)", (name,))
        c.execute("SELECT customer_id FROM customers WHERE name=?", (name,))
        row = c.fetchone()
        cid = row[0] if row else None
        return cid


def insert_stockin(p: dict) -> int:
    sid = upsert_supplier(p.get("supplier_name", "Unknown"))
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO stock_in(supplier_id,qty_logs,volume_cft,date)
                     VALUES(?,?,?,?)""",
                  (sid, p.get("qty_logs"), p.get("volume_cft"), p.get("date_str")))
        return c.lastrowid


def insert_production(p: dict) -> int:
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO stock_out(batch_id,thickness_mm,width_mm,length_mm,qty,date)
                     VALUES(?,?,?,?,?,?)""",
                  (p.get("batch_id"), p.get("thickness_mm"), p.get("width_mm"),
                   p.get("length_mm"), p.get("qty"), p.get("date_str")))
        return c.lastrowid


def insert_order(p: dict) -> int:
    cid = upsert_customer(p.get("customer_name", "Unknown"))
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO orders(customer_id,status,date)
                     VALUES(?,?,?)""", (cid, "pending", p.get("date_str")))
        order_id = c.lastrowid
        c.execute("""INSERT INTO order_items(order_id,thickness_mm,width_mm,length_mm,size_label,qty)
                     VALUES(?,?,?,?,?,?)""",
                  (order_id, p.get("thickness_mm"), p.get("width_mm"),
                   p.get("length_mm"), p.get("size_label"), p.get("qty")))
        return order_id


def insert_delivery(p: dict) -> int:
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO deliveries(order_id,lorry_number,status,date)
                     VALUES(?,?,?,?)""",
                  (p.get("order_id"), p.get("lorry_number"), "dispatched", p.get("date_str")))
        return c.lastrowid


def insert_payment(p: dict) -> int:
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO payments(order_id,amount,method,date)
                     VALUES(?,?,?,?)""",
                  (p.get("order_id"), p.get("amount"), p.get("method"), p.get("date_str")))
        return c.lastrowid


# idempotency helpers
def is_update_processed(update_id: int) -> bool:
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM updates_processed WHERE update_id=?", (update_id,))
        return bool(c.fetchone())


def mark_update_processed(update_id: int):
    with db_conn() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO updates_processed(update_id) VALUES(?)", (update_id,))
