# ¿Por qué pueden operarte el cerebro despierto? — notas

Short #23 de la planilla. Animación procedural (`cerebro.py`), armazón de `astronauta.py`; usa `pantalla.py`,
`picante.py`, el cerebro con cara de `sueno.py` (`S.cerebrito`, `S.ojo_p`) y el Vos de `kit.py`.

- **Guion:** el "Cerebro" del chat del 15/11 (guion 4 de la tanda Altura, Momias y Cerebro), con la apertura cambiada
  por el usuario en el audio. El guion del 15/11 decía "Tu cerebro siente cada dolor tuyo, menos el propio. […] ¿Qué
  pasa entonces si te lo operan despierto? No es ciencia ficción: se hace hoy." El audio dice "Tu cerebro interpreta el
  dolor de tu cuerpo, menos el del propio cerebro. […] Por eso, muchas veces te lo operan despierto." Los subtítulos
  siguen al audio. El resto es igual.
- **Fuentes:** Mayo Clinic y Johns Hopkins (el tejido del cerebro no tiene receptores de dolor; el dolor de cabeza sale
  de vasos, membranas y músculos de alrededor); King's College Hospital, febrero de 2020 (violinista despertada para
  tocar mientras le sacaban un tumor del lóbulo frontal derecho, junto a la zona que mueve la mano izquierda; conservó la
  función de la mano); Inserm (la capa más fina pegada al cerebro y sus vasos sí pueden doler: el guion dice "ahí
  adentro", que es el tejido).
- **Audio:** ElevenLabs, `procesar_voz.py --sin-eq --pausa 0.3`: 48,4 s -> 45,7 s, −14,2 LUFS. La voz va a 3,3
  palabras por segundo (150 en 45,5 s). La transcripción coincide palabra por palabra con el guion del audio; sin
  nombres mal pronunciados.
- **Segundos clave:** primer dato fuerte a los 6,6 s ("Por eso, muchas veces te lo operan despierto"); pregunta a los
  22,2 s ("¿Para qué despertarlo?"). Al sacar la pregunta del segundo 5, C3 queda rota: el misterio se planta como
  afirmación a los 6,6 s.
- **Primer cuadro (G2):** Vos pisa una chinche: estrella del golpe, "¡AY!", el rayito rojo empieza a subir hacia el
  cerebro que flota arriba de su cabeza (unido por un cable punteado) y el medidor de DOLOR está vacío.
- **Escenas:** apertura (tres golpes: pie y las dos manos; los rayitos suben por el cuerpo al cerebro, que hace mueca y
  llena el medidor; en "menos el del propio cerebro" el medidor se vacía y un dedo con guante toca el cerebro tres
  veces sin que pase nada; "0" verde en "dolería") → quirófano (cabeza del paciente con paño verde y una ventana donde se
  ve el cerebro, monitor con latido, sonda con guante; sello DESPIERTO; abre los ojos; habla, globo "BLA, BLA") → corte
  en capas (PIEL, HUESO, MEMBRANA y el cerebro con cara; los sensores con cara aparecen solo en las capas de afuera; la
  lupa no encuentra ninguno adentro: "0"; la jeringa los duerme uno por uno; en "dolor de cabeza" se despiertan rojos y
  las capas se ponen rojas mientras el cerebro sonríe) → mapa del hemisferio izquierdo ("?"; la línea de corte crece de
  más y pisa cerebro sano: cruz roja; zona HABLA en la parte de abajo del lóbulo frontal, arriba de la cisura lateral, y
  el tumor pegado; mientras el globo dice "BLA, BLA" la sonda achica el tumor y aparece un tilde; "B... B..." en rojo,
  la zona titila, la sonda se frena con luz roja; sello POR AHÍ NO) → Londres (torre del reloj genérica, cartel
  "LONDRES, 2020", violín) → mapa del hemisferio derecho, en espejo con "FRENTE →" (franja que mueve el cuerpo adelante
  de la cisura central, zona MANO y el tumor adelante, en el lóbulo frontal) → violín (sello DESPIERTA; suben del paño
  solo las manos con el violín; toca y salen notas; arriba, el mapa chico con la sonda que saca el tumor de al lado de la
  zona de la mano) → mano izquierda grande, palma hacia nosotros, que mueve los dedos; sello INTACTA → cierre.
- **Exactitud (V4):** el dibujo del cerebro de `pantalla.py` tiene el cerebelo y el tronco atrás a la derecha, así que
  sin espejo el frente queda a la izquierda (hemisferio izquierdo, donde está la zona del habla) y con espejo, a la
  derecha (hemisferio derecho, el de la violinista). Las curvas sueltas del dibujo se reemplazaron por la cisura lateral
  y la central en su lugar. Las capas son cuero cabelludo, hueso y duramadre: la voz dice "la piel y el hueso" y la
  jeringa duerme también la membrana, que es lo que se hace con anestesia local. Pulgar de la mano izquierda con la
  palma hacia nosotros: a nuestra izquierda.
- **Personajes:** Vos sale solo en la apertura (V2) y vuelve en el cierre del loop. El paciente del quirófano es
  genérico. La violinista no tiene cara ni nombre (T2): solo manos y violín.
- **Sonido:** solo golpes cortos (golpe, pop, plop, tick, clic, clunk, ding), el bip del monitor cada 0,85 s muy bajo y
  notas cortas de cuerda (`s_nota`) mientras toca. Efectos al 40%.
- **Loop:** "…gracias a un detalle." -> "Tu cerebro interpreta el dolor…". El cierre es la apertura con el tiempo corrido
  (`d_apertura(t - TOTAL)`) desde 44,7 s: aparecen Vos, el cerebro, el medidor y la chinche, y la estrella del golpe
  cae justo al cerrar. El cuadro de TOTAL es igual al de 0 (diferencia 0,0); el último cuadro renderizado difiere en
  0,36 de media. `COLA = 0.3`.
- **Duración (D1):** 45,8 s, por debajo de los 50.
- **Salida:** `salidas/por_que_pueden_operarte_el_cerebro_despierto.mp4`, 45,8 s, 1080x1920, 30 fps, −14,1 LUFS (pico
  −3,0 dBFS).
- **Publicación:** no publicarlo seguido de "Así operaban antes de la anestesia" (#17), que abre con "te operaban
  despierto". Descripción: "El cerebro no siente dolor, y por eso se puede operar con el paciente despierto.
  #curiosidades #ciencia #sabiasque #cerebro #cuerpohumano. Fuentes: King's College Hospital (2020), Mayo Clinic,
  Inserm." Comentario para fijar: "¿Te animás a estar despierto mientras te operan el cerebro?"
