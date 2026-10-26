"""Genera escenas.json del short de torturas (parte 3). Uso: python3 proyectos/torturas3/armar_escenas.py"""
import json
import math
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "escenas.json")

narr = [
    "¡Te muestro 3 instrumentos de tortura tan crueles que cuesta creer que existieron!",
    "Parte 3.",
    "1. El tenedor del hereje.",
    "Una barra de metal con dos puntas afiladas en cada extremo, atada al cuello con una correa: dos púas debajo de la barbilla y dos sobre el pecho.",
    "Colgaban al prisionero de las manos para que no pudiera acostarse, y cuando el sueño le hacía bajar la cabeza, las puntas se le clavaban en la garganta.",
    "2. El potro.",
    "Una mesa de madera con rodillos en los extremos, donde ataban las muñecas y los tobillos.",
    "Al girar las palancas, las cuerdas estiraban el cuerpo hasta desgarrar los músculos y dislocar hombros y caderas, con chasquidos que se escuchaban en toda la sala.",
    "3. La rueda.",
    "Ataban al prisionero a una gran rueda de madera y le golpeaban brazos y piernas con una barra de hierro hasta romperle todos los huesos.",
    "Después le entrelazaban las extremidades entre los rayos",
    "y subían la rueda a lo alto de un poste, para que los cuervos lo picotearan todavía vivo.",
    "¿Cuál te parece el peor? Cuéntanos en los comentarios y síguenos para la parte 4.",
]

