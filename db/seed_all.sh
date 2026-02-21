#!/bin/bash
# Seed all chapter JSONs from data/ into Neo4j.
#
# Usage:
#   bash db/seed_all.sh
#
# Prerequisites:
#   - Neo4j running (configured via .env: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
#   - Chapter JSON files in data/ directory

set -e

echo ""
echo "🌱 Seeding all chapters into Neo4j..."
echo ""

# First, normalize all JSON files
echo "🔧 Step 1: Normalizing JSON files..."
uv run python -m extract.normalize_json

echo ""
echo "📥 Step 2: Seeding into Neo4j..."
echo ""

for json_file in data/ncert_*.json; do
    # Skip progress files
    if [[ "$json_file" == *".progress."* ]]; then
        continue
    fi

    if [ -f "$json_file" ]; then
        echo "--------------------------------------------"
        uv run python -m db.seed "$json_file"
    fi
done

echo ""
echo "🎉 All chapters seeded successfully!"
