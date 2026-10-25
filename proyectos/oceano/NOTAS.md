# 3 animales del océano profundo

- Guion adaptado del borrador del usuario (2026-10-25):
  - Formato de la serie: "N. Nombre (apodo):"; los apodos salen de los títulos del borrador.
  - Cangrejo yeti: "a más de 2000 m" y "completamente ciego" son de Kiwa hirsuta (2200 m, ojos atrofiados),
    pero el "baile" está documentado en Kiwa puravida (~1000 m) → "a más de 1000 metros" y "casi ciego".
    "Fertiliza" → "alimenta": al mover las pinzas les lleva oxígeno y gases a las bacterias.
  - Calamar vampiro: sus "púas" son cirros blandos → "que parecen llenos de púas"; el moco brillante
    confunde (no está documentado que deje ciego) → "para confundir a su enemigo y escapar".
  - Rape abisal: el macho conserva los testículos → "casi todos sus órganos".
  - Cierre agregado: "¿Cuál de los tres te parece más extraterrestre?" (cierra el gancho).
- Ideas de producción: fondo abisal oscuro con nieve marina (partículas), luz solo de los animales
  (bioluminiscencia con halos), chimeneas hidrotermales con burbujas de gas para el cangrejo; Vos con
  traje de buzo / batiscafo; el macho del rape pegándose y "fundiéndose" de a poco.

- Producción (2026-10-25):
  - Ambiente "abismo" en `motor.py` (sonar lejano, burbujas, llamado grave; eventos sueltos con ducking).
  - Vos en batiscafo con haz de luz (`rayo_luz` orientado al objetivo) a la izquierda, debajo de la banda
    de carteles; se apaga con "oscuridad total" y se desvanece durante el zoom al brazo del cangrejo.
  - Transición `cortina_burbujas` entre animales; zooms al brazo con bacterias (1,8) y a la fusión del
    macho (2,0) con carteles en coordenadas de escena.
  - Primera vista de hojas: batiscafo arriba a la izquierda pisaba los carteles, animales del gancho y del
    cierre chicos, platillo casi invisible → corregido antes de entregar.
  - "pelos" no lo reconoció el ASR (tiempo interpolado); revisado a ojo, el cartel cae bien.
