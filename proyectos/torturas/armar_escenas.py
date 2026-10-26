"""Genera escenas.json del short de torturas (parte 2). Uso: python3 proyectos/torturas/armar_escenas.py"""
import json
OUT = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "escenas.json")

narr = [
    "¡Te muestro 3 instrumentos de tortura tan crueles que cuesta creer que existieron!",
    "Parte 2.",
    "1. La cuna de Judas.",
    "Colgaban a la persona con cuerdas y poleas justo encima de una pirámide de madera con la punta afilada.",
    "Después la bajaban de a poco, o la soltaban de golpe, y su propio peso hacía que la punta se le clavara en la entrepierna, desgarrándola por dentro.",
    "2. La garra de gato.",
    "Era una tenaza de hierro con puntas curvas y afiladas que se calentaba al rojo vivo en las brasas.",
    "Se clavaba en la espalda o el torso y se tiraba con fuerza, arrancando trozos de carne hasta dejar las costillas a la vista.",
    "3. El aplastacabezas.",
    "Un casco de metal con un tornillo gigante que apretaba el cráneo contra una barra debajo de la barbilla.",
    "Con cada vuelta de la manivela, primero se rompían los dientes, después la mandíbula, los ojos se salían de sus órbitas… y al final, cedía el cráneo.",
]

estilos = {
    "numero": {"size": 92, "color": "#FFFFFF", "box": "#FF5D5D", "circle": True, "pad": [30, 14]},
    "titulo": {"size": 66, "color": "#24201F", "box": "#FFF3DF"},
    "censura": {"size": 74, "color": "#FFFFFF", "box": "#141218", "radius": 10},
    "crack": {"size": 120, "color": "#FFD23F", "stroke": 14},
    "etiqueta": {"size": 52, "color": "#24201F", "box": "#FFD23F", "pad": [24, 12]},
}


def titulo(n, txt, b, hasta):
    return [
        {"texto": {"t": str(n), "estilo": "numero"}, "x": 120, "y": 250, "in": f"b{b}", "out": hasta,
         "fx_in": "pop", "fx_out": "pop", "idle": "breathe"},
        {"texto": {"t": txt, "estilo": "titulo"}, "x": 590, "y": 250, "in": f"b{b}+0.25", "out": hasta,
         "fx_in": "slide_left", "fx_out": "pop", "r": -2},
    ]


def vuelo(a, x0, y0, dx, alto, piso, t, dur=1.0, r=360, s0=1.0, s1=None, **kw):
    """Elemento que sale disparado: sube (ease out) y cae al piso (ease in) girando."""
    s1 = s0 if s1 is None else s1
    sube = dur * .4
    base, off = (t.rsplit("+", 1)[0], float(t.rsplit("+", 1)[1])) if "+" in t else (t, 0.0)
    el = {"a": a, "x": x0, "y": y0, "s": s0, "in": t, "fx_in": "pop", "sfx": "none", "z": 9,
          "keys": [{"at": t, "dur": sube, "x": x0 + dx * .45, "y": y0 - alto, "r": r * .4, "s": s1, "ease": "out"},
                   {"at": f"{base}+{off + sube:.2f}", "dur": dur - sube, "x": x0 + dx, "y": piso, "r": r, "ease": "in"}]}
    el.update(kw)
    return el


persist = []
for x in (110, 970):
    persist.append({"a": "antorcha_0", "x": x, "y": 760, "s": .9, "z": -20, "in": 0, "out": "fin",
                    "loop": {"frames": ["antorcha_0", "antorcha_1"], "fps": 5}, "sfx": "none"})
persist += titulo(1, "LA CUNA DE JUDAS", 2, "b5-0.15")
persist += titulo(2, "LA GARRA DE GATO", 5, "b8-0.15")
persist += titulo(3, "EL APLASTACABEZAS", 8, "fin")

