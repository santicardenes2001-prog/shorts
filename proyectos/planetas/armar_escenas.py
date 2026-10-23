"""Genera escenas.json (python3 armar_escenas.py [--sin-audio]). Editá acá y volvé a correrlo."""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "escenas.json")

narracion = [
    "¡Te muestro 3 planetas tan extraños que parecen inventados!",
    "1. HD 189733b, donde llueve vidrio de lado.",
    "Se ve azul y hermoso,",
    "pero su atmósfera está llena de silicatos, el material del vidrio.",
    "Con más de 900 grados y vientos de 8700 kilómetros por hora,",
    "llueve vidrio derretido en horizontal.",
    "2. TrES-2b, el planeta más oscuro que se conoce.",
    "Es del tamaño de Júpiter,",
    "pero refleja menos del 1% de la luz que recibe: es más negro que el carbón.",
    "Aunque no del todo invisible: a casi 1000 grados, brilla con un rojo tenue, como una brasa.",
    "3. 55 Cancri e, el planeta de diamante.",
    "Mide el doble que la Tierra",
    "y su año dura solo 18 horas.",
    "Tiene tanto carbono, y tanta presión y calor adentro,",
    "que se cree que gran parte de su interior podría ser diamante.",
]


def estrellas(semilla):
    """Estrellas que titilan sobre el fondo (detrás de todo)."""
    return {"particulas": {"a": ["estrellita", "punto_estrella", "punto_estrella"], "n": 26, "semilla": semilla,
                           "s": [.35, .9], "titila": .8, "vy": [4, 10]}, "z": -10}


def lluvia(at, n=26, fundido=False, out=None, vel=(1300, 1900), zona=(-300, 470, 1380, 1340), z=8):
    a = ["vidrio_a", "vidrio_b", "vidrio_c"]
    if fundido:
        a += ["vidrio_fundido_a", "vidrio_fundido_b", "vidrio_fundido_c"]
    e = {"particulas": {"a": a, "n": n, "semilla": 7 + n, "zona": list(zona), "vx": list(vel), "vy": [-20, 70],
                        "s": [.45, .95], "r": [-4, 8], "alpha": [.8, 1]},
         "in": at, "fx_in": "fade", "dur_in": .4, "z": z}
    if out:
        e.update(out=out, fx_out="fade")
    return e


def viento(at, n=9, out=None, zona=(-400, 470, 1480, 1340), z=7):
    e = {"particulas": {"a": "viento", "n": n, "semilla": 3, "zona": list(zona), "vx": [1700, 2300], "vy": [0, 0],
                        "s": [.6, 1.1], "alpha": [.35, .7]}, "in": at, "fx_in": "fade", "z": z}
    if out:
        e.update(out=out, fx_out="fade")
    return e


def cartel(t, x, y, at, size=96, estilo="cartel", **kw):
    e = {"texto": {"t": t, "estilo": estilo, "size": size}, "x": x, "y": y, "in": at, "fx_in": "pop", "z": 20}
    e.update(kw)
    return e


escenas = []

