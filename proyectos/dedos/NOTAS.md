# ¿Por qué solo se arrugan los dedos? — notas

Animación procedural (`dedos.py`), armazón de `bostezo.py`; usa `pantalla.py`, `picante.py` (fondo, caras, gota, vaso,
sonidos), `tierra.py` (ayudas de dibujo, sellos, carteles) y la cabeza de Vos de `kit.py`.

- **Guion:** escrito por el usuario el 21/11/2026, respetado palabra por palabra. Guion técnico armado en el mismo
  chat; el usuario pidió que se vea profesional, sin errores, dinámico y sin tiempo estático.
- **Fuentes:** Lewis y Pickering (años 30: sin arrugas con el nervio dañado); Wilder-Smith (2003-2004: las arrugas
  vienen de la vasoconstricción); Kareklas, Nettle y Smulders, *Biology Letters* 2013 (agarre de objetos mojados);
  Haseleu y otros, *PLoS ONE* 2014 (no lo pudo repetir); Laytin y German, Binghamton University,
  *Journal of the Mechanical Behavior of Biomedical Materials* 2025 (el dibujo se repite y sigue a los vasos).
  Avisos al usuario: "solo los dedos" deja afuera palmas y plantas, que también se arrugan, aunque menos; el
  experimento del agarre está discutido.
- **Audio:** ElevenLabs (Agustín – Warm, Expressive), `procesar_voz.py --sin-eq --pausa 0.3`: 56,6 s -> 50,6 s,
  −14,1 LUFS. 164 palabras en 50,5 s: 3,2 palabras por segundo. `transcribir.py` escribió "chup" y "siguien";
  transcriptos solos dicen "chupa" y "siguiendo": el audio sigue el guion.
- **Segundos clave:** pregunta a los 5,4 s ("¿Por qué solo se arrugan los dedos?"); primer dato fuerte a los 16,1 s
  ("No es el agua: es una orden de tus nervios").
- **Primer cuadro:** Vos en una bañera celeste con espuma, la mano izquierda saliendo del agua con la palma hacia
  nosotros, el patito de goma y vapor; la cámara ya se acerca a la mano.
- **Escenas:** bañera (las arrugas se dibujan en vivo en "arrugan"; la cámara baja por el antebrazo y un brillo lo
  recorre en "liso"; "?" y anillo en las yemas) → yema gigante con huella; gotas que vuelan hacia la piel y se vuelve
  esponja con cara → burbuja de pensamiento: una persona se arruga entera de los pies a la cabeza → la burbuja explota:
  mano y planta del pie; brillan y se arrugan solo las yemas en "manos" y "pies" → gota con cara que se encoge de
  hombros, sello NO → mano con los nervios; el nervio con cara grita la orden y los pulsos suben a las yemas → corte de
  costado de la yema (uña, falanges, nervio, vasos con glóbulos): los vasos se achican, la yema se desinfla junto con
  un globo con cara y la piel se pliega → mano con un nervio cortado: los pulsos arrugan cuatro dedos y el índice queda
  liso → "?" gigante → experimento en dos paneles: dedos lisos (se les cae la canica dos veces) contra arrugados, con
  cronómetro → yema sobre un vidrio mojado: el agua sale por los canales → neumático en ruta mojada, ranuras que
  brillan → paneles: mano que agarra un vaso mojado y pie que pisa un piso mojado → yema gigante: dibujos al azar que
  se frenan en el de siempre → fotos BAÑO 1 y BAÑO 2 que coinciden; la piel se vuelve transparente y se ven los vasos
  debajo de cada arruga → las arrugas se van y el dibujo queda latente → la cámara se aleja hasta la bañera.
- **Exactitud:** mano izquierda con la palma hacia nosotros en todo el video (pulgar a nuestra izquierda), cinco dedos.
  Un solo dibujo de arrugas por dedo (`PATRONES`), en coordenadas de la yema: el mismo en la mano chica, la yema
  gigante y las fotos; las arrugas siguen a los vasos. Arrugas solo del lado de la yema, nunca en la uña. En el corte,
  lo que se pliega es la piel, no el hueso; la última falange tiene la punta ensanchada. La planta es del pie izquierdo
  (dedo gordo a nuestra izquierda). En el vaso se ven las uñas: la yema está contra el vidrio.
- **Dinamismo:** vaivén suave de cámara en todo el video (`flotar`, cierra en el loop) más acercamientos por escena.
  Medido en el MP4 (diferencia entre cuadros a 10 fps): 7% de cuadros casi quietos y como máximo 0,8 s seguidos
  (Más alto: 43% y 1,3 s; Cerebro: 51% y 1,9 s).
- **Personajes (V2):** Vos sale solo en la bañera (apertura y cierre del loop).
- **Sonido:** golpes cortos (pop, tick, plop, clic, clunk, ding, boing, golpe, whoosh suave), chispazo del nervio y
  siseo del globo; efectos al 40%.
- **Loop:** "Esperando el próximo baño." -> "Después de un baño largo…". El cierre es la bañera con el tiempo corrido
  (`d_bano(t - TOTAL)`): la cámara se aleja desde la yema y la mano baja hasta la posición del primer cuadro. El cuadro
  de TOTAL es igual al de 0 (diferencia 0,0 sin subtítulos). `COLA = 0.3`.
- **Duración (D1):** 50,8 s.
- **Salida:** `salidas/por_que_solo_se_arrugan_los_dedos.mp4`, 50,8 s, 1080x1920, 30 fps, −14,1 LUFS (pico −2,4 dBFS).
- **Publicación:** título "¿Por qué solo se arrugan los dedos?". Descripción: "Después de un baño largo tus dedos se
  arrugan, pero tu brazo no. No es el agua: es una orden de tus nervios. #curiosidades #ciencia #sabiasque
  #cuerpohumano #dedos. Fuentes: Binghamton University (2025), Biology Letters (2013), PLoS ONE (2014)."
  Comentario para fijar: "¿Te fijaste alguna vez si tus arrugas salen siempre iguales?"
