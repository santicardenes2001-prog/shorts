# ¿Por qué eres más alto por la mañana? — notas

Short de la tanda del 15/11/2026 (altura, momias, cerebro). Animación procedural (`altura.py`), armazón de
`momias.py`; usa `pantalla.py`, `picante.py`, las piezas espaciales de `cielo.py` (Sol, estrellas y Tierra) y el
Vos de `kit.py`.

- **Guion:** el aprobado el 15/11, sin cambios. Formato misterio. Fuentes (verificadas al escribir el guion):
  Scientific Reports (2020): los discos explican una baja de hasta casi 2 cm por día, cerca del 1% de la altura,
  que se recupera de noche; estudio con 90 adultos de Ghana: 1,6 cm de pérdida promedio y 2,7 de máxima; NASA:
  en el espacio la columna se estira hasta un 3% (unos 5 cm para alguien de 1,80 m), lo que cambia el calce del
  traje y del asiento de regreso, y la altura normal vuelve con el tiempo después del regreso.
- **Audio:** ElevenLabs (Agustín), `procesar_voz.py --sin-eq --pausa 0.3`: 53,2 s -> 48,7 s, −14,1 LUFS.
  `transcribir.py` se comió "miras" y "llenas" y escribió "aplastas" y "Vuelve llenarse"; al volver a transcribir
  esos tramos sueltos, la voz dice el guion bien. En `palabras.json` se corrigieron a mano esas cuatro palabras
  con los tiempos de la transcripción por tramo. Los números van en cifras en `NARRACION` ("2", "5").
- **Segundos clave:** pregunta a los 5,4 s ("¿Qué te está encogiendo mientras miras esto?"); primer dato fuerte a
  los 10,6 s ("Al final del día, perdiste hasta 2 centímetros").
- **Primer cuadro (G2):** Vos de pie contra una regla de pared, con la escuadra apoyada en la cabeza y el Sol en
  la ventana. A los 0,3 s ("noche") la ventana pasa a la Luna, Vos pone cara de cansado y la escuadra baja.
- **Escenas:** cuarto (noche y mañana que se alternan, "¿ILUSIÓN?" tachado, lupa sobre la regla con la marca del
  Sol y la de la Luna) → "?" y reloj digital de 07:00 a 23:00 mientras la marca baja en la lupa, "−2 cm" →
  silueta de perfil con la columna entera: los huesos brillan con una cruz y los discos se encienden uno por uno
  → zoom continuo a la zona lumbar, "DISCOS", núcleo que se llena de agua → pila L3-L5 de día: cae la pesa
  "TU PESO", los discos se aplastan, sueltan gotas y la regla marca cuánto bajó → de noche, la pila se acuesta
  boca abajo en un colchón, la pesa se va ("SIN PESO"), las gotas vuelven y los discos se inflan → amanece, se
  levanta y la regla vuelve a la marca, con tilde → "?", pesa fantasma y señal de prohibido → espacio: sello
  "PROBADO" y estación → astronauta que sale con cable, regla que flota y "+5 cm" → el traje le queda corto
  (se ve la ropa de abajo en tobillos y muñecas) y el asiento le queda chico → cápsula con paracaídas que
  aterriza, flecha de la gravedad y sello "COBRADO" → calendario que pasa hojas y la marca vuelve a "ANTES" →
  vuelve el cuarto: una noche y una mañana más, y queda igual al primer cuadro.
- **Exactitud (V4):** Vos mide 172 cm en la regla de pared y 170 de noche: los 2 cm reales se ven en la lupa
  (42 px por cm). La columna está de costado con adelante a la izquierda: 7 cervicales, 12 dorsales, 5 lumbares,
  sacro y cóccix; lordosis cervical y lumbar, cifosis dorsal; 23 discos (no hay disco entre C1 y C2); las
  espinosas dorsales bajan inclinadas y las lumbares son anchas y casi horizontales; alto de disco ≈ 0,4 del
  cuerpo en la zona lumbar. Los discos pierden un 15% de alto en el día (2 cm repartidos en unos 15 cm de discos).
  El núcleo pulposo va un poco hacia atrás. El astronauta crece un 3% (22 de 745). Estación y cápsula genéricas,
  sin marcas. El calendario no tiene números: la fuente dice "con el tiempo", sin un plazo fijo.
- **Personajes (V2):** Vos sale en la apertura (0 a 13,4 s, como pedía la tabla del guion aprobado) y desde
  46,2 s para cerrar el loop. Las caras están en los discos, el Sol y la Luna; el astronauta va con el visor
  oscuro.
- **Sonido:** solo golpes cortos (pop, tick, clic, clunk, plop, golpe, ding), efectos al 40%.
- **Loop:** "Vuelve a la rutina de todos en la Tierra:" -> "Esta noche vas a medir menos que esta mañana." El
  cuadro de TOTAL es igual al de 0 (diferencia 0 fuera de los subtítulos); el último cuadro renderizado difiere
  en 0,04 de media. `COLA = 0.3`.
- **Duración (D1):** 48,9 s.
- **Salida:** `salidas/por_que_eres_mas_alto_a_la_manana.mp4`, 48,9 s, 1080x1920, 30 fps, −14,0 LUFS
  (pico −3,3 dBFS).
