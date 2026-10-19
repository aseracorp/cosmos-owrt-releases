#!/usr/bin/env python3
"""
Generate the GitHub Pages download tree for Cosmos Cloud OpenWrt images.

The site contains NO binaries. Every file entry links to a release asset
hosted on GitHub Releases (public mirror repo), so users can download the
files even though the source repo (aseracorp/cosmos-owrt) is private.

Structure:
    <openwrt>/<cosmos>/files          download links for that combo
    latest/...                        latest Cosmos Cloud overall (auto-updating)
    latest/<openwrt>/...              latest Cosmos Cloud for each OpenWrt
    index.html                        root listing

Only the LATEST release of each <openwrt>/<cosmos> combo gets download
links; older replicates are listed without links. Files are presented
directly on the OpenWrt / Cosmos version pages (no intermediate stub).

Usage:
    generate.py --source aseracorp/cosmos-owrt-releases [--root site] [--token ...]
"""
import argparse, html, json, os, re, urllib.request
from datetime import datetime

SITE_ROOT = '/cosmos-owrt-releases'   # GitHub Pages base path (no trailing slash)

def api_get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def parse_versions(tag, name):
    ow = co = None
    m = re.search(r'owv?(\d+\.\d+\.\d+)', tag)
    if m: ow = m.group(1)
    else:
        m = re.search(r'-(\d+\.\d+\.\d+)$', tag)
        if m: ow = m.group(1)
    m = re.search(r'(?:ccv|vv)(v?\d+(?:\.\w+)+)', tag, re.I)
    if m: co = m.group(1)
    name = (name or '')
    m2 = re.search(r'OpenWrt\s+(\d+\.\d+\.\d+)', name)
    if m2: ow = m2.group(1)
    m2 = re.search(r'(v\d+\.\d+(?:\.\w+)*)', name)
    if m2: co = m2.group(1)
    return ow, (co or '')

def vkey(v):
    if not v: return (0,)
    nums = re.findall(r'\d+', v)
    return tuple(int(x) for x in nums[:3]) if nums else (0,)

def human(n):
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024: return f"{n:.0f} {unit}" if unit=='B' else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

def size_sort_key(fn):
    # checksum/signature files at the end
    return (fn.lower().endswith('.sha256') or fn.endswith('.sig'))

def h(text): return html.escape(str(text), quote=True)

CSS = """
:root { color-scheme: light dark; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 62rem; margin: 2rem auto; padding: 0 1.25rem 4rem; line-height: 1.5; color: #1f2328; background: #ffffff; }
a { color: #0969da; text-decoration: none; }
a:hover { text-decoration: underline; }
h1 { font-size: 1.6rem; border-bottom: 1px solid #d8dee4; padding-bottom: .4rem; }
h2 { font-size: 1.2rem; margin-top: 2rem; }
.breadcrumbs { font-size: .9rem; color: #59636e; margin-bottom: 1rem; }
.breadcrumbs a { color: #59636e; }
.tag { display:inline-block; padding: .15rem .5rem; border-radius: 999px; font-size: .75rem; font-weight: 600; margin-left: .5rem; vertical-align: middle; }
.latest-tag { background:#2da44e; color:#fff; }
.stable-tag { background:#0969da; color:#fff; }
.pre-tag { background:#bf8700; color:#fff; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { text-align: left; padding: .45rem .6rem; border-bottom: 1px solid #d8dee4; }
th { font-size: .75rem; text-transform: uppercase; letter-spacing: .04em; color: #59636e; }
.size { text-align: right; white-space: nowrap; color: #59636e; font-variant-numeric: tabular-nums; }
.muted { color: #59636e; }
.back { display:inline-block; margin: .5rem 0 1rem; font-size: .9rem; }
footer { margin-top: 3rem; font-size: .8rem; color: #59636e; }
body.dark { background: #0d1117; color: #e6edf3; }
body.dark a { color: #4493f8; }
body.dark .breadcrumbs, body.dark .breadcrumbs a, body.dark th, body.dark .size, body.dark .muted, body.dark footer { color: #9198a1; }
body.dark th, body.dark td { border-color: #30363d; }
body.dark h1 { border-bottom-color: #30363d; }
body.dark .latest-tag { background:#1f883d; }
body.dark .stable-tag { background:#1f6feb; }
@media (prefers-color-scheme: dark) {
  body { background: #0d1117; color: #e6edf3; }
  a { color: #4493f8; }
  .breadcrumbs, .breadcrumbs a, th, .size, .muted, footer { color: #9198a1; }
  th, td { border-color: #30363d; }
  h1 { border-bottom-color: #30363d; }
  .latest-tag { background: #1f883d; }
  .stable-tag { background: #1f6feb; }
}
"""

