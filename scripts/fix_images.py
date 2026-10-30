# -*- coding: utf-8 -*-
"""Fill in missing gallery photographs.

For each destination still short of three images:
  1. search Wikipedia for the best article and use its media list,
  2. fall back to a Commons geosearch around the destination coordinates,
     which returns photographs actually taken at that place.
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from data import all_destinations

UA = "KarnatakaExploreCollegeProject/1.0 (student project; harishhg2012@gmail.com)"
BAD = re.compile(r"(map|locator|logo|icon|flag|seal|stamp|diagram|coat.of.arms|"
                 r"\.svg|\.tif|\.gif|\.pdf|\.ogg|\.webm|\.ogv|\.webp|location|"
                 r"blank|question|graph|chart|banner|collage|montage|plaque|"
                 r"signboard|disambig|wiktionary|commons-logo|wiki)", re.I)
PATH = os.path.join(HERE, "..", "data", "enrichment.json")


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                d = json.load(r)
            time.sleep(0.9)
            return d
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(5 * (i + 1))
                continue
            return None
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def post(host, params, tries=4):
    params = dict(params, format="json", formatversion="2")
    data = urllib.parse.urlencode(params).encode()
    for i in range(tries):
        try:
            req = urllib.request.Request("https://%s/w/api.php" % host, data=data,
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                d = json.load(r)
            time.sleep(0.9)
            return d
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(5 * (i + 1))
                continue
            return None
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def norm(url):
    if not url:
        return None
    url = url.split("?")[0]
    url = url.replace("//thumb.wikimedia.org/", "//upload.wikimedia.org/")
    m = re.match(r"(https://upload\.wikimedia\.org/.+/thumb/.+?)/(?:\d+)?px-([^/]+)$", url)
    if m:
        return "%s/1280px-%s" % (m.group(1), m.group(2))
    return url


def file_urls(host, files):
    out = {}
    for i in range(0, len(files), 20):
        res = post(host, {"action": "query", "prop": "imageinfo", "iiprop": "url|mime|size",
                          "iiurlwidth": "1280", "titles": "|".join(files[i:i + 20])})
        for p in (res or {}).get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [{}])[0]
            if p.get("missing") or not ii:
                continue
            if not str(ii.get("mime", "")).startswith("image/jpeg") and not str(ii.get("mime", "")).startswith("image/png"):
                continue
            if (ii.get("width") or 0) < 600 or (ii.get("height") or 0) < 400:
                continue
            out[p["title"]] = norm(ii.get("thumburl") or ii.get("url"))
    return out


def media_list(title):
    d = get("https://en.wikipedia.org/api/rest_v1/page/media-list/" + urllib.parse.quote(title.replace(" ", "_")))
    out = []
    for it in (d or {}).get("items", []):
        if it.get("type") != "image" or BAD.search(it.get("title", "")):
            continue
        ss = it.get("srcset") or []
        if ss:
            u = norm(ss[0].get("src"))
            if u and u not in out:
                out.append(u)
    return out


def search_title(name, district):
    res = post("en.wikipedia.org", {"action": "query", "list": "search",
                                    "srsearch": "%s %s Karnataka" % (name, district),
                                    "srlimit": "5"})
    for h in (res or {}).get("query", {}).get("search", []):
        t = h["title"]
        if BAD.search(t) or "disambiguation" in t.lower():
            continue
        return t
    return None


def commons_geo(lat, lng, radius=2500):
    res = post("commons.wikimedia.org", {"action": "query", "list": "geosearch",
                                         "gscoord": "%s|%s" % (lat, lng),
                                         "gsradius": str(radius), "gsnamespace": "6",
                                         "gslimit": "25"})
    files = [g["title"] for g in (res or {}).get("query", {}).get("geosearch", [])
             if not BAD.search(g["title"])]
    if not files:
        return []
    urls = file_urls("commons.wikimedia.org", files[:12])
    return [u for u in urls.values() if u]


def main():
    data = json.load(open(PATH))
    dests = {d["name"]: d for d in all_destinations()}
    todo = [k for k, v in data.items() if len(v.get("images", [])) < 3]
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    for name in todo[:limit]:
        rec = data[name]
        d = dests[name]
        imgs = list(rec.get("images") or [])
        # 1. better wikipedia article
        t = search_title(d["name"], d["district"])
        if t:
            for u in media_list(t):
                if u not in imgs:
                    imgs.append(u)
            if len(imgs) >= 3 and not rec.get("wiki_url"):
                rec["wiki_url"] = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_"))
        # 2. commons geosearch
        if len(imgs) < 3 and rec.get("lat") and rec.get("lng"):
            for u in commons_geo(rec["lat"], rec["lng"]):
                if u not in imgs:
                    imgs.append(u)
        rec["images"] = imgs[:4]
        print("%-45s %d imgs %s" % (name[:44], len(rec["images"]), "" if t else "(no article)"), flush=True)
        json.dump(data, open(PATH, "w"), indent=1)
    thin = [k for k, v in data.items() if len(v.get("images", [])) < 3]
    print("\nstill <3:", len(thin), thin)


if __name__ == "__main__":
    main()
