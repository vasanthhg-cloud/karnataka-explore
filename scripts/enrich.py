# -*- coding: utf-8 -*-
"""Fetch real photographs + coordinates for every destination from Wikipedia.

Writes data/enrichment.json : {destination name: {images:[urls], lat, lng,
wiki_url, extract}}. Image URLs are normalised to 1280px thumbnails on
upload.wikimedia.org, which is the size bucket the CDN serves reliably.
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from data import all_destinations

API = "https://en.wikipedia.org/w/api.php"
UA = "KarnatakaExploreCollegeProject/1.0 (educational student project)"
BAD = re.compile(r"(map|locator|logo|icon|flag|seal|stamp|diagram|coat.of.arms|"
                 r"\.svg|\.tif|\.gif|\.pdf|\.ogg|\.webm|\.ogv|location|blank|"
                 r"commons-logo|edit|ambox|question|\.ogg|graph|chart)", re.I)


def post(params, tries=5):
    params = dict(params, format="json", formatversion="2")
    data = urllib.parse.urlencode(params).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(API, data=data, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                time.sleep(0.5)
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(3 * (i + 1))
                continue
            raise
        except Exception as e:  # network hiccup
            last = e
            time.sleep(2 * (i + 1))
    raise last


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def norm(url):
    """Normalise a Wikimedia thumb URL to a reliable 1280px upload.wikimedia URL."""
    if not url:
        return None
    url = url.split("?")[0]
    url = url.replace("//thumb.wikimedia.org/", "//upload.wikimedia.org/")
    m = re.match(r"(https://upload\.wikimedia\.org/.+/thumb/.+?)/(?:\d+)?px-([^/]+)$", url)
    if m:
        return "%s/1280px-%s" % (m.group(1), m.group(2))
    if "/thumb/" not in url:  # original file, build a thumb path from its md5 layout
        m2 = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(\w)/(\w\w)/(.+)$", url)
        if m2:
            return ("https://upload.wikimedia.org/wikipedia/commons/thumb/%s/%s/%s/1280px-%s"
                    % (m2.group(1), m2.group(2), m2.group(3), m2.group(3)))
    return url


def resolve(titles):
    """titles: list of wiki titles -> {title: page dict}"""
    out = {}
    for group in chunks(titles, 20):
        res = post({"action": "query", "redirects": "1",
                    "prop": "pageimages|coordinates|extracts",
                    "piprop": "thumbnail", "pithumbsize": "1280", "colimit": "50",
                    "exintro": "1", "explaintext": "1", "exsentences": "3",
                    "titles": "|".join(group)})
        if "error" in res:
            print("  ! api error:", res["error"].get("info"), flush=True)
        q = res.get("query", {})
        alias = {}
        for n in q.get("normalized", []) or []:
            alias[n["from"]] = n["to"]
        for r in q.get("redirects", []) or []:
            alias[r["from"]] = r["to"]
        pages = {p["title"]: p for p in q.get("pages", [])}
        for t in group:
            key = alias.get(t, t)
            key = alias.get(key, key)
            out[t] = pages.get(key) or {}
    return out


def pages_files(page_titles):
    """{page title: [File:...]} for a batch of pages."""
    out = {}
    for group in chunks(page_titles, 10):
        res = post({"action": "query", "redirects": "1", "prop": "images", "imlimit": "25",
                    "titles": "|".join(group)})
        q = res.get("query", {})
        alias = {}
        for n in q.get("normalized", []) or []:
            alias[n["from"]] = n["to"]
        for r in q.get("redirects", []) or []:
            alias[r["from"]] = r["to"]
        pages = {p["title"]: p for p in q.get("pages", [])}
        for t in group:
            key = alias.get(t, t)
            key = alias.get(key, key)
            p = pages.get(key) or {}
            out[t] = [im["title"] for im in p.get("images", []) if not BAD.search(im["title"])][:4]
    return out


def file_urls(files):
    out = {}
    for group in chunks(files, 25):
        res = post({"action": "query", "prop": "imageinfo", "iiprop": "url|mime|size",
                    "iiurlwidth": "1280", "titles": "|".join(group)})
        for p in res.get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [{}])[0]
            if p.get("missing") or not ii:
                continue
            if not str(ii.get("mime", "")).startswith("image/"):
                continue
            if (ii.get("width") or 0) < 500 or (ii.get("height") or 0) < 350:
                continue
            out[p["title"]] = norm(ii.get("thumburl") or ii.get("url"))
    return out


def main():
    dests = all_destinations()
    titles = sorted({d["wiki"] for d in dests})
    pages = resolve(titles)
    print("pass1: %d pages resolved" % len(pages), flush=True)

    real = [(t, pages[t]["title"]) for t in titles
            if pages.get(t) and not pages[t].get("missing") and pages[t].get("title")]
    by_page = pages_files([pt for _, pt in real])
    files_by_title, allfiles = {}, set()
    for t, pt in real:
        fs = by_page.get(pt, [])
        files_by_title[t] = fs
        allfiles.update(fs)
    print("pass2: %d files from %d pages" % (len(allfiles), len(files_by_title)), flush=True)

    urls = file_urls(sorted(allfiles))
    print("pass3: %d files resolved" % len(urls), flush=True)

    out = {}
    for d in dests:
        p = pages.get(d["wiki"]) or {}
        imgs = []
        th = norm((p.get("thumbnail") or {}).get("source"))
        if th:
            imgs.append(th)
        for f in files_by_title.get(d["wiki"], []):
            u = urls.get(f)
            if u and u not in imgs:
                imgs.append(u)
        co = p.get("coordinates") or []
        out[d["name"]] = {
            "images": imgs[:4],
            "lat": co[0]["lat"] if co else None,
            "lng": co[0]["lon"] if co else None,
            "wiki_url": ("https://en.wikipedia.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))) if p.get("title") else None,
            "extract": p.get("extract"),
        }
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "enrichment.json")
    json.dump(out, open(path, "w"), indent=1)
    thin = [k for k, v in out.items() if len(v["images"]) < 3]
    noco = [k for k, v in out.items() if not v["lat"]]
    print("\nTOTAL %d | <3 images: %d | no coords: %d" % (len(out), len(thin), len(noco)))
    print("thin:", thin)
    print("nocoords:", noco)


if __name__ == "__main__":
    main()
