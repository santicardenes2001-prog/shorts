"""Genera escenas.json (python3 armar_escenas.py [--sin-audio]). Editá acá y volvé a correrlo."""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", ".."))
from comun import armar_doc, cartel, cortina, encabezado, suscripcion  # noqa: E402

narracion = [
    "¡Te muestro 3 aves tan raras que cuesta creer que sean reales!",
    "1. El picozapato:",
    "Mide hasta un metro y medio y tiene un pico enorme y filoso que parece un zapato de madera.",
    "Puede quedarse inmóvil como una estatua durante horas para emboscar a sus presas, ¡hasta cocodrilos bebés!",
    "Y para comunicarse, choca el pico tan rápido que suena como una ráfaga de disparos.",
    "2. Urutaú (el pájaro fantasma):",
    "De día se queda rígido en la punta de una rama, haciéndose pasar por un tronco roto.",
    "Tiene ranuras en los párpados para vigilar con los ojos cerrados, sin que lo delate el brillo de sus enormes ojos amarillos.",
    "Pero de noche se transforma: abre una boca tan enorme que parece partirle la cabeza en dos y caza insectos en pleno vuelo,",
    "y su canto suena como el llanto de una persona.",
    "3. El hoacín (el pájaro apestoso):",
    "Es la única ave que digiere como una vaca, fermentando las hojas.",
    "Es por eso que huele tanto a estiércol que casi nadie se anima a cazarlo.",
    "Sus polluelos nacen con dos garras en cada ala y trepan por las ramas como pequeños dinosaurios.",
    "¿Tendrías alguno de ellos?",
]

PZ = dict(x=560, y=1300, s=1.0)          # picozapato en la orilla (escenas 1-3)
UR = dict(x=540, y=1380, s=1.0)          # urutaú en su tronco (escenas 4 y 6)
HO = dict(x=520, y=1015, s=1.0)          # hoacín en la rama (escenas 7-9)


# ------------------------------------------------------------ ambientación reutilizable
def rayos(op=.8):
    return {"a": "capa_rayos", "alpha": op, "z": 12, "idle": {"fx": "latido", "vel": .25, "fuerza": .5}, "fase": 0}


def hojas_frente():
    """Hojas desenfocadas en primer plano que se mecen apenas (profundidad)."""
    return {"a": "capa_hojas_frente", "z": 15, "idle": {"fx": "sway", "fuerza": .25}, "fase": 0}


def papiros_frente():
    return {"a": "capa_papiros_frente", "z": 15, "idle": {"fx": "sway", "fuerza": .2}, "fase": 0}


def vineta(op=1.0, **kw):
    e = {"a": "capa_vineta", "alpha": op, "z": 14}
    e.update(kw)
    return e


def niebla(y, x0, x1, op=.7, z=5):
    """Banco de niebla que se desliza despacio de x0 a x1 durante toda la escena."""
    return {"a": "niebla", "x": x0, "y": y, "s": 1.0, "alpha": op, "z": z, "fase": 0,
            "keys": [{"at": "esc", "hasta": "esc>", "x": x1, "ease": "linear"}]}


def hojas_caen(semilla, n=7, desde="esc"):
    return {"particulas": {"a": "hoja", "n": n, "semilla": semilla, "zona": [-100, -200, 1180, 2100], "vx": [-30, 40],
                           "vy": [60, 120], "s": [.18, .3], "giro": [-60, 60], "ondula": [40, .3], "alpha": [.7, 1]},
            "in": desde, "fx_in": "fade", "z": 16}


def luciernagas(desde, n=18):
    return {"particulas": {"a": "luciernaga", "n": n, "semilla": 4, "zona": [0, 500, 1080, 1500], "vx": [-15, 15],
                           "vy": [-15, 10], "s": [.6, 1.2], "titila": .9, "ondula": [30, .25]},
            "in": desde, "fx_in": "fade", "dur_in": 1.2, "z": 13}


def camara_lenta(z0, z1, extra=None):
    """Respiración de cámara: de zoom z0 a z1 durante toda la escena (continúa el zoom de la anterior)."""
    keys = [{"at": "esc", "dur": .001, "zoom": z0}, {"at": "esc+0.01", "hasta": "esc>", "zoom": z1, "ease": "linear"}]
    return {"keys": keys + (extra or [])}


def sale(e, fx="pop"):
    """Marca un elemento para que salga animado antes del corte."""
    e["fx_out"] = fx
    return e


