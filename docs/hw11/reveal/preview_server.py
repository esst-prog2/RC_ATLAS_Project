"""Serve only the HW11 deck, using the future GitHub Pages URL path."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
ROOT = Path(__file__).resolve().parent
class Preview(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split('?')[0] in ('/RC_ATLAS_Project/slides/', '/RC_ATLAS_Project/slides/index.html'):
            payload = (ROOT/'slides/index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_error(404)
HTTPServer(('127.0.0.1', 8871), Preview).serve_forever()
