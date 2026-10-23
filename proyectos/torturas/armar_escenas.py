"""Genera escenas.json (python3 armar_escenas.py [--sin-audio]). Editá acá y volvé a correrlo."""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "escenas.json")

narracion = [
    "Te cuento 3 torturas extremas de la Edad Media.",
    "1. El Escafismo (o tortura de las barcas):",
    "El prisionero era atado desnudo entre dos barcas, dejando fuera solo su cabeza y extremidades.",
    "Se le obligaba a consumir leche y miel para causarle diarrea masiva,",
    "y luego se le untaba la piel con dulce.",
    "Al dejarlo flotando en un pantano, miles de insectos eran atraídos por el olor,",
    "anidando en su cuerpo y devorándolo vivo por dentro y por fuera durante días de agonía.",
    "2. La Sierra:",
    "Este método se reservaba principalmente para los acusados de traición o brujería por su alto impacto visual y psicológico.",
    "Consistía en colgar al prisionero boca abajo, lo que garantizaba que el cerebro recibiera suficiente flujo de sangre "
    "para mantenerlo consciente el mayor tiempo posible.",
    "Dos verdugos comenzaban a serrar el cuerpo por la mitad desde la pelvis,",
    "y la víctima solía sobrevivir sintiendo todo el proceso hasta llegar al ombligo.",
    "3. El Desollamiento:",
    "Esta brutal técnica consistía en fijar firmemente al prisionero a una mesa o poste para retirar la piel de su cuerpo "
    "por completo con cuchillos afilados.",
    "Los verdugos solían comenzar por el rostro y la cabeza, manteniendo a la víctima con vida la mayor cantidad de tiempo "
    "posible durante el proceso.",
    "Al terminar, la persona quedaba completamente expuesta y moría horas o días después debido al shock térmico, "
    "la pérdida de sangre o infecciones masivas.",
]


def antorchas():
    """Dos antorchas en la pared de la mazmorra, con resplandor que late."""
    out = []
    for x in (110, 970):
        out += [{"a": "halo_amarillo", "x": x, "y": 690, "s": .55, "alpha": .7, "z": -9,
                 "idle": {"fx": "latido", "vel": 2.2, "fuerza": .6}},
                {"a": "antorcha", "x": x, "y": 900, "s": .8, "z": -8, "idle": {"fx": "wiggle", "fuerza": .3}}]
    return out


def chispas(semilla):
    """Polvo/brasas flotando en la mazmorra."""
    return {"particulas": {"a": "punto_estrella", "n": 16, "semilla": semilla, "zona": [0, 300, 1080, 1700],
                           "vy": [-60, -25], "vx": [-10, 10], "s": [.4, .9], "alpha": [.25, .6], "titila": .6,
                           "ondula": [12, .4]}, "z": -7}


def moscas(at, n, zona, semilla=5, out=None, s=(.4, .7), z=10):
    e = {"particulas": {"a": "mosca", "n": n, "semilla": semilla, "zona": list(zona), "vx": [-50, 50], "vy": [-30, 30],
                        "s": list(s), "r": [-15, 15], "ondula": [45, .7]},
         "in": at, "fx_in": "fade", "dur_in": .5, "z": z}
    if out:
        e.update(out=out, fx_out="fade")
    return e


def cartel(t, x, y, at, size=84, estilo="cartel", **kw):
    e = {"texto": {"t": t, "estilo": estilo, "size": size}, "x": x, "y": y, "in": at, "fx_in": "pop", "z": 20}
    e.update(kw)
    return e


def censura(at, x, y, size=104, r=-6, **kw):
    e = {"texto": {"t": "CENSURADO", "estilo": "censura", "size": size}, "x": x, "y": y, "r": r, "in": at,
         "fx_in": "pop", "z": 30, "sfx": "golpe"}
    e.update(kw)
    return e


escenas = []

