# -*- coding: utf-8 -*-
"""Read-side queries shared by the public pages, the user area and admin."""
import math

from db import query

DEST_COLS = """
    d.id, d.name, d.slug, d.category, d.description, d.location, d.latitude, d.longitude,
    d.best_time, d.entry_fee, d.timings, d.activities, d.nearby, d.travel_info,
    d.duration, d.ticket_price, d.featured, d.active, d.district_id,
    dist.name AS district_name, dist.slug AS district_slug, dist.region AS district_region,
    (SELECT image_url FROM destination_images i WHERE i.destination_id = d.id
        ORDER BY i.sort_order LIMIT 1) AS image,
    (SELECT ROUND(AVG(rating), 1) FROM reviews r WHERE r.destination_id = d.id
        AND r.status = 'Approved') AS rating,
    (SELECT COUNT(*) FROM reviews r WHERE r.destination_id = d.id
        AND r.status = 'Approved') AS review_count
"""

HOMESTAY_COLS = """
    h.*, dist.name AS district_name, dist.slug AS district_slug,
    (SELECT image_url FROM homestay_images i WHERE i.homestay_id = h.id
        ORDER BY i.sort_order LIMIT 1) AS image,
    (SELECT ROUND(AVG(rating), 1) FROM reviews r WHERE r.homestay_id = h.id
        AND r.status = 'Approved') AS review_avg,
    (SELECT COUNT(*) FROM reviews r WHERE r.homestay_id = h.id
        AND r.status = 'Approved') AS review_count
"""


def paginate(total, page, per_page):
    pages = max(1, math.ceil(total / per_page)) if total else 1
    page = max(1, min(page, pages))
    return {"page": page, "pages": pages, "total": total, "per_page": per_page,
            "has_prev": page > 1, "has_next": page < pages}


def destinations(q=None, district=None, category=None, sort="popular",
                 page=1, per_page=12, featured_only=False, limit=None):
    where, args = ["d.active = 1"], []
    if q:
        like = "%" + q.strip() + "%"
        where.append("(d.name LIKE ? OR d.description LIKE ? OR d.category LIKE ? "
                     "OR d.location LIKE ? OR dist.name LIKE ?)")
        args += [like] * 5
    if district:
        where.append("dist.slug = ?")
        args.append(district)
    if category:
        where.append("d.category = ?")
        args.append(category)
    if featured_only:
        where.append("d.featured = 1")
    clause = " WHERE " + " AND ".join(where)

    order = {
        "popular": "d.featured DESC, review_count DESC, d.name ASC",
        "name": "d.name ASC",
        "price_low": "d.ticket_price ASC, d.name ASC",
        "price_high": "d.ticket_price DESC, d.name ASC",
        "rating": "rating DESC, review_count DESC",
    }.get(sort, "d.featured DESC, d.name ASC")

    base = ("SELECT " + DEST_COLS + " FROM destinations d "
            "JOIN districts dist ON dist.id = d.district_id" + clause)
    total = query("SELECT COUNT(*) AS c FROM (" + base + ")", args, one=True)["c"]
    if limit:
        rows = query(base + " ORDER BY " + order + " LIMIT ?", args + [limit])
        return rows, paginate(total, 1, limit)
    page_info = paginate(total, page, per_page)
    rows = query(base + " ORDER BY " + order + " LIMIT ? OFFSET ?",
                 args + [per_page, (page_info["page"] - 1) * per_page])
    return rows, page_info


def destination(slug):
    row = query("SELECT " + DEST_COLS + " FROM destinations d "
                "JOIN districts dist ON dist.id = d.district_id WHERE d.slug = ?",
                (slug,), one=True)
    if not row:
        return None, [], []
    images = query("SELECT image_url, caption FROM destination_images WHERE destination_id = ? "
                   "ORDER BY sort_order", (row["id"],))
    reviews = query("""SELECT r.*, u.full_name FROM reviews r JOIN users u ON u.id = r.user_id
                       WHERE r.destination_id = ? AND r.status = 'Approved'
                       ORDER BY r.created_at DESC LIMIT 12""", (row["id"],))
    return row, images, reviews


def nearby_places(row, limit=4):
    """Same district first, then same category anywhere in the state."""
    same = query("SELECT " + DEST_COLS + " FROM destinations d "
                 "JOIN districts dist ON dist.id = d.district_id "
                 "WHERE d.active = 1 AND d.district_id = ? AND d.id <> ? "
                 "ORDER BY d.featured DESC LIMIT ?", (row["district_id"], row["id"], limit))
    if len(same) < limit:
        more = query("SELECT " + DEST_COLS + " FROM destinations d "
                     "JOIN districts dist ON dist.id = d.district_id "
                     "WHERE d.active = 1 AND d.category = ? AND d.district_id <> ? "
                     "ORDER BY d.featured DESC LIMIT ?",
                     (row["category"], row["district_id"], limit - len(same)))
        same += more
    return same


