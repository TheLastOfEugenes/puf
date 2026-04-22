// ── State ─────────────────────────────────────
let tabs = {};
let activeTabId = null;
let counter = 0;
var ICONS = {};
var _filterTargetPath = null;
var _filterTargetName = null;

// ── Tabs ──────────────────────────────────────
function createTab(label, kind) {
  const id = 'tab' + (++counter);
  const tabbar = document.getElementById('tabbar');
  const hint = document.getElementById('tabbar-empty');
  if (hint) hint.remove();

  const tab = document.createElement('div');
  tab.className = 'tab';
  tab.id = 'tabbtn_' + id;
  tab.innerHTML =
    '<span class="tab-dot running" id="dot_' + id + '"></span>' +
    '<span class="tab-label">' + label + '</span>' +
    '<span class="tab-kind">' + kind + '</span>' +
    '<button class="tab-kill btn-ghost" id="kill_' + id + '" onclick="killTab(event,\'' + id + '\')" title="Kill scan">&#x25A0;</button>' +
    '<button class="tab-x" onclick="closeTab(event,\'' + id + '\')">&#x2715;</button>';
  tab.addEventListener('click', function(e) {
    if (!e.target.classList.contains('tab-x') && !e.target.classList.contains('tab-kill')) activateTab(id);
  });
  tabbar.appendChild(tab);

  const pane = document.createElement('div');
  pane.className = 'pane';
  pane.id = 'pane_' + id;
  pane.style.display = 'none';

  const isFfuf = (kind === 'files' || kind === 'dirs' || kind === 'subs');
  if (isFfuf) {
    pane.innerHTML =
      '<div style="display:flex;flex-direction:column;gap:12px;padding:20px 0;">' +
        '<div style="color:var(--muted);font-size:var(--xs);">Running ' + kind + ' scan on ' + label + '…</div>' +
        '<div style="background:var(--surface);border-radius:var(--r);overflow:hidden;height:18px;width:100%;">' +
          '<div id="bar_' + id + '" style="height:100%;width:0%;background:var(--blue);transition:width 0.4s;"></div>' +
        '</div>' +
        '<div id="pct_' + id + '" style="color:var(--muted);font-size:var(--xs);">0%</div>' +
      '</div>';
  } else {
    pane.innerHTML = '<pre class="scan-out" id="out_' + id + '"></pre>';
  }

  document.getElementById('output-area').appendChild(pane);
  tabs[id] = { label, kind, tab, pane };
  document.getElementById('empty-hint').style.display = 'none';
  activateTab(id);
  return id;
}

function activateTab(id) {
  if (activeTabId && tabs[activeTabId]) {
    tabs[activeTabId].tab.classList.remove('active');
    tabs[activeTabId].pane.style.display = 'none';
  }
  activeTabId = id;
  tabs[id].tab.classList.add('active');
  tabs[id].pane.style.display = 'flex';
}

function closeTab(e, id) {
  e.stopPropagation();
  tabs[id].tab.remove();
  tabs[id].pane.remove();
  delete tabs[id];
  const keys = Object.keys(tabs);
  if (keys.length > 0) {
    activateTab(keys[keys.length - 1]);
  } else {
    activeTabId = null;
    document.getElementById('empty-hint').style.display = 'flex';
    const tabbar = document.getElementById('tabbar');
    const hint = document.createElement('span');
    hint.className = 'tabbar-empty';
    hint.id = 'tabbar-empty';
    hint.textContent = 'No scans yet';
    tabbar.appendChild(hint);
  }
}

function killTab(e, id) {
  e.stopPropagation();
  if (tabs[id]) tabs[id].killed = true;
  fetch('/api/scan/kill/' + id, { method: 'POST' })
    .then(function() {
      setDot(id, 'error');
      var kill = document.getElementById('kill_' + id);
      if (kill) kill.style.display = 'none';
    });
}

function setDot(id, state) {
  const dot = document.getElementById('dot_' + id);
  if (dot) dot.className = 'tab-dot ' + state;
}

function appendLine(id, text) {
  const out = document.getElementById('out_' + id);
  if (!out) return;
  out.textContent += text + '\n';
  if (activeTabId === id) {
    const pane = tabs[id].pane;
    pane.scrollTop = pane.scrollHeight;
  }
}

function setPaneContent(id, html) {
  tabs[id].pane.innerHTML = html;
}

