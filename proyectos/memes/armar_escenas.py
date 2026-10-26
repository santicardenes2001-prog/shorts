"""Genera escenas.json (python3 armar_escenas.py [--sin-audio]). Editá acá y volvé a correrlo."""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", ".."))
from comun import armar_doc, cartel, cortina, encabezado, suscripcion  # noqa: E402

narracion = [
    "¡Te muestro 3 personas que ahora son memes…",
    "y la historia detrás de cada meme no es ningún chiste!",
    "Charlie Kirk (el de la cara chiquita):",
    "Era un activista político de Estados Unidos famoso por armar mesas de debate en universidades y desafiar a "
    "cualquier estudiante a discutir con él.",
    "Internet empezó a editar sus fotos con la cara diminuta, y el chiste se volvió un clásico.",
    "En 2025 fue asesinado durante uno de esos debates, y desde entonces sus videos están en todos lados.",
    "P. Diddy (el del aceite para bebés):",
    "Fue uno de los productores de rap más poderosos del mundo, famoso por sus fiestas llenas de celebridades.",
    "En 2024 allanaron sus mansiones y, según la fiscalía, encontraron más de 1000 botellas de aceite para bebés: "
    "los memes explotaron.",
    "En 2025 lo condenaron a más de cuatro años de prisión.",
    "Jeffrey Epstein (el que \"no se suicidó\"):",
    "Era un millonario con amigos famosos y poderosos, acusado de tráfico sexual de menores.",
    "En 2019 apareció muerto en su celda antes del juicio; la versión oficial dijo suicidio, pero las cámaras "
    "fallaron y los guardias se quedaron dormidos.",
    "Así nació el meme \"Epstein no se suicidó\", que hoy aparece en cualquier conversación.",
    "¿Cuál de estos memes conocías? Contanos en los comentarios.",
]

ESTILOS = {
    "titulo_meme": {"size": 96, "color": "#FFFFFF", "stroke": 14, "stroke_color": "#1B1035"},
    "banner": {"size": 62, "color": "#C8312F", "stroke": 0},
    "meme": {"size": 92, "color": "#FFFFFF", "stroke": 16, "stroke_color": "#000000"},
    "chat": {"size": 54, "color": "#24201F", "box": "#FFFFFF", "radius": 30, "pad": [30, 18], "sombra": 6, "box_stroke": 4},
    "chat_verde": {"size": 54, "color": "#24201F", "box": "#C9F7B4", "radius": 30, "pad": [30, 18], "sombra": 6,
                   "box_stroke": 4},
    "risa": {"size": 70, "color": "#FFD23F", "stroke": 10},
    "taza": {"size": 30, "color": "#24201F", "stroke": 0},
    "remera": {"size": 34, "color": "#FFFFFF", "stroke": 0},
}

BUSTO = dict(y=1330)          # los bustos (cara de foto + cuerpo dibujado) se apoyan en y=1330
VOS_S = .42


def sale(e, fx="pop"):
    e["fx_out"] = fx
    return e


def vineta(op=.6, **kw):
    e = {"a": "capa_vineta", "alpha": op, "z": 14}
    e.update(kw)
    return e


def camara_lenta(z0, z1, extra=None, x=540, y=960):
    return {"keys": [{"at": "esc", "dur": .001, "zoom": z0, "x": x, "y": y},
                     {"at": "esc+0.01", "hasta": "esc>", "zoom": z1, "ease": "linear"}] + (extra or [])}


def emojis(at, puntos, out, semilla=0, desde=0.0):
    """Reacciones (😂 💀 ❤) que saltan una por una con un aviso de celular."""
    import random
    rnd = random.Random(semilla)
    els = []
    for i, (x, y, s) in enumerate(puntos):
        a = ["emoji_risa", "emoji_risa", "calavera_emoji", "corazon"][rnd.randrange(4)] if i else "emoji_risa"
        els.append({"a": a, "x": x, "y": y, "s": s * (.6 if a == "corazon" else 1), "r": rnd.uniform(-14, 14),
                    "in": f"{at}+{desde + i * .09:.2f}", "fx_in": "pop", "sfx": "notificacion" if i % 2 == 0 else "none",
                    "vol": .5, "idle": "float", "fase": rnd.uniform(0, 6), "out": out, "fx_out": "pop", "z": 8})
    return els


