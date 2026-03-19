#!/usr/bin/env bash
# Submit all integration test URLs to the crawllmer API.
# Usage: ./scripts/submit-inttest.sh [category]
#   category: a, b, c, or all (default: all)

set -euo pipefail

API="${CRAWLLMER_API:-http://localhost:8000}"
CATEGORY="${1:-all}"

submit() {
    local url="$1"
    local id="$2"
    local result
    result=$(curl -s --max-time 10 -X POST "$API/api/v1/crawls" \
        -H 'Content-Type: application/json' \
        -d "{\"url\":\"$url\"}" 2>/dev/null) || true

    if echo "$result" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        echo "$id  $url  -> queued"
    else
        echo "$id  $url  -> FAILED ($result)"
    fi
}

# Category A: Sites with llms.txt
if [[ "$CATEGORY" == "all" || "$CATEGORY" == "a" ]]; then
    echo "=== Category A: Sites with llms.txt ==="
    submit "https://nextjs.org"       "A1"
    submit "https://vite.dev"         "A3"
    submit "https://docs.retool.com"  "A5"
    submit "https://uploadcare.com"   "A6"
    submit "https://mariadb.com"      "A7"
fi

# Category B: Sites with sitemap, no llms.txt
if [[ "$CATEGORY" == "all" || "$CATEGORY" == "b" ]]; then
    echo "=== Category B: Sitemap only ==="
    submit "https://docs.python.org"            "B1"
    submit "https://flask.palletsprojects.com"  "B2"
    submit "https://expressjs.com"              "B3"
    submit "https://jquery.com"                 "B4"
fi

# Category C: No llms.txt, no sitemap
if [[ "$CATEGORY" == "all" || "$CATEGORY" == "c" ]]; then
    echo "=== Category C: Nothing (spider fallback) ==="
    submit "https://httpbin.org"  "C2"
fi

echo ""
echo "All submitted. Check status with: make crawl-status"
echo "Verbose:                          make crawl-status ARGS=\"-v\""