// ── SSE ───────────────────────────────────────
function stream(url, tabId, cmd, key) {
  logCommand(tabId, key || '', cmd || url);
  const src = new EventSource(url);
  let autoFilter = true;
  
  src.onmessage = function(e) {

    if (e.data.startsWith('OUTFILE:')) {
      if (tabs[tabId]) tabs[tabId].outfile = e.data.split(':').slice(1).join(':');
      return;
    }

    if (e.data.startsWith('PROGRESS:')) {
      var val = e.data.split(':')[1];
      var bar = document.getElementById('bar_' + tabId);
      var pct = document.getElementById('pct_' + tabId);
      if (bar) bar.style.width = val + '%';
      if (pct) pct.textContent = val + '%';
      return;
    }

    if (e.data.startsWith('AUTO_FILTER:')) {
      autoFilter = e.data.split(':')[1] === 'true';
      return;
    }

    if (e.data === '[DONE]') {
      updateLogDot(tabId, 'done');
      src.close();
      refreshTree();

      var outfile = tabs[tabId] && tabs[tabId].outfile;
      var kind    = tabs[tabId] && tabs[tabId].kind;
      var killed  = tabs[tabId] && tabs[tabId].killed;

      if (outfile && !killed) {
        if (kind === 'nmap') {
            var target = outfile.split('/')[0];
            viewNmap(target);
        } else {
            var label = tabs[tabId].label + ' (' + kind + ')';
            var label = tabs[tabId].label + ' (' + kind + ')';
            if (autoFilter) {
            var filteredOutfile = outfile.replace(/\.json$/, '_f.json');
            fetch('/api/results/file?path=' + encodeURIComponent('puf/' + filteredOutfile))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                var useFile = (data && data.results) ? filteredOutfile : outfile;
                var u = '/api/results/file?path=' + encodeURIComponent('puf/' + useFile);
                viewJson(u, label);
                });
            } else {
                var u = '/api/results/file?path=' + encodeURIComponent('puf/' + outfile);
                viewJson(u, label);
            }
        }
    }

      if (tabs[tabId]) {
        tabs[tabId].tab.remove();
        tabs[tabId].pane.remove();
        delete tabs[tabId];
        var keys = Object.keys(tabs);
        if (keys.length > 0) {
          activateTab(keys[keys.length - 1]);
        } else {
          activeTabId = null;
          document.getElementById('empty-hint').style.display = 'flex';
          var tabbar = document.getElementById('tabbar');
          var hint = document.createElement('span');
          hint.className = 'tabbar-empty';
          hint.id = 'tabbar-empty';
          hint.textContent = 'No scans yet';
          tabbar.appendChild(hint);
        }
      }
      return;
    }

    appendLine(tabId, e.data);
  };

  src.onerror = function() {
    src.close();
    setDot(tabId, 'error');
    updateLogDot(tabId, 'error');
  };
}

// ── Launchers ─────────────────────────────────
function isIp(str) {
  return /^(\d{1,3}\.){3}\d{1,3}$/.test(str);
}

