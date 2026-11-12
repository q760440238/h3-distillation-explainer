"""Build the full audio track: intro silence + narration + outro silence, with music.

Keeping the audio out of the per-segment encode makes the mix easy to control:
the narration stays at full level and the bed sits far below it.
"""

import io
import json
import os
import subprocess
import wave

import imageio_ffmpeg

OUT = r'E:\minimaxh3\out'
TT = os.path.join(OUT, 'tts')
MUSIC = os.path.join(OUT, 'music_bed.wav')
NARR = os.path.join(OUT, 'narration_full.wav')
MIXED = os.path.join(OUT, 'audio_final.wav')
FF = imageio_ffmpeg.get_ffmpeg_exe()

INTRO_SECONDS = 2.4
OUTRO_SECONDS = 3.2
MUSIC_DB = -6.0          # bed level relative to the narration


def silence(seconds, path, channels=1, rate=44100, width=2):
    n = int(rate * seconds)
    with wave.open(path, 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b'\x00' * (n * channels * width))
    return path


def concat_wavs(paths, out_path):
    """Concatenate mono WAVs with identical parameters."""
    with wave.open(paths[0]) as first:
        params = first.getparams()
    tmp = out_path + '.tmp'
    with wave.open(tmp, 'wb') as out:
        out.setparams(params)
        for p in paths:
            with wave.open(p) as src:
                out.writeframes(src.readframes(src.getnframes()))
    os.replace(tmp, out_path)
    return out_path


def main():
    manifest = json.load(io.open(os.path.join(TT, 'manifest.json'), encoding='utf-8'))
    items = manifest['items']

    head = silence(INTRO_SECONDS, os.path.join(OUT, '_sil_head.wav'))
    tail = silence(OUTRO_SECONDS, os.path.join(OUT, '_sil_tail.wav'))
    pieces = [head] + [os.path.join(TT, f'p{it["index"]:02d}.wav') for it in items] + [tail]
    concat_wavs(pieces, NARR)

    with wave.open(NARR) as w:
        narr_sec = w.getnframes() / w.getframerate()
    print(f'  narration track {narr_sec:.2f}s ({len(pieces)} pieces)')

    r = subprocess.run([
        FF, '-y', '-i', NARR, '-i', MUSIC,
        '-filter_complex',
        f'[1:a]volume={MUSIC_DB}dB,atempo=1.0[m];'
        f'[0:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,volume=-1dB,loudnorm=I=-16:TP=-1.5:LRA=11[a]',
        '-map', '[a]', '-ar', '44100', '-ac', '1',
        '-c:a', 'pcm_s16le', MIXED],
        capture_output=True, text=True, errors='replace')
    if r.returncode != 0:
        print('mix failed:', (r.stderr or '')[-600:])
        raise SystemExit(1)
    print(f'  mixed -> {MIXED}')
    for p in (head, tail):
        os.remove(p)


if __name__ == '__main__':
    main()
