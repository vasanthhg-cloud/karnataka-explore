# -*- coding: utf-8 -*-
"""Admin area: separate login, dashboard, CRUD for every content type."""
import os
import uuid

from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import services
from data import CATEGORIES
from db import execute, query
from security import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _allowed(filename):
    return ("." in filename and
            filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"])


def _save_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if not _allowed(file_storage.filename):
        return None
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    name = uuid.uuid4().hex + "." + ext
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], name)
    file_storage.save(path)
    return "/static/uploads/" + name


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_id"):
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        row = query("SELECT * FROM admins WHERE email = ?", (email,), one=True)
        if row and check_password_hash(row["password_hash"], password):
            session["admin_id"] = row["id"]
            session["admin_name"] = row["full_name"]
            execute("UPDATE admins SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
            return redirect(url_for("admin.dashboard"))
        flash("Invalid administrator credentials.", "error")
    return render_template("admin/login.html")


@bp.route("/logout")
def logout():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    return redirect(url_for("admin.login"))


@bp.route("/")
@admin_required
def dashboard():
    stats = {
        "users": query("SELECT COUNT(*) AS c FROM users", one=True)["c"],
        "destinations": query("SELECT COUNT(*) AS c FROM destinations", one=True)["c"],
        "homestays": query("SELECT COUNT(*) AS c FROM homestays", one=True)["c"],
        "bookings": query("SELECT COUNT(*) AS c FROM bookings", one=True)["c"],
        "revenue": query("SELECT COALESCE(SUM(total),0) AS s FROM bookings WHERE payment_status = 'Paid'", one=True)["s"],
        "pending_reviews": query("SELECT COUNT(*) AS c FROM reviews WHERE status = 'Pending'", one=True)["c"],
        "messages": query("SELECT COUNT(*) AS c FROM contact_messages WHERE status = 'New'", one=True)["c"],
        "guides": query("SELECT COUNT(*) AS c FROM tour_guides", one=True)["c"],
    }
    recent = query("""SELECT b.*, u.full_name,
                             COALESCE(d.name, h.name, g.name) AS item_name
                      FROM bookings b JOIN users u ON u.id = b.user_id
                      LEFT JOIN destinations d ON d.id = b.destination_id
                      LEFT JOIN homestays h ON h.id = b.homestay_id
                      LEFT JOIN tour_guides g ON g.id = b.guide_id
                      ORDER BY b.id DESC LIMIT 8""")
    by_category = query("""SELECT category, COUNT(*) AS c FROM destinations
                           GROUP BY category ORDER BY c DESC""")
    by_district = query("""SELECT dist.name, COUNT(d.id) AS c FROM districts dist
                           LEFT JOIN destinations d ON d.district_id = dist.id
                           GROUP BY dist.id ORDER BY c DESC LIMIT 8""")
    monthly = query("""SELECT substr(created_at,1,7) AS month, COUNT(*) AS c,
                              COALESCE(SUM(CASE WHEN payment_status='Paid' THEN total ELSE 0 END),0) AS revenue
                       FROM bookings GROUP BY month ORDER BY month DESC LIMIT 6""")
    return render_template("admin/dashboard.html", stats=stats, recent=recent,
                           by_category=by_category, by_district=by_district,
                           monthly=list(reversed(monthly)))


# --------------------------------------------------------------------------
# destinations
# --------------------------------------------------------------------------
@bp.route("/destinations")
@admin_required
def destinations():
    q = request.args.get("q", "").strip()
    rows, info = services.destinations(q=q or None, per_page=20,
                                       page=int(request.args.get("page", 1) or 1))
    return render_template("admin/destinations.html", destinations=rows, info=info, q=q)


@bp.route("/destinations/new", methods=["GET", "POST"])
@admin_required
def destination_new():
    if request.method == "POST":
        did = _save_destination()
        if did:
            flash("Destination added.", "success")
            return redirect(url_for("admin.destination_edit", dest_id=did))
    return render_template("admin/destination_form.html", d=None, categories=CATEGORIES,
                           districts=services.districts_with_counts())


@bp.route("/destinations/<int:dest_id>/edit", methods=["GET", "POST"])
@admin_required
def destination_edit(dest_id):
    d = query("SELECT * FROM destinations WHERE id = ?", (dest_id,), one=True)
    if not d:
        abort(404)
    if request.method == "POST":
        _save_destination(dest_id)
        flash("Destination updated.", "success")
        return redirect(url_for("admin.destination_edit", dest_id=dest_id))
    images = query("SELECT * FROM destination_images WHERE destination_id = ? ORDER BY sort_order",
                   (dest_id,))
    return render_template("admin/destination_form.html", d=d, categories=CATEGORIES,
                           districts=services.districts_with_counts(), images=images)


def _save_destination(dest_id=None):
    f = request.form
    name = f.get("name", "").strip()
    if not name:
        flash("A destination needs a name.", "error")
        return None
    slug = f.get("slug", "").strip() or __import__("re").sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    values = (name, slug, f.get("district_id", type=int), f.get("category", ""),
              f.get("description", "").strip(), f.get("location", "").strip(),
              f.get("latitude", type=float), f.get("longitude", type=float),
              f.get("best_time", "").strip(), f.get("entry_fee", "").strip(),
              f.get("timings", "").strip(), f.get("activities", "").strip(),
              f.get("nearby", "").strip(), f.get("travel_info", "").strip(),
              f.get("duration", "").strip(), f.get("ticket_price", type=float) or 0,
              1 if f.get("featured") else 0, 1 if f.get("active") else 0)
    if dest_id:
        execute("""UPDATE destinations SET name=?, slug=?, district_id=?, category=?, description=?,
                   location=?, latitude=?, longitude=?, best_time=?, entry_fee=?, timings=?,
                   activities=?, nearby=?, travel_info=?, duration=?, ticket_price=?,
                   featured=?, active=? WHERE id=?""", values + (dest_id,))
        new_id = dest_id
    else:
        new_id = execute("""INSERT INTO destinations
                   (name, slug, district_id, category, description, location, latitude, longitude,
                    best_time, entry_fee, timings, activities, nearby, travel_info, duration,
                    ticket_price, featured, active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)
    upload = _save_upload(request.files.get("photo"))
    if upload:
        count = query("SELECT COUNT(*) AS c FROM destination_images WHERE destination_id = ?",
                      (new_id,), one=True)["c"]
        execute("INSERT INTO destination_images (destination_id, image_url, sort_order) VALUES (?,?,?)",
                (new_id, upload, count))
    return new_id


@bp.route("/destinations/<int:dest_id>/delete", methods=["POST"])
@admin_required
def destination_delete(dest_id):
    execute("DELETE FROM destinations WHERE id = ?", (dest_id,))
    flash("Destination deleted.", "success")
    return redirect(url_for("admin.destinations"))


@bp.route("/images/<int:image_id>/delete", methods=["POST"])
@admin_required
def image_delete(image_id):
    row = query("SELECT * FROM destination_images WHERE id = ?", (image_id,), one=True)
    if row:
        execute("DELETE FROM destination_images WHERE id = ?", (image_id,))
        back = request.form.get("back")
        return redirect(back or url_for("admin.destinations"))
    abort(404)


# --------------------------------------------------------------------------
# homestays
# --------------------------------------------------------------------------
@bp.route("/homestays")
@admin_required
def homestays():
    rows, info = services.homestays(q=request.args.get("q") or None, per_page=20,
                                    page=int(request.args.get("page", 1) or 1))
    return render_template("admin/homestays.html", stays=rows, info=info,
                           q=request.args.get("q", ""))


@bp.route("/homestays/new", methods=["GET", "POST"])
@admin_required
def homestay_new():
    if request.method == "POST":
        hid = _save_homestay()
        if hid:
            flash("Homestay added.", "success")
            return redirect(url_for("admin.homestay_edit", stay_id=hid))
    return render_template("admin/homestay_form.html", h=None,
                           districts=services.districts_with_counts())


@bp.route("/homestays/<int:stay_id>/edit", methods=["GET", "POST"])
@admin_required
def homestay_edit(stay_id):
    h = query("SELECT * FROM homestays WHERE id = ?", (stay_id,), one=True)
    if not h:
        abort(404)
    if request.method == "POST":
        _save_homestay(stay_id)
        flash("Homestay updated.", "success")
        return redirect(url_for("admin.homestay_edit", stay_id=stay_id))
    images = query("SELECT * FROM homestay_images WHERE homestay_id = ? ORDER BY sort_order", (stay_id,))
    return render_template("admin/homestay_form.html", h=h, images=images,
                           districts=services.districts_with_counts())


def _save_homestay(stay_id=None):
    f = request.form
    name = f.get("name", "").strip()
    if not name:
        flash("A homestay needs a name.", "error")
        return None
    slug = f.get("slug", "").strip() or __import__("re").sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    values = (name, slug, f.get("district_id", type=int), f.get("description", "").strip(),
              f.get("address", "").strip(), f.get("latitude", type=float),
              f.get("longitude", type=float), f.get("price_per_night", type=float) or 0,
              f.get("rooms_available", type=int) or 1, f.get("max_guests", type=int) or 2,
              f.get("checkin_time", "12:00 PM"), f.get("checkout_time", "11:00 AM"),
              f.get("facilities", "").strip(), f.get("contact_name", "").strip(),
              f.get("contact_phone", "").strip(), f.get("contact_email", "").strip(),
              1 if f.get("active") else 0)
    if stay_id:
        execute("""UPDATE homestays SET name=?, slug=?, district_id=?, description=?, address=?,
                   latitude=?, longitude=?, price_per_night=?, rooms_available=?, max_guests=?,
                   checkin_time=?, checkout_time=?, facilities=?, contact_name=?, contact_phone=?,
                   contact_email=?, active=? WHERE id=?""", values + (stay_id,))
        new_id = stay_id
    else:
        new_id = execute("""INSERT INTO homestays
                   (name, slug, district_id, description, address, latitude, longitude,
                    price_per_night, rooms_available, max_guests, checkin_time, checkout_time,
                    facilities, contact_name, contact_phone, contact_email, active, is_sample)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)""", values)
    upload = _save_upload(request.files.get("photo"))
    if upload:
        count = query("SELECT COUNT(*) AS c FROM homestay_images WHERE homestay_id = ?",
                      (new_id,), one=True)["c"]
        execute("INSERT INTO homestay_images (homestay_id, image_url, sort_order) VALUES (?,?,?)",
                (new_id, upload, count))
    return new_id


@bp.route("/homestays/<int:stay_id>/delete", methods=["POST"])
@admin_required
def homestay_delete(stay_id):
    execute("DELETE FROM homestays WHERE id = ?", (stay_id,))
    flash("Homestay deleted.", "success")
    return redirect(url_for("admin.homestays"))


# --------------------------------------------------------------------------
# bookings / payments / users
# --------------------------------------------------------------------------
@bp.route("/bookings")
@admin_required
def bookings():
    q = request.args.get("q", "").strip()
    status = request.args.get("status") or None
    sql = """SELECT b.*, u.full_name, u.email,
                    COALESCE(d.name, h.name, g.name) AS item_name,
                    p.txn_id
             FROM bookings b JOIN users u ON u.id = b.user_id
             LEFT JOIN destinations d ON d.id = b.destination_id
             LEFT JOIN homestays h ON h.id = b.homestay_id
             LEFT JOIN tour_guides g ON g.id = b.guide_id
             LEFT JOIN payments p ON p.booking_id = b.id
             WHERE 1=1"""
    args = []
    if q:
        sql += " AND (b.booking_ref LIKE ? OR u.full_name LIKE ? OR u.email LIKE ?)"
        args += ["%" + q + "%"] * 3
    if status:
        sql += " AND b.status = ?"
        args.append(status)
    sql += " GROUP BY b.id ORDER BY b.id DESC LIMIT 200"
    return render_template("admin/bookings.html", bookings=query(sql, args), q=q, status=status)


@bp.route("/bookings/<int:booking_id>/status", methods=["POST"])
@admin_required
def booking_status(booking_id):
    status = request.form.get("status", "Pending")
    if status not in ("Pending", "Confirmed", "Cancelled", "Completed"):
        abort(400)
    execute("UPDATE bookings SET status = ? WHERE id = ?", (status, booking_id))
    flash("Booking status updated.", "success")
    return redirect(request.referrer or url_for("admin.bookings"))


@bp.route("/payments")
@admin_required
def payments():
    rows = query("""SELECT p.*, b.booking_ref, u.full_name FROM payments p
                    JOIN bookings b ON b.id = p.booking_id
                    JOIN users u ON u.id = b.user_id
                    ORDER BY p.id DESC LIMIT 200""")
    return render_template("admin/payments.html", payments=rows)


@bp.route("/users")
@admin_required
def users():
    rows = query("""SELECT u.*, (SELECT COUNT(*) FROM bookings b WHERE b.user_id = u.id) AS bookings
                    FROM users u ORDER BY u.id DESC""")
    return render_template("admin/users.html", users=rows)


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id):
    execute("DELETE FROM users WHERE id = ?", (user_id,))
    flash("User removed.", "success")
    return redirect(url_for("admin.users"))


# --------------------------------------------------------------------------
# guides
# --------------------------------------------------------------------------
@bp.route("/guides")
@admin_required
def guides():
    return render_template("admin/guides.html", guides=services.guides())


@bp.route("/guides/new", methods=["GET", "POST"])
@admin_required
def guide_new():
    if request.method == "POST":
        _save_guide()
        flash("Guide added.", "success")
        return redirect(url_for("admin.guides"))
    return render_template("admin/guide_form.html", g=None,
                           districts=services.districts_with_counts())


@bp.route("/guides/<int:guide_id>/edit", methods=["GET", "POST"])
@admin_required
def guide_edit(guide_id):
    g = query("SELECT * FROM tour_guides WHERE id = ?", (guide_id,), one=True)
    if not g:
        abort(404)
    if request.method == "POST":
        _save_guide(guide_id)
        flash("Guide updated.", "success")
        return redirect(url_for("admin.guides"))
    return render_template("admin/guide_form.html", g=g,
                           districts=services.districts_with_counts())


def _save_guide(guide_id=None):
    f = request.form
    values = (f.get("name", "").strip(), f.get("district_id", type=int),
              f.get("languages", "").strip(), f.get("experience", type=int) or 0,
              f.get("fee_per_day", type=float) or 0, f.get("phone", "").strip(),
              f.get("email", "").strip(), f.get("bio", "").strip(),
              1 if f.get("active") else 0)
    if guide_id:
        execute("""UPDATE tour_guides SET name=?, district_id=?, languages=?, experience=?,
                   fee_per_day=?, phone=?, email=?, bio=?, active=? WHERE id=?""",
                values + (guide_id,))
    else:
        execute("""INSERT INTO tour_guides (name, district_id, languages, experience,
                   fee_per_day, phone, email, bio, active, is_sample)
                   VALUES (?,?,?,?,?,?,?,?,?,0)""", values)


@bp.route("/guides/<int:guide_id>/delete", methods=["POST"])
@admin_required
def guide_delete(guide_id):
    execute("DELETE FROM tour_guides WHERE id = ?", (guide_id,))
    flash("Guide removed.", "success")
    return redirect(url_for("admin.guides"))


# --------------------------------------------------------------------------
# reviews, messages, content
# --------------------------------------------------------------------------
@bp.route("/reviews")
@admin_required
def reviews():
    rows = query("""SELECT r.*, u.full_name, d.name AS destination_name, h.name AS homestay_name
                    FROM reviews r JOIN users u ON u.id = r.user_id
                    LEFT JOIN destinations d ON d.id = r.destination_id
                    LEFT JOIN homestays h ON h.id = r.homestay_id
                    ORDER BY CASE r.status WHEN 'Pending' THEN 0 ELSE 1 END, r.id DESC""")
    return render_template("admin/reviews.html", reviews=rows)


@bp.route("/reviews/<int:review_id>/<action>", methods=["POST"])
@admin_required
def review_action(review_id, action):
    if action == "approve":
        execute("UPDATE reviews SET status = 'Approved' WHERE id = ?", (review_id,))
        flash("Review approved.", "success")
    elif action == "reject":
        execute("UPDATE reviews SET status = 'Rejected' WHERE id = ?", (review_id,))
        flash("Review rejected.", "success")
    elif action == "delete":
        execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        flash("Review deleted.", "success")
    else:
        abort(400)
    return redirect(url_for("admin.reviews"))


@bp.route("/messages")
@admin_required
def messages():
    rows = query("SELECT * FROM contact_messages ORDER BY id DESC")
    return render_template("admin/messages.html", messages=rows)


@bp.route("/messages/<int:msg_id>/read", methods=["POST"])
@admin_required
def message_read(msg_id):
    execute("UPDATE contact_messages SET status = 'Read' WHERE id = ?", (msg_id,))
    return redirect(url_for("admin.messages"))


@bp.route("/content", methods=["GET", "POST"])
@admin_required
def content():
    keys = ("travel_tips", "emergency", "home_notice")
    if request.method == "POST":
        for k in keys:
            if k in request.form:
                existing = query("SELECT 1 FROM site_content WHERE key = ?", (k,), one=True)
                if existing:
                    execute("UPDATE site_content SET value = ? WHERE key = ?",
                            (request.form.get(k, ""), k))
                else:
                    execute("INSERT INTO site_content (key, value) VALUES (?,?)",
                            (k, request.form.get(k, "")))
        flash("Website content updated.", "success")
        return redirect(url_for("admin.content"))
    values = {k: services.site_content(k) for k in keys}
    return render_template("admin/content.html", values=values)


@bp.route("/admins", methods=["GET", "POST"])
@admin_required
def admins():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("full_name", "").strip() or "Administrator"
        if len(password) < 8 or "@" not in email:
            flash("Enter a valid email and a password of at least 8 characters.", "error")
        elif query("SELECT 1 FROM admins WHERE email = ?", (email,), one=True):
            flash("That administrator already exists.", "error")
        else:
            execute("INSERT INTO admins (full_name, email, password_hash, role) VALUES (?,?,?,'admin')",
                    (name, email, generate_password_hash(password)))
            flash("Administrator added.", "success")
        return redirect(url_for("admin.admins"))
    return render_template("admin/admins.html",
                           admins=query("SELECT id, full_name, email, role, last_login FROM admins"))