function rootDomain(input) {
  var host = input.replace(/^https?:\/\//, '').split('/')[0].split(':')[0];
  if (isIp(host)) return host;
  var parts = host.split('.');
  return parts.length > 2 ? parts.slice(-2).join('.') : host;
}

function launchNmapForm(e) {
  e.preventDefault();
  var t = document.getElementById('target-input').value.trim();
  if (!t) return;
  var root = rootDomain(t);
  launchNmap(root);
  if (!isIp(root)) {
    webScan('http://' + root, root);
  }
}

function launchNmap(target) {
  var clean = rootDomain(target);
  var id = createTab(clean, 'nmap');
  fetch('/api/commands/get').then(function(r) { return r.json(); }).then(function(cmds) {
    var cmd = cmds['nmap'].replace('{target}', clean).replace('{outfile}', '...');
    stream('/api/scan/nmap?target=' + encodeURIComponent(clean) + '&tabId=' + id, id, cmd);
  });
  closePopover();
}

function launchFfuf(target, type) {
  var id = createTab(target, type);
  fetch('/api/commands/get').then(function(r) { return r.json(); }).then(function(cmds) {
    var key = type === 'subs' ? 'fuzz_subs' : 'fuzz';
    var cmd = cmds[key]
      .replace('{target}', target)
      .replace('{hostname}', new URL(target.startsWith('http') ? target : 'http://' + target).hostname)
      .replace(/-w\s+\S+/g, '-w {wordlist}')
      .replace(/-o\s+\S+/g, '-o {outfile}');
    stream('/api/scan/ffuf?target=' + encodeURIComponent(target) + '&type=' + type + '&tabId=' + id, id, cmd);
  });
  closePopover();
}

function webScan(baseUrl, hostname) {
  launchFfuf(baseUrl, 'files');
  launchFfuf(baseUrl, 'dirs');
  launchFfuf(baseUrl, 'subs');
  closePopover();
}

// ── Result viewers ────────────────────────────
function viewNmap(target) {
  fetch('/api/results/' + encodeURIComponent(target))
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var id = createTab(target, 'nmap results');
      setDot(id, 'done');
      if (!Array.isArray(data) || !data.length) {
        setPaneContent(id, '<div class="empty-hint"><p>No results yet</p></div>');
        return;
      }
      var rows = '';
      var idx = 0;
      data.forEach(function(host) {
        host.ports.forEach(function(p) {
          var scheme = (p.port === '443' || p.service === 'https') ? 'https' : 'http';
          var standardPort = (scheme === 'http' && p.port === '80') || (scheme === 'https' && p.port === '443');
          var clickUrl = standardPort ? scheme + '://' + target : scheme + '://' + target + ':' + p.port;
          rows += '<tr class="result-row" id="rrow_' + id + '_' + idx + '" onclick="resultRowClick(event, \'' + clickUrl + '\')">' +
            '<td>' + target + '</td>' +
            '<td>' + p.port + '</td>' +
            '<td>' + p.protocol + '</td>' +
            '<td class="status-' + (p.state === 'open' ? '2xx' : 'muted') + '">' + p.state + '</td>' +
            '<td>' + p.service + '</td>' +
            '<td class="muted">' + (p.version || '') + '</td>' +
            '<td><button class="flag-btn" onclick="toggleFlag(this, \'rrow_' + id + '_' + idx + '\')" title="Flag as target">⚑</button></td>' +
            '</tr>';
          idx++;
        });
      });
      setPaneContent(id,
        '<div class="pane-table"><table class="rtable"><thead><tr>' +
        '<th>Host</th><th>Port</th><th>Proto</th><th>State</th><th>Service</th><th>Version</th><th></th>' +
        '</tr></thead><tbody>' + rows + '</tbody></table></div>');
    });
  closePopover();
}

function viewJson(apiUrl, label) {
  var baseUrl = apiUrl.split('&offset=')[0].split('?offset=')[0];
  // strip any existing offset/limit params
  baseUrl = baseUrl.replace(/[&?]offset=\d+/, '').replace(/[&?]limit=\d+/, '');
  var separator = baseUrl.includes('?') ? '&' : '?';

  var offset = 0;
  var limit  = 500;
  var total  = null;
  var loading = false;
  var isSubs = false;
  var tabId  = null;

  function fetchPage(id) {
    if (loading) return;
    if (total !== null && offset >= total) return;
    loading = true;

    fetch(baseUrl + separator + 'offset=' + offset + '&limit=' + limit)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var results = data.results || data;
        total = data.total !== undefined ? data.total : results.length;

        if (offset === 0) {
          // first page — build the tab and table
          tabId = createTab(label, 'results');
          setDot(tabId, 'done');

          if (!Array.isArray(results) || !results.length) {
            setPaneContent(tabId, '<div class="empty-hint"><p>No results</p></div>');
            loading = false;
            return;
          }

          isSubs = results[0].input && results[0].input.FUZZ && !results[0].url.includes(results[0].input.FUZZ);

          var html =
            '<div class="pane-table" id="jtable_' + tabId + '">' +
            '<table class="rtable"><thead><tr>' +
            '<th>URL</th>' + (isSubs ? '<th>Host</th>' : '') +
            '<th>Status</th><th>Length</th><th>Words</th><th>Lines</th><th></th>' +
            '</tr></thead>' +
            '<tbody id="jtbody_' + tabId + '">' +
            buildRows(results, tabId, 0, isSubs) +
            '</tbody></table>' +
            '<div id="jloader_' + tabId + '" style="padding:12px;text-align:center;color:var(--muted);font-size:var(--xs);">' +
              (offset + results.length < total ? 'Loading more…' : '') +
            '</div>' +
            '</div>';

          setPaneContent(tabId, html);

          // attach scroll listener
          var pane = document.getElementById('jtable_' + tabId);
          pane.addEventListener('scroll', function() {
            if (pane.scrollTop + pane.clientHeight >= pane.scrollHeight - 100) {
              fetchPage(tabId);
            }
          });

        } else {
          // subsequent pages — append rows
          var tbody = document.getElementById('jtbody_' + tabId);
          if (tbody) tbody.innerHTML += buildRows(results, tabId, offset, isSubs);
          var loader = document.getElementById('jloader_' + tabId);
          if (loader) loader.textContent = (offset + results.length < total ? '' : 'All ' + total + ' results loaded');
        }

        offset += results.length;
        loading = false;
      });
  }

  function buildRows(results, id, startIdx, isSubs) {
    var rows = '';
    results.forEach(function(r, i) {
      var idx = startIdx + i;
      var display    = isSubs ? r.input.FUZZ + '.' + new URL(r.url).hostname : r.url;
      var host       = isSubs ? new URL(r.url).hostname : null;
      var clickTarget = isSubs ? 'http://' + display : r.url;
      rows += '<tr class="result-row" id="rrow_' + id + '_' + idx + '" onclick="resultRowClick(event, \'' + clickTarget + '\')">' +
        '<td><a href="' + (isSubs ? 'http://' + display : r.url) + '" target="_blank" class="result-url">' + display + '</a></td>' +
        (isSubs ? '<td class="muted">' + host + '</td>' : '') +
        '<td class="status-' + Math.floor(r.status/100) + 'xx">' + r.status + '</td>' +
        '<td class="muted">' + r.length + '</td>' +
        '<td class="muted">' + r.words + '</td>' +
        '<td class="muted">' + r.lines + '</td>' +
        '<td><button class="flag-btn" onclick="toggleFlag(this, \'rrow_' + id + '_' + idx + '\')" title="Flag as target">⚑</button></td>' +
        '</tr>';
    });
    return rows;
  }

  fetchPage(null);
  closePopover();
}

