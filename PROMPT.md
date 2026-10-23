# Short animado: "3 planetas extraños"

Vas a producir un short vertical animado (1080×1920, 30 fps, ~50 s) para YouTube Shorts y TikTok, en el estilo de los videos de historia y ciencia "explicados con muñequitos": personajes simples con contorno grueso, colores planos, objetos que entran rebotando, carteles y subtítulos grandes. Usá personajes y dibujos propios; no copies personajes de otros canales.

Ya existe un taller que hace casi todo. Tu trabajo es dibujar los recursos nuevos que pide este guion, convertir el guion en escenas animadas, sincronizarlas con la voz y renderizar. Si para hacerlo bien necesitás herramientas o funciones que no existen, creálas (ver "Crear herramientas nuevas").

## Las herramientas que tenés

| Archivo | Qué hace |
|---|---|
| `instalar.sh` | Instala dependencias (cairosvg, sherpa-onnx, numpy, pillow, ffmpeg), descarga el modelo de reconocimiento de voz (~490 MB) y genera el kit. Corrélo primero. |
| `kit.py` | Dibuja todos los recursos en SVG con una guía de estilo común y los rasteriza a `kit/png/`. También escribe `kit/meta.json` (anclas y puntos útiles). |
| `motor.py` | Lee un `escenas.json` y renderiza el MP4: animaciones, subtítulos palabra por palabra, efectos de sonido y mezcla con la voz. |
| `procesar_voz.py` | Acorta silencios largos, limpia y normaliza la voz a -14 LUFS. Con `--sin-eq` para audios que ya vienen producidos (ElevenLabs). |
| `transcribir.py` | Reconocimiento de voz offline con tiempos por palabra → `palabras.json`. |
| `hoja_kit.py` | Hoja de contacto con todos los recursos del kit (PNG). |
| `ejemplos/3cosas/` | Un short terminado: su `escenas.json` es la mejor referencia del formato. Leélo entero antes de empezar. |
| `fonts/` | Lilita One (licencia OFL). |

Comandos:

```bash
bash instalar.sh
python3 motor.py proyectos/planetas/escenas.json --tiempos            # tiempos por bloque y escena
python3 motor.py proyectos/planetas/escenas.json --fotos 2.5,7,12.3   # fotogramas sueltos en proyectos/planetas/fotos/
python3 motor.py proyectos/planetas/escenas.json                      # render completo -> short.mp4
python3 procesar_voz.py audio/original.mp3 audio/voz.wav --sin-eq --pausa 0.3
ffmpeg -i audio/voz.wav -ac 1 -ar 16000 audio/voz16k.wav && python3 transcribir.py audio/voz16k.wav audio/palabras.json
python3 hoja_kit.py hoja_kit.png
```

## El guion

Está en `proyectos/planetas/guion.txt`. Es el texto que se ve en los subtítulos, así que en `narracion` va tal cual (podés partirlo en bloques, pero no cambies palabras sin preguntarme). `guion_elevenlabs.txt` es la misma narración escrita para que la voz sintética pronuncie bien los nombres y números; con ese texto genero el audio.

```
¡Te muestro 3 planetas tan extraños que parecen inventados!

1. HD 189733b, donde llueve vidrio de lado. Se ve azul y hermoso, pero su atmósfera está llena de silicatos, el material del vidrio. Con más de 900 grados y vientos de 8700 kilómetros por hora, llueve vidrio derretido en horizontal.

2. TrES-2b, el planeta más oscuro que se conoce. Es del tamaño de Júpiter, pero refleja menos del 1% de la luz que recibe: es más negro que el carbón. Aunque no del todo invisible: a casi 1000 grados, brilla con un rojo tenue, como una brasa.

3. 55 Cancri e, el planeta de diamante. Mide el doble que la Tierra y su año dura solo 18 horas. Tiene tanto carbono, y tanta presión y calor adentro, que se cree que gran parte de su interior podría ser diamante.
```

