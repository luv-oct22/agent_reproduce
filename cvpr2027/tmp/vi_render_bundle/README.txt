Visual-interaction frames: render on a Windows PC with an RTX 4090

1. Install Blender 3.6 LTS (same major version as the server, 3.6.23):
   https://download.blender.org/release/Blender3.6/  -> blender-3.6.23-windows-x64.msi (or the .zip)
2. Copy this whole folder to the PC, e.g. D:\vi_render_bundle
3. Open PowerShell in that folder and run:
     powershell -ExecutionPolicy Bypass -File .\render_windows.ps1 -Blender "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
   Optional: -Device CUDA if OPTIX fails; -Samples 32 is the default.
   Quick test first (one world):  add  -Samples 8  and stop it with Ctrl+C after the first world.
4. Expect 54 worlds x 72 frames = 3888 PNGs under frames\visual_interaction\...
5. Copy the whole frames\visual_interaction folder back to the server, merging into
     agent_reproduce/renders/visual_interaction/
   (same relative paths; only e*.png files are new).
6. On the server: python -m src.visual_interaction status   -> frames rendered for 48/48 worlds
