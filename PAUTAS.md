# Pautas del taller

Lo aprendido de las correcciones del usuario, convertido en reglas. **Leer antes de empezar un short y
actualizar después de cada ronda de correcciones**: cada pedido nuevo se agrega como regla general en
la sección que corresponda (no como caso puntual) y con una línea en el historial del final. Si una
regla se puede chequear con código, sumarla también a `revisar.py`.

## Guion y formato de la serie
- Estructura fija de la serie: gancho que arranca con "Te muestro / Te cuento 3 …", y después
  "1. Nombre: explicación" (3-4 oraciones por ítem). No inventar formatos nuevos. Si el ítem tiene
  apodo, va entre paréntesis: "2. El urutaú (el pájaro fantasma):". Los tres ítems con el mismo formato.
- Cuando el usuario pide corregir un borrador: ajustar al formato de la serie, corregir datos dudosos
  (explicando cada cambio) y, si pide "agregar algo", proponer el dato más visual/animable. Ofrecer
  una sola idea por agregado; el usuario elige.
- Las aclaraciones entre paréntesis del usuario ("animar al animal haciendo el ruido") son notas de
  producción: no van en la narración; se anotan en `NOTAS.md` y se cumplen al animar.
- Si se pide un efecto de sonido protagonista (p. ej. el ruido del pico), darle un hueco propio en
  la edición para que se escuche solo.
- El gancho tiene que crear curiosidad ("…y la primera es la peor"); la primera tiene que ser la más fuerte.
- Si el usuario escribe el guion, es palabra por palabra. No cambiar palabras sin preguntar.
- Si el audio no dice lo mismo que el texto (p. ej. falta un "más"), **los subtítulos siguen al audio**
  y se avisa al usuario. Excepción: un error gramatical de la voz ("el único ave") se escribe bien en
  el subtítulo ("la única ave") y se avisa.
- **Cierre de cada video**: una pregunta amena para el público (p. ej. "¿Tendrías alguno de ellos?")
  y la animación de suscripción (`suscripcion()` de `comun.py`: botón, cursor, clic, campanita), con
  ~3,4 s de `cola`. El usuario puede traer la pregunta ya grabada en el audio.
- Revisar los datos y **avisar antes de cambiar**: época equivocada (el escafismo es de la Persia
  antigua, no de la Edad Media), afirmaciones sin fuente, repeticiones ("extremas … extrema").
- Duración: el usuario prefiere contenido completo antes que cortar; 50-90 s está bien (no recortar
  datos para llegar a 60 s).

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

## Ambientación (profundidad)
- Cada lugar se ambienta en capas, no se llena de cosas: fondo propio del hábitat real + luz (rayos,
  sol, luna) + atmósfera (niebla, hojas que caen, luciérnagas) + primer plano desenfocado que se
  mece (profundidad de campo) + **sonido ambiente** (`"ambiente"`: selva, pantano, noche, bosque).
- El ambiente son **eventos sueltos con silencio entre medio** (pájaros, ranas, ráfagas de grillos) y
  se agacha solo cuando habla el narrador (ducking). **Nunca ruido ni tonos continuos**: debajo de la
  voz se escuchan como un siseo molesto. `revisar.py` avisa si el piso de efectos+ambiente pasa -58 dB.
- Las capas de primer plano van por delante de los personajes (z 12-16) pero detrás de los carteles (z 20+).
- Toda luz va pegada a lo que la genera (halo del señuelo, haz de la lámpara, brillo de una antorcha):
  `"sigue": {"id": ..., "punto": [x, y del dibujo]}`, así acompaña el idle, los movimientos y la escala. Lo
  mismo para lo que queda pegado a un personaje (el macho del rape). `revisar.py` avisa las luces sueltas.
- Humo, gas y burbujas nacen de su fuente (boca de la chimenea): partículas con zona angosta sobre la
  boca, `"desvanece"` y `"crece"`; con `"continuo"` siguen igual en los cortes dentro del mismo lugar.
- La cámara siempre "respira" (zoom lento) y se usa para contar: primer plano de un detalle (el ojo),
  acercarse a la acción (el pico), alejarse para revelar (de la cara al bosque de noche).
- Cambios de momento dentro del mismo lugar con fundidos (día → noche: el fondo de día se desvanece).
- Entre ítems, una transición (`cortina()` de `comun.py`) en vez de un corte seco.
- Los animales tienen vida propia: parpadean, respiran, y su acción característica se anima cuadro a
  cuadro (`loops` con ventana de tiempo) con su sonido propio.
- Un efecto pedido por el usuario va `"destacado": true` (no se baja bajo la voz) y con su hueco
  (`"pausas"` en la voz).

## Personajes
- "Vos" es el personaje de la cuenta: aparece en cada video, con variante temática (astronauta,
  explorador) y con objetos según la escena (binoculares, linterna de noche, tapándose la nariz). Su cara tiene que corresponder a la emoción de la narración (**miedo** ante algo
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
- Lo que no sigue en la escena siguiente **sale animado antes del corte** (fx_out), también los objetos
  chicos (flechas, íconos). Si el lugar sigue igual, mejor que el objeto continúe y se mueva a su nueva
  posición (las barcas bajan al agua) en vez de cortar a otro encuadre.
- Un salto de tiempo en el mismo lugar ("Al terminar…") se marca con `flash`.

## Carteles
- Usar `cartel()` de `comun.py`: entrada y salida `"suave"`, sombra y borde finos, sonido bajo.
- Nunca desaparecen de golpe en un corte (sin `out`, se van solos antes del final).
- Cuando un cartel reemplaza a otro en el mismo lugar, el viejo sale antes de que entre el nuevo.
- No se pisan entre sí ni con el título; fuera de la zona de botones (x>960, y 1000-1650), fuera de los
  subtítulos (y≈1470) y nada importante debajo de y=1600.
- Los datos van en carteles grandes ("900 °C", "1%", "+1500 AÑOS").
- La banda de carteles (y≈400-540) queda libre: Vos u otro personaje fijo va más abajo (p. ej. y=700).
- Con zoom de cámara, los carteles van en coordenadas de escena (x,y = centro + (pantalla − 540/960)/zoom,
  size/zoom) y lo que el zoom agrandaría sobre el encabezado se desvanece antes de acercar.

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
- 2026-10-24 · torturas · Prueba de la memoria: carteles a `comun.py`, nada desaparece de golpe en los
  cortes (`revisar.py` ahora también lo detecta), flash en el salto de tiempo.
- 2026-10-25 · aves · Corrección de borrador: formato de serie, datos, apodos entre paréntesis; notas
  de producción aparte; "no pasa nada si dura un poco más"; del agregado al nº 2 solo la boca enorme.
- 2026-10-25 · aves · "Le falta algo más a las animaciones, profundizar y ambientar más fino" → capas
  de luz/niebla/primer plano desenfocado, sonido ambiente, cámara narrativa, transición de hojas,
  animaciones cuadro a cuadro, efecto destacado con pausa. Cierre con pregunta + suscripción.

- 2026-10-25 · aves · "Ruido de fondo perjudicial": el ambiente tenía ruido y tonos continuos (piso
  -40 dB) → ambiente de eventos sueltos + ducking bajo la voz (piso -63 dB) y chequeo en `revisar.py`.
- 2026-10-25 · océano · "Las luces están separadas de los generadores": halos y haces quedaban fijos mientras
  su fuente flotaba, y el gas salía de cualquier lado → `"sigue"` en el motor, gas desde las bocas, chequeo.