# ------------------------------------------------------------ 0. gancho
escenas.append({
    "nombre": "gancho", "beats": [0], "fondo": "fondo_espacio",
    "sonidos": [{"at": "b0:extraños", "s": "boing", "vol": .6}],
    "elementos": [
        estrellas(1),
        {"texto": {"t": "3 PLANETAS\nEXTRAÑOS", "estilo": "titulo", "size": 104}, "x": 540, "y": 330,
         "in": "b0:3", "fx_in": "pop", "idle": "breathe"},
        {"a": "halo_azul", "x": 250, "y": 760, "s": .45, "alpha": .5, "in": "b0:planetas", "fx_in": "fade", "idle": "latido"},
        {"a": "hd189733b_lindo", "x": 250, "y": 760, "s": .42, "in": "b0:planetas", "fx_in": "pop", "idle": "float"},
        {"a": "halo_rojo", "x": 540, "y": 640, "s": .45, "alpha": .45, "in": "b0:planetas+0.15", "fx_in": "fade", "idle": "latido"},
        {"a": "tres2b_cool", "x": 540, "y": 640, "s": .42, "in": "b0:planetas+0.15", "fx_in": "pop", "idle": "float"},
        {"a": "cancri_neutral", "x": 830, "y": 760, "s": .42, "in": "b0:planetas+0.3", "fx_in": "pop", "idle": "float",
         "swaps": [{"at": "b0:inventados", "a": "cancri_sorpresa"}]},
        {"a": "vos_astro", "x": 540, "y": 1330, "s": .62, "in": "b0+0.1", "fx_in": "jump", "idle": "breathe", "blink": True,
         "swaps": [{"at": "b0:extraños", "a": "vos_astro_sorpresa", "fx": "punch"}]},
        {"texto": {"t": "?", "estilo": "pregunta"}, "x": 290, "y": 1010, "r": -12, "in": "b0:inventados", "fx_in": "pop",
         "idle": "wiggle"},
        {"texto": {"t": "?", "estilo": "pregunta"}, "x": 800, "y": 980, "r": 12, "in": "b0:inventados+0.12", "fx_in": "pop",
         "idle": "wiggle"},
    ]})

# ------------------------------------------------------------ 1. HD 189733b presentación
escenas.append({
    "nombre": "hd_intro", "beats": [1], "fondo": "fondo_espacio", "flash": True,
    "sonidos": [{"at": "b1:llueve", "s": "viento", "vol": .8}, {"at": "b1:vidrio", "s": "cristal"}],
    "camara": {"keys": [{"at": "b1:hd", "dur": 3.5, "zoom": 1.08, "ease": "linear"}]},
    "elementos": [
        estrellas(2),
        {"a": "halo_azul", "x": 540, "y": 860, "s": 1.05, "alpha": .55, "in": "b1:hd", "fx_in": "fade", "idle": "latido"},
        {"a": "hd189733b_lindo", "x": 540, "y": 860, "s": .95, "in": "b1:hd", "fx_in": "grow", "idle": "float", "blink": False,
         "swaps": [{"at": "b1:vidrio", "a": "hd189733b_contento", "fx": "punch"}]},
        viento("b1:llueve"),
        lluvia("b1:llueve", n=22),
        cartel("DE LADO →", 540, 1300, "b1:lado", size=84, estilo="cartel_celeste"),
    ]})