def risa_jaja(at, x, y, hasta, desde=0.0):
    """'JA JA JA' saltando alrededor de alguien que se ríe."""
    return [{"texto": {"t": "JA", "estilo": "risa", "size": 66 - i * 6}, "x": x + dx, "y": y + dy, "r": r,
             "in": f"{at}{desde + i * .22:+.2f}", "fx_in": "pop", "sfx": "none", "idle": "wiggle", "out": hasta, "fx_out": "pop",
             "z": 22}
            for i, (dx, dy, r) in enumerate([(-70, 30, -12), (50, -90, 8), (170, 10, -6)])]


escenas = []

# ------------------------------------------------------------ 0. gancho: los tres convertidos en memes
escenas.append({
    "nombre": "gancho", "beats": [0, 1], "fondo": "fondo_internet", "ambiente": "internet",
    "camara": camara_lenta(1.0, 1.06, x=540, y=1050),
    "sonidos": [{"at": "b1:chiste", "s": "golpe", "vol": .7}],
    "elementos": [
        vineta(.35, keys=[{"at": "b1:historia", "dur": 1.2, "alpha": .95}]),
        {"texto": {"t": "3 PERSONAS QUE\nAHORA SON MEMES", "estilo": "titulo_meme"}, "x": 540, "y": 330, "in": "b0:3",
         "fx_in": "pop", "idle": "breathe", "out": "b1:historia", "fx_out": "suave", "z": 45},
        # caras borrosas: todavía no se sabe quiénes son (se revelan cuando se nombra a cada uno)
        *[x for i, (a, bx, bs) in enumerate([("kirk_borroso_traje", 195, .68), ("diddy_borroso_blanco", 540, .72),
                                              ("epstein_borroso_sueter", 885, .68)]) for x in (
            {"a": a, "id": f"b{i}", "x": bx, **BUSTO, "s": bs, "in": f"b0:personas+{i * .12:.2f}", "fx_in": "pop",
             "idle": "float", "fase": i * 2},
            {"texto": {"t": "?", "estilo": "pregunta", "size": 130}, "x": bx - (0, 0, 40)[i], "y": 1050, "r": (-10, 6, 12)[i],
             "in": f"b0:personas+{.35 + i * .12:.2f}", "fx_in": "pop", "sfx": "none", "idle": "wiggle", "fase": i,
             "out": "esc>-0.35", "fx_out": "pop", "sigue": {"id": f"b{i}"}, "z": 9})],
        *emojis("b0:memes", [(150, 760, .62), (930, 740, .58), (540, 640, .68), (330, 600, .5), (760, 580, .52),
                             (100, 1000, .46), (985, 980, .44)], "b1:no", semilla=3),
        cartel("NO ES NINGÚN CHISTE", 540, 470, "b1:no", size=70, estilo="cartel_negro"),
    ]})

# ------------------------------------------------------------ 1. Charlie Kirk: la cara chiquita
escenas.append({
    "nombre": "kirk_intro", "beats": [2], "fondo": "fondo_internet", "ambiente": "internet",
    "camara": camara_lenta(1.0, 1.04, x=540, y=1050),
    "elementos": [
        vineta(.35),
        sale({"a": "kirk_traje", "x": 540, **BUSTO, "s": .9, "in": "b2:charlie", "fx_in": "pop", "idle": "float", "fase": 0,
              "swaps": [{"at": "b2:cara", "a": "kirk_chica_traje", "fx": "punch"}]}, "fade"),
        cartel("(EL DE LA CARA CHIQUITA)", 540, 470, "b2:el", size=62),
        *emojis("b2:cara", [(860, 800, .5), (210, 860, .46)], "esc>-0.3", semilla=5, desde=.25),
    ]})