escenas = []

# ------------------------------------------------------------ 0. gancho
escenas.append({
    "nombre": "gancho", "beats": [0], "fondo": "fondo_rio", "ambiente": "selva",
    "camara": camara_lenta(1.0, 1.05),
    "elementos": [
        rayos(), hojas_frente(), hojas_caen(1),
        {"texto": {"t": "3 AVES\nRARAS", "estilo": "titulo_verde", "size": 116}, "x": 540, "y": 330, "in": "b0:3",
         "fx_in": "pop", "fx_out": "suave", "idle": "breathe", "z": 45},
        sale({"a": "picozapato_0", "x": 215, "y": 1010, "s": .55, "in": "b0:aves", "fx_in": "pop", "sfx": "aleteo",
              "idle": "breathe", "blink": True}),
        sale({"a": "urutau_ojos", "x": 540, "y": 880, "s": .5, "in": "b0:aves+0.15", "fx_in": "pop", "sfx": "pop",
              "idle": "breathe"}),
        sale({"a": "hoacin", "x": 850, "y": 990, "s": .68, "in": "b0:aves+0.3", "fx_in": "pop", "sfx": "aleteo",
              "idle": "breathe", "blink": True}),
        sale({"a": "vos_explo_binoculares", "x": 540, "y": 1330, "s": .55, "in": "b0+0.1", "fx_in": "jump", "idle": "breathe",
              "swaps": [{"at": "b0:reales", "a": "vos_explo_sorpresa", "fx": "punch"}]}, "slide_down"),
    ]})

# ------------------------------------------------------------ 1. picozapato: tamaño y pico
escenas.append({
    "nombre": "picozapato_intro", "beats": [1, 2], "fondo": "fondo_humedal", "ambiente": "pantano",
    "camara": camara_lenta(1.0, 1.04),
    "sonidos": [{"at": "b2:filoso", "s": "filo", "vol": .8}],
    "elementos": [
        niebla(1050, -300, 200), niebla(1180, 900, 600, .5), rayos(.6), papiros_frente(),
        {"a": "picozapato_0", **PZ, "in": "b1:picozapato", "fx_in": "drop", "dur_in": .9, "sfx": "aleteo",
         "idle": "breathe", "blink": True, "fase": 0},
        sale({"a": "regla", "x": 170, "y": 1300, "s": 1.0, "in": "b2:metro", "fx_in": "grow", "dur_in": .6}),
        cartel("1,5 m", 170, 500, "b2:metro", size=84, estilo="cartel_amarillo"),
        sale({"a": "flecha_roja", "x": 985, "y": 650, "s": .32, "r": 90, "in": "b2:pico", "fx_in": "pop", "idle": "work"}),
        sale({"a": "brillo", "x": 872, "y": 676, "s": .45, "in": "b2:filoso", "fx_in": "pop", "idle": "pulse", "sfx": "none"}),
        sale({"a": "zueco", "x": 760, "y": 470, "s": .8, "r": -8, "in": "b2:zapato", "fx_in": "pop", "idle": "float"}),
    ]})