def homestays(q=None, district=None, max_price=None, facility=None, sort="rating",
              page=1, per_page=9):
    where, args = ["h.active = 1"], []
    if q:
        like = "%" + q.strip() + "%"
        where.append("(h.name LIKE ? OR h.description LIKE ? OR h.address LIKE ? OR dist.name LIKE ?)")
        args += [like] * 4
    if district:
        where.append("dist.slug = ?")
        args.append(district)
    if max_price:
        where.append("h.price_per_night <= ?")
        args.append(max_price)
    if facility:
        where.append("h.facilities LIKE ?")
        args.append("%" + facility + "%")
    clause = " WHERE " + " AND ".join(where)
    order = {"rating": "review_avg DESC, h.rating DESC",
             "price_low": "h.price_per_night ASC",
             "price_high": "h.price_per_night DESC"}.get(sort, "h.rating DESC")
    base = ("SELECT " + HOMESTAY_COLS + " FROM homestays h "
            "JOIN districts dist ON dist.id = h.district_id" + clause)
    total = query("SELECT COUNT(*) AS c FROM (" + base + ")", args, one=True)["c"]
    info = paginate(total, page, per_page)
    rows = query(base + " ORDER BY " + order + " LIMIT ? OFFSET ?",
                 args + [per_page, (info["page"] - 1) * per_page])
    return rows, info


def homestay(slug):
    row = query("SELECT " + HOMESTAY_COLS + " FROM homestays h "
                "JOIN districts dist ON dist.id = h.district_id WHERE h.slug = ?",
                (slug,), one=True)
    if not row:
        return None, [], [], []
    images = query("SELECT image_url FROM homestay_images WHERE homestay_id = ? ORDER BY sort_order",
                   (row["id"],))
    rooms = query("SELECT * FROM rooms WHERE homestay_id = ?", (row["id"],))
    reviews = query("""SELECT r.*, u.full_name FROM reviews r JOIN users u ON u.id = r.user_id
                       WHERE r.homestay_id = ? AND r.status = 'Approved'
                       ORDER BY r.created_at DESC LIMIT 12""", (row["id"],))
    return row, images, rooms, reviews


def districts_with_counts():
    return query("""
        SELECT dist.id, dist.name, dist.slug, dist.region, dist.description,
               (SELECT COUNT(*) FROM destinations d WHERE d.district_id = dist.id AND d.active = 1) AS dest_count,
               (SELECT COUNT(*) FROM homestays h WHERE h.district_id = dist.id AND h.active = 1) AS stay_count,
               (SELECT i.image_url FROM destinations d JOIN destination_images i
                    ON i.destination_id = d.id WHERE d.district_id = dist.id
                    ORDER BY d.featured DESC, d.id ASC, i.sort_order LIMIT 1) AS image
        FROM districts dist ORDER BY dist.name""")


def district_by_slug(slug):
    return query("SELECT * FROM districts WHERE slug = ?", (slug,), one=True)


def map_points():
    return query("""SELECT d.name, d.slug, d.category, d.latitude, d.longitude,
                           dist.name AS district_name
                    FROM destinations d JOIN districts dist ON dist.id = d.district_id
                    WHERE d.active = 1 AND d.latitude IS NOT NULL AND d.longitude IS NOT NULL""")


def homestay_points():
    return query("""SELECT h.name, h.slug, h.price_per_night, h.latitude, h.longitude,
                           dist.name AS district_name
                    FROM homestays h JOIN districts dist ON dist.id = h.district_id
                    WHERE h.active = 1 AND h.latitude IS NOT NULL AND h.longitude IS NOT NULL""")


def guides(q=None, district=None):
    where, args = ["g.active = 1"], []
    if q:
        like = "%" + q.strip() + "%"
        where.append("(g.name LIKE ? OR g.languages LIKE ? OR g.bio LIKE ? OR dist.name LIKE ?)")
        args += [like] * 4
    if district:
        where.append("dist.slug = ?")
        args.append(district)
    return query("""SELECT g.*, dist.name AS district_name, dist.slug AS district_slug
                    FROM tour_guides g LEFT JOIN districts dist ON dist.id = g.district_id
                    WHERE """ + " AND ".join(where) + " ORDER BY g.rating DESC, g.name", args)


def guide(guide_id):
    return query("""SELECT g.*, dist.name AS district_name, dist.slug AS district_slug
                    FROM tour_guides g LEFT JOIN districts dist ON dist.id = g.district_id
                    WHERE g.id = ?""", (guide_id,), one=True)


def top_reviews(limit=6):
    return query("""SELECT r.*, u.full_name, d.name AS destination_name, d.slug AS destination_slug
                    FROM reviews r JOIN users u ON u.id = r.user_id
                    LEFT JOIN destinations d ON d.id = r.destination_id
                    WHERE r.status = 'Approved' ORDER BY r.rating DESC, r.created_at DESC LIMIT ?""",
                 (limit,))


def site_content(key, default=""):
    row = query("SELECT value FROM site_content WHERE key = ?", (key,), one=True)
    return row["value"] if row and row["value"] else default


def destination_options():
    return query("""SELECT d.id, d.name, d.slug, d.category, d.district_id, d.latitude, d.longitude,
                           d.duration, dist.name AS district_name
                    FROM destinations d JOIN districts dist ON dist.id = d.district_id
                    WHERE d.active = 1 ORDER BY dist.name, d.name""")