# ------------------------------------------------------------ 2. mesas de debate en universidades
MESA_Y = 1335
escenas.append({
    "nombre": "kirk_debate", "beats": [3], "fondo": "fondo_campus", "ambiente": "bosque",
    "camara": camara_lenta(1.0, 1.05, x=540, y=1100),
    "elementos": [
        cartel("ACTIVISTA POLÍTICO", 540, 470, "b3:activista", size=72, estilo="cartel_celeste", out="b3:mesas"),
        {"a": "carpa", "x": 540, "y": MESA_Y - 60, "s": 1.15, "in": "b3:mesas", "fx_in": "drop", "sfx": "none", "z": -3},
        {"a": "kirk_habla_traje", "x": 540, "y": MESA_Y - 175, "s": .9, "in": "b3:mesas+0.15", "fx_in": "pop",
         "idle": "float", "fase": 0, "z": -1},
        {"a": "mesa_debate", "x": 540, "y": MESA_Y, "s": 1.2, "in": "b3:mesas", "fx_in": "jump", "z": 1},
        {"texto": {"t": "PROVE ME WRONG", "estilo": "banner", "size": 64}, "x": 540, "y": MESA_Y - 118, "in": "b3:debate",
         "fx_in": "pop", "z": 2},
        {"a": "microfono", "x": 250, "y": MESA_Y - 250, "s": .6, "r": -8, "in": "b3:debate", "fx_in": "pop", "sfx": "none",
         "z": 2},
        cartel("DEBATES EN UNIVERSIDADES", 540, 470, "b3:debate", size=60, out="b3:desafiar"),
        {"a": "estudiante_b", "x": 150, "y": MESA_Y + 10, "s": VOS_S, "in": "b3:estudiante", "fx_in": "jump", "idle": "breathe",
         "z": 3},
        {"a": "vos_celu_contento", "x": 940, "y": MESA_Y + 10, "s": VOS_S, "in": "b3:cualquier", "fx_in": "jump",
         "idle": "breathe", "blink": True, "z": 3},
        cartel("«DEMOSTRÁ QUE ME EQUIVOCO»", 540, 470, "b3:desafiar", size=54, estilo="cartel_amarillo"),
    ]})

# ------------------------------------------------------------ 3. internet le achica la cara (y él se ríe)
TEL = dict(x=370, y=900, s=.8)     # celular grande: pantalla de (190, 551) a (550, 1249)
escenas.append({
    "nombre": "kirk_meme", "beats": [4], "fondo": "fondo_internet", "ambiente": "internet",
    "camara": camara_lenta(1.0, 1.04, x=540, y=1000),
    "sonidos": [{"at": "b4:editar", "s": "obturador"}],
    "elementos": [
        vineta(.35),
        {"a": "pantalla_feed", "x": 370, "y": 900, "s": .98, "z": 2, "sfx": "none"},
        {"a": "kirk_traje", "x": 370, "y": 1176, "s": .62, "in": "b4:fotos-0.3", "fx_in": "pop", "z": 3,
         "swaps": [{"at": "b4:diminuta", "a": "kirk_chica_traje", "fx": "punch"}]},
        {"a": "celular_marco", **TEL, "in": "esc", "fx_in": "slide_up", "sfx": "whoosh", "z": 5},
        cartel("EDITAN SUS FOTOS", 540, 470, "b4:editar", size=70, out="b4:chiste"),
        {"particulas": {"a": ["emoji_risa", "corazon", "calavera_emoji"], "n": 12, "semilla": 4,
                        "zona": [478, 640, 530, 1150], "vx": [0, 0], "vy": [-140, -110], "s": [.18, .26],
                        "ondula": [18, .5], "desvanece": True},
         "in": "b4:chiste", "fx_in": "fade", "z": 6},
        sale({"a": "kirk_traje", "x": 830, **BUSTO, "s": .68, "in": "b4:diminuta+0.25", "fx_in": "slide_left", "fase": 1,
              "idle": ["float", {"fx": "shake", "fuerza": .35, "from": "b4:chiste-0.2"},
                       {"fx": "chew", "fuerza": 3, "from": "b4:chiste-0.2"}], "z": 7}, "fade"),
        *risa_jaja("b4:chiste", 740, 800, "esc>-0.3", desde=-.1),
        cartel("¡UN CLÁSICO!", 540, 470, "b4:clásico", size=76, estilo="cartel_amarillo"),
    ]})

# ------------------------------------------------------------ 4. 2025: el homenaje y sus videos en todos lados
VIDEOS = [(240, 690, -5), (830, 650, 6), (540, 880, -2), (210, 1060, 4), (860, 1040, -6), (540, 1230, 3),
          (250, 1340, -3), (830, 1330, 5)]