# ------------------------------------------------------------ 2. estatua, horas y caza
escenas.append({
    "nombre": "picozapato_caza", "beats": [3], "fondo": "fondo_humedal", "ambiente": "pantano",
    "camara": camara_lenta(1.04, 1.08),
    "sonidos": [{"at": "b3:presas", "s": "glup"}, {"at": "b3:horas", "s": "tictac", "vol": .7}],
    "elementos": [
        niebla(1050, 200, 500), niebla(1180, 600, 300, .5), rayos(.6), papiros_frente(),
        {"a": "picozapato_0", **PZ, "idle": {"fx": "breathe", "to": "b3:inmóvil"}, "blink": True, "fase": 0,
         "keys": [{"at": "b3:presas-0.15", "dur": .18, "y": 1350, "r": 14, "ease": "in"},
                  {"at": "b3:presas+0.2", "dur": .35, "y": 1300, "r": 0, "ease": "out"}]},
        cartel("COMO UNA ESTATUA", 540, 470, "b3:estatua", size=70, out="b3:horas"),
        sale({"a": "vos_explo", "x": 150, "y": 1330, "s": .4, "in": "b3:estatua", "fx_in": "jump", "idle": "breathe",
              "blink": True, "fase": 0, "swaps": [{"at": "b3:cocodrilos", "a": "vos_explo_sorpresa", "fx": "punch"}]}, "none"),
        sale({"a": "zzz", "x": 250, "y": 930, "s": .45, "in": "b3:horas", "fx_in": "pop", "idle": "float",
              "out": "b3:emboscar"}),
        sale({"a": "reloj", "x": 890, "y": 600, "s": .5, "in": "b3:horas", "fx_in": "pop", "sfx": "none", "out": "b3:presas"}),
        sale({"a": "reloj_aguja", "x": 890, "y": 600, "s": .5, "z": 1, "in": "b3:horas", "fx_in": "pop", "sfx": "none",
              "idle": {"fx": "spin", "vel": 1440}, "out": "b3:presas"}),
        cartel("HORAS…", 640, 520, "b3:horas", size=70, estilo="cartel_celeste", out="b3:emboscar"),
        # el pez nada hacia el picozapato y desaparece cuando ataca
        {"a": "pez_pulmonado", "x": 1150, "y": 1395, "s": .75, "flip": True, "in": "b3:emboscar", "z": 2,
         "keys": [{"at": "b3:emboscar", "dur": 1.0, "x": 760, "ease": "out"},
                  {"at": "b3:presas", "dur": .15, "alpha": 0, "s": .3}], "idle": "sway", "out": "b3:presas+0.3"},
        sale({"a": "cocodrilo_bebe", "x": 820, "y": 1300, "s": 1.05, "flip": True, "in": "b3:cocodrilos", "fx_in": "jump",
              "idle": "shake", "z": 2}),
        cartel("¡HASTA COCODRILOS!", 540, 470, "b3:cocodrilos", size=70, estilo="cartel_verde"),
    ]})

# ------------------------------------------------------------ 3. castañeteo de pico (con su pausa)
escenas.append({
    "nombre": "picozapato_matraca", "beats": [4], "fondo": "fondo_humedal", "ambiente": "pantano",
    "camara": {"keys": [{"at": "esc", "dur": .001, "zoom": 1.08},
                        {"at": "b4:comunicarse", "dur": .9, "zoom": 1.65, "x": 650, "y": 720, "ease": "inout"}],
               "temblor": [{"from": "b4:disparos>", "to": "b4:disparos>+1.45", "fuerza": 1.0}]},
    "sonidos": [{"at": "b4:disparos>", "s": "matraca", "destacado": True, "vol": 1.1}, {"at": "b4:disparos>+0.2", "s": "aleteo", "vol": .7}],
    "elementos": [
        niebla(1050, 500, 700), niebla(1180, 300, 150, .5), rayos(.6), papiros_frente(),
        {"a": "picozapato_0", **PZ, "blink": True, "fase": 0,
         "loops": [{"frames": ["picozapato_0", "picozapato_1"], "fps": 5, "from": "b4:choca", "to": "b4:rápido"},
                   {"frames": ["picozapato_0", "picozapato_2", "picozapato_1"], "fps": 18,
                    "from": "b4:disparos>", "to": "b4:disparos>+1.4"}],
         "idle": {"fx": "shake", "fuerza": .5, "from": "b4:disparos>", "to": "b4:disparos>+1.4"}},
        {"a": "vos_explo_sorpresa", "x": 150, "y": 1330, "s": .4, "idle": "breathe", "blink": True, "fase": 0,
         "swaps": [{"at": "b4:disparos>", "a": "vos_explo_miedo", "fx": "punch"}]},
        {"a": "rayitas", "x": 880, "y": 700, "s": .9, "in": "b4:disparos>", "out": "b4:disparos>+1.4", "fx_in": "pop",
         "sfx": "none", "idle": {"fx": "pulse", "fuerza": 2}},
        cartel("¡RA-TA-TA-TA!", 662, 423, "b4:disparos>", size=52, estilo="cartel_amarillo", r=-6, idle="shake",
               out="b4:disparos>+1.45", sfx="none"),
        {"particulas": {"a": "pajarito", "n": 9, "semilla": 6, "zona": [-100, 300, 1180, 1000], "vx": [-420, -250],
                        "vy": [-260, -140], "s": [.6, 1.1], "ondula": [10, 2]},
         "in": "b4:disparos>+0.15", "out": "b4:disparos>+1.45", "fx_in": "fade", "fx_out": "fade", "z": 25},
    ]})

