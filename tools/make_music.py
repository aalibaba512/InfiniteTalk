#!/usr/bin/env python3
"""
Background music generator.

Composes a short original instrumental bed offline with numpy — no samples, no
network, no licence. Useful when a video needs music and every stock-music host
is unreachable (see AGENTS.md: this sandbox can only reach GitHub and PyPI).

Everything is synthesised from scratch:
  pad    slow warm chord bed, two detuned voices panned wide
  arp    soft plucked arpeggio on the chord tones, carries the pulse
  bass   one root note per chord, dry
  perc   very soft kick + shaker, gated by an arrangement curve
  bell   sparse inharmonic sparkle every few bars

Voices are summed, sent through a synthetic plate reverb (block FFT
convolution), then normalised to a background level and faded in/out.

Moods:
  uplifting  I - V - vi - IV in C, 76 BPM, gentle percussion (default)
  calm       slower, no percussion, longer reverb

Examples:
    python3 tools/make_music.py --duration 241.6 --out music.wav
    python3 tools/make_music.py --mood calm --duration 60 --out calm.wav
"""

import argparse
import sys

import numpy as np

SR = 44100
NOTE = {  # midi -> Hz
    "A2": 45, "F2": 41, "C3": 48, "G2": 43,
    "A3": 57, "C4": 60, "E4": 64, "F3": 53, "G3": 55, "B3": 59, "D4": 62,
    "F4": 65, "G4": 67, "A4": 69, "C5": 72, "D5": 74, "E5": 76, "B4": 71,
}


def hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


# --------------------------------------------------------------------------
# building blocks
# --------------------------------------------------------------------------


def asr(n, attack, release, sr=SR):
    """Attack / sustain / release amplitude envelope."""
    env = np.ones(n, dtype=np.float64)
    a = min(n, max(1, int(attack * sr)))
    r = min(n, max(1, int(release * sr)))
    if a > 1:
        env[:a] = np.linspace(0.0, 1.0, a) ** 1.6
    if r > 1:
        env[-r:] *= np.linspace(1.0, 0.0, r) ** 1.4
    return env


def decay_env(n, tau, sr=SR, attack=0.004):
    """Percussive exponential decay with a click-free attack."""
    t = np.arange(n) / sr
    env = np.exp(-t / max(1e-4, tau))
    a = max(1, int(attack * sr))
    if a < n:
        env[:a] *= np.linspace(0.0, 1.0, a) ** 0.7
    return env


def voice(freq, dur, partials, env, sr=SR, detune=0.0):
    """
    One note: a sum of harmonic partials with per-partial levels and decays.

    partials: [(ratio, amplitude, tau_seconds_or_None), ...]
              tau None means the partial sustains with the note envelope.
    """
    n = max(2, int(dur * sr))
    t = np.arange(n) / sr
    out = np.zeros(n, dtype=np.float64)
    for ratio, amp, tau in partials:
        f = freq * ratio * (1.0 + detune)
        if f > sr * 0.45:                      # above Nyquist: skip
            continue
        if tau is None:
            a = np.ones(n)
        else:
            a = np.exp(-t / max(1e-4, tau))
        out += amp * a * np.sin(2 * np.pi * f * t)
    return out * env


def ramp(x, lo, hi):
    """Smoothstep 0..1 between two threshold values."""
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    t = float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))
    return t * t * (3 - 2 * t)


def add_at(buf, sig, start, gain=1.0):
    """
    Mix `sig` into `buf` at sample `start`.

    Handles both ends: a negative start (a humanised note landing just before
    the bar line, or at sample 0) trims the head of the note, and a note running
    past the buffer is trimmed at the tail. Slicing a negative start straight
    into the buffer would wrap around and mix into the wrong place.
    """
    if len(sig) == 0:
        return
    if start < 0:
        sig = sig[-start:]
        start = 0
    if start >= len(buf) or len(sig) == 0:
        return
    end = min(len(buf), start + len(sig))
    if end <= start:
        return
    buf[start:end] += gain * sig[: end - start]


# --------------------------------------------------------------------------
# reverb
# --------------------------------------------------------------------------


def plate_ir(seconds=2.2, sr=SR, seed=7, damp=0.42):
    """Synthetic plate impulse response: decaying, slowly darkening noise."""
    n = int(seconds * sr)
    rng = np.random.default_rng(seed)
    t = np.arange(n) / sr
    ir = rng.standard_normal(n) * np.exp(-t * (3.2 / seconds))
    # one-pole low-pass, opening darkens with time -> softer tail
    a = damp
    for _ in range(2):
        ir = np.concatenate([[ir[0]], a * ir[1:] + (1 - a) * ir[:-1]])
    ir[: int(0.002 * sr)] *= np.linspace(0.0, 1.0, int(0.002 * sr))   # no click
    ir /= np.abs(ir).max() + 1e-9
    return ir


