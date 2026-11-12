param(
    [Parameter(Mandatory = $true)][string]$TextFile,
    [Parameter(Mandatory = $true)][string]$OutFile,
    [int]$Rate = 2,
    [string]$Voice = 'Microsoft Huihui Desktop'
)

Add-Type -AssemblyName System.Speech

$text = Get-Content -LiteralPath $TextFile -Encoding UTF8 -Raw
if (-not $text -or $text.Trim().Length -eq 0) {
    Write-Error "empty text file: $TextFile"
    exit 1
}

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try { $synth.SelectVoice($Voice) } catch { }
$synth.Rate = $Rate
$synth.SetOutputToWaveFile($OutFile)
$synth.Speak($text)
$synth.Dispose()

Write-Output "wrote $OutFile"
