# ¿Por qué odias tu voz grabada? — notas

Animación procedural (`voz.py`), armazón de `bostezo.py` (importa de ahí `cabeza`, `torso`, `cara`, `corazon`,
`medidor` y `ondas`); usa `pantalla.py`, `picante.py` (fondo, caritas, sonidos), `tierra.py` (carteles, sellos,
signos) y a Vos de `kit.py`.

- **Guion:** el 2 de la tanda del chat del 26/11/2026 ("crear un guion"), reescrito a pedido del usuario: la respuesta
  ("tus huesos") no se da de entrada, se arma con dos pruebas (taparse los oídos y la mano en la garganta) y llega a
  los 22 s ("tu cráneo"). Fuentes: la voz llega al oído por el aire y por los huesos del cráneo, que suman graves; el
  micrófono solo capta el aire (Scientific American); taparse los oídos hace sonar la voz más retumbante: efecto de
  oclusión (ÉTS Montréal); 80 personas calificaron voces grabadas sin saber que estaba la suya y la puntuaron mejor
  que los demás y mejor que las ajenas (Hughes y Harrison, Perception, 2013).
- **Audio:** ElevenLabs (Agustín – Warm, Expressive), `procesar_voz.py --sin-eq --pausa 0.3`: 53,8 s -> 46,9 s,
  −14,2 LUFS. 149 palabras en 46,7 s: 3,19 palabras por segundo. Es la segunda toma: la primera (26/11) decía
  "tus audio", sin la s. Esta dice el guion entero; "80" en cifra en `NARRACION`.
- **Segundos clave:** pregunta a los 6,0 s ("¿De dónde sale, entonces, la que oyes tú?"); primer dato fuerte a los
  3,0 s ("La verdadera es la de tus audios"); respuesta a los 22,0 s ("Tu cráneo").
- **Primer cuadro (G2):** Vos de frente, con las ondas doradas de su voz que salen de la boca y le vuelven a entrar
  por las dos orejas; ya se mueven en el primer cuadro.
- **Escenas:** apertura (Vos habla con boca sincronizada; en "verdadera" se corre a la izquierda y entra el celular
  con el audio, cartel TU VOZ REAL y anillos blancos; en "odias" Vos pone cara de vergüenza y suda) → cabeza de
  perfil con una onda dorada que da vueltas buscando por dónde entra; anillos en la oreja y "?" → el muñequito se
  tapa las orejas, habla, la voz queda adentro (anillos dorados dentro de la cabeza), ¡MÁS FUERTE!, sube el barril con
  eco; la cámara se acerca y caen los carteles CERRADO en las manos → la mano en la garganta, la garganta vibra
  (rayitas), ¡VIBRA!, el pulso dorado arranca a subir y la cámara lo sigue → corte seco al perfil a oscuras: el pulso
  sube por la mandíbula hasta el oído, se ilumina la oreja, "?"; en "cráneo" se prende el cráneo en rayos X, vibra,
  destello y cartel CRÁNEO; zoom al oído, aparece el parlante con cara pegado a la cóclea y la perilla BAJOS que sube
  → micrófono con cara que se encoge de hombros; calavera tachada en "huesos" → el muñequito habla, las ondas blancas
  van por el aire al micrófono (cartel AIRE) y a dos amigos, que reciben tilde → perilla BAJOS que cae y la onda que
  se afina, cartel AGUDA → 80 caras con auriculares que aparecen en diagonal, contador hasta 80 PERSONAS, estrellitas
  de calificación y tarjetas de audio que pasan → el muñequito escucha; el carrusel de audios frena en el centro en
  "estaba la suya" y esa tarjeta brilla con su cara → barras ÉL (alta, con estrella en "mejor") y LOS DEMÁS → feliz
  con corazones; la tarjeta con "?"; en "suya" cae el sello ES TU VOZ y le cambia la cara a vergüenza → cierre.
- **Loop (F4):** el cierre es la apertura con el tiempo corrido (`d_apertura(t - TOTAL)`), sin celular: el último
  cuadro es igual al primero (Vos con la boca cerrada y las ondas en la misma fase, período 1,3 s). La última frase
  ("Lo que te molesta es descubrir que") empalma con la primera.
- **Vos (V2):** solo en la apertura (0 a 6,0 s) y en el cierre (desde 44,6 s).
- **COLA:** 0,3 s.
- **Salida:** `salidas/por_que_odias_tu_voz_grabada.mp4`, 1080×1920, 30 fps, 47,0 s, −14,2 LUFS medidos en el MP4
  final (pico −1,7 dBFS).
- **Revisión:** hojas de fotogramas de cada escena y de antes y después de cada corte. Se corrigió: la manga de la
  mano en la garganta quedaba suelta (se agregó el antebrazo) y esa cara no tenía ojos; el micrófono y la gente
  quedaban chicos; en la transición a la onda aguda quedaba un amigo asomado arriba; las tarjetas del estudio y las
  etiquetas de las barras pisaban los subtítulos; la tarjeta "suya" frenaba fuera del centro; la perilla tapaba el
  parlante.