# ------------------------------------------------------------ 2. lindo... pero malvado
escenas.append({
    "nombre": "hd_lindo_malo", "beats": [2, 3], "fondo": "fondo_espacio",
    "sonidos": [{"at": "b2:hermoso", "s": "brillo", "vol": .7}, {"at": "b3:pero", "s": "zumbido"},
                {"at": "b3:vidrio", "s": "cristal"}],
    "elementos": [
        estrellas(3),
        {"a": "halo_azul", "x": 540, "y": 740, "s": .9, "alpha": .5, "idle": "latido"},
        {"a": "halo_azul", "x": 540, "y": 740, "s": 1.25, "alpha": 0, "idle": {"fx": "latido", "fuerza": 1.4, "vel": 2},
         "keys": [{"at": "b3:atmósfera", "dur": .4, "alpha": .9}]},
        {"a": "hd189733b_lindo", "x": 540, "y": 740, "s": .82, "idle": "float",
         "swaps": [{"at": "b3:pero", "a": "hd189733b_malo", "fx": "punch"}]},
        {"a": "corazon", "x": 230, "y": 520, "s": .8, "r": -12, "in": "b2:hermoso", "fx_in": "pop", "idle": "bob",
         "out": "b3:pero", "fx_out": "pop"},
        {"a": "corazon", "x": 850, "y": 540, "s": .65, "r": 14, "in": "b2:hermoso+0.12", "fx_in": "pop", "idle": "bob",
         "out": "b3:pero", "fx_out": "pop"},
        {"a": "brillo", "x": 250, "y": 980, "s": .6, "in": "b2:azul", "fx_in": "pop", "idle": "pulse", "out": "b3:pero", "fx_out": "pop"},
        {"a": "brillo", "x": 830, "y": 900, "s": .45, "in": "b2:azul+0.1", "fx_in": "pop", "idle": "pulse", "out": "b3:pero", "fx_out": "pop"},
        {"a": "vos_astro_contento", "x": 830, "y": 1330, "s": .5, "in": "b2", "fx_in": "jump", "idle": "breathe", "blink": True,
         "swaps": [{"at": "b3:pero", "a": "vos_astro_susto", "fx": "punch"}]},
        cartel("SILICATOS", 360, 1150, "b3:silicatos", size=84, estilo="cartel", idle="breathe"),
        cartel("= VIDRIO", 360, 1310, "b3:vidrio", size=66, estilo="cartel_celeste"),
        {"a": "vidrio_a", "x": 110, "y": 1300, "s": .7, "r": -30, "in": "b3:vidrio", "fx_in": "pop", "idle": "wiggle", "sfx": "none"},
        {"a": "vidrio_b", "x": 610, "y": 1290, "s": .7, "r": 25, "in": "b3:vidrio+0.1", "fx_in": "pop", "idle": "wiggle", "sfx": "none"},
    ]})

# ------------------------------------------------------------ 3. datos + lluvia horizontal
escenas.append({
    "nombre": "hd_datos_lluvia", "beats": [4, 5], "fondo": "fondo_espacio",
    "sonidos": [{"at": "b5", "s": "viento"}, {"at": "b5+1.0", "s": "viento", "vol": .7},
                {"at": "b5:derretido", "s": "cristal"}],
    "camara": {"temblor": [{"from": "b5", "to": "esc>", "fuerza": 1.2}]},
    "elementos": [
        estrellas(4),
        {"a": "hd189733b_malo", "x": 540, "y": 640, "s": .5, "idle": "float"},
        {"a": "termometro_00", "x": 200, "y": 1260, "s": .85, "in": "b4", "fx_in": "pop",
         "seq": {"frames": [f"termometro_{i:02d}" for i in range(11)], "at": "b4:900", "dur": .7},
         "idle": {"fx": "shake", "fuerza": .3, "from": "b4:900+0.7"}, "out": "b5", "fx_out": "pop"},
        cartel("+900 °C", 250, 700, "b4:900", size=92, estilo="cartel_rojo", idle="pulse", out="b5", fx_out="pop"),
        {"a": "velocimetro", "x": 780, "y": 1170, "s": .85, "in": "b4:vientos", "fx_in": "pop", "out": "b5", "fx_out": "pop"},
        {"a": "velocimetro_aguja", "x": 780, "y": 1170, "s": .9, "r": -178, "z": 1, "in": "b4:vientos", "fx_in": "pop",
         "sfx": "none", "keys": [{"at": "b4:8700", "dur": .7, "r": -6, "ease": "back", "sfx": "zoom"}],
         "idle": {"fx": "wiggle", "fuerza": .25, "from": "b4:8700+0.7"}, "out": "b5", "fx_out": "pop"},
        cartel("8700 km/h", 780, 930, "b4:8700", size=84, estilo="cartel", idle="pulse", out="b5", fx_out="pop"),
        viento("b5", n=12),
        {"a": "vos_astro_susto", "x": 540, "y": 1330, "s": .62, "in": "b5", "fx_in": "slide_right", "z": 5,
         "r": 0, "keys": [{"at": "b5+0.3", "dur": .4, "r": 10, "x": 600}], "idle": "shake", "blink": True},
        lluvia("b5", n=40, fundido=True, vel=(1600, 2300), z=9),
        cartel("¡EN HORIZONTAL!", 540, 520, "b5:horizontal", size=80, estilo="cartel_celeste", r=-4),
    ]})

