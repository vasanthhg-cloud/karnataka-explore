# -*- coding: utf-8 -*-
"""Authentication decorators, input validation and id generation."""
import random
import re
import string
from functools import wraps

from flask import flash, redirect, request, session, url_for

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            flash("Admin sign-in required.", "warning")
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def valid_email(value):
    return bool(value and EMAIL_RE.match(value.strip()))


def valid_mobile(value):
    return bool(value and MOBILE_RE.match(re.sub(r"\D", "", value)[-10:]))


def password_problem(password):
    """Return an error message, or None when the password is acceptable."""
    if not password or len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain both letters and numbers."
    return None


def new_booking_ref():
    return "KX-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def new_txn_id():
    return "DEMO" + "".join(random.choices(string.digits, k=10))


def money(value):
    return "₹{:,.0f}".format(value or 0)
