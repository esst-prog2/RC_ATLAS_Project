"""Verify the exact HW9 public boundary; write a review manifest, never publish."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'promo'
EXPECTED = {'.nojekyll', 'favicon.svg', 'index.html', 'styles.css'}
EXTERNAL = {
    'https://github.com/esst-prog2/RC_ATLAS_Project',
    'https://github.com/esst-prog2/RC_ATLAS_Project/blob/main/docs/DEVELOPMENT.md',
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.assets, self.tags = [], [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'a':
            self.links.append(a['href'])
        if tag == 'link':
            self.assets.append(a['href'])
        if tag == 'img':
            assert 'alt' in a, 'Image lacks an alternative-text attribute'
            self.assets.append(a['src'])


def main():
    assert not PUBLIC.is_symlink() and PUBLIC.resolve().parent == ROOT
    actual = {p.name for p in PUBLIC.iterdir()}
    assert actual == EXPECTED, f'Unexpected or missing public files: {actual ^ EXPECTED}'
    files = []
    for name in sorted(EXPECTED):
        p = PUBLIC / name
        assert p.is_file() and not p.is_symlink() and p.stat().st_nlink == 1
        data = p.read_bytes()
        committed = git('show', f'HEAD:promo/{name}')
        assert data == committed, f'Uncommitted public bytes in {name}'
        assert not re.search(rb'PRIVATE KEY|github_pat_|ghp_[A-Za-z0-9]|Bearer\s+[A-Za-z0-9]|(?:password|api_key)\s*=|(?<![A-Za-z])[A-Za-z]:[\\/]', data, re.I), f'Suspicious public content: {name}'
        with urlopen(f'http://127.0.0.1:8770/{name}', timeout=10) as response:
            assert response.status == 200 and response.read() == data
        files.append({'source': f'promo/{name}', 'published_path': name,
                      'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                      'git_blob': git('rev-parse', f'HEAD:promo/{name}').decode().strip(),
                      'local_http_status': 200})
    page = Page()
    html = (PUBLIC / 'index.html').read_text(encoding='utf-8')
    page.feed(html)
    assert len(page.ids) == len(set(page.ids))
    assert page.tags.count('main') == 1 and page.tags.count('h1') == 1
    assert not set(page.tags) & {'script', 'iframe', 'video', 'form', 'object', 'embed'}
    for href in page.links:
        if href.startswith('#'):
            assert href[1:] in page.ids
        else:
            assert href in EXTERNAL, f'Unapproved outbound link: {href}'
    for asset in page.assets:
        assert asset in EXPECTED and not urlparse(asset).scheme
    assert 'url(' not in (PUBLIC / 'styles.css').read_text(encoding='utf-8')
    assert 'http' not in (PUBLIC / 'favicon.svg').read_text(encoding='utf-8').replace('http://www.w3.org/2000/svg', '')
    assert (PUBLIC / '.nojekyll').stat().st_size == 0
    tree = git('rev-parse', 'HEAD:promo').decode().strip()
    entries = git('ls-tree', tree).decode().splitlines()
    assert len(entries) == 4 and all(e.startswith('100644 blob ') for e in entries)
    manifest = {
        'status': 'VALIDATED_LOCAL_CANDIDATE_NOT_PUBLISHED',
        'source_commit': git('rev-parse', 'HEAD').decode().strip(),
        'public_git_tree': tree,
        'proposed_repository': 'esst-prog2/RC_ATLAS_Project',
        'proposed_source': {'method': 'Deploy from a branch', 'branch': 'gh-pages', 'folder': '/'},
        'expected_url_not_yet_verified': 'https://esst-prog2.github.io/RC_ATLAS_Project/',
        'files': files,
        'total_bytes': sum(f['bytes'] for f in files),
        'external_links': sorted(EXTERNAL),
        'product_screenshots': [],
        'fallback': 'Owner-approved labelled text explanations; no verified runtime screenshot available.',
        'review': 'Four files manually reviewed. No credentials, personal/institutional data, application code, technical reports, or preview artifacts in this tree.',
    }
    (ROOT / 'docs/hw9/PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': manifest['status'], 'files': len(files), 'bytes': manifest['total_bytes'], 'git_tree': tree}))


if __name__ == '__main__':
    main()
