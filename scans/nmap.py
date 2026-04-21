import sys, subprocess
from pathlib import Path

def run_nmap():
    target = sys.argv[1]
    outfile = sys.argv[2]
    logfile = Path(outfile).parent / 'nmap.log'

    print(f"[*] Starting nmap on {target}", flush=True)

    nmap_command = ['nmap', '-sCV', '-T4', '-v', '-p-', target, '-oX', outfile]

    proc = subprocess.Popen(nmap_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    with open(logfile, 'w') as log:
        for line in proc.stdout:
            log.write(line)
            log.flush()
            print(line, end='', flush=True)
    proc.wait()

    if proc.returncode != 0:
        print(f"[!] nmap failed with code {proc.returncode}", flush=True)
        sys.exit(1)

run_nmap()