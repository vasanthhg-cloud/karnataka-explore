# -*- coding: utf-8 -*-
"""Create the schema and load seed data: 31 districts, 116 destinations,
sample homestays, guides and reviews, plus an admin and a demo user.

Run once:  python seed.py     (safe to re-run; it skips existing rows)
"""
import json
import os
import random
import re
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from data import ALL_PART, CATEGORIES, DISTRICTS, all_destinations  # noqa: E402
from data.sample_content import GUIDES, HOMESTAYS, REVIEWS  # noqa: E402

REGIONS = {
    "Bagalkote": "North Karnataka", "Ballari": "Kalyana Karnataka",
    "Belagavi": "North Karnataka", "Bengaluru Rural": "Bengaluru region",
    "Bengaluru Urban": "Bengaluru region", "Bidar": "Kalyana Karnataka",
    "Chamarajanagara": "Southern Karnataka", "Chikkaballapura": "Bengaluru region",
    "Chikkamagaluru": "Malnad", "Chitradurga": "Central Karnataka",
    "Dakshina Kannada": "Coastal Karnataka", "Davanagere": "Central Karnataka",
    "Dharwad": "North Karnataka", "Gadag": "North Karnataka", "Hassan": "Malnad",
    "Haveri": "North Karnataka", "Kalaburagi": "Kalyana Karnataka", "Kodagu": "Malnad",
    "Kolar": "Bengaluru region", "Koppal": "Kalyana Karnataka", "Mandya": "Southern Karnataka",
    "Mysuru": "Southern Karnataka", "Raichur": "Kalyana Karnataka",
    "Ramanagara": "Bengaluru region", "Shivamogga": "Malnad", "Tumakuru": "Central Karnataka",
    "Udupi": "Coastal Karnataka", "Uttara Kannada": "Coastal Karnataka",
    "Vijayapura": "North Karnataka", "Vijayanagara": "Kalyana Karnataka",
    "Yadgir": "Kalyana Karnataka",
}

DISTRICT_BLURB = {
    "Bagalkote": "Chalukyan cave temples, the cradle of temple architecture at Aihole and Pattadakal, and the Malaprabha valley.",
    "Ballari": "Granite hill forts, the Daroji sloth bear sanctuary and the dry iron-ore country of eastern Karnataka.",
    "Belagavi": "Gokak Falls, Rani Chennamma's Kittur, old Jain basadis and the coolest city in the state.",
    "Bengaluru Rural": "Devanahalli fort, Nrityagram's dance village and the grasslands of Hesaraghatta.",
    "Bengaluru Urban": "Gardens, palaces, museums and the most cosmopolitan city in south India.",
    "Bidar": "The Bahmani capital with its basalt fort, Sufi dargahs and the Guru Nanak Jhira.",
    "Chamarajanagara": "Bandipur's tigers, the Biligiri Rangan hills and the Kaveri breaking into falls.",
    "Chikkaballapura": "Nandi Hills at sunrise, night treks to Skandagiri and a thousand-year-old temple.",
    "Chikkamagaluru": "Karnataka's coffee country - Mullayanagiri, Hebbe Falls and shola forest.",
    "Chitradurga": "Seven rings of fort walls built into granite hills, and a town of heroic legend.",
    "Dakshina Kannada": "Coastal temples, fishing harbours and sunsets over the Arabian Sea.",
    "Davanagere": "The Tungabhadra confluence, Hoysala temples and benne dosa.",
    "Dharwad": "Hindustani music, Lingayat monasteries and the twin city of Hubballi.",
    "Gadag": "Lakkundi's temples and stepwells, the finest Kalyani Chalukyan carving in the state.",
    "Hassan": "Belur, Halebidu and Shravanabelagola - the Hoysala and Jain heartland.",
    "Haveri": "Hangal's pillared temples, Bankapura's fort and blackbuck on the plains.",
    "Kalaburagi": "Bahmani forts, a great Sufi dargah and the Buddha Vihar.",
    "Kodagu": "Coffee, mist and the Kaveri's source, with elephant camps on the river.",
    "Kolar": "Ancient temples, the Antara Gange spring and the old gold fields.",
    "Koppal": "Hill forts and the Itagi temple, with Hampi on the doorstep.",
    "Mandya": "Srirangapatna, Ranganathittu's birds and the Brindavan Gardens at dusk.",
    "Mysuru": "The palace city - Chamundi Hills, markets and Dasara.",
    "Raichur": "Forts on the Tungabhadra and the Ashokan edict at Maski.",
    "Ramanagara": "Silk, lacquer toys, the Savandurga monolith and the Sholay hills.",
    "Shivamogga": "Jog Falls, Agumbe's rainforest and the Malnad of Kuvempu.",
    "Tumakuru": "Devarayanadurga's forest, Madhugiri's rock fort and Siddaganga.",
    "Udupi": "The Krishna temple, St. Mary's Island and eight kilometres of coast.",
    "Uttara Kannada": "Gokarna, Yana, Murudeshwar and the Kali river's forests.",
    "Vijayapura": "Adil Shahi Bijapur - Gol Gumbaz, Ibrahim Rauza and the great cannon.",
    "Vijayanagara": "Hampi, the Vijayanagara capital, and the Tungabhadra dam.",
    "Yadgir": "Quiet forts and the Buddhist stupa at Kanaganahalli.",
}

