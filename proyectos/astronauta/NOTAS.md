# Cocinarse a 270 grados bajo cero — notas

Short de la tanda del 16/11/2026 (agua, astronauta, hielo, nube). Animación procedural (`astronauta.py`), armazón de
`altura.py` (de ahí salen la estación y el astronauta); usa `pantalla.py`, `picante.py` y las piezas espaciales de
`cielo.py` (estrellas, Tierra y Sol) y el Vos de `kit.py`.

- **Guion:** el del doc "Guiones: agua, astronauta, hielo y nube" (16/11), sin cambios. Mecanismo de Estómago: dos
  hechos aceptados (el espacio está a −270 y un astronauta afuera) llevan a algo que no debería pasar (se cocina).
  Fuentes: Space Center Houston citando a NASA (la malla tiene unos 300 pies de tubos, ≈91 m: el guion dice "más de
  70"); NASA NTRS 20140003403 (el sublimador del traje de la estación es una placa porosa: el agua se congela y el hielo
  pasa a vapor hacia el vacío; se usa desde Apollo); patente US 5092129 (la mayor parte del calor del traje es el del
  cuerpo). "−270" es la temperatura del fondo del universo (2,7 K).
- **Audio:** ElevenLabs, `procesar_voz.py --sin-eq --pausa 0.3`: 55,3 s -> 50,5 s, −14,2 LUFS. La voz sale a
  3,2 palabras por segundo (161 en 50,3 s). `transcribir.py` juntó "café sigue" en "cafue"; al transcribir ese tramo
  solo, la voz dice el guion bien, y en `palabras.json` se separaron las dos palabras con esos tiempos. Los números van
  en cifras en `NARRACION` ("270", "70").
- **Segundos clave:** primer dato fuerte a los 3,4 s ("Y aun así, un astronauta afuera de la nave se puede cocinar";
  "cocinar" a los 6,5 s); pregunta a los 7,0 s ("¿Cómo te cocinas a 270 bajo cero?").
- **Primer cuadro (G2):** espacio con la estación, el astronauta con el cable, la Tierra abajo y el termómetro gigante
  con el líquido rojo que ya está bajando; llega a −270 a los 1,5 s ("270") y se cubre de escarcha.
- **Escenas:** apertura (termómetro que baja, cartel "−270 °C"; en "cocinar" el medidor del pecho pasa a rojo, el visor
  se empaña con gotas de sudor y aparecen bolitas de calor adentro del traje) → pantalla partida AFUERA/ADENTRO con dos
  termómetros y "?" → Tierra: a Vos le salen bolitas de calor y las bolitas de aire se las llevan → espacio: las
  bolitas quedan adentro del traje, bolitas de aire fantasma tachadas y "SIN AIRE" → termo cortado al medio (pared de
  afuera, hueco sin aire con cruces, pared de adentro, café con vapor y bolitas que rebotan), reloj de 08:00 a 15:00 →
  el café se vacía, aparece el astronauta adentro del termo, el hueco se llena de estrellas ("ESPACIO") y "= CAFÉ" →
  guante con llave que da tres vueltas a un bulón: cada vuelta suelta una bolita que entra al termómetro "TRAJE" y lo
  sube un escalón → rayos X: aparece la malla de tubitos, un tubito desenrollado y el contador "+70 m", copo en "fría"
  y las bolitas se meten en los tubitos → los tubitos pasan a rojo; "?" y una bolita que choca contra el borde del
  traje; afuera, bolitas de aire tachadas y "NADA" → el astronauta se da vuelta y sale un cubito con cara de la
  mochila → corte de la mochila: tanque de AGUA, caño, placa con poros, tubo rojo que viene del traje; las gotitas
  llegan a la placa, se congelan (copos), el hielo se hace vapor que se va al VACÍO llevándose bolitas de calor, y el
  tubo sale azul → vuelve el plano del espacio: el medidor baja a verde, esquinas con escarcha y sello "−270 °C";
  copos en la mochila e hilito de vapor → cierre: vuelve a entrar el termómetro gigante.
- **Exactitud (V4):** el calor solo sale del traje por la mochila (en ninguna otra escena sale vapor ni calor del
  traje). El agua que se congela es la del tanque, aparte de la de los tubitos: el tubo rojo pasa pegado a la placa y
  vuelve frío. La placa es porosa y da al vacío. Estación genérica, sin marcas.
- **Personajes (V2):** Vos sale solo en la Tierra (9,8 a 13,0 s). Las caras están en el termómetro, las bolitas de
  calor y de aire y el cubito; el astronauta va con el visor oscuro.
- **Sonido:** solo golpes cortos (pop, tick, clic, clunk, plop, golpe, ding), efectos al 40%.
- **Loop:** "Aunque afuera," -> "El espacio está a 270 grados bajo cero." El cierre es la apertura con el tiempo corrido
  (`d_apertura(t - TOTAL)`): el termómetro entra y el líquido empieza a bajar justo al cerrar. El cuadro de TOTAL es
  igual al de 0 (diferencia 0 fuera de los subtítulos); el último cuadro renderizado difiere en 0,75 de media.
  `COLA = 0.3`.
- **Duración (D1):** 50,6 s, 0,6 s por encima de los 50.
- **Salida:** `salidas/cocinarse_a_270_bajo_cero.mp4`, 50,6 s, 1080x1920, 30 fps, −14,2 LUFS (pico −2,3 dBFS).
- **Pendiente:** el usuario no está conforme con el guion técnico de la animación; esta versión lo sigue tal cual
  para revisarlo sobre el video.
