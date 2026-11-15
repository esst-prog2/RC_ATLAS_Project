"""Use the installed gstack browser for the authorized live-site acceptance pass."""
from pathlib import Path
import subprocess,json,time,sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
B=r'C:/Users/Elitebook/.codex/skills/gstack/browse/dist/browse.exe'
SITE='https://esst-prog2.github.io/RC_ATLAS_Project/'
def run(*args):
 r=subprocess.run([B,*args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
 if r.returncode or any(x in r.stdout for x in ['page.evaluate:','Command timed out','locator.click:']):raise RuntimeError(r.stdout+r.stderr)
 print(r.stdout.strip()[:250],flush=True)
 return r.stdout

def evaluate(source,name):
 target=HERE/name
 run('eval',str(source),'--out',str(target))
 return json.loads(target.read_text(encoding='utf-8-sig'))

def check_player(name):
 j=evaluate(HERE/'check_player.js',name)
 assert not j['overflow'] and not j['brokenAnchors'] and j['logoLoaded']
 assert j['video']['posterLoaded'] and j['video']['controls'] and not j['video']['autoplay']
 assert j['transcript']['items']==5 and j['transcript']['summaryHeight']>=44
 return j
if '--resume' not in sys.argv:
 run('goto',SITE);run('viewport','1440x1000');run('click','a.text-link[href$=video]')
 check_player('public-desktop.json')
 run('screenshot','--viewport',str(HERE/'public-desktop.png'))
 evaluate(HERE/'start_player.js','public-play-start.json')
 time.sleep(32)
 j=evaluate(ROOT/'docs/hw10/evidence/playback-status.js','public-playback-complete.json')
 assert j['ended'] and j['currentTime']==30 and j['error'] is None
 j=evaluate(ROOT/'docs/hw10/evidence/seek-workflow.js','public-seek.json');assert j['time']==15.5
 run('eval',str(HERE/'focus_video.js'));run('press','Space')
 j=evaluate(ROOT/'docs/hw10/evidence/playback-status.js','public-keyboard-play.json');assert not j['paused']
 run('press','Space')
 j=evaluate(ROOT/'docs/hw10/evidence/playback-status.js','public-keyboard-pause.json');assert j['paused']
else:
 run('goto',SITE)
for target in ['capabilities','workflow','explore']:run('click',f'header nav a[href$={target}]')
run('click','a.text-link[href$=video]');run('eval',str(HERE/'focus_transcript.js'));run('press','Enter')
assert check_player('public-desktop.json')['transcript']['open']
j=evaluate(ROOT/'docs/hw9/verify_preview.js','public-accessibility.json');assert not j['overflow'] and not j['lowContrast']
for width in [390,320]:
 run('viewport',f'{width}x844');run('click','a.text-link[href$=video]')
 check_player(f'public-mobile-{width}.json')
 j=evaluate(ROOT/'docs/hw9/verify_preview.js',f'public-mobile-{width}-accessibility.json');assert not j['overflow'] and not j['lowContrast']
 run('screenshot','--viewport',str(HERE/f'public-mobile-{width}.png'))
console=run('console','--errors');(HERE/'public-console.txt').write_text(console,encoding='utf-8')
assert '(no console errors)' in console
run('click','.button.light')
j=evaluate(HERE/'page_state.js','public-github-link.json');assert j['url'].rstrip('/')=='https://github.com/esst-prog2/RC_ATLAS_Project'
run('goto',SITE);run('click','a.text-link[href*=DEVELOPMENT]')
j=evaluate(HERE/'page_state.js','public-setup-link.json');assert '/blob/main/docs/DEVELOPMENT.md' in j['url']
run('goto',SITE);run('press','Tab');run('press','Enter')
j=evaluate(HERE/'page_state.js','public-skip-link.json');assert j['active']=='main'
run('viewport','1440x1000');run('click','a.text-link[href$=video]')
run('screenshot','--viewport',str(HERE/'public-desktop.png'))
print('PUBLIC BROWSER ACCEPTANCE PASS',flush=True)
