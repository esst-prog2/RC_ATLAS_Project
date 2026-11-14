"""Run pinned HyperFrames with project-local cache/config/temp and explicit tools."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT.parent / 'tooling'


def environment():
    env = os.environ.copy()
    for key, relative in {
        'TEMP': '../tooling/temp', 'TMP': '../tooling/temp', 'TMPDIR': '../tooling/temp',
        'npm_config_cache': '.cache/npm', 'XDG_CACHE_HOME': '.cache',
        'PUPPETEER_CACHE_DIR': '.cache/puppeteer',
        'HYPERFRAMES_CONFIG_DIR': '.cache/hyperframes-config',
        'HYPERFRAMES_CACHE_DIR': '.cache/hyperframes',
        'HYPERFRAMES_EXTRACT_CACHE_DIR': '.cache/extract',
        'HYPERFRAMES_FONT_CACHE_DIR': '.cache/fonts',
        'XDG_CONFIG_HOME': '.cache/config', 'XDG_STATE_HOME': '.cache/state',
    }.items():
        p = ROOT / relative
        p.mkdir(parents=True, exist_ok=True)
        env[key] = str(p)
    ffbin = TOOLS / 'ffmpeg-9.0.2-essentials_build/bin'
    env.update({
        'HYPERFRAMES_FFMPEG_PATH': str(ffbin / 'ffmpeg.exe'),
        'HYPERFRAMES_FFPROBE_PATH': str(ffbin / 'ffprobe.exe'),
        'HYPERFRAMES_BROWSER_PATH': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        'HYPERFRAMES_NO_TELEMETRY': '1', 'DO_NOT_TRACK': '1',
        'HYPERFRAMES_NO_AUTO_INSTALL': '1', 'HYPERFRAMES_NO_UPDATE_CHECK': '1',
        'HYPERFRAMES_SKIP_SKILLS': '1',
    })
    env['PATH'] = str(ffbin) + os.pathsep + env['PATH']
    return env


if __name__ == '__main__':
    raise SystemExit(subprocess.call(['node', str(ROOT / 'node_modules/hyperframes/bin/hyperframes.mjs'), *sys.argv[1:]], cwd=ROOT, env=environment()))
