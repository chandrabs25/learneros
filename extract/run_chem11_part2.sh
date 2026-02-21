#!/bin/bash
# Extract Chemistry Class 11 — Part 2 (Units 7-9)
# PDFs are in chapters/chemistry 11 part 2/
set -e

MAX_RETRIES=3
COOLDOWN=300

# Unit number : PDF filename
CHAPTERS="7:kech201.pdf 8:kech202.pdf 9:kech203.pdf"

for entry in $CHAPTERS; do
    ch="${entry%%:*}"
    pdf_name="${entry#*:}"
    output="data/ncert_chemistry_11_ch${ch}.json"

    if [ -f "$output" ]; then
        echo "⏭  Unit $ch: already extracted ($output exists), skipping"
        continue
    fi

    echo ""
    echo "============================================"
    echo "  Chemistry 11 Unit $ch ($pdf_name)"
    echo "============================================"

    attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))

        uv run python -m extract.pdf_to_json \
            --pdf "chapters/chemistry 11 part 2/${pdf_name}" \
            --curriculum ncert --subject chemistry --grade 11 \
            --chapter-number "$ch" \
            --textbook-name "Chemistry Part II" \
            --output "$output" \
            --resume

        if [ $? -eq 0 ]; then
            echo "✅ Unit $ch done!"
            rm -f "data/ncert_chemistry_11_ch${ch}.progress.json"
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
echo "🎉 Chemistry 11 Part 2 extraction complete!"