escenas.append({
    "nombre": "kirk_homenaje", "beats": [5], "fondo": "fondo_campus", "ambiente": "bosque",
    "camara": camara_lenta(1.04, 1.0, x=540, y=1100),
    "elementos": [
        {"a": "fondo_campus_noche", "alpha": 0, "z": -10, "sfx": "none",
         "keys": [{"at": "b5:asesinado", "dur": 1.4, "alpha": 1, "ease": "inout"}]},
        vineta(.2, keys=[{"at": "b5:asesinado", "dur": 1.4, "alpha": .9}]),
        cartel("2025", 540, 470, "b5:2025", size=110, estilo="cartel_negro", out="b5:asesinado"),
        {"a": "carpa", "x": 540, "y": MESA_Y - 60, "s": 1.15, "z": -3},
        {"a": "mesa_sin_cartel", "x": 540, "y": MESA_Y, "s": 1.2, "z": 1},
        {"a": "retrato_kirk", "x": 540, "y": MESA_Y - 420, "s": .72, "in": "b5:asesinado", "fx_in": "fade", "dur_in": 1.0,
         "z": 2, "sfx": "none"},
        *[x for i, vx in enumerate((360, 440, 640, 720)) for x in (
            {"a": "vela", "id": f"vela{i}", "x": vx, "y": MESA_Y - 245 + (i % 2) * 6, "s": .55, "in": "b5:durante",
             "fx_in": "fade", "z": 3, "sfx": "none"},
            {"a": "halo_amarillo", "s": .25, "alpha": .7, "in": "b5:durante", "fx_in": "fade", "z": 2, "sfx": "none",
             "idle": {"fx": "latido", "vel": 2.4, "fuerza": .5}, "fase": i, "sigue": {"id": f"vela{i}", "punto": [45, 40]}},
            {"a": "llama_vela", "s": .5, "in": "b5:durante", "fx_in": "fade", "z": 4, "sfx": "none", "fase": i * 1.3,
             "idle": {"fx": "wiggle", "fuerza": .5}, "sigue": {"id": f"vela{i}", "punto": [45, 52]}})],
        {"a": "flores", "x": 540, "y": MESA_Y - 236, "s": .62, "in": "b5:debates", "fx_in": "fade", "z": 4, "sfx": "none"},
        cartel("FUE ASESINADO", 540, 470, "b5:asesinado", size=78, estilo="cartel_negro", out="b5:videos"),
        {"a": "vos_celu_triste", "x": 940, "y": MESA_Y + 10, "s": VOS_S, "in": "b5:debates", "fx_in": "fade", "z": 5,
         "blink": True, "idle": "breathe"},
        *[{"a": "video_kirk", "x": x, "y": y, "s": .64, "r": r, "in": f"b5:videos+{i * .2:.2f}", "fx_in": "pop",
           "sfx": "notificacion" if i % 2 == 0 else "none", "vol": .5, "z": 10, "idle": "float", "fase": i}
          for i, (x, y, r) in enumerate(VIDEOS)],
        cartel("EN TODOS LADOS", 540, 470, "b5:todos", size=78, estilo="cartel_amarillo"),
    ]})

# ------------------------------------------------------------ 5. P. Diddy: el productor, las fiestas y el allanamiento
BOTELLAS = [(700, 1338), (760, 1342), (820, 1338), (880, 1342), (940, 1338), (1000, 1340), (730, 1250), (790, 1254),
            (850, 1250), (910, 1254), (970, 1250), (760, 1162), (820, 1166), (880, 1162), (940, 1166), (790, 1074),
            (850, 1078), (910, 1074)]
