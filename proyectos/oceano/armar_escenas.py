"""Genera escenas.json (python3 armar_escenas.py [--sin-audio]). Editá acá y volvé a correrlo."""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", ".."))
from comun import armar_doc, cartel, cortina, encabezado, suscripcion  # noqa: E402

narracion = [
    "¡Te muestro 3 animales del océano profundo tan extraños que parecen extraterrestres!",
    "1. El cangrejo yeti (el que cultiva su comida en los brazos):",
    "Vive en la oscuridad total, a más de 1000 metros bajo el agua, y es casi ciego.",
    "Para no morir de hambre, mueve sus largas pinzas peludas como si estuviera bailando sobre los gases tóxicos del suelo marino;",
    "así alimenta a las bacterias que crecen en sus propios pelos, para después comérselas.",
    "2. El calamar vampiro (el que dispara luz en vez de tinta):",
    "Vive a casi 1000 metros de profundidad, donde la oscuridad es total y la tinta negra no serviría de nada.",
    "Cuando un depredador lo ataca, se envuelve con sus tentáculos, que parecen llenos de púas,",
    "y lanza una nube de moco que brilla en la oscuridad para confundir a su enemigo y escapar.",
    "3. El rape abisal (el macho que se fusiona con la hembra):",
    "En el fondo del mar es tan difícil encontrar pareja que, cuando un macho diminuto encuentra a una hembra gigante, "
    "la muerde y nunca más la suelta.",
    "Con el tiempo, su piel y sus vasos sanguíneos se funden con los de ella, pierde los ojos y casi todos sus órganos, "
    "y pasa el resto de su vida pegado a ella como una parte más de su cuerpo.",
    "¿Cuál de los tres te parece más extraterrestre? Cuéntanos en los comentarios.",
]

KIWA = dict(x=540, y=1335, s=.9)       # cangrejo yeti sobre el lecho (escenas 1 y 2)
VAMP = dict(x=500, y=930, s=1.0)       # calamar vampiro (escenas 3 y 4)
RAPE = dict(x=500, y=1000, s=1.1)      # hembra de rape (escenas 5 y 6)
LAMPARA = [428, 250]                   # vidrio de la lámpara en el dibujo del batiscafo (440x420)
SENUELO = [640, 70]                    # punta del señuelo en el dibujo de la hembra de rape (700x600)
PANZA_L = [330 + 80 * .8 / 1.1, 520]   # donde queda pegado el macho (centro), en el dibujo de la hembra
BATI = dict(x=150, y=700, s=.45)       # batiscafo de Vos a la izquierda, debajo de los carteles


# ------------------------------------------------------------ ambientación reutilizable
def nieve(semilla, n=30):
    """Nieve marina: partículas que bajan despacio (siempre algo se mueve, aunque esté oscuro)."""
    return {"particulas": {"a": "nieve_marina", "n": n, "semilla": semilla, "zona": [-20, -40, 1100, 1960], "vx": [-8, 8],
                           "vy": [18, 40], "s": [.6, 1.6], "alpha": [.4, .9], "ondula": [10, .2], "continuo": True}, "z": 13}


def vineta(op=1.0, **kw):
    e = {"a": "capa_vineta", "alpha": op, "z": 14}
    e.update(kw)
    return e


def batiscafo(cara="neutral", objetivo=None, **kw):
    """Vos en el batiscafo arriba a la izquierda, con el haz de la lámpara apuntando a 'objetivo' (x, y)."""
    import math
    e = {"a": f"batiscafo_{cara}", **BATI, "id": "bati", "idle": "float", "fase": 0, "z": 5}
    e.update(kw)
    out = [e]
    if objetivo:
        lx, ly = BATI["x"] + (LAMPARA[0] - 220) * BATI["s"], BATI["y"] + (LAMPARA[1] - 210) * BATI["s"]
        ang = math.degrees(math.atan2(objetivo[1] - ly, objetivo[0] - lx))
        largo = math.hypot(objetivo[0] - lx, objetivo[1] - ly) / 700
        out.append({"a": "rayo_luz", "x": lx, "y": ly, "r": round(ang, 1), "s": round(largo, 2), "alpha": .55, "z": -1,
                    "idle": {"fx": "latido", "fuerza": .25}, "fase": 0, "sigue": {"id": "bati", "punto": LAMPARA}})
    return out


