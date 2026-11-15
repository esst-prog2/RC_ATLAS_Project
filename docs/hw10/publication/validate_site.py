"""Verify the HW10 static publication boundary; does not publish."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re,subprocess,sys
from urllib.request import urlopen,Request
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
PUBLIC=ROOT/'promo'
EXPECTED={'.nojekyll','favicon.ico','favicon.png','index.html','styles.css','logo.png','logo@2x.png','rc-atlas-promo.mp4','video-poster.jpg'}
EXTERNAL={'https://github.com/esst-prog2/RC_ATLAS_Project','https://github.com/esst-prog2/RC_ATLAS_Project/blob/main/docs/DEVELOPMENT.md'}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
class Page(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.links=[];self.assets=[];self.tags=[];self.video=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);self.tags.append(tag)
  if 'id' in a:self.ids.append(a['id'])
  if tag=='a':self.links.append(a['href'])
  if tag=='link':self.assets.append(a['href'])
  if tag in ['img','source']:self.assets.append(a['src'])
  if tag=='img':
   assert 'alt' in a
   self.assets.extend(x.strip().split()[0] for x in a.get('srcset','').split(',') if x)
  if tag=='video':self.video=a;self.assets.append(a['poster'])
def main():
 assert {p.name for p in PUBLIC.iterdir()}==EXPECTED
 files=[]
 for name in sorted(EXPECTED):
  p=PUBLIC/name;assert p.is_file() and not p.is_symlink() and p.stat().st_nlink==1
  data=p.read_bytes()
  if '--committed' in sys.argv:assert data==git('show',f'HEAD:promo/{name}')
  if name.endswith(('.html','.css')):
   assert not re.search(rb'PRIVATE KEY|github_pat_|ghp_[A-Za-z0-9]|Bearer\s+[A-Za-z0-9]|(?:password|api_key)\s*=|(?<![A-Za-z])[A-Za-z]:[\\/]',data,re.I)
  with urlopen('http://127.0.0.1:8788/'+name,timeout=15) as r:assert r.status==200 and r.read()==data
  files.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':git('hash-object',str(p)).decode().strip()})
 html=(PUBLIC/'index.html').read_text(encoding='utf-8');page=Page();page.feed(html)
 assert len(page.ids)==len(set(page.ids))
 assert not set(page.tags)&{'script','iframe','form','object','embed'}
 assert page.tags.count('video')==1 and page.tags.count('h1')==1
 assert 'controls' in page.video and 'playsinline' in page.video
 assert page.video['preload']=='none' and not {'autoplay','loop'}&set(page.video)
 assert page.video['aria-labelledby'] in page.ids and page.video['aria-describedby'] in page.ids
 for link in page.links:
  assert (link[1:] in page.ids) if link.startswith('#') else (link in EXTERNAL or link=='rc-atlas-promo.mp4'),link
 assert {a.split("?",1)[0] for a in page.assets}<=EXPECTED
 assert 'url(' not in (PUBLIC/'styles.css').read_text()
 # Remove only the added block/link: all previous markup must remain identical.
 restored=re.sub(r'        <div class="video-feature" id="video">.*?\n        </div>\n','',html,flags=re.S)
 restored=restored.replace('\n              <a class="text-link" href="#video">Watch the 30-second introduction</a>','')
 old=git('show','834e56b:promo/index.html').decode().replace('\r\n','\n')
 old=re.sub(r'        <!-- A future accessible promotional video.*?-->\n','',old)
 restored=restored.replace('styles.css?v=hw10','styles.css')
 assert restored==old,'Existing page markup changed'
 for name in ['logo.png','logo@2x.png','favicon.png','favicon.ico','.nojekyll']:
  assert (PUBLIC/name).read_bytes()==git('show','834e56b:promo/'+name)
 digest=hashlib.sha256((PUBLIC/'rc-atlas-promo.mp4').read_bytes()).hexdigest()
 assert digest=='970f44467d8a7f58e483869c275b186aee5f0c92adcea4f0f4c4ad84ce963bd0'
 assert (PUBLIC/'rc-atlas-promo.mp4').read_bytes()==(ROOT/'docs/hw10/output/rc-atlas-promo.mp4').read_bytes()
 with Image.open(PUBLIC/'video-poster.jpg') as image:
  assert image.size==(1280,720) and image.format=='JPEG';assert not image.getexif();image.verify()
 responses=[]
 for url in sorted(EXTERNAL):
  with urlopen(Request(url,headers={'User-Agent':'RC-Atlas-HW10'}),timeout=30) as r:assert r.status==200;responses.append({'url':url,'status':r.status})
 with urlopen(Request('http://127.0.0.1:8788/rc-atlas-promo.mp4',headers={'Range':'bytes=0-31'})) as r:assert r.status==206 and len(r.read())==32
 result={'files':files,'total_bytes':sum(f['bytes'] for f in files),'external_links':responses,'source':{'branch':'gh-pages','folder':'/'},'video_unchanged':True,'existing_markup_and_brand_assets_preserved':True,'poster':'Frame at 2.5 seconds from approved MP4, scaled to 1280x720; no generated imagery','transcript':'Inline complete text and visual sequence description; video has no audio','validated_source_commit':git('rev-parse','HEAD').decode().strip()}
 if '--committed' in sys.argv:result['public_git_tree']=git('rev-parse','HEAD:promo').decode().strip()
 (Path(__file__).parent/'PUBLICATION_MANIFEST.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'result':'PASS','files':len(files),'bytes':result['total_bytes'],'video_sha256':digest}))
if __name__=='__main__':main()