# ------------------------------------------------------------ 4. TrES-2b presentación
escenas.append({
    "nombre": "tres_intro", "beats": [6], "fondo": "fondo_espacio_rojo", "flash": True,
    "sonidos": [{"at": "b6:oscuro", "s": "zumbido", "vol": .8}],
    "elementos": [
        estrellas(5),
        {"a": "halo_rojo", "x": 540, "y": 840, "s": 1.0, "alpha": .2, "idle": "latido"},
        {"a": "tres2b_neutral", "x": 540, "y": 840, "s": .95, "in": "b6:tres", "fx_in": "grow", "idle": "float",
         "swaps": [{"at": "b6:oscuro", "a": "tres2b_cool", "fx": "punch"}]},
        cartel("EL MÁS OSCURO", 540, 1280, "b6:oscuro", size=86, estilo="cartel_negro", idle="breathe"),
    ]})

# ------------------------------------------------------------ 5. tamaño de Júpiter, 1 %, carbón
escenas.append({
    "nombre": "tres_jupiter_luz", "beats": [7, 8], "fondo": "fondo_espacio_rojo",
    "sonidos": [{"at": "b8:luz", "s": "whoosh_suave"}],
    "elementos": [
        estrellas(6),
        {"a": "tres2b_cool", "x": 540, "y": 820, "s": .75, "idle": "float",
         "keys": [{"at": "b7:tamaño", "dur": .45, "x": 290, "s": .5},
                  {"at": "b8:refleja", "dur": .5, "x": 600, "y": 860, "s": .7}],
         "swaps": [{"at": "b8:carbón", "a": "tres2b_contento", "fx": "punch"}]},
        {"a": "jupiter_neutral", "x": 790, "y": 820, "s": .5, "in": "b7:júpiter-0.15", "fx_in": "slide_left", "idle": "float",
         "out": "b8:refleja", "fx_out": "slide_right"},
        cartel("=", 540, 820, "b7:júpiter+0.25", size=120, estilo="cartel", out="b8:refleja", fx_out="pop"),
        cartel("MISMO TAMAÑO", 540, 1190, "b7:júpiter+0.3", size=74, estilo="cartel", out="b8:refleja", fx_out="pop"),
        {"a": "halo_amarillo", "x": 170, "y": 560, "s": .55, "alpha": .9, "in": "b8:refleja", "fx_in": "fade", "idle": "latido"},
        {"a": "estrella", "x": 170, "y": 560, "s": .6, "in": "b8:refleja", "fx_in": "pop", "idle": "pulse", "z": 2},
        {"a": "rayo_luz", "x": 200, "y": 580, "r": 26, "s": .85, "in": "b8:luz-0.3", "fx_in": "wipe", "z": -1, "sfx": "none",
         "idle": {"fx": "latido", "fuerza": .5}},
        cartel("1%", 830, 560, "b8:1", size=150, estilo="cartel_amarillo", idle="pulse"),
        cartel("REFLEJA", 830, 420, "b8:1+0.15", size=56, estilo="cartel"),
        {"a": "carbon", "x": 800, "y": 1180, "s": .62, "in": "b8:carbón", "fx_in": "jump", "idle": "breathe",
         "swaps": [{"at": "b8:carbón+0.8", "a": "carbon_sorpresa", "fx": "punch"}]},
        cartel("¡MÁS NEGRO!", 330, 1240, "b8:negro", size=74, estilo="cartel_negro", r=-3),
    ]})