def camara_lenta(z0, z1, extra=None, x=540, y=960):
    keys = [{"at": "esc", "dur": .001, "zoom": z0, "x": x, "y": y},
            {"at": "esc+0.01", "hasta": "esc>", "zoom": z1, "ease": "linear"}]
    return {"keys": keys + (extra or [])}


def sale(e, fx="pop"):
    e["fx_out"] = fx
    return e


FUMAROLAS = [(200, 900, 420), (880, 660, 420), (560, 1000, 330)]   # boca (x, y) y altura del penacho en fondo_lecho


def humo(desde, n=3, semilla=1, alpha=(.4, .8)):
    """Gases que salen de la boca de cada fumarola: nacen ahí, suben abriéndose y se apagan (n por chimenea)."""
    return [{"particulas": {"a": "humo_toxico", "n": n, "semilla": semilla + i, "zona": [x - 22, y - alto, x + 22, y + 10],
                            "vx": [0, 0], "vy": [-95, -60], "s": [.45, .7], "alpha": list(alpha), "ondula": [18, .3],
                            "desvanece": True, "crece": 2.2, "continuo": True},
             "in": desde, "fx_in": "fade", "dur_in": 1.0, "z": -.5}
            for i, (x, y, alto) in enumerate(FUMAROLAS)]


escenas = []

# ------------------------------------------------------------ 0. gancho: bajando al abismo
escenas.append({
    "nombre": "gancho", "beats": [0], "fondo": "fondo_abismo", "ambiente": "abismo",
    "camara": camara_lenta(1.0, 1.05),
    "sonidos": [{"at": "b0:extraterrestres", "s": "zoom"}, {"at": "b0", "s": "whoosh_suave"}],
    "elementos": [
        nieve(1), vineta(.7),
        {"texto": {"t": "3 ANIMALES DEL\nOCÉANO PROFUNDO", "estilo": "titulo_azul", "size": 108}, "x": 540, "y": 330, "in": "b0:3",
         "fx_in": "pop", "fx_out": "suave", "idle": "breathe", "z": 45},
        sale({"a": "batiscafo_neutral", "x": 300, "y": -260, "s": .7, "idle": "float", "fase": 0, "blink": True,
              "keys": [{"at": "b0", "hasta": "b0:animales", "y": 760, "ease": "out"}],
              "swaps": [{"at": "b0:extraños", "a": "batiscafo_sorpresa", "fx": "punch"}]}, "fade"),
        sale({"a": "halo_celeste", "s": .7, "alpha": .5, "in": "b0:animales", "fx_in": "fade",
              "idle": "latido", "sigue": {"id": "vamp", "punto": [260, 320]}}, "fade"),
        sale({"a": "calamar_vampiro_brilla", "id": "vamp", "x": 800, "y": 800, "s": .6, "in": "b0:animales", "fx_in": "fade", "dur_in": .6,
              "idle": "float"}, "fade"),
        sale({"a": "cangrejo_yeti_quieto", "x": 270, "y": 1330, "s": .65, "in": "b0:océano", "fx_in": "fade", "dur_in": .6,
              "idle": "sway"}, "fade"),
        sale({"a": "rape_hembra", "id": "rape", "x": 760, "y": 1210, "s": .55, "in": "b0:profundo", "fx_in": "fade",
              "dur_in": .6, "idle": "float"}, "fade"),
        sale({"a": "halo_celeste", "s": .18, "alpha": .9, "in": "b0:profundo", "fx_in": "fade", "dur_in": .6, "idle": "latido",
              "sigue": {"id": "rape", "punto": SENUELO}}, "fade"),
        {"a": "platillo", "x": -250, "y": 640, "s": 1.3, "r": -8, "in": "b0:extraterrestres", "sfx": "none", "z": 6,
         "keys": [{"at": "b0:extraterrestres", "dur": 1.1, "x": 1350, "y": 540, "ease": "inout"}]},
    ]})

