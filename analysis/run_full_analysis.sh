#!/bin/bash
set -e
cd /home/irjudson/Projects/Seestar/seestar-analysis

echo "=== Step 1: Decompile + analyze + compare all app versions ==="
uv run seestar-analysis run-all

echo ""
echo "=== Step 2: Firmware analysis for all versions ==="
uv run seestar-analysis analyze-fw --all

echo ""
echo "=== Step 3: Firmware comparisons for new consecutive pairs ==="
PAIRS=(
  "1.18.0 1.19.0"
  "1.19.0 1.20.0"
  "1.20.0 1.20.2"
  "1.20.2 2.0.0"
  "2.0.0 2.1.0"
  "2.1.0 2.2.0"
  "2.2.0 2.2.1"
  "2.2.1 2.3.0"
)

for pair in "${PAIRS[@]}"; do
  v1=$(echo $pair | cut -d' ' -f1)
  v2=$(echo $pair | cut -d' ' -f2)
  echo "  Comparing firmware $v1 vs $v2..."
  uv run seestar-analysis compare-fw "$v1" "$v2" || echo "  [warn] compare-fw $v1 $v2 failed"
done

echo ""
echo "=== All done ==="
