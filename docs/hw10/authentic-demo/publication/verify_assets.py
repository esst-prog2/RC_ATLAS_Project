"""Verify only the approved static video replacement, locally or at the public URL."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import urlopen,Request
import hashlib,json,re,subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SITE=ROOT/'promo'
FILES={'.nojekyll','favicon.ico','favicon.png','index.html','styles.css','logo.png','logo@2x.png','rc-atlas-promo.mp4','video-poster.jpg'}
HASH='cc8dbe3276a7c4ca8dc580e683b0a85852a99342f95327cb4b85a67452efc574'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()
def get(url,headers=None):
    with urlopen(Request(url,headers={'User-Agent':'RC-Atlas-HW10-verification',**(headers or {})}),timeout=40) as r:return r.status,r.read()
class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[];self.assets=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a':self.links.append(a['href'])
        if tag=='source':self.assets.append(a['src'])
        if tag=='video':self.video=a;self.assets.append(a['poster'])
def main():
    assert {p.name for p in SITE.iterdir()}==FILES
    old=git('show','640bcb2:promo/index.html').decode().replace('\r\n','\n')
    html=(SITE/'index.html').read_text(encoding='utf-8')
    strip=lambda s:re.sub(r'        <div class="video-feature" id="video">.*?\n        </div>','',s,flags=re.S)
    assert strip(html).replace('Watch the 30-second application demo','Watch the 30-second introduction')==strip(old)
    assert 'text-led' not in html and '29.8' in html and 'Task completion does not establish indicator outcomes.' in html
    page=Page();page.feed(html);assert len(page.ids)==len(set(page.ids))
    assert {'controls','playsinline'}<=set(page.video) and page.video['preload']=='none'
    assert not {'autoplay','loop'}&set(page.video)
    for link in page.links:
        if link.startswith('#'):assert link[1:] in page.ids
    assert all('v=authentic-cc8dbe3276a7' in a for a in page.assets)
    files=[]
    for name in sorted(FILES):
        path=SITE/name;assert path.is_file() and not path.is_symlink()
        data=path.read_bytes()
        if name not in {'index.html','rc-atlas-promo.mp4','video-poster.jpg'}:assert data==git('show','4be004c:'+name)
        if name.endswith(('.html','.css')):assert not re.search(rb'PRIVATE KEY|github_pat_|ghp_[A-Za-z0-9]|Bearer\s+[A-Za-z0-9]|(?:password|api_key)\s*=|(?<![A-Za-z])[A-Za-z]:[\\/]',data,re.I)
        if '--committed' in sys.argv:assert data==git('show','HEAD:promo/'+name),name
        files.append(dict(path=name,bytes=len(data),sha256=sha(data)))
    assert sha((SITE/'rc-atlas-promo.mp4').read_bytes())==HASH
    assert (SITE/'rc-atlas-promo.mp4').read_bytes()==(HERE.parent/'output/rc-atlas-authentic-demo.mp4').read_bytes()
    assert (SITE/'video-poster.jpg').read_bytes()==(HERE.parent/'output/poster.jpg').read_bytes()
    result=dict(status='PASS',files=files,video_sha256=HASH,old_video_hash='970f44467d8a7f58e483869c275b186aee5f0c92adcea4f0f4c4ad84ce963bd0',only_three_static_files_changed=True,other_markup_and_six_assets_unchanged=True,pages_source='gh-pages / (root)')
    if '--live' in sys.argv:
        base='https://esst-prog2.github.io/RC_ATLAS_Project/'
        checks=[]
        for name in ['',*sorted(FILES)]:
            status,data=get(base+name);expected=(SITE/(name or 'index.html')).read_bytes()
            assert status==200 and data==expected,(name,status,sha(data))
            checks.append(dict(path=name or '/',status=status,sha256=sha(data)))
        for asset in page.assets:
            status,data=get(base+asset);assert status==200 and data==(SITE/asset.split('?')[0]).read_bytes()
        status,data=get(base+page.assets[1],{'Range':'bytes=0-1023'})
        assert status==206 and data==(SITE/'rc-atlas-promo.mp4').read_bytes()[:1024]
        external=[]
        for link in sorted({x for x in page.links if x.startswith('https:')}):
            status,_=get(link);assert status==200;external.append(dict(url=link,status=status))
        result.update(public_url=base,http=checks,versioned_urls_match=True,range_206=True,external_links=external)
    (HERE/('public-http.json' if '--live' in sys.argv else 'manifest.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in {'files','http'}},indent=2))
if __name__=='__main__':main()
