"""Verify the exact review MP4 and decode representative frames using local tools."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent.parent
video=ROOT/'output/rc-atlas-promo.mp4'
bin=ROOT/'tooling/ffmpeg-9.0.2-essentials_build/bin'
evidence=ROOT/'evidence'
r=subprocess.run([str(bin/'ffprobe.exe'),'-v','error','-count_frames','-show_streams','-show_format','-of','json',str(video)],capture_output=True,text=True,check=True)
probe=json.loads(r.stdout)
(evidence/'render-probe.json').write_text(json.dumps(probe,indent=2),encoding='utf-8')
assert len(probe['streams'])==1,'Unexpected stream inventory'
s=probe['streams'][0]
assert s['codec_type']=='video' and s['codec_name']=='h264'
assert (s['width'],s['height'])==(1920,1080)
assert s['avg_frame_rate']=='30/1' and s['pix_fmt']=='yuv420p'
assert int(s['nb_read_frames'])==900
assert abs(float(probe['format']['duration'])-30)<0.001
r=subprocess.run([str(bin/'ffmpeg.exe'),'-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True,check=True)
assert not r.stderr.strip(),r.stderr
frames=evidence/'decoded';frames.mkdir(exist_ok=True)
for t in [0,2.5,8.5,15.5,22,27.5,29.966667]:
 subprocess.run([str(bin/'ffmpeg.exe'),'-v','error','-ss',str(t),'-i',str(video),'-frames:v','1','-update','1','-y',str(frames/f'frame-{t}.png')],check=True)
# Verify the streaming index precedes media data without changing the file.
boxes=[]
with video.open('rb') as f:
 while True:
  start=f.tell();header=f.read(8)
  if len(header)<8:break
  size=int.from_bytes(header[:4],'big');kind=header[4:].decode('ascii')
  if size==1:size=int.from_bytes(f.read(8),'big')
  boxes.append({'type':kind,'offset':start,'size':size})
  if size==0:break
  f.seek(start+size)
positions={b['type']:b['offset'] for b in boxes}
assert positions['moov']<positions['mdat'],'MP4 needs faststart before future embedding'
source=ROOT.parent/'hw9/branding/approved-source.png'
logo=ROOT/'video/assets/rc-atlas-approved.png'
assert source.read_bytes()==logo.read_bytes()
manifest={'file':'rc-atlas-promo.mp4','sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'bytes':video.stat().st_size,'duration_seconds':30,'frames':900,'fps':30,'width':1920,'height':1080,'codec':'h264','pixel_format':'yuv420p','audio_streams':0,'decode_errors':0,'faststart':True,'mp4_boxes':boxes,'logo_sha256':hashlib.sha256(logo.read_bytes()).hexdigest()}
(evidence/'render-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