SAMPLE_REVIEW_COMMENTS = [
    "Well maintained and easy to reach. We spent longer here than planned.",
    "Beautiful in the monsoon. Carry good shoes if you plan to walk.",
    "The guide made all the difference - ask questions, they know the stories.",
    "Go early in the morning; by noon it gets crowded and hot.",
]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def ticket_price(entry_fee):
    """Turn an entry-fee string into a demo ticket price."""
    if not entry_fee or "free" in entry_fee.lower():
        return 0.0
    m = re.search(r"(?:Rs|₹)\s*(\d+)", entry_fee)
    if m:
        return float(m.group(1))
    return 50.0


def main():
    from app import create_app
    from db import execute, get_db, init_schema, query

    app = create_app()
    with app.app_context():
        init_schema()
        random.seed(7)

        # ---------- languages -------------------------------------------
        for code, name, native in (("en", "English", "English"),
                                   ("hi", "Hindi", "हिन्दी"),
                                   ("kn", "Kannada", "ಕನ್ನಡ")):
            if not query("SELECT 1 FROM languages WHERE code = ?", (code,), one=True):
                execute("INSERT INTO languages (code, name, native) VALUES (?,?,?)",
                        (code, name, native))

        # ---------- districts -------------------------------------------
        for d in DISTRICTS:
            if not query("SELECT 1 FROM districts WHERE name = ?", (d,), one=True):
                execute("INSERT INTO districts (name, slug, region, description) VALUES (?,?,?,?)",
                        (d, slugify(d), REGIONS.get(d, ""), DISTRICT_BLURB.get(d, "")))
        districts = {r["name"]: r["id"] for r in query("SELECT id, name FROM districts")}

        # ---------- destinations + images --------------------------------
        enrichment_path = BASE / "data" / "enrichment.json"
        enrichment = json.load(open(enrichment_path)) if enrichment_path.exists() else {}
        added = 0
        for d in all_destinations():
            if query("SELECT 1 FROM destinations WHERE slug = ?", (d["slug"],), one=True):
                continue
            enr = enrichment.get(d["name"], {})
            lat = enr.get("lat") or d["lat"]
            lng = enr.get("lng") or d["lng"]
            dest_id = execute(
                """INSERT INTO destinations
                   (name, slug, district_id, category, description, location, latitude, longitude,
                    best_time, entry_fee, timings, activities, nearby, travel_info, duration,
                    ticket_price, featured, active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                (d["name"], d["slug"], districts[d["district"]], d["category"],
                 d["description"], d["location"], lat, lng, d["best_time"], d["entry_fee"],
                 d["timings"], "|".join(d["activities"]), "|".join(d["nearby"]),
                 d["travel_info"], d["duration"], ticket_price(d["entry_fee"]),
                 1 if d["name"] in (
                     "Jog Falls", "Mysore Palace", "Hampi Virupaksha", "Badami Cave Temples",
                     "Gol Gumbaz", "Abbey Falls", "Nandi Hills", "Murudeshwar Temple",
                     "Chitradurga Fort", "Belur Chennakeshava Temple", "Om Beach, Gokarna",
                     "Brindavan Gardens, KRS") else 0))
            for i, url in enumerate(enr.get("images", [])[:4]):
                execute("INSERT INTO destination_images (destination_id, image_url, sort_order) VALUES (?,?,?)",
                        (dest_id, url, i))
            added += 1
        print("destinations added:", added)

        # ---------- homestays + images -----------------------------------
        dest_images = query("""SELECT d.district_id, i.image_url FROM destination_images i
                               JOIN destinations d ON d.id = i.destination_id
                               ORDER BY d.district_id, i.sort_order""")
        pool = {}
        for row in dest_images:
            pool.setdefault(row["district_id"], []).append(row["image_url"])

        for (name, district, price, rooms, guests, facilities, address, rating, desc) in HOMESTAYS:
            slug = slugify(name)
            if query("SELECT 1 FROM homestays WHERE slug = ?", (slug,), one=True):
                continue
            did = districts[district]
            imgs = pool.get(did, [])
            lat = lng = None
            row = query("SELECT latitude, longitude FROM destinations WHERE district_id = ? AND latitude IS NOT NULL LIMIT 1", (did,), one=True)
            if row:
                lat, lng = row["latitude"], row["longitude"]
            hid = execute(
                """INSERT INTO homestays
                   (name, slug, district_id, description, address, latitude, longitude,
                    price_per_night, rooms_available, max_guests, checkin_time, checkout_time,
                    facilities, contact_name, contact_phone, contact_email, rating, active, is_sample)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,1)""",
                (name, slug, did, desc, "%s, %s district, Karnataka" % (address, district),
                 lat, lng, price, rooms, guests, "12:00 PM", "11:00 AM", facilities,
                 "Host", "+91 90000 00000", "stay@example.com", rating))
            for i, url in enumerate(imgs[:3]):
                execute("INSERT INTO homestay_images (homestay_id, image_url, sort_order) VALUES (?,?,?)",
                        (hid, url, i))
            execute("""INSERT INTO rooms (homestay_id, room_type, price, capacity, total_rooms)
                       VALUES (?,?,?,?,?)""", (hid, "Deluxe double", price, 2, max(1, rooms // 2)))
            execute("""INSERT INTO rooms (homestay_id, room_type, price, capacity, total_rooms)
                       VALUES (?,?,?,?,?)""", (hid, "Family room", round(price * 1.6), 4, 2))

        # ---------- guides -----------------------------------------------
        for (name, district, langs, exp, fee, phone, rating, bio) in GUIDES:
            if query("SELECT 1 FROM tour_guides WHERE name = ?", (name,), one=True):
                continue
            execute("""INSERT INTO tour_guides
                       (name, district_id, languages, experience, fee_per_day, phone, email,
                        bio, photo_url, rating, active, is_sample)
                       VALUES (?,?,?,?,?,?,?,?,?,?,1,1)""",
                    (name, districts.get(district), langs, exp, fee, phone,
                     "guide@example.com", bio, None, rating))

        # ---------- admin + demo user ------------------------------------
        from flask import current_app
        if not query("SELECT 1 FROM admins LIMIT 1"):
            execute("INSERT INTO admins (full_name, email, password_hash, role) VALUES (?,?,?,?)",
                    ("Site Administrator", current_app.config["DEFAULT_ADMIN_EMAIL"],
                     generate_password_hash(current_app.config["DEFAULT_ADMIN_PASSWORD"]), "superadmin"))
        if not query("SELECT 1 FROM users WHERE email = ?",
                     (current_app.config["DEFAULT_DEMO_USER_EMAIL"],), one=True):
            execute("""INSERT INTO users (full_name, email, mobile, password_hash, district, gender)
                       VALUES (?,?,?,?,?,?)""",
                    ("Demo Traveller", current_app.config["DEFAULT_DEMO_USER_EMAIL"],
                     "9876543210",
                     generate_password_hash(current_app.config["DEFAULT_DEMO_USER_PASSWORD"]),
                     "Bengaluru Urban", "Prefer not to say"))

        # ---------- reviews ----------------------------------------------
        if not query("SELECT 1 FROM reviews LIMIT 1"):
            users = query("SELECT id, full_name FROM users")
            uid = users[0]["id"] if users else None
            if uid:
                dests = {r["name"]: r["id"] for r in query("SELECT id, name FROM destinations")}
                for (who, stars, dest_name, text) in REVIEWS:
                    if dest_name in dests:
                        execute("""INSERT INTO reviews (user_id, destination_id, rating, comment, status)
                                   VALUES (?,?,?,?,'Approved')""", (uid, dests[dest_name], stars, text))
                for r in query("SELECT id FROM destinations ORDER BY RANDOM() LIMIT 24"):
                    execute("""INSERT INTO reviews (user_id, destination_id, rating, comment, status)
                               VALUES (?,?,?,?,'Approved')""",
                            (uid, r["id"], random.choice([4, 4, 5, 5, 3]),
                             random.choice(SAMPLE_REVIEW_COMMENTS)))

        # ---------- site content -----------------------------------------
        defaults = {
            "travel_tips": "Carry cash for small towns and forest gates.|Book safari slots and homestays well ahead in season.|Karnataka's coast is at its best from November to February.|Monsoon (June-September) is the time for waterfalls, not beaches.|Most temples ask visitors to remove footwear and cover shoulders.",
            "emergency": "Police: 100|Ambulance: 108|Fire: 101|Tourist helpline: 1363|Karnataka Tourism: 080-2235 2828",
        }
        for k, v in defaults.items():
            if not query("SELECT 1 FROM site_content WHERE key = ?", (k,), one=True):
                execute("INSERT INTO site_content (key, value) VALUES (?,?)", (k, v))

        print("seed complete")
        print("  districts :", len(query("SELECT id FROM districts")))
        print("  destinations:", len(query("SELECT id FROM destinations")))
        print("  images    :", len(query("SELECT id FROM destination_images")))
        print("  homestays :", len(query("SELECT id FROM homestays")))
        print("  guides    :", len(query("SELECT id FROM tour_guides")))
        print("  admin     :", app.config["DEFAULT_ADMIN_EMAIL"],
              "/", app.config["DEFAULT_ADMIN_PASSWORD"])


if __name__ == "__main__":
    main()
