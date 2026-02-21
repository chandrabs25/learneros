#!/bin/bash
# Extract Physics 12 Part 2 (Chapters 9-14) from PDFs
set -e

MAX_RETRIES=3
COOLDOWN=300  # 5 minutes

# Chapter number and corresponding PDF filename pairs
CHAPTERS="9:leph201.pdf 10:leph202.pdf 11:leph203.pdf 12:leph204.pdf 13:leph205.pdf 14:leph206.pdf"

for entry in $CHAPTERS; do
    ch="${entry%%:*}"
    pdf_name="${entry##*:}"
    output="data/ncert_physics_12_ch${ch}.json"
    pdf="chapters/physics 12 part 2/${pdf_name}"

    # Skip if already fully extracted
    if [ -f "$output" ]; then
        echo "⏭  Chapter $ch: already extracted ($output exists), skipping"
        continue
    fi

    echo ""
    echo "============================================"
    echo "  Chapter $ch ($pdf_name)"
    echo "============================================"

    attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))

        uv run python -m extract.pdf_to_json \
            --pdf "$pdf" \
            --curriculum ncert --subject physics --grade 12 \
            --chapter-number "$ch" \
            --textbook-name "Physics Part II" \
            --output "$output" \
            --resume

        if [ $? -eq 0 ]; then
            echo "✅ Chapter $ch done!"
            rm -f "data/ncert_physics_12_ch${ch}.progress.json"
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
echo "🎉 Part 2 extraction complete!"
