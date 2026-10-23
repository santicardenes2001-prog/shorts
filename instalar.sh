#!/usr/bin/env bash
# Prepara el entorno para el taller de shorts. Se puede correr varias veces.
set -e
cd "$(dirname "$0")"

echo "== Paquetes de Python"
pip install --quiet cairosvg sherpa-onnx numpy pillow 2>/dev/null \
  || pip install --quiet --break-system-packages cairosvg sherpa-onnx numpy pillow

echo "== ffmpeg"
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1 && (sudo -n true 2>/dev/null || [ "$(id -u)" = 0 ]); then
    (sudo -n apt-get update -qq && sudo -n apt-get install -y -qq ffmpeg) || (apt-get update -qq && apt-get install -y -qq ffmpeg)
  else
    # ffmpeg estático desde PyPI como alternativa
    pip install --quiet imageio-ffmpeg 2>/dev/null || pip install --quiet --break-system-packages imageio-ffmpeg
    mkdir -p "$HOME/.local/bin"
    ln -sf "$(python3 -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" "$HOME/.local/bin/ffmpeg"
    export PATH="$HOME/.local/bin:$PATH"
    echo "   ffmpeg instalado en ~/.local/bin (agregalo al PATH)"
  fi
fi
ffmpeg -version | head -1

echo "== Cairo (para dibujar los SVG)"
python3 -c "import cairosvg" 2>/dev/null || {
  echo "   Falta libcairo. Probá: sudo apt-get install -y libcairo2"; exit 1; }

echo "== Modelo de reconocimiento de voz (Parakeet v3, ~490 MB, solo la primera vez)"
M=modelos/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8
if [ ! -f "$M/encoder.int8.onnx" ]; then
  mkdir -p modelos
  curl -sSL -o modelos/parakeet.tar.bz2 \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8.tar.bz2
  tar xjf modelos/parakeet.tar.bz2 -C modelos
  rm modelos/parakeet.tar.bz2
fi

echo "== Kit de dibujos"
python3 kit.py

echo "Listo."
