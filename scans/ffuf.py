import sys, subprocess

# run ffuf script
def run_ffuf():
    target = sys.argv[1]
    hostname = sys.argv[2]
    wordlist = sys.argv[3]
    outfile = sys.argv[4]
    subs = (bool(sys.argv[5]) == "True")
    
    print(f"[*] Starting nmap on {target}", flush=True)



    if not subs:
        ffuf_command = ['ffuf', '-k', '-c', '-mc', 'all', '-u', target+"/FUZZ", '-w', wordlist, '-o', outfile]
    else:
        ffuf_command = ['ffuf', '-k', '-c', '-mc', 'all', '-u', target, '-w', wordlist, '-o', outfile, '-H', f"'Host: FUZZ.{hostname}'"]

    proc = subprocess.Popen(ffuf_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        print(line, end='', flush=True)
    proc.wait()

    if proc.returncode != 0:
        print(f"[!] nmap failed with code {proc.returncode}", flush=True)
        sys.exit(1)

run_ffuf()