# ------------------------------------------------------------ 1. cangrejo yeti: oscuridad y ceguera
escenas.append({
    "nombre": "yeti_intro", "beats": [1, 2], "fondo": "fondo_lecho", "ambiente": "abismo",
    "camara": camara_lenta(1.0, 1.04),
    "sonidos": [{"at": "b2:oscuridad", "s": "click"}, {"at": "b2:más", "s": "click"}],
    "elementos": [
        nieve(2), vineta(.8, keys=[{"at": "b2:oscuridad", "dur": .3, "alpha": 1.0}, {"at": "b2:más", "dur": .3, "alpha": .8}]),
        *humo("esc", 3, 2),
        *batiscafo("neutral", (540, 1150), **{"in": "b1", "fx_in": "slide_down", "sfx": "whoosh_suave", "blink": True,
                                              "swaps": [{"at": "b2:ciego", "a": "batiscafo_pensando", "fx": "punch"}]}),
        {"a": "cangrejo_yeti_quieto", **KIWA, "in": "b1:cangrejo", "fx_in": "fade", "dur_in": .8, "idle": "sway", "fase": 0,
         "keys": [{"at": "b2:oscuridad", "dur": .3, "alpha": .15}, {"at": "b2:más", "dur": .3, "alpha": 1}]},
        cartel("(CULTIVA SU COMIDA\nEN LOS BRAZOS)", 540, 470, "b1:cultiva", size=62, out="b2"),
        cartel("OSCURIDAD TOTAL", 540, 470, "b2:oscuridad", size=72, estilo="cartel_negro", out="b2:más"),
        cartel("-1000 m", 540, 470, "b2:1000", size=96, estilo="cartel_celeste", out="b2:casi"),
        cartel("CASI CIEGO", 540, 470, "b2:ciego", size=80, estilo="cartel_amarillo"),
    ]})
for e in escenas[-1]["elementos"]:   # el haz se apaga y se prende con la oscuridad
    if e.get("a") == "rayo_luz":
        e["keys"] = [{"at": "b2:oscuridad", "dur": .1, "alpha": 0}, {"at": "b2:más", "dur": .1, "alpha": .55}]

# ------------------------------------------------------------ 2. el baile sobre los gases y las bacterias
escenas.append({
    "nombre": "yeti_baile", "beats": [3, 4], "fondo": "fondo_lecho", "ambiente": "abismo",
    "camara": camara_lenta(1.04, 1.06, [{"at": "b4:bacterias", "dur": .9, "zoom": 1.8, "x": 430, "y": 1180, "ease": "inout"}]),
    "sonidos": [{"at": "b3:gases", "s": "glup", "vol": .7}, {"at": "b4:comérselas", "s": "pop"},
                {"at": "b4:comérselas+0.3", "s": "pop", "vol": .7}],
    "elementos": [
        nieve(2), vineta(.8), *humo("esc", 3, 2), *humo("b3:gases", 4, 7, (.6, .95)),
        *batiscafo("pensando", (540, 1150)),
        {"a": "cangrejo_yeti_quieto", **KIWA, "idle": "sway", "fase": 0,
         "loops": [{"frames": ["cangrejo_yeti_baila_a", "cangrejo_yeti_baila_b"], "fps": 3, "from": "b3:mueve", "to": "b4:alimenta"}],
         "swaps": [{"at": "b4:bacterias", "a": "cangrejo_yeti_bacterias", "fx": "punch"},
                   {"at": "b4:comérselas", "a": "cangrejo_yeti_come_bacterias", "fx": "punch"}]},
        {"particulas": {"a": "nota_musical", "n": 5, "semilla": 2, "zona": [300, 700, 800, 1000], "vy": [-80, -50],
                        "s": [.4, .6], "ondula": [20, .5]}, "in": "b3:bailando", "out": "b4", "fx_in": "fade", "fx_out": "fade",
         "z": 6},
        cartel("¡BAILA!", 540, 470, "b3:bailando", size=84, estilo="cartel_amarillo", r=-4, out="b3:gases"),
        cartel("GASES TÓXICOS", 540, 470, "b3:gases", size=74, estilo="cartel_verde", out="b4:bacterias"),
        # ya con zoom 1,8 centrado en (430, 1180): (430, 908) en la escena cae en (540, 470) de la pantalla
        cartel("BACTERIAS EN SUS PELOS", 430, 908, "b4:pelos", size=40, out="b4:comérselas"),
        cartel("¡SE LAS COME!", 430, 908, "b4:comérselas", size=46, estilo="cartel_amarillo"),
    ]})