def page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""

def nav(parts):
    out = [f'<div class="breadcrumbs"><a href="{A("index.html")}">📦 Cosmos Cloud releases</a>']
    for label, href in parts:
        if href:
            out.append(f' / <a href="{h(href)}">{h(label)}</a>')
        else:
            out.append(f' / <b>{h(label)}</b>')
    out.append('</div>')
    return '\n'.join(out)

def abspath(*parts):
    """Absolute site path (rooted at the Pages base URL)."""
    return SITE_ROOT + '/' + '/'.join(str(p) for p in parts)

PREFIX = ''   # e.g. 'latest/' when rendering the latest/ subtree

def A(*parts):
    """Absolute path honouring the current PREFIX."""
    return SITE_ROOT + '/' + PREFIX + '/'.join(str(p) for p in parts)

def placeholder():
    body = nav([]) + ('<h1>Cosmos Cloud — OpenWrt releases</h1>'
                      '<p class="muted">No mirrored releases yet. The index will appear here once releases are mirrored '
                      'from <a href="https://github.com/aseracorp/cosmos-owrt">aseracorp/cosmos-owrt</a>.</p>')
    write('index.html', page('Cosmos Cloud — OpenWrt releases', body))
    write('latest/index.html', page('Latest release', nav([('latest/', None)]) + '<h1>Latest</h1><p class="muted">No releases yet.</p>'))
    write('sitemap.xml', sitemap_root([]))
    print('No releases — wrote placeholder.')

def sitemap_root(releases, latest_by_ow=None):
    urls = ['<url><loc>https://aseracorp.github.io/cosmos-owrt-releases/</loc></url>',
            '<url><loc>https://aseracorp.github.io/cosmos-owrt-releases/latest/</loc></url>']
    for r in releases:
        urls.append(f'<url><loc>https://aseracorp.github.io/cosmos-owrt-releases/{h(r["ow"])}/</loc></url>')
        urls.append(f'<url><loc>https://aseracorp.github.io/cosmos-owrt-releases/{h(r["ow"])}/{h(r["co"])}/files/</loc></url>')
    if latest_by_ow:
        for ow, lat in latest_by_ow.items():
            urls.append(f'<url><loc>https://aseracorp.github.io/cosmos-owrt-releases/latest/{h(ow)}/</loc></url>')
            urls.append(f'<url><loc>https://aseracorp.github.io/cosmos-owrt-releases/latest/{h(ow)}/{h(lat["co"])}/files/</loc></url>')
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(urls) + '\n</urlset>\n'

def render_root(releases, latest_all, latest_by_ow):
    ow = sorted({r['ow'] for r in releases if r['ow']})
    rows = []
    for v_ow in ow:
        rels = [r for r in releases if r['ow'] == v_ow]
        rels.sort(key=lambda r: (vkey(r['co']), r['id']), reverse=True)
        lat = latest_by_ow.get(v_ow)
        latest_flag = '<span class="tag latest-tag">latest</span>' if lat and rels[0]['id'] == lat['id'] else ''
        stable = any(not r['pre'] for r in rels)
        badge = latest_flag + ('<span class="tag stable-tag">stable</span>' if stable else '')
        rows.append(f'<tr><td><a href="{h(v_ow)}/index.html">{h(v_ow)}</a> {badge}</td></tr>')
    latest_row = ''
    if latest_all:
        lat = latest_all
        latest_row = (f'<tr><td><a href="{abspath("latest")}/index.html"><code>latest/</code></a> '
                      f'<span class="tag latest-tag">latest</span> '
                      f'— Cosmos Cloud {h(lat["co"])} / OpenWrt {h(lat["ow"])} '
                      f'({h(lat["name"])})</td></tr>')
    body = [nav([]), '<h1>Cosmos Cloud — OpenWrt releases</h1>',
            '<p class="muted">Download index generated automatically from GitHub Releases. No binaries are stored in this repository — all files are served from GitHub Release assets.</p>']
    if latest_row:
        body.append('<h2>Latest</h2><table>' + latest_row + '</table>')
    else:
        body.append('<p class="muted">No releases found yet in the mirror.</p>')
    body.append('<h2>By OpenWrt version</h2><table><tr><th>OpenWrt</th><th></th></tr>' + ''.join(rows) + '</table>')
    body.append(f'<p class="muted">{len(releases)} release(s) indexed.</p>')
    write('index.html', page('Cosmos Cloud — OpenWrt releases', '\n'.join(body)))
    write('sitemap.xml', sitemap_root(releases, latest_by_ow))