## Cómo trabajar

1. **Prepará el entorno** con `bash instalar.sh`. Si algo falla (red, permisos, librerías del sistema), decime exactamente qué falta en vez de rodearlo.
2. **Estudiá el ejemplo**: `ejemplos/3cosas/escenas.json`, `kit.py` y `motor.py`. Mirá `python3 hoja_kit.py` para conocer el estilo.
3. **Planificá las escenas.** Partí la narración en bloques (gancho, y varios bloques por planeta). Para cada bloque decidí qué se ve y en qué palabra pasa cada cosa. Pensá en el chiste visual: los planetas pueden tener cara y reaccionar; el personaje "Vos" puede aparecer de astronauta. Mostrame el plan en una lista corta antes de dibujar.
4. **Dibujá los recursos nuevos en `kit.py`** (ver lista sugerida abajo), siguiendo la guía de estilo. Regenerá el kit y revisá la hoja de contacto mirando la imagen. Corregí lo que se vea mal.
5. **Escribí `proyectos/planetas/escenas.json`.** Mientras no haya audio, el motor estima los tiempos.
6. **Vista previa:** sacá fotogramas de cada escena con `--fotos`, armá una hoja con todos y miralos. Revisá superposiciones, textos cortados, zonas seguras y que cada acción caiga en su palabra. Iterá hasta que se vea bien.
7. **Voz:** cuando te pase el MP3 de ElevenLabs, ponelo en `proyectos/planetas/audio/original.mp3`, procesalo con `--sin-eq`, transcribilo y agregá al JSON `"audio_voz": "audio/voz.wav"` y `"palabras_json": "audio/palabras.json"`. El motor alinea guion y audio solo (avisa si alguna palabra no se reconoció; con nombres como "HD 189733b" es normal). Revisá de nuevo los fotogramas con los tiempos reales.
8. **Render final** y verificación: duración, que el audio esté en -14 LUFS (`ffmpeg -i short.mp4 -af ebur128 -f null -`) y un último vistazo a fotogramas clave.
9. **Entrega:** el MP4 y la hoja del kit actualizada. Si estás en un repositorio, guardalos en `salidas/` y subilos en una rama nueva para que los descargue desde GitHub; si tenés otra forma de mandarme archivos, usala. Resumime en pocas líneas qué recursos y funciones agregaste.

## Recursos nuevos sugeridos

Es una guía, no una lista cerrada; sumá o cambiá lo que haga falta.

- **Fondo de espacio**: azul noche profundo con estrellas de varios tamaños y alguna nebulosa suave. Quizás variantes de color por planeta.
- **HD 189733b**: gigante gaseoso azul cobalto con bandas; lindo de lejos, con una cara que cambia a malvada.
- **Lluvia de vidrio**: fragmentos de vidrio celestes y filosos, más líneas de viento.
- **Termómetro** con número (o cartel de temperatura), y velocímetro o cartel "8700 km/h".
- **TrES-2b**: esfera casi negra con un borde/halo rojo tenue que late, como una brasa. **Júpiter** para comparar tamaño. **Carbón** y una **brasa** encendida.
- **Estrella** anfitriona (reutilizá el estilo de `sol` con más brillo).
- **55 Cancri e**: planeta rocoso oscuro con grietas de lava; ideal un corte en cuña que muestre el interior de **diamante**. La **Tierra** para comparar (el doble de tamaño). Un **reloj** o calendario para "su año dura 18 horas". Brillos de diamante.
- **Vos astronauta**: el personaje existente con escafandra (podés agregar una variante en `VOS_VARIANTS` y dibujar el casco encima).

## Crear herramientas nuevas

Si el guion pide algo que el motor no hace, agregalo como función general y configurable desde el JSON, sin romper lo que ya existe (el ejemplo `ejemplos/3cosas` tiene que seguir renderizando igual). Cosas que probablemente hagan falta:

