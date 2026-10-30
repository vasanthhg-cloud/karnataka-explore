# -*- coding: utf-8 -*-
"""Database layer.

SQLite is used by default so the project runs with no setup. The same SQL
statements run on MySQL when DB_BACKEND=mysql is set (see schema/mysql_schema.sql
for the MySQL DDL). All queries use parameter binding - no string building.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app, g

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS districts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    region      TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    mobile        TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    district      TEXT,
    gender        TEXT,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'admin',
    last_login    TEXT,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS destinations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    slug           TEXT NOT NULL UNIQUE,
    district_id    INTEGER NOT NULL REFERENCES districts(id) ON DELETE CASCADE,
    category       TEXT NOT NULL,
    description    TEXT NOT NULL,
    description_hi TEXT,
    description_kn TEXT,
    location       TEXT,
    latitude       REAL,
    longitude      REAL,
    best_time      TEXT,
    entry_fee      TEXT,
    timings        TEXT,
    activities     TEXT,
    nearby         TEXT,
    travel_info    TEXT,
    duration       TEXT,
    ticket_price   REAL NOT NULL DEFAULT 0,
    featured       INTEGER NOT NULL DEFAULT 0,
    active         INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS destination_images (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    destination_id INTEGER NOT NULL REFERENCES destinations(id) ON DELETE CASCADE,
    image_url      TEXT NOT NULL,
    caption        TEXT,
    sort_order     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS homestays (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    slug          TEXT NOT NULL UNIQUE,
    district_id   INTEGER NOT NULL REFERENCES districts(id) ON DELETE CASCADE,
    description   TEXT NOT NULL,
    address       TEXT,
    latitude      REAL,
    longitude     REAL,
    price_per_night REAL NOT NULL DEFAULT 0,
    rooms_available INTEGER NOT NULL DEFAULT 1,
    max_guests    INTEGER NOT NULL DEFAULT 2,
    checkin_time  TEXT DEFAULT '12:00 PM',
    checkout_time TEXT DEFAULT '11:00 AM',
    facilities    TEXT,
    contact_name  TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    rating        REAL DEFAULT 0,
    active        INTEGER NOT NULL DEFAULT 1,
    is_sample     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS homestay_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    homestay_id INTEGER NOT NULL REFERENCES homestays(id) ON DELETE CASCADE,
    image_url   TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rooms (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    homestay_id INTEGER NOT NULL REFERENCES homestays(id) ON DELETE CASCADE,
    room_type   TEXT NOT NULL,
    price       REAL NOT NULL,
    capacity    INTEGER NOT NULL DEFAULT 2,
    total_rooms INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bookings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_ref    TEXT NOT NULL UNIQUE,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind           TEXT NOT NULL,
    destination_id INTEGER REFERENCES destinations(id) ON DELETE SET NULL,
    homestay_id    INTEGER REFERENCES homestays(id) ON DELETE SET NULL,
    guide_id       INTEGER REFERENCES tour_guides(id) ON DELETE SET NULL,
    visit_date     TEXT,
    checkin_date   TEXT,
    checkout_date  TEXT,
    nights         INTEGER DEFAULT 0,
    visitors       INTEGER NOT NULL DEFAULT 1,
    rooms          INTEGER DEFAULT 1,
    unit_price     REAL NOT NULL DEFAULT 0,
    subtotal       REAL NOT NULL DEFAULT 0,
    tax            REAL NOT NULL DEFAULT 0,
    total          REAL NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'Pending',
    payment_status TEXT NOT NULL DEFAULT 'Unpaid',
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking_tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id  INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    ticket_no   TEXT NOT NULL,
    issued_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    download_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    method     TEXT NOT NULL,
    txn_id     TEXT NOT NULL,
    amount     REAL NOT NULL,
    status     TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tour_guides (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    district_id   INTEGER REFERENCES districts(id) ON DELETE SET NULL,
    languages     TEXT,
    experience    INTEGER DEFAULT 0,
    fee_per_day   REAL NOT NULL DEFAULT 0,
    phone         TEXT,
    email         TEXT,
    bio           TEXT,
    photo_url     TEXT,
    rating        REAL DEFAULT 0,
    active        INTEGER NOT NULL DEFAULT 1,
    is_sample     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS guide_bookings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    guide_id   INTEGER NOT NULL REFERENCES tour_guides(id) ON DELETE CASCADE,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    days       INTEGER NOT NULL DEFAULT 1,
    start_date TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    destination_id INTEGER REFERENCES destinations(id) ON DELETE CASCADE,
    homestay_id    INTEGER REFERENCES homestays(id) ON DELETE CASCADE,
    rating         INTEGER NOT NULL,
    comment        TEXT,
    status         TEXT NOT NULL DEFAULT 'Pending',
    created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wishlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL,
    item_id    INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, kind, item_id)
);

CREATE TABLE IF NOT EXISTS languages (
    code   TEXT PRIMARY KEY,
    name   TEXT NOT NULL,
    native TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    phone      TEXT,
    subject    TEXT,
    message    TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'New',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS newsletter (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    email      TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS site_content (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_dest_district ON destinations(district_id);
CREATE INDEX IF NOT EXISTS idx_dest_category ON destinations(category);
CREATE INDEX IF NOT EXISTS idx_book_user ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_book_ref ON bookings(booking_ref);
"""


def get_db():
    """One connection per request."""
    if "db" not in g:
        if current_app.config["DB_BACKEND"] == "mysql":
            g.db = _mysql_connect(current_app.config)
        else:
            path = current_app.config["SQLITE_PATH"]
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            g.db = sqlite3.connect(path)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def _mysql_connect(cfg):
    import mysql.connector  # optional dependency
    conn = mysql.connector.connect(
        host=cfg["DB_HOST"], port=cfg["DB_PORT"], user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"], database=cfg["DB_NAME"],
        autocommit=False,
    )
    return conn


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@contextmanager
def cursor():
    db = get_db()
    cur = db.cursor()
    try:
        yield cur
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()


def query(sql, args=(), one=False):
    cur = get_db().cursor()
    cur.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    if rows and isinstance(rows[0], sqlite3.Row):
        rows = [dict(r) for r in rows]
    else:
        cols = [c[0] for c in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in rows]
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    with cursor() as cur:
        cur.execute(sql, args)
        return cur.lastrowid


def init_schema():
    db = get_db()
    if current_app.config["DB_BACKEND"] == "mysql":
        return
    db.executescript(SCHEMA_SQLITE)
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
