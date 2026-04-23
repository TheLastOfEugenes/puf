import json
from pathlib import Path
from collections import Counter
from utils import get_output_path
import re as re_module

def run_custom_filter(input_path, smart_enabled=True, smart_limit=1000,
                      status_codes=[], word_counts=[], lengths=[], status_codes_keep=False, word_counts_keep=False, lengths_keep=False, regex='', regex_keep=False, custom=True):
    input_path = Path(input_path)
    output_path = get_output_path(input_path, custom)

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
            if count > smart_limit
        )
        if dominant_fps:
            outliers = [r for r in results if
                (r.get('status'), r.get('length', 0), r.get('words', 0), r.get('lines', 0))
                not in dominant_fps]
            results = outliers if outliers else [results[0]]

    results = [r for r in results if
            (not status_codes or (r.get('status') in status_codes) == status_codes_keep) and
            (not word_counts  or (int(r.get('words',  -1)) in [int(x) for x in word_counts])  == word_counts_keep) and
            (not lengths      or (int(r.get('length', -1)) in [int(x) for x in lengths])       == lengths_keep)]

    if regex:
        pattern = re_module.compile(regex)

        def get_text(r):
            return "\n".join([
                str(r.get('content', '')),
                str(r.get('url', '')),
                str(r.get('redirectlocation', '')),
            ])

        if regex_keep:
            print("regex filter by")
            results = [r for r in results if pattern.search(get_text(r))]
        else:
            print("regex filter out")
            results = [r for r in results if not pattern.search(get_text(r))]
            
    output = {**data, 'results': results} if isinstance(data, dict) and 'results' in data else results

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    return str(output_path)