# ------------------------------------------------------------ 0. gancho
escenas.append({
    "nombre": "gancho", "beats": [0], "fondo": "fondo_mazmorra",
    "sonidos": [{"at": "b0:3", "s": "golpe"}, {"at": "b0:media", "s": "zumbido", "vol": .8}],
    "camara": {"keys": [{"at": "b0", "dur": 3.2, "zoom": 1.07, "y": 900, "ease": "linear"}]},
    "elementos": antorchas() + [
        chispas(1),
        {"texto": {"t": "3 TORTURAS\nEXTREMAS", "estilo": "titulo_rojo", "size": 112}, "x": 540, "y": 330,
         "in": "b0:3", "fx_in": "pop", "idle": "breathe", "sfx": "none"},
        {"a": "barcas_miedo", "x": 300, "y": 580, "s": .42, "r": -6, "in": "b0:torturas", "fx_in": "pop", "idle": "float"},
        {"a": "sierra", "x": 600, "y": 530, "s": .4, "r": 12, "in": "b0:torturas+0.15", "fx_in": "pop", "idle": "sway"},
        {"a": "cuchillo", "x": 800, "y": 600, "s": .58, "r": -18, "in": "b0:torturas+0.3", "fx_in": "pop", "idle": "sway"},
        {"a": "vos_neutral", "x": 380, "y": 1330, "s": .62, "in": "b0+0.1", "fx_in": "jump", "idle": "breathe", "blink": True,
         "swaps": [{"at": "b0:extremas", "a": "vos_sorpresa", "fx": "punch"}]},
        {"a": "verdugo_risa", "x": 790, "y": 1330, "s": .58, "in": "b0:edad", "fx_in": "slide_left", "idle": "breathe",
         "swaps": [{"at": "b0:media+0.4", "a": "verdugo"}]},
    ]})

# ------------------------------------------------------------ 1. Escafismo: presentación y barcas
escenas.append({
    "nombre": "escafismo_intro", "beats": [1, 2], "fondo": "fondo_pantano", "flash": True,
    "sonidos": [{"at": "b2:desnudo", "s": "boing", "vol": .6}],
    "elementos": [
        {"a": "vos_mira", "x": 180, "y": 1330, "s": .45, "in": "b1+0.1", "fx_in": "jump", "idle": "breathe", "blink": True,
         "swaps": [{"at": "b2:desnudo", "a": "vos_sorpresa", "fx": "punch"}]},
        cartel("(TORTURA DE LAS BARCAS)", 560, 520, "b1:tortura", size=60, out="b2:barcas", fx_out="pop"),
        {"a": "prisionero_miedo", "x": 590, "y": 1330, "s": .6, "in": "b2:prisionero", "fx_in": "jump", "idle": "shake",
         "blink": True, "swaps": [{"at": "b2:desnudo", "a": "prisionero_desnudo", "fx": "punch"}],
         "out": "b2:barcas", "fx_out": "pop"},
        censura("b2:desnudo", 590, 1240, size=30, r=0, sfx="none", idle="shake", out="b2:barcas", fx_out="pop"),
        {"a": "barcas_miedo", "x": 580, "y": 820, "s": .85, "in": "b2:barcas", "fx_in": "drop", "idle": "sway"},
        {"a": "flecha_roja", "x": 357, "y": 610, "s": .35, "in": "b2:cabeza", "fx_in": "pop", "idle": "work"},
        {"a": "flecha_roja", "x": 540, "y": 590, "s": .3, "in": "b2:extremidades", "fx_in": "pop", "idle": "work", "sfx": "none"},
        {"a": "flecha_roja", "x": 710, "y": 590, "s": .3, "in": "b2:extremidades+0.1", "fx_in": "pop", "idle": "work", "sfx": "none"},
        {"a": "flecha_roja", "x": 865, "y": 650, "s": .3, "in": "b2:extremidades+0.2", "fx_in": "pop", "idle": "work", "sfx": "none"},
    ]})