# ------------------------------------------------------------ 6. brilla como una brasa
escenas.append({
    "nombre": "tres_brasa", "beats": [9], "fondo": "fondo_espacio_rojo",
    "sonidos": [{"at": "b9:brilla", "s": "brillo"}, {"at": "b9:brasa", "s": "pop"}],
    "elementos": [
        estrellas(7),
        {"a": "halo_rojo", "x": 560, "y": 800, "s": 1.05, "alpha": 0, "idle": {"fx": "latido", "fuerza": 1.1, "vel": 1.1},
         "keys": [{"at": "b9:brilla", "dur": .9, "alpha": 1}]},
        {"a": "tres2b_cool", "x": 560, "y": 800, "s": .8, "idle": "float",
         "keys": [{"at": "b9:invisible", "dur": .5, "alpha": .3}, {"at": "b9:brilla", "dur": .5, "alpha": 1}],
         "swaps": [{"at": "b9:no", "a": "tres2b_sorpresa"}, {"at": "b9:brilla", "a": "tres2b_brasa", "fx": "punch"}]},
        cartel("¿INVISIBLE?", 560, 1240, "b9:invisible", size=74, estilo="cartel", out="b9:1000", fx_out="pop"),
        {"a": "termometro_00", "x": 140, "y": 1250, "s": .75, "in": "b9:casi", "fx_in": "pop",
         "seq": {"frames": [f"termometro_{i:02d}" for i in range(11)], "at": "b9:1000", "dur": .7}},
        cartel("1000 °C", 470, 1220, "b9:1000", size=92, estilo="cartel_rojo", idle="pulse"),
        {"a": "halo_rojo", "x": 830, "y": 1180, "s": .5, "alpha": .9, "in": "b9:brasa", "fx_in": "fade", "idle": "latido"},
        {"a": "brasa", "x": 830, "y": 1180, "s": .55, "in": "b9:brasa", "fx_in": "jump", "idle": "breathe"},
    ]})

# ------------------------------------------------------------ 7. 55 Cancri e presentación
escenas.append({
    "nombre": "cancri_intro", "beats": [10], "fondo": "fondo_espacio_violeta", "flash": True,
    "sonidos": [{"at": "b10:diamante", "s": "brillo"}],
    "elementos": [
        estrellas(8),
        {"a": "halo_rojo", "x": 540, "y": 820, "s": .95, "alpha": .35, "idle": "latido"},
        {"a": "cancri_neutral", "x": 540, "y": 820, "s": .95, "in": "b10:55", "fx_in": "grow", "idle": "float",
         "swaps": [{"at": "b10:diamante", "a": "cancri_contento", "fx": "punch"}]},
        {"a": "halo_celeste", "x": 790, "y": 1190, "s": .5, "alpha": .9, "in": "b10:diamante", "fx_in": "fade", "idle": "latido"},
        {"a": "diamante", "x": 790, "y": 1190, "s": .6, "in": "b10:diamante", "fx_in": "pop", "idle": "float", "sfx": "none"},
        {"a": "brillo", "x": 660, "y": 1110, "s": .45, "in": "b10:diamante+0.15", "fx_in": "pop", "idle": "pulse", "sfx": "none"},
        {"a": "brillo", "x": 920, "y": 1290, "s": .35, "in": "b10:diamante+0.3", "fx_in": "pop", "idle": "pulse", "sfx": "none"},
    ]})

# ------------------------------------------------------------ 8. doble que la Tierra, año de 18 h
escenas.append({
    "nombre": "cancri_tierra_reloj", "beats": [11, 12], "fondo": "fondo_espacio_violeta",
    "sonidos": [{"at": "b12:año", "s": "tictac"}, {"at": "b12:dura", "s": "tictac", "vol": .8}],
    "elementos": [
        estrellas(9),
        {"a": "cancri_neutral", "x": 340, "y": 820, "s": .78, "idle": "float",
         "swaps": [{"at": "b12:solo", "a": "cancri_sorpresa", "fx": "punch"}]},
        {"a": "tierra", "x": 810, "y": 900, "s": .39, "in": "b11:tierra", "fx_in": "pop", "idle": "float",
         "out": "b12:año", "fx_out": "pop"},
        cartel("×2", 760, 610, "b11:doble", size=120, estilo="cartel_amarillo", idle="pulse", out="b12:año", fx_out="pop"),
        {"a": "reloj", "x": 790, "y": 900, "s": .75, "in": "b12:año", "fx_in": "pop", "idle": "shake"},
        {"a": "reloj_aguja", "x": 790, "y": 900, "s": .75, "z": 1, "in": "b12:año", "fx_in": "pop", "sfx": "none",
         "idle": {"fx": "spin", "vel": 900}},
        cartel("1 AÑO = 18 h", 600, 1290, "b12:18", size=92, estilo="cartel_amarillo", idle="pulse"),
    ]})

