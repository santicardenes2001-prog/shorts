# ¿Por qué Europa comía momias? — notas

Short de la tanda del 15/11/2026 (altura, momias, cerebro). Animación procedural (`momias.py`), armazón de
`anestesia.py` y `luna.py`: solo usa `pantalla.py` y `picante.py`.

- **Tono (regla V3):** historia oscura, así que va sobrio: sin personajes, sin caras y sin caricaturas. Todo se cuenta
  con objetos: frasco de botica, sarcófago (óvalo sin rasgos), cuerpo vendado sin rasgos, mortero, corona, libro,
  brea, lista de precios. Sin sangre.
- **Correcciones de Luna v2 aplicadas:** sin flechas de giro y sin sonidos sostenidos; cada tramo tiene un recurso
  propio para mirar (17 escenas en 56 s, una cada 3,3 s en promedio, con hechos adentro).
- **Guion:** el aprobado el 15/11, sin cambios. Formato misterio. Sin nombres propios en la voz (ni el rey ni el
  laboratorio). Fuentes: historia corporativa de Merck KGaA de Darmstadt (lista de precios de 1924, 12 marcos oro
  el kilo), National Geographic (brea de Persia y error de traducción), The Conversation (500 años como remedio,
  falsificaciones vistas en Alejandría en 1564), ExplorersWeb (Francisco I), Journal of Biological Research
  (cuerpos de ejecutados o esclavos tratados con betún y secados al sol).
- **Audio:** ElevenLabs (Agustín), `procesar_voz.py --sin-eq --pausa 0.3`: 60,6 s -> 55,8 s, −14,2 LUFS.
  `transcribir.py` escribió "frasco" y "reciente" donde el guion dice "frascos" y "recientes": el subtítulo usa el
  guion; conviene escuchar si la voz pronuncia la s. Los números van en cifras en `NARRACION` ("1924", "12").
- **Segundos clave:** pregunta a los 6,3 s ("¿Cómo terminó un muerto egipcio en una farmacia?"); primer dato fuerte
  a los 12,0 s ("Hasta un rey de Francia la llevaba siempre encima").
- **Primer cuadro (G2):** el estante de la botica con el frasco "MUMIA" bajo la luz y el sarcófago al fondo; desde
  el primer cuadro la cámara se acerca y entra una cuchara con el polvo.
- **Escenas:** botica (cuchara, "¿BRUJERÍA?" tachado, receta con firma) → sarcófago, camino punteado y frasco con
  "?" → mortero que muele y cuatro frascos → corona que cae al cojín y bolsita que se balancea → libro con
  "MUMIA = BREA" y "MUMIA = MOMIA" y sello "ERROR" → montaña con chorros y gotas de brea → cuenco y momia con dos
  muestras iguales → rasqueta que saca la costra → el cuerpo se hunde en el mortero → tumbas que se vacían y
  frascos que se llenan, sello "SAQUEADAS" → frascos que se vacían y pila de pedidos → sello "FALSA" y brocha
  que pinta de brea un cuerpo reciente → bultos que se oscurecen al sol con etiquetas "ANTIGUA" → dos frascos
  que se cruzan, "¿CUÁL ES CUÁL?" y sello "NO CURABA NADA" → contador de años hasta 1924 y laboratorio → lista
  de precios con resaltador y círculo rojo → vuelve la botica.
- **Exactitud (V4):** el sarcófago y los cuerpos no tienen rasgos. La lista de precios solo tiene una fila con texto
  real ("MUMIA VERA AEGYPTIACA … 12 M"); las demás son renglones grises, sin productos inventados. No se nombra a
  la empresa en pantalla. "SIGLO XVI" para el rey (Francisco I reinó de 1515 a 1547). El cartel «DE 3.000 AÑOS» es
  ilustrativo de "vendidos como antiguos". El edificio es un laboratorio genérico, no el real.
- **Sonido:** solo golpes cortos (tick, pop, ding, clunk, clic, plop, golpe), efectos al 40%.
- **Loop:** "Fue el último rastro de una historia difícil de creer:" -> "Durante siglos, los europeos comieron
  momias para curarse." El cuadro de TOTAL es igual al de 0 (diferencia 0 fuera de los subtítulos); el último cuadro
  renderizado difiere en 0,015 de media. `COLA = 0.3`.
- **Duración (D1):** 56 s, por encima de los 50 que pide la regla: la voz salió a 2,7 palabras por segundo, más
  lenta que la estimación (2,98).
- **Salida:** `salidas/por_que_europa_comia_momias.mp4`, 56,0 s, 1080x1920, 30 fps, −14,1 LUFS (pico −2,0 dBFS).