# ---------------------------------------------------------------- escena 0: gancho
e0 = {"nombre": "gancho", "beats": [0, 1], "fondo": "fondo_mazmorra", "elementos": [
    {"a": "vos_miedo", "x": 290, "y": 1330, "s": .7, "in": "b0", "fx_in": "jump", "blink": True, "idle": "breathe",
     "swaps": [{"at": "b0:crueles", "a": "vos_grito", "fx": "punch"}, {"at": "b0:cuesta", "a": "vos_miedo", "fx": "punch"}],
     "keys": [{"at": "b0:crueles", "dur": .4, "x": 270}]},
    {"a": "verdugo", "x": 790, "y": 1330, "s": .7, "in": "b0:tortura", "fx_in": "slide_left", "idle": "breathe",
     "swaps": [{"at": "b0:existieron", "a": "verdugo_risa", "fx": "punch"}]},
    {"a": "piramide", "x": 200, "y": 570, "s": .5, "anchor": [.5, .5], "in": "b0:instrumentos", "out": "b1", "fx_in": "pop", "fx_out": "pop", "idle": "bob"},
    {"a": "garra", "x": 540, "y": 570, "s": .5, "anchor": [.5, .5], "r": -12, "in": "b0:instrumentos+0.25", "out": "b1", "fx_in": "pop", "fx_out": "pop", "idle": "bob"},
    {"a": "aplasta_icono", "x": 880, "y": 570, "s": .31, "anchor": [.5, .5], "in": "b0:instrumentos+0.5", "out": "b1", "fx_in": "pop", "fx_out": "pop", "idle": "bob"},
    {"a": "sudor", "x": 370, "y": 830, "s": 1.4, "in": "b0:crueles", "out": "b0:cuesta", "fx_in": "pop", "fx_out": "fade",
     "keys": [{"at": "b0:crueles", "dur": .8, "y": 900, "ease": "in"}], "sfx": "none"},
    {"texto": {"t": "PARTE 2", "size": 150, "color": "#FFFFFF", "box": "#FF5D5D"}, "x": 540, "y": 640, "r": -6,
     "in": "b1", "fx_in": "pop", "sfx": "golpe", "idle": {"fx": "pulse", "fuerza": .6}},
]}

# ---------------------------------------------------------------- escena 1: la cuna de Judas
PX = 620
pres = {"a": "preso_colgado", "x": PX, "y": 870, "s": .5, "z": 3, "in": "b3:colgaban", "fx_in": "slide_down", "dur_in": .6,
        "idle": [{"fx": "sway", "fuerza": 1.5, "to": "b4:clavara"}, {"fx": "shake", "fuerza": 1.6, "from": "b4:clavara"}],
        "swaps": [{"at": "b4:clavara", "a": "preso_colgado_grito", "fx": "punch"}],
        "keys": [{"at": "b4:poco-0.4", "dur": 1.2, "y": 915, "ease": "inout"},
                 {"at": "b4:golpe", "dur": .22, "y": 985, "ease": "in", "sfx": "whoosh"},
                 {"at": "b4:clavara", "dur": .16, "y": 1035, "ease": "in", "sfx": "golpe"}]}
