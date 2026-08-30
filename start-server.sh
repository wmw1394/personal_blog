#!/usr/bin/env bash
# Script to launch Hugo development server with Blowfish theme
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HUGO_BIN="${SCRIPT_DIR}/../bin/hugo"

if [ ! -f "$HUGO_BIN" ]; then
    HUGO_BIN="hugo"
fi

echo "🚀 Starting Hugo Development Server with Blowfish Theme..."
echo "📍 Access your blog at http://localhost:1313/"
echo ""

"$HUGO_BIN" server --source "$SCRIPT_DIR" -D --bind 0.0.0.0 --port 1313
