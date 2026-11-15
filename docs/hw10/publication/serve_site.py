"""Serve only the static promo directory locally, including byte-range playback."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('review_server',Path(__file__).resolve().parents[1]/'video/serve_review.py')
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
server.ROOT=Path(__file__).resolve().parents[3]/'promo'
print('Static promo preview: http://127.0.0.1:8788/',flush=True)
server.ThreadingHTTPServer(('127.0.0.1',8788),server.Handler).serve_forever()