- **Partículas**: un tipo de elemento que emita muchas copias de uno o varios recursos con posición, velocidad, rotación y escala aleatorias pero con semilla fija (para la lluvia de vidrio horizontal y las estrellas que titilan).
- **Brillo/halo**: un resplandor que late (para TrES-2b y el diamante). Puede ser un recurso con degradado radial + `idle: pulse`, o un efecto del motor.
- **Cámara**: un zoom o paneo suave de toda la escena, si mejora el ritmo.
- **Sonidos nuevos** en `synth()` (viento, cristal, brillo) si hacen falta.

Documentá cada función nueva con un comentario corto en el código y mencionala en la entrega.

## Formato de `escenas.json` (resumen)

Raíz: `velocidad` (solo sin audio), `cola` (seg. al final), `volumen_efectos`, `subtitulos` `{activos, y, size}`, `estilos` (estilos de texto reutilizables), `narracion` `[{texto}]` (bloques b0, b1…), `persistentes` (elementos que cruzan escenas, como el número y el título de cada planeta), `escenas`, `audio_voz`, `palabras_json`.

Escena: `nombre`, `beats` (bloques de narración que cubre), `fondo`, `flash` (destello blanco al entrar), `sonidos` `[{at, s}]`, `elementos`.

Elemento:
- `a` (recurso del kit) o `texto` `{t, size, color, box, circle, estilo, ...}`.
- `x`, `y` (posición del ancla), `s`, `sx`, `sy`, `r` (grados, horario), `alpha`, `anchor` `[ax, ay]`, `z`, `flip`.
- `in`, `out`: referencias de tiempo. `fx_in`: `pop grow jump drop fade wipe slide_up slide_down slide_left slide_right`. `fx_out`: `pop fade slide_*`.
- `idle`: `breathe bob float wiggle sway shake spin pulse work chew`, o `{fx, fuerza, from, to, vel}`; puede ser una lista.
- `blink: true` (parpadeo si existe la variante `__blink`).
- `swaps` `[{at, a, fx: "punch"}]` (cambiar de dibujo, por ejemplo de expresión).
- `keys` `[{at, dur, x, y, s, r, alpha, ease, sfx}]` (movimientos); `ease`: `linear out in inout back bounce`.
- `seq` `{frames, at, dur}` (secuencia de dibujos que avanza una vez) y `loop` `{frames, fps}` (secuencia en bucle).
- `sfx`: `pop whoosh whoosh_suave ding boing zoom none`.

Referencias de tiempo: `"b3"` (empieza el bloque 3), `"b3>"` (termina), `"b3:vidrio"` (cuando se dice "vidrio" en el bloque 3), `"b3:vidrio>"`, `"e2"` / `"e2>"` (empieza/termina la escena 2), `"esc"` / `"esc>"` (la escena actual), `"fin"`; todas aceptan `+0.2` o `-0.1`.

## Guía de estilo y composición

- Contorno `#24201F` de 7 px, colores planos de la paleta `P` de `kit.py`, formas redondeadas, caras simples y expresivas. Los recursos se dibujan en píxeles del lienzo final y se rasterizan a 1,5×.
- Zonas: número y título del planeta arriba (y ≈ 250, como en el ejemplo); acción principal entre y = 450 y 1330; personajes de pie con ancla abajo en y = 1330; subtítulos en y = 1470.
- Evitá poner cosas importantes debajo de y = 1600 (ahí va la descripción del video) y a la derecha de x = 960 entre y = 1000 y 1650 (botones de la app).
- Algo tiene que moverse siempre: cada palabra clave dispara algo (entrada, cambio de cara, cartel con el número).
- Los datos se muestran también en carteles grandes: "900 °C", "8700 km/h", "1%", "18 h".

## Qué pedirme

Si te falta algo (el audio, una decisión de estilo, acceso a la red o permisos), preguntame. Si encontrás un dato del guion que te parezca incorrecto, avisame antes de cambiarlo.