# ------------------------------------------------------------ 2. leche, miel y dulce
escenas.append({
    "nombre": "escafismo_miel", "beats": [3, 4], "fondo": "fondo_pantano",
    "sonidos": [{"at": "b3:causarle", "s": "whoosh_suave"}, {"at": "b3:diarrea", "s": "boing"}],
    "elementos": [
        {"a": "vos_neutral", "x": 180, "y": 1330, "s": .45, "idle": "breathe", "blink": True,
         "swaps": [{"at": "b3:diarrea", "a": "vos_asco", "fx": "punch"}]},
        {"a": "barcas_nervio", "x": 580, "y": 820, "s": .85, "idle": "sway",
         "swaps": [{"at": "b3:diarrea", "a": "barcas_asco", "fx": "punch"},
                   {"at": "b4:untaba", "a": "barcas_miel", "fx": "punch"}]},
        {"a": "jarra_leche", "x": 470, "y": 1190, "s": .5, "in": "b3:leche", "fx_in": "pop",
         "keys": [{"at": "b3:causarle", "dur": .5, "x": 380, "y": 830, "s": .2, "alpha": 0, "ease": "in"}]},
        {"a": "tarro_miel", "x": 740, "y": 1190, "s": .5, "in": "b3:miel", "fx_in": "pop",
         "keys": [{"at": "b3:causarle+0.1", "dur": .5, "x": 380, "y": 830, "s": .2, "alpha": 0, "ease": "in"}]},
        cartel("¡DIARREA!", 620, 1170, "b3:diarrea", size=96, estilo="cartel_marron", r=-4, idle="shake", out="b4:untaba",
               fx_out="pop"),
        {"a": "olor", "x": 540, "y": 690, "s": .6, "in": "b3:diarrea", "fx_in": "fade", "idle": "sway"},
        {"a": "olor", "x": 760, "y": 680, "s": .5, "in": "b3:masiva", "fx_in": "fade", "idle": "sway", "flip": True},
        {"a": "tarro_miel", "x": 820, "y": 1190, "s": .55, "r": -15, "in": "b4:untaba", "fx_in": "pop", "idle": "wiggle"},
        cartel("+ MIEL EN LA PIEL", 560, 520, "b4:piel", size=66, estilo="cartel_amarillo"),
    ]})

# ------------------------------------------------------------ 3. el pantano y los insectos
escenas.append({
    "nombre": "escafismo_insectos", "beats": [5, 6], "fondo": "fondo_pantano",
    "sonidos": [{"at": "b5:insectos", "s": "mosca"}, {"at": "b5:insectos+1.4", "s": "mosca"},
                {"at": "b6", "s": "mosca"}, {"at": "b6+1.4", "s": "mosca"}, {"at": "b6+2.8", "s": "mosca"},
                {"at": "b6:días", "s": "golpe", "vol": .8}],
    "camara": {"keys": [{"at": "b6", "dur": 4.5, "zoom": 1.15, "x": 560, "y": 1050, "ease": "inout"}]},
    "elementos": [
        {"a": "barcas_miel", "x": 560, "y": 1170, "s": .8, "in": "b5", "fx_in": "slide_up", "idle": ["float", "sway"],
         "swaps": [{"at": "b6:devorándolo", "a": "barcas_miel_dolor", "fx": "punch"},
                   {"at": "b6:dentro", "a": "barcas_podrido1", "fx": "punch"},
                   {"at": "b6:días", "a": "barcas_podrido2", "fx": "punch"}]},
        {"a": "olor", "x": 420, "y": 1030, "s": .6, "in": "b5:olor", "fx_in": "fade", "idle": "sway"},
        {"a": "olor", "x": 700, "y": 1020, "s": .55, "in": "b5:olor+0.15", "fx_in": "fade", "idle": "sway", "flip": True},
        moscas("b5:insectos", 12, (160, 560, 960, 1150), semilla=5),
        moscas("b6:anidando", 22, (240, 900, 900, 1300), semilla=6, s=(.3, .55), z=11),
        moscas("b6:dentro", 26, (200, 950, 940, 1350), semilla=7, s=(.25, .5), z=12),
        cartel("MILES DE INSECTOS", 540, 480, "b5:miles", size=74, estilo="cartel_verde", out="b6", fx_out="pop"),
        cartel("DÍAS DE AGONÍA", 540, 650, "b6:días", size=86, estilo="cartel_rojo", idle="pulse"),
    ]})

# ------------------------------------------------------------ 4. La Sierra: presentación, traición y brujería
escenas.append({
    "nombre": "sierra_intro", "beats": [7, 8], "fondo": "fondo_mazmorra", "flash": True,
    "sonidos": [{"at": "b7:sierra", "s": "sierra"}],
    "elementos": antorchas() + [
        chispas(2),
        {"a": "sierra", "x": 540, "y": 760, "s": .9, "r": -8, "in": "b7:sierra", "fx_in": "pop", "idle": "sway",
         "keys": [{"at": "b8:método", "dur": .5, "y": 470, "s": .7, "r": 0}]},
        {"a": "verdugo_frente", "x": 540, "y": 1330, "s": .62, "in": "b8:método", "fx_in": "jump", "idle": "breathe",
         "swaps": [{"at": "b8:psicológico", "a": "verdugo_risa", "fx": "punch"}]},
        cartel("TRAICIÓN", 270, 700, "b8:traición", size=66, estilo="cartel_rojo"),
        {"a": "corona", "x": 270, "y": 870, "s": .6, "r": -10, "in": "b8:traición", "fx_in": "pop", "idle": "float", "sfx": "none"},
        cartel("BRUJERÍA", 810, 700, "b8:brujería", size=66, estilo="cartel_violeta"),
        {"a": "sombrero_bruja", "x": 810, "y": 870, "s": .6, "r": 10, "in": "b8:brujería", "fx_in": "pop", "idle": "float",
         "sfx": "none"},
    ]})

