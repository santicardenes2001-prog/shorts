# ¿Por qué los bostezos se contagian? — notas

Animación procedural (`bostezo.py`), armazón de `tierra.py` (importa de ahí las ayudas de dibujo); usa `pantalla.py`,
`picante.py` (fondo, caras, sonidos) y a Vos de `kit.py`.

- **Guion:** el 4 de la tanda del chat del 20/11/2026 ("pensar con estrategia 5 guiones"), aprobado por el usuario
  ("muy sólido"). Sin cambios en el audio. Fuentes: todos los vertebrados bostezan, incluso serpientes; el contagio
  solo se demostró en humanos, chimpancés y posiblemente perros; leer sobre bostezos alcanza (NBC News); los chicos se
  contagian desde cerca de los 4 años, cuando empiezan a entender las emociones de otros (Live Science, Universidad de
  Connecticut 2010); los perros se contagian más del dueño que de un desconocido (CBS News, estudio de 2012); más de
  familia y amigos que de extraños (Norscia y Palagi, PLoS ONE 2011); cerca de la mitad de los adultos se contagia y el
  estudio de Duke (2014) no encontró relación fuerte con la empatía (Psychology Today).
- **Audio:** ElevenLabs (Agustín – Warm, Expressive), `procesar_voz.py --sin-eq --pausa 0.3`: 55,8 s -> 51,6 s,
  −14,2 LUFS. 154 palabras en 51,4 s: 3,0 palabras por segundo. `transcribir.py` escribió "¿Por tu", "Bostez",
  "bostez." y "estudante": al transcribir esos tramos solos dice "¿Por qué tu", "Bostezar" y "estudio grande", así que
  el audio sigue el guion. Se corrigió en `palabras.json` ("qué" con el tiempo del tramo; "estudio grande" partido a la
  mitad del tiempo de "estudante"). "4" en cifra en `NARRACION`.
- **Segundos clave:** pregunta a los 6,4 s ("¿Por qué tu cuerpo copia un bostezo ajeno?"); primer dato fuerte a los
  11,3 s ("Hasta las serpientes bostezan").
- **Primer cuadro (G2):** Vos de frente mirando a cámara, arriba una barra de progreso del video vacía y al final de la
  barra el bostecito amarillo (la promesa: antes de que termine, bostezás).
- **Escenas:** apertura (en "bostezar" el bostecito de la barra bosteza; Zzz que se tachan en "sueño"; entra la
  almohada con cara, bosteza en "hacerlo", las ondas viajan de su boca a la de Vos y Vos bosteza en "copia"; "?") →
  pez y pájaro bostezan, entra la serpiente y abre la mandíbula en "bostezan"; sello RARÍSIMO → "COMPROBADO EN": tres
  cartas con "?" que se llenan con humano, chimpancé y perro (tildes en los dos primeros, "?" en el perro); cada uno
  bosteza al aparecer → ojo grande con cruz roja ("verlo") → libro abierto con cara, "BOSTEZO" resaltado, bosteza en
  "bostezar" → la almohada bosteza y las ondas rebotan en el bebé, que se ríe → torta con 4 velas que se prenden,
  "4 AÑOS"; el nene se pone triste cuando ve triste a la almohada y aparece un corazón → bostecito, cadena y corazón,
  sello EMPATÍA → familia contra extraño con barras de contagio (alta y baja) → el perro bosteza, copia al "TÚ" y no al
  "DESCONOCIDO"; barras → tablero ESTUDIO que se llena de caras; la cadena bostecito–corazón se rompe con cruz roja →
  bostecito grande bostezando entre signos "?" → diez adultos, bostezan cinco, "LA MITAD" → cierre.
- **Exactitud (V4):** la serpiente abre la mandíbula de perfil (el bostezo de las serpientes es con la boca muy
  abierta); chimpancé con cara clara y hocico; el perro de orejas caídas. "INMUNES" se sacó de la escena del bebé: los
  bebés no son inmunes, solo no se contagian todavía.
- **Personajes (V2):** Vos sale solo en la apertura (0 a 8,8 s) y en el cierre del loop. El resto lo hacen la almohada,
  el bostecito, los animales, el libro y caras genéricas.
- **Sonido:** solo golpes cortos (pop, tick, clic, clunk, plop, golpe, ding), efectos al 40%. Sin sonido de bostezo.
- **Loop:** "Si todavía no bostezaste, no te preocupes." -> "Antes de que termine este video, vas a bostezar." El cierre
  es la apertura con el tiempo corrido (`d_apertura(t - TOTAL)`) desde 48,7 s: Vos vuelve al centro, la barra llega
  al final y el bostecito bosteza en "bostezaste"; Vos sonríe en "preocupes" y vuelve a la pose del primer cuadro. La
  barra se vacía al repetir, como un video que vuelve a empezar (diferencia media entre el primer y el último cuadro
  del MP4: 3,0, contando los subtítulos y la barra). `COLA = 0.3`.
- **Duración (D1):** 51,8 s.
- **Salida:** `salidas/por_que_los_bostezos_se_contagian.mp4`, 51,8 s, 1080x1920, 30 fps, −14,2 LUFS (pico −2,8 dBFS).
- **Publicación:** título "¿Por qué los bostezos se contagian?". Descripción: "Antes de que termine este video, vas a
  bostezar. Por qué el bostezo se contagia, a quién le pasa y qué no se sabe. #curiosidades #ciencia #sabiasque
  #bostezo #cerebro. Fuentes: NBC News, Live Science, CBS News, PLoS ONE (Norscia y Palagi, 2011), Universidad de
  Duke (2014)." Comentario para fijar: "¿Bostezaste? Sé honesto."
