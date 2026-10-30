# Render visual-interaction outcome frames on Windows. Run from this folder in PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\render_windows.ps1 -Blender "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
# Resumable: frames that already exist are skipped. Log per world: <world>\render.log
param(
  [string]$Blender = "C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
  [string]$Device = "OPTIX",          # OPTIX (RTX, fastest) | CUDA | CPU
  [int]$Samples = 32
)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $root "code\src\simulation\blender_visual_interaction.py"
$manifests = Get-ChildItem -Path (Join-Path $root "frames") -Recurse -Filter frames.json | Sort-Object FullName
if (-not (Test-Path $Blender)) { Write-Error "Blender not found: $Blender"; exit 1 }
Write-Host "Worlds: $($manifests.Count)  device: $Device  samples: $Samples"
$failed = @()
$i = 0
foreach ($m in $manifests) {
  $i++
  $dir = $m.DirectoryName
  Write-Host ("[{0}/{1}] {2}  {3}" -f $i, $manifests.Count, $dir.Substring($root.Length + 1), (Get-Date -Format HH:mm:ss))
  & $Blender --background --python-exit-code 1 --python $script -- --manifest $m.FullName --device $Device --samples $Samples *> (Join-Path $dir "render.log")
  if ($LASTEXITCODE -ne 0) { $failed += $dir; Write-Host "  FAILED (see render.log)" -ForegroundColor Red }
}
$png = (Get-ChildItem -Path (Join-Path $root "frames") -Recurse -Filter e*.png).Count
Write-Host "Done. PNG frames: $png (expected 3888). Failed worlds: $($failed.Count)"
$failed | ForEach-Object { Write-Host "  $_" }