estilos = {
    "numero": {"size": 92, "color": "#FFFFFF", "box": "#FF5D5D", "circle": True, "pad": [30, 14]},
    "titulo": {"size": 66, "color": "#24201F", "box": "#FFF3DF"},
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


def crack(t, x, y, r=8, txt="¡CRACK!", size=110, dur=.7, sfx="crack"):
    base, off = (t.rsplit("+", 1)[0], float(t.rsplit("+", 1)[1])) if "+" in t else (t, 0.0)
    return {"texto": {"t": txt, "estilo": "crack", "size": size}, "x": x, "y": y, "r": r, "z": 10, "in": t,
            "out": f"{base}+{off + dur:.2f}", "fx_in": "pop", "fx_out": "pop", "sfx": sfx}


persist = []
for x in (110, 970):   # antorchas solo en la mazmorra
    for t0, t1 in [(0, "e4"), ("e5", "fin")]:
        persist.append({"a": "antorcha_0", "x": x, "y": 760, "s": .9, "z": -20, "in": t0, "out": t1,
                        "loop": {"frames": ["antorcha_0", "antorcha_1"], "fps": 5}, "sfx": "none"})
persist += titulo(1, "EL TENEDOR DEL HEREJE", 2, "b5-0.15")
persist += titulo(2, "EL POTRO", 5, "b8-0.15")
persist += titulo(3, "LA RUEDA", 8, "b12-0.15")

# ---------------------------------------------------------------- escena 0: gancho
e0 = {"nombre": "gancho", "beats": [0, 1], "fondo": "fondo_mazmorra", "elementos": [
    {"a": "vos_miedo", "x": 290, "y": 1330, "s": .7, "in": "b0", "fx_in": "jump", "blink": True, "idle": "breathe",
     "swaps": [{"at": "b0:crueles", "a": "vos_grito", "fx": "punch"}, {"at": "b0:cuesta", "a": "vos_miedo", "fx": "punch"}]},
    {"a": "verdugo", "x": 790, "y": 1330, "s": .7, "in": "b0:tortura", "fx_in": "slide_left", "idle": "breathe",
     "swaps": [{"at": "b0:existieron", "a": "verdugo_risa", "fx": "punch"}]},
    {"a": "tenedor", "x": 200, "y": 570, "s": 1.5, "anchor": [.5, .5], "r": 12, "in": "b0:instrumentos", "out": "b1", "fx_in": "pop", "fx_out": "pop", "idle": "bob"},
    {"a": "potro_icono", "x": 540, "y": 570, "s": .27, "anchor": [.5, .5], "in": "b0:instrumentos+0.25", "out": "b1", "fx_in": "pop", "fx_out": "pop", "idle": "bob"},
    {"a": "rueda_icono", "x": 870, "y": 570, "s": .34, "anchor": [.5, .5], "in": "b0:instrumentos+0.5", "out": "b1", "fx_in": "pop", "fx_out": "pop", "idle": {"fx": "spin", "vel": 40}},
    {"a": "sudor", "x": 370, "y": 830, "s": 1.4, "in": "b0:crueles", "out": "b0:cuesta", "fx_in": "pop", "fx_out": "fade",
     "keys": [{"at": "b0:crueles", "dur": .8, "y": 900, "ease": "in"}], "sfx": "none"},
    {"texto": {"t": "PARTE 3", "size": 150, "color": "#FFFFFF", "box": "#FF5D5D"}, "x": 540, "y": 640, "r": -6,
     "in": "b1", "fx_in": "pop", "sfx": "golpe", "idle": {"fx": "pulse", "fuerza": .6}},
]}

# ---------------------------------------------------------------- escena 1: el tenedor del hereje
S1 = 1.25
PIES = 1245
CH = round(PIES - (806 - 442) * S1)    # mentón en pantalla
FS = S1 * .72                          # el tenedor va del mentón al esternón
BIG, BR, BX, BY = 2.4, 15, 540, 560    # tenedor grande en la presentación


def punta(dx, dy):
    a = math.radians(BR)
    return BX + (dx * math.cos(a) - dy * math.sin(a)) * BIG, BY + (dx * math.sin(a) + dy * math.cos(a)) * BIG


brillos = []
for i, (dx, dy) in enumerate([(-26, 0), (26, 0), (-26, 166), (26, 166)]):
    x, y = punta(dx, dy)
    brillos.append({"a": "brillo", "x": round(x), "y": round(y), "s": .5, "z": 6, "in": f"b3:puntas+{i*0.1:.1f}",
                    "out": "b3:atada", "fx_in": "pop", "fx_out": "pop", "sfx": "ding" if i == 0 else "none",
                    "idle": {"fx": "spin", "vel": 90 if i % 2 else -90}})

# se duerme, se pincha y se despierta, tres veces; a la cuarta ya no puede más
ciclos = [("b4:sueño", .6), ("b4:bajar+0.15", .55), ("b4:cabeza+0.45", .5)]
cab_keys, cab_swaps, extra = [], [], []
for i, (t, d) in enumerate(ciclos):
    base, off = (t.split("+")[0], float(t.split("+")[1])) if "+" in t else (t, 0.0)
    pin = f"{base}+{off + d:.2f}"
    cab_swaps.append({"at": t, "a": "cabeza_cansado" if i < 2 else "cabeza_dormido", "sfx": "none"})
    cab_swaps.append({"at": pin, "a": "cabeza_pinchazo", "fx": "punch", "sfx": "none"})
    cab_keys.append({"at": t, "dur": d, "y": CH + 12 + 2 * i, "ease": "in"})
    cab_keys.append({"at": pin, "dur": .1, "y": CH - 12, "ease": "out", "sfx": "golpe"})
    cab_keys.append({"at": f"{base}+{off + d + 0.1:.2f}", "dur": .3, "y": CH, "ease": "out"})
    extra.append(crack(pin, 760 if i % 2 == 0 else 330, CH - 300 + 40 * i, 8 if i % 2 == 0 else -8, "¡AY!", 76, .5, "none"))
    extra.append(vuelo("gota_sangre", 540 + (14 if i % 2 else -14), CH + 6, 50 if i % 2 else -50, 20, 1290, pin, .9, 0, .7))
# el final: se le cierran los ojos, baja la cabeza del todo y las púas se hunden
cab_swaps += [{"at": "b4:puntas", "a": "cabeza_dormido", "sfx": "none"},
              {"at": "b4:clavaban+0.35", "a": "cabeza_rendido", "fx": "punch", "sfx": "none"}]
cab_keys += [{"at": "b4:puntas", "dur": .8, "y": CH + 16, "ease": "in"},
             {"at": "b4:clavaban", "dur": .5, "y": CH + 30, "ease": "in", "sfx": "crack"}]
extra += [vuelo("gota_sangre", 540 + dx, CH + 20, dx * 3, 10, 1290, f"b4:clavaban+{0.4 + i*0.15:.2f}", 1.0, 0, .8)
          for i, dx in enumerate([-20, 18, -6, 26])]

e1 = {"nombre": "tenedor", "beats": [2, 3, 4], "fondo": "fondo_mazmorra", "flash": True,
      "camara": [{"at": "b4:sueño", "dur": 3.0, "s": 1.3, "x": 540, "y": CH + 40, "ease": "inout"},
                 {"at": "b4:garganta", "dur": .6, "s": 1.0, "ease": "inout"}],
      "elementos": [
    {"a": "tenedor", "x": BX, "y": BY, "s": BIG, "r": BR, "z": 4, "in": "b2:tenedor", "fx_in": "pop",
     "idle": {"fx": "float", "to": "b3:cuello"},
     "keys": [{"at": "b3:barra", "dur": .2, "s": BIG * 1.1, "ease": "out"}, {"at": "b3:barra+0.2", "dur": .3, "s": BIG},
              {"at": "b3:cuello", "dur": .55, "x": 540, "y": CH - 4, "s": FS, "r": 0, "ease": "inout", "sfx": "whoosh"},
              {"at": "b4:clavaban", "dur": .5, "y": CH + 6, "ease": "in"}],
     "swaps": [{"at": "b4:clavaban+0.3", "a": "tenedor_hundido", "sfx": "none"}]},
    *brillos,
    {"a": "preso_sogas", "x": 540, "y": PIES, "s": S1, "z": 3, "in": "b3:atada", "fx_in": "slide_up",
     "idle": {"fx": "shake", "fuerza": .6, "from": "b4:clavaban", "to": "b4:clavaban+1.0"},
     "keys": [{"at": "b4:colgaban", "dur": .3, "y": PIES - 30, "ease": "out"}, {"at": "b4:colgaban+0.3", "dur": .5, "y": PIES, "ease": "bounce"}]},
    {"a": "cabeza_sudor", "x": 540, "y": CH, "s": S1, "z": 5, "in": "b3:atada", "fx_in": "slide_up",
     "idle": {"fx": "shake", "fuerza": .6, "from": "b4:clavaban", "to": "b4:clavaban+1.0"},
     "swaps": cab_swaps,
     "keys": [{"at": "b4:colgaban", "dur": .3, "y": CH - 30, "ease": "out"}, {"at": "b4:colgaban+0.3", "dur": .5, "y": CH, "ease": "bounce"}] + cab_keys},
    {"texto": {"t": "CORREA", "estilo": "etiqueta"}, "x": 840, "y": CH + 50, "r": 5, "z": 8, "in": "b3:correa", "out": "b3:barbilla", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "BARBILLA", "estilo": "etiqueta"}, "x": 850, "y": CH - 20, "r": -4, "z": 8, "in": "b3:barbilla", "out": "b4:colgaban", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "PECHO", "estilo": "etiqueta"}, "x": 830, "y": CH + 130, "r": 4, "z": 8, "in": "b3:pecho", "out": "b4:colgaban", "fx_in": "pop", "fx_out": "pop"},
    {"a": "cama_vacia", "x": 210, "y": 1300, "s": .4, "z": 6, "in": "b4:acostarse", "out": "b4:sueño", "fx_in": "pop", "fx_out": "pop"},
    {"a": "prohibido", "x": 210, "y": 1225, "s": .8, "z": 7, "in": "b4:acostarse+0.15", "out": "b4:sueño", "fx_in": "pop", "fx_out": "pop", "sfx": "boing"},
    {"a": "zzz", "x": 800, "y": CH - 400, "s": .6, "z": 8, "in": "b4:sueño", "fx_in": "pop", "idle": "float",
     "out": "b4:garganta", "fx_out": "pop"},
    *extra,
    {"a": "vos_miedo", "x": 150, "y": 1330, "s": .45, "z": 8, "in": "b4:sueño", "fx_in": "slide_right", "blink": True, "idle": "breathe",
     "swaps": [{"at": "b4:clavaban+0.35", "a": "vos_grito", "fx": "punch"}]},
]}

