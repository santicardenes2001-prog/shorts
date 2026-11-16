"""Short "Cocinarse a 270 grados bajo cero" — animación procedural (armazón de altura.py).

Estilo del canal: fondo azul con puntos (oscuro en el espacio), cosas con cara (el termómetro, las bolitas de calor y
de aire, el cubito) y subtítulos palabra por palabra. Vos sale solo en la Tierra (apertura) y el cierre vuelve al
primer cuadro: el cuadro de TOTAL es igual al de 0. Sin flechas de giro ni sonidos sostenidos: solo golpes cortos.

Hilos que se repiten: las bolitas rojas de calor (salen del cuerpo; en la Tierra se las lleva el aire, en el espacio
quedan adentro), las bolitas de aire tachadas donde no hay aire y el medidor de calor del pecho del traje.

    python proyectos/astronauta/astronauta.py --hoja 0,3,6      # hoja de fotogramas -> proyectos/astronauta/fotos/hoja.png
    python proyectos/astronauta/astronauta.py --probar
    python proyectos/astronauta/astronauta.py                   # render -> salidas/cocinarse_a_270_bajo_cero.mp4
"""
import argparse
import functools
import io
import json
import math
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from multiprocessing import Pool

import cairo
import cairosvg
import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
for _p in (ROOT, os.path.join(ROOT, "proyectos", "pantalla"), os.path.join(ROOT, "proyectos", "picante"),
           os.path.join(ROOT, "proyectos", "cielo")):
    sys.path.insert(0, _p)
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
import picante as K  # noqa: E402
import cielo as C  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, rng, rrect, texto)
from picante import _elipse_suave, capa, fondo_azul, mezcla  # noqa: E402

W, H, FPS, SR = 1080, 1920, 30, 48000
TAU = 2 * math.pi

NARRACION = [
    "El espacio está a 270 grados bajo cero.",                                                  # b0
    "Y aun así, un astronauta afuera de la nave se puede cocinar.",                              # b1
    "¿Cómo te cocinas a 270 bajo cero?",                                                        # b2
    "En la Tierra te enfrías porque el aire se lleva tu calor.",                                 # b3
    "En el espacio no hay aire que se lo lleve.",                                               # b4
    "Es como un termo: entre sus paredes no hay aire, y por eso el café sigue caliente durante horas.",  # b5
    "El astronauta es el café.",                                                                # b6
    "Cada esfuerzo lo calienta un poco más.",                                                   # b7
    "Por eso, debajo del traje lleva una malla con más de 70 metros de tubitos con agua fría.",  # b8
    "Pero esa agua también se calienta.",                                                       # b9
    "¿Dónde tira el calor, si afuera no hay nada?",                                             # b10
    "Lo tira con hielo.",                                                                       # b11
    "El traje deja salir un poco de agua a una placa abierta al vacío.",                        # b12
    "Ahí se congela, y el hielo se evapora directo al espacio, llevándose el calor.",           # b13
    "Para no cocinarse en el lugar más frío que existe, el traje fabrica hielo.",               # b14
    "Aunque afuera,",                                                                           # b15
]
WORDS = motor.align_times([{"texto": t} for t in NARRACION],
                          json.load(open(os.path.join(AQUI, "audio", "palabras.json"))))
COLA = 0.3
TOTAL = WORDS[-1][-1]["end"] + COLA


def b(i, palabra=None, fin=False, n=0):
    ws = WORDS[i]
    if palabra is None:
        return ws[-1]["end"] if fin else ws[0]["start"]
    obj = motor.norm(palabra)
    cand = [w for w in ws if w["n"] == obj] or [w for w in ws if w["n"].startswith(obj)]
    if not cand:
        raise ValueError(f"no está {palabra!r} en b{i}")
    w = cand[min(n, len(cand) - 1)]
    return w["end"] if fin else w["start"]


# ------------------------------------------------------------------ colores
ROJO = hx("#E5383B")
VERDE = hx("#2BD45A")
NARANJA = hx("#FF8A3D")
CREMA = hx("#F6EEDC")
ACERO = hx("#D5DAE2")
ACERO_OSC = hx("#8E97A8")
TRAJE = hx("#F3F5F8")
TRAJE_OSC = hx("#C3CAD6")
VISOR = hx("#22345C")
PANEL = hx("#2F5FB8")
PANEL_CLARO = hx("#5C8FE8")
LCD = hx("#7CFF8A")
CALOR = hx("#FF4A2E")
CALOR_CLARO = hx("#FFB347")
FRIO = hx("#5EC8FF")
FRIO_OSC = hx("#2E7FD6")
HIELO = hx("#E8F7FF")
HIELO_OSC = hx("#9ED5F5")
AIRE = hx("#D6F1FF")
CAFE = hx("#6B3E22")
CAFE_CLARO = hx("#9A6236")
TERMO_COL = hx("#2F9E6B")
TERMO_OSC = hx("#1F7550")
VACIO = hx("#0B1030")
CIELO_DIA = hx("#8FD3FF")
CIELO_DIA2 = hx("#D4F0FF")
PASTO = hx("#5BC46A")
PASTO_OSC = hx("#3E9E50")
MOCHILA = hx("#E4E8EF")
MOCHILA_IN = hx("#C7D0DE")
KF = 60 * round(14 * TOTAL / 60) / (14 * TOTAL)      # el fondo de puntos cierra justo en el loop


# ------------------------------------------------------------------ ayudas
@contextmanager
def en(ctx, x, y, s=1.0, rot=0.0):
    ctx.save()
    ctx.translate(x, y)
    if rot:
        ctx.rotate(rot)
    s = max(s, 1e-3)
    ctx.scale(s, s)
    try:
        yield
    finally:
        ctx.restore()


@contextmanager
def alfa(ctx, a):
    if a >= 0.999:
        yield
        return
    ctx.push_group()
    try:
        yield
    finally:
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(a))


def trazo(ctx, col=INK, w=7.0, a=1.0):
    ctx.set_source_rgba(*col, a)
    ctx.set_line_width(w)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()


def rellena(ctx, col, w=7.0, borde=INK, a=1.0):
    ctx.set_source_rgba(*col, a)
    ctx.fill_preserve()
    trazo(ctx, borde, w, a)


def elipse(ctx, x, y, rx, ry):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(max(rx, 1e-3), max(ry, 1e-3))
    ctx.new_sub_path()
    ctx.arc(0, 0, 1, 0, TAU)
    ctx.restore()


def fondo(ctx, t, oscuro=0.0):
    fondo_azul(ctx, t * KF)
    if oscuro > 0:
        ctx.set_source_rgba(0.027, 0.043, 0.11, oscuro)
        ctx.paint()


def espacio(ctx, t, seed=9, n=70):
    fondo(ctx, t, 0.72)
    C.campo(ctx, t, seed=seed, n=n)


def sale(t, t1, d=0.2):
    return 1 - prog(t, t1, d, "in")


def zoom(ctx, z, cx=540, cy=900):
    z = max(z, 0.01)
    ctx.translate(cx, cy)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)


def kartel(ctx, txt, x, y, size, t, t0, t1=None, **kw):
    if t < t0:
        return
    s = pop(t, t0) * (sale(t, t1) if t1 is not None else 1.0)
    if s > 0.01:
        cartel(ctx, txt, x, y, size, s=s, **kw)


def sacudida(t, t0, d=0.35, amp=14.0):
    if t < t0 or t > t0 + d:
        return 0.0, 0.0
    q = (t - t0) / d
    k = amp * (1 - q) ** 2
    return k * math.sin(t * 90), k * math.cos(t * 70)


def sello(ctx, txt, x, y, size, t, t0, t1=None, rot=-8, col=ROJO):
    """Sello de goma que cae de golpe."""
    if t < t0:
        return
    q = clamp((t - t0) / 0.14)
    sc = lerp(2.4, 1.0, ease(q, "in"))
    a = min(1.0, q * 1.6) * (sale(t, t1) if t1 is not None else 1.0)
    if a <= 0.01:
        return
    with en(ctx, x, y, sc, math.radians(rot)), alfa(ctx, a):
        P.fuente(ctx, P.LILITA, size)
        tw = ctx.text_extents(txt)[4]
        bw, bh = tw + 80, size * 1.4
        rrect(ctx, -bw / 2, -bh / 2, bw, bh, 16)
        ctx.set_source_rgb(*CREMA)
        ctx.fill()
        rrect(ctx, -bw / 2, -bh / 2, bw, bh, 16)
        trazo(ctx, col, 11)
        rrect(ctx, -bw / 2 + 15, -bh / 2 + 15, bw - 30, bh - 30, 8)
        trazo(ctx, col, 4)
        texto(ctx, txt, 0, size * 0.04, size, fill=col, stroke=None)


def signo(ctx, txt, x, y, size, t, t0, t1=None, col=AMARILLO, sw=14):
    """Signo grande ("?", "!") que entra con rebote."""
    s = pop(t, t0, 0.35) * (sale(t, t1) if t1 is not None else 1.0)
    if t < t0 or s <= 0.01:
        return
    with en(ctx, x, y, s, math.radians(4 * math.sin((t - t0) * 6))):
        texto(ctx, txt, 0, 0, size, fill=col, sw=sw)


def linea_punteada(ctx, x0, y0, x1, y1, col=BLANCO, w=5, a=1.0):
    C.punteada(ctx, x0, y0, x1, y1, col, w=w, a=a)


# ------------------------------------------------------------------ polilíneas (tubitos)
def poli_cum(pts):
    d = [0.0]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d.append(d[-1] + math.hypot(x1 - x0, y1 - y0))
    return d


def poli_punto(pts, cum, s):
    s = clamp(s, 0, cum[-1])
    for i in range(1, len(cum)):
        if cum[i] >= s:
            q = (s - cum[i - 1]) / max(cum[i] - cum[i - 1], 1e-6)
            return lerp(pts[i - 1][0], pts[i][0], q), lerp(pts[i - 1][1], pts[i][1], q)
    return pts[-1]


def poli_camino(ctx, pts, p=1.0):
    """Arma el camino de la fracción p de la polilínea (desde el principio)."""
    cum = poli_cum(pts)
    L = cum[-1] * clamp(p)
    if L <= 0.5:
        return False
    ctx.move_to(*pts[0])
    for i in range(1, len(pts)):
        if cum[i] <= L:
            ctx.line_to(*pts[i])
        else:
            x, y = poli_punto(pts, cum, L)
            ctx.line_to(x, y)
            break
    return True


