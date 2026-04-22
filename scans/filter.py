import json, sys
from pathlib import Path
from collections import Counter

# ── Filters ────────────────────────────────────────────────
# Edit this list freely to add/remove status codes to drop
FILTERED_STATUS_CODES = [
    404, 301
]

# Add more filter functions here as needed, each takes a result dict
# and returns True if the result should be KEPT
def apply_filters(result):
    if result.get('status') in FILTERED_STATUS_CODES:
        return False
    return True
# ────────────────────────────────────────────────────────────

def filter_results(results):
    # Find dominant fingerprint across ALL results (status + size + words + lines)
    fingerprints = Counter(
        (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0))
        for r in results
    )

    dominant = fingerprints.most_common(1)[0][0]
    dominant_count = fingerprints.most_common(1)[0][1]

    # Only filter if dominant fingerprint appears >1000 times AND represents >50% of results
    if dominant_count <= 1000 or dominant_count <= len(results) * 0.5:
        return results

    # Keep only results that don't match the dominant fingerprint
    outliers = [r for r in results if
        (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0)) != dominant]

    return outliers if outliers else [results[0]]


if __name__ == '__main__':
    filter_results(sys.argv[1])