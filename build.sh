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
    npm install terser clean-css-cli javascript-obfuscator --save-dev
fi

# Step 1: Minify JavaScript with terser
echo "Step 1: Minifying JavaScript with terser..."
npx terser "$STATIC_DIR/js/app.js" \
    --compress \
    --mangle \
    --output "$STATIC_DIR/js/app.terser.js"

# Step 2: Obfuscate with javascript-obfuscator for maximum protection
echo "Step 2: Obfuscating JavaScript..."
npx javascript-obfuscator "$STATIC_DIR/js/app.terser.js" \
    --output "$STATIC_DIR/js/app.min.js" \
    --compact true \
    --control-flow-flattening true \
    --control-flow-flattening-threshold 0.5 \
    --dead-code-injection false \
    --debug-protection false \
    --identifier-names-generator hexadecimal \
    --rename-globals false \
    --self-defending false \
    --string-array true \
    --string-array-encoding base64 \
    --string-array-threshold 0.5 \
    --unicode-escape-sequence false

# Clean up temp file
rm -f "$STATIC_DIR/js/app.terser.js"

JS_ORIG=$(wc -c < "$STATIC_DIR/js/app.js")
JS_MIN=$(wc -c < "$STATIC_DIR/js/app.min.js")
echo "  app.js: $JS_ORIG -> $JS_MIN bytes"

# Minify CSS with clean-css
echo "Step 3: Minifying CSS..."
npx cleancss -o "$STATIC_DIR/css/style.min.css" "$STATIC_DIR/css/style.css"

CSS_ORIG=$(wc -c < "$STATIC_DIR/css/style.css")
CSS_MIN=$(wc -c < "$STATIC_DIR/css/style.min.css")
echo "  style.css: $CSS_ORIG -> $CSS_MIN bytes ($(( 100 - CSS_MIN * 100 / CSS_ORIG ))% reduction)"

echo ""
echo "=== Build complete ==="
echo "Files generated:"
echo "  - $STATIC_DIR/js/app.min.js (obfuscated)"
echo "  - $STATIC_DIR/css/style.min.css"