# ------------------------------------------------------------ 4. urutaú de día: rama o pájaro
escenas.append({
    "nombre": "urutau_dia", "beats": [5, 6], "fondo": "fondo_bosque_dia", "ambiente": "bosque",
    "camara": {"keys": [{"at": "esc", "hasta": "b6:roto", "zoom": 1.04, "ease": "linear"},
                        {"at": "b6:roto", "hasta": "esc>", "zoom": 2.3, "x": 540, "y": 832, "ease": "in"}]},
    "elementos": [
        sale(rayos(.7), "fade"), hojas_caen(2, 5),
        {"a": "urutau_rama", **UR, "in": "b5:urutaú", "fx_in": "fade", "dur_in": 1.0, "idle": "breathe", "fase": 0},
        cartel("(EL PÁJARO FANTASMA)", 540, 470, "b5:fantasma", size=62, out="b6:rama"),
        sale({"a": "tronco_roto", "x": 230, "y": 1385, "s": 1.25, "in": "b6:tronco", "fx_in": "grow", "z": -1}),
        sale({"a": "vos_explo_binoculares", "x": 860, "y": 1330, "s": .42, "flip": True, "in": "b6:rígido", "fx_in": "jump",
              "idle": "breathe", "swaps": [{"at": "b6:tronco", "a": "vos_explo_pensando", "fx": "punch"}]}),
        cartel("¿RAMA O PÁJARO?", 540, 470, "b6:tronco", size=74, estilo="cartel_amarillo", out="b6:roto+0.3"),
    ]})

# ------------------------------------------------------------ 5. primer plano del ojo
escenas.append({
    "nombre": "urutau_ojo", "beats": [7], "fondo": "fondo_bosque_dia", "ambiente": "bosque",
    "transicion": "primer plano (la cámara entra en la cara del urutaú y corta al ojo)",
    "camara": camara_lenta(1.0, 1.03),
    "sonidos": [{"at": "b7:brillo", "s": "brillo"}],
    "elementos": [
        {"a": "fondo_bosque_dia", "s": 1.7, "x": 540, "y": 700, "z": -20},
        vineta(),
        {"a": "urutau_ojo_1", "x": 540, "y": 900, "s": 1.35, "z": 36, "idle": "breathe", "fx_in": "grow", "dur_in": .35,
         "sfx": "none",
         "loops": [{"frames": ["urutau_ojo_0", "urutau_ojo_1", "urutau_ojo_2", "urutau_ojo_1"], "fps": 2.5,
                    "from": "b7:vigilar", "to": "b7:brillo"}],
         "swaps": [{"at": "b7:brillo", "a": "urutau_ojo_abierto", "fx": "punch"}]},
        sale({"a": "flecha_roja", "x": 459, "y": 790, "s": .3, "z": 37, "in": "b7:ranuras", "fx_in": "pop", "idle": "work",
              "out": "b7:brillo"}),
        sale({"a": "flecha_roja", "x": 621, "y": 790, "s": .3, "z": 37, "in": "b7:ranuras+0.1", "fx_in": "pop", "idle": "work",
              "sfx": "none", "out": "b7:brillo"}),
        cartel("RANURAS EN LOS PÁRPADOS", 540, 470, "b7:ranuras", size=58, out="b7:cerrados", z=38),
        cartel("VIGILA CON LOS OJOS CERRADOS", 540, 470, "b7:cerrados", size=54, estilo="cartel_celeste", out="b7:brillo", z=38),
        {"a": "brillo", "x": 430, "y": 780, "s": .6, "z": 38, "in": "b7:brillo", "fx_in": "pop", "idle": "pulse", "sfx": "none",
         "fx_out": "pop"},
        {"a": "brillo", "x": 680, "y": 1010, "s": .35, "z": 38, "in": "b7:brillo+0.15", "fx_in": "pop", "idle": "pulse",
         "sfx": "none", "fx_out": "pop"},
    ]})

