"""Synthesises the launcher's navigation sounds (godot/sounds/): a tock when the focus moves, a whoosh when a system is entered.

Both are made from sines and seeded noise, so the output is the same on every run and every machine (the WAVs are
committed; run this only to change them). 48 kHz, mono, 16-bit PCM, which Godot imports as an AudioStreamWAV.

- nav_tock.wav (45 ms): a soft key press on a mechanical keyboard, a damped "thock" rather than a click. The keycap's
  body is three heavily damped resonances (320, 610 and 1150 Hz, gone within about 30 ms) with a 1.5 ms swell instead of
  an instant attack, and the tap of the key bottoming out is 2 ms of noise, band-passed and kept under 3.5 kHz. The whole
  sound is low-passed at 4 kHz, so nothing in it is bright. Quiet (peak -14 dBFS), since a held move repeats it up to 28
  times a second.
- nav_whoosh.wav (700 ms): a soft rising chime with a breath of air under it. Three notes of G major in an open voicing
  (G4, D5, B5), 45 ms apart, each a sine with a little of its second and third harmonics, swelling in over 20 ms and
  dying away slowly, each sliding up a quarter-tone into its pitch. Under them, faint noise through a band-pass sweeping
  from 400 Hz to 1.8 kHz, peaking 150 ms in (with the systems grid sliding away). Everything is low-passed at 5 kHz.
  Peak -14 dBFS.

Needs numpy and scipy, and matplotlib for --preview. Run from the repo root:

    python tools/ui-sounds/make_sounds.py [--preview=<folder>]

--preview also writes <folder>/<name>.png: each sound's waveform over its spectrogram (use a folder in artifacts/).
"""

import os
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

RATE = 48000
TARGET = 'godot/sounds'
SEED = 20261010
PREVIEW = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--preview=')), None)


def db(value):
    return 10 ** (value / 20)


def fade(signal, fade_in_ms, fade_out_ms):
    """Raised-cosine fades at both ends, so neither end clicks."""
    out = signal.copy()
    n_in = int(RATE * fade_in_ms / 1000)
    n_out = int(RATE * fade_out_ms / 1000)
    if n_in:
        out[:n_in] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n_in))
    if n_out:
        out[-n_out:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, n_out))
    return out


def normalise(signal, peak_db):
    return signal * (db(peak_db) / np.max(np.abs(signal)))


def filtered(signal, kind, cutoff, order=2):
    return sosfilt(butter(order, cutoff, btype=kind, fs=RATE, output='sos'), signal)


def tock(rng):
    length = 0.045
    t = np.arange(int(RATE * length)) / RATE

    # The keycap's body: damped resonances, low and mid, swelling in over 1.5 ms so there's no sharp edge.
    swell = 1 - np.exp(-t / 0.0015)
    body = np.zeros_like(t)
    for frequency, amplitude, decay in [(320, 1.0, 0.009), (610, 0.55, 0.006), (1150, 0.25, 0.0035)]:
        body += amplitude * np.sin(2 * np.pi * frequency * t) * np.exp(-t / decay)
    body *= swell

    # The key bottoming out: a soft tap of noise, nothing bright in it.
    tap = rng.standard_normal(len(t)) * np.exp(-t / 0.002)
    tap = filtered(filtered(tap, 'bandpass', [600, 2500]), 'lowpass', 3500)
    out = body / np.max(np.abs(body)) + 0.45 * tap / np.max(np.abs(tap))

    out = filtered(filtered(out, 'highpass', 90), 'lowpass', 4000)
    return normalise(fade(out, 0.3, 10), -14)


def svf_bandpass(signal, centre, q):
    """A state-variable band-pass (Zavalishin's topology-preserving form), re-tuned every sample to centre."""
    g = np.tan(np.pi * centre / RATE)
    k = 1 / q
    a1 = 1 / (1 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    band = np.empty(len(signal))
    ic1 = ic2 = 0.0
    for i in range(len(signal)):
        v3 = signal[i] - ic2
        v1 = a1[i] * ic1 + a2[i] * v3
        v2 = ic2 + a2[i] * ic1 + a3[i] * v3
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        band[i] = v1
    return band


def whoosh(rng):
    length = 0.700
    n = int(RATE * length)
    t = np.arange(n) / RATE

    # The chime: G4, D5, B5, each 45 ms after the last, sliding up a quarter-tone into its pitch.
    chime = np.zeros(n)
    for index, frequency in enumerate([392.00, 587.33, 987.77]):
        start = 0.045 * index
        local = np.clip(t - start, 0, None)
        on = t >= start
        glide = 2 ** (-0.5 / 12 * np.exp(-local / 0.04))
        phase = 2 * np.pi * np.cumsum(frequency * glide * on) / RATE
        tone = np.sin(phase) + 0.12 * np.sin(2 * phase) + 0.04 * np.sin(3 * phase)
        envelope = (1 - np.exp(-local / 0.020)) * np.exp(-local / (0.26 - 0.05 * index)) * on
        chime += (1.0 - 0.18 * index) * tone * envelope

    # The air: faint noise through two band-passes in series, sweeping up, peaking 150 ms in.
    x = t / length
    centre = 400 * (1800 / 400) ** (0.5 - 0.5 * np.cos(np.pi * np.clip(x / 0.5, 0, 1)))
    air = svf_bandpass(svf_bandpass(rng.standard_normal(n), centre, 0.8), centre, 0.8)
    peak = 0.150 / length
    air *= (x / peak) ** 2 * np.exp(2 * (1 - x / peak))

    out = chime / np.max(np.abs(chime)) + 0.35 * air / np.max(np.abs(air))
    out = filtered(filtered(out, 'highpass', 120), 'lowpass', 5000)
    return normalise(fade(out, 2, 120), -14)


def preview(name, signal, folder):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    t = np.arange(len(signal)) / RATE * 1000
    figure, (wave, spectrum) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    wave.plot(t, signal, linewidth=0.6)
    wave.set_ylim(-1, 1)
    wave.set_ylabel('amplitude')
    wave.set_title(f'{name}: peak {20 * np.log10(np.max(np.abs(signal))):.1f} dBFS, '
                   f'RMS {20 * np.log10(np.sqrt(np.mean(signal ** 2))):.1f} dBFS')
    spectrum.specgram(signal, NFFT=1024, Fs=RATE / 1000, noverlap=960, cmap='magma', vmin=-110)
    spectrum.set_ylim(0, 8)
    spectrum.set_ylabel('kHz')
    spectrum.set_xlabel('ms')
    spectrum.set_xlim(0, t[-1])
    figure.tight_layout()
    figure.savefig(os.path.join(folder, name + '.png'), dpi=100)
    plt.close(figure)


def main():
    rng = np.random.default_rng(SEED)
    sounds = {'nav_tock': tock(rng), 'nav_whoosh': whoosh(rng)}
    os.makedirs(TARGET, exist_ok=True)
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)

    for name, signal in sounds.items():
        path = os.path.join(TARGET, name + '.wav')
        wavfile.write(path, RATE, np.round(signal * 32767).astype(np.int16))
        print(f'{path}: {len(signal) / RATE * 1000:.0f} ms, {os.path.getsize(path):,} bytes')
        if PREVIEW:
            preview(name, signal, PREVIEW)


main()
