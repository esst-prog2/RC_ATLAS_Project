"""Read-only verification of the approved logo deployment; never publish."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
API = 'https://api.github.com/repos/esst-prog2/RC_ATLAS_Project'
SITE = 'https://esst-prog2.github.io/RC_ATLAS_Project/'
COMMIT = '23de743274a68e1a0863ca733e13c1a5ce94a348'
RUN = 43476713822


def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'RC-Atlas-HW9-verification'}), timeout=30) as response:
        return response.status, response.read(), response.headers.get('Content-Type')


def api(path):
    return json.loads(fetch(API + path)[1])


def main():
    manifest = json.loads((HERE / 'PUBLICATION_MANIFEST.json').read_text())
    run = api(f'/actions/runs/{RUN}')
    assert run['head_sha'] == COMMIT
    assert run['status'] == 'completed' and run['conclusion'] == 'success', (run['status'], run['conclusion'])
    assert api('/git/ref/heads/gh-pages')['object']['sha'] == COMMIT
    commit = api(f'/git/commits/{COMMIT}')
    assert commit['tree']['sha'] == manifest['public_git_tree']
    tree = api('/git/trees/' + commit['tree']['sha'])
    expected = {f['published_path']: f for f in manifest['files']}
    assert not tree['truncated'] and len(tree['tree']) == 7
    assert {f['path'] for f in tree['tree']} == set(expected)
    for f in tree['tree']:
        assert f['type'] == 'blob' and f['mode'] == '100644'
        assert f['sha'] == expected[f['path']]['git_blob']
    files = []
    for name, approved in expected.items():
        status, data, content_type = fetch(SITE + name)
        digest = hashlib.sha256(data).hexdigest()
        assert status == 200 and digest == approved['sha256'], f'Public bytes differ: {name}'
        files.append({'file': name, 'http_status': status, 'bytes': len(data), 'sha256': digest, 'content_type': content_type})
    status, root, _ = fetch(SITE)
    assert status == 200 and hashlib.sha256(root).hexdigest() == expected['index.html']['sha256']
    excluded = {}
    for name in ['favicon.svg', 'PROCESS.md', 'docs/ui-01/PHASE_1_REPORT.md', 'logitrack_studio.html', 'Site.txt']:
        try:
            status = fetch(SITE + name)[0]
        except HTTPError as error:
            status = error.code
        assert status == 404, (name, status)
        excluded[name] = status
    result = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'site': SITE,
              'commit': COMMIT, 'tree': manifest['public_git_tree'],
              'run': {'id': RUN, 'status': run['status'], 'conclusion': run['conclusion'], 'url': run['html_url']},
              'files': files, 'excluded_paths': excluded}
    (HERE / 'public-evidence/deployment.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'result': 'PASS', 'run': RUN, 'files': len(files), 'bytes': sum(f['bytes'] for f in files)}))


if __name__ == '__main__':
    main()
