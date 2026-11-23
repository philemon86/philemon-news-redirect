#!/usr/bin/env python3
"""Mirror complete public Soonsoon Bible data at build time; app has no internet permission."""
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
    relative = posixpath.normpath(urlsplit(relative).path.lstrip("/"))
    if relative.startswith("../") or relative == "..":
        raise ValueError("Unsafe path: " + relative)
    if relative in downloaded:
        return (OUTPUT / relative).read_bytes()
    request = urllib.request.Request(urljoin(BASE, relative),
               headers={"User-Agent": "Mozilla/5.0 SoonsoonBibleOfflineBuild"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    if not data:
        raise RuntimeError("Empty asset: " + relative)
    dest = OUTPUT / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    downloaded.add(relative)
    total_bytes += len(data)
    print("MIRROR", relative, len(data), flush=True)
    return data

html = grab("index.html").decode("utf-8")
html = re.sub(r'<script[^>]*ga4-unified\.js[^>]*></script>', '', html, flags=re.I)
(OUTPUT / "index.html").write_text(html, encoding="utf-8")

for name in ("style.css","favicon.svg","app.js","search-worker.js","core.js","books.js","chinese.js","language.js"):
    grab(name)

queue = [f for f in downloaded if f.endswith(".js")]
seen_js = set()
while queue:
    filename = queue.pop(0)
    if filename in seen_js: continue
    seen_js.add(filename)
    source = (OUTPUT / filename).read_text(encoding="utf-8")
    for src in re.findall(r'''['"]((?:\./|\.\./)[^'"]+\.js(?:\?[^'"]*)?)['"]''', source):
        path = posixpath.normpath(posixpath.join(posixpath.dirname(filename), urlsplit(src).path))
        if path not in downloaded: grab(path)
        if path not in seen_js: queue.append(path)

# Local no-op telemetry keeps original interface while eliminating all network calls.
(OUTPUT / "telemetry.js").write_text(
    "export const API = '';\n"
    "export function track() {}\n"
    "export function newSearch() { return 'offline'; }\n"
    "export function safeQuery() { return ''; }\n",
    encoding="utf-8")
print("OFFLINE telemetry disabled")

manifest = json.loads(grab("data/manifest.json"))
books = manifest.get("books", {})
if len(books) != 66:
    raise AssertionError(f"Expected 66 books, got {len(books)}")
for book_id, info in books.items():
    json.loads(grab("data/" + info["file"]))
print("CHECKED", len(books), "book datasets")
full_bible = grab("bible.csv")
if len(full_bible) < 1000000:
    raise AssertionError(f"Bible CSV unexpectedly short: {len(full_bible)} bytes")
print("CHECKED full-text global search CSV:", len(full_bible), "bytes")

css = (OUTPUT / "style.css").read_text(encoding="utf-8")
for src in re.findall(r'''url\(\s*["']?([^"')]+)''', css):
    if src.startswith(("data:", "https:", "http:", "//", "#")):
        print("SKIPPED_EXTERNAL_CSS_URL", src[:120])
    else:
        grab(posixpath.normpath(urlsplit(src).path))

print("COMPLETE", len(downloaded), "web files, source bytes:", total_bytes)