e1 = {"nombre": "cuna", "beats": [2, 3, 4], "fondo": "fondo_mazmorra", "flash": True, "elementos": [
    {"a": "piramide", "x": PX, "y": 1330, "s": .7, "z": 1, "in": "b2:cuna", "fx_in": "drop",
     "keys": [{"at": "b3:pirámide", "dur": .18, "s": .78, "ease": "out", "sfx": "boing"}, {"at": "b3:pirámide+0.18", "dur": .3, "s": .7, "ease": "out"}]},
    {"a": "brillo", "x": PX, "y": 958, "s": .7, "z": 2, "in": "b3:afilada", "out": "b3:afilada+0.9", "fx_in": "pop", "fx_out": "pop",
     "sfx": "ding", "idle": {"fx": "spin", "vel": 90}},
    {"a": "polea", "x": PX, "y": 445, "s": .8, "z": 4, "in": "b3:poleas", "fx_in": "drop",
     "keys": [{"at": "b4:poco-0.4", "dur": 1.2, "r": 0}]},
    pres,
    {"texto": {"t": "CUERDAS", "estilo": "etiqueta"}, "x": 300, "y": 520, "r": -6, "in": "b3:cuerdas", "out": "b3:pirámide", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "POLEAS", "estilo": "etiqueta"}, "x": 300, "y": 620, "r": 5, "in": "b3:poleas", "out": "b3:pirámide", "fx_in": "pop", "fx_out": "pop"},
    {"a": "vos_miedo", "x": 200, "y": 1330, "s": .55, "z": 5, "in": "b3:pirámide", "fx_in": "slide_right", "blink": True, "idle": "breathe",
     "swaps": [{"at": "b4:clavara", "a": "vos_grito", "fx": "punch"}]},
    {"texto": {"t": "DE A POCO...", "estilo": "etiqueta"}, "x": 300, "y": 560, "r": -5, "in": "b4:poco", "out": "b4:golpe", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "¡DE GOLPE!", "size": 64, "color": "#FFFFFF", "box": "#FF5D5D"}, "x": 300, "y": 560, "r": 5, "in": "b4:golpe", "out": "b4:clavara", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "CENSURADO", "estilo": "censura"}, "x": PX, "y": 985, "r": -7, "z": 8, "in": "b4:clavara+0.1", "fx_in": "pop",
     "sfx": "crack", "idle": {"fx": "pulse", "fuerza": .5}},
    {"a": "exclamacion", "x": 330, "y": 820, "s": .7, "r": -10, "in": "b4:desgarrándola", "fx_in": "pop", "idle": "wiggle"},
]}

# ---------------------------------------------------------------- escena 2: la garra
e2 = {"nombre": "garra", "beats": [5, 6], "fondo": "fondo_mazmorra", "flash": True,
      "sonidos": [{"at": "b6:calentaba", "s": "fuego", "vol": .8}, {"at": "b6:rojo", "s": "fuego", "vol": .8}],
      "elementos": [
    {"a": "garra", "x": 420, "y": 700, "s": 1.1, "r": -8, "z": 1, "in": "b5:garra", "fx_in": "pop", "idle": {"fx": "float", "to": "b6:calentaba"},
     "swaps": [{"at": "b6:rojo", "a": "garra_roja", "fx": "punch"}],
     "keys": [{"at": "b6:tenaza", "dur": .2, "s": 1.2, "ease": "out"}, {"at": "b6:tenaza+0.2", "dur": .3, "s": 1.1},
              {"at": "b6:calentaba", "dur": .6, "x": 440, "y": 990, "r": 32, "ease": "inout", "sfx": "whoosh"},
              {"at": "b6:brasas", "dur": .5, "x": 420, "y": 700, "r": -8, "ease": "back"}]},
    {"a": "brillo", "x": 670, "y": 720, "s": .6, "z": 2, "in": "b6:afiladas", "out": "b6:afiladas+0.8", "fx_in": "pop", "fx_out": "pop", "sfx": "ding", "idle": {"fx": "spin", "vel": 90}},
    {"a": "brillo", "x": 620, "y": 800, "s": .45, "z": 2, "in": "b6:afiladas+0.15", "out": "b6:afiladas+0.9", "fx_in": "pop", "fx_out": "pop", "sfx": "none", "idle": {"fx": "spin", "vel": -90}},
    {"a": "texto_hierro", "texto": {"t": "HIERRO", "estilo": "etiqueta"}, "x": 250, "y": 520, "r": -6, "in": "b6:hierro", "out": "b6:calentaba", "fx_in": "pop", "fx_out": "pop"},
    {"a": "brasero_0", "x": 600, "y": 1330, "s": 1.0, "z": 2, "in": "b6:calentaba-0.4", "fx_in": "jump",
     "loop": {"frames": ["brasero_0", "brasero_1"], "fps": 6}},
    {"a": "resplandor", "x": 600, "y": 1160, "s": 1.0, "z": 0, "in": "b6:rojo", "fx_in": "fade", "idle": "pulse",
     "keys": [{"at": "b6:brasas", "dur": .5, "x": 600, "y": 730, "s": .9, "ease": "back"}]},
    {"texto": {"t": "¡AL ROJO VIVO!", "size": 64, "color": "#FFFFFF", "box": "#FF5D5D"}, "x": 300, "y": 470, "r": -4, "in": "b6:rojo", "fx_in": "pop", "idle": "wiggle"},
    {"a": "vos_miedo", "x": 170, "y": 1330, "s": .5, "z": 3, "in": "b6:calentaba", "fx_in": "slide_right", "blink": True, "idle": "breathe",
     "swaps": [{"at": "b6:rojo", "a": "vos_sorpresa", "fx": "punch"}]},
]}
e2["elementos"][3].pop("a")

