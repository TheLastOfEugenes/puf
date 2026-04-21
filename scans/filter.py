import json, sys
from pathlib import Path

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

def filter_results(input_path):
    input_path = Path(input_path)
    raw = json.load(open(input_path))
    results = raw.get('results', []) if isinstance(raw, dict) else raw

    filtered = [r for r in results if apply_filters(r)]

    output_path = input_path.parent / (input_path.stem + '_filtered.json')
    json.dump({'results': filtered}, open(output_path, 'w'), indent=2)
    print(f"[*] Filtered {len(results) - len(filtered)} results → {output_path}", flush=True)

if __name__ == '__main__':
    filter_results(sys.argv[1])