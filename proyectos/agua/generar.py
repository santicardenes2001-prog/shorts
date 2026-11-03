"""Genera escenas.json del short "¿Por qué hay tanta agua en la Tierra?".

    python proyectos/agua/generar.py
Calcula algunas posiciones (el tachón sobre "TANTA", los números del tablero) con la fuente real.
"""
import json
import os

from PIL import ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
FONT = os.path.join(ROOT, "fonts", "LilitaOne-Regular.ttf")
INK = "#24201F"
ROJO, AMARILLO, VERDE = "#FF5D5D", "#FFD23F", "#46C281"
RS = 1.5

TABLERO = {1: (265, 640), 2: (815, 640), 3: (540, 1060)}

NARRACION = [
    "La Tierra no debería tener ni una gota de agua.",                                               # b0 gancho
    "Nació tan cerca del Sol que el hielo no aguantaba.",                                           # b1
    "¿Entonces de dónde salió? Hay tres sospechosos, y el que hoy gana fuerza estuvo aquí desde el principio.",  # b2 intro
    "Uno: los cometas, bolas de hielo sucio.",                                                      # b3 cuerpo 1
    "En 2014, una sonda midió uno y su agua no coincidía con la nuestra.",                          # b4
    "Caso cerrado… hasta que en 2024 descubrieron que el polvo había alterado la medición.",        # b5
    "Pero había otro favorito.",                                                                    # b6 bucle 1
    "Dos: los asteroides. Su agua sí coincide.",                                                    # b7 cuerpo 2
    "Pero el polvo lunar de las misiones Apolo mostró que los que cayeron tarde trajeron muy poca.",  # b8
    "Y el tercero es el que nadie revisaba.",                                                       # b9 bucle 2
    "Tres: la propia Tierra.",                                                                      # b10 cuerpo 3
    "Las rocas que la formaron traían hidrógeno escondido, como para llenar los océanos tres veces.",  # b11
    "Y en 2026, un laboratorio calentó roca seca a más de mil grados con hidrógeno, y salió vapor de agua.",  # b12
    "La Tierra pudo fabricar su propia agua.",                                                      # b13
    "¿Y el título? Era una trampa: toda el agua del planeta cabe en una bola de unos mil cuatrocientos kilómetros, ni la mitad de la Luna.",  # b14 revelación
    "Y parte de esa agua sería más vieja que el Sol.",                                              # b15
    "Sígueme y te cuento cómo en el próximo.",                                                      # b16 llamado
]

ESTILOS = {
    "titulo": {"size": 74, "box": "#FFFFFF", "color": INK},
    "header": {"size": 64, "box": "#FFFFFF", "color": INK},
    "numero": {"size": 72, "box": AMARILLO, "color": INK, "circle": True, "pad": [22, 14]},
    "dato": {"size": 78, "box": AMARILLO, "color": INK},
    "sello": {"size": 82, "box": "#FFFFFF", "color": ROJO, "box_stroke": 8},
    "foto_num": {"size": 60, "color": INK, "stroke": 0},
}

TITULO = "¿POR QUÉ HAY\nTANTA AGUA\nEN LA TIERRA?"
TITULO_XY = (540, 330)


def T(t, estilo, **kw):
    return dict({"t": t, "estilo": estilo}, **kw)


def tachon_spec():
    """Ubica el tachón justo sobre "TANTA" (misma geometría que render_text del motor)."""
    sp = ESTILOS["titulo"]
    k = RS
    font = ImageFont.truetype(FONT, int(sp["size"] * k))
    lines = TITULO.split("\n")
    asc, desc = font.getmetrics()
    lh = (asc + desc) * 0.92
    pady = 18 * k
    bh = lh * len(lines) + 2 * pady
    img_h = bh + 8 * k + 10 * k                       # + sombra
    top = TITULO_XY[1] - img_h / k / 2
    cy = top + (4 * k + pady + lh * 1.5 + 3 * k) / k  # centro de la línea 2
    line_w = font.getlength(lines[1]) / k
    w_tanta = font.getlength("TANTA") / k
    left = TITULO_XY[0] - line_w / 2
    s = (w_tanta + 34) / 388
    return {"x": round(left - 17 - 16 * s, 1), "y": round(cy - 6, 1), "s": round(s, 3)}


