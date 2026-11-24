# ¿Por qué enterraban a los muertos con una campana? — notas

Animación procedural (`campana.py`), armazón de `bostezo.py` y `mar.py` (cámara con `deriva`, cortes secos); usa
`pantalla.py`, `picante.py` (fondo, sonidos) y `tierra.py` (ayudas de dibujo, carteles y sellos). Sin Vos.

- **Guion:** el 5 de la tanda del chat del 20/11/2026 ("pensar con estrategia 5 guiones"). Fuentes: el miedo a ser
  enterrado vivo llegó a su pico con las epidemias de cólera del siglo XIX, cuando se enterraba rápido y sin
  distinguir muertos de moribundos, y los diarios contaban de ataúdes arañados por dentro (History.com, Wikipedia
  "Safety coffin"); más de treinta diseños patentados en Alemania en la segunda mitad del siglo XIX; en 1822 un médico
  alemán se hizo enterrar vivo varias horas y le pasaron sopa, cerveza y salchichas por el tubo; un modelo levantaba una
  bandera y hacía sonar una campana si el cuerpo se movía (Karnice-Karnicki, 1897); las cuerdas atadas a brazos y
  piernas se activaban con los movimientos de un cuerpo que se descompone y se hincha (Wikipedia "Safety coffin",
  Australian Museum).
- **Audio:** ElevenLabs (Agustín – Warm, Expressive), `procesar_voz.py --sin-eq --pausa 0.3`: 61,6 s -> 55,3 s,
  −14,1 LUFS. 158 palabras en 55,1 s: 2,87 palabras por segundo. `transcribir.py` escribió "al muerto moribundo" y
  "una banderas": transcribiendo el tramo solo aparece "del" (se agregó en `palabras.json` con el tiempo del tramo);
  "banderas" se cambió por "bandera" (en el tramo solo dice "banderas y el cuerpo"; conviene escuchar el segundo 30,7).
  "200" y "30" en cifra en `NARRACION`.
- **Segundos clave:** pregunta a los 7,2 s ("¿Para qué querría un muerto una campana?"); primer dato fuerte a los
  9,4 s ("Por si no estaba muerto").
- **Primer cuadro (G2):** corte del cementerio de noche: luna, lápida R.I.P., poste con la campana, el tubo con la
  cuerda que baja bajo tierra hasta la mano que sale de la sábana dentro del ataúd.
- **Escenas:** apertura (HACE 200 AÑOS; la cuerda se ilumina de la campana a la mano y la cámara baja) → la cámara
  sube por la cuerda hasta la campana, "?" → corte seco a la mano: el dedo se mueve, panorámica rápida hacia arriba y
  la campana suena en "muerto" → CÓLERA: tres ataúdes caen en fosas, la tierra los tapa, reloj que gira rápido,
  MIEDO AL CONTAGIO → dos camillas con cuerpos tapados, casi iguales; la línea del pulso es plana en una y tiene un
  latido mínimo en la otra (MUERTO, MORIBUNDO, "?") → el diario gira y cae: LA GACETA, ¡ENTERRADO VIVO!; la cámara
  entra al grabado de la tapa y aparecen los arañazos → termómetro del MIEDO que se llena → el plano azul "ATAÚD DE
  SEGURIDAD" se dibuja de izquierda a derecha → ALEMANIA: 36 planitos que aparecen uno atrás del otro, sello MÁS DE 30
  → corte del cementerio: el tubo brilla y bajan flechas de aire (PARA RESPIRAR); después el dedo se mueve, sube la
  varilla y se despliega una bandera roja (SI SE MOVÍA) → maletín de MÉDICO y su plano con tilde → el ataúd baja a la
  fosa, late (está vivo), lo tapa la tierra, queda el tubo, reloj y VARIAS HORAS → sopa, cerveza y salchichas bajan
  por el tubo → tres planitos (campana, tubo, bandera), sello PROBLEMA → plano con el contorno del cuerpo acostado:
  cuerdas a BRAZOS y PIERNAS hasta la barra de la campana; el contorno se hincha (SE HINCHA), las cuerdas tiran y la
  campana suena → la campana suena sola en el cementerio vacío (SOLA) → plano más abierto, un farol se acerca desde la
  izquierda, "?" en "quién" → cierre.
- **Tono (V3):** historia oscura sin caras ni personajes; los cuerpos van siempre tapados con sábana o como contorno
  de plano; solo se ve una mano.
- **Cámara:** acercamiento lento en cada escena del medio (`deriva`), golpe de zoom al entrar, cortes secos en la
  pregunta, en "Por si no estaba muerto" y en "La campana podía sonar sola"; panorámicas por el corte del cementerio
  con `cam()`.
- **Sonido:** solo golpes cortos (pop, tick, clic, clunk, plop, golpe, ding, crunch, whoosh), efectos al 40%. La
  campana es "ding".
- **Loop:** "Si un vivo… o un muerto." -> "Hace unos 200 años, a algunos muertos los enterraban con una campana." El
  cierre es la apertura con el tiempo corrido (`d_apertura(t - TOTAL)`) desde 53,2 s: la cámara vuelve al plano del
  primer cuadro y la campana se mece en "vivo" y se queda quieta antes del final. Diferencia media entre el primer y el
  último cuadro del MP4: 2,1 (0,6 sin subtítulos). `COLA = 0.3`.
- **Duración (D1):** 55,4 s.
- **Salida:** `salidas/por_que_enterraban_con_campana.mp4`, 55,4 s, 1080x1920, 30 fps, −14,1 LUFS (pico −1,7 dBFS).
- **Publicación:** título "¿Por qué enterraban a los muertos con una campana?". Descripción: "Hace unos 200 años,
  a algunos muertos los enterraban con una campana. El miedo a ser enterrado vivo y los ataúdes de seguridad.
  #curiosidades #historia #sabiasque #historiaoscura #misterio. Fuentes: Wikipedia (Safety coffin), History.com,
  Australian Museum." Comentario para fijar: "¿Pedirías que te entierren con campana?"
