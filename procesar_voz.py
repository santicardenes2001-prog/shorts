"""Procesa una grabación de voz para shorts.

    python procesar_voz.py original.m4a voz.wav [--pausa 0.28] [--tono 0]

1. Acorta los silencios largos (pausas de más de --pausa segundos).
2. Limpia y da presencia: filtro de graves, EQ, compresor.
3. Normaliza a -14 LUFS (el nivel de YouTube/TikTok).
4. --tono N sube/baja N semitonos (opcional, para voz de personaje).
"""
import argparse
import json
import subprocess

import numpy as np

SR = 48000


def load(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def find_pauses(x, min_len=0.18):
    hop = SR // 100   # 10 ms
    n = len(x) // hop
    fr = x[:n * hop].reshape(n, hop)
    e = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    thr = np.percentile(e, 90) - 22          # relativo al nivel de la voz
    sil = e < thr
    pauses, i = [], 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]:
                j += 1
            if (j - i) * 0.01 >= min_len or i == 0 or j == n:
                pauses.append((i * hop, j * hop))
            i = j
        else:
            i += 1
    return pauses, thr


def trim(x, pauses, keep, lead=0.12, tail=0.5, xf=0.015):
    """Devuelve el audio con las pausas acortadas a `keep` segundos."""
    k = int(keep * SR)
    f = int(xf * SR)
    cuts = []                         # (inicio, fin) de lo que se elimina
    for a, b in pauses:
        if a == 0:
            if b - a > lead * SR:
                cuts.append((0, b - int(lead * SR)))
        elif b >= len(x) - SR // 100:
            if b - a > tail * SR:
                cuts.append((a + int(tail * SR), len(x)))
        elif b - a > k:
            mid = (a + b) // 2
            cuts.append((mid - k // 2, mid + (k - k // 2)))
    out, pos = [], 0
    ramp_in = np.linspace(0, 1, f, dtype=np.float32)
    for a, b in cuts:
        seg = x[pos:a].copy()
        if pos > 0 and len(seg) > f:
            seg[:f] *= ramp_in
        if b < len(x) and len(seg) > f:
            seg[-f:] *= ramp_in[::-1]
        out.append(seg)
        pos = b
    seg = x[pos:].copy()
    if pos > 0 and len(seg) > f:
        seg[:f] *= ramp_in
    out.append(seg)
    removed = sum(b - a for a, b in cuts) / SR
    return np.concatenate(out), removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("--pausa", type=float, default=0.28)
    ap.add_argument("--tono", type=float, default=0.0)
    ap.add_argument("--sin-eq", action="store_true", help="no ecualizar (audios ya producidos, p. ej. ElevenLabs)")
    a = ap.parse_args()

    x = load(a.entrada)
    pauses, thr = find_pauses(x)
    y, removed = trim(x, pauses, a.pausa)
    tmp = a.salida + ".tmp.f32"
    y.astype(np.float32).tofile(tmp)
    pre = ["highpass=f=60"] if a.sin_eq else ["highpass=f=75", "equalizer=f=280:t=q:w=1.2:g=-2",
                                              "equalizer=f=3500:t=q:w=1.0:g=2.5"]
    if a.tono:
        pre.append(f"rubberband=pitch={2 ** (a.tono / 12):.4f}")

    def measure(chain):
        err = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", tmp, "-af",
                              ",".join(chain + ["ebur128=framelog=quiet"]), "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        return float(err[err.rindex("I:"):].split()[1])

    def full(gain, makeup):
        # ganancia primero, después compresor y limitador (pico máx. -1.5 dB)
        return pre + [f"volume={gain:.2f}dB",
                      f"acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup={makeup:.2f}",
                      "alimiter=limit=0.84:attack=2:release=50:level=false"]

    # llevar a -14 LUFS: ajustar en unas pasadas porque compresor y limitador cambian el nivel
    gain = -18.0 - measure(pre)
    makeup = 1.0
    for _ in range(4):
        integ = measure(full(gain, makeup))
        if abs(integ + 14) < 0.3:
            break
        makeup = min(8.0, makeup * 10 ** ((-14 - integ) / 20))
    print(f"loudness final {integ:.1f} LUFS")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", tmp,
                    "-af", ",".join(full(gain, makeup)), "-ar", str(SR), "-ac", "2", a.salida], check=True)
    import os
    os.remove(tmp)
    print(f"duración {len(x)/SR:.2f}s -> {len(y)/SR:.2f}s (se quitaron {removed:.2f}s de silencio, "
          f"{len(pauses)} pausas, umbral {thr:.1f} dB)")


if __name__ == "__main__":
    main()