# ------------------------------------------------------------ 5. boca abajo, sangre al cerebro
escenas.append({
    "nombre": "sierra_colgado", "beats": [9], "fondo": "fondo_mazmorra",
    "sonidos": [{"at": "b9:consciente", "s": "ding", "vol": .5}],
    "elementos": antorchas() + [
        chispas(3),
        {"a": "cuerda", "x": 438, "y": 0, "sy": 1.223, "in": "b9:colgar", "fx_in": "drop", "sfx": "none"},
        {"a": "cuerda", "x": 642, "y": 0, "sy": 1.223, "in": "b9:colgar", "fx_in": "drop", "sfx": "none"},
        {"a": "colgado_v_miedo", "x": 540, "y": 856, "s": .6, "in": "b9:colgar", "fx_in": "drop",
         "idle": {"fx": "sway", "fuerza": .6}},
        {"a": "cerebro", "x": 830, "y": 1110, "s": .42, "in": "b9:cerebro", "fx_in": "pop", "idle": "pulse"},
        {"a": "gota", "x": 250, "y": 760, "s": .55, "in": "b9:sangre", "fx_in": "drop", "idle": "bob"},
        {"a": "flecha_roja", "x": 250, "y": 960, "s": .4, "in": "b9:sangre+0.2", "fx_in": "pop", "idle": "work", "sfx": "none"},
        cartel("SANGRE AL CEREBRO", 540, 600, "b9:sangre", size=64, estilo="cartel_rojo", out="b9:consciente", fx_out="pop"),
        cartel("¡CONSCIENTE!", 540, 600, "b9:consciente", size=86, estilo="cartel_amarillo", idle="pulse"),
    ]})

# ------------------------------------------------------------ 6. los dos verdugos y la sierra
escenas.append({
    "nombre": "sierra_verdugos", "beats": [10, 11], "fondo": "fondo_mazmorra",
    "sonidos": [{"at": "b10:serrar", "s": "sierra"}, {"at": "b10:serrar+1.1", "s": "sierra"},
                {"at": "b10:serrar+2.2", "s": "sierra"}, {"at": "b11:ombligo", "s": "golpe", "vol": .8}],
    "camara": {"temblor": [{"from": "b10:cuerpo", "to": "b11", "fuerza": .8}]},
    "elementos": antorchas() + [
        {"a": "cuerda", "x": 438, "y": 0, "sy": 1.223, "keys": [{"at": "b11:proceso", "dur": .6, "x": 388, "ease": "back"}]},
        {"a": "cuerda", "x": 642, "y": 0, "sy": 1.223, "keys": [{"at": "b11:proceso", "dur": .6, "x": 692, "ease": "back"}]},
        {"a": "colgado_v_miedo", "x": 540, "y": 856, "s": .6, "idle": {"fx": "sway", "fuerza": .3},
         "swaps": [{"at": "b10:serrar", "a": "colgado_v_grito", "fx": "punch"}], "out": "b11:proceso"},
        # partido en dos: cada mitad cuelga de su soga y se separa
        {"a": "colgado_mitad_izq", "x": 438, "y": 856, "s": .6, "in": "b11:proceso", "sfx": "golpe",
         "keys": [{"at": "b11:proceso", "dur": .6, "r": 20, "x": 388, "ease": "back"}], "idle": {"fx": "sway", "fuerza": .5}},
        {"a": "colgado_mitad_der", "x": 642, "y": 856, "s": .6, "in": "b11:proceso",
         "keys": [{"at": "b11:proceso", "dur": .6, "r": -20, "x": 692, "ease": "back"}], "idle": {"fx": "sway", "fuerza": .5}},
        # los verdugos sostienen la sierra por los mangos con el brazo en alto
        {"a": "verdugo_sierra", "x": 177, "y": 1330, "s": .5, "in": "b10:verdugos", "fx_in": "slide_right", "z": 2},
        {"a": "verdugo_sierra", "x": 903, "y": 1330, "s": .5, "flip": True, "in": "b10:verdugos+0.15", "fx_in": "slide_left",
         "z": 2},
        # la sierra pasa entre las piernas: va detrás del cuerpo (se ve en el hueco) y baja mientras corta
        {"a": "sierra", "x": 540, "y": 940, "s": .65, "in": "b10:comenzaban", "fx_in": "fade", "z": -1,
         "idle": {"fx": "vaiven", "fuerza": .8, "vel": 2.6, "from": "b10:serrar"},
         "keys": [{"at": "b10:serrar", "dur": 5, "y": 1040, "ease": "linear"},
                  {"at": "b11:proceso", "dur": .4, "alpha": 0}]},
        censura("b10:cuerpo", 540, 1050, size=96, r=-6, idle="shake", out="b11:proceso", fx_out="pop"),
        cartel("HASTA EL OMBLIGO", 540, 640, "b11:ombligo", size=70, estilo="cartel_rojo", idle="pulse"),
    ]})