# ---------------------------------------------------------------- escena 2: el potro
PX, PY, PS = 540, 826, .92      # potro parado: lienzo 700x1100
ox, oy = PX - 350 * PS, PY - 550 * PS
def kpos(cx, cy):
    return round(ox + cx * PS), round(oy + cy * PS)


palancas = [kpos(54, 90), kpos(646, 1010)]
giro = [("b7:girar", .8), ("b7:estiraban", .8), ("b7:desgarrar", .8), ("b7:dislocar", .8), ("b7:caderas", .8), ("b7:chasquidos", .8)]
rod_keys = lambda sgn: [{"at": at, "dur": d, "r": sgn * 90 * (i + 1), "ease": "inout", **({"sfx": "cruje"} if sgn > 0 else {})}
                        for i, (at, d) in enumerate(giro)]
hombros_y = kpos(0, 434)[1]
caderas_y = kpos(0, 720)[1]
e2 = {"nombre": "potro", "beats": [5, 6, 7], "fondo": "fondo_mazmorra", "flash": True,
      "camara": [{"at": "b7:dislocar", "dur": .15, "s": 1.5, "x": 540, "y": hombros_y, "ease": "out"},
                 {"at": "b7:caderas", "dur": .3, "y": caderas_y, "ease": "inout"},
                 {"at": "b7:escuchaban", "dur": .5, "s": 1.0, "ease": "inout"}],
      "elementos": [
    {"a": "potro_sangre", "x": PX, "y": PY, "s": PS, "z": .5, "in": "b7:dislocar", "fx_in": "fade", "dur_in": .6, "sfx": "none"},
    {"a": "pantalla_roja", "x": 540, "y": 960, "z": 30, "alpha": .4, "in": "b7:dislocar", "out": "b7:dislocar+0.35", "fx_out": "fade", "dur_out": .3, "sfx": "none"},
    {"a": "potro_mesa", "x": PX, "y": PY, "s": PS, "z": 0, "in": "b5:potro", "fx_in": "drop",
     "keys": [{"at": "b6:mesa", "dur": .15, "s": PS * 1.04, "ease": "out"}, {"at": "b6:mesa+0.15", "dur": .3, "s": PS, "ease": "out"}]},
    {"a": "potro_preso_0", "x": PX, "y": PY, "s": PS, "z": 1, "in": "b6:ataban", "fx_in": "drop",
     "seq": {"frames": ["potro_preso_0", "potro_preso_1", "potro_preso_2", "potro_preso_2", "potro_preso_3", "potro_preso_4", "potro_preso_4"],
             "at": "b7:estiraban", "dur": 3.4, "ease": "linear"},
     "idle": [{"fx": "shake", "fuerza": .5, "from": "b7:estiraban", "to": "b7:dislocar"}, {"fx": "shake", "fuerza": 1.3, "from": "b7:dislocar"}]},
    *[{"a": "rodillo", "x": x, "y": y, "s": PS * .9, "z": 2, "in": "b6:rodillos", "fx_in": "pop",
       "keys": [{"at": "b6:rodillos", "dur": .6, "r": (1 if i else -1) * 90, "ease": "out"}] + rod_keys(1 if i else -1)}
      for i, (x, y) in enumerate(palancas)],
    {"texto": {"t": "RODILLOS", "estilo": "etiqueta"}, "x": 540, "y": 400, "r": -3, "z": 6, "in": "b6:rodillos", "out": "b6:ataban", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "RODILLOS", "estilo": "etiqueta"}, "x": 540, "y": 1250, "r": 3, "z": 6, "in": "b6:rodillos+0.2", "out": "b6:ataban", "fx_in": "pop", "fx_out": "pop", "sfx": "none"},
    {"texto": {"t": "MUÑECAS", "estilo": "etiqueta"}, "x": 800, "y": 470, "r": 5, "z": 6, "in": "b6:muñecas", "out": "b7", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "TOBILLOS", "estilo": "etiqueta"}, "x": 790, "y": 1130, "r": -5, "z": 6, "in": "b6:tobillos", "out": "b7", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "¡GIRAR!", "estilo": "etiqueta"}, "x": 540, "y": 400, "r": 3, "z": 6, "in": "b7:girar", "out": "b7:estiraban", "fx_in": "pop", "fx_out": "pop"},
    {"texto": {"t": "¡ESTIRA!", "size": 70, "color": "#FFFFFF", "box": "#FF5D5D"}, "x": 540, "y": 400, "z": 6, "in": "b7:estiraban", "out": "b7:dislocar",
     "fx_in": "pop", "fx_out": "pop", "keys": [{"at": "b7:estiraban", "dur": 1.6, "sy": 1.3, "ease": "inout"}]},
    crack("b7:hombros", 330, hombros_y - 150, -10),
    crack("b7:caderas", 750, caderas_y - 60, 10),
    crack("b7:chasquidos", 300, 560, -8, "¡CHASK!", 110, .6),
    crack("b7:escuchaban", 780, 900, 8, "¡CRACK!", 110, .6),
    {"a": "vos_grito", "x": 120, "y": 1330, "s": .42, "z": 3, "in": "b7:dislocar", "fx_in": "jump", "idle": "shake"},
]}

