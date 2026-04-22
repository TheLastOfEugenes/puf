from flask import Flask, jsonify, request, Response, stream_with_context, render_template
import subprocess, json, os
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import shutil

processes = {}
working_path = Path.cwd() # ./
base_path = working_path/'puf' # ./puf
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
#      services
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
    
    url = target
    if not (url.startswith("http://") or url.startswith("https://")):
        url = '%s%s' % ("http://", url)
    parsed = urlparse(url)

    target_path = base_path / parsed.hostname
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
    
@app.route('/api/results/file')
def file_results():
    rel_path = request.args.get('path', '')
    target = (working_path / rel_path).resolve()

    if not str(target).startswith(str(base_path.resolve())):
        return jsonify({'error': 'forbidden'}), 403
    if not target.exists():
        return jsonify([])

    return jsonify(json.load(open(target)))

# scans are started by posting to a single endpoint with the necessary values
# app.py
@app.route('/api/scan/nmap')
def stream_nmap():
    target = request.args.get('target')
    tab_id = request.args.get('tabId')
    url = target
    if not (url.startswith("http://") or url.startswith("https://")):
        url = '%s%s' % ("http://", url)
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
        if tab_id:
            processes[tab_id] = process
        yield f"data: OUTFILE:{str(outfile.relative_to(base_path))}\n\n"
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.rstrip(chr(10))}\n\n"
        process.stdout.close()
        process.wait()
        if tab_id:
            processes.pop(tab_id, None)
        yield "data: [DONE]\n\n"
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/scan/ffuf')
def stream_ffuf():
    target = request.args.get('target')
    type = request.args.get('type')
    tab_id = request.args.get('tabId')
    url = target
    if not (url.startswith("http://") or url.startswith("https://")):
        url = '%s%s' % ("http://", url)
    parsed = urlparse(url)

    print(parsed)

    scheme = parsed.scheme

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
        outfile = outpath/f"{scheme}_subs.json"
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
        if tab_id:
            processes[tab_id] = process
        yield f"data: OUTFILE:{str(outfile.relative_to(base_path))}\n\n"
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.rstrip(chr(10))}\n\n"
        process.stdout.close()
        process.wait()
        if tab_id:
            processes.pop(tab_id, None)
        yield "data: [DONE]\n\n"
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/scan/kill/<tab_id>', methods=['POST'])
def kill_scan(tab_id):
    proc = processes.pop(tab_id, None)
    if proc:
        proc.terminate()
        return jsonify({'ok': True})
    return jsonify({'error': 'not found'}), 404

@app.route('/api/delete', methods=['POST'])
def delete_path():
    data = request.get_json()
    rel_path = data.get('path', '')

    # strip leading 'puf/' since base_path is already pointing to puf/
    if rel_path.startswith('puf/') or rel_path == 'puf':
        rel_path = rel_path[4:]

    target = (base_path / rel_path).resolve()

    # safety check — must be inside base_path
    if not str(target).startswith(str(base_path.resolve())):
        return jsonify({'error': 'forbidden'}), 403

    if not target.exists():
        return jsonify({'error': 'not found'}), 404

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    return jsonify({'ok': True})

@app.route('/')
def index():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5454, threaded=True)