for e in escenas[-1]["elementos"]:   # con el zoom al brazo, el batiscafo agrandado taparía el encabezado
    if e.get("a") in ("batiscafo_pensando", "rayo_luz"):
        e["keys"] = [{"at": "b4:bacterias", "dur": .4, "alpha": 0}]

# ------------------------------------------------------------ 3. calamar vampiro: tinta inútil
escenas.append({
    "nombre": "vampiro_intro", "beats": [5, 6], "fondo": "fondo_abismo", "ambiente": "abismo",
    "camara": camara_lenta(1.0, 1.04),
    "elementos": [
        nieve(3), vineta(.8),
        *batiscafo("sorpresa", (VAMP["x"], VAMP["y"])),
        {"a": "calamar_vampiro", **VAMP, "in": "b5:calamar", "fx_in": "fade", "dur_in": .8, "idle": "float", "fase": 0},
        cartel("(DISPARA LUZ\nEN VEZ DE TINTA)", 540, 470, "b5:dispara", size=64, out="b6"),
        cartel("-1000 m", 540, 470, "b6:1000", size=96, estilo="cartel_celeste", out="b6:oscuridad"),
        sale({"a": "tinta", "x": 790, "y": 1180, "s": .9, "in": "b6:tinta", "fx_in": "grow", "sfx": "glup",
              "keys": [{"at": "b6:serviría", "dur": .8, "alpha": .15}]}, "fade"),
        cartel("¡NO SE VE!", 540, 470, "b6:tinta", size=80, estilo="cartel_negro"),
    ]})