function viewRaw(filePath, name) {
  fetch('/api/results/raw?path=' + encodeURIComponent(filePath))
    .then(function(r) { return r.text(); })
    .then(function(content) {
      var id = createTab(name, 'file');
      setDot(id, 'done');
      setPaneContent(id, '<pre class="scan-out" style="padding:16px;white-space:pre-wrap;word-break:break-all;">' +
        content.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>');
    });
}

function toggleFlag(btn, rowId) {
  var row = document.getElementById(rowId);
  row.classList.toggle('flagged');
  btn.classList.toggle('flagged');
}

// ── Popover ───────────────────────────────────
function showPopover(x, y, title, actions) {
  var p = document.getElementById('popover');
  document.getElementById('popover-title').textContent = title;
  var el = document.getElementById('popover-actions');
  el.innerHTML = '';
  actions.forEach(function(a) {
    var btn = document.createElement('button');
    btn.className = 'popover-btn' + (a.primary ? ' primary' : '');
    btn.innerHTML = a.label;
    btn.onclick = a.fn;
    el.appendChild(btn);
  });
  p.style.display = 'block';
  p.style.left = (x + 4) + 'px';
  p.style.top = y + 'px';
}

function closePopover() {
  document.getElementById('popover').style.display = 'none';
}

document.addEventListener('click', function(e) {
  if (!e.target.closest('#popover') && !e.target.closest('.tree-label')) closePopover();
});

// ── Row clicks ────────────────────────────────
function portRowClick(e, hostname, port) {
  e.stopPropagation();
  var httpUrl  = 'http://'  + hostname + ':' + port;
  var httpsUrl = 'https://' + hostname + ':' + port;
  showPopover(e.clientX, e.clientY, hostname + ':' + port, [
    { label: '▶ web scan (http)',  fn: function() { webScan(httpUrl,  hostname); }, primary: true },
    { label: '▶ web scan (https)', fn: function() { webScan(httpsUrl, hostname); }, primary: true },
  ]);
}

function resultRowClick(e, url) {
  if (e.target.tagName === 'A' || e.target.classList.contains('flag-btn')) return;
  e.stopPropagation();
  showPopover(e.clientX, e.clientY, url, [
    { label: '▶ web scan (http)',  fn: function() { webScan(url.replace(/^https/, 'http'),  new URL(url).hostname); }, primary: true },
    { label: '▶ web scan (https)', fn: function() { webScan(url.replace(/^http:/, 'https:'), new URL(url).hostname); }, primary: true },
    { label: '▶ files (http)',     fn: function() { launchFfuf(url.replace(/^https/, 'http'),  'files'); } },
    { label: '▶ dirs  (http)',     fn: function() { launchFfuf(url.replace(/^https/, 'http'),  'dirs');  } },
    { label: '▶ files (https)',    fn: function() { launchFfuf(url.replace(/^http:/, 'https:'), 'files'); } },
    { label: '▶ dirs  (https)',    fn: function() { launchFfuf(url.replace(/^http:/, 'https:'), 'dirs');  } },
  ]);
}

// ── Tree ──────────────────────────────────────
function refreshTree() {
  fetch('/api/tree')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var root = document.getElementById('tree-root');
      root.innerHTML = '';
      buildTree(data, root);
    });
}

