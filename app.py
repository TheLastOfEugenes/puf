from flask import Flask, jsonify, request, Response, stream_with_context, render_template
import subprocess, json, os, sys
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import shutil
sys.path.insert(0, str(Path(__file__).parent / 'scans'))
from custom_filter import run_custom_filter
import configparser
import shlex
import re

conf = configparser.ConfigParser()
conf.read(Path(__file__).parent / 'puf.conf')

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
# port     = parsed.port      # 3333a
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

conf = configparser.ConfigParser()
conf.read(Path(__file__).parent / 'puf.conf')

commands = {
    'nmap':      conf.get('commands', 'nmap',      fallback=''),
    'fuzz':      conf.get('commands', 'fuzz',      fallback=''),
    'fuzz_subs': conf.get('commands', 'fuzz_subs', fallback=''),
}

def get_auto_filter():
    return conf.getboolean('ffuf', 'auto_filter', fallback=True)

def get_wordlist(type):
    return conf.get('wordlists', type, fallback={
        'files': '/usr/share/wordlists/seclists/Discovery/Web-Content/raft-large-files-lowercase.txt',
        'dirs':  '/usr/share/wordlists/seclists/Discovery/Web-Content/raft-large-directories-lowercase.txt',
        'subs':  '/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt',
    }[type])

def reload_commands():
    conf.read(Path(__file__).parent / 'puf.conf')
    commands['nmap']      = conf.get('commands', 'nmap',      fallback='')
    commands['fuzz']      = conf.get('commands', 'fuzz',      fallback='')
    commands['fuzz_subs'] = conf.get('commands', 'fuzz_subs', fallback='')

# tree walk, allows to show updated path 
# files are obtained by querying /path/to/target as it corresponds to the tree structure
def get_root_domain(hostname):
    import re
    if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
        return hostname  # IP, don't strip
    parts = hostname.split('.')
    return '.'.join(parts[-2:]) if len(parts) > 2 else hostname

@app.route('/api/tree')
def file_tree():
    tree = {}
    for root, dirs, files in os.walk('puf'):
        tree[root] = {'dirs': dirs, 'files': files}
    return jsonify(tree)

@app.route('/api/config/icons')
def config_icons():
    icons = dict(conf['icons']) if 'icons' in conf else {}
    return jsonify(icons)

@app.route('/api/results/<target>')
def nmap_results(target):
    url = target
    if not (url.startswith("http://") or url.startswith("https://")):
        url = 'http://' + url
    parsed = urlparse(url)
    root = get_root_domain(parsed.hostname)

    target_path = base_path / root
    if not target_path.exists():
        return jsonify([])

    # find any xml file instead of hardcoded nmap.xml
    xml_files = list(target_path.glob('*.xml'))
    if not xml_files:
        return jsonify([])
    nmap_path = xml_files[0]

    if not nmap_path.read_text().strip():
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
    offset   = int(request.args.get('offset', 0))
    limit    = int(request.args.get('limit', 500))
    target   = (working_path / rel_path).resolve()

    if not str(target).startswith(str(base_path.resolve())):
        return jsonify({'error': 'forbidden'}), 403
    if not target.exists():
        return jsonify([])

    data    = json.load(open(target))
    results = data.get('results', data) if isinstance(data, dict) else data
    total   = len(results)
    page    = results[offset:offset + limit]

    return jsonify({'results': page, 'total': total, 'offset': offset, 'limit': limit})

@app.route('/api/results/raw')
def raw_file():
    rel_path = request.args.get('path', '')
    target = (working_path / rel_path).resolve()
    if not str(target).startswith(str(base_path.resolve())):
        return jsonify({'error': 'forbidden'}), 403
    if not target.exists():
        return jsonify({'error': 'not found'}), 404
    return target.read_text(errors='replace'), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route('/api/filter', methods=['POST'])
