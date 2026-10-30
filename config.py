# -*- coding: utf-8 -*-
"""Application configuration. Secrets come from the environment (.env)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # --- security -------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me-in-production")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024          # 8 MB uploads

    # --- database -------------------------------------------------------
    # SQLite by default so the project runs with zero setup.
    # Set DB_BACKEND=mysql plus the DB_* variables to run on MySQL
    # (see schema/mysql_schema.sql and README).
    DB_BACKEND = os.environ.get("DB_BACKEND", "sqlite")
    SQLITE_PATH = os.environ.get("SQLITE_PATH", str(BASE_DIR / "instance" / "karnataka_explore.db"))
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "3306"))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "karnataka_explore")

    # --- uploads --------------------------------------------------------
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "static" / "uploads"))
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

    # --- maps -----------------------------------------------------------
    # OpenStreetMap tiles through Leaflet need no API key. If you prefer
    # Google Maps, put a key here and swap the map partial.
    MAP_TILE_URL = os.environ.get("MAP_TILE_URL", "https://tile.openstreetmap.org/{z}/{x}/{y}.png")
    MAP_ATTRIBUTION = os.environ.get("MAP_ATTRIBUTION", "&copy; OpenStreetMap contributors")

    # --- site -----------------------------------------------------------
    SITE_NAME = os.environ.get("SITE_NAME", "Karnataka Explore")
    SITE_TAGLINE = "Discover Karnataka"
    CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "hello@karnatakaexplore.in")
    CONTACT_PHONE = os.environ.get("CONTACT_PHONE", "+91 80 2222 3344")
    DEFAULT_ADMIN_EMAIL = os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@karnatakaexplore.in")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin@123")
    DEFAULT_DEMO_USER_EMAIL = os.environ.get("DEFAULT_DEMO_USER_EMAIL", "demo@karnatakaexplore.in")
    DEFAULT_DEMO_USER_PASSWORD = os.environ.get("DEFAULT_DEMO_USER_PASSWORD", "Demo@1234")
    LANGUAGES = {"en": "English", "hi": "हिन्दी", "kn": "ಕನ್ನಡ"}
