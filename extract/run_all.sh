#!/bin/bash
# Extract chapters 2-8 sequentially with auto-resume.
# If a chapter fails, it retries after a cooldown period,
# resuming from the progress file.

MAX_RETRIES=3
COOLDOWN=300  # 5 minutes between retries

for ch in 2 3 4 5 6 7 8; do
    output="data/ncert_physics_11_ch${ch}.json"

    # Skip if already fully extracted
    if [ -f "$output" ]; then
        echo "⏭  Chapter $ch: already extracted ($output exists), skipping"
        continue
    fi

    echo ""
    echo "============================================"
    echo "  Chapter $ch"
    echo "============================================"

    attempt=0
    while [ $attempt -lt $MAX_RETRIES ]; do
        attempt=$((attempt + 1))

        uv run python -m extract.pdf_to_json \
            --pdf "chapters/physics_11_ch${ch}.pdf" \
            --curriculum ncert \
            --subject physics \
            --grade 11 \
            --chapter-number "$ch" \
            --textbook-name "Physics Part I" \
            --output "$output" \
            --resume

        if [ $? -eq 0 ]; then
            echo "✅ Chapter $ch done!"
            # Clean up progress file
            rm -f "data/ncert_physics_11_ch${ch}.progress.json"
            break
        else
            if [ $attempt -lt $MAX_RETRIES ]; then
                echo ""
                echo "⚠️  Chapter $ch failed (attempt $attempt/$MAX_RETRIES). Cooling down ${COOLDOWN}s before retry..."
                sleep $COOLDOWN
            else
                echo ""
                echo "❌ Chapter $ch failed after $MAX_RETRIES attempts. Moving to next chapter."
            fi
        fi
    done
done

echo ""
echo "🎉 Batch extraction complete!"