def fft_convolve(sig, ir, block=1 << 18):
    """Block overlap-add convolution, so memory stays flat on long tracks."""
    n, m = len(sig), len(ir)
    if m == 0 or n == 0:
        return np.zeros(n + m - 1)
    nfft = 1 << int(np.ceil(np.log2(block + m - 1)))
    ir_f = np.fft.rfft(ir, nfft)
    out = np.zeros(n + m - 1, dtype=np.float64)
    for start in range(0, n, block):
        chunk = sig[start : start + block]
        spec = np.fft.rfft(chunk, nfft) * ir_f
        piece = np.fft.irfft(spec, nfft)[: len(chunk) + m - 1]
        out[start : start + len(piece)] += piece
    return out


# --------------------------------------------------------------------------
# arrangement
# --------------------------------------------------------------------------

# each entry: (bass midi, pad midis, arp midis one octave up)
PROG_UPLIFT = [
    (45, (57, 60, 64), (69, 72, 76, 72)),   # Am
    (41, (53, 57, 60), (65, 69, 72, 69)),   # F
    (48, (55, 60, 64), (67, 72, 76, 72)),   # C/G
    (43, (55, 59, 62), (67, 71, 74, 71)),   # G
]
PROG_CALM = [
    (45, (57, 64, 69), (72, 76, 79, 76)),   # Am
    (41, (53, 60, 65), (69, 72, 77, 72)),   # F
    (48, (55, 64, 67), (72, 76, 79, 76)),   # C
    (43, (55, 62, 67), (71, 74, 79, 74)),   # G
]


def make_music(duration, mood="uplifting", bpm=None, seed=3):
    """Render `duration` seconds of stereo audio as float64 (n, 2)."""
    rng = np.random.default_rng(seed)
    calm = mood == "calm"
    bpm = bpm or (68 if calm else 76)
    beat = 60.0 / bpm
    bar = 4 * beat
    n = int(duration * SR)

    prog = PROG_CALM if calm else PROG_UPLIFT

    # separate buses so reverb only touches what should be wet
    pad = np.zeros(n)
    arp = np.zeros(n)
    bass = np.zeros(n)
    perc = np.zeros(n)
    bell = np.zeros(n)
    pad_r = np.zeros(n)          # second detuned pad voice for width

    n_bars = int(np.ceil(duration / bar))
    total_bars = max(1, n_bars)

    def intensity(bar_i):
        """
        Arrangement curve: ease in, hold steady, ease out.

        Kept deliberately flat in the middle: this is a bed under a showcase
        video, so the level should not swell across the piece. The intro rises
        from ~0.62 rather than near-silence, which keeps the step when the bass
        and percussion arrive small.
        """
        x = bar_i / total_bars
        if x < 0.14:
            v = 0.62 + 2.6 * x                       # ease in
        elif x < 0.86:
            v = 1.0
        else:
            v = 1.0 - (x - 0.86) / 0.14 * 0.42       # ease out
        return float(np.clip(v, 0.0, 1.0))

    pad_partials = [(1, 1.0, None), (2, 0.30, None), (3, 0.12, None), (4, 0.05, None)]
    arp_partials = [(1, 1.0, 0.62), (2, 0.34, 0.42), (3, 0.13, 0.30), (4, 0.05, 0.22)]
    bass_partials = [(1, 1.0, None), (2, 0.22, None), (3, 0.06, None)]
    bell_partials = [(1, 1.0, 2.4), (2.76, 0.30, 1.6), (5.40, 0.10, 1.0)]

    for b in range(n_bars):
        t0 = b * bar
        s0 = int(t0 * SR)
        root, pads, arps = prog[b % len(prog)]
        lvl = intensity(b)

        # ---- pad: held chord, two detuned voices ------------------------
        for m in pads:
            dur = bar * 1.06
            e = asr(int(dur * SR), 0.85 if calm else 0.6, 0.85)
            sig = voice(hz(m), dur, pad_partials, e)
            g = (0.115 if calm else 0.10) * (0.75 + 0.25 * lvl)
            add_at(pad, sig, s0, g)
            add_at(pad_r, sig, s0, g * 0.9)     # detuned on render below

        # ---- bass: root, on the downbeat and the third beat -------------
        # each instrument eases in over its own range, so the texture thickens
        # instead of switching on
        g_bass = ramp(lvl, 0.30, 0.78)
        if g_bass > 0.01:
            for off, gmul in ((0.0, 1.0), (2 * beat, 0.72)):
                dur = beat * 1.7
                e = asr(int(dur * SR), 0.02, 0.35)
                add_at(bass, voice(hz(root), dur, bass_partials, e),
                       int((t0 + off) * SR), 0.16 * g_bass * gmul)

        # ---- arpeggio: 8th notes, humanised ----------------------------
        g_arp = ramp(lvl, 0.40, 0.88)
        if g_arp > 0.01 and not calm:
            for k in range(8):
                if k in (3, 6) and rng.random() < 0.25:
                    continue                     # occasional rest
                m = arps[k % len(arps)]
                if k >= 4:
                    m += 0                            # second half mirrors
                dur = 1.35
                e = decay_env(int(dur * SR), tau=0.55 + 0.1 * rng.random(), attack=0.006)
                jitter = int(rng.integers(-6, 7) / 1000.0 * SR)
                g = 0.075 * g_arp * (0.72 + 0.28 * rng.random())
                add_at(arp, voice(hz(m), dur, arp_partials, e), s0 + int(k * beat / 2) + jitter, g)

        # ---- bell: sparse sparkle every 4 bars -------------------------
        g_bell = ramp(lvl, 0.45, 0.90)
        if b % 4 == 2 and g_bell > 0.01:
            m = arps[2] + 12 if b % 8 == 2 else arps[0] + 12
            dur = 3.0
            e = decay_env(int(dur * SR), tau=1.5, attack=0.01)
            add_at(bell, voice(hz(m), dur, bell_partials, e), s0, 0.05 * g_bell)

        # ---- percussion: soft kick + shaker ----------------------------
        g_perc = ramp(lvl, 0.55, 0.98)
        if g_perc > 0.01 and not calm:
            for off in (0.0, 2 * beat):
                dur = 0.4
                t = np.arange(int(dur * SR)) / SR
                f = 92 * np.exp(-t * 18) + 44
                kick = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9.5)
                add_at(perc, kick, int((t0 + off) * SR), 0.13 * g_perc)
            for k in range(8):
                if k % 2 == 0:
                    continue
                dur = 0.09
                t = np.arange(int(dur * SR)) / SR
                nz = rng.standard_normal(len(t)) * np.exp(-t * 42)
                nz = np.diff(np.concatenate([[0.0], nz]))   # crude high-pass
                add_at(perc, nz, int((t0 + k * beat / 2) * SR), 0.030 * g_perc)

    # ---- stereo, reverb, mix -------------------------------------------
    pad_r = np.roll(pad_r, int(0.011 * SR))          # ~11 ms haas offset for width
    pad_r[: int(0.011 * SR)] = 0.0

    wet_bus = pad + pad_r + arp + bell
    ir = plate_ir(3.0 if calm else 2.2, seed=seed)
    wet = fft_convolve(wet_bus, ir, block=1 << 17)
    wet = wet[:n] / (np.abs(wet[:n]).max() + 1e-9)

    dry = pad * 0.72 + pad_r * 0.72 + arp * 0.55 + bell * 0.6
    core = dry[:n] + wet * (0.42 if calm else 0.34) + bass[:n] + perc[:n]

    left = core.copy()
    right = core.copy()
    left += pad_r[:n] * 0.16
    right -= pad_r[:n] * 0.10
    # widen the reverb tail, not the transient
    left[0:n] += 0.06 * wet[:n]
    right[0:n] += 0.04 * np.roll(wet[:n], int(0.006 * SR))

    stereo = np.stack([left, right], axis=1)

    # ---- level, fades ---------------------------------------------------
    fade_in = min(3.0, duration * 0.05)
    fade_out = min(8.0, duration * 0.08)
    env = np.ones(n)
    fi, fo = int(fade_in * SR), int(fade_out * SR)
    if fi > 1:
        env[:fi] = np.linspace(0, 1, fi) ** 1.5
    if fo > 1:
        env[-fo:] *= np.linspace(1, 0, fo) ** 1.3
    stereo *= env[:, None]

    # gentle soft-knee compression, then normalise to a background level
    peak = np.abs(stereo).max() + 1e-9
    stereo = np.tanh(stereo / peak * 1.25) * 0.92
    rms = np.sqrt((stereo ** 2).mean())
    target_rms = 0.105
    stereo *= min(4.0, target_rms / (rms + 1e-9))
    stereo = np.clip(stereo, -0.97, 0.97)

    return stereo, bpm


