#!/bin/bash
# Extract Biology Class 11 (Chapters 1-19)
# PDFs are in chapters/biology 11 /
# Note: directory has trailing space
set -e

MAX_RETRIES=3
COOLDOWN=300

# Chapter number : PDF filename
CHAPTERS="1:kebo101.pdf 2:kebo102.pdf 3:kebo103.pdf 4:kebo104.pdf 5:kebo105.pdf 6:kebo106.pdf 7:kebo107.pdf 8:kebo108.pdf 9:kebo109.pdf 10:kebo110.pdf 11:kebo111.pdf 12:kebo112.pdf 13:kebo113.pdf 14:kebo114.pdf 15:kebo115.pdf 16:kebo116.pdf 17:kebo117.pdf 18:kebo118.pdf 19:kebo119.pdf"

PDF_DIR="chapters/biology 11 /"

for entry in $CHAPTERS; do
    ch="${entry%%:*}"
    pdf_name="${entry#*:}"
    output="data/ncert_biology_11_ch${ch}.json"

    if [ -f "$output" ]; then
        echo "⏭  Chapter $ch: already extracted ($output exists), skipping"
        continue
    fi

    echo ""
    echo "============================================"
    echo "  Biology 11 Chapter $ch ($pdf_name)"
    echo "============================================"

    attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))

        uv run python -m extract.pdf_to_json \
            --pdf "${PDF_DIR}${pdf_name}" \
            --curriculum ncert --subject biology --grade 11 \
            --chapter-number "$ch" \
            --textbook-name "Biology" \
            --output "$output" \
            --resume

        if [ $? -eq 0 ]; then
            echo "✅ Chapter $ch done!"
            rm -f "data/ncert_biology_11_ch${ch}.progress.json"
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
echo "🎉 Biology 11 extraction complete!"
