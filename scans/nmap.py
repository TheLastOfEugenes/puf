import sys, subprocess

# run the nmap script
def run_nmap():
    target = sys.argv[1]
    outfile = sys.argv[2]
    print(f"[*] Starting nmap on {target}", flush=True)

    nmap_command = ['nmap', '-sCV', '-T4', '-v', '-p-', target, '-oX', outfile]

    proc = subprocess.Popen(nmap_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        print(line, end='', flush=True)
    proc.wait()

    if proc.returncode != 0:
        print(f"[!] nmap failed with code {proc.returncode}", flush=True)
        sys.exit(1)

run_nmap()