# ------------------------------------------------------------------ personajes chicos
def bola_calor(ctx, x, y, r, a=1.0, cara="picara"):
    """Bolita de calor: roja, con cara pícara."""
    if a <= 0.01 or r <= 1:
        return
    with alfa(ctx, a):
        _elipse_suave(ctx, x, y, r * 2.3, r * 2.3, CALOR, 0.32)
        ctx.arc(x, y, r, 0, TAU)
        g = cairo.RadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r)
        g.add_color_stop_rgb(0, *CALOR_CLARO)
        g.add_color_stop_rgb(1, *CALOR)
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, max(2.5, r * 0.13))
        if r >= 13:
            if cara == "picara":
                C.cara(ctx, x, y, r, ojos="open", boca="grin", ceja="angry", look=(0.3, 0))
            elif cara == "susto":
                C.cara(ctx, x, y, r, ojos="wide", boca="o", ceja="worried")
            else:
                C.cara(ctx, x, y, r, ojos="happy", boca="grin")


def bola_aire(ctx, x, y, r, a=1.0, fantasma=False):
    """Bolita de aire: celeste con cara; fantasma = solo el contorno punteado (donde no hay aire)."""
    if a <= 0.01:
        return
    with alfa(ctx, a):
        if fantasma:
            ctx.arc(x, y, r, 0, TAU)
            ctx.set_dash([12, 10])
            trazo(ctx, BLANCO, 5, 0.85)
            ctx.set_dash([])
            return
        ctx.arc(x, y, r, 0, TAU)
        ctx.set_source_rgb(*AIRE)
        ctx.fill_preserve()
        trazo(ctx, INK, max(2.5, r * 0.12))
        ctx.arc(x - r * 0.35, y - r * 0.38, r * 0.22, 0, TAU)
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.fill()
        if r >= 13:
            C.cara(ctx, x, y + r * 0.05, r, ojos="dot", boca="smile")


def copo(ctx, x, y, r, a=1.0, rot=0.0):
    """Cristal de hielo de seis puntas."""
    if a <= 0.01 or r <= 1:
        return
    with en(ctx, x, y, 1.0, rot), alfa(ctx, a):
        for lw, col in ((r * 0.34, INK), (r * 0.17, HIELO)):
            for k in range(6):
                ang = k * TAU / 6
                ca, sa = math.cos(ang), math.sin(ang)
                ctx.move_to(0, 0)
                ctx.line_to(r * ca, r * sa)
                for f in (0.55,):
                    px, py = r * f * ca, r * f * sa
                    for sg in (-1, 1):
                        a2 = ang + sg * 0.75
                        ctx.move_to(px, py)
                        ctx.line_to(px + r * 0.32 * math.cos(a2), py + r * 0.32 * math.sin(a2))
            trazo(ctx, col, lw)


def cubito(ctx, x, y, s=1.0, a=1.0, rot=0.0):
    """Cubito de hielo con cara."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        _elipse_suave(ctx, 0, 0, 190, 190, FRIO, 0.35)
        rrect(ctx, -95, -95, 190, 190, 34)
        g = cairo.LinearGradient(-95, -95, 95, 95)
        g.add_color_stop_rgb(0, *hx("#FFFFFF"))
        g.add_color_stop_rgb(1, *HIELO_OSC)
        ctx.set_source(g)
        ctx.fill_preserve()
        trazo(ctx, INK, 8)
        ctx.move_to(-62, -70)
        ctx.line_to(-30, -70)
        trazo(ctx, BLANCO, 12)
        ctx.move_to(-70, -55)
        ctx.line_to(-70, -20)
        trazo(ctx, BLANCO, 12)
        C.cara(ctx, 0, 14, 80, ojos="happy", boca="grin")


def destello(ctx, x, y, r, t, t0, d=0.5):
    """Brillito de cuatro puntas que aparece y se va."""
    q = (t - t0) / d
    if q <= 0 or q >= 1:
        return
    s = math.sin(math.pi * q)
    C.estrella(ctx, x, y, r * s, a=1.0, col=BLANCO, halo=1.0)


def termometro(ctx, x, y_top, y_bot, f, a=1.0, ancho=60, bulbo=66, escarcha=0.0, cara=None, marcas=True,
               col=None, t=0.0):
    """Termómetro con cara en el bulbo. f = altura del líquido (0 abajo, 1 arriba). col por defecto va de azul a rojo."""
    if a <= 0.01:
        return
    col = col if col is not None else mezcla(FRIO_OSC, CALOR, clamp((f - 0.15) / 0.5))
    by = y_bot + bulbo * 0.78
    with alfa(ctx, a):
        # contorno (debajo) y vidrio
        for lw, c in ((14, INK), (0, BLANCO)):
            rrect(ctx, x - ancho / 2, y_top - ancho / 2, ancho, y_bot - y_top + ancho / 2, ancho / 2)
            ctx.new_sub_path()
            ctx.arc(x, by, bulbo, 0, TAU)
            if lw:
                trazo(ctx, c, lw)
            else:
                ctx.set_source_rgb(*c)
                ctx.fill()
        # líquido
        yl = lerp(y_bot, y_top, clamp(f))
        rrect(ctx, x - ancho * 0.22, yl, ancho * 0.44, by - yl, ancho * 0.22)
        ctx.set_source_rgb(*col)
        ctx.fill()
        ctx.arc(x, by, bulbo * 0.74, 0, TAU)
        ctx.set_source_rgb(*col)
        ctx.fill()
        if marcas:
            n = 9
            for k in range(n + 1):
                yy = lerp(y_bot, y_top, k / n)
                ctx.move_to(x + ancho / 2 - 4, yy)
                ctx.line_to(x + ancho / 2 + (24 if k % 3 == 0 else 13), yy)
                trazo(ctx, BLANCO, 5)
        # brillo del vidrio
        ctx.move_to(x - ancho * 0.3, y_top + 10)
        ctx.line_to(x - ancho * 0.3, y_bot - 20)
        trazo(ctx, BLANCO, 6, 0.55)
        if cara:
            r = bulbo * 0.74
            if cara == "frio":
                C.cara(ctx, x, by + 4, r * 1.25, ojos="wide", boca="wavy", ceja="worried")
            elif cara == "calor":
                C.cara(ctx, x, by + 4, r * 1.25, ojos="wide", boca="o", ceja="worried")
            elif cara == "bien":
                C.cara(ctx, x, by + 4, r * 1.25, ojos="happy", boca="grin")
            else:
                C.cara(ctx, x, by + 4, r * 1.25, ojos="open", boca="smile")
        if escarcha > 0.01:
            rr = rng(5)
            pts = [(x + rr.uniform(-1, 1) * (ancho / 2 + 6), rr.uniform(y_top, y_bot)) for _ in range(9)]
            pts += [(x + bulbo * math.cos(a_) * 1.02, by + bulbo * math.sin(a_) * 1.02)
                    for a_ in (3.6, 4.4, 5.3, 0.4)]
            for k, (px, py) in enumerate(pts):
                e = clamp(escarcha * 1.6 - k * 0.05)
                copo(ctx, px, py, 15 + 6 * (k % 3), a=e, rot=k * 0.7)


def nube(ctx, x, y, r, a):
    """Bocanada de vapor: tres círculos blancos con contorno suave."""
    if a <= 0.01 or r <= 1:
        return
    with alfa(ctx, a):
        for dx, dy, k in ((-0.55, 0.15, 0.7), (0.5, 0.2, 0.65), (0, -0.15, 0.9)):
            ctx.new_sub_path()
            ctx.arc(x + dx * r, y + dy * r, r * k, 0, TAU)
        ctx.set_source_rgba(*INK, 0.5)
        ctx.set_line_width(max(3, r * 0.12))
        ctx.stroke_preserve()
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()


def reloj_digital(ctx, x, y, s, hora):
    if s <= 0.01:
        return
    with en(ctx, x, y, s):
        rrect(ctx, -150, -66, 300, 132, 26)
        rellena(ctx, hx("#1A1F33"), 7)
        rrect(ctx, -128, -46, 256, 92, 14)
        ctx.set_source_rgb(*hx("#0E2A18"))
        ctx.fill()
        texto(ctx, f"{int(hora):02d}:00", 0, 2, 76, fill=LCD, stroke=None)


# ------------------------------------------------------------------ la estación y el astronauta
def estacion(ctx, x, y, s=1.0, a=1.0):
    """Estación espacial genérica: armazón, módulos y cuatro alas de paneles solares (de altura.py)."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s), alfa(ctx, a):
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0 = sx * 250 - 45
                y0 = -32 if sy < 0 else 32
                ctx.move_to(sx * 250, 0)
                ctx.line_to(sx * 250, sy * 32)
                trazo(ctx, INK, 6)
                yb = y0 if sy > 0 else y0 - 210
                rrect(ctx, x0, yb, 90, 210, 6)
                rellena(ctx, PANEL, 6)
                for k in range(1, 6):
                    ctx.move_to(x0 + 4, yb + 35 * k)
                    ctx.line_to(x0 + 86, yb + 35 * k)
                    trazo(ctx, PANEL_CLARO, 3)
                ctx.move_to(x0 + 45, yb + 4)
                ctx.line_to(x0 + 45, yb + 206)
                trazo(ctx, PANEL_CLARO, 3)
        rrect(ctx, -300, -10, 600, 20, 6)
        rellena(ctx, ACERO, 5)
        for k in range(-5, 6):
            ctx.move_to(k * 52 - 10, -10)
            ctx.line_to(k * 52 + 10, 10)
            trazo(ctx, ACERO_OSC, 3)
        rrect(ctx, -120, -36, 240, 72, 34)
        rellena(ctx, TRAJE, 6)
        rrect(ctx, -40, -70, 80, 140, 34)
        rellena(ctx, TRAJE, 6)
        for k in (-80, -40, 0, 40, 80):
            ctx.move_to(k, -32)
            ctx.line_to(k, 32)
            trazo(ctx, TRAJE_OSC, 3)
        elipse(ctx, 0, 70, 22, 10)
        rellena(ctx, ACERO_OSC, 4)


TOP = -560                      # hombros del astronauta (en su marco: las botas en 0)
MOCHILA_C = (0, -420)           # centro de la mochila
ASTRO_ALTO = 770