# ------------------------------------------------------------ 6. de noche: boca enorme y canto
escenas.append({
    "nombre": "urutau_noche", "beats": [8, 9], "fondo": "fondo_bosque_noche", "ambiente": "noche",
    "camara": {"keys": [{"at": "esc", "dur": .001, "zoom": 1.9, "x": 540, "y": 832},
                        {"at": "esc+0.05", "hasta": "b8:abre", "zoom": 1.0, "x": 540, "y": 960, "ease": "inout"},
                        {"at": "b8:boca", "dur": .5, "zoom": 1.3, "x": 540, "y": 860, "ease": "back"},
                        {"at": "b9", "dur": .8, "zoom": 1.1, "x": 540, "y": 960, "ease": "inout"}]},
    "sonidos": [{"at": "b8:boca", "s": "zumbido", "vol": .7}, {"at": "b8:vuelo", "s": "glup"},
                {"at": "b9:canto", "s": "llanto", "vol": 1.2}],
    "elementos": [
        # atardecer: el bosque de día se desvanece sobre el de noche
        {"a": "fondo_bosque_dia", "z": -20, "keys": [{"at": "b8:noche", "dur": 1.4, "alpha": 0, "ease": "inout"}]},
        vineta(0, keys=[{"at": "b8:noche", "dur": 1.4, "alpha": 1}]),
        luciernagas("b8:noche+0.6"),
        {"a": "urutau_rama", **UR, "idle": "breathe", "fase": 0,
         "swaps": [{"at": "b8:transforma", "a": "urutau_ojos", "fx": "punch"},
                   {"at": "b8:boca", "a": "urutau_boca", "fx": "punch"},
                   {"at": "b8:vuelo+0.4", "a": "urutau_ojos"},
                   {"at": "b9:canto", "a": "urutau_canto", "fx": "punch"}]},
        {"particulas": {"a": "polilla", "n": 6, "semilla": 3, "zona": [300, 640, 780, 1000], "vx": [-30, 30], "vy": [-20, 20],
                        "s": [.5, .8], "ondula": [40, .8]}, "in": "b8:insectos", "out": "b9", "fx_in": "fade",
         "fx_out": "fade", "z": 3},
        {"a": "polilla", "x": 800, "y": 700, "s": .7, "z": 4, "in": "b8:insectos", "fx_in": "fade", "sfx": "none",
         "keys": [{"at": "b8:vuelo-0.2", "dur": .45, "x": 545, "y": 832, "s": .2, "alpha": 0, "ease": "in"}],
         "idle": {"fx": "bob", "fuerza": 2}, "out": "b8:vuelo+0.4"},
        cartel("¡BOCA GIGANTE!", 540, 470, "b8:enorme", size=80, estilo="cartel_rojo", out="b9"),
        {"particulas": {"a": "nota_musical", "n": 6, "semilla": 5, "zona": [380, 300, 760, 820], "vx": [-10, 10],
                        "vy": [-90, -60], "s": [.5, .8], "ondula": [25, .5], "r": [-15, 15]},
         "in": "b9:canto", "fx_in": "fade", "fx_out": "fade", "z": 6},
        sale({"a": "vos_explo_linterna", "x": 170, "y": 1330, "s": .42, "in": "b8:noche+0.4", "fx_in": "jump",
              "idle": ["breathe", {"fx": "shake", "fuerza": .5, "from": "b9:llanto"}], "blink": True}, "slide_left"),
        sale({"a": "rayo_luz", "x": 273, "y": 1177, "r": -52, "s": .95, "alpha": .9, "z": -1, "in": "b8:noche+0.8",
              "fx_in": "wipe", "sfx": "click", "idle": {"fx": "latido", "fuerza": .3}}, "fade"),
    ]})

# ------------------------------------------------------------ 7. hoacín: apestoso y digiere como vaca
escenas.append({
    "nombre": "hoacin_vaca", "beats": [10, 11], "fondo": "fondo_rio", "ambiente": "selva",
    "camara": camara_lenta(1.0, 1.04),
    "sonidos": [{"at": "b11:vaca", "s": "muu"}],
    "elementos": [
        rayos(), hojas_frente(), hojas_caen(3),
        {"a": "rama", "x": 540, "y": 1020, "s": 1.0, "z": -1},
        {"a": "hoacin", **HO, "in": "b10:hoacín", "fx_in": "slide_down", "sfx": "aleteo", "idle": "breathe", "blink": True,
         "fase": 0},
        {"a": "olor", "x": 420, "y": 600, "s": .5, "in": "b10:apestoso", "fx_in": "fade", "idle": "sway", "fase": 0},
        {"a": "olor", "x": 640, "y": 590, "s": .45, "in": "b10:apestoso+0.15", "fx_in": "fade", "idle": "sway", "flip": True,
         "fase": 1},
        cartel("(EL PÁJARO APESTOSO)", 540, 470, "b10:apestoso", size=60, out="b11:vaca"),
        sale({"a": "vaca", "x": 820, "y": 1330, "s": .7, "in": "b11:vaca", "fx_in": "jump", "sfx": "none", "idle": "breathe"}),
        cartel("DIGIERE COMO UNA VACA", 540, 470, "b11:vaca", size=60, estilo="cartel_verde"),
        # hojas que entran al buche y burbujas de fermentación
        sale({"a": "halo_verde", "x": 600, "y": 870, "s": .3, "alpha": .9, "z": 2, "in": "b11:fermentando", "fx_in": "fade",
              "idle": "latido"}, "fade"),
        {"particulas": {"a": "burbuja", "n": 8, "semilla": 4, "zona": [540, 800, 660, 940], "vy": [-40, -20], "s": [.4, .8],
                        "ondula": [6, .6]}, "in": "b11:fermentando", "fx_in": "fade", "fx_out": "fade", "z": 3},
        sale({"a": "hoja", "x": 860, "y": 640, "s": .3, "in": "b11:hojas", "fx_in": "pop", "sfx": "none",
              "keys": [{"at": "b11:hojas+0.2", "dur": .5, "x": 600, "y": 870, "s": .1, "alpha": 0, "r": 200, "ease": "in"}]}),
    ]})