# ------------------------------------------------------------ 7. Desollamiento: presentación y poste
escenas.append({
    "nombre": "desollamiento_intro", "beats": [12, 13], "fondo": "fondo_mazmorra", "flash": True,
    "sonidos": [{"at": "b12:desollamiento", "s": "filo"}, {"at": "b13:cuchillos", "s": "filo"}],
    "elementos": antorchas() + [
        chispas(4),
        {"a": "cuchillo", "x": 540, "y": 800, "s": 1.0, "r": -20, "in": "b12:desollamiento", "fx_in": "pop", "idle": "sway",
         "sfx": "none", "out": "b13:fijar", "fx_out": "pop"},
        {"a": "brillo", "x": 640, "y": 720, "s": .5, "in": "b12:desollamiento+0.2", "fx_in": "pop", "idle": "pulse",
         "sfx": "none", "out": "b13:fijar", "fx_out": "pop"},
        {"a": "poste", "x": 540, "y": 1330, "in": "b13:fijar", "fx_in": "drop", "z": -1},
        {"a": "prisionero_miedo", "x": 540, "y": 1330, "s": .6, "in": "b13:fijar", "fx_in": "jump", "idle": "shake",
         "blink": True, "swaps": [{"at": "b13:piel", "a": "prisionero_nervio", "fx": "punch"}]},
        {"a": "cuerdas", "x": 540, "y": 1200, "s": .6, "z": 1, "in": "b13:firmemente", "fx_in": "grow"},
        {"a": "vos_neutral", "x": 170, "y": 1330, "s": .45, "in": "b13:mesa", "fx_in": "jump", "idle": "breathe",
         "blink": True, "swaps": [{"at": "b13:piel", "a": "vos_miedo", "fx": "punch"}]},
        {"a": "verdugo", "x": 850, "y": 1330, "s": .52, "flip": True, "in": "b13:retirar", "fx_in": "slide_left", "idle": "breathe"},
        {"a": "cuchillo", "x": 760, "y": 1180, "s": .42, "r": -35, "in": "b13:cuchillos", "fx_in": "pop", "idle": "wiggle",
         "sfx": "none", "z": 3},
        cartel("CUCHILLOS AFILADOS", 540, 520, "b13:cuchillos", size=66, estilo="cartel"),
    ]})

# ------------------------------------------------------------ 8. empezaban por el rostro
escenas.append({
    "nombre": "desollamiento_rostro", "beats": [14], "fondo": "fondo_mazmorra",
    "sonidos": [{"at": "b14:rostro", "s": "filo"}, {"at": "b14:tiempo", "s": "tictac"}],
    "elementos": antorchas() + [
        {"a": "poste", "x": 540, "y": 1330, "z": -1},
        {"a": "prisionero_nervio", "x": 540, "y": 1330, "s": .6, "idle": "shake",
         "swaps": [{"at": "b14:rostro", "a": "prisionero_dolor", "fx": "punch"}]},
        {"a": "cuerdas", "x": 540, "y": 1200, "s": .6, "z": 1},
        {"a": "vos_miedo", "x": 170, "y": 1330, "s": .45, "idle": "shake", "blink": True},
        {"a": "verdugo", "x": 850, "y": 1330, "s": .52, "flip": True, "idle": "breathe",
         "keys": [{"at": "b14:comenzar", "dur": .6, "x": 760}]},
        {"a": "cuchillo", "x": 760, "y": 1180, "s": .42, "r": -35, "z": 3, "idle": "wiggle",
         "keys": [{"at": "b14:comenzar", "dur": .6, "x": 640, "y": 1000, "r": -50}]},
        censura("b14:rostro", 540, 1045, size=62, r=-5),
        {"a": "reloj", "x": 820, "y": 600, "s": .55, "in": "b14:tiempo", "fx_in": "pop", "sfx": "none"},
        {"a": "reloj_aguja", "x": 820, "y": 600, "s": .55, "z": 1, "in": "b14:tiempo", "fx_in": "pop", "sfx": "none",
         "idle": {"fx": "spin", "vel": 360}},
        cartel("¡CON VIDA!", 260, 560, "b14:vida", size=80, estilo="cartel_rojo", r=-5, idle="pulse"),
    ]})