def write_wav(path, stereo, sr=SR):
    """16-bit PCM stereo WAV, written without scipy."""
    import struct

    data = np.clip(stereo, -1.0, 1.0)
    ints = (data * 32767.0).astype("<i2")
    frames = ints.tobytes()
    n = len(ints)
    with open(path, "wb") as fh:
        fh.write(b"RIFF")
        fh.write(struct.pack("<I", 36 + len(frames)))
        fh.write(b"WAVEfmt ")
        fh.write(struct.pack("<IHHIIHH", 16, 1, 2, sr, sr * 4, 4, 16))
        fh.write(b"data")
        fh.write(struct.pack("<I", len(frames)))
        fh.write(frames)
    return n


def main():
    ap = argparse.ArgumentParser(description="Generate a royalty-free background music bed.")
    ap.add_argument("--duration", type=float, default=60.0, help="seconds")
    ap.add_argument("--mood", choices=["uplifting", "calm"], default="uplifting")
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--out", default="music.wav")
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()

    if args.duration <= 0:
        sys.exit("--duration must be positive")

    stereo, bpm = make_music(args.duration, args.mood, args.bpm, args.seed)
    n = write_wav(args.out, stereo)
    dur = n / SR
    rms = float(np.sqrt((stereo ** 2).mean()))
    peak = float(np.abs(stereo).max())
    print(f"{args.mood} @ {bpm:.0f} BPM -> {args.out}")
    print(f"  {dur:.2f}s, {n} frames, stereo {SR} Hz 16-bit")
    print(f"  peak {peak:.3f}   rms {rms:.3f} ({20 * np.log10(rms + 1e-9):.1f} dBFS)")


if __name__ == "__main__":
    main()