# ---------------------------------------------------------------- escena 3: la garra en acción
ES = .95                     # escala del preso de espaldas
PIES = 1340                  # y de los pies (ancla)
HX, HY0, HL, HP = [206, 242, 278, 314], 480, 210, 886   # surcos en el dibujo (META espalda_heridas)
y_ini = PIES - (HP - HY0) * ES
y_fin = y_ini + HL * ES
zoom = 1.55
HERIDA_C = 590
pies_zoom = 1000 + (HP - HERIDA_C) * zoom
carne = [vuelo(f"carne_{i % 3}", 540 + dx * .3, y_ini + 110, dx, alto, 1330, f"b7:arrancando+{i*0.07:.2f}", 1.1, rr, .8)
         for i, (dx, alto, rr) in enumerate([(-380, 260, -400), (360, 300, 380), (-200, 380, 300), (240, 200, -260)])]
gotas = [vuelo("gota_sangre", 540, y_ini + 100, dx, alto, 1330, f"b7:arrancando+{0.04 + i*0.06:.2f}", .9, 0, 1.0)
         for i, (dx, alto) in enumerate([(-260, 180), (300, 220), (-120, 300), (160, 260), (60, 340)])]
e3 = {"nombre": "garra_espalda", "beats": [7], "fondo": "fondo_mazmorra", "elementos": [
    {"a": "viga", "x": 540, "y": 500, "s": 1.0, "z": 0, "in": "esc", "out": "b7:costillas", "fx_out": "fade", "dur_out": .3},
    {"a": "espalda", "x": 540, "y": PIES, "s": ES, "z": 1, "in": "esc", "out": "b7:arrancando",
     "idle": [{"fx": "sway", "to": "b7:clavaba"}, {"fx": "shake", "fuerza": 1.3, "from": "b7:clavaba"}],
     "seq": {"frames": ["espalda_surcos_1"] * 6 + ["espalda_surcos_2", "espalda_surcos_3", "espalda_surcos_4"],
             "at": "b7:clavaba+0.1", "dur": 3.1, "ease": "linear"},
     "keys": []},
    {"a": "espalda_desgarrada", "x": 540, "y": PIES, "s": ES, "z": 1, "in": "b7:arrancando",
     "idle": {"fx": "shake", "fuerza": 1.6, "to": "b7:costillas"},
     "keys": [{"at": "b7:costillas-0.2", "dur": .7, "s": zoom, "y": pies_zoom, "ease": "inout", "sfx": "zoom"}]},
    {"a": "resplandor", "x": 250, "y": 600, "s": .6, "z": 2, "in": "esc", "out": "b7:arrancando+0.3", "fx_out": "fade", "idle": "pulse",
     "keys": [{"at": "b7:clavaba", "dur": .15, "x": 540, "y": y_ini - 60, "ease": "in"},
              {"at": "b7:tiraba", "dur": 1.1, "y": y_fin - 60, "ease": "linear"},
              {"at": "b7:arrancando", "dur": .3, "x": 120, "y": 500, "ease": "out"}]},
    {"a": "garra_frente_roja", "x": 250, "y": 660, "s": ES, "r": 10, "z": 3, "in": "esc", "out": "b7:arrancando+0.35", "fx_in": "slide_right",
     "idle": {"fx": "float", "fuerza": .6, "to": "b7:clavaba"},
     "keys": [{"at": "b7:clavaba", "dur": .15, "x": 540, "y": y_ini, "r": 0, "ease": "in", "sfx": "golpe"},
              {"at": "b7:tiraba", "dur": 1.1, "y": y_fin, "ease": "linear", "sfx": "whoosh_suave"},
              {"at": "b7:arrancando", "dur": .3, "x": 60, "y": 420, "r": -30, "ease": "out", "sfx": "whoosh"}]},
    {"texto": {"t": "¡AAAAH!", "estilo": "crack", "size": 96}, "x": 800, "y": 560, "r": 8, "z": 6, "in": "b7:clavaba", "out": "b7:tiraba", "fx_in": "pop", "fx_out": "pop", "sfx": "none", "idle": "shake"},
    {"texto": {"t": "¡TIRÓN!", "estilo": "crack", "size": 100}, "x": 280, "y": 600, "r": -10, "z": 6, "in": "b7:tiraba", "out": "b7:arrancando", "fx_in": "pop", "fx_out": "pop", "sfx": "none"},
    {"texto": {"t": "¡AAAAAAH!", "estilo": "crack", "size": 104}, "x": 560, "y": 560, "r": -6, "z": 6, "in": "b7:arrancando", "out": "b7:costillas", "fx_in": "pop", "fx_out": "pop", "sfx": "crack", "idle": "shake"},
    *carne, *gotas,
    {"texto": {"t": "¡LAS COSTILLAS!", "estilo": "etiqueta", "size": 60}, "x": 540, "y": 1300, "r": -3, "z": 8, "in": "b7:costillas+0.4", "fx_in": "pop"},
]}

