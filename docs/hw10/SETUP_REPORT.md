# HW10 local setup and technical render

14 November 2026. Codex operated the actual HyperFrames CLI; Claude Code was not used. The owner explicitly authorized this host substitution. HyperFrames supports Codex in its upstream quickstart, so the video-generation method is unchanged; this does not claim independent confirmation from the professor about the host substitution.

All project artifacts, dependencies, npm cache, HyperFrames config/cache/temp and downloaded tools are under the canonical RC_Atlas_Project directory. No global package installation, machine PATH change, execution-policy change, new worktree, backend runtime or website modification was performed. The wrapper hf.py passes explicit environment paths per process and disables telemetry/cloud auto-install/update behavior. Tooling and disposable caches are ignored by Git.

- Node v24.19.0 and npm.cmd 11.17.0.
- Pinned npm `hyperframes` 0.9.42 and GSAP 3.14.2, installed with --ignore-scripts; package-lock.json records integrity values. Local CLI prints 0.9.42.
- FFmpeg/FFprobe 9.0.2 essentials Windows build. Source: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip (provider linked by ffmpeg.org). Archive SHA-256 `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba` matched the provider's .sha256 before extraction. No tool binary is committed or published.
- Chrome explicitly configured at its existing installed executable. HyperFrames confirmed AMD hardware graphics; forced single-worker screenshot capture uses its built-in low-memory rendering path, not a substituted renderer.
- Doctor's overall result is false because available RAM was about 0.9 GB and optional Docker, transcription/voice/music tools were absent. Node, Chrome, FFmpeg and FFprobe checks passed. Those optional providers are unnecessary for this approved silent local film. No claim of a fully green doctor result.

Initial `init .` correctly refused the already populated dependency directory. A fresh ignored `.tmp/smoke` subfolder scaffolded successfully; no existing file was overwritten by the scaffolder. The separate technical-test.html render reported no root index.html during project preflight but nevertheless rendered the explicitly selected composition successfully. The complete film will have its required root index.html, resolving that preflight warning.

Technical test command: `python docs/hw10/video/hf.py render --composition technical-test.html --fps 30 --quality draft --workers 1 --low-memory-mode -o ../evidence/technical-test.mp4`.

Actual result: 60 frames, 2.0 seconds, 1920x1080, H.264, yuv420p, 30fps, approximately 21 KB; about 22 seconds of render time. FFprobe output and a decoded frame are in evidence/. This is proof the preferred local renderer runs; no screen-recording fallback is needed.

The original approved logo is copied byte-for-byte into video/assets. The final composition uses locally installed Segoe UI through explicit local font faces; fonts are not redistributed. No generated product screenshots, institutional data or live providers are used.