def _piernas_brazos(ctx):
    for lx in (-58, 58):
        rrect(ctx, lx - 50, -310, 100, 310 - 52, 36)
        rellena(ctx, TRAJE, 7)
        elipse(ctx, lx, -185, 40, 26)
        rellena(ctx, TRAJE_OSC, 5)
        rrect(ctx, lx - 50, -58, 100, 58, 20)
        rellena(ctx, ACERO, 7)
    for sx in (-1, 1):
        hx_, hy = sx * 178, TOP + 300
        ctx.move_to(sx * 120, TOP + 60)
        ctx.line_to(hx_, hy - 60)
        trazo(ctx, INK, 86)
        ctx.move_to(sx * 120, TOP + 60)
        ctx.line_to(hx_, hy - 60)
        trazo(ctx, TRAJE, 72)
        elipse(ctx, sx * 155, TOP + 185, 38, 16)
        rellena(ctx, TRAJE_OSC, 5)
        rrect(ctx, hx_ - 36, hy - 62, 72, 80, 24)
        rellena(ctx, ACERO, 7)


def _frente(ctx, calor, empa, t):
    # mochila (asoma por los costados)
    rrect(ctx, -150, TOP - 24, 300, 290, 30)
    rellena(ctx, TRAJE_OSC, 7)
    _piernas_brazos(ctx)
    # torso
    rrect(ctx, -132, TOP, 264, -300 - TOP + 20, 60)
    rellena(ctx, TRAJE, 7)
    rrect(ctx, -132, -330, 264, 34, 12)
    rellena(ctx, TRAJE_OSC, 6)
    # panel del pecho con el medidor de calor
    rrect(ctx, -80, TOP + 62, 160, 92, 14)
    rellena(ctx, ACERO, 6)
    rrect(ctx, -60, TOP + 82, 120, 30, 10)
    ctx.set_source_rgb(*hx("#1A1F33"))
    ctx.fill()
    nivel = lerp(0.22, 1.0, clamp(calor))
    rrect(ctx, -56, TOP + 86, 112 * nivel, 22, 8)
    ctx.set_source_rgb(*mezcla(VERDE, ROJO, clamp(calor * 1.15)))
    ctx.fill()
    for k in range(3):
        on = calor > 0.66 and math.sin(t * 14 + k) > 0
        elipse(ctx, -36 + 36 * k, TOP + 133, 9, 9)
        rellena(ctx, ROJO if on else mezcla(VERDE, AMARILLO, clamp(calor * 1.5)), 3)
    elipse(ctx, 100, TOP + 52, 18, 18)
    rellena(ctx, PANEL, 4)
    # casco
    rrect(ctx, -74, TOP - 22, 148, 32, 12)
    rellena(ctx, ACERO, 6)
    elipse(ctx, 0, TOP - 110, 104, 100)
    rellena(ctx, TRAJE, 8)
    elipse(ctx, 0, TOP - 106, 80, 68)
    g2 = cairo.LinearGradient(0, TOP - 170, 0, TOP - 40)
    g2.add_color_stop_rgb(0, *hx("#3A6EA5"))
    g2.add_color_stop_rgb(1, *VISOR)
    ctx.set_source(g2)
    ctx.fill_preserve()
    path = ctx.copy_path()
    trazo(ctx, INK, 6)
    if empa > 0.01:
        # visor empañado y gotas de sudor adentro
        ctx.save()
        ctx.append_path(path)
        ctx.clip()
        ctx.append_path(path)
        ctx.set_source_rgba(1, 1, 1, 0.42 * empa)
        ctx.fill()
        for k, ph in enumerate((0.1, 0.45, 0.8, 0.3)):
            q = (t * 0.55 + ph) % 1
            gx = (-48, 22, 52, -12)[k]
            K.gota(ctx, gx, TOP - 160 + q * 110, 9, K.AZUL_AGUA, alpha=empa * (1 - q * 0.5))
        ctx.restore()
    ctx.new_sub_path()
    ctx.arc(-6, TOP - 106, 58, math.radians(200), math.radians(250))
    trazo(ctx, BLANCO, 10, 0.6)
    elipse(ctx, 40, TOP - 70, 9, 9)
    ctx.set_source_rgba(1, 1, 1, 0.5)
    ctx.fill()


def _espalda(ctx):
    _piernas_brazos(ctx)
    rrect(ctx, -132, TOP, 264, -300 - TOP + 20, 60)
    rellena(ctx, TRAJE, 7)
    # mochila grande
    rrect(ctx, -170, TOP - 40, 340, 330, 36)
    rellena(ctx, MOCHILA, 8)
    rrect(ctx, -130, TOP + 10, 260, 120, 20)
    rellena(ctx, TRAJE_OSC, 5)
    for k in range(4):
        ctx.move_to(-100, TOP + 34 + 24 * k)
        ctx.line_to(100, TOP + 34 + 24 * k)
        trazo(ctx, ACERO_OSC, 5)
    rrect(ctx, -110, TOP + 160, 220, 90, 16)
    rellena(ctx, ACERO, 5)
    for i in range(6):
        for j in range(2):
            elipse(ctx, -80 + 32 * i, TOP + 185 + 38 * j, 7, 7)
            ctx.set_source_rgb(*ACERO_OSC)
            ctx.fill()
    # casco de atrás
    rrect(ctx, -74, TOP - 22, 148, 32, 12)
    rellena(ctx, ACERO, 6)
    elipse(ctx, 0, TOP - 110, 104, 100)
    rellena(ctx, TRAJE, 8)
    ctx.new_sub_path()
    ctx.arc(-10, TOP - 112, 72, math.radians(195), math.radians(250))
    trazo(ctx, BLANCO, 10, 0.8)


def _tubos_pts():
    """Recorridos de los tubitos de la malla, en el marco del astronauta."""
    L = []
    # torso: serpentina horizontal
    pts = []
    ys = [TOP + 40 + 30 * k for k in range(9)]
    for k, y in enumerate(ys):
        xs = (-104, 104) if k % 2 == 0 else (104, -104)
        pts += [(xs[0], y), (xs[1], y)]
    L.append(pts)
    # brazos: ida y vuelta por la manga
    for sx in (-1, 1):
        x0, y0 = sx * 120, TOP + 60
        x1, y1 = sx * 178, TOP + 240
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy)
        px, py = -dy / n, dx / n
        a = [(x0 + px * o + dx * f, y0 + py * o + dy * f) for o, f in ((-16, 0), (-16, 1.0))]
        bb = [(x0 + px * o + dx * f, y0 + py * o + dy * f) for o, f in ((16, 1.0), (16, 0))]
        L.append(a + bb)
    # piernas: serpentina vertical
    for lx in (-58, 58):
        pts = []
        for k, x in enumerate((lx - 30, lx - 10, lx + 10, lx + 30)):
            ya, yb = (-290, -75) if k % 2 == 0 else (-75, -290)
            pts += [(x, ya), (x, yb)]
        L.append(pts)
    return L


TUBOS = _tubos_pts()
TUBOS_CUM = [poli_cum(p) for p in TUBOS]


def _tubos(ctx, p, rojo, t, flujo=0.0):
    col = mezcla(FRIO, CALOR, clamp(rojo))
    for pts in TUBOS:
        if poli_camino(ctx, pts, p):
            trazo(ctx, INK, 15)
        if poli_camino(ctx, pts, p):
            trazo(ctx, col, 9)
        if flujo > 0.01 and poli_camino(ctx, pts, p):
            ctx.set_dash([12, 26], -t * 90)
            trazo(ctx, mezcla(col, BLANCO, 0.65), 4, flujo)
            ctx.set_dash([])


def astronauta(ctx, x, y, s=1.0, rot=0.0, a=1.0, calor=0.0, empa=0.0, t=0.0, giro=0.0, rx=0.0, tubos=0.0,
               rojo=0.0, flujo=0.0):
    """Astronauta con traje; (x, y) = suela de las botas, mide 770. giro: 0 de frente, 1 de espaldas.
    rx: rayos X (el traje se ve transparente y aparece la malla de tubitos)."""
    if s <= 0.01 or a <= 0.01:
        return
    with en(ctx, x, y, s, rot), alfa(ctx, a):
        cx = math.cos(math.pi * clamp(giro))
        ctx.scale(max(abs(cx), 0.03), 1)
        if giro >= 0.5:
            _espalda(ctx)
            return
        if rx <= 0.01:
            _frente(ctx, calor, empa, t)
            return
        ctx.push_group()
        _frente(ctx, calor, empa, t)
        traje = ctx.pop_group()
        ctx.set_source(traje)
        ctx.paint_with_alpha(1 - 0.5 * rx)
        ctx.set_source_rgba(*hx("#0E2A55"), 0.62 * rx)
        ctx.mask(traje)
        ctx.push_group()
        _tubos(ctx, tubos, rojo, t, flujo)
        tub = ctx.pop_group()
        ctx.set_source(tub)
        ctx.mask(traje)


def a_mundo(x, y, s, lx, ly):
    return x + lx * s, y + ly * s


# ------------------------------------------------------------------ Vos (solo en la Tierra)
VOS_POSES = {
    "mira": dict(look=(0.3, -0.4)),
    "contento": dict(eyes="happy", brows="happy", mouth_kind="open_smile"),
}


@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    body = kit.vos(**VOS_POSES[pose])
    png = cairosvg.svg2png(bytestring=kit.svg(520, 820, body).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


def vos(ctx, pose, x, y, k=1.0, alpha=1.0):
    """Vos con los pies en (x, y); k = 1 es el dibujo a 520x820."""
    if alpha <= 0.01 or k <= 0.01:
        return
    s = vos_surface(pose)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k / 2, k / 2)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


# ------------------------------------------------------------------ bolitas de calor que andan sueltas adentro del traje
def bolas_adentro(t, n, t0, x, y, s, seed=1, paso=0.12, zona=(0, -420, 95, 120)):
    """Posiciones de n bolitas que rebotan adentro del torso (Lissajous acotado). Devuelve (x, y, escala)."""
    r = rng(seed)
    out = []
    cx, cy, ax, ay = zona
    for k in range(n):
        w1, w2 = r.uniform(1.6, 2.6), r.uniform(1.3, 2.2)
        p1, p2 = r.uniform(0, TAU), r.uniform(0, TAU)
        lx = cx + ax * math.sin(w1 * t + p1)
        ly = cy + ay * math.sin(w2 * t + p2)
        out.append((x + lx * s, y + ly * s, pop(t, t0 + paso * k, 0.3)))
    return out