function buildTree(data, container) {
  Object.keys(data).forEach(function(path) {
    var node = data[path];
    var parts = path.replace(/\\/g, '/').split('/').filter(Boolean);
    var depth = parts.length - 1;
    var indent = (depth * 14) + 'px';
    var name = parts[parts.length - 1] || path;

    var li = document.createElement('li');
    var label = document.createElement('div');
    label.className = 'tree-label';
    label.style.cssText = 'padding-left:calc(' + indent + ' + 12px);display:flex;align-items:center;width:100%';
    label.innerHTML =
      getFolderIcon(depth) +
      '<span style="flex:1">' + name + '</span>' +
      '<button class="tree-del" onclick="event.stopPropagation();deletePath(\'' + path + '\',\'' + name + '\')">&#x2715;</button>';
    label.addEventListener('click', function(e) {
      e.stopPropagation();
      folderPopover(e.clientX, e.clientY, name, parts);
    });
    li.appendChild(label);

    if (node.files && node.files.length) {
      node.files.forEach(function(f) {
        var fileIndent = ((depth + 1) * 14) + 'px';
        var fli = document.createElement('li');
        var flabel = document.createElement('div');
        flabel.className = 'tree-label file';
        flabel.style.cssText = 'padding-left:calc(' + fileIndent + ' + 14px);display:flex;align-items:center;width:100%';
        flabel.innerHTML =
          getFileIcon(f) +
          '<span style="flex:1">' + f + '</span>' +
          '<button class="tree-del" onclick="event.stopPropagation();deletePath(\'' + path + '/' + f + '\',\'' + f + '\')">&#x2715;</button>';
        flabel.addEventListener('click', function(e) {
          e.stopPropagation();
          filePopover(e.clientX, e.clientY, f, parts);
        });
        flabel.addEventListener('dblclick', function(e) {
          e.stopPropagation();
          var filePath = 'puf/' + parts.slice(1).join('/') + '/' + f;
          if (f.endsWith('.xml')) {
            viewNmap(parts[1]);
          } else if (f.endsWith('.json')) {
            viewJson('/api/results/file?path=' + encodeURIComponent(filePath), f);
          } else {
            viewRaw(filePath, f);
          }
        });
        fli.appendChild(flabel);
        li.appendChild(fli);
      });
    }

    container.appendChild(li);
  });
}

function getFolderIcon(depth) {
  var src = ICONS['icon_depth_' + depth] || ICONS['icon_depth_0'];
  return '<img src="/' + src + '" class="tree-icon">';
}

function getFileIcon(name) {
  var key = name.endsWith('.json') ? 'icon_file_json'
          : name.endsWith('.xml')  ? 'icon_file_xml'
          : 'icon_file_default';
  return '<img src="/' + ICONS[key] + '" class="tree-icon">';
}

// ── Popovers ──────────────────────────────────
function folderPopover(x, y, name, parts) {
  var actions = [];
  if (parts.length === 1) return;
  if (parts.length === 2) {
    var target = parts[1];
    actions.push({ label: '▶ nmap scan', fn: function() { launchNmap(target); }, primary: true });
  }
  if (parts.length === 3) {
    var hostname = parts[2];
    actions.push({ label: '▶ subdomains scan (http)',  fn: function() { launchFfuf('http://'  + hostname, 'subs'); }, primary: true });
    actions.push({ label: '▶ subdomains scan (https)', fn: function() { launchFfuf('https://' + hostname, 'subs'); }, primary: true });
  }
  if (parts.length === 4) {
    var hostname2 = parts[2];
    var sp = parts[3].split('_');
    var url = sp[0] + '://' + hostname2 + ':' + sp[1];
    actions.push({ label: '▶ files scan', fn: function() { launchFfuf(url, 'files'); } });
    actions.push({ label: '▶ dirs scan',  fn: function() { launchFfuf(url, 'dirs');  } });
  }
  if (actions.length) showPopover(x, y, name, actions);
}

