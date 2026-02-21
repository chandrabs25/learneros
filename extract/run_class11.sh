#!/bin/bash
# Extract Physics Class 11 — Part 1 (Chapters 1-7) + Part 2 (Chapters 8-14)
# Uses GEMINI_API_KEY_2 env var to allow parallel runs with a different API key
set -e

MAX_RETRIES=3
COOLDOWN=300

# Override API key if GEMINI_API_KEY_2 is set
if [ -n "$GEMINI_API_KEY_2" ]; then
    export GEMINI_API_KEY="$GEMINI_API_KEY_2"
    echo "🔑 Using GEMINI_API_KEY_2"
else
    echo "⚠️  No GEMINI_API_KEY_2 set, using default from .env"
fi

# Part 1: keph101-107 → Chapters 1-7
# Part 2: keph201-207 → Chapters 8-14
CHAPTERS="1:keph101.pdf:part1 2:keph102.pdf:part1 3:keph103.pdf:part1 4:keph104.pdf:part1 5:keph105.pdf:part1 6:keph106.pdf:part1 7:keph107.pdf:part1 8:keph201.pdf:part2 9:keph202.pdf:part2 10:keph203.pdf:part2 11:keph204.pdf:part2 12:keph205.pdf:part2 13:keph206.pdf:part2 14:keph207.pdf:part2"

for entry in $CHAPTERS; do
    ch=$(echo "$entry" | cut -d: -f1)
    pdf_name=$(echo "$entry" | cut -d: -f2)
    part=$(echo "$entry" | cut -d: -f3)

    if [ "$part" = "part1" ]; then
        pdf="chapters/physics 11 part 1/${pdf_name}"
        textbook="Physics Part I"
    else
        pdf="chapters/physics 11 part 2/${pdf_name}"
        textbook="Physics Part II"
    fi

    output="data/ncert_physics_11_ch${ch}.json"

    # Skip if already fully extracted
    if [ -f "$output" ]; then
        echo "⏭  Chapter $ch: already extracted ($output exists), skipping"
        continue
    fi

    echo ""
    echo "============================================"
    echo "  Class 11 Chapter $ch ($pdf_name)"
    echo "============================================"

    attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))

        uv run python -m extract.pdf_to_json \
            --pdf "$pdf" \
            --curriculum ncert --subject physics --grade 11 \
            --chapter-number "$ch" \
            --textbook-name "$textbook" \
            --output "$output" \
            --resume

        if [ $? -eq 0 ]; then
            echo "✅ Chapter $ch done!"
            rm -f "data/ncert_physics_11_ch${ch}.progress.json"
            break
        else
            if [ $attempt -lt $MAX_RETRIES ]; then
                echo ""
                echo "⚠️  Chapter $ch failed (attempt $attempt/$MAX_RETRIES). Cooling down ${COOLDOWN}s before retry..."
                sleep $COOLDOWN
            else
                echo "❌ Chapter $ch failed after $MAX_RETRIES attempts. Moving to next chapter."
            fi
        fi
    done
done

echo ""
echo "🎉 Class 11 extraction complete!"
