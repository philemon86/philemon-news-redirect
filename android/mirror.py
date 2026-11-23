#!/usr/bin/env python3
"""Build-time mirror of public Soonsoon Bible assets. No app runtime network access."""
import json
import posixpath
import re
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlsplit

BASE = "https://www.philemon.com.tw/soonsoonbible/"
OUTPUT = Path(__file__).resolve().parent / "app/src/main/assets/web"
OUTPUT.mkdir(parents=True, exist_ok=True)
downloaded = set()
total_bytes = 0

def grab(relative):
    global total_bytes
    relative = urlsplit(relative).path.lstrip("/")
    relative = posixpath.normpath(relative)
    if relative.startswith("../") or relative == "..":
        raise ValueError("Unsafe path: " + relative)
    if relative in downloaded:
        return (OUTPUT / relative).read_bytes()
    url = urljoin(BASE, relative)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SoonsoonBibleOfflineBuild"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Empty asset " + relative)
    destination = OUTPUT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    downloaded.add(relative)
    total_bytes += len(data)
    print("MIRROR", relative, len(data), flush=True)
    return data

html = grab("index.html").decode("utf-8")
# Remove Google Analytics. Offline builds never transmit usage data.
html = re.sub(r'<script[^>]*ga4-unified\\.js[^>]*></script>', '', html, flags=re.I)
(OUTPUT / "index.html").write_text(html, encoding="utf-8")

for path in ("style.css", "favicon.svg", "app.js", "search-worker.js", "core.js", "books.js", "chinese.js", "language.js"):
    grab(path)

# Follow all relative ES module imports, including bundled Traditional/Simplified conversion.
queue = [f for f in downloaded if f.endswith(".js")]
seen_js = set()
while queue:
    filename = queue.pop(0)
    if filename in seen_js:
        continue
    seen_js.add(filename)
    source = (OUTPUT / filename).read_text(encoding="utf-8")
    for src in re.findall(r'''['"]((?:\\./|\\.\\./)[^'"]+\\.js(?:\\?[^'"]*)?)['"]''', source):
        name = posixpath.normpath(posixpath.join(posixpath.dirname(filename), urlsplit(src).path))
        if name not in downloaded:
            grab(name)
        if name not in seen_js:
            queue.append(name)

# Replace network analytics module with the same exports but zero network requests.
telemetry = OUTPUT / "telemetry.js"
telemetry.write_text(
    "export const API = '';\\n"
    "export function track() {}\\n"
    "export function newSearch() { return 'offline'; }\\n"
    "export function safeQuery() { return ''; }\\n",
    encoding="utf-8")
print("OFFLINE telemetry disabled")

manifest = json.loads(grab("data/manifest.json"))
books = manifest.get("books", {})
if len(books) != 66:
    raise AssertionError(f"Expected 66 books, got {len(books)}")
for key, info in books.items():
    relative = "data/" + info["file"]
    json.loads(grab(relative))
print("CHECKED", len(books), "book datasets")
full_bible = grab("bible.csv")
if len(full_bible) < 1000000:
    raise AssertionError(f"Bible CSV unexpectedly short: {len(full_bible)} bytes")
print("CHECKED full-text global search CSV:", len(full_bible), "bytes")

# Download local CSS resources if the website references any.
css = (OUTPUT / "style.css").read_text(encoding="utf-8")
for raw in re.findall(r'url\\(\\s*["\\x27]?([^"\\x27)]+)', css):
    if raw.startswith(("data:", "https:", "http:", "//", "#")):
        print("EXTERNAL_OR_DATA_CSS_URL", raw[:120])
        continue
    grab(posixpath.normpath(posixpath.join("", urlsplit(raw).path)))

for m in re.findall(r'((?:src|href)=["\\x27])(/[^"\\x27]+)', html):
    if "ga4" not in m[1]:
        print("ROOT_PATH_IN_HTML", m[1])

print("COMPLETE", len(downloaded), "web files, source bytes:", total_bytes)