# ================================================================== escenas
# ------------------------------------------------------------------ 1. apertura (y cierre del loop): el espacio a −270
T_270 = b(0, "270")
T_CERO = b(0, "cero")
T_AUN = b(1)
T_ASTRO1 = b(1, "astronauta")
T_COCINAR = b(1, "cocinar")
AP_X, AP_Y, AP_S = 410, 1205, 0.78         # botas del astronauta
EST = (255, 330, 0.48)                     # estación
TH_X, TH_TOP, TH_BOT = 872, 300, 1030      # termómetro de afuera


def th_entra(u):
    return lerp(460, 0, prog(u, -0.95, 0.5, "out"))


def th_nivel(u):
    return 1 - 0.98 * prog(u, -0.5, 2.0, "inout")


def cable(ctx, u, ax, ay, s, a=1.0):
    ex, ey, es = EST
    x0, y0 = ex + 20, ey + 70 * es + 6
    x1, y1 = a_mundo(ax, ay, s, -150, -460)
    for w, col in ((10, INK), (5, NARANJA)):
        ctx.move_to(x0, y0)
        ctx.curve_to(x0 + 40, y0 + 330, x1 - 260, y1 - 80, x1, y1)
        trazo(ctx, col, w, a)


def escena_espacio(ctx, u, calor=0.0, empa=0.0, th=True, z=1.0, glow=0.0, extra=None):
    """Plano del espacio: estación, astronauta con cable, Tierra abajo y el termómetro de afuera."""
    espacio(ctx, u)
    C.tierra(ctx, 540, 2350, 1000, u)
    ctx.save()
    zoom(ctx, z, AP_X, 860)
    ex, ey, es = EST
    estacion(ctx, ex, ey + 6 * math.sin(u * 1.1), es)
    fl = 10 * math.sin(u * 1.6)
    rot = math.radians(2.0 * math.sin(u * 1.2))
    cable(ctx, u, AP_X, AP_Y + fl, AP_S)
    if glow > 0.01:
        _elipse_suave(ctx, AP_X, AP_Y - 430 * AP_S, 360, 420, CALOR, 0.45 * glow)
    astronauta(ctx, AP_X, AP_Y + fl, AP_S, rot, calor=calor, empa=empa, t=u)
    if extra:
        extra(ctx, u, AP_X, AP_Y + fl, AP_S, rot)
    ctx.restore()
    if th:
        dx = th_entra(u)
        f = th_nivel(u)
        frio = prog(u, 1.2, 1.2)
        jit = 3 * math.sin(u * 55) * frio
        termometro(ctx, TH_X + dx + jit, TH_TOP, TH_BOT, f, escarcha=frio,
                   cara="frio" if f < 0.6 else "normal", t=u)
        texto(ctx, "+20", TH_X + dx + 82, TH_TOP, 40, fill=BLANCO, sw=7, ax=0)


def d_apertura(ctx, u):
    calor = prog(u, T_COCINAR - 0.25, 0.5)
    z = 1 + 0.10 * prog(u, T_AUN, 2.8)

    def bolas(ctx, uu, ax, ay, s, rot):
        if calor <= 0.01:
            return
        for x, y, sc in bolas_adentro(uu, 3, T_COCINAR - 0.1, ax, ay, s, seed=3):
            bola_calor(ctx, x, y, 26 * sc, cara="picara")

    escena_espacio(ctx, u, calor=calor, empa=calor, z=z, glow=calor, extra=bolas)
    kartel(ctx, "−270 °C", TH_X - 20, 1255, 76, u, T_270, box=FRIO, fg=INK, rot=-3)


# ------------------------------------------------------------------ 2. ¿cómo te cocinas a 270 bajo cero?
T_COMO = b(2)
T_COCINAS = b(2, "cocinas")


def d_pregunta(ctx, t):
    espacio(ctx, t)
    # mitades: afuera frío / adentro calor
    ctx.move_to(0, 0)
    ctx.line_to(600, 0)
    ctx.line_to(480, H)
    ctx.line_to(0, H)
    ctx.close_path()
    ctx.set_source_rgba(*hx("#1B4FA0"), 0.55)
    ctx.fill()
    ctx.move_to(600, 0)
    ctx.line_to(W, 0)
    ctx.line_to(W, H)
    ctx.line_to(480, H)
    ctx.close_path()
    ctx.set_source_rgba(*hx("#B8321A"), 0.55)
    ctx.fill()
    ctx.move_to(600, 0)
    ctx.line_to(480, H)
    trazo(ctx, BLANCO, 8, 0.8)
    q = prog(t, T_COMO - 0.1, 0.4, "out")
    # termómetro de afuera
    termometro(ctx, lerp(-150, 165, q), 430, 960, 0.02, escarcha=1.0, cara="frio", t=t)
    kartel(ctx, "AFUERA", lerp(-150, 165, q), 300, 58, t, T_COMO - 0.1, box=FRIO, rot=-4)
    kartel(ctx, "−270 °C", lerp(-150, 165, q), 1175, 54, t, T_COMO, box=BLANCO, rot=3)
    # termómetro de adentro
    f = lerp(0.55, 0.95, prog(t, T_COMO, 2.0, "out"))
    termometro(ctx, lerp(1230, 915, q), 430, 960, f, cara="calor", t=t)
    kartel(ctx, "ADENTRO", lerp(1230, 915, q), 300, 58, t, T_COMO, box=CALOR_CLARO, rot=4)
    for k in range(3):
        K.gota(ctx, lerp(1230, 915, q) + 70 + 14 * k, 1060 + ((t * 0.9 + k * 0.33) % 1) * 90, 11, K.AZUL_AGUA,
               alpha=0.9)
    # astronauta en el medio, cocinándose
    _elipse_suave(ctx, 560, 900, 300, 380, CALOR, 0.4)
    astronauta(ctx, 545, 1250 + 8 * math.sin(t * 1.6), 0.8, math.radians(1.5 * math.sin(t * 1.3)), calor=1.0,
               empa=1.0, t=t)
    for x, y, sc in bolas_adentro(t, 4, T_COMO - 1, 545, 1250, 0.8, seed=4):
        bola_calor(ctx, x, y, 26 * sc)
    signo(ctx, "?", 545, 300, 300, t, T_COCINAS - 0.05)


# ------------------------------------------------------------------ 3. en la Tierra, el aire se lleva tu calor
T_TIERRA = b(3, "tierra")
T_ENFRIAS = b(3, "enfrias")
T_AIRE3 = b(3, "aire")
T_LLEVA = b(3, "lleva")
T_CALOR3 = b(3, "calor")
SUELO_T = 1270
VOS_T = (540, SUELO_T, 1.05)
AIRE_V = 620.0


CALOR_T = [(415, 950), (668, 930), (540, 1060), (440, 1120), (640, 1110), (500, 1215), (585, 1220)]


def _tierra_bolas():
    r = rng(21)
    calor = []
    for k, (bx, by) in enumerate(CALOR_T):
        tb = T_TIERRA + 0.05 + 0.12 * k
        tc = T_LLEVA - 0.3 + 0.14 * k
        calor.append((bx, by, tb, tc))
    aires = []
    for bx, by, tb, tc in calor:
        aires.append((by + 6, tc - (bx + 90) / AIRE_V, True))
    for k in range(10):
        aires.append((float(r.uniform(560, 1180)), T_AIRE3 - 0.9 + 0.22 * k, False))
    return calor, aires


TB_CALOR, TB_AIRES = _tierra_bolas()


def d_tierra(ctx, t):
    g = cairo.LinearGradient(0, 0, 0, SUELO_T)
    g.add_color_stop_rgb(0, *CIELO_DIA)
    g.add_color_stop_rgb(1, *CIELO_DIA2)
    ctx.set_source(g)
    ctx.paint()
    C.sol(ctx, 900, 250, 80, t)
    ctx.move_to(-20, SUELO_T)
    for k in range(13):
        ctx.line_to(k * 100, SUELO_T + 8 * math.sin(k * 1.3))
    ctx.line_to(1120, H)
    ctx.line_to(-20, H)
    ctx.close_path()
    rellena(ctx, PASTO, 8)
    vx, vy, vk = VOS_T
    vos(ctx, "contento" if t >= T_ENFRIAS else "mira", vx, vy, vk)
    kartel(ctx, "EN LA TIERRA", 330, 230, 66, t, T_TIERRA - 0.05, box=BLANCO, rot=-4)
    # aire que pasa
    if t >= T_AIRE3 - 1.0:
        for y, s0, lleva in TB_AIRES:
            x = -90 + AIRE_V * (t - s0)
            if -100 < x < W + 100:
                bola_aire(ctx, x, y + 10 * math.sin(t * 5 + y), 38, a=prog(t, T_AIRE3 - 0.6, 0.3))
    # bolitas de calor que salen del cuerpo y se van con el aire
    for bx, by, tb, tc in TB_CALOR:
        if t < tb:
            continue
        sc = pop(t, tb, 0.3)
        if t < tc:
            x, y = bx + 6 * math.sin(t * 4 + by), by - 25 * prog(t, tb, 0.8, "out")
        else:
            x = bx + AIRE_V * (t - tc)
            y = by + 6 + 10 * math.sin(t * 5 + by + 6) - 40
        if x < W + 60:
            bola_calor(ctx, x, y, 28 * sc, cara="picara" if t < tc else "feliz")


# ------------------------------------------------------------------ 4. en el espacio no hay aire que se lo lleve
T_ESP4 = b(4, "espacio")
T_NO4 = b(4, "no")
T_AIRE4 = b(4, "aire")
T_LLEVE = b(4, "lleve")
FANT = [(540 + 390 * math.cos(a_), 880 + 470 * math.sin(a_)) for a_ in np.linspace(-2.6, 2.6, 6)]