# ---------------------------------------------------------------- escena 3: la rueda
RX, RY, RS = 600, 980, .9
def rpos(cx, cy):
    return round(RX + (cx - 350) * RS), round(RY + (cy - 350) * RS)


golpes = ["b9:golpeaban", "b9:brazos", "b9:piernas", "b9:romperle", "b9:huesos"]
verd_swaps = []
for g in golpes:
    verd_swaps.append({"at": f"{g}-0.25", "a": "verdugo_barra_arriba"})
    verd_swaps.append({"at": g, "a": "verdugo_barra_abajo", "fx": "punch", "sfx": "golpe"})
verd_swaps.append({"at": "b10", "a": "verdugo_barra_arriba"})
e3 = {"nombre": "rueda", "beats": [8, 9, 10], "fondo": "fondo_mazmorra", "flash": True,
      "camara": [{"at": "b9:huesos", "dur": .12, "s": 1.35, "x": RX, "y": RY - 80, "ease": "out"},
                 {"at": "b9:huesos+0.9", "dur": .5, "s": 1.0, "ease": "inout"}],
      "elementos": [
    {"a": "rueda", "x": RX, "y": RY, "s": RS, "z": 0, "in": "b8:rueda", "fx_in": "slide_left",
     "keys": [{"at": "b8:rueda", "dur": .45, "r": -120, "ease": "out"}]},
    {"a": "rueda_preso_0", "x": RX, "y": RY, "s": RS, "z": 1, "in": "b9:ataban", "fx_in": "drop",
     "swaps": [{"at": "b9:brazos", "a": "rueda_preso_1", "fx": "punch", "sfx": "none"},
               {"at": "b9:piernas", "a": "rueda_preso_2", "fx": "punch", "sfx": "none"},
               {"at": "b10:entrelazaban", "a": "rueda_preso_3", "fx": "punch", "sfx": "cruje"}],
     "idle": {"fx": "shake", "fuerza": 1.0, "from": "b9:golpeaban"}},
    {"a": "verdugo_barra_arriba", "x": 170, "y": 1330, "s": .62, "z": 3, "in": "b9:golpeaban-0.6", "fx_in": "slide_right",
     "swaps": verd_swaps, "idle": "breathe"},
    {"texto": {"t": "BARRA DE HIERRO", "estilo": "etiqueta"}, "x": 330, "y": 560, "r": -4, "z": 6, "in": "b9:barra", "out": "b9:romperle", "fx_in": "pop", "fx_out": "pop"},
    crack("b9:golpeaban", *rpos(150, 230), -8),
    crack("b9:brazos", *rpos(560, 230), 8),
    crack("b9:piernas", *rpos(230, 600), -8),
    crack("b9:romperle", *rpos(500, 600), 8),
    crack("b9:huesos", 560, 560, -4, "¡CRACK!", 160, .9),
    {"texto": {"t": "ENTRE LOS RAYOS", "estilo": "etiqueta"}, "x": 600, "y": 560, "r": 3, "z": 6, "in": "b10:rayos", "fx_in": "pop"},
]}

