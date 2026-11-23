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
# Online ranking dashboard and bookstore links cannot work in a networkless APK.
html, removed_links = re.subn(
    r'''<a\b[^>]*href=["'](?:\./rankings\.html|https://www\.pbooks\.com\.tw/?)["'][^>]*>.*?</a>''',
    "", html, flags=re.I | re.S)
assert removed_links == 2, f"Unexpected external links count: {removed_links}"
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

# Match the Android offline behavior in the built-in help and shared search URL.
app = OUTPUT / "app.js"
app_source = app.read_text(encoding="utf-8")
app_source = app_source.replace(
    "我們記錄匿名搜尋與複製彙總，改善查經體驗；不建立個人檔案，不在統計資料庫保存姓名、email 或 IP。短暫搜尋識別碼用於計算轉換並在兩天內清除。",
    "離線版完全不收集或傳送搜尋、複製及其他使用統計。")
app_source = app_source.replace(
    "GA4 用於整體流量、裝置及互動分析。搜尋內容不送入 GA4；網址中的搜尋詞也會從 GA4 頁面資料移除。",
    "聖經資料與搜尋程式均已內建，開啟飛航模式也能使用。")
app_source = app_source.replace(
    "navigator.clipboard.writeText(location.href)",
    "navigator.clipboard.writeText(location.href.replace('https://appassets.androidplatform.net/assets/web/', 'https://www.philemon.com.tw/soonsoonbible/'))")
app_source, replaced = re.subn(
    r"c\.append\(d,field\('匿名使用統計'.*?location\.reload\(\);\}\)\);",
    "c.append(d);", app_source, flags=re.S)
assert replaced == 1, "Analytics preference not found"
app.write_text(app_source, encoding="utf-8")

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
