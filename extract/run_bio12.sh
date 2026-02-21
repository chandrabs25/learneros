#!/bin/bash
# Extract Biology Class 12 (Chapters 1-13)
# PDFs are in chapters/biology 12/
set -e

MAX_RETRIES=3
COOLDOWN=300

# Chapter number : PDF filename
CHAPTERS="1:lebo101.pdf 2:lebo102.pdf 3:lebo103.pdf 4:lebo104.pdf 5:lebo105.pdf 6:lebo106.pdf 7:lebo107.pdf 8:lebo108.pdf 9:lebo109.pdf 10:lebo110.pdf 11:lebo111.pdf 12:lebo112.pdf 13:lebo113.pdf"

PDF_DIR="chapters/biology 12/"

for entry in $CHAPTERS; do
    ch="${entry%%:*}"
    pdf_name="${entry#*:}"
    output="data/ncert_biology_12_ch${ch}.json"

    if [ -f "$output" ]; then
        echo "⏭  Chapter $ch: already extracted ($output exists), skipping"
        continue
    fi

    echo ""
    echo "============================================"
    echo "  Biology 12 Chapter $ch ($pdf_name)"
    echo "============================================"

    attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))

        uv run python -m extract.pdf_to_json \
            --pdf "${PDF_DIR}${pdf_name}" \
            --curriculum ncert --subject biology --grade 12 \
            --chapter-number "$ch" \
            --textbook-name "Biology" \
            --output "$output" \
            --resume

        if [ $? -eq 0 ]; then
            echo "✅ Chapter $ch done!"
            rm -f "data/ncert_biology_12_ch${ch}.progress.json"
            break
        else
            if [ $attempt -lt $MAX_RETRIES ]; then
                echo ""
                echo "⚠️  Chapter $ch failed (attempt $attempt/$MAX_RETRIES). Cooling down ${COOLDOWN}s..."
                sleep $COOLDOWN
            else
                echo "❌ Chapter $ch failed after $MAX_RETRIES attempts. Moving to next."
            fi
        fi
    done
done

echo ""
echo "🎉 Biology 12 extraction complete!"
