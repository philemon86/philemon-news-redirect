#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
if [ "$#" -gt 0 ]; then OUT="$1"; else OUT="$ROOT/output"; fi
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT
APP="$BUILD/Payload/SoonsoonBible.app"
mkdir -p "$APP"
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
echo "Building for physical iPhone (arm64), SDK: $SDK"
xcrun swiftc \
    -sdk "$SDK" \
    -target arm64-apple-ios15.0 \
    -swift-version 5 \
    -parse-as-library \
    -O \
    -emit-executable \
    -o "$APP/SoonsoonBible" \
    ios/SoonsoonBible.swift
cp ios/Info.plist "$APP/Info.plist"
cp -R android/app/src/main/assets/web "$APP/web"
# Default to Simplified Chinese on mainland-oriented iOS installs, while
# retaining the user's language preference once switched in the app.
python3 - "$APP/web/language.js" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = "valid(saved)?saved:'zh-Hant'"
assert old in text, "Language preference initialization changed upstream"
path.write_text(text.replace(old, "valid(saved)?saved:'zh-Hans'"), encoding="utf-8")
PY
swift ios/make_icon.swift "$APP/Icon.png"
plutil -lint "$APP/Info.plist"
test -s "$APP/web/bible.csv"
test -s "$APP/web/data/manifest.json"
test -s "$APP/web/search-worker.js"
test -s "$APP/web/vendor/opencc/opencc-1.4.2.js"
# The result still requires the end user's Apple code signing and provisioning.
cd "$BUILD"
zip -qry "$OUT/SoonsoonBible-iOS-UNSIGNED.ipa" Payload
cd "$ROOT"
echo "Created UNSIGNED IPA (requires Apple code signing):"
ls -lh "$OUT/SoonsoonBible-iOS-UNSIGNED.ipa"
