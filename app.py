from flask import Flask, jsonify, request, Response, stream_with_context, render_template
import subprocess, json, os
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

working_path = Path.cwd()
base_path = working_path/'puf'
base_path.mkdir(parents=True, exist_ok=True)
server_base_path = Path(__file__).parent

# url = "http://this.target.scan:3333/api"
# parsed = urlparse(url)
#
# scheme   = parsed.scheme    # "http"
# hostname   = parsed.hostname  # "this.target.scan"
# port     = parsed.port      # 3333
# path     = parsed.path      # "/api"

#base
#  target (ip to machine, scan nmap)
#    hostname (domain name, subdomains scan)
#      service (web service, subdomains scan)
#        - files
#        - dirs
#      service
#        - files
#        - dirs
#      - subs
#    domain
#      service
#        - files
#      - subs
#    - nmap
#  target
#    - nmap

app = Flask(__name__)

# tree walk, allows to show updated path 
# files are obtained by querying /path/to/target as it corresponds to the tree structure
@app.route('/api/tree')
def file_tree():
    tree = {}
    for root, dirs, files in os.walk('puf'):
        tree[root] = {'dirs': dirs, 'files': files}
    return jsonify(tree)

@app.route('/api/results/<target>')
def nmap_results(target):
    print("fetching nmap", target)
    target_path = base_path / target
    if not target_path.exists():
        return jsonify([])
    nmap_path = target_path / 'nmap.xml'
    if not nmap_path.exists() or not nmap_path.read_text().strip():
        return jsonify([])

    try:
        tree = ET.parse(nmap_path)
        root = tree.getroot()
        hosts = []
        for host in root.findall('host'):
            addr = host.find('address')
            ports = []
            for port in host.findall('.//port'):
                service = port.find('service')
                ports.append({
                    'port':     port.get('portid'),
                    'protocol': port.get('protocol'),
                    'state':    port.find('state').get('state'),
                    'service':  service.get('name') if service is not None else '',
                    'version':  service.get('product', '') + ' ' + service.get('version', '') if service is not None else ''
                })
            hosts.append({
                'ip':    addr.get('addr') if addr is not None else '',
                'ports': ports
            })
        return jsonify(hosts)
    except ET.ParseError:
        return jsonify({'error': 'XML not ready yet'}), 204
    
@app.route('/api/results/<target>/<hostname>')
def subs_ffuf_results(target, hostname):
    print("fetching ffuf subs", target, hostname)

    target_path = base_path / target
    if not target_path.exists():
        return jsonify([])

    hostname_path = target_path / hostname
    if not hostname_path.exists():
        return jsonify([])

    subs_ffuf_path = hostname_path / 'subs.json'
    if not subs_ffuf_path.exists() or not subs_ffuf_path.read_text().strip():
        return jsonify([])

    return jsonify(json.load(open(subs_ffuf_path)))

@app.route('/api/results/<target>/<hostname>/<service>/files')
def files_ffuf_results(target, hostname, service):
    print("fetching ffuf files", target, hostname, service)

    target_path = base_path / target
    if not target_path.exists():
        return jsonify([])

    hostname_path = target_path / hostname
    if not hostname_path.exists():
        return jsonify([])
    
    service_path = hostname_path / service
    if not service_path.exists():
        return jsonify([])

    files_ffuf_path = service_path / 'files.json'
    if not files_ffuf_path.exists() or not files_ffuf_path.read_text().strip():
        return jsonify([])

    return jsonify(json.load(open(files_ffuf_path)))

@app.route('/api/results/<target>/<hostname>/<service>/dirs')
def dirs_ffuf_results(target, hostname, service):
    print("fetching ffuf dirs", target, hostname, service)

    target_path = base_path / target
    if not target_path.exists():
        return jsonify([])

    hostname_path = target_path / hostname
    if not hostname_path.exists():
        return jsonify([])
    
    service_path = hostname_path / service
    if not service_path.exists():
        return jsonify([])

    dirs_ffuf_path = service_path / 'dirs.json'
    if not dirs_ffuf_path.exists() or not dirs_ffuf_path.read_text().strip():
        return jsonify([])

    return jsonify(json.load(open(dirs_ffuf_path)))

# scans are started by posting to a single endpoint with the necessary values
# app.py
@app.route('/api/scan/nmap')
def stream_nmap():
    target = request.args.get('target')
    url = target
    if '://' not in url:
        url = '%s%s' % ('http://', url)
    parsed = urlparse(url)
    
    outpath = base_path/f"{parsed.hostname}"
    outpath.mkdir(parents=True, exist_ok=True)
    outfile = outpath/'nmap.xml'
    
    def generate():
        nmap_script_path = server_base_path/'scans/nmap.py'
        process = subprocess.Popen(
            ['python3', str(nmap_script_path), target, str(outfile)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True
        )
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.rstrip(chr(10))}\n\n"
        process.stdout.close()
        process.wait()
        yield "data: [DONE]\n\n"
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/scan/ffuf')
def stream_ffuf():
    target = request.args.get('target')
    type = request.args.get('type')
    url = target
    if '://' not in url:
        url = '%s%s' % ('http://', url)
    parsed = urlparse(url)

    if not parsed.port:
        if parsed.scheme == "http":
            port = 80
        elif parsed.scheme == "https":
            port = 443
        else:
            port = -1
    else:
        port = parsed.port

    if type == "files" or type == "dirs":
        outpath = base_path/f"{parsed.hostname}"/f"{parsed.hostname}"/f"{parsed.scheme}_{port}"
        outpath.mkdir(parents=True, exist_ok=True)
        path = parsed.path
        if path != "":
            if path[0] == '/':
                path = path[1:]
            if path[-1] != '/':
                path = path+'/'
            path = path.replace('/', '_')
        if type == "files":
            outfile = outpath/f"{path}files.json"
            wordlist = "/usr/share/wordlists/seclists/Discovery/Web-Content/raft-large-files-lowercase.txt"
        else:
            outfile = outpath/f"{path}dirs.json"
            wordlist = "/usr/share/wordlists/seclists/Discovery/Web-Content/raft-large-directories-lowercase.txt"
    elif type == "subs":
        outpath = base_path/f"{parsed.hostname}"/f"{parsed.hostname}"
        outpath.mkdir(parents=True, exist_ok=True)
        outfile = outpath/"subs.json"
        wordlist = "/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt"
    else:
        return jsonify({'error': 'invalid type, must be files, dirs or subs'}), 400

    def generate():
        ffuf_script_path = server_base_path/'scans/ffuf.py'
        process = subprocess.Popen(
            ['python3', str(ffuf_script_path), target, parsed.hostname, wordlist, str(outfile), str(type=="subs")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True
        )
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.rstrip(chr(10))}\n\n"
        process.stdout.close()
        process.wait()
        yield "data: [DONE]\n\n"
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/')
def index():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5454, threaded=True)