# ------------------------------------------------------------ 4. ataque: púas y nube de luz
escenas.append({
    "nombre": "vampiro_ataque", "beats": [7, 8], "fondo": "fondo_abismo", "ambiente": "abismo",
    "camara": {"keys": [{"at": "esc", "dur": .001, "zoom": 1.04}, {"at": "esc+0.01", "dur": 1.0, "zoom": 1.0}],
               "temblor": [{"from": "b8:brilla", "to": "b8:brilla+0.6", "fuerza": .8}]},
    "sonidos": [{"at": "b7:depredador", "s": "zumbido", "vol": .7}, {"at": "b8:brilla", "s": "brillo"},
                {"at": "b8:escapar", "s": "whoosh"}],
    "elementos": [
        nieve(3), vineta(.8),
        *batiscafo("sorpresa", (VAMP["x"], VAMP["y"])),
        {"a": "calamar_vampiro", **VAMP, "idle": "float", "fase": 0,
         "swaps": [{"at": "b7:envuelve", "a": "calamar_vampiro_pina", "fx": "punch"},
                   {"at": "b8:confundir", "a": "calamar_vampiro_brilla", "fx": "punch"}],
         "keys": [{"at": "b8:escapar", "dur": .7, "x": 560, "y": -450, "s": .7, "ease": "in"}]},
        {"a": "pez_vibora", "x": 1500, "y": 1190, "s": 1.3, "in": "b7:depredador", "sfx": "none", "idle": "sway", "z": 2,
         "keys": [{"at": "b7:depredador", "dur": 1.0, "x": 900, "ease": "out"}],
         "swaps": [{"at": "b8:confundir", "a": "pez_vibora_mareado", "fx": "punch"}]},
        cartel("¡PARECE LLENO DE PÚAS!", 540, 470, "b7:púas", size=62, estilo="cartel_rojo", out="b8:moco"),
        # nube de moco luminoso
        sale({"a": "halo_celeste", "x": 560, "y": 980, "s": .3, "alpha": 0, "in": "b8:nube", "z": 3, "sfx": "none", "suelta": True,
              "keys": [{"at": "b8:nube", "dur": .8, "s": 1.9, "alpha": 1, "ease": "out"}], "idle": "latido"}, "fade"),
        {"particulas": {"a": "destello", "n": 34, "semilla": 6, "zona": [220, 620, 900, 1380], "vx": [-25, 25], "vy": [-25, 25],
                        "s": [.4, 1.1], "titila": .7, "ondula": [30, .4]}, "in": "b8:nube", "fx_in": "fade", "dur_in": .6,
         "fx_out": "fade", "z": 4},
        {"a": "blanco", "alpha": 0, "z": 30, "in": "b8:brilla", "out": "b8:brilla+0.6", "sfx": "none",
         "keys": [{"at": "b8:brilla", "dur": .08, "alpha": .45}, {"at": "b8:brilla+0.1", "dur": .45, "alpha": 0}]},
        cartel("MOCO QUE BRILLA", 540, 470, "b8:moco", size=72, estilo="cartel_celeste", out="b8:confundir"),
        cartel("¡CONFUNDIDO!", 540, 470, "b8:confundir", size=80, estilo="cartel_amarillo"),
    ]})
for e in escenas[-1]["elementos"]:
    if e.get("a") == "batiscafo_sorpresa":
        e["swaps"] = [{"at": "b7:depredador", "a": "batiscafo_miedo", "fx": "punch"},
                      {"at": "b8:escapar", "a": "batiscafo_contento", "fx": "punch"}]

