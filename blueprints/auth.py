# -*- coding: utf-8 -*-
"""User registration, login, profile and password help."""
from flask import (Blueprint, flash, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from db import execute, query
from security import login_required, password_problem, valid_email, valid_mobile

bp = Blueprint("auth", __name__)

DISTRICT_CHOICES = None  # filled lazily from the database


def _districts():
    return query("SELECT name FROM districts ORDER BY name")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("public.index"))
    form = request.form
    if request.method == "POST":
        full_name = form.get("full_name", "").strip()
        email = form.get("email", "").strip().lower()
        mobile = form.get("mobile", "").strip()
        password = form.get("password", "")
        confirm = form.get("confirm_password", "")
        district = form.get("district", "").strip()
        gender = form.get("gender", "").strip()

        errors = []
        if len(full_name) < 3:
            errors.append("Please enter your full name.")
        if not valid_email(email):
            errors.append("That email address does not look right.")
        if not valid_mobile(mobile):
            errors.append("Enter a valid 10-digit Indian mobile number.")
        problem = password_problem(password)
        if problem:
            errors.append(problem)
        if password != confirm:
            errors.append("The two passwords do not match.")
        if not district:
            errors.append("Please choose your district.")
        if not errors:
            if query("SELECT 1 FROM users WHERE email = ?", (email,), one=True):
                errors.append("An account with this email already exists. Try signing in.")
            elif query("SELECT 1 FROM users WHERE mobile = ?", (mobile[-10:],), one=True):
                errors.append("This mobile number is already registered.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/register.html", districts=_districts(), form=form)

        uid = execute("""INSERT INTO users (full_name, email, mobile, password_hash, district, gender)
                         VALUES (?,?,?,?,?,?)""",
                      (full_name, email, mobile[-10:], generate_password_hash(password),
                       district, gender))
        session.clear()
        session["user_id"] = uid
        session["user_name"] = full_name
        flash("Welcome to Karnataka Explore, %s." % full_name.split()[0], "success")
        return redirect(url_for("public.index"))

    return render_template("auth/register.html", districts=_districts(), form={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("public.index"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember")
        user = query("SELECT * FROM users WHERE email = ? OR mobile = ?",
                     (identity.lower(), identity[-10:]), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session.permanent = bool(remember)
            flash("Signed in as %s." % user["full_name"], "success")
            nxt = request.args.get("next")
            return redirect(nxt if nxt and nxt.startswith("/") else url_for("public.index"))
        flash("Those details did not match an account.", "error")
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("user_name", None)
    flash("You have signed out.", "success")
    return redirect(url_for("public.index"))


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user:
            flash("Account found. In a real deployment a reset link would be emailed. "
                  "For this demo you can set a new password below.", "success")
            return redirect(url_for("auth.reset_password", email=email))
        flash("No account uses that email address.", "error")
    return render_template("auth/forgot.html")


@bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email", "").strip().lower()
    user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
    if not user:
        return redirect(url_for("auth.forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        problem = password_problem(password)
        if problem:
            flash(problem, "error")
        elif password != request.form.get("confirm_password", ""):
            flash("The two passwords do not match.", "error")
        else:
            execute("UPDATE users SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(password), user["id"]))
            flash("Password updated. Please sign in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/reset.html", email=email)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = query("SELECT * FROM users WHERE id = ?", (session["user_id"],), one=True)
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        district = request.form.get("district", "").strip()
        gender = request.form.get("gender", "").strip()
        if len(full_name) < 3 or not valid_mobile(mobile):
            flash("Please check your name and mobile number.", "error")
        else:
            execute("UPDATE users SET full_name = ?, mobile = ?, district = ?, gender = ? WHERE id = ?",
                    (full_name, mobile[-10:], district, gender, user["id"]))
            session["user_name"] = full_name
            flash("Profile updated.", "success")
            return redirect(url_for("auth.profile"))
    bookings_count = query("SELECT COUNT(*) AS c FROM bookings WHERE user_id = ?",
                           (user["id"],), one=True)["c"]
    return render_template("auth/profile.html", user=user, districts=_districts(),
                           bookings_count=bookings_count)
