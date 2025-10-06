import sqlite3
from contextlib import contextmanager
from .config import settings

def db_conn():
    return sqlite3.connect(settings.DB_PATH, check_same_thread=False)

def init_db():
    conn = db_conn()
    c = conn.cursor()
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
    conn.commit()
    conn.close()