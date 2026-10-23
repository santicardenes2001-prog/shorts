"""Transcribe una grabación con tiempos por palabra (offline, Parakeet v3 multilingüe).

    python transcribir.py audio.wav salida.json
"""
import json
import os
import sys
import wave

import numpy as np
import sherpa_onnx

MODEL = os.environ.get("SHORTS_MODELO") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "modelos", "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8")


def main(wav_path, out_path):
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{MODEL}/encoder.int8.onnx", decoder=f"{MODEL}/decoder.int8.onnx",
        joiner=f"{MODEL}/joiner.int8.onnx", tokens=f"{MODEL}/tokens.txt",
        model_type="nemo_transducer", num_threads=2)
    with wave.open(wav_path) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    st = rec.create_stream()
    st.accept_waveform(sr, x)
    rec.decode_stream(st)
    r = st.result
    toks, ts = list(r.tokens), list(r.timestamps)
    durs = list(getattr(r, "durations", []) or [])
    words = []
    for i, (tk, t) in enumerate(zip(toks, ts)):
        d = durs[i] if i < len(durs) else 0.08
        if tk.startswith(("▁", " ")) or not words or not words[-1]["word"].strip():
            if words and not words[-1]["word"].strip():
                words.pop()
            words.append({"word": tk.replace("▁", "").strip(), "start": float(t), "end": float(t + d)})
        else:
            words[-1]["word"] += tk
            words[-1]["end"] = float(t + d)
    words = [w for w in words if w["word"].strip()]
    json.dump(words, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(r.text)
    print(f"{len(words)} palabras")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
