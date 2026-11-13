"""Deterministic raster sizing of the owner-approved logo. No cropping or redrawing."""
import base64
import hashlib
import json
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / 'approved-source.png'
EXPECTED_SHA = '479835cff8a75eabb4e8f62e1d51093a374e775344628a77db1b2d2c10459cc7'


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED_SHA
    image = Image.open(SOURCE).convert('RGBA')
    assert image.size == (1536, 1024)
    output = HERE / 'prepared'
    output.mkdir(exist_ok=True)
    for width, name in [(192, 'logo.png'), (384, 'logo@2x.png')]:
        image.resize((width, width * 2 // 3), Image.Resampling.LANCZOS).save(output / name, optimize=True)
    # A transparent square canvas contains the entire original 3:2 image.
    # It changes only the canvas, never the artwork's proportions or margins.
    square = Image.new('RGBA', (1536, 1536))
    square.paste(image, (0, 256))
    for size in (48, 96, 192, 384):
        square.resize((size, size), Image.Resampling.LANCZOS).save(output / f'icon-{size}.png', optimize=True)
    square.save(output / 'favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
    files = []
    for p in sorted(output.iterdir()):
        files.append({'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    (HERE / 'ASSET_MANIFEST.json').write_text(json.dumps({
        'source_sha256': EXPECTED_SHA, 'source_dimensions': [1536, 1024],
        'method': 'Pillow Lanczos proportional resizing; transparent square padding for icons; original alpha retained; no crop, redraw, recolour or SVG conversion',
        'files': files,
    }, indent=2) + '\n', encoding='utf-8')
    logo = base64.b64encode((output / 'logo@2x.png').read_bytes()).decode()
    icon = base64.b64encode((output / 'icon-96.png').read_bytes()).decode()
    panels = ''
    for background, colour in [('#ffffff', '#123b5d'), ('#123b5d', '#ffffff'), ('#080f18', '#ffffff')]:
        samples = ''.join(f'<figure><img src="data:image/png;base64,{icon}" width="{size}" height="{size}" alt="RC Atlas icon"><figcaption>{size}px</figcaption></figure>' for size in (16, 24, 32, 48, 96))
        panels += f'<section style="background:{background};color:{colour}"><h2>{background}</h2><div class="brand"><img src="data:image/png;base64,{logo}" width="90" height="60" alt="">RC Atlas</div><div class="samples">{samples}</div></section>'
    (HERE / 'preview.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RC Atlas approved logo sizing review</title><style>body{margin:0;font:18px/1.5 system-ui;background:#edf2f5;color:#123b5d}main{max-width:1000px;margin:auto;padding:24px}h1{font-size:30px}section{padding:24px;margin:20px 0}.brand{display:flex;align-items:center;gap:12px;font-size:25px;font-weight:700}.samples{display:flex;align-items:center;gap:24px;flex-wrap:wrap}figure{margin:24px 0 0}figcaption{font-size:14px}img{object-fit:contain}</style><main><h1>Approved logo: background and size review</h1><p>Exact source artwork, resized only. Original transparency and margins retained. Small favicon details are limited by the supplied image composition.</p>' + panels + '</main></html>', encoding='utf-8')
    print(json.dumps(files, indent=2))


if __name__ == '__main__':
    main()
