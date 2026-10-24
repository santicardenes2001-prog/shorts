# Taller de shorts animados

Shorts verticales (1080×1920, 30 fps) "explicados con muñequitos", en español rioplatense neutro.
Herramientas: `kit.py` (dibujos SVG), `motor.py` (render), `procesar_voz.py`, `transcribir.py`,
`hoja_kit.py`, `revisar.py` (revisor automático), `comun.py` (estilos y ayudantes compartidos).
Instrucciones originales del encargo: `PROMPT.md`.

## Memoria del taller (obligatorio)
- **Antes de empezar cualquier video, leer `PAUTAS.md`** y las `proyectos/*/NOTAS.md`: son las
  correcciones que ya hizo el usuario. No repetir errores que figuran ahí.
- **Después de cada ronda de correcciones**: sumar la regla general a `PAUTAS.md` (y una línea al
  historial), anotar el detalle en `proyectos/<p>/NOTAS.md`, y si se puede chequear con código,
  agregarlo a `revisar.py`. Lo que mejore en el estilo va a `comun.py` para que lo hereden los
  videos nuevos.
- Antes de renderizar: `python3 revisar.py proyectos/<p>/escenas.json` sin avisos sin justificar.

## Convenciones
- Cada proyecto en `proyectos/<nombre>/`: `guion.txt`, `armar_escenas.py` (genera `escenas.json`),
  `audio/original.mp3` + `audio/palabras.json`, `NOTAS.md`. `voz.wav` no se sube (se regenera).
- Entregables en `salidas/` (MP4 + `hoja_kit.png`), commit y push a la rama de trabajo.
- Los recursos existentes del kit no se modifican sin necesidad (otros videos dependen de ellos);
  agregar parámetros con valores por defecto que mantengan el dibujo anterior.
