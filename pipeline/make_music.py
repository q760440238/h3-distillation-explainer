"""Synthesise a soft ambient music bed so the narration is not bare.

No samples, no downloads: a slow pad built from detuned sine partials over a
quiet filtered-noise floor, with a gentle chord change every 8 seconds and a
fade in/out. Written as 44.1 kHz mono WAV.
"""

import os
import wave

import numpy as np

OUT = r'E:\minimaxh3\out'
SR = 44100
DURATION = 80.0

# A minor-ish progression: i - VI - III - VII (frequencies in Hz)
CHORDS = [
    [220.00, 261.63, 329.63],   # Am
    [174.61, 220.00, 261.63],   # F
    [261.63, 329.63, 392.00],   # C
    [196.00, 246.94, 293.66],   # G
]


def pad_chord(freqs, seconds, rng):
    n = int(SR * seconds)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float64)
    for f in freqs:
        for detune in (-0.18, 0.0, 0.18):
            ff = f + detune
            phase = rng.uniform(0, 2 * np.pi)
            lfo = 0.55 + 0.45 * np.sin(2 * np.pi * (0.06 + rng.uniform(0, 0.04)) * t + phase)
            out += np.sin(2 * np.pi * ff * t + phase) * lfo * 0.16
            out += np.sin(2 * np.pi * ff * 2 * t + phase) * lfo * 0.035
    # slow attack/release so chords breathe into each other
    fade = int(SR * 1.8)
    env = np.ones(n)
    env[:fade] = np.linspace(0, 1, fade) ** 2
    env[-fade:] = np.linspace(1, 0, fade) ** 2
    return out * env


def main():
    rng = np.random.default_rng(7)
    total = np.zeros(int(SR * DURATION), dtype=np.float64)

    seg = 8.0
    start = 0.0
    i = 0
    while start < DURATION:
        chord = CHORDS[i % len(CHORDS)]
        block = pad_chord(chord, min(seg * 1.6, DURATION - start + 2.0), rng)
        a = int(SR * start)
        b = min(a + len(block), len(total))
        total[a:b] += block[:b - a]
        start += seg
        i += 1

    # quiet noise floor, low-passed, to glue the pad together
    noise = rng.normal(0, 1, len(total))
    kernel = np.ones(220) / 220
    noise = np.convolve(noise, kernel, mode='same')
    total += noise * 0.05

    # overall dynamics: fade in 3 s, fade out 5 s
    fi, fo = int(SR * 3), int(SR * 5)
    total[:fi] *= np.linspace(0, 1, fi)
    total[-fo:] *= np.linspace(1, 0, fo)

    peak = np.max(np.abs(total)) or 1.0
    total = total / peak * 0.55          # keep plenty of headroom under speech

    pcm = (total * 32767).astype('<i2')
    path = os.path.join(OUT, 'music_bed.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f'{path}  {DURATION:.0f}s  peak={np.max(np.abs(total)):.2f}')


if __name__ == '__main__':
    main()