def d_vacio(ctx, t):
    espacio(ctx, t)
    glow = lerp(0.35, 0.9, prog(t, T_LLEVE - 0.4, 0.8))
    _elipse_suave(ctx, 545, 900, 320, 420, CALOR, 0.45 * glow)
    ax, ay, s = 545, 1250 + 8 * math.sin(t * 1.6), 0.82
    astronauta(ctx, ax, ay, s, math.radians(1.5 * math.sin(t * 1.3)), calor=lerp(0.7, 0.95, glow), empa=1.0, t=t)
    n = 3 + int(clamp((t - T_ESP4) / 0.25, 0, 6))
    for x, y, sc in bolas_adentro(t, 9, b(4) - 0.2, ax, ay, s, seed=5, paso=0.22):
        bola_calor(ctx, x, y, 24 * sc)
    del n
    # donde tendría que estar el aire: nada
    for k, (fx, fy) in enumerate(FANT):
        tk = T_AIRE4 - 0.15 + 0.07 * k
        bola_aire(ctx, fx, fy, 52, a=prog(t, tk, 0.2), fantasma=True)
        C.cruz(ctx, fx, fy, 30, s=pop(t, tk + 0.12, 0.25))
    kartel(ctx, "SIN AIRE", 540, 250, 76, t, T_NO4, box=BLANCO, rot=-3)


# ------------------------------------------------------------------ 5. es como un termo (y el astronauta es el café)
T_TERMO = b(5, "termo")
T_PAREDES = b(5, "paredes")
T_NO5 = b(5, "no")
T_AIRE5 = b(5, "aire")
T_CAFE5 = b(5, "cafe")
T_CALIENTE = b(5, "caliente")
T_DURANTE = b(5, "durante")
T_HORAS = b(5, "horas")
T_ASTRO6 = b(6, "astronauta")
T_CAFE6 = b(6, "cafe")
TX0, TX1, TY0, TY1 = 300, 780, 420, 1300
GAP = 64
HORAS = [T_DURANTE - 0.1 + 0.11 * k for k in range(7)]


def termo(ctx, t, cafe_nivel, cafe_a, paredes_brillo=0.0, estrellas=0.0, astro=0.0):
    w, h = TX1 - TX0, TY1 - TY0
    # tapa
    rrect(ctx, TX0 + 50, TY0 - 86, w - 100, 110, 30)
    rellena(ctx, TERMO_OSC, 8)
    rrect(ctx, TX0 + 120, TY0 - 120, w - 240, 50, 18)
    rellena(ctx, ACERO, 6)
    # carcasa (cortada al medio)
    rrect(ctx, TX0, TY0, w, h, 70)
    rellena(ctx, TERMO_COL, 9)
    # hueco sin aire entre las dos paredes
    rrect(ctx, TX0 + 16, TY0 + 16, w - 32, h - 32, 58)
    ctx.set_source_rgb(*VACIO)
    ctx.fill()
    if estrellas > 0.01:
        ctx.save()
        rrect(ctx, TX0 + 16, TY0 + 16, w - 32, h - 32, 58)
        ctx.clip()
        r = rng(31)
        for k in range(26):
            lado = k % 4
            if lado == 0:
                x, y = r.uniform(TX0 + 18, TX0 + GAP - 4), r.uniform(TY0 + 30, TY1 - 30)
            elif lado == 1:
                x, y = r.uniform(TX1 - GAP + 4, TX1 - 18), r.uniform(TY0 + 30, TY1 - 30)
            elif lado == 2:
                x, y = r.uniform(TX0 + 30, TX1 - 30), r.uniform(TY0 + 18, TY0 + GAP - 4)
            else:
                x, y = r.uniform(TX0 + 30, TX1 - 30), r.uniform(TY1 - GAP + 4, TY1 - 18)
            C.estrella(ctx, x, y, r.uniform(2, 4.5), a=estrellas, halo=0.5)
        ctx.restore()
    # pared de adentro
    rrect(ctx, TX0 + GAP, TY0 + GAP, w - 2 * GAP, h - 2 * GAP, 40)
    rellena(ctx, ACERO, 7)
    ix0, iy0, iw, ih = TX0 + GAP + 14, TY0 + GAP + 14, w - 2 * GAP - 28, h - 2 * GAP - 28
    rrect(ctx, ix0, iy0, iw, ih, 30)
    ctx.set_source_rgb(*hx("#3A2A22"))
    ctx.fill()
    ctx.save()
    rrect(ctx, ix0, iy0, iw, ih, 30)
    ctx.clip()
    if cafe_a > 0.01:
        yc = lerp(iy0 + ih, iy0 + 180, cafe_nivel)
        ctx.move_to(ix0 - 10, yc)
        for k in range(9):
            ctx.line_to(ix0 + iw * k / 8, yc + 7 * math.sin(t * 4 + k))
        ctx.line_to(ix0 + iw + 10, iy0 + ih + 10)
        ctx.line_to(ix0 - 10, iy0 + ih + 10)
        ctx.close_path()
        g = cairo.LinearGradient(0, yc, 0, iy0 + ih)
        g.add_color_stop_rgba(0, *CAFE_CLARO, cafe_a)
        g.add_color_stop_rgba(1, *CAFE, cafe_a)
        ctx.set_source(g)
        ctx.fill()
        # vapor adentro, sobre el café
        for k in range(6):
            q = (t * 0.5 + k / 6) % 1
            px = ix0 + iw * (0.2 + 0.6 * ((k * 0.37) % 1)) + 20 * math.sin(t * 2 + k)
            py = yc - 20 - q * 150
            ctx.arc(px, py, lerp(16, 40, q), 0, TAU)
            ctx.set_source_rgba(1, 1, 1, 0.45 * (1 - q) * cafe_a)
            ctx.fill()
    ctx.restore()
    if paredes_brillo > 0.01:
        rrect(ctx, TX0 - 6, TY0 - 6, w + 12, h + 12, 74)
        trazo(ctx, AMARILLO, 10, paredes_brillo)
        rrect(ctx, TX0 + GAP, TY0 + GAP, w - 2 * GAP, h - 2 * GAP, 40)
        trazo(ctx, AMARILLO, 10, paredes_brillo)
    return ix0, iy0, iw, ih


def d_termo(ctx, t):
    fondo(ctx, t, 0.25)
    s = lerp(0.82, 1.0, pop(t, b(5) - 0.05, 0.45))
    astro = pop(t, T_ASTRO6 - 0.05, 0.4)
    cafe_n = lerp(0.62, 0.0, prog(t, T_ASTRO6 - 0.2, 0.5))
    cafe_a = 1 - prog(t, T_ASTRO6 + 0.1, 0.4)
    brillo = bump(t, T_PAREDES - 0.05, 0.7, 1.0) - 1 if T_PAREDES - 0.05 <= t <= T_PAREDES + 0.65 else 0.0
    ctx.save()
    zoom(ctx, s, 540, 860)
    ix0, iy0, iw, ih = termo(ctx, t, cafe_n, cafe_a, paredes_brillo=clamp(brillo * 1.4),
                             estrellas=prog(t, T_CAFE6 - 0.1, 0.4))
    # bolitas de calor en el café: rebotan contra la pared de adentro y no pasan
    cx, cy = ix0 + iw / 2, iy0 + ih * 0.66
    for k, (x, y, sc) in enumerate(bolas_adentro(t, 5, b(5) + 0.1, cx, cy, 1.0, seed=8,
                                                 zona=(0, 0, iw / 2 - 34, ih * 0.22))):
        bola_calor(ctx, x, y, 26 * sc * (1 - 0.0 * astro))
    if astro > 0.01:
        astronauta(ctx, cx, iy0 + ih - 18, 0.58 * astro, math.radians(3 * math.sin(t * 1.4)), calor=0.6, empa=0.4,
                   t=t)
    ctx.restore()
    # carteles
    kartel(ctx, "TERMO", 540, 200, 76, t, T_TERMO - 0.05, T_ASTRO6 - 0.1, box=BLANCO, rot=-3)
    if t >= T_NO5 - 0.1:
        a = prog(t, T_NO5 - 0.1, 0.25) * (1 - prog(t, T_CAFE5 - 0.1, 0.3))
        linea_punteada(ctx, 860, 640, TX1 - 22, 720, BLANCO, 6, a)
        kartel(ctx, "SIN AIRE", 880, 600, 54, t, T_NO5 - 0.1, T_CAFE5 - 0.1, box=BLANCO, rot=4)
        ctx.save()
        zoom(ctx, s, 540, 860)
        for k, yy in enumerate((640, 860, 1080)):
            for xx in (TX0 + GAP / 2 + 6, TX1 - GAP / 2 - 6):
                C.cruz(ctx, xx, yy, 14, s=pop(t, T_AIRE5 - 0.1 + 0.06 * k, 0.25) * sale(t, T_CAFE5 - 0.1))
        ctx.restore()
    if t >= T_DURANTE - 0.2:
        n = sum(1 for h_ in HORAS if t >= h_)
        reloj_digital(ctx, 880, 250, 0.72 * pop(t, T_DURANTE - 0.2, 0.3) * sale(t, T_ASTRO6 - 0.1), 8 + 1 * n)
    kartel(ctx, "ESPACIO", 900, 700, 58, t, T_CAFE6 - 0.05, box=BLANCO, rot=4)
    if t >= T_CAFE6 - 0.05:
        linea_punteada(ctx, 880, 740, TX1 - 22, 820, BLANCO, 6, prog(t, T_CAFE6 - 0.05, 0.25))
    kartel(ctx, "= CAFÉ", 200, 860, 64, t, T_CAFE6 + 0.05, box=CAFE_CLARO, fg=BLANCO, rot=-5)


# ------------------------------------------------------------------ 6. cada esfuerzo lo calienta un poco más
T_CADA = b(7)
T_ESFUERZO = b(7, "esfuerzo")
T_CALIENTA7 = b(7, "calienta")
T_MAS7 = b(7, "mas")
VUELTAS = 3
V0, V1 = T_ESFUERZO - 0.1, T_MAS7 + 0.35
BULON = (330, 820)


def guante(ctx, x, y, ang, s=1.0):
    with en(ctx, x, y, s, ang):
        rrect(ctx, -50, -46, 100, 92, 30)
        rellena(ctx, ACERO, 7)
        for k in range(4):
            rrect(ctx, -46 + 24 * k, -70, 20, 36, 10)
            rellena(ctx, ACERO, 5)


def llave_inglesa(ctx, x, y, ang, largo=300):
    with en(ctx, x, y, 1.0, ang):
        rrect(ctx, 0, -20, largo, 40, 18)
        rellena(ctx, ACERO_OSC, 7)
        ctx.new_sub_path()
        ctx.arc(0, 0, 52, 0, TAU)
        rellena(ctx, ACERO_OSC, 7)
        ctx.new_sub_path()
        for k in range(6):
            a_ = k * TAU / 6
            (ctx.move_to if k == 0 else ctx.line_to)(26 * math.cos(a_), 26 * math.sin(a_))
        ctx.close_path()
        rellena(ctx, hx("#3A3F4C"), 4)