# ---------------------------------------------------------------- escena 4: el aplastacabezas
BX, BS = 540, .9        # base: lienzo 700x900, ancla abajo en y=1330
top = 1330 - 900 * BS


def sc(cx, cy):
    return BX + (cx - 350) * BS, top + cy * BS


chin = sc(350, 565)
rim = sc(350, 300)
HS = .82 * BS
HEAD_H = 254          # alto del mentón al tope de la cabeza con sy=1 (px de pantalla a escala HS)


def head_keys(rim_y):
    sy = min(1.0, (chin[1] - (rim_y - 16)) / (344 * HS))
    return dict(sy=round(sy, 3), sx=round(1 + (1 - sy) * .45, 3))


pasos = [("b9:apretaba", 20, .5), ("b10:vuelta", 34, .8), ("b10:dientes", 56, .35), ("b10:mandíbula", 78, .35),
         ("b10:ojos", 92, .35), ("b10:cedía", 110, .5), ("b10:cráneo", 200, .08)]
tor_keys, head_k = [], []
for at, dy, dur in pasos:
    ry = rim[1] + dy
    tor_keys.append({"at": at, "dur": dur, "y": round(ry, 1), "ease": "out"})
    head_k.append(dict({"at": at, "dur": dur, "ease": "out"}, **head_keys(ry)))

