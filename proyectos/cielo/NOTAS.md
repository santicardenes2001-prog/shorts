# ¿Por qué el cielo de noche es negro? — notas

Short 1 de la tanda del 10/11/2026. Animación procedural (`cielo.py`), mismo armazón que `influencer.py`.

- **Guion:** misterio que se resuelve al final. La pista la da Edgar Allan Poe («Eureka», 1848): la luz tarda en
  viajar, así que el universo tuvo que nacer. Fuentes: BBC Sky at Night, Penn State (Astro 801), Edge, Astronomy.
- **Loop:** la última frase ("Durante siglos faltó esa sola idea:") empalma con la primera ("La oscuridad de la noche
  no tenía explicación."). El último cuadro es igual al primero: el "?" de estrellas se vuelve a formar y Vos sube
  desde atrás de la loma. `COLA = 0.3`. El titilar y el fondo de puntos usan períodos que cierran justo en `TOTAL`.
- **Vos:** solo en la apertura y en el empalme del final.
- **Poe:** no se dibuja su cara. Se muestra con una hoja, una pluma, un cuervo, la luna y murciélagos, y el cartel con
  su nombre.
- **Audio:** ElevenLabs (Agustín), `procesar_voz.py --sin-eq --pausa 0.3`. 71,0 s -> 63,8 s. El reconocedor se comió
  "en" ("habría estrellas en todas las direcciones"): tiempo interpolado, la voz lo dice bien.
- **Salida:** `salidas/por_que_el_cielo_es_negro.mp4`, 64,0 s, 1080x1920, 30 fps, -14,0 LUFS.

Pendiente: correcciones del usuario sobre esta primera versión.
