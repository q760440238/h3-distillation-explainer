"""Generate one WAV per script paragraph with Windows SAPI, plus a manifest.

Per-paragraph audio is what lets the video timing follow the narration instead of
guessing where each sentence lands.
"""

import io
import json
import os
import re
import subprocess
import wave

SCRIPT = r'E:\minimaxh3\out\distill_script.txt'
OUT_DIR = r'E:\minimaxh3\out\tts'
SAY_PS1 = r'E:\minimaxh3\out\tts_say.ps1'
RATE = 5

os.makedirs(OUT_DIR, exist_ok=True)

paras = [p.strip() for p in io.open(SCRIPT, encoding='utf-8').read().split('\n') if p.strip()]
manifest = []
total = 0.0

for i, text in enumerate(paras, 1):
    txt_path = os.path.join(OUT_DIR, f'p{i:02d}.txt')
    wav_path = os.path.join(OUT_DIR, f'p{i:02d}.wav')
    io.open(txt_path, 'w', encoding='utf-8').write(text)
    r = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-File', SAY_PS1, '-TextFile', txt_path,
                        '-OutFile', wav_path, '-Rate', str(RATE)],
                       capture_output=True, text=True)
    if not os.path.exists(wav_path):
        print(f'  [{i}] FAILED', r.stderr[-200:])
        continue
    with wave.open(wav_path) as w:
        sec = w.getnframes() / w.getframerate()
    total += sec
    chars = len(re.sub(r'\s', '', text))
    manifest.append({'index': i, 'text': text, 'chars': chars,
                     'wav': wav_path, 'seconds': round(sec, 2)})
    print(f'  [{i:02d}] {chars:3d} 字  {sec:5.1f} 秒  {text[:30]}')

meta = {'rate': RATE, 'paragraphs': len(manifest),
        'total_seconds': round(total, 2), 'items': manifest}
with io.open(os.path.join(OUT_DIR, 'manifest.json'), 'w', encoding='utf-8') as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=1)

print(f'\n总时长 {total:.1f} 秒 / 目标 70 秒')
