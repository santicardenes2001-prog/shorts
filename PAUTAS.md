# Pautas del taller

Lo aprendido de las correcciones del usuario, convertido en reglas. **Leer antes de empezar un short y
actualizar después de cada ronda de correcciones**: cada pedido nuevo se agrega como regla general en
la sección que corresponda (no como caso puntual) y con una línea en el historial del final. Si una
regla se puede chequear con código, sumarla también a `revisar.py`.

## Guion y formato de la serie
- Estructura fija de la serie: gancho que arranca con "Te muestro / Te cuento 3 …", y después
  "1. Nombre: explicación" (3-4 oraciones por ítem). No inventar formatos nuevos.
- El gancho tiene que crear curiosidad ("…y la primera es la peor"); la primera tiene que ser la más fuerte.
- Si el usuario escribe el guion, es palabra por palabra. No cambiar palabras sin preguntar.
- Si el audio no dice lo mismo que el texto (p. ej. falta un "más"), **los subtítulos siguen al audio**
  y se avisa al usuario.
- Revisar los datos y **avisar antes de cambiar**: época equivocada (el escafismo es de la Persia
  antigua, no de la Edad Media), afirmaciones sin fuente, repeticiones ("extremas … extrema").
- Duración: 50-60 s es lo ideal; hasta ~90 s funciona en Shorts/TikTok pero avisar si se pasa.

## Audio
- ElevenLabs: `procesar_voz.py --sin-eq --pausa 0.3`, después transcribir. Objetivo -14 LUFS.
- Los nombres raros (HD 189733b, Hydnora, Nepenthes, Welwitschia) el reconocedor los escribe mal: es
  normal, pero avisar para que el usuario escuche si ElevenLabs los pronunció bien.

## Qué se muestra y cuándo
- **No mostrar nada antes de que la narración lo nombre** (la flor recién cuando se habla de la flor,
  la planta huésped recién en "otras plantas"). En el gancho sí se pueden adelantar los 3 protagonistas.
- Cada palabra clave dispara algo: entrada, cambio de cara o cartel con el dato.
- Los dibujos de cosas reales tienen que ser fieles a la realidad (rasgos que la identifican, color
  correcto). Antes de dibujar, repasar cómo es de verdad: la Hydnora parasita euforbias, no cactus; la
  tapa de la Nepenthes va pegada al borde; la N. rajah es roja.
- Las interacciones físicas tienen que tener sentido (la sierra pasa entre las piernas, por detrás, y la
  sostienen los verdugos con las manos en los mangos).
- Mirar cada dibujo nuevo con zoom: los detalles chicos (dientes de una sierra) se rompen fácil.

## Personajes
- "Vos" es el personaje de la cuenta: aparece en cada video, con variante temática (astronauta,
  explorador). Su cara tiene que corresponder a la emoción de la narración (**miedo** ante algo
  terrible, **asco** ante algo asqueroso; no confundirlas).
- Los objetos y animales llevan cara simple y reaccionan.

## Contenido fuerte
- El usuario quiere mostrar los resultados (cuerpo podrido, partido en dos, sin piel) en estilo
  dibujo plano, sin realismo.
- **Censura solo para**: partes íntimas (un cartel chico sobre la entrepierna) y el momento exacto del
  corte/acto. Antes y después, se ve el resultado sin censura.
- Avisar una vez que puede tener restricción de edad; guardar también una versión censurada.

## Animación y cortes
- **Nada salta en un corte**: si el mismo personaje/objeto sigue en la escena siguiente, mantener
  dibujo (cara), posición, tamaño y `"fase"` del idle. Para mostrar "adentro" de algo, fundido tipo
  rayos X dentro de la misma composición, no un corte con otra cara.
- Si la cámara terminó con zoom, la escena siguiente arranca con el mismo zoom y se aleja suave.
- Los personajes que entran a mitad de escena lo hacen con animación (jump/slide), nunca de golpe.

## Carteles
- Usar `cartel()` de `comun.py`: entrada y salida `"suave"`, sombra y borde finos, sonido bajo.
- Nunca desaparecen de golpe en un corte (sin `out`, se van solos antes del final).
- Cuando un cartel reemplaza a otro en el mismo lugar, el viejo sale antes de que entre el nuevo.
- No se pisan entre sí ni con el título; fuera de la zona de botones (x>960, y 1000-1650), fuera de los
  subtítulos (y≈1470) y nada importante debajo de y=1600.
- Los datos van en carteles grandes ("900 °C", "1%", "+1500 AÑOS").

## Proceso
1. Leer `PAUTAS.md` y las `NOTAS.md` de los proyectos anteriores.
2. Guion → plan corto de escenas → dibujos nuevos en `kit.py` (mirar la hoja con zoom).
3. `armar_escenas.py` del proyecto usando `comun.py` (partir de `proyectos/plantas/armar_escenas.py`).
4. `python3 revisar.py proyectos/<p>/escenas.json` hasta que no queden avisos (o estén justificados).
5. Fotogramas con `--fotos`: cada escena, cada palabra clave, y **justo antes y después de cada corte**.
6. Render, -14 LUFS, fotogramas del MP4, `salidas/`, commit y push.
7. Al recibir correcciones: aplicarlas, **sumar la regla acá**, anotar en `proyectos/<p>/NOTAS.md`.

## Historial de correcciones
- 2026-10-23 · planetas · Versión de audio nueva: re-transcribir y revisar tiempos, sin tocar escenas.
- 2026-10-23 · torturas · El guion "estaba muy distinto": respetar el formato de la serie.
- 2026-10-23 · torturas · Mostrar cuerpos afectados; censura solo en partes íntimas y durante el acto;
  dientes de la sierra mal dibujados; la sierra debe pasar entre las piernas; Vos con miedo, no asco.
- 2026-10-23 · torturas · "Al terminar" ya tiene que verse el resultado, sin censura.
- 2026-10-24 · plantas · No mostrar la flor ni la planta huésped antes de nombrarlas; el cactus no se
  entendía (y era incorrecto: es una euforbia).
- 2026-10-24 · plantas · La jarra cambiaba de cara de golpe al mostrar los litros → continuidad en cortes.
- 2026-10-24 · plantas · "Los mensajes que popean no están finos" → carteles suaves, sombra fina.
- 2026-10-24 · plantas · ¿Las plantas son correctas? → Hydnora, Nepenthes y huésped redibujadas fieles.
