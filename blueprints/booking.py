# -*- coding: utf-8 -*-
"""Booking, demo payment, tickets, wishlist, reviews and the itinerary planner."""
import math
from datetime import date, datetime, timedelta

from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   send_file, session, url_for)

import services
from db import execute, query
from security import login_required, new_booking_ref, new_txn_id
from tickets import build_itinerary_pdf, build_ticket_pdf

bp = Blueprint("booking", __name__)

TAX_RATES = {"destination": 0.05, "homestay": 0.12, "guide": 0.18}
PAY_METHODS = {"upi": "UPI", "debit": "Debit Card", "credit": "Credit Card",
               "netbanking": "Net Banking"}


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _unique_ref():
    for _ in range(8):
        ref = new_booking_ref()
        if not query("SELECT 1 FROM bookings WHERE booking_ref = ?", (ref,), one=True):
            return ref
    raise RuntimeError("could not allocate a booking reference")


def _split_costs(kind, unit_price, quantity):
    subtotal = round(unit_price * quantity, 2)
    tax = round(subtotal * TAX_RATES.get(kind, 0.05), 2)
    return subtotal, tax, round(subtotal + tax, 2)


def _own_booking(booking_id):
    row = query("SELECT * FROM bookings WHERE id = ?", (booking_id,), one=True)
    if not row:
        abort(404)
    if row["user_id"] != session.get("user_id"):
        abort(403)
    return row


def _item_name(row):
    if row["kind"] == "destination":
        d = query("SELECT d.name, dist.name AS district FROM destinations d "
                  "JOIN districts dist ON dist.id = d.district_id WHERE d.id = ?",
                  (row["destination_id"],), one=True)
        return (d["name"], d["district"]) if d else ("Destination", "")
    if row["kind"] == "homestay":
        h = query("SELECT h.name, dist.name AS district FROM homestays h "
                  "JOIN districts dist ON dist.id = h.district_id WHERE h.id = ?",
                  (row["homestay_id"],), one=True)
        return (h["name"], h["district"]) if h else ("Homestay", "")
    g = query("SELECT g.name, dist.name AS district FROM tour_guides g "
              "LEFT JOIN districts dist ON dist.id = g.district_id WHERE g.id = ?",
              (row["guide_id"],), one=True)
    return (g["name"], g["district"] or "") if g else ("Tour guide", "")


def _booking_view(booking_id):
    row = query("""SELECT b.*, p.method, p.txn_id, p.status AS pay_status
                   FROM bookings b LEFT JOIN payments p ON p.booking_id = b.id
                   WHERE b.id = ? ORDER BY p.id DESC LIMIT 1""", (booking_id,), one=True)
    if not row:
        row = query("SELECT * FROM bookings WHERE id = ?", (booking_id,), one=True)
    name, district = _item_name(row)
    row["item_name"] = name
    row["district_name"] = district
    return row


# --------------------------------------------------------------------------
# booking creation
# --------------------------------------------------------------------------
@bp.route("/book/destination/<slug>", methods=["GET", "POST"])
@login_required
def book_destination(slug):
    row, images, _ = services.destination(slug)
    if not row:
        abort(404)
    if request.method == "POST":
        visit_date = request.form.get("visit_date", "")
        visitors = max(1, request.form.get("visitors", type=int) or 1)
        if not visit_date or visit_date < date.today().isoformat():
            flash("Please choose a visit date today or later.", "error")
            return render_template("book_destination.html", d=row, images=images,
                                   today=date.today().isoformat())
        subtotal, tax, total = _split_costs("destination", row["ticket_price"], visitors)
        bid = execute("""INSERT INTO bookings
              (booking_ref, user_id, kind, destination_id, visit_date, visitors,
               unit_price, subtotal, tax, total, status, payment_status)
              VALUES (?,?,'destination',?,?,?,?,?,?,?, 'Pending', 'Unpaid')""",
              (_unique_ref(), session["user_id"], row["id"], visit_date, visitors,
               row["ticket_price"], subtotal, tax, total))
        return redirect(url_for("booking.payment", booking_id=bid))
    return render_template("book_destination.html", d=row, images=images,
                           today=date.today().isoformat())


