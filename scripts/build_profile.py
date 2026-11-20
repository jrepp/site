#!/usr/bin/env python3
"""Build the standalone profile. --refresh updates the public GitHub snapshot."""
import argparse
import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SELECTED = ['jelligothci', 'docuchango', 'merge-god', 'ipv6-parse', 'lm-based', 'mac-rom-atlas']

def fetch(path):
    req = Request('https://api.github.com/' + path, headers={'User-Agent': 'jrepp.com-profile', 'Accept': 'application/vnd.github+json'})
    with urlopen(req, timeout=20) as response:
        return json.load(response)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    snapshot = ROOT / 'assets/profile.json'
    if args.refresh:
        user = fetch('users/jrepp')
        repos = [fetch('repos/jrepp/' + name) for name in SELECTED]
        if any(r.get('private', True) for r in repos):
            raise ValueError('Only public repositories can be published')
        data = {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'profile': {k: user[k] for k in ['name', 'login', 'location', 'company', 'public_repos', 'followers', 'html_url']},
            'repos': [{k: r[k] for k in ['name', 'description', 'language', 'stargazers_count', 'html_url']} for r in repos],
        }
        snapshot.write_text(json.dumps(data, indent=2) + '\n')
    data = json.loads(snapshot.read_text())
    esc = lambda value: html.escape(str(value or ''), quote=True)
    cards = []
    for i, repo in enumerate(data['repos'], 1):
        cards.append(f'''<a class="project" href="{esc(repo['html_url'])}"><span class="project-number">0{i}</span><div><h3>{esc(repo['name'])} <span aria-hidden="true">↗</span></h3><p>{esc(repo['description'])}</p><div class="project-meta"><span>{esc(repo['language'] or 'Code')}</span><span data-stars="{esc(repo['name'])}">☆ {repo['stargazers_count']}</span></div></div></a>''')
    page = (ROOT / 'scripts/profile.html').read_text()
    values = {'projects': '\n'.join(cards), 'updated': data['updated_at'][:10], **data['profile']}
    for key, value in values.items():
        page = page.replace('{{' + key + '}}', value if key == 'projects' else esc(value))
    if '{{' in page:
        raise ValueError('Unresolved template fields')
    (ROOT / 'index.html').write_text(page)
    output = ROOT / 'build/profile'
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'index.html', output / 'index.html')
    shutil.copytree(ROOT / 'assets', output / 'assets', dirs_exist_ok=True)
    print(f'Built {output}')

if __name__ == '__main__':
    main()