# ------------------------------------------------------------ 8. olor: nadie lo caza
escenas.append({
    "nombre": "hoacin_olor", "beats": [12], "fondo": "fondo_rio", "ambiente": "selva",
    "camara": camara_lenta(1.04, 1.08),
    "sonidos": [{"at": "b12:estiércol", "s": "boing", "vol": .6}],
    "elementos": [
        rayos(), hojas_frente(), hojas_caen(3),
        {"a": "rama", "x": 540, "y": 1020, "s": 1.0, "z": -1},
        {"a": "hoacin", **HO, "idle": "breathe", "blink": True, "fase": 0},
        {"a": "olor", "x": 420, "y": 600, "s": .5, "idle": "sway", "fase": 0,
         "keys": [{"at": "b12:huele", "dur": .5, "s": .75, "y": 560}]},
        {"a": "olor", "x": 640, "y": 590, "s": .45, "idle": "sway", "flip": True, "fase": 1,
         "keys": [{"at": "b12:huele", "dur": .5, "s": .7, "y": 550}]},
        sale({"a": "olor", "x": 300, "y": 720, "s": .6, "in": "b12:estiércol", "fx_in": "fade", "idle": "sway"}, "fade"),
        sale({"a": "olor", "x": 770, "y": 700, "s": .55, "in": "b12:estiércol+0.1", "fx_in": "fade", "idle": "sway",
              "flip": True}, "fade"),
        {"a": "vos_explo_nariz", "x": 860, "y": 1330, "s": .42, "in": "b12:huele", "fx_in": "jump", "idle": "shake",
         "fase": 0},
        cartel("¡OLOR A ESTIÉRCOL!", 540, 470, "b12:estiércol", size=70, estilo="cartel_marron", out="b12:nadie"),
        # un jaguar se acerca por la rama, lo huele y se va
        {"a": "jaguar", "x": -200, "y": 1015, "s": .55, "in": "b12:nadie-0.6", "out": "b12:anima-0.2", "sfx": "none",
         "keys": [{"at": "b12:nadie-0.6", "dur": .6, "x": 230, "ease": "out"}], "idle": "breathe"},
        {"a": "jaguar_asco", "x": 230, "y": 1015, "s": .55, "flip": True, "in": "b12:anima-0.2", "sfx": "boing",
         "keys": [{"at": "b12:anima+0.2", "dur": .45, "x": -300, "ease": "in", "sfx": "whoosh"}], "idle": "shake"},
        cartel("NADIE LO CAZA", 540, 470, "b12:nadie", size=74, estilo="cartel_rojo"),
    ]})

