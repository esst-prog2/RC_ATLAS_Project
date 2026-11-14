"""Build editable HyperFrames scene files from the owner-approved storyboard."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
COMMON = '''
@font-face{font-family:RCAtlasUI;src:local('Segoe UI');font-weight:400}
@font-face{font-family:RCAtlasUI;src:local('Segoe UI Semibold');font-weight:600 800}
*{box-sizing:border-box}#root{position:absolute;inset:0;font-family:RCAtlasUI;color:#fff}
.surface{position:absolute;inset:0;background:#123b5d;overflow:hidden}
.content{position:absolute;inset:0;padding:110px 192px}
h1,h2,p{margin:0}h1,h2{font-weight:600;letter-spacing:-.025em;line-height:1.12}
.brand{display:flex;align-items:center;gap:26px;height:242px;font-size:78px;font-weight:600}
.brand img{display:block;width:360px;height:240px;object-fit:contain;flex-shrink:0}
.brand span{margin-left:-20px}.accent{color:#9ddbd5}
.footer-line{position:absolute;left:192px;right:192px;bottom:128px;height:3px;background:#52758c}
'''


def scene(name, duration, markup, css='', moves=''):
    folder = ROOT / 'compositions'
    folder.mkdir(exist_ok=True)
    # Keep the opening title fully visible from frame zero.
    fade = '1' if name == 'intro' else '0'
    text_fades = '' if name == 'intro' else f"tl.fromTo('#{name}-content',{{opacity:0}},{{opacity:1,duration:0.25,ease:'power1.out'}},0.2);"
    if name != 'closing':
        text_fades += f"tl.to('#{name}-content',{{opacity:0,duration:0.15,ease:'power1.in'}},{duration-0.5});"
    body = f'''<template>
<style>{COMMON}{css}</style>
<div id="root" data-composition-id="{name}" data-width="1920" data-height="1080" data-duration="{duration}">
 <div id="{name}-clip" class="clip" data-start="0" data-duration="{duration}" data-track-index="0" data-hold="Reading hold for concise approved copy" data-layout-allow-overlap>
  <div class="surface" id="{name}-surface"><div class="content" id="{name}-content">{markup}</div></div>
 </div>
</div>
<script>
const tl=gsap.timeline({{paused:true}});
tl.fromTo('#{name}-surface',{{opacity:{fade}}},{{opacity:1,duration:0.35,ease:'power1.out'}},0);
tl.fromTo('#{name}-content',{{y:12}},{{y:0,duration:0.4,ease:'power2.out'}},0);
{moves}
{text_fades}
window.__timelines=window.__timelines||{{}};window.__timelines['{name}']=tl;
</script></template>'''
    (folder / f'{name}.html').write_text(body, encoding='utf-8')


def main():
    logo = '<img src="assets/rc-atlas-approved.png" width="360" height="240" alt="Official RC Atlas logo" data-var-src="logo" data-start="0" data-duration="5.35">'
    scene('intro', 5.35,
          f'<div class="brand">{logo.replace("<img ", "<img id=\"intro-logo\" ")}<span>RC Atlas</span></div><h1 id="intro-title">From institutional data<br>to <span class="accent">coordinated action.</span></h1><div class="footer-line" aria-hidden="true"></div>',
          'h1{font-size:104px;margin-top:76px;line-height:1.14}',
          "")

    names = ['Project<br>management', 'Monitoring', 'Indicators', 'Analytics', 'Reporting']
    items = ''.join(f'<div class="cap" id="cap-{i}"><span>{name}</span><div class="cap-rule" id="cap-rule-{i}" aria-hidden="true"></div></div>' for i, name in enumerate(names))
    scene('capabilities', 7.35,
          '<h2>For institutional<br>project teams.</h2><div class="caps">' + items + '</div>',
          'h2{font-size:88px}.caps{display:grid;grid-template-columns:repeat(3,1fr);gap:42px 62px;margin-top:74px}.cap{font-size:68px;font-weight:600;line-height:1.16;min-height:180px;position:relative;padding-bottom:28px}.cap-rule{position:absolute;left:0;bottom:0;height:5px;width:100%;background:#9ddbd5;transform-origin:left}',
          '\n'.join(f"tl.fromTo('#cap-{i}',{{opacity:0.3}},{{opacity:1,duration:0.35}},0.15+{i}*0.08);tl.fromTo('#cap-rule-{i}',{{scaleX:0}},{{scaleX:1,duration:0.55,ease:'power2.out'}},{0.5+i*1.1});" for i in range(5)))

    labels = ['Assignment', 'Submission', 'Validation', 'Approval']
    stages = ''.join(f'<div class="stage" id="stage-{i}"><div class="node" id="node-{i}" aria-hidden="true"></div><div class="stage-label">{label}</div></div>' for i,label in enumerate(labels))
    scene('workflow', 7.35,
          '<h2>One example<br>workflow.</h2><div class="flow"><div class="connector" aria-hidden="true"></div>' + stages + '</div><p class="support">Clear responsibility at each handoff.</p>',
          'h2{font-size:92px}.flow{position:relative;display:grid;grid-template-columns:repeat(4,1fr);column-gap:24px;margin-top:112px}.connector{position:absolute;left:18px;right:340px;top:18px;height:4px;background:#52758c}.node{width:40px;height:40px;border:3px solid #9ddbd5;border-radius:50%;background:#123b5d;position:relative}.stage-label{font-size:74px;font-weight:600;margin-top:35px;letter-spacing:-.035em}.support{font-size:62px;color:#c8e8e6;margin-top:125px}',
          '\n'.join(f"tl.fromTo('#node-{i}',{{backgroundColor:'#123b5d'}},{{backgroundColor:'#9ddbd5',duration:0.35}},{0.6+i*1.3});" for i in range(4)))

    scene('evidence', 6.35,
          '<div class="evidence-rule" aria-hidden="true"></div><h2>From completed work<br>to <span>measurable results.</span></h2><p class="evidence-support">Reliable indicators require<br>evidence and clear methods.</p>',
          '.surface{background:#f4f8fa;color:#123b5d}.content{padding-top:178px}.evidence-rule{width:130px;height:7px;background:#11828a;margin-bottom:65px}h2{font-size:100px;line-height:1.14}h2 span{color:#07646b}.evidence-support{font-size:68px;line-height:1.35;margin-top:84px}',
          "tl.fromTo('.evidence-support',{opacity:0.2},{opacity:1,duration:0.4},0.5);")

    scene('closing', 5,
          f'<div class="brand">{logo.replace("5.35", "5").replace("<img ", "<img id=\"closing-logo\" ")}<span>RC Atlas</span></div><h2>Explore RC Atlas<br><span class="accent">on GitHub.</span></h2><p class="url">github.com/esst-prog2/<br>RC_ATLAS_Project</p><p class="availability">Local setup required · No public live demo</p>',
          '.content{padding-top:75px}.brand{height:220px}.brand img{width:330px;height:220px}h2{font-size:92px;margin-top:34px}.url{font-size:72px;line-height:1.18;margin-top:45px;color:#c8e8e6}.availability{font-size:72px;line-height:1.18;margin-top:30px}',
          "tl.fromTo('.url',{opacity:0.3},{opacity:1,duration:0.35},0.3);")

    hosts = ''.join(f'<div id="{name}" data-composition-id="{name}" data-composition-src="compositions/{name}.html" data-start="{start}" data-duration="{duration}" data-width="1920" data-height="1080" data-track-index="{i}" data-track-kind="graphics" data-layout-allow-overlap style="position:absolute;inset:0;z-index:{i}"></div>\n' for i,(name,start,duration) in enumerate([('intro',0,5.35),('capabilities',5,7.35),('workflow',12,7.35),('evidence',19,6.35),('closing',25,5)]))
    variables = json.dumps([{'id':'logo','type':'string','label':'Approved logo','default':'assets/rc-atlas-approved.png'}])
    (ROOT / 'index.html').write_text(f'''<!doctype html><html lang="en" data-composition-variables='{variables}'><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>RC Atlas — HW10 promotional video</title><link rel="icon" href="data:,"><script src="assets/gsap.min.js"></script><style>html,body{{margin:0;width:1920px;height:1080px;background:#123b5d;overflow:hidden}}#main{{position:relative;width:1920px;height:1080px}}</style></head><body><div id="main" data-composition-id="main" data-start="0" data-duration="30" data-fps="30" data-width="1920" data-height="1080">{hosts}</div><script>window.__timelines=window.__timelines||{{}};window.__timelines.main=gsap.timeline({{paused:true}});</script></body></html>''', encoding='utf-8')
    print('Built five scenes, 30 seconds, 1920x1080 at 30fps; original logo unchanged.')


if __name__ == '__main__':
    main()
