# ¿Por qué se arrugan los dedos en el agua? — notas

Animación procedural (`dedos.py`), armazón de `bostezo.py`; usa `pantalla.py` (cerebro), `picante.py` (fondo, caras,
sonidos), `tierra.py` (ayudas de dibujo) y a Vos de `kit.py`.

- **Guion:** escrito por el usuario el 21/11/2026 y respetado palabra por palabra. Fuentes: las arrugas las produce
  la contracción de los vasos de sangre ordenada por el sistema nervioso, no la hinchazón de la piel; un dedo con el
  nervio dañado no se arruga (se sabe desde los años 30; Guy German, Binghamton University, en The Conversation y
  ScienceDaily); los dedos arrugados movieron canicas mojadas un 12% más rápido y no cambiaron con objetos secos
  (Kareklas, Nettle y Smulders, Biology Letters, 2013; Newcastle University); las arrugas como ranuras de neumático
  que sacan el agua (misma fuente; idea de Changizi, 2011); las arrugas salen casi con el mismo dibujo en dos baños
  separados por 24 h porque siguen a los vasos de sangre (German y Laytin, Journal of the Mechanical Behavior of
  Biomedical Materials, 2025; Science News). Matices que no cambian el guion: el agua sí es el disparador (entra por
  los poros del sudor y el nervio avisa), un estudio de 2014 no replicó la ventaja de agarre y otro de 2021 sí la
  encontró (Davis, PLoS ONE), y el estudio del dibujo fue con 3 voluntarios y algunas arrugas no coincidieron.
- **Audio:** ElevenLabs (Agustín – Warm, Expressive), `procesar_voz.py --sin-eq --pausa 0.3`: 56,6 s -> 50,6 s,
  −14,1 LUFS. 164 palabras en 50,5 s: 3,25 palabras por segundo. `transcribir.py` escribió "chup" y "siguien" (y
  "tus" de duración cero); al transcribir esos tramos solos dice "chupa" y "siguiendo tus", así que el audio sigue
  el guion. Se corrigió en `palabras.json` ("tus" con 0,24 s después de "siguiendo"). El audio dice "mojado y sigue
  liso" sin pausa en la coma.
- **Segundos clave:** pregunta a los 5,4 s ("¿Por qué solo se arrugan los dedos?"); primer dato fuerte a los 16,1 s
  ("No es el agua: es una orden de tus nervios").
- **Primer cuadro (G2):** Vos en la bañera con espuma y patito, un reloj en la pared y una lupa (burbuja que apunta a
  su mano bajo el agua) con tres yemas lisas. En "baño largo" el minutero da vueltas; en "arrugan" se dibujan las
  arrugas en la lupa.
- **Escenas:** bañera → mano y antebrazo grandes con gotas que bajan: las yemas arrugadas, "LISO" con tilde en el
  antebrazo, cuatro "?" sobre los dedos → la yema con cara "chupa" gotas, "=" esponja que se hincha → "¿Y SI FUERA
  ESO?": figura de una persona que se llena de arrugas, que se van en "solo" y quedan en manos y pies, que brillan →
  gota con cruz roja; el cerebro manda un pulso por el nervio hasta las yemas, sello ORDEN → yema grande en corte
  (vasos rojos y nervio amarillo); los vasos se achican con flechas, la yema se achica junto con un globo que se
  desinfla, el borde se ondula y aparecen las arrugas (SE PLIEGA) → dos dedos con su nervio; al de la derecha se le
  corta (NERVIO DAÑADO), les cae agua y solo se arruga el izquierdo; el otro queda LISO → "?" → EXPERIMENTO: dos
  pinzas de índice y pulgar con una canica mojada; la de los lisos la suelta en el cuenco, la de los arrugados la
  sostiene (tilde) → la yema arrugada larga gotas por los canales, "=" neumático con cara que gira y despide agua
  (RANURAS) → mano y planta del pie con las yemas que brillan (AGARRAS, PISAS) → yema que se arruga, "!", dos dados
  que ruedan y se tachan (AZAR) → BAÑO 1 = BAÑO 2 con el mismo dibujo y, en "siguiendo", los vasos debajo de cada
  arruga (SIGUEN LOS VASOS) → yema lisa con el dibujo escondido en líneas punteadas amarillas (YA ESTÁ AHÍ) → cierre.
- **Hilo visual:** el dibujo de las arrugas (`CURVAS`) es uno solo y es el mismo camino que los vasos de sangre: está
  en la lupa, en la yema grande, en las dos yemas iguales y en el dibujo escondido del final.
- **Exactitud (V4):** las arrugas se forman solo en las yemas de manos y pies y corren a lo largo del dedo,
  ramificadas; la mano se ve del lado de la palma (sin uñas), con el índice junto al pulgar y el meñique más corto.
  El nervio de cada dedo va por el centro y se abre en la yema; los vasos se dibujan debajo de las arrugas.
- **Personajes (V2):** Vos sale solo en la apertura (0 a 2,8 s) y en el cierre del loop (desde 48,9 s). El resto lo
  hacen la mano, las yemas, la gota, la esponja, el globo, el neumático, los dados y una figura genérica (no es Vos).
- **Sonido:** solo golpes cortos (pop, tick, clic, clunk, plop, golpe, ding, crunch corto, zap), efectos al 40%.
- **Loop:** "Esperando el próximo baño." -> "Después de un baño largo, tus dedos se arrugan." El cierre es la
  apertura con el tiempo corrido (`d_apertura(t - TOTAL)`) desde 48,9 s: vuelve la bañera con la lupa de yemas
  lisas; burbujas, vapor y patito son periódicos y el cuadro de TOTAL es el de 0. `COLA = 0.3`.
- **Duración (D1):** 50,8 s.
- **Salida:** `salidas/por_que_se_arrugan_los_dedos.mp4`, 1080x1920, 30 fps.
- **Publicación:** título propuesto "¿Por qué se arrugan los dedos en el agua?". Descripción: "Después de un baño
  largo, tus dedos se arrugan, pero tu brazo no. No es el agua: es una orden de tus nervios. #curiosidades #ciencia
  #sabiasque #cuerpohumano #dedos. Fuentes: Binghamton University (German y Laytin, Journal of the Mechanical
  Behavior of Biomedical Materials, 2025), Kareklas, Nettle y Smulders (Biology Letters, 2013), Newcastle
  University." Comentario para fijar: "¿Tú también creías que era el agua?"
