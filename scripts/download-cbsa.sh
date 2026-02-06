#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_DIR/data/shapefiles"

mkdir -p "$DATA_DIR/cbsa"

ZIP_FILE="$DATA_DIR/tl_2024_us_cbsa.zip"

echo "Downloading Census TIGER/Line 2024 CBSA shapefile..."
echo "Target: $ZIP_FILE"

# Resumable download (~500 MB)
curl -L -C - -o "$ZIP_FILE" \
  "https://www2.census.gov/geo/tiger/TIGER2024/CBSA/tl_2024_us_cbsa.zip"

echo "Extracting..."
unzip -o "$ZIP_FILE" -d "$DATA_DIR/cbsa/"

echo "Done. Files in $DATA_DIR/cbsa/:"
ls -lh "$DATA_DIR/cbsa/"
