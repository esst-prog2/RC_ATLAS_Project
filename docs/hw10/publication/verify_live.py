"""Read-only byte, source-boundary and HTTP-range verification of the live HW10 site."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import hashlib,json
HERE=Path(__file__).resolve().parent
SITE='https://esst-prog2.github.io/RC_ATLAS_Project/'
def fetch(url,headers=None):
 with urlopen(Request(url,headers={'User-Agent':'RC-Atlas-HW10-verification',**(headers or {})}),timeout=30) as r:return r.status,r.read(),dict(r.headers)
def main():
 m=json.loads((HERE/'PUBLICATION_MANIFEST.json').read_text());results=[]
 for f in m['files']:
  status,data,headers=fetch(SITE+f['path'])
  assert status==200 and hashlib.sha256(data).hexdigest()==f['sha256'],f['path']
  results.append({'path':f['path'],'status':status,'bytes':len(data),'sha256':f['sha256'],'content_type':next((v for k,v in headers.items() if k.lower()=='content-type'),None)})
 status,data,_=fetch(SITE)
 assert hashlib.sha256(data).hexdigest()==next(f['sha256'] for f in m['files'] if f['path']=='index.html')
 status,segment,headers=fetch(SITE+'rc-atlas-promo.mp4',{'Range':'bytes=100000-100031'})
 assert status==206 and len(segment)==32
 assert segment==(HERE.parents[2]/'promo/rc-atlas-promo.mp4').read_bytes()[100000:100032]
 excluded={}
 for path in ['PROCESS.md','Site.txt','docs/ui-01/PHASE_1_REPORT.md','docs/hw10/video/index.html','logitrack_studio.html']:
  try:code=fetch(SITE+path)[0]
  except HTTPError as e:code=e.code
  assert code==404,(path,code)
  excluded[path]=code
 links=[]
 for link in m['external_links']:
  status,_,_=fetch(link['url']);assert status==200;links.append({'url':link['url'],'status':status})
 result={'site':SITE,'files':results,'range_status':206,'range_bytes_verified':32,'external_links':links,'excluded_paths':excluded,'result':'PASS'}
 (HERE/'public-http.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps({'result':'PASS','public_files':len(results),'range_status':206,'excluded_404':len(excluded)}))
if __name__=='__main__':main()