# ------------------------------------------------------------ 5. rape: la hembra gigante y el macho diminuto
PANZA = (RAPE["x"] + (330 - 350) * RAPE["s"] + 80 * .8, RAPE["y"] + (520 - 300) * RAPE["s"])
escenas.append({
    "nombre": "rape_encuentro", "beats": [9, 10], "fondo": "fondo_abismo", "ambiente": "abismo",
    "camara": camara_lenta(1.0, 1.04),
    "sonidos": [{"at": "b9:rape", "s": "brillo", "vol": .6}, {"at": "b10:muerde", "s": "golpe", "vol": .8}],
    "elementos": [
        nieve(4), vineta(1.0),
        *batiscafo("sorpresa"),
        # en la oscuridad primero se ve solo el señuelo; después aparece la hembra
        {"a": "halo_celeste", "s": .35, "alpha": .9, "in": "b9:rape", "fx_in": "fade", "z": 4,
         "idle": "latido", "fase": 0, "sigue": {"id": "rape", "punto": SENUELO}},
        {"a": "rape_hembra", **RAPE, "id": "rape", "alpha": 0, "idle": "float", "fase": 0, "z": 2,
         "keys": [{"at": "b9:abisal", "dur": 1.2, "alpha": 1, "ease": "inout"}]},
        cartel("(EL MACHO SE FUSIONA\nCON LA HEMBRA)", 540, 470, "b9:macho", size=62, out="b10:difícil"),
        # sigue a la hembra: sus keys son desplazamientos respecto de la panza, así al morder queda pegado justo ahí
        {"a": "rape_macho_0", "x": PANZA[0], "y": PANZA[1], "s": .8, "in": "b10:difícil", "fx_in": "fade", "z": 6,
         "sigue": {"id": "rape", "punto": PANZA_L},
         "idle": {"fx": "bob", "to": "b10:muerde-0.35"},
         "keys": [{"at": "b10:difícil", "dur": .001, "x": 960, "y": 560},
                  {"at": "b10:difícil+0.01", "dur": 1.6, "x": 760, "y": 640, "ease": "inout"},
                  {"at": "b10:muerde-0.35", "dur": .35, "x": PANZA[0], "y": PANZA[1], "ease": "in"}],
         "swaps": [{"at": "b10:muerde", "a": "rape_macho_1", "fx": "punch"}]},
        {"texto": {"t": "?", "estilo": "pregunta", "size": 90}, "x": 820, "y": 560, "in": "b10:difícil+0.4", "fx_in": "pop",
         "idle": "wiggle", "out": "b10:diminuto", "fx_out": "pop", "z": 7},
        cartel("MACHO DIMINUTO", 540, 470, "b10:diminuto", size=66, estilo="cartel_celeste", out="b10:hembra"),
        cartel("HEMBRA GIGANTE", 540, 470, "b10:hembra", size=74, estilo="cartel_rojo", out="b10:muerde"),
        cartel("¡Y NUNCA MÁS LA SUELTA!", 540, 470, "b10:nunca", size=62, estilo="cartel_amarillo"),
        sale({"a": "corazon", "x": PANZA[0] + 40, "y": PANZA[1] - 120, "s": .4, "in": "b10:muerde", "fx_in": "pop", "sfx": "none",
              "idle": "bob", "z": 7}),
    ]})

# ------------------------------------------------------------ 6. la fusión
escenas.append({
    "nombre": "rape_fusion", "beats": [11], "fondo": "fondo_abismo", "ambiente": "abismo",
    "camara": {"keys": [{"at": "esc", "dur": .001, "zoom": 1.04},
                        {"at": "b11:tiempo", "dur": 1.0, "zoom": 2.0, "x": PANZA[0] - 20, "y": PANZA[1] - 20, "ease": "inout"},
                        {"at": "b11:resto", "dur": 1.0, "zoom": 1.0, "x": 540, "y": 960, "ease": "inout"}]},
    "sonidos": [{"at": "b11:funden", "s": "zumbido", "vol": .6}, {"at": "b11:ojos", "s": "pop"}, {"at": "b11:órganos", "s": "glup"}],
    "elementos": [
        nieve(4), vineta(1.0),
        *batiscafo("sorpresa", None, swaps=[{"at": "b11:ojos", "a": "batiscafo_asco", "fx": "punch"},
                                            {"at": "b11:pegado", "a": "batiscafo_sorpresa"}]),
        {"a": "halo_celeste", "s": .35, "alpha": .9, "z": 4, "idle": "latido", "fase": 0,
         "sigue": {"id": "rape", "punto": SENUELO}},
        {"a": "rape_hembra", **RAPE, "id": "rape", "idle": "float", "fase": 0, "z": 2,
         "swaps": [{"at": "b11:parte", "a": "rape_hembra_feliz", "fx": "punch"}]},
        {"a": "rape_macho_1", "x": PANZA[0], "y": PANZA[1], "s": .8, "z": 6, "sigue": {"id": "rape", "punto": PANZA_L},
         "swaps": [{"at": "b11:funden", "a": "rape_macho_2", "fx": "punch"},
                   {"at": "b11:ojos", "a": "rape_macho_3", "fx": "punch"},
                   {"at": "b11:órganos", "a": "rape_macho_4", "fx": "punch"}]},
        # carteles en coordenadas de escena equivalentes a arriba de la pantalla con zoom 2
        cartel("SE FUNDEN", PANZA[0] - 20, PANZA[1] - 265, "b11:funden", size=36, estilo="cartel_rojo", out="b11:ojos"),
        cartel("PIERDE LOS OJOS…", PANZA[0] - 20, PANZA[1] - 265, "b11:ojos", size=36, out="b11:órganos"),
        cartel("…Y SUS ÓRGANOS", PANZA[0] - 20, PANZA[1] - 265, "b11:órganos", size=36, estilo="cartel_amarillo",
               out="b11:resto"),
        cartel("PEGADO DE POR VIDA", 540, 470, "b11:pegado", size=70, estilo="cartel_rojo"),
    ]})

