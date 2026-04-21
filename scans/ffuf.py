import json, sys, subprocess, re
from pathlib import Path

def run_ffuf():
    target = sys.argv[1]
    hostname = sys.argv[2]
    wordlist = sys.argv[3]
    outfile = sys.argv[4]
    subs = (sys.argv[5] == "True")

    if not subs:
        ffuf_command = ['ffuf', '-k', '-c', '-mc', 'all',
                        '-u', target + "/FUZZ", '-w', wordlist, '-o', outfile, '-of', 'json']
    else:
        ffuf_command = ['ffuf', '-k', '-c', '-mc', 'all',
                        '-u', target, '-w', wordlist, '-o', outfile, '-of', 'json',
                        '-H', f"Host: FUZZ.{hostname}"]

    proc = subprocess.Popen(
        ffuf_command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True
    )

    for line in proc.stderr:
        m = re.search(r'\[(\d+)/(\d+)\]', line)
        if m:
            done, total = int(m.group(1)), int(m.group(2))
            pct = int((done / total) * 100) if total else 0
            print(f"PROGRESS:{pct}", flush=True)

    proc.wait()

    # ── run filter after scan completes ──
    filter_script = Path(__file__).parent / 'filter.py'
    subprocess.run(['python3', str(filter_script), outfile])
    # ─────────────────────────────────────

    if proc.returncode != 0:
        print("PROGRESS:error", flush=True)
        sys.exit(1)

run_ffuf()