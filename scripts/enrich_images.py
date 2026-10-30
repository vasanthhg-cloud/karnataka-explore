# -*- coding: utf-8 -*-
"""Add gallery photographs to data/enrichment.json using the Wikimedia REST
media-list endpoint (one request per destination, paced)."""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from data import all_destinations

UA = "KarnatakaExploreCollegeProject/1.0 (student project; contact: harishhg2012@gmail.com)"
BAD = re.compile(r"(map|locator|logo|icon|flag|seal|stamp|diagram|coat.of.arms|"
                 r"\.svg|\.tif|\.gif|\.pdf|\.ogg|\.webm|\.ogv|location|blank|"
                 r"commons-logo|question|graph|chart|banner|collage|montage|"
                 r"panorama|signboard|plaque|inscription)", re.I)
PATH = os.path.join(HERE, "..", "data", "enrichment.json")


def norm(url):
    if not url:
        return None
    url = url.split("?")[0]
    url = url.replace("//thumb.wikimedia.org/", "//upload.wikimedia.org/")
    m = re.match(r"(https://upload\.wikimedia\.org/.+/thumb/.+?)/(?:\d+)?px-([^/]+)$", url)
    if m:
        return "%s/1280px-%s" % (m.group(1), m.group(2))
    m2 = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(\w)/(\w\w)/(.+)$", url)
    if m2 and "/thumb/" not in url:
        return ("https://upload.wikimedia.org/wikipedia/commons/thumb/%s/%s/%s/1280px-%s"
                % (m2.group(1), m2.group(2), m2.group(3), m2.group(3)))
    return url


def fetch(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503, 500):
                time.sleep(6 * (i + 1))
                continue
            return None
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def images_for(wiki):
    t = urllib.parse.quote(wiki.replace(" ", "_"))
    data = fetch("https://en.wikipedia.org/api/rest_v1/page/media-list/" + t)
    out = []
    if not data:
        return out
    for it in data.get("items", []):
        if it.get("type") != "image":
            continue
        if BAD.search(it.get("title", "")):
            continue
        ss = it.get("srcset") or []
        if not ss:
            continue
        u = norm(ss[0].get("src"))
        if u and u not in out:
            out.append(u)
        if len(out) >= 4:
            break
    return out


def main():
    data = json.load(open(PATH))
    dests = all_destinations()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    done = 0
    for d in dests:
        rec = data.setdefault(d["name"], {"images": [], "lat": None, "lng": None,
                                          "wiki_url": None, "extract": None})
        if len(rec.get("images", [])) >= 3:
            continue
        if done >= limit:
            break
        imgs = images_for(d["wiki"])
        merged = list(rec.get("images") or [])
        for u in imgs:
            if u not in merged:
                merged.append(u)
        rec["images"] = merged[:4]
        data[d["name"]] = rec
        done += 1
        print("%-45s %d imgs" % (d["name"][:44], len(rec["images"])), flush=True)
        time.sleep(1.4)
    json.dump(data, open(PATH, "w"), indent=1)
    thin = [k for k, v in data.items() if len(v.get("images", [])) < 3]
    print("\nprocessed %d this run | total %d | still <3 images: %d" % (done, len(data), len(thin)))
    print(thin)


if __name__ == "__main__":
    main()