# ------------------------------------------------------------ 9. interior de diamante
escenas.append({
    "nombre": "cancri_interior", "beats": [13, 14], "fondo": "fondo_espacio_violeta",
    "sonidos": [{"at": "b13:presión", "s": "zumbido", "vol": .7}, {"at": "b14:diamante", "s": "brillo"},
                {"at": "b14:diamante+0.5", "s": "ding", "vol": .5}],
    "camara": {"keys": [{"at": "b14:interior", "dur": .9, "zoom": 1.22, "x": 620, "y": 900}]},
    "elementos": [
        estrellas(10),
        {"a": "halo_rojo", "x": 540, "y": 820, "s": 1.0, "alpha": 0, "idle": {"fx": "latido", "vel": 1.6},
         "keys": [{"at": "b13:calor", "dur": .5, "alpha": .9}, {"at": "b14:interior", "dur": .4, "alpha": 0}]},
        {"a": "halo_celeste", "x": 620, "y": 900, "s": .7, "alpha": 0, "idle": "latido",
         "keys": [{"at": "b14:interior+0.3", "dur": .6, "alpha": 1}]},
        {"a": "cancri_neutral", "x": 540, "y": 820, "s": .85, "idle": "float",
         "swaps": [{"at": "b13:presión", "a": "cancri_sorpresa", "fx": "punch"},
                   {"at": "b14:interior", "a": "cancri_corte", "fx": "punch"}],
         "keys": [{"at": "b13:presión", "dur": .3, "s": .78}, {"at": "b14:interior", "dur": .4, "s": .9}]},
        {"a": "atomo_c", "x": 170, "y": 560, "s": .75, "in": "b13:carbono", "fx_in": "pop", "idle": {"fx": "spin", "vel": 40},
         "out": "b13:presión", "fx_out": "pop"},
        {"a": "atomo_c", "x": 900, "y": 600, "s": .6, "in": "b13:carbono+0.12", "fx_in": "pop", "idle": {"fx": "spin", "vel": -50},
         "out": "b13:presión", "fx_out": "pop"},
        {"a": "atomo_c", "x": 820, "y": 1160, "s": .65, "in": "b13:carbono+0.24", "fx_in": "pop", "idle": {"fx": "spin", "vel": 45},
         "out": "b13:presión", "fx_out": "pop"},
        {"a": "flecha_roja", "x": 540, "y": 360, "s": .6, "r": 0, "in": "b13:presión", "fx_in": "pop", "idle": "work",
         "keys": [{"at": "b13:presión+0.2", "dur": .4, "y": 400, "ease": "back"}], "out": "b14:interior", "fx_out": "pop"},
        {"a": "flecha_roja", "x": 120, "y": 820, "s": .6, "r": -90, "in": "b13:presión+0.08", "fx_in": "pop", "sfx": "none",
         "keys": [{"at": "b13:presión+0.2", "dur": .4, "x": 160, "ease": "back"}], "idle": "shake", "out": "b14:interior", "fx_out": "pop"},
        {"a": "flecha_roja", "x": 960, "y": 820, "s": .6, "r": 90, "in": "b13:presión+0.16", "fx_in": "pop", "sfx": "none",
         "keys": [{"at": "b13:presión+0.2", "dur": .4, "x": 920, "ease": "back"}], "idle": "shake", "out": "b14:interior", "fx_out": "pop"},
        {"a": "llama", "x": 300, "y": 1290, "s": .7, "in": "b13:calor", "fx_in": "grow", "idle": "wiggle",
         "out": "b14:interior", "fx_out": "pop"},
        {"a": "llama", "x": 540, "y": 1310, "s": .85, "in": "b13:calor+0.1", "fx_in": "grow", "idle": "wiggle", "sfx": "none",
         "out": "b14:interior", "fx_out": "pop"},
        {"a": "llama", "x": 780, "y": 1290, "s": .7, "in": "b13:calor+0.2", "fx_in": "grow", "idle": "wiggle", "sfx": "none",
         "out": "b14:interior", "fx_out": "pop"},
        {"a": "brillo", "x": 760, "y": 1000, "s": .5, "in": "b14:diamante", "fx_in": "pop", "idle": "pulse", "z": 5},
        {"a": "brillo", "x": 600, "y": 1150, "s": .35, "in": "b14:diamante+0.12", "fx_in": "pop", "idle": "pulse", "z": 5, "sfx": "none"},
        {"a": "brillo", "x": 880, "y": 830, "s": .3, "in": "b14:diamante+0.24", "fx_in": "pop", "idle": "pulse", "z": 5, "sfx": "none"},
        {"a": "vos_astro_pulgar", "x": 310, "y": 1250, "s": .4, "in": "b14:podría", "fx_in": "jump", "idle": "breathe", "z": 6},
        cartel("¡DIAMANTE!", 620, 470, "b14:diamante", size=96, estilo="cartel_celeste", idle="pulse"),
    ]})