function filePopover(x, y, name, parts) {
  var actions = [];
  var filePath = 'puf/' + parts.slice(1).join('/') + '/' + name;
  if (name.endsWith('.xml')) {
    actions.push({ label: 'View nmap results', fn: function() { viewNmap(parts[1]); } });
  } else if (name.endsWith('.json')) {
    var u = '/api/results/file?path=' + encodeURIComponent(filePath);
    actions.push({ label: 'View results', fn: function() { viewJson(u, name); } });
    actions.push({ label: 'View raw file', fn: (function(fp, n) { return function() { viewRaw(fp, n); }; })(filePath, name) });
    if (!name.endsWith('_f.json') && !name.endsWith('_cs.json')) {
      actions.push({
        label: '<img src="/' + ICONS['icon_filter'] + '" class="tree-icon" style="filter:invert(60%) sepia(100%) saturate(500%) hue-rotate(0deg);"> Custom filter',
        fn: (function(fp, n) { return function() { openFilterModal(fp, n); }; })(filePath, name),
      });
    }
  } else {
    actions.push({ label: 'View raw file', fn: (function(fp, n) { return function() { viewRaw(fp, n); }; })(filePath, name) });
  }
  if (actions.length) showPopover(x, y, name, actions);
}

// ── Filter modal ──────────────────────────────
function openFilterModal(path, name) {
  _filterTargetPath = path;
  _filterTargetName = name;
  document.getElementById('fm-smart-enabled').checked = true;
  document.getElementById('fm-smart-limit').value = 1000;
  document.getElementById('fm-smart-limit').disabled = false;
  document.getElementById('fm-status').value = '';
  document.getElementById('fm-words').value = '';
  document.getElementById('fm-lengths').value = '';
  document.getElementById('filter-modal').style.display = 'flex';
  closePopover();
}

function closeFilterModal() {
  document.getElementById('filter-modal').style.display = 'none';
}

function toggleSmartLimit() {
  var enabled = document.getElementById('fm-smart-enabled').checked;
  document.getElementById('fm-smart-limit').disabled = !enabled;
  document.getElementById('fm-smart-limit').style.opacity = enabled ? '1' : '0.4';
}

function parseList(val) {
  return val.split(',').map(function(v) { return v.trim(); })
    .filter(Boolean).map(Number).filter(function(n) { return !isNaN(n); });
}

function runCustomFilter() {
  var payload = {
    path: _filterTargetPath,
    smart_enabled: document.getElementById('fm-smart-enabled').checked,
    smart_limit: parseInt(document.getElementById('fm-smart-limit').value) || 1000,
    status_codes: parseList(document.getElementById('fm-status').value),
    word_counts:  parseList(document.getElementById('fm-words').value),
    lengths:      parseList(document.getElementById('fm-lengths').value)
  };
  closeFilterModal();
  var filterId = 'filter_' + Date.now();
  logCommand(filterId, 'filter', 'filter → ' + _filterTargetName);
  fetch('/api/filter', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    updateLogDot(filterId, data.error ? 'error' : 'done');
    if (data.error) { alert('Filter error: ' + data.error); return; }
    var label = _filterTargetName.replace('.json', '_custom_filtered.json');
    var u = '/api/results/file?path=' + encodeURIComponent(data.output_path);
    viewJson(u, label);
    refreshTree();
  });
}

// ── Modal ─────────────────────────────────────
function showModal(message, onConfirm) {
  document.getElementById('modal-body').textContent = message;
  document.getElementById('modal-confirm').onclick = function() {
    closeModal();
    onConfirm();
  };
  document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
  document.getElementById('modal-overlay').style.display = 'none';
}

function deletePath(path, label) {
  showModal('Delete "' + label + '"? This cannot be undone.', function() {
    fetch('/api/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: path })
    }).then(function() { refreshTree(); });
  });
}

