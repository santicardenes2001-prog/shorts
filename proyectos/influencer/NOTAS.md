# ¿Puedo ser influencer? (8/11/2026)

Primer Short hecho con el cuestionario y las reglas medidas el 7/11 (ver `caidas-de-retencion-2026-11-07.md`
en el proyecto de Claude).

- Voz: ElevenLabs (Agustín, Warm Expressive). `procesar_voz.py --sin-eq --pausa 0.25` (70,5 s -> 63,5 s).
- El reconocedor escribió "deslican" (0:34) y "extiría" (0:57): avisado al usuario para que escuche si
  ElevenLabs pronunció bien "deslizan" y "existiría". Los subtítulos siguen el guion.
- Cola de 0,25 s: el pedido fue que no quede espacio al final para que el loop arranque enseguida.
- Sin pregunta de cierre ni animación de suscripción (los pedidos finales costaron 13-41 puntos).
- Los ejemplos se presentan por su tema ("animales del fondo del mar…", "por qué la Tierra tiene tanta agua")
  para que se entiendan sin conocer el canal y den ganas de verlos. No se usa el Short de pelotitas.
- Datos en pantalla con fuente: YouTube 2025 (200.000 millones de vistas de Shorts por día), DataReportal 2026
  (2 h 21 min por día en redes), Morning Consult 2023 (57% de la Generación Z en EE. UU.), Studio 7/11 para
  los números del canal (~1.200 vistas en 3 h, 99% de horas de no suscritos, océano 56,3%/1.611, agua
  83,1%/6.131, más de 35.000 vistas en total).
- Render: `python proyectos/influencer/influencer.py` -> `salidas/puedo_ser_influencer.mp4`.