def d_esfuerzo(ctx, t):
    espacio(ctx, t, seed=12)
    # casco de la estación, de cerca
    rrect(ctx, -60, 430, 620, 820, 60)
    rellena(ctx, TRAJE, 9)
    for k in range(5):
        ctx.move_to(-60, 520 + 150 * k)
        ctx.line_to(560, 520 + 150 * k)
        trazo(ctx, TRAJE_OSC, 5)
    for x, y in ((60, 470), (480, 470), (60, 1210), (480, 1210)):
        elipse(ctx, x, y, 12, 12)
        rellena(ctx, ACERO_OSC, 4)
    q = clamp((t - V0) / (V1 - V0))
    vueltas = VUELTAS * ease(q, "inout")
    ang = -0.5 + TAU * vueltas
    bx, by = BULON
    largo = 300
    gx, gy = bx + largo * math.cos(ang), by + largo * math.sin(ang)
    # manga que viene desde abajo a la derecha
    for w, col in ((118, INK), (102, TRAJE)):
        ctx.move_to(720, 1330)
        ctx.curve_to(700, 1150, gx + 120 * math.cos(ang), gy + 120 * math.sin(ang), gx, gy)
        trazo(ctx, col, w)
    elipse(ctx, 720, 1330, 70, 30)
    rellena(ctx, TRAJE_OSC, 7)
    llave_inglesa(ctx, bx, by, ang, largo)
    guante(ctx, gx, gy, ang + math.pi / 2, 1.0)
    # medidor del traje: sube un escalón por vuelta
    f = 0.5
    for k in range(VUELTAS):
        tk = V0 + (V1 - V0) * (k + 0.6) / VUELTAS
        f += 0.14 * prog(t, tk + 0.45, 0.2, "out")
    termometro(ctx, 905, 420, 1000, f, cara="calor" if f > 0.75 else "normal", t=t)
    kartel(ctx, "TRAJE", 905, 300, 62, t, T_CADA - 0.1, box=BLANCO, rot=4)
    for k in range(VUELTAS):
        tk = V0 + (V1 - V0) * (k + 0.6) / VUELTAS
        u = t - tk
        if 0 <= u < 0.5:
            q = ease(u / 0.45, "inout")
            x0, y0 = bx + 300 * math.cos(-0.5 + TAU * (k + 0.6)), by + 300 * math.sin(-0.5 + TAU * (k + 0.6))
            x = lerp(x0, 905, q)
            y = lerp(y0 - 40, 1051, q) - 160 * math.sin(math.pi * q)
            bola_calor(ctx, x, y, 30 * pop(t, tk, 0.25) * lerp(1, 0.6, q))


# ------------------------------------------------------------------ 7. la malla de tubitos con agua fría (rayos X)
T_DEBAJO = b(8, "debajo")
T_MALLA = b(8, "malla")
T_70 = b(8, "70")
T_TUBITOS = b(8, "tubitos")
T_AGUA8 = b(8, "agua")
T_FRIA = b(8, "fria")
T_PERO9 = b(9)
T_CALIENTA9 = b(9, "calienta")
T_DONDE = b(10)
T_TIRA10 = b(10, "tira")
T_AFUERA10 = b(10, "afuera")
T_NADA = b(10, "nada")
MX, MY, MS = 440, 1300, 1.0
LARGO_PTS = [(MX + 120, MY - 330), (760, MY - 330), (760, 640), (920, 640), (920, 1080), (1000, 1080),
             (1000, 420), (1200, 420)]


def d_malla(ctx, t):
    espacio(ctx, t, seed=14)
    rx = prog(t, T_DEBAJO - 0.1, 0.5)
    tub = prog(t, T_MALLA - 0.35, 1.2)
    rojo = prog(t, T_CALIENTA9 - 0.2, 0.7)
    flujo = prog(t, T_AGUA8 - 0.1, 0.3)
    fl = 8 * math.sin(t * 1.6)
    astronauta(ctx, MX, MY + fl, MS, 0.0, calor=lerp(0.85, 0.35, prog(t, T_AGUA8, 0.8)), empa=0.5, t=t, rx=rx,
               tubos=tub, rojo=rojo, flujo=flujo)
    # el tubito desenrollado: más de 70 metros
    if T_70 - 0.1 <= t < T_AGUA8 + 0.3:
        p = prog(t, T_70 - 0.1, 0.9, "out")
        a = 1 - prog(t, T_AGUA8 - 0.1, 0.3)
        with alfa(ctx, a):
            if poli_camino(ctx, LARGO_PTS, p):
                trazo(ctx, INK, 17)
            if poli_camino(ctx, LARGO_PTS, p):
                trazo(ctx, FRIO, 10)
        if t >= T_70:
            m = int(round(70 * prog(t, T_70, 0.6, "out")))
            kartel(ctx, f"+{m} m" if m >= 70 else f"{m} m", 830, 330, 84, t, T_70, T_AGUA8 - 0.1, box=FRIO,
                   rot=-4)
    kartel(ctx, "MALLA", 830, 1150, 60, t, T_MALLA - 0.05, T_70 - 0.1, box=BLANCO, rot=4)
    if t >= T_FRIA - 0.15:
        copo(ctx, 800, 640, 70 * pop(t, T_FRIA - 0.15, 0.35) * sale(t, T_CALIENTA9 - 0.2), rot=t * 0.4)
    # bolitas de calor: antes sueltas en el traje, con el agua fría se meten en los tubitos
    absorb = prog(t, T_AGUA8 + 0.1, 0.7)
    for k, (x, y, sc) in enumerate(bolas_adentro(t, 4, b(8) - 1, MX, MY + fl, MS, seed=6)):
        pts, cum = TUBOS[k % len(TUBOS)], TUBOS_CUM[k % len(TUBOS)]
        s_ = (cum[-1] * (0.2 + 0.18 * k) + 140 * (t - T_AGUA8)) % cum[-1]
        tx, ty = poli_punto(pts, cum, s_)
        tx, ty = MX + tx * MS, MY + fl + ty * MS
        bola_calor(ctx, lerp(x, tx, absorb), lerp(y, ty, absorb), lerp(26, 13, absorb) * sc,
                   a=1.0 if rx < 0.99 else lerp(1, 0.95, absorb))
    # ¿dónde tira el calor? una bolita se choca con el borde del traje
    if t >= T_DONDE - 0.2:
        signo(ctx, "?", 760, 330, 260, t, T_DONDE - 0.05)
        x_borde = MX + 132 * MS - 30
        ida = []
        for k, t0 in enumerate((T_TIRA10 - 0.1, T_AFUERA10 - 0.15)):
            u = t - t0
            if 0 <= u < 0.9:
                xx = lerp(MX, x_borde, clamp(u / 0.35)) if u < 0.35 else lerp(x_borde, MX + 30,
                                                                                ease(clamp((u - 0.35) / 0.5), "out"))
                ida.append((xx, MY - 470 + 60 * k))
        for xx, yy in ida:
            bola_calor(ctx, xx, yy + fl, 34, cara="susto")
        for k, t0 in enumerate((T_TIRA10 + 0.25, T_AFUERA10 + 0.2)):
            if t0 <= t < t0 + 0.4:
                ctx.move_to(x_borde + 40, MY - 470 + 60 * k - 60 + fl)
                ctx.line_to(x_borde + 40, MY - 470 + 60 * k + 60 + fl)
                trazo(ctx, BLANCO, 8, 1 - (t - t0) / 0.4)
        for k, (fx, fy) in enumerate(((800, 720), (930, 940), (790, 1160), (950, 560))):
            tk = T_AFUERA10 + 0.05 + 0.08 * k
            bola_aire(ctx, fx, fy, 40, a=prog(t, tk, 0.2), fantasma=True)
            C.cruz(ctx, fx, fy, 26, s=pop(t, tk + 0.1, 0.25))
        kartel(ctx, "NADA", 870, 1290, 70, t, T_NADA - 0.05, box=BLANCO, rot=-4)


# ------------------------------------------------------------------ 8. lo tira con hielo: se da vuelta y sale el cubito
T_LO = b(11)
T_HIELO11 = b(11, "hielo")
GX, GY, GS = 540, 1300, 1.0


def d_giro(ctx, t):
    espacio(ctx, t, seed=14)
    q = prog(t, T_LO - 0.05, 0.55)
    x = lerp(MX, GX, q)
    rx = 1 - prog(t, T_LO - 0.1, 0.3)
    giro = prog(t, T_LO, 0.38)
    zq = prog(t, b(12) - 0.3, 0.3, "in")
    ctx.save()
    zoom(ctx, 1 + 2.4 * zq, GX, GY + MOCHILA_C[1] * GS)
    astronauta(ctx, x, GY + 8 * math.sin(t * 1.6), GS, 0.0, calor=0.5, empa=0.3, t=t, giro=giro, rx=rx, tubos=1.0,
               rojo=1.0, flujo=1.0)
    ctx.restore()
    t_cub = T_HIELO11 - 0.3
    if t >= t_cub:
        u = pop(t, t_cub, 0.4)
        cy = lerp(GY - 420, 330, ease(clamp((t - t_cub) / 0.4), "out"))
        cubito(ctx, GX, cy, 1.05 * u * (1 - zq), rot=math.radians(6 * math.sin(t * 3)))
        destello(ctx, GX + 120, cy - 110, 40, t, t_cub + 0.2)
        destello(ctx, GX - 130, cy + 40, 30, t, t_cub + 0.35)


# ------------------------------------------------------------------ 9. adentro de la mochila: la placa abierta al vacío
T_DEJA = b(12, "deja")
T_SALIR = b(12, "salir")
T_AGUA12 = b(12, "agua")
T_PLACA = b(12, "placa")
T_ABIERTA = b(12, "abierta")
T_VACIO = b(12, "vacio")
T_CONGELA = b(13, "congela")
T_HIELO13 = b(13, "hielo")
T_EVAPORA = b(13, "evapora")
T_ESP13 = b(13, "espacio")
T_LLEVANDO = b(13, "llevandose")
T_CALOR13 = b(13, "calor")
PX0, PX1, PY0, PY1 = 660, 724, 380, 1180      # placa porosa
TANQUE = (80, 270, 260, 200)
CANO = [(210, 470), (210, 520), (600, 520), (600, 1150)]
SALIDAS = [(600, 560 + 44 * k) for k in range(14)]
POROS = [(PX0 + 20 + 26 * (j % 2), 400 + 44 * k + (22 if j % 2 else 0)) for k in range(18) for j in range(2)
         if 400 + 44 * k + (22 if j % 2 else 0) < PY1 - 14]
