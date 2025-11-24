#!/bin/bash
# Build script for obfuscating JavaScript
# CSS остаётся открытым для удобного редактирования
# Usage: ./build.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATIC_DIR="$SCRIPT_DIR/apps/static"

echo "=== Building frontend assets ==="
echo ""
echo "CSS: остаётся открытым (style.css) - редактируйте напрямую"
echo ""

# Check if npm dependencies are installed
if [ ! -d "$SCRIPT_DIR/node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install terser javascript-obfuscator --save-dev
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
echo "  app.js: $JS_ORIG -> $JS_MIN bytes (obfuscated)"

echo ""
echo "=== Build complete ==="
echo ""
echo "Что редактировать:"
echo "  HTML:   apps/static/index.html      (без пересборки)"
echo "  CSS:    apps/static/css/style.css   (без пересборки)"
echo "  JS:     apps/static/js/app.js       (требует ./build.sh)"