teeth = []
for i, (dx, dy, rr) in enumerate([(-260, 260, -300), (230, 300, 280), (-120, 330, 200), (300, 120, -240)]):
    teeth.append({"a": "diente", "x": chin[0] + (i - 1.5) * 18, "y": chin[1] - 30, "s": .9, "z": 9,
                  "in": f"b10:dientes+{i*0.05:.2f}", "out": "b10:mandíbula+0.6", "fx_in": "pop", "fx_out": "fade", "sfx": "none",
                  "keys": [{"at": f"b10:dientes+{i*0.05:.2f}", "dur": .9, "x": chin[0] + dx, "y": chin[1] - 30 - 160, "r": rr / 2, "ease": "out"},
                           {"at": f"b10:dientes+{0.9 + i*0.05:.2f}", "dur": .7, "y": chin[1] + dy, "r": rr, "ease": "in"}]})

# los ojos salen de las órbitas (posición de cada ojo en la cabeza aplastada)
sy_ojos = head_keys(rim[1] + 92)["sy"]
sx_ojos = head_keys(rim[1] + 92)["sx"]
ojo_y = chin[1] - (442 - 305) * HS * sy_ojos
ojos = []
for ex, dx, flip in [(200, -330, True), (320, 330, False)]:
    x0 = chin[0] + (ex - 260) * HS * sx_ojos
    ojos.append(vuelo("ojo_volador", round(x0), round(ojo_y), dx, 330, 1290, "b10:salían", 1.3, 0, .45, 1.15, flip=flip,
                      out="fin", sfx="pop"))
# la cabeza explota
cy_cab = chin[1] - 150
estallido = [
    {"a": "explosion_0", "x": chin[0], "y": cy_cab, "s": 1.2, "z": 11, "in": "b10:cráneo+0.05", "out": "b10:cráneo+1.3", "fx_out": "fade", "dur_out": .4,
     "seq": {"frames": ["explosion_0", "explosion_1", "explosion_2", "explosion_3"], "at": "b10:cráneo+0.05", "dur": .7, "ease": "out"},
     "sfx": "crack"},
    {"texto": {"t": "¡BOOM!", "estilo": "crack", "size": 170}, "x": 540, "y": 470, "r": -6, "z": 13, "in": "b10:cráneo+0.1", "fx_in": "pop", "sfx": "golpe", "idle": "shake"},
]
for i, (x, y) in enumerate([(250, 640), (820, 590), (880, 900), (190, 960), (560, 560)]):
    estallido.append({"a": f"salpicadura_{i % 3}", "x": x, "y": y, "s": .9 + .1 * (i % 2), "r": i * 70, "z": 0, "in": f"b10:cráneo+{0.12 + i*0.03:.2f}",
                      "fx_in": "pop", "sfx": "none"})
for i, (a, dx, alto, rr) in enumerate([("craneo_trozo_0", -420, 420, 500), ("craneo_trozo_1", 400, 380, -480), ("craneo_trozo_2", -180, 520, 360),
                                       ("mechon", 260, 500, -300), ("mechon", -320, 300, 260), ("carne_0", 360, 260, 400),
                                       ("carne_1", -260, 220, -380), ("diente", 120, 600, 720), ("gota_sangre", -60, 560, 0),
                                       ("gota_sangre", 200, 440, 0), ("gota_sangre", -380, 340, 0)]):
    estallido.append(vuelo(a, chin[0], cy_cab, dx, alto, 1300, f"b10:cráneo+{0.05 + i*0.02:.2f}", 1.3, rr, .9, 1.2, z=12))
estallido.append({"a": "craneo_trozo_1", "x": chin[0] - 20, "y": chin[1] - 40, "s": .9, "r": 20, "z": 2, "in": "b10:cráneo+0.06", "sfx": "none"})

