# -*- coding: utf-8 -*-
"""Public pages: home, listings, detail pages, map, about, contact."""
import json

from flask import (Blueprint, flash, jsonify, redirect, render_template, request,
                   session, url_for)

import services
from data import CATEGORIES
from db import execute, query
from i18n import TRANSLATIONS
from security import valid_email

bp = Blueprint("public", __name__)

FACILITY_CHOICES = ["Free Wi-Fi", "Parking", "Food", "Swimming Pool", "AC Rooms",
                    "Family Rooms", "Nature View", "Campfire", "Trekking", "Local Food"]


@bp.route("/")
def index():
    featured, _ = services.destinations(featured_only=True, limit=6)
    if len(featured) < 6:
        extra, _ = services.destinations(sort="rating", limit=6 - len(featured))
        featured += extra
    waterfalls, _ = services.destinations(category="Waterfalls", limit=4)
    historical, _ = services.destinations(category="Historical Places", limit=4)
    temples, _ = services.destinations(category="Temples", limit=4)
    beaches, _ = services.destinations(category="Beaches", limit=2)
    hills, _ = services.destinations(category="Hill Stations", limit=2)
    stays, _ = services.homestays(page=1, per_page=3)
    return render_template(
        "index.html",
        featured=featured, waterfalls=waterfalls, historical=historical,
        temples=temples, beaches_hills=beaches + hills,
        stays=stays, districts=services.districts_with_counts(),
        reviews=services.top_reviews(6),
        tips=services.site_content("travel_tips").split("|"),
        map_points=services.map_points(),
        total_destinations=len(services.map_points()),
        categories=CATEGORIES)


@bp.route("/destinations")
def destinations():
    q = request.args.get("q", "").strip()
    district = request.args.get("district") or None
    category = request.args.get("category") or None
    sort = request.args.get("sort", "popular")
    page = int(request.args.get("page", 1) or 1)
    rows, info = services.destinations(q=q, district=district, category=category,
                                       sort=sort, page=page, per_page=9)
    return render_template("destinations.html", destinations=rows, info=info,
                           q=q, district=district, category=category, sort=sort,
                           districts=services.districts_with_counts(),
                           categories=CATEGORIES)


@bp.route("/destination/<slug>")
def destination_detail(slug):
    row, images, reviews = services.destination(slug)
    if not row:
        return render_template("errors/404.html"), 404
    return render_template("destination_detail.html", d=row, images=images,
                           reviews=reviews, nearby=services.nearby_places(row),
                           in_wishlist=_in_wishlist("destination", row["id"]))


@bp.route("/districts")
def districts():
    return render_template("districts.html", districts=services.districts_with_counts())


@bp.route("/district/<slug>")
def district_detail(slug):
    district = services.district_by_slug(slug)
    if not district:
        return render_template("errors/404.html"), 404
    rows, info = services.destinations(district=slug, per_page=12)
    stays, _ = services.homestays(district=slug, per_page=3)
    return render_template("district_detail.html", district=district, destinations=rows,
                           info=info, stays=stays, categories=CATEGORIES)


@bp.route("/homestays")
def homestays():
    q = request.args.get("q", "").strip()
    district = request.args.get("district") or None
    facility = request.args.get("facility") or None
    max_price = request.args.get("max_price", type=int)
    sort = request.args.get("sort", "rating")
    page = int(request.args.get("page", 1) or 1)
    rows, info = services.homestays(q=q, district=district, max_price=max_price,
                                    facility=facility, sort=sort, page=page, per_page=9)
    return render_template("homestays.html", stays=rows, info=info, q=q, district=district,
                           facility=facility, max_price=max_price, sort=sort,
                           districts=services.districts_with_counts(),
                           facilities=FACILITY_CHOICES)


@bp.route("/homestay/<slug>")
def homestay_detail(slug):
    row, images, rooms, reviews = services.homestay(slug)
    if not row:
        return render_template("errors/404.html"), 404
    return render_template("homestay_detail.html", h=row, images=images, rooms=rooms,
                           reviews=reviews, in_wishlist=_in_wishlist("homestay", row["id"]))


@bp.route("/guides")
def guides():
    q = request.args.get("q", "").strip()
    district = request.args.get("district") or None
    return render_template("guides.html", guides=services.guides(q=q, district=district),
                           q=q, district=district,
                           districts=services.districts_with_counts())


@bp.route("/map")
def tourism_map():
    return render_template("map.html", points=services.map_points(),
                           stays=services.homestay_points(),
                           categories=CATEGORIES)


@bp.route("/map/data")
def map_data():
    """JSON feed used by the Leaflet map."""
    return jsonify({
        "destinations": services.map_points(),
        "homestays": services.homestay_points(),
    })


@bp.route("/itinerary")
def itinerary():
    return render_template("itinerary.html", places=services.destination_options(),
                           categories=CATEGORIES)


@bp.route("/about")
def about():
    return render_template("about.html", districts=services.districts_with_counts())


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not message or not valid_email(email):
            flash("Please enter your name, a valid email and a message.", "error")
        else:
            execute("""INSERT INTO contact_messages (name, email, phone, subject, message)
                       VALUES (?,?,?,?,?)""", (name, email, phone, subject, message))
            flash("Thank you - your message has reached us.", "success")
            return redirect(url_for("public.contact"))
    return render_template("contact.html",
                           emergency=services.site_content("emergency").split("|"))


@bp.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.form.get("email", "").strip()
    if valid_email(email):
        if not query("SELECT 1 FROM newsletter WHERE email = ?", (email,), one=True):
            execute("INSERT INTO newsletter (email) VALUES (?)", (email,))
        flash("You are subscribed. Travel notes will reach you monthly.", "success")
    else:
        flash("Please enter a valid email address.", "error")
    return redirect(request.referrer or url_for("public.index"))


@bp.route("/language/<code>")
def set_language(code):
    if code in TRANSLATIONS:
        session["lang"] = code
    return redirect(request.referrer or url_for("public.index"))


@bp.route("/search")
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return redirect(url_for("public.destinations"))
    return redirect(url_for("public.destinations", q=q))


def _in_wishlist(kind, item_id):
    uid = session.get("user_id")
    if not uid:
        return False
    return bool(query("SELECT 1 FROM wishlist WHERE user_id = ? AND kind = ? AND item_id = ?",
                      (uid, kind, item_id), one=True))
