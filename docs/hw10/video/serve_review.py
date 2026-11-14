"""Loopback-only review server with MP4 byte ranges; serves output/ only."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import re
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent.parent/'output'
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        header=self.headers.get('Range')
        if not header or urlsplit(self.path).path!='/rc-atlas-promo.mp4':
            return super().do_GET()
        path=ROOT/'rc-atlas-promo.mp4'
        size=path.stat().st_size
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',header)
        if not match or not any(match.groups()):
            self.send_error(416);return
        a,b=match.groups()
        start=int(a) if a else max(0,size-int(b))
        end=min(int(b),size-1) if a and b else size-1
        if start>end or start>=size:
            self.send_error(416);return
        self.send_response(206)
        self.send_header('Content-Type','video/mp4')
        self.send_header('Accept-Ranges','bytes')
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length',str(end-start+1))
        self.end_headers()
        try:
            with path.open('rb') as f:
                f.seek(start);remaining=end-start+1
                while remaining:
                    data=f.read(min(65536,remaining))
                    if not data:break
                    self.wfile.write(data);remaining-=len(data)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            pass
if __name__=='__main__':
    print('Local review: http://127.0.0.1:8787/review.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8787),Handler).serve_forever()