def foto_xy(n, dy=0):
    x, y = TABLERO[n]
    return x, y + dy


def tablero(foto3="foto_misterio", con_entrada=False, extra_t=None):
    """Fotos, números e hilos del tablero. Con entrada animada solo en la escena de los sospechosos."""
    els = []
    tiempos = {1: "b2:Hay", 2: "b2:tres", 3: "b2:sospechosos"}
    assets = {1: "foto_cometa", 2: "foto_asteroide", 3: foto3}
    for n in (1, 2, 3):
        x, y = foto_xy(n)
        e = {"a": assets[n], "x": x, "y": y, "z": 2}
        nx, ny = foto_xy(n, 128)
        num = {"texto": T(str(n), "foto_num"), "x": nx, "y": ny, "z": 3}
        if con_entrada:
            e.update({"in": tiempos[n], "fx_in": "pop"})
            num.update({"in": tiempos[n] + "+0.12", "fx_in": "pop", "sfx": "none"})
        els += [e, num]
    h = {"a": "hilos", "x": 540, "y": 960, "z": 2.5}
    if con_entrada:
        h.update({"in": "b2:sospechosos+0.3", "fx_in": "wipe", "dur_in": 0.7})
    els.append(h)
    return els


def lupa_sobre(n):
    x, y = foto_xy(n, -27)
    return x, y


def vos_tablero(asset="vosdet_mira", **kw):
    return dict({"a": asset, "x": 175, "y": 1340, "s": 0.55, "blink": True, "idle": "breathe", "z": 4}, **kw)


def header(num, titulo, tin, tout):
    """Número y título del sospechoso, centrados como un solo grupo."""
    font = ImageFont.truetype(FONT, ESTILOS["header"]["size"])
    w_t = font.getlength(titulo) + 2 * 34 + 8
    d_num, gap = 110, 22
    x0 = 540 - (d_num + gap + w_t) / 2
    xn, xt = x0 + d_num / 2, x0 + d_num + gap + w_t / 2
    return [
        {"texto": T(str(num), "numero"), "x": round(xn), "y": 250, "in": tin, "out": tout, "fx_in": "pop", "fx_out": "pop", "z": 60},
        {"texto": T(titulo, "header"), "x": round(xt), "y": 250, "in": tin + "+0.1", "out": tout, "fx_in": "slide_left",
         "fx_out": "fade", "z": 60, "sfx": "none"},
    ]


def off(ref, dt):
    """Referencia de palabra con desplazamiento numérico (una sola suma)."""
    return f"{ref}{dt:+.2f}"


def meteoros(t0, base=0.0, n=5):
    out = []
    starts = [(60, 560), (360, 470), (620, 560), (180, 760), (470, 700)]
    for i in range(n):
        x, y = starts[i % len(starts)]
        t = off(t0, base + 0.16 * i)
        out.append({"a": "meteorito", "x": x, "y": y, "s": 1.1, "in": t, "out": off(t0, base + 0.16 * i + 0.8),
                    "keys": [{"at": t, "dur": 0.75, "x": x + 560, "y": y + 560, "ease": "in"}],
                    "sfx": "whoosh_suave" if i % 2 == 0 else "none", "z": 6})
    return out


def rocas_a_tierra(cx, cy):
    tray = [((90, 460), (cx - 150, cy - 120)), ((990, 480), (cx + 150, cy - 120)),
            ((110, 1180), (cx - 160, cy + 120)), ((900, 1200), (cx + 160, cy + 120)), ((540, 1300), (cx, cy + 180))]
    tiempos = [("b11:rocas", -0.1), ("b11:rocas", 0.15), ("b11:que", 0), ("b11:formaron", 0), ("b11:formaron", 0.25)]
    out = []
    for i, ((x0, y0), (x1, y1)) in enumerate(tray):
        t = off(*tiempos[i])
        out.append({"a": f"roca_{i % 3}", "x": x0, "y": y0, "s": 1.6, "r": 20 * i, "in": t, "out": off(tiempos[i][0], tiempos[i][1] + 0.5),
                    "keys": [{"at": t, "dur": 0.5, "x": x1, "y": y1, "s": 0.95, "r": 20 * i + 90, "ease": "in"}],
                    "sfx": "whoosh_suave", "z": 6})
    return out