def custom_filter():
    body = request.get_json()
    try:
        output_path = run_custom_filter(
            input_path   = working_path / body['path'],
            smart_enabled= body.get('smart_enabled', True),
            smart_limit  = body.get('smart_limit', 1000),
            status_codes = body.get('status_codes', []),
            word_counts  = body.get('word_counts', []),
            lengths      = body.get('lengths', [])
        )
        return jsonify({'output_path': output_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/commands/get')
def get_commands():
    return jsonify(commands)

@app.route('/api/commands/set', methods=['POST'])
def set_command():
    body = request.get_json()
    key  = body.get('key')
    cmd  = body.get('cmd')
    if key not in commands:
        return jsonify({'error': 'unknown key'}), 400
    commands[key] = cmd
    return jsonify({'ok': True})

@app.route('/api/commands/reset', methods=['POST'])
def reset_commands():
    reload_commands()
    return jsonify({'ok': True})

@app.route('/api/scan/nmap')
def stream_nmap():
    target = request.args.get('target')
    tab_id = request.args.get('tabId')
    url = target if target.startswith('http') else 'http://' + target
    parsed = urlparse(url)
    root = get_root_domain(parsed.hostname)

    outpath = base_path / root
    outpath.mkdir(parents=True, exist_ok=True)
    outfile = outpath / 'nmap.xml'

    def generate():
        cmd = shlex.split(commands['nmap'].format(target=target, outfile=str(outfile)))

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, text=True)
        if tab_id:
            processes[tab_id] = process
        yield f"data: OUTFILE:{str(outfile.relative_to(base_path))}\n\n"
        for line in iter(process.stdout.readline, ''):
            yield f"data: {line.rstrip()}\n\n"
        process.stdout.close()
        process.wait()
        processes.pop(tab_id, None)
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route('/api/scan/ffuf')
def stream_ffuf():
    target = request.args.get('target')
    type   = request.args.get('type')
    tab_id = request.args.get('tabId')
    url = target if target.startswith('http') else 'http://' + target
    parsed = urlparse(url)
    root = get_root_domain(parsed.hostname)

    port = parsed.port or (80 if parsed.scheme == 'http' else 443)
    wordlist = get_wordlist(type)

    if type in ('files', 'dirs'):
        outpath = base_path / root / parsed.hostname / f"{parsed.scheme}_{port}"
        outpath.mkdir(parents=True, exist_ok=True)
        path = (parsed.path or '').lstrip('/').rstrip('/').replace('/', '_')
        outfile = outpath / f"{path}{'files' if type == 'files' else 'dirs'}.json"
    elif type == 'subs':
        outpath = base_path / root / parsed.hostname
        outpath.mkdir(parents=True, exist_ok=True)
        outfile = outpath / f"{parsed.scheme}_subs.json"
    else:
        return jsonify({'error': 'invalid type'}), 400

    def generate():
        if type == 'subs':
            cmd = shlex.split(commands['fuzz_subs'].format(
                target=target,
                hostname=parsed.hostname,
                wordlist=wordlist,
                outfile=str(outfile)
            ))
        else:
            cmd = shlex.split(commands['fuzz'].format(
                target=target,
                wordlist=wordlist,
                outfile=str(outfile)
            ))

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, text=True)
        if tab_id:
            processes[tab_id] = process
        yield f"data: OUTFILE:{str(outfile.relative_to(base_path))}\n\n"
        for line in iter(process.stdout.readline, ''):
            m = re.search(r'\[(\d+)/(\d+)\]', line)
            if m:
                done, total = int(m.group(1)), int(m.group(2))
                pct = int((done / total) * 100) if total else 0
                yield f"data: PROGRESS:{pct}\n\n"
            else:
                yield f"data: {line.rstrip()}\n\n"
        
        process.stdout.close()
        process.wait()
        processes.pop(tab_id, None)

        if get_auto_filter():
            try:
                run_custom_filter(
                    input_path=outfile,
                    smart_enabled=True,
                    smart_limit=1000,
                    status_codes=[],
                    word_counts=[],
                    lengths=[],
                    custom=False
                )
            except Exception as e:
                yield f"data: [filter error: {e}]\n\n"

        yield f"data: AUTO_FILTER:{'true' if get_auto_filter() else 'false'}\n\n"
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
    host = conf.get('server', 'host', fallback='127.0.0.1')
    port = conf.getint('server', 'port', fallback=5454)
    app.run(host=host, port=port, threaded=True)