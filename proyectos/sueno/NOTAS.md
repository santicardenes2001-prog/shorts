# Un día sin dormir te deja como borracho — notas

Short 6 de la tanda del 10/11/2026. Animación procedural (`sueno.py`), armazón de `anestesia.py`: usa `pantalla.py`,
`picante.py` y el Vos de `kit.py`.

- **Pedido del usuario:** usar las herramientas de animación que mejor sirvan para un gancho fuerte y para retener.
- **Herramientas de gancho y retención:**
  - **Primer cuadro en movimiento (G2):** Vos cansado, con ojeras, se bambolea y tiene visión doble (el personaje
    pintado dos veces, con desfase). En "borracho" hace "¡hic!", se marea y se le duplica más; en "No es una forma de
    decir" la imagen se endereza de golpe, y en "está medido" cae un sello rojo con temblor de cámara.
  - **Hilo que avanza:** un contador de horas despierto (0 → 17 → 24) y dos barras comparadas: 17 h igual a
    0,05 % de alcohol en sangre; a las 24 h las dos se duplican (0,10 %) y aparece "×2".
  - **El video se duerme:** en "Se apaga" los párpados tapan la pantalla entera unos 0,7 s, con los subtítulos encima
    y sin efectos de sonido, y reabre con un sacudón. Vuelve a parpadear en "conduces" y dos veces en "más veces te
    pasa" (nunca más de 3 parpadeos por segundo).
  - **Cambio visual cada 1,5 a 3 s.** Las escenas largas (laboratorio, ojos, barra, volantes y autopista) tienen
    hechos adentro cada 0,3 a 1 s, y la cámara se acerca despacio.
  - **Intensidad que sube (C7):** laboratorio → alcoholímetro en rojo → oscuridad → batería vacía → palillos que se
    rompen → apagón → ojos abiertos con el cerebro "SIN SEÑAL" → la ruta de noche → 3 de cada 4 → la autopista con la
    cancha al lado → viñeta roja que late.
  - **Sonido sincronizado:** tic del contador, trago, alarma del alcoholímetro, crujido de los palillos, silencio
    durante el apagón, nieve de TV, clic por cada hueco de la barra, "plop" por cada volante que se duerme, y un
    traqueteo grave cuando el auto se va de carril.
- **Personajes (V1 y V2):** Vos sale solo en la apertura y en el último 0,9 s (cierre del loop). El resto lo cuentan
  objetos con cara: el cerebro (el de `pantalla.py`), los volantes y el cronómetro.
- **Guion:** el del documento de la tanda, sin cambios. El reconocedor escribió "Rinde es igual" y "Rinde como"; el
  subtítulo usa el guion ("Rindes igual", "Rindes como"). Conviene escuchar si la voz dice "Rindes".
- **Fuentes:** CDC/NIOSH (17 h despierto ≈ 0,05 % de alcohol en sangre; 24 h ≈ 0,10 %). Ergonomics, 2021
  (doi 10.1080/00140139.2021.1882707): 144 hombres en una pista de manejo supervisada tras 27 h sin dormir; más del
  74 % tuvo microsueños. Velocidad de autopista 110 a 130 km/h: en 3 o 4 s se recorren más de 100 m.
- **Exactitud (V4):** la cancha es de 105 × 68 m con las áreas, el círculo central y los arcos reglamentarios, y está al
  lado de la ruta a la misma escala (3 carriles de 3,5 m). El auto mide 4,5 × 1,85 m y el volante de adentro, unos
  38 cm; la cara del volante se ve en una lupa. El auto va con el volante a la izquierda (México y Argentina).
  El alcoholímetro no pone número en el límite (cambia según el país: 0, 0,05 % u 0,08 %); el 0,10 % queda por encima
  de todos.
- **Loop:** "Para llegar a eso, no hace falta mucho:" (con un reloj de 1 día que se llena) → "Un día entero sin
  dormir te deja como borracho." El cuadro de TOTAL es igual al de 0 (diferencia máxima de 1 en 255 fuera de los
  subtítulos). `COLA = 0.3`.
- **Segundos clave:** sin pregunta planteada (tema explicado). Primer dato fuerte: 5,8 s ("Tras 17 horas despierto,
  ya reaccionas más lento").
- **Salida:** `salidas/un_dia_sin_dormir.mp4`, 57,6 s, 1080x1920, 30 fps, −14,2 LUFS.
