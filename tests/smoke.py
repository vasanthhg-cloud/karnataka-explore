# -*- coding: utf-8 -*-
"""End-to-end smoke test: walks every route as a visitor, a user and an admin."""
import io
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from db import query

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False
FAILS = []


def check(label, resp, expect=(200,), body_contains=None):
    ok = resp.status_code in expect
    if ok and body_contains:
        text = resp.get_data(as_text=True)
        ok = all(b.lower() in text.lower() for b in body_contains)
    status = "ok  " if ok else "FAIL"
    print("%s %-52s %s" % (status, label, resp.status_code))
    if not ok:
        FAILS.append((label, resp.status_code, resp.get_data(as_text=True)[:600]))
    return resp


def main():
    ctx = app.app_context()
    ctx.push()
    c = app.test_client()

    # ---------- public ----------
    check("home", c.get("/"))
    check("destinations", c.get("/destinations"), body_contains=["Badami"])
    check("destinations filter", c.get("/destinations?district=mysuru&category=Temples"))
    check("destinations search", c.get("/destinations?q=falls"))
    check("destination detail", c.get("/destination/jog-falls"), body_contains=["Jog Falls"])
    check("destination 404", c.get("/destination/nope-nope"), expect=(404,))
    check("districts", c.get("/districts"))
    check("district detail", c.get("/district/kodagu"))
    check("homestays", c.get("/homestays"))
    check("homestay detail", c.get("/homestay/coffee-blossom-estate-stay"))
    check("guides", c.get("/guides"))
    check("map", c.get("/map"))
    check("map json", c.get("/map/data"))
    check("itinerary", c.get("/itinerary"))
    check("about", c.get("/about"))
    check("contact", c.get("/contact"))
    check("language hi", c.get("/language/hi"), expect=(302,))
    check("home in hindi", c.get("/"), body_contains=["कर्नाटक"])
    check("language kn", c.get("/language/kn"), expect=(302,))
    check("home in kannada", c.get("/"), body_contains=["ಕರ್ನಾಟಕ"])
    check("language back to en", c.get("/language/en"), expect=(302,))
    check("404 page", c.get("/nothing-here"), expect=(404,))

    # contact form
    check("contact post", c.post("/contact", data={
        "name": "Test Person", "email": "test@example.com", "message": "Hello there"},
        follow_redirects=True), body_contains=["Thank you"])

    # ---------- auth ----------
    check("login page", c.get("/login"))
    check("register page", c.get("/register"))
    import random
    stamp = random.randint(100000, 999999)
    email = "smoke%s@example.com" % stamp
    mobile = "9%09d" % stamp
    check("register post", c.post("/register", data={
        "full_name": "Smoke Tester", "email": email, "mobile": mobile,
        "password": "Testing123", "confirm_password": "Testing123",
        "district": "Mysuru", "gender": "Prefer not to say"}, follow_redirects=True),
        body_contains=["Welcome"])
    check("profile", c.get("/profile"))
    check("profile update", c.post("/profile", data={
        "full_name": "Smoke Tester", "mobile": mobile,
        "district": "Kodagu", "gender": "Other"}, follow_redirects=True))
    check("wishlist empty", c.get("/wishlist"))
    check("my bookings empty", c.get("/my-bookings"))
    check("forgot password", c.get("/forgot-password"))
    check("forgot post", c.post("/forgot-password", data={"email": email}), expect=(302,))

    # ---------- destination booking ----------
    check("book destination page", c.get("/book/destination/jog-falls"))
    visit = (date.today() + timedelta(days=10)).isoformat()
    r = check("book destination post", c.post("/book/destination/jog-falls",
              data={"visit_date": visit, "visitors": "3"}), expect=(302,))
    booking_url = r.headers["Location"]
    check("payment page", c.get(booking_url))
    bid = int(re.search(r"/payment/(\d+)", booking_url).group(1))
    check("ticket before payment", c.get("/booking/%d" % bid))
    check("pay fail", c.post("/payment/%d" % bid, data={"method": "upi", "outcome": "failure"},
                             follow_redirects=True), body_contains=["failed"])
    check("pay success", c.post("/payment/%d" % bid, data={"method": "upi", "outcome": "success"},
                                follow_redirects=True), body_contains=["successful"])
    check("ticket page", c.get("/booking/%d" % bid), body_contains=["KX-"])
    pdf = check("ticket pdf", c.get("/booking/%d/ticket.pdf" % bid))
    assert pdf.data[:4] == b"%PDF", "ticket pdf is not a PDF"
    print("     pdf bytes:", len(pdf.data))
    row = query("SELECT booking_ref FROM bookings WHERE id = ?", (bid,), one=True)
    check("verify page", c.get("/verify/" + row["booking_ref"]))
    check("qr png", c.get("/qr.png?data=https://example.com/verify/" + row["booking_ref"]))
    check("my bookings", c.get("/my-bookings"), body_contains=[row["booking_ref"]])
    check("my bookings search", c.get("/my-bookings?q=" + row["booking_ref"]))

    # ---------- homestay booking ----------
    check("book homestay page", c.get("/book/homestay/coffee-blossom-estate-stay"))
    ci = (date.today() + timedelta(days=5)).isoformat()
    co = (date.today() + timedelta(days=8)).isoformat()
    r = check("book homestay post", c.post("/book/homestay/coffee-blossom-estate-stay",
              data={"checkin": ci, "checkout": co, "guests": "2", "rooms": "1"}), expect=(302,))
    bid2 = int(re.search(r"/payment/(\d+)", r.headers["Location"]).group(1))
    check("homestay pay", c.post("/payment/%d" % bid2, data={"method": "credit", "outcome": "success"},
                                 follow_redirects=True))
    pdf2 = c.get("/booking/%d/ticket.pdf" % bid2)
    assert pdf2.data[:4] == b"%PDF"
    print("     homestay ticket pdf bytes:", len(pdf2.data))

    # ---------- guide booking ----------
    gid = query("SELECT id FROM tour_guides LIMIT 1", one=True)["id"]
    check("book guide page", c.get("/book/guide/%d" % gid))
    r = check("book guide post", c.post("/book/guide/%d" % gid,
              data={"start_date": visit, "days": "2", "visitors": "2"}), expect=(302,))
    bid3 = int(re.search(r"/payment/(\d+)", r.headers["Location"]).group(1))
    check("guide pay", c.post("/payment/%d" % bid3, data={"method": "netbanking", "outcome": "success"},
                              follow_redirects=True))

    # ---------- wishlist + review + itinerary ----------
    d = query("SELECT id, slug FROM destinations LIMIT 1", one=True)
    check("wishlist toggle on", c.post("/wishlist/toggle", data={"kind": "destination", "item_id": d["id"]},
                                       follow_redirects=True))
    check("wishlist page", c.get("/wishlist"))
    check("wishlist toggle off", c.post("/wishlist/toggle", data={"kind": "destination", "item_id": d["id"]},
                                        follow_redirects=True))
    check("review post", c.post("/review", data={"kind": "destination", "slug": d["slug"],
              "rating": "5", "comment": "Lovely place, worth the drive."}, follow_redirects=True))
    check("itinerary build", c.post("/itinerary/build", data={
        "places": ["jog-falls", "om-beach-gokarna", "mysore-palace", "hampi-virupaksha"]}, follow_redirects=True))
    check("itinerary plan", c.get("/itinerary/plan"), body_contains=["Day 1"])
    ipdf = c.get("/itinerary/pdf")
    assert ipdf.data[:4] == b"%PDF", "itinerary pdf broken"
    print("     itinerary pdf bytes:", len(ipdf.data))

    # cancel
    check("cancel booking", c.post("/booking/%d/cancel" % bid3, follow_redirects=True),
          body_contains=["cancelled"])
    check("logout", c.get("/logout"), expect=(302,))

    # protected page while signed out
    check("my-bookings blocked", c.get("/my-bookings"), expect=(302,))

    # ---------- admin ----------
    a = app.test_client()
    check("admin login page", a.get("/admin/login"))
    check("admin blocked", a.get("/admin/"), expect=(302,))
    check("admin login bad", a.post("/admin/login", data={"email": "x@y.com", "password": "nope"},
                                    follow_redirects=True), body_contains=["Invalid"])
    check("admin login", a.post("/admin/login", data={
        "email": app.config["DEFAULT_ADMIN_EMAIL"],
        "password": app.config["DEFAULT_ADMIN_PASSWORD"]}), expect=(302,))
    for path in ["/admin/", "/admin/destinations", "/admin/homestays", "/admin/guides",
                 "/admin/bookings", "/admin/payments", "/admin/users", "/admin/reviews",
                 "/admin/messages", "/admin/content", "/admin/admins"]:
        check("admin " + path, a.get(path))

    # admin CRUD
    check("admin destination new page", a.get("/admin/destinations/new"))
    a.post("/admin/destinations/new", data={
        "name": "Smoke Test Falls", "district_id": "1", "category": "Waterfalls",
        "description": "A test destination created by the smoke test.",
        "location": "Somewhere", "ticket_price": "40", "active": "on"})
    new = query("SELECT id FROM destinations WHERE name = 'Smoke Test Falls'", one=True)
    assert new, "destination was not created"
    check("admin destination edit page", a.get("/admin/destinations/%d/edit" % new["id"]))
    check("admin destination edit post", a.post("/admin/destinations/%d/edit" % new["id"], data={
        "name": "Smoke Test Falls", "district_id": "1", "category": "Waterfalls",
        "description": "Updated description.", "ticket_price": "55", "active": "on",
        "featured": "on"}, follow_redirects=True))
    check("admin homestay new page", a.get("/admin/homestays/new"))
    check("admin guide new page", a.get("/admin/guides/new"))
    check("admin booking status", a.post("/admin/bookings/%d/status" % bid, data={"status": "Completed"},
                                         follow_redirects=True))
    rid = query("SELECT id FROM reviews WHERE status = 'Pending' LIMIT 1", one=True)
    if rid:
        check("admin approve review", a.post("/admin/reviews/%d/approve" % rid["id"],
                                             follow_redirects=True))
    check("admin content post", a.post("/admin/content", data={"travel_tips": "Tip one|Tip two",
                                                               "emergency": "Police 100"}, follow_redirects=True))
    check("admin delete destination", a.post("/admin/destinations/%d/delete" % new["id"],
                                             follow_redirects=True))
    check("admin logout", a.get("/admin/logout"), expect=(302,))

    ctx.pop()
    print("\n" + ("ALL CHECKS PASSED" if not FAILS else "%d FAILURES" % len(FAILS)))
    for f in FAILS:
        print("\n---", f[0], f[1])
        print(f[2][:500])
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
