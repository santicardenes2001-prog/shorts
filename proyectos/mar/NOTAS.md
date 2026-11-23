# ¿Por qué el mar es salado si los ríos son dulces? — notas

Animación procedural (`mar.py`), armazón de `dedos.py`; usa `pantalla.py`, `picante.py` (fondo, caras, sonidos) y
`tierra.py` (ayudas de dibujo, nube y sol). Sin Vos.

- **Guion:** el 2 de la tanda del chat "Guiones para shorts" (21/11/2026), con la respuesta "Por acumulación" pedida
  por el usuario; respetado palabra por palabra. Fuentes: la sal del mar viene sobre todo de las rocas de la tierra,
  que la lluvia (apenas ácida) desgasta; los ríos la llevan al mar (USGS, NOAA); sodio y cloruro son más del 85-90% de
  los iones disueltos en el agua de mar (NOAA, USGS); también entra sal por las chimeneas hidrotermales y los volcanes
  del fondo, por eso "casi toda" (NOAA); la sal esparcida sobre la tierra formaría una capa de más de 166 m, la altura
  de un edificio de 40 pisos (USGS, NOAA). La sal se cuenta en pasado ("se juntó"): hoy entra y sale más o menos lo
  mismo (NOAA).
- **Audio:** ElevenLabs (Agustín – Warm, Expressive), `procesar_voz.py --sin-eq --pausa 0.3`: 56,6 s -> 51,8 s,
  −14,0 LUFS. 169 palabras en 51,7 s: 3,27 palabras por segundo. `transcribir.py` lo transcribió completo sin errores
  ("Aún así" se escribe "Aun así" en `NARRACION`; "40" en cifra). El audio dice "Por acumulación, como una alcancía…"
  de corrido: el guion aprobado tenía "Por acumulación." como frase suelta. El sello igual cae en "acumulación".
- **Segundos clave:** pregunta a los 6,9 s ("¿de dónde sale la sal?"; la frase arranca a los 5,1 s); primer dato
  fuerte a los 12,5 s ("Dice sodio, lo mismo que sala el mar"). Segunda pregunta a los 19,9 s y "Por acumulación" a
  los 23,6 s.
- **Primer cuadro (G2):** paisaje con montañas, sol y nubes; el río con cara feliz baja y desemboca en el mar, que
  tiene cara de salado (boca ondulada, cejas preocupadas). El agua del río corre y salpica desde el primer cuadro.
- **Escenas:** apertura (en "dulce" brilla el río y sale DULCE; en "salado" el mar cierra los ojos, saca la lengua y
  cae el sello SALADO; la cámara se acerca a la desembocadura, entran gotas felices y aparece un salero con "?") →
  gota grande: DULCE se tacha en "tan", aparecen granitos de sal adentro, ¡TIENE SAL! → botella de agua con cara; la
  etiqueta se agranda (COMPOSICIÓN en mg por litro: calcio, magnesio, sodio, potasio) y en "sodio" se resalta la fila;
  el cartel SODIO viaja al mar: grano = mar → río visto de costado con montañas: las piedras del fondo hacen muecas y
  les salen granos que se lleva la corriente (PIEDRAS) → vaso de agua de río con pajita y medidor de SAL casi en cero
  (CASI NADA) → un granito en la playa frente al mar enorme; la cámara se aleja → corte seco: sellos POR y
  ACUMULACIÓN con una lluvia de granos que se apila → alcancía chanchito: caen monedas de a una, +1, se ven por la
  ventana de la panza (DE A UNA) → ciclo: el sol, gotas que suben del mar a la nube, los granos saltan y no pueden
  subir (SE QUEDA), llueve sobre la montaña, el río trae un grano nuevo (+1), flechas del ciclo (VA Y VIENE) y los
  granos se multiplican → el mar en una pecera que se llena de puntitos de sal mientras corre un calendario hasta
  300.000.000 de años (CIENTOS DE MILLONES) → una montaña de sal con cara sale del mar, sube sobre la Tierra y se
  vuelca: los continentes se ponen blancos de a uno (TODOS LOS CONTINENTES) → edificio de 40 pisos con cara; la capa
  de sal sube con el contador PISO 1 a 40 y lo pasa; el edificio queda enterrado como fantasma (40 PISOS) → cierre.
- **Hilo visual:** los granos de sal con cara aparecen en casi todas las escenas: en la gota, en la etiqueta, en las
  piedras, frente al mar, en el ciclo, en la montaña de sal y en el río del cierre.
- **Exactitud (V4):** la sal del mar se dibuja disuelta (granos y puntitos flotando en el agua), no apilada en el
  fondo; los granos no suben con las gotas. Los valores de la etiqueta son de un agua mineral cualquiera (sodio 14
  mg/L; las marcas van de unos pocos a decenas). Los continentes del globo son caricaturas (vista centrada en el
  Atlántico). El edificio tiene 40 pisos dibujados.
- **Personajes (V2):** Vos no aparece. Caras: río, mar, gota, botella, vaso, granos, piedras, salero, chanchito, sol,
  nube, montaña de sal, Tierra y edificio.
- **Cámara:** acercamiento lento dentro de cada escena del medio (`deriva`), golpe de zoom al entrar y corte seco en
  "Por acumulación".
- **Sonido:** solo golpes cortos (pop, tick, clic, clunk, plop, golpe, ding, crunch corto), efectos al 40%.
- **Loop:** "…el agua dulce de los ríos." -> "Todos los ríos del mundo le echan agua dulce al mar." El cierre es la
  apertura con el tiempo corrido (`paisaje(t - TOTAL)`) desde 49,0 s, con granitos que bajan por el río y se apagan
  antes del final. Diferencia media entre el primer y el último cuadro del MP4: 2,0 (0,8 sin subtítulos).
  `COLA = 0.3`.
- **Duración (D1):** 52,0 s.
- **Salida:** `salidas/por_que_el_mar_es_salado.mp4`, 52,0 s, 1080x1920, 30 fps, −14,0 LUFS (pico −2,4 dBFS).
- **Publicación:** título "¿Por qué el mar es salado si los ríos son dulces?". Descripción: "Todos los ríos le
  echan agua dulce al mar, y aun así el mar es salado. La respuesta: acumulación. #curiosidades #ciencia #sabiasque
  #mar #oceano. Fuentes: USGS (Why is the ocean salty?), NOAA Ocean Service." Comentario para fijar: "Si pudieras
  sacarle la sal al mar, ¿lo harías?"
