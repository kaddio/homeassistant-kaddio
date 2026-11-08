#!/usr/bin/env bash
# Regenerates the Home Assistant brand images from the vector sources in brand/.
# Needs rsvg-convert (brew install librsvg / apt install librsvg2-bin).
set -euo pipefail
cd "$(dirname "$0")/.."
out=custom_components/kaddio/brand
mkdir -p "$out"
tmp=$(mktemp -d)
sed 's/fill="black"/fill="white"/g' brand/kaddio-symbol.svg > "$tmp/symbol-dark.svg"
sed 's/fill="black"/fill="white"/g' brand/kaddio-logotype.svg > "$tmp/logotype-dark.svg"

# icon: square, 256 and 512 (@2x); logo: landscape, height 256 and 512 (@2x)
render() { rsvg-convert -h "$3" "$1" -o "$2"; }
render brand/kaddio-symbol.svg "$out/icon.png" 256
render brand/kaddio-symbol.svg "$out/icon@2x.png" 512
render "$tmp/symbol-dark.svg" "$out/dark_icon.png" 256
render "$tmp/symbol-dark.svg" "$out/dark_icon@2x.png" 512
render brand/kaddio-logotype.svg "$out/logo.png" 256
render brand/kaddio-logotype.svg "$out/logo@2x.png" 512
render "$tmp/logotype-dark.svg" "$out/dark_logo.png" 256
render "$tmp/logotype-dark.svg" "$out/dark_logo@2x.png" 512
cp "$out/icon.png" brand/icon.png
rm -rf "$tmp"
