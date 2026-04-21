import sys, subprocess, re

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
        stdout=subprocess.DEVNULL,   # ← no pipe, no buffer, no block
        stderr=subprocess.PIPE,
        text=True
    )

    for line in proc.stderr:
        m = re.search(r'(\d+)\s*/\s*(\d+)', line)
        if m:
            done, total = int(m.group(1)), int(m.group(2))
            pct = int((done / total) * 100) if total else 0
            print(f"PROGRESS:{pct}", flush=True)

    proc.wait()
    if proc.returncode != 0:
        print("PROGRESS:error", flush=True)
        sys.exit(1)

run_ffuf()