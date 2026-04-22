import json
from pathlib import Path
from collections import Counter


def run_custom_filter(input_path, smart_enabled=True, smart_limit=1000,
                      status_codes=[], word_counts=[], lengths=[]):
    input_path = Path(input_path)
    output_path = input_path.with_name(input_path.stem + '_custom_filtered.json')

    with open(input_path) as f:
        data = json.load(f)

    results = data.get('results', data) if isinstance(data, dict) else data

    if smart_enabled and results:
        fingerprints = Counter(
            (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0))
            for r in results
        )
        dominant_fps = set(
            fp for fp, count in fingerprints.items()
            if count > smart_limit and count > len(results) * 0.5
        )
        if dominant_fps:
            outliers = [r for r in results if
                (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0))
                not in dominant_fps]
            results = outliers if outliers else [results[0]]

    results = [r for r in results if
        r.get('status') not in status_codes and
        r.get('words') not in word_counts and
        r.get('length') not in lengths]

    output = {**data, 'results': results} if isinstance(data, dict) and 'results' in data else results

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    return str(output_path)