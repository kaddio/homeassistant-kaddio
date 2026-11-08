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
  local source_svg=$1 target_png=$2 height=$3
  rsvg-convert -h "$height" "$source_svg" -o "$target_png"
}

make_white_copy branding/kaddio-symbol.svg "$work_dir/symbol-white.svg"
make_white_copy branding/kaddio-logotype.svg "$work_dir/logotype-white.svg"

render_png branding/kaddio-symbol.svg "$output_dir/icon.png" 256
render_png branding/kaddio-symbol.svg "$output_dir/icon@2x.png" 512
render_png "$work_dir/symbol-white.svg" "$output_dir/dark_icon.png" 256
render_png "$work_dir/symbol-white.svg" "$output_dir/dark_icon@2x.png" 512
render_png branding/kaddio-logotype.svg "$output_dir/logo.png" 256
render_png branding/kaddio-logotype.svg "$output_dir/logo@2x.png" 512
render_png "$work_dir/logotype-white.svg" "$output_dir/dark_logo.png" 256
render_png "$work_dir/logotype-white.svg" "$output_dir/dark_logo@2x.png" 512
