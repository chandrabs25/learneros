#!/bin/bash
# Extract Chemistry Class 12 (Units 1-10)
# All PDFs in a single directory: chapters/chemistry 12/
# lech101-105 = Part 1 (Units 1-5), lech201-205 = Part 2 (Units 6-10)
set -e

MAX_RETRIES=3
COOLDOWN=300

# Unit number : PDF filename
CHAPTERS="1:lech101.pdf 2:lech102.pdf 3:lech103.pdf 4:lech104.pdf 5:lech105.pdf 6:lech201.pdf 7:lech202.pdf 8:lech203.pdf 9:lech204.pdf 10:lech205.pdf"

for entry in $CHAPTERS; do
    ch="${entry%%:*}"
    pdf_name="${entry#*:}"
    output="data/ncert_chemistry_12_ch${ch}.json"

    if [ -f "$output" ]; then
        echo "⏭  Unit $ch: already extracted ($output exists), skipping"
        continue
    fi

    echo ""
    echo "============================================"
    echo "  Chemistry 12 Unit $ch ($pdf_name)"
    echo "============================================"

    attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))

        uv run python -m extract.pdf_to_json \
            --pdf "chapters/chemistry 12/${pdf_name}" \
            --curriculum ncert --subject chemistry --grade 12 \
            --chapter-number "$ch" \
            --textbook-name "Chemistry" \
            --output "$output" \
            --resume

        if [ $? -eq 0 ]; then
            echo "✅ Unit $ch done!"
            rm -f "data/ncert_chemistry_12_ch${ch}.progress.json"
            break
        else
            if [ $attempt -lt $MAX_RETRIES ]; then
                echo ""
                echo "⚠️  Unit $ch failed (attempt $attempt/$MAX_RETRIES). Cooling down ${COOLDOWN}s..."
                sleep $COOLDOWN
            else
                echo "❌ Unit $ch failed after $MAX_RETRIES attempts. Moving to next."
            fi
        fi
    done
done

echo ""
echo "🎉 Chemistry 12 extraction complete!"
