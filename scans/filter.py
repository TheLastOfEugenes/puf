import json, sys
from pathlib import Path
from collections import Counter

# ── Filters ────────────────────────────────────────────────
FILTERED_STATUS_CODES = [
    404, 301
]

def apply_filters(result):
    if result.get('status') in FILTERED_STATUS_CODES:
        return False
    return True
# ────────────────────────────────────────────────────────────

def filter_results(results):
    if not results:
        return results

    fingerprints = Counter(
        (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0))
        for r in results
    )

    dominant = fingerprints.most_common(1)[0][0]
    dominant_count = fingerprints.most_common(1)[0][1]

    if dominant_count <= 1000 or dominant_count <= len(results) * 0.5:
        return results

    outliers = [r for r in results if
        (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0)) != dominant]

    return outliers if outliers else [results[0]]


def process_file(input_path):
    input_path = Path(input_path)
    output_path = input_path.with_name(input_path.stem + '_filtered.json')

    with open(input_path) as f:
        data = json.load(f)

    results = data.get('results', data) if isinstance(data, dict) else data

    kept = [r for r in results if apply_filters(r)]
    kept = filter_results(kept)

    if isinstance(data, dict) and 'results' in data:
        output = {**data, 'results': kept}
    else:
        output = kept

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    return str(output_path)

process_file(sys.argv[1])