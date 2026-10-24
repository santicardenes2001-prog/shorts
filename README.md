# Taller de shorts animados

Convierte un guion (y una grabación de voz) en un short vertical animado.

1. `bash instalar.sh` — dependencias, modelo de voz y kit de dibujos.
2. Escribir `proyectos/<nombre>/escenas.json` (ver `ejemplos/3cosas/escenas.json`).
3. Voz: `python3 procesar_voz.py original.mp3 voz.wav --sin-eq` y `python3 transcribir.py voz16k.wav palabras.json`.
4. `python3 motor.py proyectos/<nombre>/escenas.json` → `short.mp4`.

5. `python3 revisar.py proyectos/<nombre>/escenas.json` — revisor automático (carteles que se pisan,
   zonas prohibidas, saltos en los cortes) antes de renderizar.

`PROMPT.md` tiene las instrucciones completas para que Claude arme un short nuevo.
`PAUTAS.md` junta lo aprendido de cada corrección y `CLAUDE.md` hace que Claude lo lea al empezar;
cada proyecto tiene su `NOTAS.md`. `comun.py` tiene los estilos y ayudantes que heredan los videos nuevos.