# ---------------------------------------------------------------- escena 4: el poste y los cuervos
# rueda_poste: lienzo 800x1100 con ancla abajo; centro de la rueda en (400, 400)
PO_X, PO_Y = 540, 1330
def ppos(cx, cy):
    return PO_X + (cx - 400), PO_Y - 1100 + cy


cuervos = []
for i, (sx_, sy_, lx, ly, flip, t) in enumerate([(1250, 300, *ppos(300, 330), False, "b11:cuervos"),
                                               (-200, 420, *ppos(600, 340), True, "b11:cuervos+0.3"),
                                               (1250, 700, *ppos(470, 470), False, "b11:cuervos+0.6")]):
    land = f"b11:picotearan+{i*0.2 - 0.3:.1f}".replace("+-", "-")
    cuervos.append({"a": "cuervo_vuela_a", "x": sx_, "y": sy_, "s": .7, "flip": not flip, "z": 5, "in": t, "out": land, "sfx": "cuervo",
                    "loop": {"frames": ["cuervo_vuela_a", "cuervo_vuela_b"], "fps": 9},
                    "keys": [{"at": t, "dur": 1.0, "x": lx, "y": ly, "ease": "out"}]})
    cuervos.append({"a": "cuervo_parado", "x": lx, "y": ly, "s": .7, "flip": not flip, "z": 5, "in": land, "sfx": "none",
                    "loop": {"frames": ["cuervo_pica", "cuervo_parado"], "fps": 3 + i, "from": "b11:picotearan"}})