# ------------------------------------------------------------ 7. cierre: pregunta, comentarios y suscripción
FIN = "b12>"
cierre_el, cierre_son = suscripcion(FIN)
escenas.append({
    "nombre": "cierre", "beats": [12], "fondo": "fondo_abismo", "ambiente": {"tipo": "abismo", "vol": .7},
    "sonidos": [{"at": "b12:cuéntanos", "s": "pop"}] + cierre_son,
    "elementos": [
        nieve(5), vineta(.6),
        cartel("¿CUÁL ES MÁS\nEXTRATERRESTRE?", 540, 470, "b12:cuál", size=70, estilo="cartel_amarillo", out=FIN),
        {"a": "cangrejo_yeti_baila_a", "x": 250, "y": 1060, "s": .6, "in": "b12:cuál", "fx_in": "pop", "idle": "sway",
         "loops": [{"frames": ["cangrejo_yeti_baila_a", "cangrejo_yeti_baila_b"], "fps": 3, "from": "b12", "to": "fin"}]},
        {"a": "calamar_vampiro_brilla", "x": 540, "y": 780, "s": .55, "in": "b12:cuál+0.12", "fx_in": "pop", "idle": "float"},
        {"a": "rape_hembra_feliz", "id": "rape", "x": 800, "y": 1000, "s": .5, "in": "b12:cuál+0.24", "fx_in": "pop",
         "idle": "float"},
        {"a": "halo_celeste", "s": .16, "alpha": .9, "in": "b12:cuál+0.24", "fx_in": "pop", "sfx": "none", "idle": "latido",
         "sigue": {"id": "rape", "punto": SENUELO}},
        {"a": "batiscafo_pensando", "x": 540, "y": 1270, "s": .7, "in": "b12", "fx_in": "slide_up", "idle": "float", "blink": True,
         "swaps": [{"at": f"{FIN}+1.2", "a": "batiscafo_contento", "fx": "punch"}]},
        {"texto": {"t": "?", "estilo": "pregunta"}, "x": 740, "y": 1230, "r": 12, "in": "b12:extraterrestre", "fx_in": "pop",
         "idle": "wiggle", "out": "b12:cuéntanos", "fx_out": "pop"},
        {"a": "globo_comentario_1", "x": 780, "y": 1250, "s": .55, "in": "b12:cuéntanos", "fx_in": "pop", "sfx": "none", "z": 8,
         "loops": [{"frames": ["globo_comentario_1", "globo_comentario_2", "globo_comentario_3"], "fps": 4,
                    "from": "b12:cuéntanos", "to": "fin"}], "idle": "bob"},
    ] + cierre_el})

armar_doc(
    AQUI, narracion, escenas,
    persistentes=(encabezado(1, "El cangrejo yeti", "b1", "e3")
                  + encabezado(2, "El calamar vampiro", "b5", "e5")
                  + encabezado(3, "El rape abisal", "b9", "e7")
                  + [cortina(f"e{i}", asset="cortina_burbujas", sfx="glup") for i in (1, 3, 5, 7)]),
    estilos={"titulo_azul": {"size": 100, "color": "#FFFFFF", "stroke": 14, "stroke_color": "#0E2A4A"}},
    audio="--sin-audio" not in sys.argv,
    cola=3.4, volumen_ambiente=.35)