@bp.route("/book/homestay/<slug>", methods=["GET", "POST"])
@login_required
def book_homestay(slug):
    row, images, rooms, _ = services.homestay(slug)
    if not row:
        abort(404)
    today = date.today().isoformat()
    if request.method == "POST":
        checkin = request.form.get("checkin", "")
        checkout = request.form.get("checkout", "")
        guests = max(1, request.form.get("guests", type=int) or 1)
        rooms_count = max(1, request.form.get("rooms", type=int) or 1)
        try:
            d1 = datetime.strptime(checkin, "%Y-%m-%d").date()
            d2 = datetime.strptime(checkout, "%Y-%m-%d").date()
        except ValueError:
            flash("Please choose valid check-in and check-out dates.", "error")
            return render_template("book_homestay.html", h=row, images=images, today=today)
        nights = (d2 - d1).days
        if nights < 1:
            flash("Check-out must be at least one night after check-in.", "error")
            return render_template("book_homestay.html", h=row, images=images, today=today)
        if d1 < date.today():
            flash("Check-in cannot be in the past.", "error")
            return render_template("book_homestay.html", h=row, images=images, today=today)
        if guests > row["max_guests"] * rooms_count:
            flash("That many guests will not fit in %d room(s) here." % rooms_count, "error")
            return render_template("book_homestay.html", h=row, images=images, today=today)
        if rooms_count > row["rooms_available"]:
            flash("Only %d room(s) are available." % row["rooms_available"], "error")
            return render_template("book_homestay.html", h=row, images=images, today=today)
        subtotal, tax, total = _split_costs("homestay", row["price_per_night"] * rooms_count, nights)
        bid = execute("""INSERT INTO bookings
              (booking_ref, user_id, kind, homestay_id, checkin_date, checkout_date, nights,
               visitors, rooms, unit_price, subtotal, tax, total, status, payment_status)
              VALUES (?,?,'homestay',?,?,?,?,?,?,?,?,?,?, 'Pending', 'Unpaid')""",
              (_unique_ref(), session["user_id"], row["id"], checkin, checkout, nights,
               guests, rooms_count, row["price_per_night"] * rooms_count, subtotal, tax, total))
        return redirect(url_for("booking.payment", booking_id=bid))
    return render_template("book_homestay.html", h=row, images=images, today=today,
                           tomorrow=(date.today() + timedelta(days=1)).isoformat())


@bp.route("/book/guide/<int:guide_id>", methods=["GET", "POST"])
@login_required
def book_guide(guide_id):
    g = services.guide(guide_id)
    if not g or not g["active"]:
        abort(404)
    today = date.today().isoformat()
    if request.method == "POST":
        start = request.form.get("start_date", "")
        days = max(1, request.form.get("days", type=int) or 1)
        visitors = max(1, request.form.get("visitors", type=int) or 1)
        if not start or start < today:
            flash("Choose a date today or later.", "error")
            return render_template("book_guide.html", g=g, today=today)
        subtotal, tax, total = _split_costs("guide", g["fee_per_day"], days)
        ref = _unique_ref()
        bid = execute("""INSERT INTO bookings
              (booking_ref, user_id, kind, guide_id, visit_date, nights, visitors,
               unit_price, subtotal, tax, total, status, payment_status)
              VALUES (?,?,'guide',?,?,?,?,?,?,?,?, 'Pending', 'Unpaid')""",
              (ref, session["user_id"], g["id"], start, days, visitors,
               g["fee_per_day"], subtotal, tax, total))
        execute("INSERT INTO guide_bookings (guide_id, booking_id, days, start_date) VALUES (?,?,?,?)",
                (g["id"], bid, days, start))
        return redirect(url_for("booking.payment", booking_id=bid))
    return render_template("book_guide.html", g=g, today=today)


# --------------------------------------------------------------------------
# demo payment
# --------------------------------------------------------------------------
@bp.route("/payment/<int:booking_id>", methods=["GET", "POST"])
@login_required
def payment(booking_id):
    row = _own_booking(booking_id)
    view = _booking_view(booking_id)
    if request.method == "POST":
        method = request.form.get("method", "upi")
        outcome = request.form.get("outcome", "success")
        if row["payment_status"] == "Paid":
            flash("This booking is already paid.", "warning")
            return redirect(url_for("booking.ticket", booking_id=booking_id))
        status = "Success" if outcome == "success" else "Failed"
        txn = new_txn_id()
        execute("""INSERT INTO payments (booking_id, method, txn_id, amount, status)
                   VALUES (?,?,?,?,?)""",
                (booking_id, PAY_METHODS.get(method, "UPI"), txn, row["total"], status))
        if status == "Success":
            execute("UPDATE bookings SET payment_status = 'Paid', status = 'Confirmed' WHERE id = ?",
                    (booking_id,))
            ticket_no = "TKT-" + row["booking_ref"].split("-")[-1]
            execute("INSERT INTO booking_tickets (booking_id, ticket_no) VALUES (?,?)",
                    (booking_id, ticket_no))
            flash("Demo payment successful. Your ticket is ready.", "success")
            return redirect(url_for("booking.ticket", booking_id=booking_id))
        execute("UPDATE bookings SET payment_status = 'Failed' WHERE id = ?", (booking_id,))
        flash("The demo payment failed. You can try again - nothing was charged.", "error")
        return redirect(url_for("booking.payment", booking_id=booking_id))
    return render_template("payment.html", b=view, methods=PAY_METHODS)


