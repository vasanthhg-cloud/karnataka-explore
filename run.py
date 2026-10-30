# -*- coding: utf-8 -*-
"""Convenience launcher: creates the database if needed, then serves the app.

    python run.py            -> http://127.0.0.1:5000
"""
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
except ImportError:
    pass

from app import create_app  # noqa: E402
from db import query  # noqa: E402

app = create_app()

with app.app_context():
    try:
        count = query("SELECT COUNT(*) AS c FROM destinations", one=True)["c"]
    except Exception:
        count = 0
    if not count:
        print("Database is empty - seeding it now ...")
        import seed
        seed.main()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
