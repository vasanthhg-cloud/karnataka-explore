# -*- coding: utf-8 -*-
"""Destination master data for Karnataka Explore."""
import re
from .destinations_data import PART_1
from .destinations_data2 import PART_2
from .destinations_data3 import PART_3

ALL_PART = {}
ALL_PART.update(PART_1)
ALL_PART.update(PART_2)
ALL_PART.update(PART_3)

DISTRICTS = [
    "Bagalkote", "Ballari", "Belagavi", "Bengaluru Rural", "Bengaluru Urban",
    "Bidar", "Chamarajanagara", "Chikkaballapura", "Chikkamagaluru", "Chitradurga",
    "Dakshina Kannada", "Davanagere", "Dharwad", "Gadag", "Hassan", "Haveri",
    "Kalaburagi", "Kodagu", "Kolar", "Koppal", "Mandya", "Mysuru", "Raichur",
    "Ramanagara", "Shivamogga", "Tumakuru", "Udupi", "Uttara Kannada",
    "Vijayapura", "Vijayanagara", "Yadgir",
]

CATEGORIES = [
    "Waterfalls", "Hill Stations", "Beaches", "Historical Places", "Temples",
    "Forts", "Wildlife Sanctuaries", "National Parks", "Museums",
    "Adventure Tourism", "Nature and Eco-Tourism", "Cultural Heritage",
]

FIELDS = ["name", "category", "wiki", "location", "description", "best_time",
          "entry_fee", "timings", "activities", "nearby", "travel_info",
          "duration", "lat", "lng"]


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s


def all_destinations():
    out = []
    for district in DISTRICTS:
        for row in ALL_PART.get(district, []):
            d = dict(zip(FIELDS, row))
            d["district"] = district
            d["slug"] = _slug(d["name"])
            out.append(d)
    return out