def render_latest_root(latest_all, latest_by_ow):
    if not latest_all:
        write('latest/index.html', page('Latest release', nav([('latest/', None)]) + '<h1>Latest</h1><p class="muted">No releases yet.</p>'))
        return
    rows = []
    for v_ow, lat in sorted(latest_by_ow.items()):
        rows.append(f'<tr><td><a href="{abspath("latest", v_ow)}/index.html">{h(v_ow)}</a></td>'
                    f'<td>Cosmos Cloud {h(lat["co"])}</td><td>{h(lat["name"])}</td></tr>')
    body = [nav([('latest/', None)]),
            '<h1>📌 Latest</h1>',
            f'<p class="muted">Latest Cosmos Cloud overall: <b>{h(latest_all["co"])}</b> / OpenWrt <b>{h(latest_all["ow"])}</b> — '
            f'<a href="{abspath(latest_all["ow"], latest_all["co"])}/index.html">open downloads</a></p>',
            '<h2>Per OpenWrt version</h2><table><tr><th>OpenWrt</th><th>Latest Cosmos Cloud</th><th>Release</th></tr>' + ''.join(rows) + '</table>',
            f'<h2>Files — {h(latest_all["co"])} · {h(latest_all["ow"])}</h2>',
            file_table(latest_all),
            f'<p class="back"><a href="{A("index.html")}">← back</a></p>']
    write('latest/index.html', page('Latest release', '\n'.join(body)))

def render_ow(ow, releases, latest_by_ow):
    rels = [r for r in releases if r['ow'] == ow]
    rels.sort(key=lambda r: (vkey(r['co']), r['id']), reverse=True)
    rows = []
    for r in rels:
        is_latest = (latest_by_ow.get(ow) or {}).get('id') == r['id']
        flag = '<span class="tag latest-tag">latest</span>' if is_latest else ('<span class="tag pre-tag">pre</span>' if r['pre'] else '')
        rows.append(f'<tr><td>Cosmos Cloud <b>{h(r["co"])}</b> {flag}</td><td>{h(r["name"])}</td></tr>')
    body = [nav([(ow, None)]), f'<h1>OpenWrt {h(ow)}</h1>',
            '<table><tr><th>Cosmos Cloud version</th><th>Release</th></tr>' + ''.join(rows) + '</table>']
    if rels:
        latest = rels[0]
        body.append(f'<h2>Files — Cosmos Cloud {h(latest["co"])} · {h(ow)}</h2>')
        body.append(file_table(latest))
        body.append(f'<p class="muted"><a href="{A("index.html")}">← back</a></p>')
    write(f'{PREFIX}{ow}/index.html', page(f'OpenWrt {ow}', '\n'.join(body)))

def render_cosmos(ow, co, rels):
    if not rels: return
    latest = rels[0]
    rows = []
    for r in rels:
        d = datetime.fromisoformat(r['published'].replace('Z','+00:00'))
        rows.append(f'<tr><td class="muted">{h(r["tag"])}</td>'
                    f'<td class="muted">{d.strftime("%Y-%m-%d")}</td>'
                    f'<td>{r["n"]} files</td></tr>')
    body = [nav([(ow, f"{A(ow)}/index.html"), (co, None)]),
            f'<h1>Cosmos Cloud {h(co)} <span class="muted">· OpenWrt {h(ow)}</span></h1>',
            '<table><tr><th>Tag</th><th>Published</th><th>Files</th></tr>' + ''.join(rows) + '</table>']
    body.append(f'<h2>Files — {h(co)} · {h(ow)}</h2>')
    body.append(file_table(latest))
    body.append(f'<p class="back"><a href="{A(ow)}/index.html">← back</a></p>')
    write(f'{PREFIX}{ow}/{co}/index.html', page(f'Cosmos Cloud {co} — OpenWrt {ow}', '\n'.join(body)))

def file_table(rel):
    """Direct download links, no stub page."""
    if not rel.get('files'):
        return '<p class="muted">No files.</p>'
    rows = []
    for f in sorted(rel['files'], key=lambda f: size_sort_key(f['name'])):
        rows.append(f'<tr><td><a href="{h(f["url"])}" download>{h(f["name"])}</a></td><td class="size">{h(f["size"])}</td></tr>')
    return '<table><tr><th>File</th><th>Size</th></tr>' + ''.join(rows) + '</table>'

