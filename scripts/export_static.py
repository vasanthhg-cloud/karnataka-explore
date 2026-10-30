# -*- coding: utf-8 -*-
"""Export the public site as static HTML for GitHub Pages.

Renders every browsable page through the Flask test client, rewrites internal
links to relative paths (so the export works at any URL prefix and even from
file://), neutralises POST forms, and adds a notice explaining that booking,
login and the admin console need the Python app.

    python scripts/export_static.py            -> ../docs
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from app import create_app          # noqa: E402
from db import query                # noqa: E402

OUT = BASE / "docs"

# Routes that the browser demo app handles (sign-in, booking, payment, admin).
DEMO_PREFIX = "app/index.html#"

BLOCKED = ("payment/", "booking/", "wishlist", "verify/", "logout", "review", "qr.png",
           "language/", "itinerary/build", "search", "map/data", "newsletter",
           "reset-password")


def demo_target(path):
    """Map a server route to a view in the browser demo app, or None."""
    if path.startswith("book/destination/"):
        return DEMO_PREFIX + "/book?type=destination&slug=" + path.split("/")[-1]
    if path.startswith("book/homestay/"):
        return DEMO_PREFIX + "/book?type=homestay&slug=" + path.split("/")[-1]
    if path.startswith("book/guide/"):
        return DEMO_PREFIX + "/book?type=guide&slug=" + path.split("/")[-1]
    if path in ("login", "login/"):
        return DEMO_PREFIX + "/login"
    if path in ("register", "register/"):
        return DEMO_PREFIX + "/register"
    if path in ("my-bookings", "my-bookings/"):
        return DEMO_PREFIX + "/bookings"
    if path.startswith("admin"):
        return DEMO_PREFIX + "/admin"
    if path.startswith("profile"):
        return DEMO_PREFIX + "/profile"
    return None

NOTICE_BANNER = (
    '<div style="background:#0f6b4f;color:#eaf5f0;font:600 13px/1.5 system-ui,sans-serif;'
    'padding:10px 18px;text-align:center;position:relative;z-index:100">'
    'Static preview of Karnataka Explore &mdash; every destination, homestay and guide is browsable. '
    'Booking, sign-in, payments and the admin console run in the Python app: '
    '<a href="https://github.com/vasanthhg-cloud/karnataka-explore" '
    'style="color:#fff;text-decoration:underline">see the repository</a>.'
    '</div>'
)

FORM_GUARD = (' onsubmit="alert(\'This is the static preview. Run the Flask app '
              '(python run.py) for sign-in, booking, payments and admin.\');return false;"')


def rel_prefix(out_rel_path):
    depth = out_rel_path.count("/")
    return "../" * depth if depth else ""


def has_extension(url):
    tail = url.split("?")[0].split("#")[0].rstrip("/").rsplit("/", 1)[-1]
    return "." in tail


def rewrite(html, out_path):
    rel = rel_prefix(out_path)

    def fix(match):
        attr, url = match.group(1), match.group(2)
        if url.startswith(("//", "#", "mailto:", "tel:", "http:", "https:", "data:")):
            return match.group(0)
        path = url[1:]
        if path == "":
            return '%s="%s"' % (attr, rel if rel else "./")
        demo = demo_target(path.split("?")[0].rstrip("/"))
        if demo:
            return '%s="%s%s"' % (attr, rel, demo)
        if path.startswith(BLOCKED):
            return '%s="%spreview/"' % (attr, rel)
        if attr == "href" and not has_extension(path) and not path.endswith("/") and "?" not in path:
            path += "/"
        return '%s="%s%s"' % (attr, rel, path)

    html = re.sub(r'(href|src|action)="(/(?!/)[^"]*)"', fix, html)
    html = re.sub(r'<form([^>]*?)method="post"', r'<form\1method="post"' + FORM_GUARD, html)
    html = re.sub(r"(<body[^>]*>)", r"\1" + NOTICE_BANNER.replace("\\", "\\\\"), html, count=1)
    return html


NOTICE_PAGE = """<!doctype html>
<html lang="en" data-theme="light"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Needs the Python app - Karnataka Explore</title>
<link rel="stylesheet" href="../static/css/style.css"></head>
<body>
<div style="max-width:640px;margin:14vh auto;padding:0 22px;text-align:center">
  <div style="width:56px;height:56px;border-radius:16px;background:#e4f2ec;color:#0f6b4f;display:grid;place-items:center;margin:0 auto 1rem"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg></div>
  <h1 style="font-size:1.6rem">This part needs the running app</h1>
  <p class="muted">The wishlist, review submission and saving an itinerary need a Python server and a
  database, so they are switched off in this static preview.</p>
  <p class="muted">Sign-in, booking, the demo payment step, tickets and the admin console <b>do</b>
  work here &mdash; they run in your browser in demo mode. Everything else (all 31 districts,
  116 destinations with galleries and maps, homestays, guides, dark mode) is fully browsable.</p>
  <div style="display:flex;gap:.6rem;justify-content:center;flex-wrap:wrap;margin-top:1.5rem">
    <a class="btn btn-primary" href="../index.html">Back to the home page</a>
    <a class="btn btn-ghost" href="https://github.com/vasanthhg-cloud/karnataka-explore">Run it locally</a>
  </div>
