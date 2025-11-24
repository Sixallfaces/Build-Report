#!/bin/bash
# Build script for minifying and obfuscating frontend assets
# Usage: ./build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATIC_DIR="$SCRIPT_DIR/apps/static"

echo "=== Building frontend assets ==="

# Check if npm dependencies are installed
if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install terser clean-css-cli --save-dev
fi

# Minify JavaScript with terser (with obfuscation)
echo "Minifying JavaScript..."
npx terser "$STATIC_DIR/js/app.js" \
    --compress \
    --mangle \
    --mangle-props regex=/^_/ \
    --output "$STATIC_DIR/js/app.min.js"

JS_ORIG=$(wc -c < "$STATIC_DIR/js/app.js")
JS_MIN=$(wc -c < "$STATIC_DIR/js/app.min.js")
echo "  app.js: $JS_ORIG -> $JS_MIN bytes ($(( 100 - JS_MIN * 100 / JS_ORIG ))% reduction)"

# Minify CSS with clean-css
echo "Minifying CSS..."
npx cleancss -o "$STATIC_DIR/css/style.min.css" "$STATIC_DIR/css/style.css"

CSS_ORIG=$(wc -c < "$STATIC_DIR/css/style.css")
CSS_MIN=$(wc -c < "$STATIC_DIR/css/style.min.css")
echo "  style.css: $CSS_ORIG -> $CSS_MIN bytes ($(( 100 - CSS_MIN * 100 / CSS_ORIG ))% reduction)"

echo ""
echo "=== Build complete ==="
echo "Files generated:"
echo "  - $STATIC_DIR/js/app.min.js"
echo "  - $STATIC_DIR/css/style.min.css"