# --------------------------------------------------------------------------
# tickets
# --------------------------------------------------------------------------
@bp.route("/qr.png")
def qr_png():
    """Local QR image so tickets never depend on an external service."""
    from flask import Response
    from tickets import _qr_image
    data = request.args.get("data", "")[:512]
    if not data:
        abort(400)
    buf = _qr_image(data)
    return Response(buf.getvalue(), mimetype="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})



@bp.route("/booking/<int:booking_id>")
@login_required
def ticket(booking_id):
    _own_booking(booking_id)
    view = _booking_view(booking_id)
    return render_template("ticket.html", b=view)


@bp.route("/booking/<int:booking_id>/ticket.pdf")
@login_required
def ticket_pdf(booking_id):
    _own_booking(booking_id)
    view = _booking_view(booking_id)
    user = query("SELECT * FROM users WHERE id = ?", (session["user_id"],), one=True)
    execute("UPDATE booking_tickets SET download_count = download_count + 1 WHERE booking_id = ?",
            (booking_id,))
    verify = request.url_root.rstrip("/") + url_for("booking.verify", ref=view["booking_ref"])
    pdf = build_ticket_pdf(view, user, view["item_name"], view["district_name"], verify)
    return send_file(__import__("io").BytesIO(pdf), mimetype="application/pdf",
                     as_attachment=True,
                     download_name="Karnataka-Explore-%s.pdf" % view["booking_ref"])


@bp.route("/verify/<ref>")
def verify(ref):
    row = query("""SELECT b.*, u.full_name FROM bookings b JOIN users u ON u.id = b.user_id
                   WHERE b.booking_ref = ?""", (ref,), one=True)
    if not row:
        return render_template("verify.html", booking=None, ref=ref)
    name, district = _item_name(row)
    return render_template("verify.html", booking=row, ref=ref, item_name=name,
                           district=district)


@bp.route("/my-bookings")
@login_required
def my_bookings():
    q = request.args.get("q", "").strip()
    status = request.args.get("status") or None
    sql = ("SELECT b.*, d.name AS dest_name, d.slug AS dest_slug, h.name AS stay_name, "
           "h.slug AS stay_slug, g.name AS guide_name, p.txn_id "
           "FROM bookings b "
           "LEFT JOIN destinations d ON d.id = b.destination_id "
           "LEFT JOIN homestays h ON h.id = b.homestay_id "
           "LEFT JOIN tour_guides g ON g.id = b.guide_id "
           "LEFT JOIN payments p ON p.booking_id = b.id "
           "WHERE b.user_id = ?")
    args = [session["user_id"]]
    if status:
        sql += " AND b.status = ?"
        args.append(status)
    if q:
        sql += " AND (b.booking_ref LIKE ? OR d.name LIKE ? OR h.name LIKE ? OR g.name LIKE ?)"
        args += ["%" + q + "%"] * 4
    sql += " GROUP BY b.id ORDER BY b.id DESC"
    rows = query(sql, args)
    for r in rows:
        r["item_name"] = r["dest_name"] or r["stay_name"] or r["guide_name"] or "Booking"
    return render_template("my_bookings.html", bookings=rows, q=q, status=status)


@bp.route("/booking/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel(booking_id):
    row = _own_booking(booking_id)
    if row["status"] in ("Cancelled", "Completed"):
        flash("This booking cannot be cancelled now.", "warning")
    else:
        execute("UPDATE bookings SET status = 'Cancelled' WHERE id = ?", (booking_id,))
        flash("Booking %s cancelled." % row["booking_ref"], "success")
    return redirect(url_for("booking.my_bookings"))


# --------------------------------------------------------------------------
# wishlist
# --------------------------------------------------------------------------
@bp.route("/wishlist")
@login_required
def wishlist():
    rows = query("SELECT * FROM wishlist WHERE user_id = ? ORDER BY id DESC",
                 (session["user_id"],))
    items = []
    for r in rows:
        if r["kind"] == "destination":
            d, images, _ = services.destination(
                query("SELECT slug FROM destinations WHERE id = ?", (r["item_id"],), one=True)["slug"])
            if d:
                items.append(("destination", d, images))
        else:
            h, images, _, _ = services.homestay(
                query("SELECT slug FROM homestays WHERE id = ?", (r["item_id"],), one=True)["slug"])
            if h:
                items.append(("homestay", h, images))
    return render_template("wishlist.html", items=items)


@bp.route("/wishlist/toggle", methods=["POST"])
@login_required
def wishlist_toggle():
    kind = request.form.get("kind", "destination")
    item_id = request.form.get("item_id", type=int)
    if kind not in ("destination", "homestay") or not item_id:
        abort(400)
    existing = query("SELECT id FROM wishlist WHERE user_id = ? AND kind = ? AND item_id = ?",
                     (session["user_id"], kind, item_id), one=True)
    if existing:
        execute("DELETE FROM wishlist WHERE id = ?", (existing["id"],))
        flash("Removed from your wishlist.", "success")
    else:
        execute("INSERT INTO wishlist (user_id, kind, item_id) VALUES (?,?,?)",
                (session["user_id"], kind, item_id))
        flash("Saved to your wishlist.", "success")
    return redirect(request.referrer or url_for("public.index"))


# --------------------------------------------------------------------------
# reviews
# --------------------------------------------------------------------------
@bp.route("/review", methods=["POST"])
@login_required
def review():
    kind = request.form.get("kind", "destination")
    slug = request.form.get("slug", "")
    rating = request.form.get("rating", type=int) or 0
    comment = request.form.get("comment", "").strip()
    if not 1 <= rating <= 5 or not comment:
        flash("Please choose a rating and write a short review.", "error")
        return redirect(request.referrer or url_for("public.index"))
    if kind == "destination":
        row, _, _ = services.destination(slug)
        if not row:
            abort(404)
        execute("""INSERT INTO reviews (user_id, destination_id, rating, comment, status)
                   VALUES (?,?,?,?, 'Pending')""",
                (session["user_id"], row["id"], rating, comment))
    else:
        row, _, _, _ = services.homestay(slug)
        if not row:
            abort(404)
        execute("""INSERT INTO reviews (user_id, homestay_id, rating, comment, status)
                   VALUES (?,?,?,?, 'Pending')""",
                (session["user_id"], row["id"], rating, comment))
    flash("Thank you. Your review will appear once an admin approves it.", "success")
    return redirect(request.referrer or url_for("public.index"))


# --------------------------------------------------------------------------
# itinerary planner
# --------------------------------------------------------------------------
def _haversine(a, b):
    if None in (a[0], a[1], b[0], b[1]):
        return 0.0
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _build_plan(slugs):
    places = [p for p in services.destination_options() if p["slug"] in slugs]
    if not places:
        return None
    # nearest-neighbour ordering from the first chosen place
    remaining = places[1:]
    ordered = [places[0]]
    while remaining:
        last = ordered[-1]
        nxt = min(remaining, key=lambda p: _haversine(
            (last["latitude"], last["longitude"]), (p["latitude"], p["longitude"])))
        ordered.append(nxt)
        remaining.remove(nxt)

    days, day, km_day = [], [], 0.0
    total_km = 0.0
    for i, p in enumerate(ordered):
        if i:
            leg = _haversine((ordered[i - 1]["latitude"], ordered[i - 1]["longitude"]),
                             (p["latitude"], p["longitude"]))
            total_km += leg
            km_day += leg
        stop = {"name": p["name"], "slug": p["slug"], "category": p["category"],
                "district": p["district_name"], "duration": p["duration"],
                "note": ("%s from the previous stop" % ("%.0f km" % leg)) if i else "Starting point"}
        if day and (len(day) >= 3 or km_day > 280):
            days.append(day)
            day, km_day = [], 0.0
        day.append(stop)
    if day:
        days.append(day)
    return {"days": days, "total_km": total_km,
            "title": "%d places across Karnataka" % len(ordered)}


@bp.route("/itinerary/build", methods=["POST"])
def itinerary_build():
    slugs = request.form.getlist("places")
    if not slugs:
        flash("Pick at least one destination to build a plan.", "warning")
        return redirect(url_for("public.itinerary"))
    session["itinerary"] = slugs[:12]
    return redirect(url_for("booking.itinerary_plan"))


@bp.route("/itinerary/plan")
def itinerary_plan():
    slugs = session.get("itinerary") or []
    plan = _build_plan(set(slugs))
    if not plan:
        flash("Pick a few destinations first.", "warning")
        return redirect(url_for("public.itinerary"))
    return render_template("itinerary_plan.html", plan=plan)


@bp.route("/itinerary/pdf")
@login_required
def itinerary_pdf():
    slugs = session.get("itinerary") or []
    plan = _build_plan(set(slugs))
    if not plan:
        return redirect(url_for("public.itinerary"))
    user = query("SELECT * FROM users WHERE id = ?", (session["user_id"],), one=True)
    pdf = build_itinerary_pdf(plan, user)
    return send_file(__import__("io").BytesIO(pdf), mimetype="application/pdf",
                     as_attachment=True, download_name="Karnataka-itinerary.pdf")