# ------------------------------------------------------------ 9. pichones con garras
escenas.append({
    "nombre": "hoacin_pichon", "beats": [13], "fondo": "fondo_rio", "ambiente": "selva",
    "camara": {"keys": [{"at": "esc", "dur": .001, "zoom": 1.08}, {"at": "esc+0.01", "dur": 1.0, "zoom": 1.0}]},
    "sonidos": [{"at": "b13:polluelos+0.3", "s": "pio"}, {"at": "b13:trepan+0.6", "s": "pio", "vol": .7}],
    "elementos": [
        rayos(), hojas_frente(), hojas_caen(3),
        {"a": "rama", "x": 540, "y": 1020, "s": 1.0, "z": -1},
        {"a": "hoacin", **HO, "idle": "breathe", "blink": True, "fase": 0},
        {"a": "olor", "x": 420, "y": 560, "s": .75, "idle": "sway", "fase": 0, "fx_out": "fade",
         "keys": [{"at": "esc+0.2", "dur": .6, "alpha": 0}]},
        {"a": "olor", "x": 640, "y": 550, "s": .7, "idle": "sway", "flip": True, "fase": 1,
         "keys": [{"at": "esc+0.2", "dur": .6, "alpha": 0}]},
        {"a": "vos_explo_nariz", "x": 860, "y": 1330, "s": .42, "idle": "shake", "fase": 0,
         "swaps": [{"at": "b13:garras", "a": "vos_explo_sorpresa", "fx": "punch"}]},
        sale({"a": "rama", "x": 420, "y": 1190, "s": .75, "r": -35, "in": "b13:polluelos", "fx_in": "grow", "z": -2,
              "sfx": "none"}),
        sale({"a": "hoacin_pichon_0", "x": 230, "y": 1240, "s": .8, "r": -20, "in": "b13:polluelos+0.2", "fx_in": "pop",
              "sfx": "none",
              "loops": [{"frames": ["hoacin_pichon_0", "hoacin_pichon_1"], "fps": 4, "from": "b13:trepan", "to": "esc>"}],
              "keys": [{"at": "b13:trepan", "dur": 2.4, "x": 540, "y": 1050, "ease": "linear"}]}),
        sale({"a": "flecha_roja", "x": 110, "y": 1060, "s": .3, "r": -45, "in": "b13:garras", "fx_in": "pop", "idle": "work",
              "out": "b13:trepan"}),
        cartel("GARRAS EN LAS ALAS", 540, 470, "b13:garras", size=66, out="b13:como"),
        sale({"a": "dino", "x": 300, "y": 840, "s": .45, "alpha": .9, "in": "b13:como", "fx_in": "pop", "idle": "bob"}),
        cartel("¡COMO DINOSAURIOS!", 540, 470, "b13:como", size=66, estilo="cartel_verde"),
    ]})

# ------------------------------------------------------------ 10. cierre: pregunta y suscripción
FIN = "b14>"
escenas.append({
    "nombre": "cierre", "beats": [14], "fondo": "fondo_burst_verde", "ambiente": {"tipo": "selva", "vol": .6},
    "elementos": [
        hojas_caen(5, 6),
        {"a": "picozapato_0", "x": 215, "y": 980, "s": .55, "in": "b14:tendrías", "fx_in": "pop", "sfx": "aleteo",
         "idle": "breathe", "blink": True},
        {"a": "urutau_ojos", "x": 540, "y": 860, "s": .48, "in": "b14:tendrías+0.12", "fx_in": "pop", "idle": "breathe"},
        {"a": "hoacin", "x": 850, "y": 960, "s": .66, "in": "b14:tendrías+0.24", "fx_in": "pop", "sfx": "aleteo",
         "idle": "breathe", "blink": True},
        {"a": "vos_explo_pensando", "x": 540, "y": 1330, "s": .55, "in": "b14", "fx_in": "jump", "idle": "breathe",
         "blink": True, "swaps": [{"at": f"{FIN}+1.2", "a": "vos_explo_pulgar", "fx": "punch"}]},
        {"texto": {"t": "?", "estilo": "pregunta"}, "x": 720, "y": 1070, "r": 12, "in": "b14:alguno", "fx_in": "pop",
         "idle": "wiggle", "out": f"{FIN}+0.9", "fx_out": "pop"},
    ] + suscripcion(FIN)[0]})
escenas[-1]["sonidos"] = suscripcion(FIN)[1]

armar_doc(
    AQUI, narracion, escenas,
    persistentes=(encabezado(1, "El picozapato", "b1", "e4")
                  + encabezado(2, "Urutaú", "b5", "e7")
                  + encabezado(3, "El hoacín", "b10", "e10")
                  + [cortina("e1"), cortina("e4"), cortina("e7"), cortina("e10")]),
    estilos={"titulo_verde": {"size": 100, "color": "#FFFFFF", "stroke": 14, "stroke_color": "#1E5A2A"},
},
    audio="--sin-audio" not in sys.argv,
    pausas=[{"despues": "b4:disparos", "dur": 1.5}],
    cola=3.4, volumen_ambiente=.35)