clics = [{"at": f"b10:vuelta+{k*0.3:.1f}", "s": "clic", "vol": .9} for k in range(26)]
e4 = {"nombre": "aplasta", "beats": [8, 9, 10], "fondo": "fondo_mazmorra", "flash": True, "sonidos": clics, "elementos": [
    {"a": "verdugo", "x": 150, "y": 1330, "s": .62, "z": -1, "in": "b9", "fx_in": "slide_right",
     "idle": [{"fx": "breathe"}, {"fx": "work", "from": "b10:vuelta", "to": "b10:cráneo"}],
     "swaps": [{"at": "b10:dientes", "a": "verdugo_risa", "fx": "punch"}]},
    {"a": "cabeza_miedo", "x": chin[0], "y": chin[1], "s": HS, "z": 1, "in": "b8:aplastacabezas", "fx_in": "drop",
     "idle": [{"fx": "shake", "fuerza": .4, "to": "b10:vuelta"}, {"fx": "shake", "fuerza": 1.2, "from": "b10:vuelta"}],
     "swaps": [{"at": "b9:apretaba", "a": "cabeza_grito", "fx": "punch"},
               {"at": "b10:dientes", "a": "cabeza_dientes", "fx": "punch", "sfx": "none"},
               {"at": "b10:ojos", "a": "cabeza_ojos", "fx": "punch"},
               {"at": "b10:salían", "a": "cabeza_sin_ojos", "fx": "punch", "sfx": "none"}],
     "keys": head_k, "out": "b10:cráneo+0.06"},
    {"a": "aplasta_tornillo_0", "x": rim[0], "y": rim[1], "s": BS, "z": 2, "in": "b8:aplastacabezas", "fx_in": "drop", "sfx": "none",
     "loop": {"frames": ["aplasta_tornillo_0", "aplasta_tornillo_1", "aplasta_tornillo_2", "aplasta_tornillo_1"], "fps": 8,
              "from": "b9:apretaba", "to": "b10:cráneo>"},
     "keys": tor_keys},
    {"a": "aplasta_base", "x": BX, "y": 1330, "s": BS, "z": 3, "in": "b8:aplastacabezas", "fx_in": "drop", "sfx": "golpe"},
    {"texto": {"t": "CASCO", "estilo": "etiqueta"}, "x": 860, "y": 740, "r": 5, "z": 6, "in": "b9:casco", "out": "b10", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "TORNILLO", "estilo": "etiqueta"}, "x": 850, "y": 420, "r": -5, "z": 6, "in": "b9:tornillo", "out": "b10", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "BARRA", "estilo": "etiqueta"}, "x": 870, "y": 1000, "r": -4, "z": 6, "in": "b9:barra", "out": "b10", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "¡CRACK!", "estilo": "crack"}, "x": 820, "y": 640, "r": 10, "z": 7, "in": "b10:dientes", "out": "b10:mandíbula", "fx_in": "pop", "fx_out": "pop", "sfx": "crack"},
    {"texto": {"t": "¡CRACK!", "estilo": "crack"}, "x": 300, "y": 600, "r": -10, "z": 7, "in": "b10:mandíbula", "out": "b10:ojos", "fx_in": "pop", "fx_out": "pop", "sfx": "crack"},
    {"texto": {"t": "¡POP!", "estilo": "crack"}, "x": 830, "y": 640, "r": 8, "z": 7, "in": "b10:ojos", "out": "b10:final", "fx_in": "pop", "fx_out": "pop", "sfx": "none"},
    *teeth,
    *ojos, *estallido,
    {"a": "blanco", "x": 540, "y": 960, "z": 12, "alpha": .9, "in": "b10:cráneo+0.04", "out": "b10:cráneo+0.3", "fx_out": "fade", "dur_out": .25, "sfx": "golpe"},
]}

doc = {"velocidad": 1.0, "cola": 2.4, "volumen_efectos": .5,
       "subtitulos": {"activos": True, "y": 1470, "size": 76},
       "estilos": estilos, "narracion": [{"texto": t} for t in narr], "persistentes": persist,
       "escenas": [e0, e1, e2, e3, e4],
       "audio_voz": "audio/voz.wav", "palabras_json": "audio/palabras.json"}
json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
print("ok")