# ------------------------------------------------------------ 9. el final: causas de muerte
escenas.append({
    "nombre": "desollamiento_final", "beats": [15], "fondo": "fondo_mazmorra",
    "sonidos": [{"at": "b15", "s": "golpe"}, {"at": "b15:moría", "s": "zumbido", "vol": .7}],
    "elementos": antorchas() + [
        chispas(5),
        {"a": "poste", "x": 540, "y": 1330, "z": -1},
        # al terminar ya está desollado (sin censura); en "moría" los ojos pasan a X
        {"a": "desollado", "x": 540, "y": 1330, "s": .6, "idle": {"fx": "shake", "fuerza": .5, "to": "b15:moría"},
         "swaps": [{"at": "b15:moría", "a": "desollado_muerto", "fx": "punch"}]},
        {"a": "cuerdas", "x": 540, "y": 1200, "s": .6, "z": 1},
        cartel("SHOCK TÉRMICO", 250, 520, "b15:shock", size=50, estilo="cartel_celeste"),
        {"a": "termometro_00", "x": 150, "y": 1250, "s": .5, "in": "b15:shock", "fx_in": "pop", "idle": "shake"},
        cartel("SANGRE", 250, 650, "b15:sangre", size=50, estilo="cartel_rojo"),
        {"a": "gota", "x": 260, "y": 810, "s": .6, "in": "b15:sangre", "fx_in": "drop", "idle": "bob"},
        cartel("INFECCIONES", 830, 520, "b15:infecciones", size=50, estilo="cartel_verde"),
        {"a": "microbio_verde", "x": 830, "y": 700, "s": .5, "in": "b15:infecciones", "fx_in": "pop", "idle": "wiggle"},
        {"particulas": {"a": ["microbio_verde", "microbio_violeta"], "n": 10, "semilla": 9, "zona": [-100, 400, 1180, 1000],
                        "vx": [-40, 40], "vy": [-20, 20], "s": [.2, .35], "ondula": [30, .5], "r": [-20, 20]},
         "in": "b15:masivas", "fx_in": "fade", "z": 5},
    ]})


def tortura_persistente(num, titulo, desde, hasta):
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
        "titulo_rojo": {"size": 100, "color": "#FF5D5D", "stroke": 12},
        "num": {"size": 96, "color": "#24201F", "box": "#FFD23F", "circle": True, "pad": [22, 14]},
        "cartel": {"size": 84, "color": "#24201F", "box": "#FFFFFF"},
        "cartel_rojo": {"size": 84, "color": "#FFFFFF", "box": "#FF5D5D", "stroke": 9},
        "cartel_amarillo": {"size": 84, "color": "#24201F", "box": "#FFD23F"},
        "cartel_celeste": {"size": 84, "color": "#24201F", "box": "#9ADCFF"},
        "cartel_verde": {"size": 84, "color": "#24201F", "box": "#8BD06A"},
        "cartel_violeta": {"size": 84, "color": "#FFFFFF", "box": "#7A5CFF", "stroke": 9},
        "cartel_marron": {"size": 84, "color": "#FFFFFF", "box": "#7A5236", "stroke": 9},
        "censura": {"size": 104, "color": "#FFFFFF", "box": "#14121A", "stroke": 0, "radius": 10},
    },
    "narracion": [{"texto": t} for t in narracion],
    "persistentes": (tortura_persistente(1, "El Escafismo", "b1", "e4")
                     + tortura_persistente(2, "La Sierra", "b7", "e7")
                     + tortura_persistente(3, "El Desollamiento", "b12", "fin")),
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