e4 = {"nombre": "poste", "beats": [11], "fondo": "fondo_patibulo", "flash": True,
      "sonidos": [{"at": "b11:picotearan+0.4", "s": "cuervo", "vol": .8}, {"at": "b11:vivo", "s": "cuervo", "vol": .8}],
      "elementos": [
    {"a": "rueda_poste_dolor", "x": PO_X, "y": PO_Y + 700, "s": 1.0, "z": 1, "in": "esc",
     "keys": [{"at": "b11:subían", "dur": 1.4, "y": PO_Y, "ease": "out", "sfx": "cruje"}],
     "swaps": [{"at": "b11:vivo", "a": "rueda_poste_vivo", "fx": "punch"}],
     "idle": {"fx": "shake", "fuerza": .4, "from": "b11:picotearan"}},
    {"texto": {"t": "¡TODAVÍA VIVO!", "size": 72, "color": "#FFFFFF", "box": "#FF5D5D"}, "x": 540, "y": 1180, "r": -3, "z": 8,
     "in": "b11:todavía", "fx_in": "pop", "idle": "wiggle"},
    *cuervos,
]}

# ---------------------------------------------------------------- escena 5: outro
iconos = [("tenedor", 240, 1.6, 12), ("potro_icono", 540, .28, 0), ("rueda_icono", 840, .34, 0)]
e5 = {"nombre": "outro", "beats": [12], "fondo": "fondo_mazmorra", "flash": True, "elementos": [
    {"texto": {"t": "¿CUÁL ES EL PEOR?", "size": 80, "color": "#24201F", "box": "#FFD23F"}, "x": 540, "y": 260, "r": -2, "z": 6,
     "in": "b12", "fx_in": "pop", "idle": {"fx": "pulse", "fuerza": .4}},
    *[{"a": a, "x": x, "y": 620, "s": s, "r": r, "anchor": [.5, .5], "z": 4, "in": f"b12+{0.15 + i*0.2:.2f}", "out": "b12:parte",
       "fx_in": "pop", "fx_out": "pop", "idle": "bob"} for i, (a, x, s, r) in enumerate(iconos)],
    *[{"texto": {"t": str(i + 1), "estilo": "numero", "size": 70}, "x": x, "y": 440, "z": 5, "in": f"b12+{0.25 + i*0.2:.2f}", "out": "b12:parte",
       "fx_in": "pop", "fx_out": "pop", "sfx": "none"} for i, (a, x, s, r) in enumerate(iconos)],
    {"a": "vos_mira", "x": 280, "y": 1330, "s": .62, "z": 3, "in": "b12", "fx_in": "jump", "blink": True, "idle": "breathe",
     "swaps": [{"at": "b12:síguenos", "a": "vos_pulgar", "fx": "punch"}]},
    {"a": "comentario", "x": 740, "y": 930, "s": .75, "z": 5, "in": "b12:comentarios", "fx_in": "pop", "idle": "bob"},
    {"texto": {"t": "SEGUIR", "size": 76, "color": "#FFFFFF", "box": "#FF5D5D"}, "x": 740, "y": 1170, "z": 5, "in": "b12:síguenos",
     "fx_in": "pop", "idle": {"fx": "pulse", "fuerza": .8}},
    {"texto": {"t": "PARTE 4", "size": 150, "color": "#FFFFFF", "box": "#FF5D5D"}, "x": 540, "y": 580, "r": -6, "z": 7,
     "in": "b12:parte", "fx_in": "pop", "sfx": "golpe", "idle": {"fx": "pulse", "fuerza": .6}},
]}

doc = {"velocidad": 1.0, "cola": 1.2, "volumen_efectos": .5,
       "subtitulos": {"activos": True, "y": 1470, "size": 76},
       "estilos": estilos, "narracion": [{"texto": t} for t in narr], "persistentes": persist,
       "escenas": [e0, e1, e2, e3, e4, e5],
       "audio_voz": "audio/voz.wav", "palabras_json": "audio/palabras.json"}
json.dump(doc, open(OUT, "w"), ensure_ascii=False, indent=1)
print("ok")