</div>
</body></html>"""


def main():
    app = create_app()
    app.config["SERVER_NAME"] = None
    client = app.test_client()

    with app.app_context():
        destinations = [r["slug"] for r in query("SELECT slug FROM destinations WHERE active = 1")]
        districts = [r["slug"] for r in query("SELECT slug FROM districts")]
        stays = [r["slug"] for r in query("SELECT slug FROM homestays WHERE active = 1")]

    routes = [("/", "index.html"),
              ("/destinations", "destinations/index.html"),
              ("/districts", "districts/index.html"),
              ("/homestays", "homestays/index.html"),
              ("/guides", "guides/index.html"),
              ("/map", "map/index.html"),
              ("/itinerary", "itinerary/index.html"),
              ("/about", "about/index.html"),
              ("/contact", "contact/index.html"),
              ("/login", "login/index.html"),
              ("/register", "register/index.html")]
    routes += [("/destination/" + s, "destination/%s/index.html" % s) for s in destinations]
    routes += [("/district/" + s, "district/%s/index.html" % s) for s in districts]
    routes += [("/homestay/" + s, "homestay/%s/index.html" % s) for s in stays]

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    written, skipped = 0, []
    for route, out_rel in routes:
        resp = client.get(route)
        if resp.status_code != 200:
            skipped.append((route, resp.status_code))
            continue
        html = rewrite(resp.get_data(as_text=True), out_rel)
        target = OUT / out_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        written += 1

    # assets
    shutil.copytree(BASE / "static", OUT / "static",
                    ignore=shutil.ignore_patterns("uploads"))
    (OUT / "static" / "uploads").mkdir(exist_ok=True)
    (OUT / ".nojekyll").write_text("")

    # data for the browser demo app
    with app.app_context():
        dest_rows = query("""SELECT d.slug, d.name, d.ticket_price AS price, dist.name AS district,
                                    (SELECT image_url FROM destination_images i WHERE i.destination_id = d.id
                                     ORDER BY i.sort_order LIMIT 1) AS image
                             FROM destinations d JOIN districts dist ON dist.id = d.district_id
                             WHERE d.active = 1 ORDER BY d.name""")
        stay_rows = query("""SELECT h.slug, h.name, h.price_per_night AS price, h.rooms_available AS rooms,
                                    h.max_guests, dist.name AS district,
                                    (SELECT image_url FROM homestay_images i WHERE i.homestay_id = h.id
                                     ORDER BY i.sort_order LIMIT 1) AS image
                             FROM homestays h JOIN districts dist ON dist.id = h.district_id
                             WHERE h.active = 1 ORDER BY h.name""")
        guide_rows = query("""SELECT g.id, g.name, g.fee_per_day AS fee, dist.name AS district
                              FROM tour_guides g LEFT JOIN districts dist ON dist.id = g.district_id
                              WHERE g.active = 1 ORDER BY g.name""")
    items = {
        "destinations": [dict(r) for r in dest_rows],
        "homestays": [dict(r) for r in stay_rows],
        "guides": [dict(r, slug=str(r["id"])) for r in guide_rows],
    }
    (OUT / "data").mkdir(exist_ok=True)
    (OUT / "data" / "items.json").write_text(json.dumps(items), encoding="utf-8")

    # the browser demo app (sign-in, booking, payment, tickets, admin)
    app_src = BASE / "scripts" / "static_app"
    if app_src.exists():
        shutil.copytree(app_src, OUT / "app")

    # the "needs the app" page
    (OUT / "preview").mkdir(exist_ok=True)
    (OUT / "preview" / "index.html").write_text(NOTICE_PAGE, encoding="utf-8")

    # a 404 page that sends people home
    (OUT / "404.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Not found</title>'
        '<script>location.replace("/karnataka-explore/")</script>'
        '<p>Page not found. <a href="/karnataka-explore/">Go to Karnataka Explore</a>.</p>',
        encoding="utf-8")

    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print("pages written : %d" % written)
    print("files total   : %d" % len([f for f in OUT.rglob('*') if f.is_file()]))
    print("size          : %.1f MB" % (size / 1e6))
    if skipped:
        print("skipped       :", skipped[:10])


if __name__ == "__main__":
    main()