escenas.append({
    "nombre": "diddy", "beats": [6, 7, 8], "fondo": "fondo_mansion", "ambiente": "fiesta",
    "camara": {"keys": [{"at": "esc", "dur": .001, "zoom": 1.0}, {"at": "esc+0.01", "hasta": "b8:allanaron", "zoom": 1.05,
                                                                       "ease": "linear"},
                        {"at": "b8:allanaron", "dur": .6, "zoom": 1.0}],
               "temblor": [{"from": "b8:allanaron", "to": "b8:allanaron+0.5", "fuerza": .6}]},
    "sonidos": [{"at": "b8:allanaron", "s": "sirena", "vol": .45, "destacado": True}, {"at": "b8:1000", "s": "glup", "vol": .6}],
    "elementos": [
        vineta(.4),
        # luces de fiesta que barren, y después las de la policía
        {"a": "rayo_luz", "x": 40, "y": 320, "r": 62, "s": 2.4, "alpha": .45, "z": -6, "in": "b7:fiestas", "fx_in": "fade",
         "sfx": "none", "idle": {"fx": "sway", "fuerza": 6}, "out": "b8:allanaron", "fx_out": "fade"},
        {"a": "rayo_luz", "x": 1040, "y": 320, "r": 118, "s": 2.4, "alpha": .45, "z": -6, "in": "b7:fiestas", "fx_in": "fade",
         "sfx": "none", "idle": {"fx": "sway", "fuerza": 6}, "fase": 2, "out": "b8:allanaron", "fx_out": "fade"},
        {"a": "capa_sirena_rojo", "alpha": 0, "z": 12, "sfx": "none",
         "loops": [{"frames": ["capa_sirena_rojo", "capa_sirena_azul"], "fps": 4, "from": "b8:allanaron", "to": "fin"}],
         "keys": [{"at": "b8:allanaron", "dur": .3, "alpha": .95}]},
        {"a": "siluetas_fiesta_0", "x": 540, "y": 1345, "s": 1.15, "z": -4, "in": "b7:fiestas", "fx_in": "jump",
         "loops": [{"frames": ["siluetas_fiesta_0", "siluetas_fiesta_1"], "fps": 2.5, "from": "b7:fiestas", "to": "fin"}],
         "keys": [{"at": "b8:allanaron", "dur": .5, "alpha": 0, "y": 1500}]},
        {"a": "bola_disco", "x": 920, "y": 296, "s": .55, "in": "b7:fiestas", "fx_in": "drop", "idle": "sway", "z": -5,
         "out": "b8:allanaron", "fx_out": "fade"},
        {"a": "disco_oro", "x": 160, "y": 760, "s": .55, "r": -4, "in": "b7:productores", "fx_in": "pop", "z": -5},
        {"a": "disco_oro", "x": 920, "y": 760, "s": .55, "r": 4, "in": "b7:productores+0.15", "fx_in": "pop", "z": -5},
        {"a": "diddy_blanco", "x": 540, **BUSTO, "s": .85, "in": "b6:diddy", "fx_in": "pop", "idle": "float", "fase": 0,
         "keys": [{"at": "b8:allanaron", "dur": .6, "x": 300, "s": .7, "ease": "inout"}]},
        cartel("(EL DEL ACEITE PARA BEBÉS)", 540, 470, "b6:el", size=60, out="b7"),
        cartel("PRODUCTOR DE RAP", 540, 470, "b7:productores", size=74, estilo="cartel_amarillo", out="b7:poderosos"),
        cartel("DE LOS MÁS PODEROSOS", 540, 470, "b7:poderosos", size=66, estilo="cartel_amarillo", out="b7:famoso"),
        cartel("FIESTAS CON CELEBRIDADES", 540, 470, "b7:fiestas", size=60, estilo="cartel_violeta", out="b8"),
        cartel("2024", 540, 470, "b8:2024", size=110, estilo="cartel_negro", out="b8:según"),
        cartel("SEGÚN LA FISCALÍA…", 540, 470, "b8:según", size=66, estilo="cartel_celeste", out="b8:1000"),
        {"a": "caja_evidencia", "x": 850, "y": 1345, "s": .85, "in": "b8:allanaron+0.4", "fx_in": "jump", "z": 2},
        *[{"a": "aceite_bebe", "x": x, "y": y, "s": .55, "r": (i * 37) % 17 - 8, "in": f"b8:1000+{i * .06:.2f}",
           "fx_in": "pop", "sfx": "pop" if i % 3 == 0 else "none", "vol": .4, "z": 3 + i * .01}
          for i, (x, y) in enumerate(BOTELLAS)],
        cartel("+1000 BOTELLAS", 540, 470, "b8:1000", size=90, estilo="cartel_rosa", out="b8:memes"),
        *emojis("b8:memes", [(160, 740, .66), (520, 650, .6), (930, 690, .66), (380, 860, .54), (700, 840, .58),
                             (110, 1010, .48), (985, 950, .46)], "esc>-0.2", semilla=7),
        cartel("¡LOS MEMES EXPLOTARON!", 540, 470, "b8:memes", size=64, estilo="cartel_amarillo"),
    ]})

