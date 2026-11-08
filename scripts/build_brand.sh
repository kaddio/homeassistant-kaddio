#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
output_dir=custom_components/kaddio/brand
work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT

mkdir -p "$output_dir"

make_white_copy() {
  sed 's/fill="black"/fill="white"/g' "$1" > "$2"
}

render_png() {
  local kind=$1 source_svg=$2 target_png=$3 size=$4
  local raw_png="$work_dir/raw.png"
  rsvg-convert -h 2048 "$source_svg" -o "$raw_png"
  python3 scripts/fit_brand_image.py "$kind" "$raw_png" "$target_png" "$size"
}

make_white_copy branding/kaddio-symbol.svg "$work_dir/symbol-white.svg"
make_white_copy branding/kaddio-logotype.svg "$work_dir/logotype-white.svg"

render_png icon branding/kaddio-symbol.svg "$output_dir/icon.png" 256
render_png icon branding/kaddio-symbol.svg "$output_dir/icon@2x.png" 512
render_png icon "$work_dir/symbol-white.svg" "$output_dir/dark_icon.png" 256
render_png icon "$work_dir/symbol-white.svg" "$output_dir/dark_icon@2x.png" 512
render_png logo branding/kaddio-logotype.svg "$output_dir/logo.png" 256
render_png logo branding/kaddio-logotype.svg "$output_dir/logo@2x.png" 512
render_png logo "$work_dir/logotype-white.svg" "$output_dir/dark_logo.png" 256
render_png logo "$work_dir/logotype-white.svg" "$output_dir/dark_logo@2x.png" 512
