from pathlib import Path

def get_output_path(input_path, custom=False):
    input_path = Path(input_path)
    stem = input_path.stem
    for suffix in ('_cs', '_f'):
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    suffix = '_cs' if custom else '_f'
    return input_path.with_name(stem + suffix + '.json')