# ------------------------------------------------------------ 6. 2025: preso
escenas.append({
    "nombre": "diddy_preso", "beats": [9], "fondo": "fondo_celda", "ambiente": "carcel", "flash": True,
    "transicion": "salto de tiempo (flash)",
    "camara": {"keys": [{"at": "esc", "dur": .001, "zoom": 1.06}, {"at": "esc+0.01", "hasta": "esc>", "zoom": 1.0, "ease": "linear"}],
               "temblor": [{"from": "b9:condenaron", "to": "b9:condenaron+0.45", "fuerza": 1}]},
    "sonidos": [{"at": "b9:condenaron", "s": "rejas", "vol": .45, "destacado": True}],
    "elementos": [
        {"a": "diddy_preso_caqui", "x": 540, **BUSTO, "s": .85, "idle": "breathe"},
        cartel("2025", 540, 470, "b9:2025", size=110, estilo="cartel_negro", out="b9:condenaron"),
        {"a": "capa_rejas", "x": 540, "y": -1000, "z": 10, "in": "b9:condenaron-0.3", "sfx": "none",
         "keys": [{"at": "b9:condenaron-0.3", "dur": .3, "y": 960, "ease": "in"}]},
        cartel("+4 AÑOS DE PRISIÓN", 540, 470, "b9:cuatro", size=76, estilo="cartel_rojo"),
    ]})

# ------------------------------------------------------------ 7. Jeffrey Epstein: millonario y amigos poderosos
FAJOS = [(170, 800, -12), (920, 780, 10), (150, 1130, 8), (940, 1120, -9)]
escenas.append({
    "nombre": "epstein_isla", "beats": [10, 11], "fondo": "fondo_isla", "ambiente": "internet",
    "camara": camara_lenta(1.0, 1.05, x=540, y=1050),
    "sonidos": [{"at": "b11:millonario+0.3", "s": "zoom", "vol": .6}, {"at": "b11:acusado", "s": "golpe", "vol": .7}],
    "elementos": [
        vineta(.3, keys=[{"at": "b11:acusado", "dur": .8, "alpha": .95}]),
        {"a": "avion", "x": -350, "y": 640, "s": .7, "r": -6, "in": "b11:millonario+0.3", "sfx": "none", "z": -2,
         "keys": [{"at": "b11:millonario+0.3", "dur": 2.4, "x": 1450, "y": 560, "ease": "linear"}]},
        {"a": "epstein_sueter", "x": 540, **BUSTO, "s": .85, "in": "b10:jeffrey", "fx_in": "pop", "idle": "float", "fase": 0},
        cartel("(EL QUE «NO SE SUICIDÓ»)", 540, 470, "b10:el", size=60, out="b11"),
        *[{"a": "fajo", "x": x, "y": y, "s": .55, "r": r, "in": f"b11:millonario+{i * .1:.2f}", "fx_in": "pop", "idle": "float",
           "fase": i, "out": "b11:amigos", "fx_out": "pop", "z": 3} for i, (x, y, r) in enumerate(FAJOS)],
        cartel("MILLONARIO", 540, 470, "b11:millonario", size=84, estilo="cartel_verde", out="b11:amigos"),
        *[x for i, (vx, k) in enumerate([(180, 0), (880, 1)]) for x in (
            {"a": f"silueta_vip_{k}", "x": vx, "y": 1345, "s": .7, "in": f"b11:amigos+{i * .15:.2f}", "fx_in": "jump", "z": -1,
             "keys": [{"at": "b11:acusado", "dur": .7, "x": vx + (-300 if vx < 540 else 300), "ease": "in"}]},
            {"texto": {"t": "?", "estilo": "pregunta", "size": 80}, "x": vx, "y": 1345 - 300, "in": f"b11:amigos+{.2 + i * .15:.2f}",
             "fx_in": "pop", "sfx": "none", "idle": "wiggle", "out": "b11:acusado", "fx_out": "pop", "z": 4})],
        cartel("AMIGOS FAMOSOS Y PODEROSOS", 540, 470, "b11:amigos", size=56, estilo="cartel_celeste", out="b11:acusado"),
        {"a": "esposas", "x": 860, "y": 860, "s": .7, "r": 12, "in": "b11:acusado", "fx_in": "pop", "sfx": "none", "z": 5,
         "idle": "float"},
        cartel("ACUSADO DE TRÁFICO\nSEXUAL DE MENORES", 540, 480, "b11:acusado", size=54, estilo="cartel_rojo"),
    ]})

