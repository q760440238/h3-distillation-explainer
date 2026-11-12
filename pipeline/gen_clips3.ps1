param(
    [string]$Photo = 'E:\minimaxh3\out\ref_photo.jpg',
    [string]$OutDir = 'E:\minimaxh3\out\clips'
)

$ErrorActionPreference = 'Continue'
$SDK = 'E:\minimaxh3\bin\rocm-core\PFiles64\AMD\ROCm\7.2'
$M = 'E:\minimaxh3\models'
$EXE = 'E:\minimaxh3\build-hip\bin\sd-cli.exe'
$env:PATH = "$SDK\bin;$env:PATH"
New-Item -ItemType Directory -Force $OutDir | Out-Null

$base = 'wide full body shot, the young man in light blue hanfu standing and teaching, large translucent holographic computer panel floating in front of him, blue abstract interface and charts on the panel, futuristic minimal white studio, cinematic soft light, camera at eye level'

$shots = @(
    @{ n = 'g1'; seed = 4101; extra = 'raising his right hand toward the panel' },
    @{ n = 'g2'; seed = 4102; extra = 'standing with hands clasped, speaking calmly' },
    @{ n = 'g3'; seed = 4103; extra = 'turning his head slightly to the panel then back' },
    @{ n = 'g4'; seed = 4104; extra = 'gesturing with an open palm toward the viewer' },
    @{ n = 'g5'; seed = 4105; extra = 'taking a small step and pointing at a chart' },
    @{ n = 'g6'; seed = 4106; extra = 'explaining with both hands moving slowly' }
)

foreach ($s in $shots) {
    $out = Join-Path $OutDir ("clip_{0}.webm" -f $s.n)
    if (Test-Path $out) { Write-Output "skip $($s.n)"; continue }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $prompt = "$base, $($s.extra)"
    $null = & $EXE -M vid_gen `
        --diffusion-model "$M\diffusion_models\minimax_h3_fl2va_pruned-Q4_K.gguf" `
        --vae "$M\vae\minimax_h3_video_vae_fp16.safetensors" `
        --audio-vae "$M\vae\minimax_h3_audio_vae_fp32.safetensors" `
        --llm "$M\text_encoders\qwen3vl_32b_minimax_h3-Q2_K_M.gguf" `
        -r $Photo -p $prompt `
        --cfg-scale 1.0 --steps 8 -s $s.seed --rng cpu -W 640 -H 384 --fps 24 --video-frames 48 `
        --offload-to-cpu --mmap --max-vram ROCm0=12 -o $out 2>&1 | Out-String
    $sw.Stop()
    $ok = Test-Path $out
    Write-Output ("clip_{0}: {1} {2:N0}s" -f $s.n, $(if ($ok) { 'OK' } else { 'FAILED' }), $sw.Elapsed.TotalSeconds)
}
Write-Output 'BATCH G DONE'
