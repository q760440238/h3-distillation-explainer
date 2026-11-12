"""Generate one WAV per paragraph with a neural voice (edge-tts).

The Windows SAPI voice (Huihui) is female and robotic; the presenter on screen
is a young man, so a neural male voice (Yunxi) matches better. edge-tts emits
MP3, converted to 44.1 kHz mono WAV for the rest of the pipeline.
"""

import asyncio
import io
import json
import os
import re
import subprocess

import edge_tts
import imageio_ffmpeg

SCRIPT = r'E:\minimaxh3\out\distill_script.txt'
OUT_DIR = r'E:\minimaxh3\out\tts'
VOICE = 'zh-CN-YunxiNeural'
RATE = '+40%'
FF = imageio_ffmpeg.get_ffmpeg_exe()

os.makedirs(OUT_DIR, exist_ok=True)


async def synth(text, mp3_path):
    await edge_tts.Communicate(text, VOICE, rate=RATE).save(mp3_path)


def to_wav(mp3_path, wav_path):
    r = subprocess.run([FF, '-y', '-i', mp3_path, '-ar', '44100', '-ac', '1',
                        '-c:a', 'pcm_s16le', wav_path],
                       capture_output=True, text=True, errors='replace')
    return r.returncode == 0 and os.path.exists(wav_path)


def seconds(path):
    r = subprocess.run([FF, '-i', path], capture_output=True, text=True, errors='replace')
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr or '')
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def main():
    paras = [p.strip() for p in io.open(SCRIPT, encoding='utf-8').read().split('\n') if p.strip()]
    manifest = []
    total = 0.0

    for i, text in enumerate(paras, 1):
        mp3 = os.path.join(OUT_DIR, f'p{i:02d}.mp3')
        wav = os.path.join(OUT_DIR, f'p{i:02d}.wav')
        asyncio.run(synth(text, mp3))
        if not to_wav(mp3, wav):
            print(f'  [{i}] conversion failed')
            continue
        sec = seconds(wav)
        total += sec
        chars = len(re.sub(r'\s', '', text))
        manifest.append({'index': i, 'text': text, 'chars': chars,
                         'wav': wav, 'seconds': round(sec, 2)})
        print(f'  [{i:02d}] {chars:3d} 字  {sec:5.1f} 秒  {text[:26]}')

    meta = {'voice': VOICE, 'rate': RATE, 'paragraphs': len(manifest),
            'total_seconds': round(total, 2), 'items': manifest}
    with io.open(os.path.join(OUT_DIR, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print(f'\n总时长 {total:.1f} 秒')


if __name__ == '__main__':
    main()