def render_files(ow, co, rels, latest_all, latest_by_ow):
    if not rels: return
    latest = rels[0]
    flags = []
    if latest_all and latest['id'] == latest_all['id']:
        flags.append('<span class="tag latest-tag">latest overall</span>')
    if (latest_by_ow.get(ow) or {}).get('id') == latest['id']:
        flags.append('<span class="tag latest-tag">latest</span>')
    if latest['pre']:
        flags.append('<span class="tag pre-tag">pre-release</span>')
    body = [nav([(ow, f"{A(ow)}/index.html"), (co, f"{A(ow, co)}/index.html"), ('files', None)]),
            f'<h1>📥 Files — Cosmos Cloud {h(co)} · OpenWrt {h(ow)}</h1>',
            f'<p class="muted">Release: <b>{h(latest["name"])}</b> · tag <code>{h(latest["tag"])}</code></p>'
            + ('<p>' + ' '.join(flags) + '</p>' if flags else ''),
            '<p>Files are served directly from GitHub Releases — click a filename to download.</p>'
            + file_table(latest),
            f'<p class="back"><a href="{A("index.html")}">← back</a></p>']
    write(f'{PREFIX}{ow}/{co}/files/index.html', page(f'Files — Cosmos Cloud {co} · OpenWrt {ow}', '\n'.join(body)))

def write(rel, content):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  wrote {rel}")

def main():
    global ROOT
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default='aseracorp/cosmos-owrt-releases')
    ap.add_argument('--root', default='.')
    ap.add_argument('--token', default='')
    args = ap.parse_args()
    ROOT = os.path.abspath(args.root)
    os.makedirs(ROOT, exist_ok=True)
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'cosmos-owrt-releases-generator'}
    if args.token: headers['Authorization'] = f'token {args.token}'

    releases = []
    page = 1
    while True:
        batch = api_get(f'https://api.github.com/repos/{args.source}/releases?per_page=100&page={page}', headers)
        if not batch: break
        releases.extend(batch)
        if len(batch) < 100: break
        page += 1
    if not releases:
        placeholder()
        return

    data = []
    for rel in releases:
        if rel.get('draft'): continue
        ow, co = parse_versions(rel.get('tag_name',''), rel.get('name',''))
        if not ow or not co:
            continue
        assets = []
        for a in rel.get('assets', []):
            if a.get('state') != 'uploaded': continue
            assets.append({
                'name': a['name'], 'size': human(a.get('size',0)),
                'url': a['browser_download_url']})
        data.append({
            'id': rel['id'], 'tag': rel['tag_name'], 'name': rel['name'] or rel['tag_name'],
            'published': rel['published_at'], 'ow': ow, 'co': co, 'pre': rel.get('prerelease', False),
            'files': assets, 'n': len(assets)})

    # determine "latest" (newest cosmos version)
    cand = [r for r in data if not r['pre']] or data
    latest_all = max(cand, key=lambda r: (vkey(r['co']), r['id']))
    latest_by_ow = {}
    for r in data:
        if not r['ow']: continue
        if r['ow'] not in latest_by_ow or (vkey(r['co']), r['id']) > (vkey(latest_by_ow[r['ow']]['co']), latest_by_ow[r['ow']]['id']):
            latest_by_ow[r['ow']] = r

    global PREFIX
    print(f'{len(data)} releases parsed')
    PREFIX = ''
    render_root(data, latest_all, latest_by_ow)
    render_latest_root(latest_all, latest_by_ow)
    for ow in sorted({r['ow'] for r in data if r['ow']}):
        ow_rel = [r for r in data if r['ow'] == ow]
        render_ow(ow, ow_rel, latest_by_ow)
        for co in sorted({r['co'] for r in ow_rel}, key=vkey, reverse=True):
            combo = [r for r in ow_rel if r['co'] == co]
            render_cosmos(ow, co, combo)
            render_files(ow, co, combo, latest_all, latest_by_ow)
    # latest/ subtree: mirror per-OpenWrt latest pages under latest/
    PREFIX = 'latest/'
    for ow, lat in latest_by_ow.items():
        ow_lat = [r for r in data if r['ow'] == ow and r['id'] == lat['id']]
        render_ow(ow, ow_lat, latest_by_ow)
        for co in sorted({r['co'] for r in ow_lat}, key=vkey, reverse=True):
            combo = [r for r in ow_lat if r['co'] == co]
            render_cosmos(ow, co, combo)
            render_files(ow, co, combo, latest_all, latest_by_ow)
    PREFIX = ''
    print('done.')

if __name__ == '__main__':
    main()