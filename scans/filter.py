import json, sys
from pathlib import Path
from collections import Counter

# ── Smart Filtering ─────────────────────────────────────────
SMART_FILTER_ENABLED = True
SMART_FILTER_MIN_COUNT = 1000      # minimum occurrences to consider a fingerprint dominant
SMART_FILTER_MIN_RATIO = 0.5       # minimum ratio of total results to trigger filtering
# ────────────────────────────────────────────────────────────

# ── Post-filters ────────────────────────────────────────────
FILTERED_STATUS_CODES = [404]
FILTERED_WORD_COUNTS  = []         # e.g. [12, 15] to drop results with 12 or 15 words
FILTERED_LENGTHS      = []         # e.g. [142, 500] to drop results of those byte lengths
# ────────────────────────────────────────────────────────────


def smart_filter(results):
    if not SMART_FILTER_ENABLED or not results:
        return results

    fingerprints = Counter(
        (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0))
        for r in results
    )

    # Find ALL dominant fingerprints exceeding both thresholds
    dominant_fps = set(
        fp for fp, count in fingerprints.items()
        if count > SMART_FILTER_MIN_COUNT and count > len(results) * SMART_FILTER_MIN_RATIO
    )

    if not dominant_fps:
        return results

    outliers = [r for r in results if
        (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0))
        not in dominant_fps]

    return outliers if outliers else [results[0]]


def apply_filters(result):
    if result.get('status') in FILTERED_STATUS_CODES:
        return False
    if result.get('words') in FILTERED_WORD_COUNTS:
        return False
    if result.get('length') in FILTERED_LENGTHS:
        return False
    return True


def filter_results(results):
    results = smart_filter(results)
    results = [r for r in results if apply_filters(r)]
    return results


def process_file(input_path):
    input_path = Path(input_path)
    output_path = input_path.with_name(input_path.stem + '_filtered.json')

    with open(input_path) as f:
        data = json.load(f)

    results = data.get('results', data) if isinstance(data, dict) else data

    kept = filter_results(results)

    if isinstance(data, dict) and 'results' in data:
        output = {**data, 'results': kept}
    else:
        output = kept

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    return str(output_path)