# ------------------------------------------------------------ 8. 2019: la celda, la versión oficial, cámaras y guardias
escenas.append({
    "nombre": "epstein_celda", "beats": [12], "fondo": "fondo_celda", "ambiente": "carcel", "flash": True,
    "transicion": "salto de tiempo (flash)",
    "camara": camara_lenta(1.05, 1.0, x=540, y=1000),
    "sonidos": [{"at": "b12:cámaras", "s": "estatica", "vol": .7}, {"at": "b12:fallaron", "s": "estatica", "vol": .5},
                {"at": "b12:dormidos", "s": "ronquido", "vol": .9}],
    "elementos": [
        {"a": "epstein_preso_naranja", "x": 540, **BUSTO, "s": .8, "idle": "breathe",
         "keys": [{"at": "b12:muerto", "dur": 1.0, "alpha": 0}], "out": "b12:versión"},
        {"a": "capa_negra", "alpha": 0, "z": 8, "sfx": "none",
         "keys": [{"at": "b12:muerto", "dur": .8, "alpha": .78}, {"at": "b12:versión", "dur": .8, "alpha": .35}]},
        cartel("2019", 540, 470, "b12:2019", size=110, estilo="cartel_negro", out="b12:muerto"),
        cartel("APARECIÓ MUERTO", 540, 470, "b12:muerto", size=76, estilo="cartel_negro", out="b12:juicio"),
        cartel("ANTES DEL JUICIO", 540, 470, "b12:juicio", size=76, estilo="cartel_negro", out="b12:versión"),
        cartel("VERSIÓN OFICIAL:\nSUICIDIO", 540, 480, "b12:versión", size=66, out="b12:cámaras"),
        {"a": "camara_seguridad", "x": 220, "y": 720, "s": .8, "in": "b12:cámaras", "fx_in": "pop", "z": 9,
         "swaps": [{"at": "b12:fallaron", "a": "camara_seguridad_rota", "fx": "punch", "sfx": "none"}]},
        {"a": "monitor_estatica_0", "x": 830, "y": 760, "s": .8, "in": "b12:cámaras+0.15", "fx_in": "pop", "z": 9, "sfx": "none",
         "loop": {"frames": ["monitor_estatica_0", "monitor_estatica_1", "monitor_estatica_2"], "fps": 12}},
        cartel("LAS CÁMARAS FALLARON", 540, 470, "b12:fallaron", size=66, estilo="cartel_rojo", out="b12:guardias"),
        {"a": "guardia_dormido", "x": 580, "y": 1345, "s": .95, "in": "b12:guardias", "fx_in": "jump", "z": 9,
         "idle": {"fx": "breathe", "fuerza": 2.5}},
        {"a": "zzz", "x": 720, "y": 930, "s": .5, "in": "b12:dormidos", "fx_in": "pop", "sfx": "none", "idle": "float",
         "z": 10},
        cartel("GUARDIAS DORMIDOS", 540, 470, "b12:dormidos", size=72, estilo="cartel_amarillo"),
        {"a": "vos_celu_pensando", "x": 140, "y": 1345, "s": VOS_S, "in": "b12:pero", "fx_in": "jump", "blink": True,
         "idle": "breathe", "z": 11},
    ]})

# ------------------------------------------------------------ 9. el meme: "Epstein no se suicidó" en todas partes
CHAT = [("¿Viste el partido?", "chat", 320, 650), ("Sí, increíble", "chat_verde", 760, 770),
        ("¿Y qué comemos hoy?", "chat", 340, 890), ("Epstein no se suicidó", "chat_verde", 660, 1010)]