// ── Command Log ───────────────────────────────
function logCommand(tabId, key, cmd) {
  var list = document.getElementById('cmd-log-list');
  var now  = new Date();
  var time = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0');

  var entry = document.createElement('div');
  entry.className = 'cmd-log-entry';
  entry.id = 'cmdlog_' + tabId;
  entry.innerHTML =
    '<span class="tab-dot running" id="cmdlog_dot_' + tabId + '"></span>' +
    '<span class="cmd-time">' + time + '</span>' +
    (key ? '<span class="cmd-kind">' + key + '</span>' : '') +
    '<span class="cmd-text" title="' + cmd.replace(/"/g,'&quot;') + '" ' +
    'onclick="navigator.clipboard.writeText(this.getAttribute(\'title\'));this.style.color=\'var(--blue)\';setTimeout(()=>this.style.color=\'\',800)">' + cmd + '</span>';

  var entries = list.querySelectorAll('.cmd-log-entry');
  var firstRunning = null;
  entries.forEach(function(e) {
    var dot = e.querySelector('.tab-dot');
    if (dot && dot.classList.contains('running') && !firstRunning) firstRunning = e;
  });
  if (firstRunning) {
    list.insertBefore(entry, firstRunning);
  } else {
    list.appendChild(entry);
  }

  list.scrollTop = list.scrollHeight;
}

function updateLogDot(tabId, state) {
  var dot = document.getElementById('cmdlog_dot_' + tabId);
  if (dot) {
    dot.className = 'tab-dot ' + state;
    // if done/error, move entry above running ones
    if (state === 'done' || state === 'error') {
      var list  = document.getElementById('cmd-log-list');
      var entry = document.getElementById('cmdlog_' + tabId);
      var firstRunning = null;
      list.querySelectorAll('.cmd-log-entry').forEach(function(e) {
        var d = e.querySelector('.tab-dot');
        if (d && d.classList.contains('running') && !firstRunning) firstRunning = e;
      });
      if (firstRunning && entry) list.insertBefore(entry, firstRunning);
    }
  }
}

function showCmdPopover(e, tabId) {
  var entry = document.getElementById('cmdlog_' + tabId);
  if (!entry) return;
  var cmd = entry.querySelector('.cmd-text').getAttribute('title');
  showPopover(e.clientX, e.clientY, 'Command', [
    { label: '⎘ Copy', fn: function() { navigator.clipboard.writeText(cmd); closePopover(); } }
  ]);
}

// ── Command Panel ─────────────────────────────
var cmdEdits = {};  // stores any session overrides

function initCmdPanel() {
  fetch('/api/commands/get')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var list = document.getElementById('cmd-panel-list');
      list.innerHTML = '';
      ['nmap','fuzz','fuzz_subs'].forEach(function(key) {
        var raw = data[key] || '';
        var preview = raw
          .replace(/-w\s+\S+/g, '-w {wordlist}')
          .replace(/-o\s+\S+/g, '-o {outfile}');
        var row = document.createElement('div');
        row.className = 'cmd-panel-row';
        row.id = 'cmdrow_' + key;
        row.innerHTML =
          '<span class="cmd-key">' + key + '</span>' +
          '<span class="cmd-preview" title="' + preview + '">' + preview + '</span>' +
          '<button class="btn-ghost" onclick="editCmd(\'' + key + '\')">✎</button>' +
          '<button class="btn-ghost" onclick="runCmdFromPanel(\'' + key + '\')">▶</button>';
        list.appendChild(row);
      });
    });
}

function editCmd(key) {
  fetch('/api/commands/get')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var current = cmdEdits[key] || data[key] || '';
      var modal = document.getElementById('cmd-edit-modal');
      document.getElementById('cmd-edit-key').textContent = key;
      document.getElementById('cmd-edit-input').value = current;
      document.getElementById('cmd-edit-save').onclick = function() {
        var val = document.getElementById('cmd-edit-input').value.trim();
        cmdEdits[key] = val;
        fetch('/api/commands/set', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: key, cmd: val })
        }).then(function() { initCmdPanel(); closeCmdEditModal(); });
      };
      modal.style.display = 'flex';
    });
}

function closeCmdEditModal() {
  document.getElementById('cmd-edit-modal').style.display = 'none';
}

function runCmdFromPanel(key) {
  alert('Use the tree or form to launch scans — this will be wired up soon.');
}

// ── Init ──────────────────────────────────────
fetch('/api/config/icons')
  .then(function(r) { return r.json(); })
  .then(function(data) {
    ICONS = data;
    refreshTree();
    setInterval(refreshTree, 5000);
    initCmdPanel();
  });