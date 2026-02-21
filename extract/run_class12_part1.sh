#!/bin/bash
# Extract Physics Class 12 — Part 1 (Chapters 1-8)
# PDFs are in chapters/ root directory with naming physics_11_chN.pdf
set -e

MAX_RETRIES=3
COOLDOWN=300

CHAPTERS="1:physics_11_ch1.pdf 2:physics_11_ch2.pdf 3:physics_11_ch3.pdf 4:physics_11_ch4.pdf 5:physics_11_ch5.pdf 6:physics_11_ch6.pdf 7:physics_11_ch7.pdf 8:physics_11_ch8.pdf"

for entry in $CHAPTERS; do
    ch="${entry%%:*}"
    pdf_name="${entry#*:}"
    output="data/ncert_physics_12_ch${ch}.json"

    if [ -f "$output" ]; then
        echo "⏭  Chapter $ch: already extracted ($output exists), skipping"
        continue
    fi

    echo ""
    echo "============================================"
    echo "  Physics 12 Chapter $ch ($pdf_name)"
    echo "============================================"

    attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))

        uv run python -m extract.pdf_to_json \
            --pdf "chapters/${pdf_name}" \
            --curriculum ncert --subject physics --grade 12 \
            --chapter-number "$ch" \
            --textbook-name "Physics Part I" \
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
echo "🎉 Physics 12 Part 1 extraction complete!"