escenas.append({
    "nombre": "epstein_meme", "beats": [13], "fondo": "fondo_internet", "ambiente": "internet",
    "camara": camara_lenta(1.0, 1.04, x=540, y=1000),
    "elementos": [
        vineta(.35),
        # el meme: la foto con el texto arriba y abajo
        sale({"a": "epstein_sueter", "x": 540, "y": 1300, "s": .8, "in": "b13:meme", "fx_in": "pop", "idle": "float",
              "out": "b13:aparece"}, "pop"),
        sale({"texto": {"t": "EPSTEIN", "estilo": "meme"}, "x": 540, "y": 700, "in": "b13:meme+0.2", "fx_in": "pop",
              "out": "b13:aparece", "z": 6}, "pop"),
        sale({"texto": {"t": "NO SE SUICIDÓ", "estilo": "meme", "size": 84}, "x": 540, "y": 1160, "in": "b13:epstein",
              "fx_in": "pop", "out": "b13:aparece", "z": 6}, "pop"),
        # en cualquier conversación: el chat
        *[{"texto": {"t": t, "estilo": est}, "x": x, "y": y, "in": f"b13:aparece+{i * .35:.2f}", "fx_in": "pop",
           "sfx": "notificacion", "vol": .5, "z": 6} for i, (t, est, x, y) in enumerate(CHAT)],
        {"a": "taza", "x": 250, "y": 1345, "s": .9, "in": "b13:cualquier", "fx_in": "jump", "z": 6},
        {"texto": {"t": "EPSTEIN\nNO SE\nSUICIDÓ", "estilo": "taza"}, "x": 238, "y": 1222, "in": "b13:cualquier",
         "fx_in": "jump", "sfx": "none", "z": 7},
        {"a": "remera", "x": 800, "y": 1210, "s": .62, "r": 6, "in": "b13:cualquier+0.15", "fx_in": "jump", "z": 6},
        {"texto": {"t": "EPSTEIN\nNO SE\nSUICIDÓ", "estilo": "remera"}, "x": 802, "y": 1240, "r": 6,
         "in": "b13:cualquier+0.15", "fx_in": "jump", "sfx": "none", "z": 7},
    ]})

# ------------------------------------------------------------ 10. cierre: pregunta, comentarios y suscripción
FIN = "b14>"
cierre_el, cierre_son = suscripcion(FIN)
escenas.append({
    "nombre": "cierre", "beats": [14], "fondo": "fondo_internet", "ambiente": {"tipo": "internet", "vol": .6},
    "sonidos": [{"at": "b14:contanos", "s": "pop"}] + cierre_son,
    "elementos": [
        vineta(.3),
        cartel("¿CUÁL CONOCÍAS?", 540, 470, "b14:cuál", size=80, estilo="cartel_amarillo", out=FIN),
        {"a": "kirk_traje", "x": 195, "y": 990, "s": .6, "in": "b14:cuál", "fx_in": "pop", "idle": "float", "fase": 0},
        {"a": "diddy_blanco", "x": 540, "y": 990, "s": .62, "in": "b14:cuál+0.12", "fx_in": "pop", "idle": "float", "fase": 2},
        {"a": "epstein_sueter", "x": 885, "y": 990, "s": .6, "in": "b14:cuál+0.24", "fx_in": "pop", "idle": "float", "fase": 4},
        {"a": "vos_celu_pensando", "x": 540, "y": 1345, "s": .44, "in": "b14", "fx_in": "slide_up", "blink": True,
         "idle": "breathe", "swaps": [{"at": f"{FIN}+1.2", "a": "vos_celu_risa", "fx": "punch"}]},
        {"texto": {"t": "?", "estilo": "pregunta"}, "x": 760, "y": 1150, "r": 12, "in": "b14:conocías", "fx_in": "pop",
         "idle": "wiggle", "out": "b14:contanos", "fx_out": "pop"},
        {"a": "globo_comentario_1", "x": 790, "y": 1180, "s": .55, "in": "b14:contanos", "fx_in": "pop", "sfx": "none", "z": 8,
         "loops": [{"frames": ["globo_comentario_1", "globo_comentario_2", "globo_comentario_3"], "fps": 4,
                    "from": "b14:contanos", "to": "fin"}], "idle": "bob"},
    ] + cierre_el})

armar_doc(
    AQUI, narracion, escenas,
    persistentes=(encabezado(1, "Charlie Kirk", "b2", "e5")
                  + encabezado(2, "P. Diddy", "b6", "e7")
                  + encabezado(3, "Jeffrey Epstein", "b10", "e10")
                  + [cortina(f"e{i}", asset="cortina_feed", sfx="whoosh") for i in (1, 2, 3, 4, 5, 7, 9, 10)]),
    estilos=ESTILOS, audio="--sin-audio" not in sys.argv,
    cola=3.4, volumen_ambiente=.3)
