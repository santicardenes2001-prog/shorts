# ¿Por qué la Luna siempre muestra la misma cara? — notas

Short 1 de la tanda del 14/11/2026 (punto ciego, Luna, hospital). Animación procedural (`luna.py`), armazón de
`sueno.py`; usa las piezas espaciales de `proyectos/cielo/cielo.py` (estrellas, Tierra con cara, Vos y loma).

- **Guion:** el de la tanda, sin cambios. Misterio que se resuelve a los 27 s y sigue con un segundo hilo (la Luna
  frena a la Tierra). Fuentes: NASA (vía Audacy, 2026), Farmers' Almanac (Luna 3, 1959; día que se alarga), AGU
  (de Winter et al., 2020: 372 días por año y días de 23 h 31 min hace 70 millones de años).
- **Audio:** ElevenLabs (Agustín), `procesar_voz.py --sin-eq --pausa 0.3`: 53,6 s -> 48,2 s, −14,2 LUFS.
  `transcribir.py` reconoció todo el guion menos un "en" (tiempo interpolado; la voz lo dice bien).
- **Segundos clave:** pregunta a los 5,4 s ("Si gira, ¿por qué nunca se da vuelta?"); primer dato fuerte a los
  13,2 s ("Parece una coincidencia imposible, y no lo es").
- **Exactitud (V4):** la Luna gira en sentido antihorario visto desde arriba, igual que su órbita; en la vista de
  arriba la cara siempre apunta a la Tierra. El lado lejano no tiene cara, casi no tiene mares y tiene más cráteres.
  El reloj de los dinosaurios es de 24 h y la cuña roja mide 30 min (7,5°). En pantalla: "+0,002 SEGUNDOS" por
  siglo (las fuentes dan de 1,7 a 2,3 milisegundos). La sonda se dibuja como Luna 3: cilindro con cuatro antenas.
- **Personajes (V2):** Vos sale solo en la apertura y desde "ella" (T_VUELTA) para cerrar el loop.
- **Loop:** "Por ahora, la única atrapada es ella:" -> "La Luna gira, pero siempre te muestra la misma cara."
  El cuadro de TOTAL es igual al de 0 (diferencia media de 0,5 sobre 255; la flecha de giro da 6 vueltas exactas).
  `COLA = 0.3`.
- **Salida:** `salidas/la_luna_siempre_te_mira.mp4`, 48,4 s, 1080x1920, 30 fps, −14,1 LUFS (pico −2,6 dBFS).

## Versión 2 (15/11/2026), por corrección del usuario

La versión 1 no cumplió: ruido raro en la órbita, flechas que giraban al revés, la flecha como recurso malo y
pocas cosas para mirar. Para próximos Shorts: **no usar flechas de giro ni sonidos sostenidos (siseo, zumbido)**;
el giro se muestra con el objeto girando, y cada tramo necesita un recurso propio para mirar.

- **Apertura:** pasan 29 noches, cambia la fase y la cara es la misma ("NOCHE n", "¡LA MISMA CARA!").
- **Otro lado:** la mitad que da al espacio va pixelada, con "NUNCA VISTO".
- **Pregunta:** la Luna intenta darse vuelta como una moneda y rebota, con gotas de esfuerzo.
- **Órbita:** fantasmas cada cuarto de vuelta, espalda violeta y un recuadro "ELLA SOLA" que la muestra girando.
- **Casualidad:** dos rodillos de tragamonedas que caen en "27 DÍAS" (27,3 reales) y sello "NO LO ES".
- **Frenado:** la Luna gira de verdad, velocímetro "GIRO", chispas, cadena y candado con sacudida de cámara.
- **Foto y nave:** polaroid "SIN CARA"; la sonda saca la foto detrás de la Luna y la polaroid viaja a la Tierra.
- **Ella nos frena:** los continentes giran bajo la cara, marea que apunta a la Luna, velocímetro y caracol.
- **Siglo:** barra "TU DÍA: 24 HORAS" con una puntita amarilla y lupa "+0,002 s"; el siglo cambia de XVIII a XXI.
- **Dinosaurios:** el Sol cruza rápido el cielo, reloj con cuña de 30 min, "HACE 70 MILLONES DE AÑOS".
- **Futuro y cierre:** cadena, candado y reloj de arena; después el candado cae y solo queda atrapada ella.
- **Sonido:** solo golpes cortos (tick, pop, ding, clunk, clic), efectos al 40%.
- **Salida:** misma ruta, 48,4 s, −14,2 LUFS (pico −3,0 dBFS).