def escenas():
    tac = tachon_spec()
    E = []

    # ------------------------------------------------ 0 · gancho
    gotas = []
    for i, (dx, dy) in enumerate([(-330, -260), (330, -240), (-360, 120), (360, 160), (0, 380)]):
        gotas.append({"a": "gota_tierra", "x": 540, "y": 930, "s": 0.55, "in": "b0:gota", "out": "b0:gota+0.9",
                      "keys": [{"at": "b0:gota", "dur": 0.8, "x": 540 + dx, "y": 930 + dy, "r": dx / 6, "ease": "out"},
                               {"at": "b0:gota+0.55", "dur": 0.3, "alpha": 0.0}],
                      "sfx": "pop" if i == 0 else "none", "z": 4})
    E.append({"nombre": "gancho", "beats": [0], "fondo": "fondo_espacio", "elementos": [
        {"a": "tierra", "x": 540, "y": 930, "s": 1.4, "in": 0, "fx_in": "pop", "idle": "float",
         "swaps": [{"at": "b0:no", "a": "tierra_sorpresa"},
                   {"at": "b0:gota", "a": "tierra_seca", "fx": "punch"}],
         "keys": [{"at": "b0:gota", "dur": 0.15, "s": 1.25, "ease": "out"},
                  {"at": "b0:gota+0.15", "dur": 0.3, "s": 1.4, "ease": "back"}], "z": 5},
    ] + gotas})

    # ------------------------------------------------ 1 · cerca del Sol
    hielo = [f"hielo_{i}" for i in range(8)]
    E.append({"nombre": "nace", "beats": [1], "fondo": "fondo_espacio", "elementos": [
        {"a": "sol", "x": 120, "y": 960, "s": 2.6, "in": "esc", "fx_in": "slide_right", "idle": ["pulse", {"fx": "spin", "vel": 12}], "z": 1},
        {"a": "tierra_lava", "x": 690, "y": 980, "s": 1.05, "in": "b1:Nació", "fx_in": "pop", "idle": {"fx": "shake", "fuerza": 0.35}, "z": 3},
        {"a": "hielo_0", "x": 690, "y": 690, "s": 1.0, "in": "b1:hielo-0.15", "fx_in": "drop", "dur_in": 0.45,
         "seq": {"frames": hielo, "at": "b1:no", "dur": 0.85, "ease": "linear"}, "idle": {"fx": "shake", "fuerza": 0.4}, "z": 4},
    ]})

    # ------------------------------------------------ 2 · tres sospechosos
    lx, ly = 345, 1135
    E.append({"nombre": "sospechosos", "beats": [2], "fondo": "fondo_corcho", "flash": True, "elementos":
        tablero("foto_misterio", con_entrada=True) + [
        vos_tablero("vosdet_sorpresa", **{"in": "esc", "fx_in": "jump",
                    "swaps": [{"at": "b2:Hay", "a": "vosdet_mira"}, {"at": "b2:gana", "a": "vosdet_sorpresa", "fx": "punch"}]}),
        {"a": "lupa", "x": lx, "y": ly, "s": 0.6, "flip": True, "in": "esc+0.15", "fx_in": "pop", "idle": "sway", "z": 5},
        {"a": "exclamacion", "x": 760, "y": 900, "s": 0.55, "r": 14, "in": "b2:gana", "fx_in": "pop", "idle": "wiggle", "z": 6},
    ]})
    # el sospechoso 3 late cuando se dice que gana fuerza
    E[-1]["elementos"][4]["idle"] = {"fx": "pulse", "from": "b2:gana", "fuerza": 0.8}

    # ------------------------------------------------ 3 · cometas
    E.append({"nombre": "cometas", "beats": [3, 4, 5], "fondo": "fondo_espacio", "flash": True, "elementos": [
        {"a": "cometa", "x": 640, "y": 780, "s": 1.25, "in": "b3:cometas-0.15", "fx_in": "slide_right", "idle": "float",
         "keys": [{"at": "b4", "dur": 0.6, "x": 760, "y": 760, "s": 1.0}],
         "swaps": [{"at": "b4:no", "a": "cometa_enojado", "fx": "punch"}, {"at": "b5:polvo", "a": "cometa"}], "z": 3},
        {"texto": T("2014", "dato"), "x": 540, "y": 470, "in": "b4:2014", "out": "b5", "fx_in": "pop", "fx_out": "pop", "z": 8},
        {"a": "sonda", "x": 250, "y": 600, "s": 0.95, "in": "b4:sonda-0.1", "out": "b5", "fx_in": "slide_right", "fx_out": "fade",
         "idle": "bob", "z": 4},
        {"a": "rayo", "x": 520, "y": 690, "s": 0.5, "r": 18, "in": "b4:midió", "out": "b5", "fx_in": "wipe",
         "dur_in": 0.4, "fx_out": "fade", "z": 2},
        {"a": "gota_cometa", "x": 330, "y": 1130, "s": 1.0, "in": "b4:agua", "out": "b5:cerrado", "fx_in": "pop", "fx_out": "pop",
         "idle": "bob", "z": 5},
        {"a": "gota_tierra", "x": 750, "y": 1130, "s": 1.0, "in": "b4:agua+0.2", "out": "b5:cerrado", "fx_in": "pop",
         "fx_out": "pop", "idle": "bob", "z": 5},
        {"a": "cruz", "x": 540, "y": 1140, "s": 0.85, "in": "b4:coincidía", "out": "b5:cerrado", "fx_in": "pop", "fx_out": "pop",
         "sfx": "boing", "z": 6},
        {"texto": T("CASO\nCERRADO", "sello"), "x": 540, "y": 1080, "r": -10, "in": "b5", "fx_in": "pop", "sfx": "boing",
         "keys": [{"at": "b5:alterado", "dur": 0.7, "y": 2300, "r": 35, "ease": "in", "sfx": "whoosh"}], "z": 9},
        {"texto": T("2024", "dato"), "x": 540, "y": 470, "in": "b5:2024", "fx_in": "pop", "z": 8},
        {"a": "nube_polvo", "x": 560, "y": 1000, "s": 0.85, "in": "b5:polvo-0.1", "fx_in": "slide_left", "idle": "float", "z": 4},
        {"texto": T("?", "numero", box="#FFFFFF"), "x": 905, "y": 640, "in": "b5:medición", "fx_in": "pop", "idle": "wiggle", "z": 8},
    ]})

    # ------------------------------------------------ 4 · bucle 1
    (x1, y1), (x2, y2) = lupa_sobre(1), lupa_sobre(2)
    E.append({"nombre": "bucle1", "beats": [6], "fondo": "fondo_corcho", "elementos": tablero() + [
        vos_tablero("vosdet_mira"),
        {"a": "lupa", "x": x1, "y": y1, "s": 0.85, "in": "esc", "fx_in": "pop", "z": 7,
         "keys": [{"at": "b6:otro", "dur": 0.55, "x": x2, "y": y2, "sfx": "whoosh_suave"}]},
    ]})

    # ------------------------------------------------ 5 · asteroides
    E.append({"nombre": "asteroides", "beats": [7, 8], "fondo": "fondo_espacio", "flash": True, "elementos": [
        {"a": "asteroide", "x": 540, "y": 760, "s": 1.45, "in": "b7:asteroides-0.15", "out": "b8", "fx_in": "drop",
         "fx_out": "pop", "idle": "float", "swaps": [{"at": "b7:coincide", "a": "asteroide_feliz", "fx": "punch"}], "z": 3},
        {"a": "gota_tierra", "x": 320, "y": 1140, "s": 1.0, "in": "b7:agua", "out": "b8", "fx_in": "pop", "fx_out": "pop", "idle": "bob", "z": 5},
        {"a": "gota_tierra_feliz", "x": 760, "y": 1140, "s": 1.0, "in": "b7:agua+0.2", "out": "b8", "fx_in": "pop", "fx_out": "pop",
         "idle": "bob", "z": 5},
        {"a": "tilde", "x": 540, "y": 1150, "s": 0.85, "in": "b7:coincide", "out": "b8", "fx_in": "pop", "fx_out": "pop", "sfx": "ding", "z": 6},
        {"a": "luna_llena", "x": 290, "y": 700, "s": 0.9, "in": "b8:lunar", "fx_in": "pop", "idle": "float", "z": 2},
        {"a": "bolsa_muestras", "x": 740, "y": 800, "s": 0.95, "in": "b8:Apolo-0.1", "fx_in": "jump", "idle": "sway", "z": 4},
        {"texto": {"t": "APOLO", "size": 40, "color": INK, "stroke": 0}, "x": 740, "y": 762, "in": "b8:Apolo-0.1", "fx_in": "jump",
         "idle": "sway", "sfx": "none", "z": 5},
        {"a": "frasco_00", "x": 540, "y": 1300, "s": 0.9, "in": "b8:trajeron-0.1", "fx_in": "pop",
         "seq": {"frames": ["frasco_00", "frasco_01"], "at": "b8:muy", "dur": 0.3}, "z": 7},
    ] + meteoros("b8:cayeron", -0.15)})

    # ------------------------------------------------ 6 · bucle 2 y revelación del sospechoso 3
    (x3, y3) = lupa_sobre(3)
    fx3, fy3 = foto_xy(3)
    els6 = tablero("foto_misterio_polvo") + [
        vos_tablero("vosdet_mira", swaps=[{"at": "b10:propia", "a": "vosdet_sorpresa", "fx": "punch"}]),
        {"a": "lupa", "x": x2, "y": y2, "s": 0.85, "in": "esc", "out": "b10", "fx_in": "none", "fx_out": "pop", "z": 7,
         "keys": [{"at": "b9:tercero", "dur": 0.6, "x": x3, "y": y3, "sfx": "whoosh_suave"}]},
        {"a": "nube_polvo", "x": fx3, "y": fy3, "s": 0.8, "in": "b10-0.05", "out": "b10+0.7", "fx_in": "pop", "fx_out": "fade",
         "dur_out": 0.4, "keys": [{"at": "b10", "dur": 0.7, "x": fx3 + 320, "y": fy3 - 120, "s": 1.2, "ease": "out"}], "z": 8},
    ]
    for e in els6:
        if e.get("a") == "foto_misterio_polvo":
            e["swaps"] = [{"at": "b10+0.1", "a": "foto_tierra", "fx": "punch"}]
            e["idle"] = {"fx": "pulse", "from": "b10+0.1"}
    E.append({"nombre": "bucle2", "beats": [9, 10], "fondo": "fondo_corcho", "elementos": els6})

    # ------------------------------------------------ 7 · las rocas que la formaron
    cx, cy = 540, 780
    burbujas = []
    for i, (bx, by) in enumerate([(300, 620), (790, 600), (250, 880), (830, 900), (540, 520)]):
        burbujas.append({"a": "burbuja_h", "x": bx, "y": by, "s": 0.9, "in": f"b11:hidrógeno+{0.12 * i:.2f}", "fx_in": "pop",
                         "idle": "float", "sfx": "pop" if i < 3 else "none", "z": 7})
    frascos = []
    llenado = ["b11:océanos-0.1", "b11:océanos+0.25", "b11:tres"]
    for i, fxp in enumerate([290, 540, 790]):
        frascos.append({"a": "frasco_00", "x": fxp, "y": 1300, "s": 0.8, "in": f"b11:llenar+{0.1 * i:.2f}", "fx_in": "pop",
                        "seq": {"frames": [f"frasco_{k:02d}" for k in range(11)], "at": llenado[i], "dur": 0.55}, "z": 7})
    E.append({"nombre": "rocas", "beats": [11], "fondo": "fondo_espacio", "flash": True, "elementos": [
        {"a": "tierra_lava", "x": cx, "y": cy, "s": 0.72, "in": "esc", "fx_in": "pop", "idle": {"fx": "shake", "fuerza": 0.2},
         "keys": [{"at": "b11:rocas+0.35", "dur": 0.2, "s": 0.8, "ease": "back"},
                  {"at": "b11:que+0.45", "dur": 0.2, "s": 0.88, "ease": "back"},
                  {"at": "b11:formaron+0.45", "dur": 0.2, "s": 0.96, "ease": "back"},
                  {"at": "b11:formaron+0.75", "dur": 0.2, "s": 1.02, "ease": "back"}],
         "swaps": [{"at": "b11:océanos", "a": "tierra_contenta", "fx": "punch"}], "z": 4},
    ] + rocas_a_tierra(cx, cy) + burbujas + frascos})

    # ------------------------------------------------ 8 · laboratorio
    hx, hy = 540, 1190
    win = (hx - 68, hy - 230)
    burb_lab = []
    for i, (bx, by) in enumerate([(250, 700), (540, 600), (830, 690)]):
        t = off("b12:hidrógeno", 0.1 * i)
        burb_lab.append({"a": "burbuja_h", "x": bx, "y": by, "s": 0.85, "in": t, "out": off("b12:hidrógeno", 0.1 * i + 0.95),
                         "fx_in": "pop",
                         "keys": [{"at": off("b12:hidrógeno", 0.1 * i + 0.3), "dur": 0.6, "x": win[0], "y": win[1], "s": 0.3,
                                   "ease": "in"}],
                         "sfx": "pop" if i == 0 else "none", "z": 9})
    E.append({"nombre": "laboratorio", "beats": [12, 13], "fondo": "fondo_lab", "flash": True, "elementos": [
        {"texto": T("2026", "dato"), "x": 540, "y": 470, "in": "b12:2026", "out": "b12:mil", "fx_in": "pop", "fx_out": "pop", "z": 8},
        {"a": "horno", "x": hx, "y": hy, "s": 1.2, "in": "b12:laboratorio-0.1", "out": "b13", "fx_in": "slide_up", "fx_out": "pop",
         "idle": {"fx": "shake", "fuerza": 0.25, "from": "b12:calentó"}, "z": 3},
        {"texto": {"t": "1200°", "size": 38, "color": ROJO, "stroke": 0}, "x": hx + 172, "y": hy - 345, "in": "b12:calentó",
         "out": "b13", "fx_in": "fade", "sfx": "none", "z": 4},
        {"a": "termometro", "x": 925, "y": 790, "s": 0.95, "in": "b12:calentó", "out": "b13", "fx_in": "jump", "fx_out": "pop",
         "idle": {"fx": "shake", "fuerza": 0.3, "from": "b12:mil"}, "z": 4},
        {"a": "roca_1", "x": 300, "y": 760, "s": 0.9, "in": "b12:roca", "out": "b12:roca+1.0", "fx_in": "pop",
         "keys": [{"at": "b12:seca", "dur": 0.55, "x": win[0], "y": win[1], "s": 0.3, "r": 120, "ease": "in"}], "z": 9},
        {"texto": T("+1.000 °C", "dato", box=ROJO, color="#FFFFFF"), "x": 540, "y": 470, "in": "b12:mil", "out": "b12:vapor",
         "fx_in": "pop", "fx_out": "pop", "sfx": "ding", "z": 8},
        {"a": "vapor_a", "x": hx - 40, "y": hy - 520, "s": 0.8, "in": "b12:vapor-0.1", "out": "b13", "fx_in": "grow",
         "fx_out": "fade", "loop": {"frames": ["vapor_a", "vapor_b"], "fps": 4},
         "keys": [{"at": "b12:vapor", "dur": 1.0, "y": hy - 620, "s": 1.25, "ease": "out"}], "sfx": "whoosh_suave", "z": 6},
        {"a": "gota_tierra_feliz", "x": 820, "y": 560, "s": 0.85, "in": "b12:agua", "out": "b13", "fx_in": "pop", "fx_out": "pop",
         "idle": "bob", "sfx": "ding", "z": 7},
        # b13: la Tierra fabrica su agua
        {"a": "tierra_contenta", "x": 540, "y": 860, "s": 1.15, "in": "b13", "fx_in": "pop", "idle": "float", "z": 5},
        {"a": "gota_tierra_feliz", "x": 230, "y": 700, "s": 0.75, "in": "b13:fabricar", "fx_in": "pop", "idle": "bob", "z": 6},
        {"a": "gota_tierra", "x": 850, "y": 690, "s": 0.75, "in": "b13:propia", "fx_in": "pop", "idle": "bob", "z": 6},
        {"a": "gota_tierra_feliz", "x": 540, "y": 1240, "s": 0.7, "in": "b13:agua", "fx_in": "pop", "idle": "bob", "z": 6},
    ] + burb_lab})

    # ------------------------------------------------ 9 · revelación
    E.append({"nombre": "revelacion", "beats": [14], "fondo": "fondo_espacio", "flash": True, "elementos": [
        {"texto": T(TITULO, "titulo"), "x": TITULO_XY[0], "y": TITULO_XY[1], "in": "esc", "fx_in": "pop", "z": 8},
        {"a": "tachon", "x": tac["x"], "y": tac["y"], "s": tac["s"], "in": "b14:trampa", "fx_in": "wipe", "dur_in": 0.35,
         "sfx": "whoosh", "z": 9},
        {"a": "tierra_seca", "x": 400, "y": 930, "s": 1.3, "in": "b14:toda", "fx_in": "pop", "idle": "float", "z": 3},
        {"a": "bola_agua", "x": 760, "y": 720, "s": 0.95, "in": "b14:bola", "fx_in": "pop", "z": 5,
         "keys": [{"at": "b14:mil", "dur": 0.6, "x": 755, "y": 930, "s": 0.32, "ease": "inout", "sfx": "zoom"}]},
        {"texto": T("1.400 km", "dato", size=52), "x": 755, "y": 1050, "in": "b14:kilómetros", "fx_in": "pop", "z": 7},
        {"a": "luna_llena", "x": 895, "y": 930, "s": 0.374, "in": "b14:ni", "fx_in": "pop", "z": 5},
        {"texto": T("LUNA", "foto_num", size=40, color="#FFFFFF", stroke=8), "x": 895, "y": 840, "in": "b14:mitad", "fx_in": "pop",
         "sfx": "none", "z": 7},
    ]})

    # ------------------------------------------------ 10 · más vieja que el Sol
    E.append({"nombre": "vieja", "beats": [15], "fondo": "fondo_espacio", "elementos": [
        {"a": "gota_tierra_feliz", "x": 330, "y": 880, "s": 1.35, "in": "b15", "fx_in": "pop", "idle": "bob", "z": 4},
        {"a": "sol", "x": 760, "y": 640, "s": 1.15, "in": "b15:Sol-0.1", "fx_in": "pop", "idle": "pulse", "z": 2},
        {"a": "reloj_arena", "x": 740, "y": 920, "s": 0.95, "in": "b15:vieja-0.1", "fx_in": "jump", "idle": "wiggle", "z": 5},
    ]})

    # ------------------------------------------------ 11 · llamado a la acción
    E.append({"nombre": "cierre", "beats": [16], "fondo": "fondo_burst", "flash": True, "elementos": [
        {"texto": T("¡SÍGUEME!", "dato", size=96, box=ROJO, color="#FFFFFF"), "x": 540, "y": 400, "in": "b16:Sígueme", "fx_in": "pop",
         "idle": "pulse", "z": 8},
        {"texto": T("PRÓXIMO: EL AGUA\nMÁS VIEJA QUE EL SOL", "header", size=50), "x": 540, "y": 590, "in": "b16:próximo-0.2",
         "fx_in": "slide_left", "z": 8},
        {"a": "vosdet_pulgar", "x": 540, "y": 1340, "s": 0.78, "in": "esc", "fx_in": "jump", "idle": "breathe", "z": 5},
    ]})
    return E


def main():
    doc = {
        "cola": 1.3,
        "volumen_efectos": 0.5,
        "subtitulos": {"activos": True, "y": 1470, "size": 78},
        "estilos": ESTILOS,
        "narracion": [{"texto": t} for t in NARRACION],
        "persistentes": [
            {"texto": T(TITULO, "titulo"), "x": TITULO_XY[0], "y": TITULO_XY[1], "in": 0, "out": "e2", "fx_in": "pop",
             "sfx": "none", "z": 60},
        ] + header(1, "LOS COMETAS", "b3", "b5>")
          + header(2, "LOS ASTEROIDES", "b7", "b8>")
          + header(3, "LA PROPIA TIERRA", "b11", "b13>"),
        "escenas": escenas(),
        "audio_voz": "audio/voz.wav",
        "palabras_json": "audio/palabras.json",
    }
    with open(os.path.join(AQUI, "escenas.json"), "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("escenas.json listo")


if __name__ == "__main__":
    main()
