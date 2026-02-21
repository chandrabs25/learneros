#!/bin/bash
# Extract Physics Class 11 — Part 2 (Chapters 8-14)
set -e

MAX_RETRIES=3
COOLDOWN=300

CHAPTERS="8:keph201.pdf 9:keph202.pdf 10:keph203.pdf 11:keph204.pdf 12:keph205.pdf 13:keph206.pdf 14:keph207.pdf"

for entry in $CHAPTERS; do
    ch="${entry%%:*}"
    pdf_name="${entry#*:}"
    output="data/ncert_physics_11_ch${ch}.json"

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
            --pdf "chapters/physics 11 part 2/${pdf_name}" \
            --curriculum ncert --subject physics --grade 11 \
            --chapter-number "$ch" \
            --textbook-name "Physics Part II" \
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
echo "🎉 Class 11 Part 2 extraction complete!"
