# ¿Cómo funciona la pantalla de tu celular?

Short sin personaje, animado por código (cairo + numpy/opencv). No usa `escenas.json`: las escenas están en `pantalla.py`.

```bash
pip install pycairo opencv-python-headless   # además de lo de instalar.sh
python proyectos/pantalla/tiempos.py          # tiempos por palabra de cada bloque
python proyectos/pantalla/pantalla.py --fotos 1,14.5,30   # fotogramas sueltos en proyectos/pantalla/fotos/
python proyectos/pantalla/pantalla.py         # render completo -> salidas/como_funciona_tu_pantalla.mp4
```

- `audio/original.mp3`: voz de ElevenLabs. `audio/voz.wav`: procesada con `procesar_voz.py --sin-eq --pausa 0.3` (-14 LUFS).
- `audio/palabras.json`: tiempos por palabra (`transcribir.py`, Parakeet v3).
- Efectos reutilizables: `zoom_sub` (zoom hasta los subpíxeles RGB de cualquier imagen), barrido fila por fila,
  cuadrícula táctil con pulsos, dedo, teclado y panel de comentarios, vista explotada de capas.
- Los efectos de sonido se sintetizan en el mismo script y se mezclan debajo de la voz.