def planeta_persistente(num, titulo, desde, hasta):
    return [
        {"texto": {"t": str(num), "estilo": "num"}, "x": 130, "y": 250, "in": desde, "out": hasta, "fx_in": "pop",
         "fx_out": "pop", "idle": "breathe"},
        {"texto": {"t": titulo, "estilo": "titulo"}, "x": 590, "y": 250, "in": desde + "+0.15", "out": hasta,
         "fx_in": "slide_left", "fx_out": "fade"},
    ]


doc = {
    "cola": 1.4,
    "volumen_efectos": .5,
    "subtitulos": {"activos": True, "y": 1470, "size": 76},
    "estilos": {
        "titulo": {"size": 84, "color": "#FFFFFF", "stroke": 12},
        "num": {"size": 96, "color": "#24201F", "box": "#FFD23F", "circle": True, "pad": [22, 14]},
        "pregunta": {"size": 150, "color": "#FFD23F", "stroke": 12},
        "cartel": {"size": 90, "color": "#24201F", "box": "#FFFFFF"},
        "cartel_rojo": {"size": 90, "color": "#FFFFFF", "box": "#FF5D5D", "stroke": 9},
        "cartel_amarillo": {"size": 90, "color": "#24201F", "box": "#FFD23F"},
        "cartel_celeste": {"size": 90, "color": "#24201F", "box": "#9ADCFF"},
        "cartel_negro": {"size": 90, "color": "#FFFFFF", "box": "#2B2730", "stroke": 0},
    },
    "narracion": [{"texto": t} for t in narracion],
    "persistentes": (planeta_persistente(1, "HD 189733b", "b1", "e4")
                     + planeta_persistente(2, "TrES-2b", "b6", "e7")
                     + planeta_persistente(3, "55 Cancri e", "b10", "fin")),
    "escenas": escenas,
}
if "--sin-audio" not in sys.argv:
    doc["audio_voz"] = "audio/voz.wav"
    doc["palabras_json"] = "audio/palabras.json"

# el texto de la narración tiene que ser el guion, palabra por palabra
guion = " ".join(open(os.path.join(AQUI, "guion.txt")).read().split())
assert " ".join(narracion) == guion, "la narración no coincide con guion.txt"

json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
print("ok", OUT)
