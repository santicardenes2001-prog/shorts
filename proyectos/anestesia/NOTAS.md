# Así operaban antes de la anestesia — notas

Short 4 de la tanda del 10/11/2026. Animación procedural (`anestesia.py`), armazón de `estomago.py`: solo usa
`pantalla.py` y `picante.py`.

- **Tono (regla V3):** historia con violencia real, así que va sobrio: sin personajes, sin caras, sin caricaturas y
  sin sangre. Todo se cuenta con objetos: mesa con correas, sierra, alcohol y frasco de opio, manos en sombra, balanza,
  reloj de bolsillo, gradas con relojes, corazón, calendario, inhalador de éter, mapa con un barco y un ojo.
- **Motivos que se repiten:** la línea de dolor (roja con picos en "cada corte" y "tanto dolor", blanca y plana en
  "no sintió nada"), el reloj de bolsillo con la marca roja de los 30 s, y el ojo (despierto al principio, se cierra
  con el éter, se abre al final).
- **Guion:** el del documento de la tanda, sin cambios. Sin nombres propios en la voz. Fuentes: History, Scientific
  American, Real Colegio de Cirujanos de Edimburgo (Liston), Mental Floss.
- **Datos en pantalla:** el reloj de 1:30 llega a 28 s ("menos de 30"); el de Londres, a 25 s (las fuentes dan 25 o
  28 s). "Boston, 1846" en un cartel.
- **Audio:** ElevenLabs (Agustín), `procesar_voz.py --sin-eq --pausa 0.3`, `transcribir.py`. El reconocedor escribió
  "sufría" donde el guion dice "sufrías": el subtítulo usa el guion; conviene escucharlo.
- **Loop:** "No sabía de lo que se había salvado:" -> "Hace menos de 200 años, te operaban despierto." El último
  cuadro es igual al primero (la mesa con la sierra bajo la luz, sin carteles). `COLA = 0.3`.
- **Segundos clave:** sin pregunta planteada (formato tema explicado). Primer dato fuerte: 21,4 s ("Los mejores
  amputaban una pierna en menos de 30 segundos").
- **Primer cuadro (G2):** la mesa de operaciones con correas y la sierra, bajo un cono de luz.
- **Salida:** `salidas/asi_operaban_antes_de_la_anestesia.mp4`, 58,2 s, 1080x1920, 30 fps, -14,2 LUFS.
