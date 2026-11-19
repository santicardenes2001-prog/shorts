# Vas a más de mil km/h y no lo sentís — notas

Animación procedural (`tierra.py`), armazón de `cerebro.py`; usa `pantalla.py`, `picante.py` (fondo, caras) y la cama
con Vos dormido de `kit.py`.

- **Guion:** el reescrito en el chat del 19/11/2026 (sobre el borrador del usuario "Estás acostado en tu cama…"). Sin
  cambios en el audio. Fuentes: rotación 1.670–1.675 km/h en el ecuador, y en cualquier latitud = ecuador × coseno de la
  latitud (regla de la NASA citada por Ecoticias, abril 2026): Buenos Aires ≈ 1.380 km/h, Ciudad de México ≈ 1.580 km/h,
  así que "más de 1.000" vale para el público. Órbita 29,78 km/s ≈ 107.200 km/h (Wikipedia, "Earth's orbit"). Un avión
  de línea va a unos 900 km/h. No se siente porque las dos velocidades son constantes y el cuerpo solo registra los
  cambios.
- **Audio:** ElevenLabs (Agustín – Warm, Expressive), `procesar_voz.py --sin-eq --pausa 0.3`: 52,3 s -> 47,2 s,
  −14,2 LUFS. 141 palabras en 47,0 s: 3,0 palabras por segundo. La transcripción coincide con el guion; `transcribir.py`
  escribió "Oh, eso" y "las acudidas" (al transcribir esos tramos solos dice "O eso crees" y la "s" de "las sacudidas"
  queda pegada): se corrigió en `palabras.json`. Números en cifras en `NARRACION` ("1.000", "107.000").
- **Segundos clave:** primer dato fuerte a los 3,8 s ("La Tierra gira y te lleva a más de 1.000 kilómetros por hora";
  "1.000" a los 5,9 s); pregunta a los 9,1 s ("¿Por qué no sientes nada?").
- **Primer cuadro (G2):** Vos dormido en la cama (Zzz), la mesita de luz con el vasito de agua dormido y arriba un
  velocímetro grande en 0 KM/H.
- **Escenas:** apertura (en "O eso crees" la aguja tiembla, el vasito abre los ojos y mira, "?") → la cámara se aleja de
  la cama y aparece la Tierra vista desde el polo norte con la cama en el borde; la Tierra gira (antihorario, como se ve
  desde el norte) y el velocímetro sube a +1.000; un avión va al lado más lento y queda atrás, cartel "MÁS RÁPIDO QUE UN
  AVIÓN" → la pieza otra vez con rayitas de velocidad, velocímetro en +1.000 y "?" grande → marco punteado "SI FUERAS
  ASÍ…": bolitas de aire enojadas chocan al vasito, que se inclina y salpica; en "No pasa" se oscurece y cae la cruz
  roja → la Tierra con su capa de aire (bolitas contentas), la casa, la calle con farol y las nubes, todo girando junto;
  tildes AIRE, CASA, CALLE, NUBES → vasito grande ("TU CUERPO") y velocímetro: con la velocidad quieta el agua no se mueve
  y el vasito duerme ("0"); cuando la aguja salta, el agua se sacude y "!" → avión de costado entre nubes que pasan
  rápido; se abre el costado y el vasito camina por el pasillo ("COMO EN TU CASA"); DESPEGUE (se inclina para arriba y
  el vasito se va para atrás), ATERRIZAJE (para abajo) y SACUDIDAS (tiembla y salpica) → la Tierra con alas y cola de
  avión volando parejo; FRENA, ACELERA y SE SACUDE se tachan; el vasito duerme arriba de la Tierra, "0" → la cámara sale
  de la Tierra a la órbita: aparece el Sol y el velocímetro se pasa de rosca con 107.000 en rojo → cierre.
- **Exactitud (V4):** la Tierra gira y orbita en sentido antihorario visto desde el norte. El giro y la órbita están
  exagerados (una vuelta real tarda un día y un año). Continentes genéricos. El vasito es el sensor de "lo que siente el
  cuerpo": la superficie del agua se inclina con los cambios de velocidad, no con la velocidad.
- **Personajes (V2):** Vos sale solo en la pieza del principio (0 a 10,4 s, apertura y pregunta) y en el cierre del loop.
  El resto lo hacen el vasito, la Tierra, el Sol y las bolitas de aire.
- **Sonido:** solo golpes cortos (pop, tick, clic, clunk, plop, golpe, ding), efectos al 40%.
- **Loop:** "Aun así, jurarías que..." -> "Estás en tu cama, completamente quieto." El cierre es la apertura con el tiempo
  corrido (`d_apertura(t - TOTAL)`) desde 45,0 s: vuelven la cama, la mesita y el velocímetro, que entra en 107.000 y la
  aguja cae a 0 justo al cerrar. El cuadro de TOTAL es igual al de 0 (diferencia 0,0); el último cuadro renderizado
  difiere en 0,05 de media. `COLA = 0.3`.
- **Duración (D1):** 47,3 s.
- **Salida:** `salidas/vas_a_mas_de_mil_km_por_hora.mp4`, 47,3 s, 1080x1920, 30 fps, −14,2 LUFS (pico −3,6 dBFS).
- **Publicación:** título propuesto "¿Por qué no sientes que la Tierra gira?". Descripción: "Ahora mismo vas a más de
  1.000 km/h y no lo sientes. #curiosidades #ciencia #sabiasque #tierra #espacio. Fuentes: NASA, Wikipedia (Earth's
  orbit)." Comentario para fijar: "¿Sabías que ibas tan rápido o te enteraste ahora?"