ROJO_PTS = [(-40, 1260), (420, 1260), (420, 1140), (560, 1140), (560, 1010), (420, 1010), (420, 880), (560, 880),
            (560, 750), (420, 750), (420, 620), (560, 620), (560, 300), (-40, 300)]
ROJO_CUM = poli_cum(ROJO_PTS)
PUFFS = [(k * 0.23, PY0 + 40 + ((k * 0.61) % 1) * (PY1 - PY0 - 80)) for k in range(40)]


def d_placa(ctx, t):
    t0 = b(12) - 0.08
    z = lerp(1.25, 1.0, prog(t, t0, 0.45, "out"))
    ctx.save()
    zoom(ctx, z, 690, 760)
    espacio(ctx, t, seed=17)
    # interior de la mochila
    rrect(ctx, -60, 160, PX0 + 60, 1180, 50)
    rellena(ctx, MOCHILA_IN, 10)
    texto(ctx, "MOCHILA", 300, 210, 46, fill=BLANCO, sw=8)
    # tubito rojo que viene del traje: pasa pegado a la placa y vuelve frío
    enfria = prog(t, T_LLEVANDO - 0.3, 0.9)
    cuantos = 60
    for i in range(cuantos):
        s0, s1 = ROJO_CUM[-1] * i / cuantos, ROJO_CUM[-1] * (i + 1) / cuantos
        p0, p1 = poli_punto(ROJO_PTS, ROJO_CUM, s0), poli_punto(ROJO_PTS, ROJO_CUM, s1)
        f = i / cuantos
        caliente = 1.0 if f < 0.35 else lerp(1.0, 0.0, enfria * clamp((f - 0.35) / 0.4))
        ctx.move_to(*p0)
        ctx.line_to(*p1)
        trazo(ctx, INK, 30)
    for i in range(cuantos):
        s0, s1 = ROJO_CUM[-1] * i / cuantos, ROJO_CUM[-1] * (i + 1) / cuantos
        p0, p1 = poli_punto(ROJO_PTS, ROJO_CUM, s0), poli_punto(ROJO_PTS, ROJO_CUM, s1)
        f = i / cuantos
        caliente = 1.0 if f < 0.35 else lerp(1.0, 0.0, enfria * clamp((f - 0.35) / 0.4))
        ctx.move_to(*p0)
        ctx.line_to(*p1)
        trazo(ctx, mezcla(FRIO, CALOR, caliente), 20)
    texto(ctx, "DEL TRAJE", 150, 1320, 40, fill=CALOR_CLARO, sw=7)
    # tanque de agua y caño
    tx, ty, tw, th = TANQUE
    nivel = 0.8 - 0.12 * prog(t, T_SALIR, 2.0)
    rrect(ctx, tx, ty, tw, th, 24)
    rellena(ctx, BLANCO, 7)
    ctx.save()
    rrect(ctx, tx, ty, tw, th, 24)
    ctx.clip()
    ctx.rectangle(tx, ty + th * (1 - nivel), tw, th)
    ctx.set_source_rgb(*FRIO)
    ctx.fill()
    ctx.restore()
    rrect(ctx, tx, ty, tw, th, 24)
    trazo(ctx, INK, 7)
    texto(ctx, "AGUA", tx + tw / 2, ty + th * 0.62, 50, fill=BLANCO, sw=8)
    if poli_camino(ctx, CANO, 1.0):
        trazo(ctx, INK, 24)
    if poli_camino(ctx, CANO, 1.0):
        trazo(ctx, ACERO, 14)
    for x, y in SALIDAS:
        ctx.move_to(x, y)
        ctx.line_to(PX0, y)
        trazo(ctx, INK, 12)
        ctx.move_to(x, y)
        ctx.line_to(PX0, y)
        trazo(ctx, ACERO, 6)
    # gotitas que viajan por el caño hasta la placa
    cum = poli_cum(CANO)
    if t >= T_DEJA - 0.1:
        for k in range(26):
            st = T_DEJA - 0.1 + k * 0.12
            u = t - st
            if u < 0:
                continue
            sp = 900 * u
            if sp < cum[-1]:
                x, y = poli_punto(CANO, cum, sp)
                K.gota(ctx, x, y + 6, 9, FRIO, alpha=1.0, borde=True)
    # la placa con poros
    rrect(ctx, PX0, PY0, PX1 - PX0, PY1 - PY0, 12)
    rellena(ctx, ACERO, 8)
    lleno = prog(t, T_AGUA12 + 0.2, 1.0)
    congela = prog(t, T_CONGELA - 0.1, 0.5)
    evap = prog(t, T_EVAPORA - 0.1, 0.4)
    for k, (x, y) in enumerate(POROS):
        elipse(ctx, x, y, 8, 8)
        col = mezcla(hx("#3A3F4C"), FRIO, clamp(lleno * 1.5 - k * 0.02))
        ctx.set_source_rgb(*mezcla(col, HIELO, congela))
        ctx.fill()
    if t >= T_PLACA - 0.05:
        a = bump(t, T_PLACA - 0.05, 0.6, 1.0) - 1
        if a > 0:
            rrect(ctx, PX0 - 8, PY0 - 8, PX1 - PX0 + 16, PY1 - PY0 + 16, 16)
            trazo(ctx, AMARILLO, 10, clamp(a * 1.4))
    # escarcha en la cara de afuera de la placa
    if congela > 0.01:
        rr = rng(41)
        for k in range(22):
            y = PY0 + 20 + k * (PY1 - PY0 - 40) / 21
            r_ = 16 + 8 * rr.random()
            ciclo = 0.0 if evap < 0.01 else (t * 1.7 + k * 0.37) % 1
            sc = clamp(congela * 1.4 - k * 0.015) * (1 - 0.6 * ciclo * evap)
            copo(ctx, PX1 + 12 + 6 * (k % 2), y, r_ * sc, rot=k)
    # vapor que se va al espacio, y cada tanto se lleva una bolita de calor
    if evap > 0.01:
        for k, (ph, y) in enumerate(PUFFS):
            st = T_EVAPORA - 0.1 + ph
            u = t - st
            if u < 0:
                continue
            q = (u % 1.4) / 1.4
            ciclo = int(u // 1.4)
            if st + ciclo * 1.4 > TOTAL:
                continue
            x = PX1 + 30 + q * 420
            yy = y - 60 * q + 16 * math.sin(q * 6 + k)
            r_ = lerp(20, 58, q)
            nube(ctx, x, yy, r_, 0.95 * (1 - q * q) * evap)
            lleva = (k % 3 == 0) and (st + ciclo * 1.4 >= T_LLEVANDO - 0.4)
            if lleva:
                bola_calor(ctx, x, yy - r_ * 0.2, 22 * (1 - q * 0.3), a=1 - q * q, cara="feliz")
    # bolitas de calor en el tubo rojo que saltan a la placa
    if t >= T_LLEVANDO - 0.5:
        for k in range(8):
            st = T_LLEVANDO - 0.5 + 0.18 * k
            u = t - st
            if u < 0 or u > 0.6:
                continue
            y0 = 1140 - 130 * (k % 4)
            x = lerp(560, PX1, ease(u / 0.6, "inout"))
            y = y0 - 60 * math.sin(math.pi * u / 0.6)
            bola_calor(ctx, x, y, 20)
    kartel(ctx, "PLACA", 692, 300, 56, t, T_PLACA - 0.05, box=BLANCO, rot=-3)
    kartel(ctx, "VACÍO", 900, 1250, 60, t, T_VACIO - 0.1, box=BLANCO, rot=4)
    ctx.restore()


# ------------------------------------------------------------------ 10. para no cocinarse, el traje fabrica hielo
T_PARA = b(14)
T_COCINARSE = b(14, "cocinarse")
T_LUGAR = b(14, "lugar")
T_FRIO = b(14, "frio")
T_EXISTE = b(14, "existe")
T_FABRICA = b(14, "fabrica")
T_HIELO14 = b(14, "hielo")
T_AUNQUE = b(15)


def d_fabrica(ctx, t):
    calor = lerp(0.9, 0.0, prog(t, T_COCINARSE - 0.1, 1.0))
    z = lerp(1.14, 1.0, prog(t, T_PARA - 0.08, 1.2, "out"))

    def extra(ctx, u, ax, ay, s, rot):
        if t < T_FABRICA - 0.1:
            return
        hz = pop(t, T_FABRICA - 0.1, 0.35)
        for k, (lx, ly) in enumerate(((-168, -520), (-168, -360), (168, -470), (168, -330))):
            x, y = a_mundo(ax, ay, s, lx, ly)
            copo(ctx, x, y, 24 * clamp(hz * 1.3 - 0.15 * k), rot=k + t * 0.3)
        # hilito de vapor que sale de la mochila
        x0, y0 = a_mundo(ax, ay, s, 172, -400)
        for k in range(8):
            q = ((t - T_FABRICA) * 0.9 + k / 8) % 1
            if t - T_FABRICA < k * 0.08:
                continue
            nube(ctx, x0 + 40 + q * 300, y0 - 30 * q + 8 * math.sin(q * 7 + k), lerp(10, 32, q), 0.9 * (1 - q * q) * hz)

    escena_espacio(ctx, t, calor=calor, empa=calor, th=False, z=z, glow=calor * 0.8, extra=extra)
    # el lugar más frío que existe
    hielo = prog(t, T_LUGAR - 0.1, 0.5) * sale(t, T_AUNQUE - 0.25, 0.3)
    if hielo > 0.01:
        for cx_, cy_ in ((0, 0), (W, 0), (0, H), (W, H)):
            _elipse_suave(ctx, cx_, cy_, 520, 520, FRIO, 0.55 * hielo)
        rr = rng(51)
        for k in range(16):
            esq = k % 4
            bx = (0, W, 0, W)[esq] + (1 if esq in (0, 2) else -1) * rr.uniform(20, 240)
            by = (0, 0, H, H)[esq] + (1 if esq in (0, 1) else -1) * rr.uniform(20, 260)
            copo(ctx, bx, by, rr.uniform(14, 30) * clamp(hielo * 1.5 - k * 0.04), rot=k)
    sello(ctx, "−270 °C", 690, 300, 84, t, T_FRIO - 0.05, T_FABRICA - 0.2, rot=-6, col=FRIO_OSC)


# ------------------------------------------------------------------ 11. cierre: vuelve el primer cuadro
def d_cierre(ctx, t):
    d_apertura(ctx, t - TOTAL)


# ------------------------------------------------------------------ composición
ESCENAS = [
    (0.0, d_apertura),
    (b(2) - 0.08, d_pregunta),
    (b(3) - 0.08, d_tierra),
    (b(4) - 0.08, d_vacio),
    (b(5) - 0.08, d_termo),
    (b(7) - 0.08, d_esfuerzo),
    (b(8) - 0.08, d_malla),
    (b(11) - 0.08, d_giro),
    (b(12) - 0.08, d_placa),
    (b(14) - 0.08, d_fabrica),
    (b(15) - 0.08, d_cierre),
]
XF = 0.18


def punch(t, t0, d=0.3, amp=0.05):
    return 1 + amp * (1 - ease(clamp((t - t0) / d), "out"))


def escena(t):
    return max(k for k, (t0, _) in enumerate(ESCENAS) if t >= t0)


def componer(ctx, t):
    i = escena(t)
    t0, fn = ESCENAS[i]
    dt = t - t0
    ultima = i == len(ESCENAS) - 1          # el cierre no lleva golpe de zoom: tiene que terminar igual al inicio
    sin_punch = ultima or fn in (d_placa,)
    if i > 0 and dt < XF:
        capa(ctx, ESCENAS[i - 1][1], t)
        ctx.save()
        ctx.push_group()
        if not sin_punch:
            zoom(ctx, punch(t, t0))
        fn(ctx, t)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(clamp(dt / XF))
        ctx.restore()
        return
    if i > 0 and not sin_punch:
        zoom(ctx, punch(t, t0))
    fn(ctx, t)


CAPS = motor.Captions(WORDS, {"size": 76, "y": 1470, "max_palabras": 3, "max_letras": 18})


def cuadro(t):
    s, ctx = lienzo()
    try:
        componer(ctx, min(t, TOTAL))
    except Exception as e:
        raise RuntimeError(f"falló el cuadro en t={t:.3f}: {e}") from e
    im = Image.fromarray(a_rgb(s))
    CAPS.draw(im, t)
    return im


# ------------------------------------------------------------------ sonido (solo golpes cortos, sin sonidos sostenidos)
def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # 1. apertura
    ev(0.5, "tick", 0.25, f=900, d=0.05)
    ev(0.9, "tick", 0.25, f=750, d=0.05)
    ev(T_270, "pop", 0.5)
    ev(T_CERO - 0.1, "tick", 0.35, f=2400, d=0.04)
    ev(T_CERO + 0.1, "tick", 0.3, f=2600, d=0.04)
    ev(T_COCINAR - 0.2, "golpe", 0.6)
    ev(T_COCINAR, "pop", 0.35)
    # 2. pregunta
    ev(T_COMO - 0.05, "clunk", 0.4)
    ev(T_COCINAS - 0.05, "pop", 0.55)
    # 3. tierra
    ev(T_TIERRA - 0.05, "pop", 0.4)
    for bx, by, tb, tc in TB_CALOR:
        ev(tb, "tick", 0.18, f=1300, d=0.03)
    ev(T_ENFRIAS, "ding", 0.3)
    for bx, by, tb, tc in TB_CALOR[::2]:
        ev(tc, "plop", 0.25)
    # 4. vacío
    ev(T_NO4, "pop", 0.45)
    for k in range(len(FANT)):
        ev(T_AIRE4 - 0.03 + 0.07 * k, "tick", 0.3, f=500, d=0.06)
    # 5. termo
    ev(T_TERMO - 0.05, "pop", 0.45)
    ev(T_PAREDES - 0.05, "clic", 0.4)
    ev(T_NO5 - 0.1, "pop", 0.35)
    for h_ in HORAS:
        ev(h_, "tick", 0.25, f=1800, d=0.03)
    ev(HORAS[-1] + 0.1, "ding", 0.35)
    ev(T_ASTRO6 - 0.05, "pop", 0.5)
    ev(T_CAFE6 + 0.05, "ding", 0.4)
    # 6. esfuerzo
    for k in range(VUELTAS):
        tk = V0 + (V1 - V0) * (k + 0.85) / VUELTAS
        ev(tk, "clunk", 0.45)
        ev(tk + 0.05, "tick", 0.3, f=1100 + 200 * k, d=0.05)
    # 7. malla
    ev(T_DEBAJO, "clic", 0.4)
    ev(T_MALLA - 0.1, "pop", 0.35)
    for k in range(6):
        ev(T_70 + 0.1 * k, "tick", 0.22, f=1500 + 150 * k, d=0.03)
    ev(T_70 + 0.6, "ding", 0.4)
    ev(T_FRIA - 0.15, "pop", 0.4)
    ev(T_CALIENTA9, "tick", 0.35, f=700, d=0.07)
    ev(T_DONDE - 0.05, "pop", 0.5)
    ev(T_TIRA10 + 0.25, "golpe", 0.45)
    ev(T_AFUERA10 + 0.2, "golpe", 0.45)
    ev(T_NADA - 0.05, "pop", 0.4)
    # 8. giro y cubito
    ev(T_LO + 0.05, "clic", 0.35)
    ev(T_HIELO11 - 0.3, "pop", 0.5)
    ev(T_HIELO11 - 0.1, "ding", 0.45)
    # 9. placa
    for k in range(0, 26, 4):
        ev(T_DEJA - 0.1 + k * 0.12 + 0.5, "plop", 0.2)
    ev(T_PLACA - 0.05, "clic", 0.4)
    ev(T_VACIO - 0.1, "pop", 0.4)
    for k in range(6):
        ev(T_CONGELA - 0.1 + 0.07 * k, "tick", 0.3, f=2600 + 120 * k, d=0.03)
    ev(T_EVAPORA - 0.05, "pop", 0.3)
    for k in range(4):
        ev(T_LLEVANDO - 0.5 + 0.36 * k, "plop", 0.25)
    ev(T_CALOR13, "ding", 0.4)
    # 10. fábrica de hielo
    ev(T_COCINARSE + 0.6, "ding", 0.35)
    ev(T_FRIO - 0.05, "golpe", 0.6)
    ev(T_FABRICA - 0.1, "pop", 0.4)
    for k in range(4):
        ev(T_FABRICA + 0.05 * k, "tick", 0.25, f=2400 + 150 * k, d=0.03)
    # 11. cierre
    ev(TOTAL - 0.95 + 0.5, "tick", 0.25, f=900, d=0.05)
    return E


def pista_efectos():
    n = int((TOTAL + 3) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = K.snd(k, **kw) * v
        i0 = int(t * SR)
        i1 = min(n, i0 + len(x))
        if 0 <= i0 < n:
            mix[i0:i1] += x[:i1 - i0]
    mix = mix[:int(TOTAL * SR)]
    fade = int(0.08 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix *= 0.4 / (np.abs(mix).max() or 1)
    return mix


# ------------------------------------------------------------------ render
def _seg(args):
    f0, f1, out = args
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
           str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        p.stdin.write(cuadro(f / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return out


def render(salida, hilos=2):
    fb = int(math.ceil(TOTAL * FPS))
    tmp = tempfile.mkdtemp(prefix="render_", dir=AQUI)
    k = hilos * 3
    bounds = [round(fb * i / k) for i in range(k + 1)]
    segs = [(bounds[i], bounds[i + 1], os.path.join(tmp, f"seg{i:02d}.mp4")) for i in range(k)]
    with Pool(hilos) as pool:
        files = pool.map(_seg, segs, chunksize=1)
    lst = os.path.join(tmp, "lista.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{x}'\n" for x in files)
    video = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video],
                   check=True)
    sfx = os.path.join(tmp, "efectos.wav")
    P.escribir_wav(sfx, pista_efectos())
    voz = os.path.join(AQUI, "audio", "voz.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", voz, "-i", sfx,
                    "-filter_complex", "[1:a][2:a]amix=inputs=2:normalize=0:duration=first,"
                    "alimiter=limit=0.89:level=false[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.3f}",
                    salida], check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def hoja(tiempos, salida, cols=5):
    """Hoja de fotogramas: miniaturas con su segundo, para revisar antes del render."""
    tw, th = 270, 480
    filas = math.ceil(len(tiempos) / cols)
    im = Image.new("RGB", (cols * tw, filas * th), (0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, t in enumerate(tiempos):
        x, y = (k % cols) * tw, (k // cols) * th
        im.paste(cuadro(t).resize((tw, th), Image.LANCZOS), (x, y))
        d.rectangle((x, y, x + 78, y + 24), fill=(0, 0, 0))
        d.text((x + 5, y + 5), f"{t:.2f}", fill=(255, 255, 0))
    im.save(salida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fotos")
    ap.add_argument("--hoja", help="segundos separados por coma; arma una hoja de miniaturas")
    ap.add_argument("--dir", default=os.path.join(AQUI, "fotos"))
    ap.add_argument("--nombre", default="hoja.png")
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "cocinarse_a_270_bajo_cero.mp4"))
    ap.add_argument("--hilos", type=int, default=2)
    ap.add_argument("--probar", action="store_true", help="dibuja 1 de cada 6 cuadros para cazar errores")
    a = ap.parse_args()
    if a.probar:
        for f in range(0, int(TOTAL * FPS), 6):
            cuadro(f / FPS)
        pista_efectos()
        print("sin errores")
        return
    if a.hoja:
        os.makedirs(a.dir, exist_ok=True)
        hoja([float(x) for x in a.hoja.split(",")], os.path.join(a.dir, a.nombre))
        print("hoja en", os.path.join(a.dir, a.nombre))
        return
    if a.fotos:
        os.makedirs(a.dir, exist_ok=True)
        for ts in a.fotos.split(","):
            t = float(ts)
            cuadro(t).save(os.path.join(a.dir, f"f_{t:06.2f}.png"))
        print("fotos en", a.dir)
        return
    os.makedirs(os.path.dirname(a.salida), exist_ok=True)
    render(a.salida, a.hilos)
    print("listo:", a.salida, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    main()
