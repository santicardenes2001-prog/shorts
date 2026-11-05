"""Short "El picante no es un sabor" — animación procedural; Vos solo en la apertura.

    python proyectos/picante/picante.py --fotos 1,5.5,14
    python proyectos/picante/picante.py            # render completo -> salidas/el_picante.mp4

Reutiliza las herramientas de proyectos/pantalla/pantalla.py (cairo, carteles, sonidos, subtítulos).
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
from multiprocessing import Pool

import cairo
import cairosvg
import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "proyectos", "pantalla"))
import kit  # noqa: E402
import motor  # noqa: E402
import pantalla as P  # noqa: E402
from pantalla import (AMARILLO, BLANCO, INK, LILITA, a_rgb, bump, cartel, clamp, desde_rgb, ease, flecha, hx,  # noqa: E402
                      lerp, lienzo, pop, prog, punto_brillo, rng, rrect, texto, zoom_lineal)

W, H, FPS, SR = 1080, 1920, 30, 48000

NARRACION = [
    "El picante no es un sabor.",                                                                       # b0
    "Es una alarma de incendio sin fuego.",                                                             # b1
    "Tu lengua tiene sensores que avisan cuando algo quema, a partir de unos 43 grados.",               # b2
    "El ají trae una sustancia que encaja justo en esos sensores, como una llave falsa.",               # b3
    "Tu cerebro recibe la misma señal que con un café muy caliente, pero tu boca no subió ni un grado.",  # b4
    "Por eso transpiras, te pones rojo y te lloran los ojos: tu cuerpo intenta apagar un incendio que no existe.",  # b5
    "Esta sustancia, la capsaicina, no se mezcla con el agua: tomarla solo la esparce por toda la boca.",  # b6
    "La leche sí funciona, porque su grasa atrapa la capsaicina y la despega de la lengua.",            # b7
    "Lo más raro es que la capsaicina no quema a los pájaros.",                                         # b8
    "Ellos sienten el calor como tú, pero esta llave falsa no encaja en sus sensores.",                 # b9
    "Se tragan el ají con las semillas, sin masticarlas, y las semillas salen enteras en sus excrementos, "
    "lejos de la planta.",                                                                              # b10
    "Así crecen ajíes nuevos.",                                                                         # b11
    "Un ratón, en cambio, mastica las semillas y las destruye.",                                        # b12
    "Para muchos científicos, el picante existe para eso: para espantar a los animales que mastican.",  # b13
    "Como tú.",                                                                                         # b14
]
WORDS = motor.align_times([{"texto": t} for t in NARRACION],
                          json.load(open(os.path.join(AQUI, "audio", "palabras.json"))))
COLA = 0.8
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
ROJO = hx("#FF3B2F")
ROJO2 = hx("#C4161C")
NARANJA = hx("#FF8A1F")
VERDE = hx("#3DBE5C")
VERDE2 = hx("#23863D")
ROSA = hx("#FF8FA3")
ROSA2 = hx("#E0607A")
TEAL = hx("#2EC4B6")
AZUL_AGUA = hx("#5EC8FF")
CREMA = hx("#FFF1C9")


def mezcla(c0, c1, p):
    return tuple(lerp(a, c, clamp(p)) for a, c in zip(c0, c1))


# ------------------------------------------------------------------ fondos
def fondo_calido(ctx, t, giro=True):
    g = cairo.RadialGradient(540, 820, 60, 540, 900, 1250)
    g.add_color_stop_rgb(0, *hx("#FFB347"))
    g.add_color_stop_rgb(0.55, *hx("#FF5E3A"))
    g.add_color_stop_rgb(1, *hx("#8E1414"))
    ctx.set_source(g)
    ctx.paint()
    if giro:
        ctx.save()
        ctx.translate(540, 860)
        ctx.rotate(t * 0.12)
        for k in range(16):
            ctx.move_to(0, 0)
            a0 = k * math.pi * 2 / 16
            ctx.arc(0, 0, 1700, a0, a0 + math.pi / 16)
            ctx.close_path()
        ctx.set_source_rgba(1, 1, 0.8, 0.08)
        ctx.fill()
        ctx.restore()


def fondo_boca(ctx, t):
    g = cairo.RadialGradient(540, 700, 80, 540, 900, 1300)
    g.add_color_stop_rgb(0, *hx("#7A1E2C"))
    g.add_color_stop_rgb(1, *hx("#250509"))
    ctx.set_source(g)
    ctx.paint()


def fondo_oscuro(ctx, t):
    P.fondo(ctx, t, tinte=(0.10, 0.025, 0.03))


def fondo_exterior(ctx, t, pan=0.0):
    g = cairo.LinearGradient(0, 0, 0, 1300)
    g.add_color_stop_rgb(0, *hx("#7FD3FF"))
    g.add_color_stop_rgb(1, *hx("#DFF6FF"))
    ctx.set_source(g)
    ctx.paint()
    ctx.arc(880, 260, 90, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#FFE066"))
    ctx.fill()
    for i, (cx, cy, s) in enumerate(((180, 300, 1.0), (620, 180, 0.8), (1000, 420, 1.1), (1400, 260, 0.9))):
        x = (cx - t * 18 - pan * 0.3 + i * 0) % 1500 - 200
        ctx.save()
        ctx.translate(x, cy)
        ctx.scale(s, s)
        for dx, dy, r in ((0, 0, 50), (55, -20, 60), (115, 0, 48), (60, 15, 50)):
            ctx.arc(dx, dy, r, 0, 2 * math.pi)
            ctx.new_sub_path()
        ctx.set_source_rgba(1, 1, 1, 0.9)
        ctx.fill()
        ctx.restore()
    # colinas
    for capa, (col, base, amp, f, vel) in enumerate((("#8ED47A", 1180, 70, 0.006, 0.5),
                                                       ("#5DB85A", 1260, 50, 0.009, 1.0))):
        ctx.move_to(0, 1920)
        for x in range(0, 1100, 20):
            y = base - amp * math.sin((x + pan * vel) * f + capa)
            ctx.line_to(x, y)
        ctx.line_to(1080, 1920)
        ctx.close_path()
        ctx.set_source_rgb(*hx(col))
        ctx.fill()


# ------------------------------------------------------------------ piezas
def aji(ctx, x, y, s=1.0, rot=0.0, mordida=0.0, color=ROJO, alpha=1.0):
    """Ají con la punta hacia +x; (x, y) es el centro del cuerpo."""
    if s <= 0.01 or alpha <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    ctx.push_group()
    ctx.translate(-100, 0)

    def cuerpo():
        ctx.new_path()
        ctx.move_to(0, -40)
        ctx.curve_to(80, -62, 200, -34, 252, 22)
        ctx.curve_to(196, 18, 92, 52, 0, 40)
        ctx.curve_to(-18, 22, -18, -22, 0, -40)
        ctx.close_path()

    cuerpo()
    g = cairo.LinearGradient(0, -50, 0, 50)
    g.add_color_stop_rgb(0, *mezcla(color, (1, 1, 1), 0.15))
    g.add_color_stop_rgb(1, *mezcla(color, (0, 0, 0), 0.25))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.move_to(30, -26)
    ctx.curve_to(90, -40, 160, -24, 200, 2)
    ctx.set_source_rgba(1, 1, 1, 0.45)
    ctx.set_line_width(9)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    # cáliz y tallo
    ctx.move_to(-12, 0)
    ctx.curve_to(-40, -10, -60, -40, -78, -70)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(20)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*VERDE2)
    ctx.set_line_width(10)
    ctx.stroke()
    for ang in (-50, 0, 50):
        ctx.save()
        ctx.rotate(math.radians(ang))
        ctx.move_to(-6, 0)
        ctx.curve_to(10, -30, 40, -26, 36, 0)
        ctx.curve_to(40, 26, 10, 30, -6, 0)
        ctx.set_source_rgb(*VERDE)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.restore()
    if mordida > 0:
        xc = 252 - mordida * 150
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        for k in range(-3, 4):
            ctx.arc(xc + 40, k * 26, 34, 0, 2 * math.pi)
            ctx.new_sub_path()
        ctx.rectangle(xc + 40, -90, 300, 180)
        ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
        # pulpa visible en el corte
        ctx.save()
        cuerpo()
        ctx.clip()
        for k in range(-3, 4):
            ctx.arc(xc + 40, k * 26, 40, 0, 2 * math.pi)
            ctx.new_sub_path()
        ctx.set_source_rgba(1, 0.85, 0.6, 0.9)
        ctx.set_line_width(10)
        ctx.stroke()
        for k in range(4):
            ctx.arc(xc + 2 + (k % 2) * 12, -18 + k * 12, 6, 0, 2 * math.pi)
            ctx.new_sub_path()
        ctx.set_source_rgb(*CREMA)
        ctx.fill()
        ctx.restore()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def llama(ctx, x, y, s, t, alpha=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    f = 1 + 0.08 * math.sin(t * 17) + 0.05 * math.sin(t * 29)
    for col, k in ((hx("#FF5A1F"), 1.0), (hx("#FFC23D"), 0.62)):
        ctx.save()
        ctx.scale(k, k * f)
        ctx.move_to(0, 60)
        ctx.curve_to(-70, 50, -70, -20, -20, -60)
        ctx.curve_to(-10, -30, 0, -90, 0, -110)
        ctx.curve_to(30, -70, 70, -40, 62, 10)
        ctx.curve_to(60, 50, 30, 62, 0, 60)
        ctx.close_path()
        ctx.set_source_rgba(*col, alpha)
        ctx.fill_preserve()
        if k == 1.0:
            ctx.set_source_rgba(*INK, alpha)
            ctx.set_line_width(7)
            ctx.stroke()
        ctx.new_path()
        ctx.restore()
    ctx.restore()


def prohibido(ctx, x, y, r, s=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for lw, col in ((34, INK), (22, hx("#FF2D2D"))):
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.move_to(-r * 0.7, -r * 0.7)
        ctx.line_to(r * 0.7, r * 0.7)
        ctx.set_source_rgb(*col)
        ctx.set_line_width(lw)
        ctx.stroke()
    ctx.restore()


def sello(ctx, txt, x, y, ok, s=1.0, rot=-8):
    if s <= 0.01:
        return
    col = hx("#2BB24C") if ok else hx("#FF2D2D")
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    bw, bh = cartel(ctx, txt, 60, 0, 76, box=BLANCO, fg=col, borde=8)
    ix = 60 - bw / 2 - 44
    ctx.arc(ix, 0, 56, 0, 2 * math.pi)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if ok:
        ctx.move_to(ix - 26, 2)
        ctx.line_to(ix - 6, 24)
        ctx.line_to(ix + 28, -22)
    else:
        ctx.move_to(ix - 22, -22)
        ctx.line_to(ix + 22, 22)
        ctx.move_to(ix + 22, -22)
        ctx.line_to(ix - 22, 22)
    ctx.set_source_rgb(*BLANCO)
    ctx.set_line_width(14)
    ctx.stroke()
    ctx.restore()


def campana(ctx, x, y, s, t, sonando=True):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    if sonando:
        for k in range(12):
            a = k * math.pi / 6 + t * 1.5
            ctx.move_to(0, -10)
            ctx.arc(0, -10, 330, a, a + 0.12)
            ctx.close_path()
        ctx.set_source_rgba(1, 0.2, 0.15, 0.18 + 0.12 * math.sin(t * 20))
        ctx.fill()
        for sg in (-1, 1):
            for k in range(3):
                ctx.new_sub_path()
                ctx.arc(sg * 0, -20, 150 + k * 42, (-0.45 if sg > 0 else math.pi - 0.45), (0.45 if sg > 0 else math.pi + 0.45))
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(11)
            ctx.stroke_preserve()
            ctx.set_source_rgb(*BLANCO)
            ctx.set_line_width(5)
            ctx.stroke()
        ctx.rotate(math.radians(12 * math.sin(t * 40)))
    ctx.move_to(-110, 60)
    ctx.curve_to(-110, -60, -80, -120, 0, -125)
    ctx.curve_to(80, -120, 110, -60, 110, 60)
    ctx.curve_to(130, 75, 130, 90, 0, 90)
    ctx.curve_to(-130, 90, -130, 75, -110, 60)
    ctx.close_path()
    g = cairo.LinearGradient(-110, 0, 110, 0)
    g.add_color_stop_rgb(0, *hx("#FF6B5B"))
    g.add_color_stop_rgb(0.5, *hx("#FF2D2D"))
    g.add_color_stop_rgb(1, *hx("#B8141A"))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.arc(0, 108, 26, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#FFC23D"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    rrect(ctx, -18, -150, 36, 30, 10)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.move_to(-62, -60)
    ctx.curve_to(-70, -10, -70, 20, -66, 50)
    ctx.set_source_rgba(1, 1, 1, 0.5)
    ctx.set_line_width(12)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.restore()


def lengua(ctx, y0, t, seed=5):
    ctx.save()
    ctx.move_to(60, 1960)
    ctx.line_to(60, y0 + 230)
    ctx.curve_to(60, y0 - 50, 1020, y0 - 50, 1020, y0 + 230)
    ctx.line_to(1020, 1960)
    ctx.close_path()
    path = ctx.copy_path()
    g = cairo.LinearGradient(0, y0, 0, y0 + 900)
    g.add_color_stop_rgb(0, *ROSA)
    g.add_color_stop_rgb(1, *ROSA2)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.append_path(path)
    ctx.clip()
    r = rng(seed)
    for _ in range(260):
        px, py = r.uniform(60, 1020), r.uniform(y0, 1920)
        rr = r.uniform(4, 11)
        ctx.arc(px, py, rr, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.8, 0.85, 0.35)
        ctx.fill()
    ctx.move_to(540, y0 + 60)
    ctx.curve_to(530, y0 + 400, 550, y0 + 800, 540, 1920)
    ctx.set_source_rgba(0.6, 0.15, 0.25, 0.35)
    ctx.set_line_width(16)
    ctx.stroke()
    ctx.restore()


def sensor(ctx, x, y, r, alarma, t, s=1.0, forma="redonda"):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    col = mezcla(TEAL, hx("#FF2D2D"), alarma)
    if alarma > 0.05:
        for k in range(2):
            q = ((t * 1.6 + k * 0.5) % 1)
            ctx.arc(0, 0, r * (1 + q * 1.4), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.2, 0.15, 0.6 * (1 - q) * alarma)
            ctx.set_line_width(6)
            ctx.stroke()
        g = cairo.RadialGradient(0, 0, r * 0.5, 0, 0, r * 2.2)
        g.add_color_stop_rgba(0, 1, 0.25, 0.2, 0.55 * alarma)
        g.add_color_stop_rgba(1, 1, 0.25, 0.2, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, r * 2.2, 0, 2 * math.pi)
        ctx.fill()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(max(4, r * 0.12))
    ctx.stroke()
    _ojo_cerradura(ctx, r * 0.55, forma)
    ctx.restore()


def _ojo_cerradura(ctx, k, forma="redonda"):
    ctx.set_source_rgb(*INK)
    if forma == "redonda":
        ctx.arc(0, -k * 0.25, k * 0.38, 0, 2 * math.pi)
        ctx.fill()
        ctx.move_to(-k * 0.2, -k * 0.1)
        ctx.line_to(k * 0.2, -k * 0.1)
        ctx.line_to(k * 0.32, k * 0.72)
        ctx.line_to(-k * 0.32, k * 0.72)
        ctx.close_path()
        ctx.fill()
    else:  # estrella: la cerradura de los pájaros
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = k * (0.7 if i % 2 == 0 else 0.3)
            (ctx.move_to if i == 0 else ctx.line_to)(math.cos(a) * rr, math.sin(a) * rr)
        ctx.close_path()
        ctx.fill()


def cerradura(ctx, x, y, r, alarma, t, forma="redonda", s=1.0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    if alarma > 0.05:
        for k in range(3):
            q = ((t * 1.3 + k / 3) % 1)
            ctx.arc(0, 0, r * (1 + q * 0.9), 0, 2 * math.pi)
            ctx.set_source_rgba(1, 0.2, 0.15, 0.55 * (1 - q) * alarma)
            ctx.set_line_width(10)
            ctx.stroke()
    g = cairo.RadialGradient(-r * 0.3, -r * 0.3, r * 0.1, 0, 0, r)
    base = mezcla(hx("#C9D3DD"), hx("#FF5A4F"), alarma)
    g.add_color_stop_rgb(0, *mezcla(base, (1, 1, 1), 0.5))
    g.add_color_stop_rgb(1, *mezcla(base, (0, 0, 0), 0.3))
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.stroke()
    for k in range(6):
        a = k * math.pi / 3 + 0.5
        ctx.arc(math.cos(a) * r * 0.82, math.sin(a) * r * 0.82, r * 0.05, 0, 2 * math.pi)
        ctx.set_source_rgb(*mezcla(base, (0, 0, 0), 0.45))
        ctx.fill()
    _ojo_cerradura(ctx, r * 0.62, forma)
    ctx.restore()


def llave(ctx, x, y, s=1.0, rot=0.0, alpha=1.0):
    """Llave naranja; (x, y) es la punta de la paleta (lo que entra en la cerradura)."""
    if s <= 0.01 or alpha <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    ctx.push_group()
    col = NARANJA
    ctx.move_to(-300, 0)
    ctx.line_to(0, 0)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for lw, c in ((38, INK), (24, col)):
        ctx.move_to(-300, 0)
        ctx.line_to(-6, 0)
        ctx.set_source_rgb(*c)
        ctx.set_line_width(lw)
        ctx.stroke()
    for dx in (-70, -30):
        rrect(ctx, dx - 12, 4, 24, 40, 6)
        ctx.set_source_rgb(*col)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.stroke()
    ctx.arc(-350, 0, 62, 0, 2 * math.pi)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.arc(-350, 0, 22, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def termometro(ctx, x, y, h, frac, s=1.0):
    """(x, y) = centro del bulbo; frac 0..1 de la columna."""
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    rrect(ctx, -30, -h, 60, h + 20, 30)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.arc(0, 0, 52, 0, 2 * math.pi)
    ctx.set_source_rgb(*ROJO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    hh = (h - 30) * clamp(frac)
    rrect(ctx, -14, -hh - 10, 28, hh + 30, 14)
    ctx.set_source_rgb(*ROJO)
    ctx.fill()
    for k in range(1, 6):
        yy = -k * (h - 30) / 6
        ctx.move_to(14, yy)
        ctx.line_to(30, yy)
    ctx.set_source_rgba(*INK, 0.5)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.restore()


def taza(ctx, x, y, s, t):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    for k in range(3):
        ph = t * 1.4 + k * 0.33
        q = ph % 1
        xx = -50 + k * 50
        ctx.move_to(xx, -110 - q * 120)
        for j in range(8):
            ctx.line_to(xx + 14 * math.sin(j * 1.2 + t * 4 + k), -110 - q * 120 - j * 16)
        ctx.set_source_rgba(1, 1, 1, 0.7 * (1 - q))
        ctx.set_line_width(9)
        ctx.stroke()
    ctx.arc(110, 0, 52, -math.pi / 2, math.pi / 2)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(30)
    ctx.stroke()
    ctx.arc(110, 0, 52, -math.pi / 2, math.pi / 2)
    ctx.set_source_rgb(*BLANCO)
    ctx.set_line_width(16)
    ctx.stroke()
    ctx.move_to(-110, -90)
    ctx.line_to(110, -90)
    ctx.line_to(90, 100)
    ctx.curve_to(80, 120, -80, 120, -90, 100)
    ctx.close_path()
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.save()
    ctx.scale(1, 0.25)
    ctx.arc(0, -90 / 0.25, 104, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*hx("#5A3420"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.restore()


def vaso(ctx, x, y, s, rot, color, nivel=0.75, blanco=False):
    """(x, y) = centro del vaso. rot en grados (inclinación para servir)."""
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    ctx.move_to(-80, -120)
    ctx.line_to(80, -120)
    ctx.line_to(64, 120)
    ctx.line_to(-64, 120)
    ctx.close_path()
    path = ctx.copy_path()
    ctx.set_source_rgba(0.85, 0.95, 1, 0.55)
    ctx.fill()
    ctx.save()
    ctx.append_path(path)
    ctx.clip()
    # el líquido queda horizontal aunque el vaso se incline
    ctx.rotate(-math.radians(rot))
    ys = lerp(120 - 240 * nivel, 10, clamp(abs(rot) / 100))
    ctx.rectangle(-400, ys, 800, 800)
    ctx.set_source_rgba(*color, 0.97 if blanco else 0.9)
    ctx.fill()
    ctx.restore()
    ctx.append_path(path)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.move_to(-56, -96)
    ctx.line_to(-46, 96)
    ctx.set_source_rgba(1, 1, 1, 0.6)
    ctx.set_line_width(10)
    ctx.stroke()
    ctx.restore()


def chorro(ctx, x0, y0, x1, y1, color, w, t, alpha=1.0):
    ctx.save()
    ctx.move_to(x0, y0)
    ctx.curve_to(x0 + 40, y0 + 40, x1, y0 + 80, x1, y1)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgba(*INK, alpha)
    ctx.set_line_width(w + 10)
    ctx.stroke_preserve()
    ctx.set_source_rgba(*color, alpha)
    ctx.set_line_width(w)
    ctx.stroke()
    ctx.restore()


def gota(ctx, x, y, r, color, alpha=1.0, borde=True):
    """Gota en forma de lágrima con la punta hacia arriba."""
    ctx.save()
    ctx.translate(x, y)
    ctx.move_to(0, -r * 1.8)
    ctx.curve_to(r * 0.4, -r * 1.0, r, -r * 0.4, r, r * 0.15)
    ctx.arc(0, r * 0.15, r, 0, math.pi)
    ctx.curve_to(-r, -r * 0.4, -r * 0.4, -r * 1.0, 0, -r * 1.8)
    ctx.close_path()
    ctx.set_source_rgba(*color, alpha)
    ctx.fill_preserve()
    if borde:
        ctx.set_source_rgba(*INK, alpha)
        ctx.set_line_width(max(3, r * 0.14))
        ctx.stroke()
    ctx.new_path()
    ctx.arc(-r * 0.35, -r * 0.1, r * 0.22, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.7 * alpha)
    ctx.fill()
    ctx.restore()


def gotita_aceite(ctx, x, y, r, envuelta=0.0, alpha=1.0):
    if envuelta > 0:
        for k in range(8):
            a = k * math.pi / 4
            ctx.arc(x + math.cos(a) * r * 1.25, y + math.sin(a) * r * 1.25, r * 0.55 * envuelta, 0, 2 * math.pi)
            ctx.new_sub_path()
        ctx.set_source_rgba(1, 1, 0.97, alpha)
        ctx.fill_preserve()
        ctx.set_source_rgba(*INK, 0.6 * alpha)
        ctx.set_line_width(3)
        ctx.stroke()
    g = cairo.RadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r)
    g.add_color_stop_rgba(0, 1, 0.85, 0.4, alpha)
    g.add_color_stop_rgba(1, 0.95, 0.4, 0.05, alpha)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, alpha)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.arc(x - r * 0.35, y - r * 0.35, r * 0.25, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.75 * alpha)
    ctx.fill()


def globulo(ctx, x, y, r, alpha=1.0):
    g = cairo.RadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r)
    g.add_color_stop_rgba(0, 1, 1, 1, alpha)
    g.add_color_stop_rgba(1, 0.88, 0.88, 0.82, alpha)
    ctx.arc(x, y, r, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, 0.7 * alpha)
    ctx.set_line_width(3)
    ctx.stroke()


def semilla(ctx, x, y, s, rot=0.0, rota=0.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    if rota > 0:
        for k in range(5):
            a = k * 2 * math.pi / 5
            d = 26 * rota
            ctx.save()
            ctx.translate(math.cos(a) * d, math.sin(a) * d)
            ctx.rotate(a * 2)
            ctx.move_to(-8, -6)
            ctx.line_to(9, -4)
            ctx.line_to(2, 9)
            ctx.close_path()
            ctx.set_source_rgb(*CREMA)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(3)
            ctx.stroke()
            ctx.restore()
    else:
        ctx.save()
        ctx.scale(1, 0.75)
        ctx.arc(0, 0, 16, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*CREMA)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(4)
        ctx.stroke()
    ctx.restore()


def pajaro(ctx, x, y, s, t, aleteo=0.0, pico=0.0, ojos="normal", xray=0.0, semillas=0, vuelo=False):
    """Pájaro original (redondo, celeste). (x, y) = centro del cuerpo."""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    azul, azul2 = hx("#3FA9F5"), hx("#2378C9")
    if not vuelo:
        for dx in (-30, 30):
            ctx.move_to(dx, 90)
            ctx.line_to(dx, 150)
            ctx.line_to(dx + 22, 160)
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(14)
            ctx.stroke_preserve()
            ctx.set_source_rgb(*hx("#FF9F1C"))
            ctx.set_line_width(7)
            ctx.stroke()
    # cola
    ctx.move_to(-100, 10)
    ctx.line_to(-190, -30)
    ctx.line_to(-180, 30)
    ctx.line_to(-200, 60)
    ctx.close_path()
    ctx.set_source_rgb(*azul2)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    a = 1 - xray * 0.65
    ctx.push_group()
    ctx.arc(0, 0, 115, 0, 2 * math.pi)
    ctx.set_source_rgb(*azul)
    ctx.fill()
    ctx.save()
    ctx.translate(15, 40)
    ctx.scale(1, 0.7)
    ctx.arc(0, 0, 70, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*hx("#BFE6FF"))
    ctx.fill()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    if xray > 0:
        ctx.save()
        ctx.arc(0, 0, 112, 0, 2 * math.pi)
        ctx.clip()
        ctx.rectangle(-120, -120, 240, 240)
        ctx.set_source_rgba(0.05, 0.1, 0.2, 0.3 * xray)
        ctx.fill()
        rr = rng(11)
        for k in range(semillas):
            px, py = rr.uniform(-55, 55), rr.uniform(-20, 70)
            semilla(ctx, px + 4 * math.sin(t * 3 + k), py, 1.35, rot=rr.uniform(0, 3))
        ctx.restore()
    ctx.arc(0, 0, 115, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    # ala
    ctx.save()
    ctx.translate(-20, 10)
    ctx.rotate(-aleteo * 1.1)
    ctx.scale(1, 0.6)
    ctx.arc(-30, 0, 62, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*azul2)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    # pico
    ctx.save()
    ctx.translate(100, -20)
    for sg, ang in ((-1, -pico * 25), (1, pico * 25)):
        ctx.save()
        ctx.rotate(math.radians(ang))
        ctx.move_to(0, 0)
        ctx.line_to(80, sg * 2)
        ctx.line_to(0, sg * 30)
        ctx.close_path()
        ctx.set_source_rgb(*hx("#FF9F1C"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.restore()
    ctx.restore()
    # ojo
    if ojos == "feliz":
        ctx.move_to(30, -50)
        ctx.curve_to(45, -75, 75, -75, 88, -50)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(9)
        ctx.stroke()
    else:
        rw = 30 if ojos == "grande" else 24
        ctx.arc(58, -48, rw, 0, 2 * math.pi)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.arc(66, -46, 10 if ojos == "grande" else 12, 0, 2 * math.pi)
        ctx.set_source_rgb(*INK)
        ctx.fill()
    ctx.restore()


def raton(ctx, x, y, s, t, mastica=False, rojo=0.0, huye=False):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    gris = mezcla(hx("#A9ADB5"), hx("#FF6B5B"), rojo)
    # cola
    ctx.move_to(-120, 80)
    ctx.curve_to(-230, 90, -240, -40, -300, 10)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(14)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*hx("#F4A3B4"))
    ctx.set_line_width(7)
    ctx.stroke()
    # cuerpo
    ctx.save()
    ctx.scale(1.25, 1)
    ctx.arc(-30, 40, 100, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*gris)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    # orejas
    for ox in (-30, 80):
        ctx.arc(ox, -120, 52, 0, 2 * math.pi)
        ctx.set_source_rgb(*gris)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7)
        ctx.stroke()
        ctx.arc(ox, -120, 30, 0, 2 * math.pi)
        ctx.set_source_rgb(*hx("#F4A3B4"))
        ctx.fill()
    # cabeza
    ctx.arc(40, -40, 85, 0, 2 * math.pi)
    ctx.set_source_rgb(*gris)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.stroke()
    ctx.move_to(100, -70)
    ctx.curve_to(170, -50, 175, -10, 150, -2)
    ctx.curve_to(120, 10, 100, 0, 90, -10)
    ctx.set_source_rgb(*gris)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.arc(160, -32, 14, 0, 2 * math.pi)
    ctx.set_source_rgb(*hx("#FF7A93"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    for k in (-1, 0, 1):
        ctx.move_to(140, -20 + k * 10)
        ctx.line_to(205, -30 + k * 22)
    ctx.set_source_rgba(*INK, 0.8)
    ctx.set_line_width(4)
    ctx.stroke()
    if rojo > 0.5:
        ctx.arc(60, -58, 22, 0, 2 * math.pi)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5)
        ctx.stroke()
        ctx.arc(66, -58, 8, 0, 2 * math.pi)
        ctx.set_source_rgb(*INK)
        ctx.fill()
    else:
        ctx.arc(70, -58, 12, 0, 2 * math.pi)
        ctx.set_source_rgb(*INK)
        ctx.fill()
    # boca y dientes
    ab = (0.5 + 0.5 * math.sin(t * 50)) if mastica else 0.0
    rrect(ctx, 112, 2 + ab * 6, 14, 22, 3)
    rrect(ctx, 128, 2 + ab * 6, 14, 22, 3)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.restore()


def planta_aji(ctx, x, y, s, crec, t, ajies=True):
    if crec <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    h = 360 * ease(crec, "out")
    ctx.move_to(0, 0)
    ctx.curve_to(10, -h * 0.3, -10, -h * 0.6, 0, -h)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(22)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*VERDE2)
    ctx.set_line_width(12)
    ctx.stroke()
    hojas = [(-0.35, -1), (-0.55, 1), (-0.75, -1), (-0.9, 1), (-1.0, 0)]
    for i, (fy, lado) in enumerate(hojas):
        k = clamp((crec - i * 0.12) / 0.3)
        if k <= 0:
            continue
        ctx.save()
        ctx.translate(0, h * fy)
        ctx.rotate(math.radians(-60 * lado if lado else -90) + 0.05 * math.sin(t * 2 + i))
        ctx.scale(k, k)
        ctx.move_to(0, 0)
        ctx.curve_to(30, -40, 100, -40, 130, 0)
        ctx.curve_to(100, 40, 30, 40, 0, 0)
        ctx.set_source_rgb(*VERDE)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.restore()
    if ajies:
        for i, (fx, fy, rot) in enumerate(((-60, -0.5, 100), (70, -0.68, 80), (-40, -0.85, 110))):
            k = clamp((crec - 0.6 - i * 0.1) / 0.25)
            if k > 0:
                aji(ctx, fx, h * fy + 60, 0.42 * pop(k, 0, 1), rot=rot)
    ctx.restore()


def boca_grande(ctx, x, y, s, cierre, t):
    """Boca con dientes vista de frente; cierre 0 = abierta, 1 = cerrada."""
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ab = 260 * (1 - ease(cierre, "in"))
    ctx.save()
    ctx.scale(1, max(0.05, (ab + 60) / 320))
    ctx.arc(0, 0, 330, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*hx("#5C0E1E"))
    ctx.fill()
    for sg in (-1, 1):
        yy = sg * ab / 2
        for k in range(-3, 4):
            rrect(ctx, k * 82 - 36, yy - (0 if sg > 0 else 90) - (6 if sg > 0 else -6), 72, 90, 22)
            ctx.set_source_rgb(*BLANCO)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(6)
            ctx.stroke()
        ctx.save()
        ctx.translate(0, yy + sg * 70)
        ctx.scale(1, 0.32)
        ctx.arc(0, 0, 360, math.pi if sg < 0 else 0, 2 * math.pi if sg < 0 else math.pi)
        ctx.restore()
        ctx.set_source_rgb(*hx("#E2445C"))
        ctx.set_line_width(70)
        ctx.stroke()
    ctx.restore()


# ------------------------------------------------------------------ Vos (solo en la apertura)
def _vos_svg(pose):
    P_ = kit.P
    viejo = dict(P_)
    try:
        if pose == "aji":
            izq = (kit.stroke_path("M 182 505 Q 150 575 148 652", P_["piel"], 28)
                   + f'<circle cx="148" cy="655" r="25" fill="{P_["piel"]}" stroke="{kit.INK}" stroke-width="{kit.SW}"/>')
            der = (kit.stroke_path("M 338 505 Q 430 520 372 438", P_["piel"], 28)
                   + f'<circle cx="372" cy="436" r="27" fill="{P_["piel"]}" stroke="{kit.INK}" stroke-width="{kit.SW}"/>')
            mangas = (f'<circle cx="186" cy="500" r="30" fill="{P_["remera"]}" stroke="{kit.INK}" stroke-width="{kit.SW}"/>'
                      f'<circle cx="334" cy="500" r="30" fill="{P_["remera"]}" stroke="{kit.INK}" stroke-width="{kit.SW}"/>')
            kit_arms = kit.arms
            kit.arms = lambda kind: (izq + der + mangas, "")
            try:
                body = kit.vos(eyes="happy", brows="happy", mouth_kind="open_smile")
            finally:
                kit.arms = kit_arms
        elif pose == "mastica":
            izq = (kit.stroke_path("M 182 505 Q 150 575 148 652", P_["piel"], 28)
                   + f'<circle cx="148" cy="655" r="25" fill="{P_["piel"]}" stroke="{kit.INK}" stroke-width="{kit.SW}"/>')
            der = (kit.stroke_path("M 338 505 Q 430 520 372 438", P_["piel"], 28)
                   + f'<circle cx="372" cy="436" r="27" fill="{P_["piel"]}" stroke="{kit.INK}" stroke-width="{kit.SW}"/>')
            mangas = (f'<circle cx="186" cy="500" r="30" fill="{P_["remera"]}" stroke="{kit.INK}" stroke-width="{kit.SW}"/>'
                      f'<circle cx="334" cy="500" r="30" fill="{P_["remera"]}" stroke="{kit.INK}" stroke-width="{kit.SW}"/>')
            kit_arms = kit.arms
            kit.arms = lambda kind: (izq + der + mangas, "")
            try:
                body = kit.vos(eyes="happy", brows="neutral", mouth_kind="mid")
            finally:
                kit.arms = kit_arms
        elif pose == "quema":
            P_["piel"] = "#FF7A66"
            P_["piel2"] = "#E5523F"
            body = kit.vos(eyes="wide", brows="up", mouth_kind="yawn", arm_kind="up")
        else:
            raise ValueError(pose)
    finally:
        P_.clear()
        P_.update(viejo)
    return kit.svg(520, 820, body)


@functools.lru_cache(maxsize=None)
def vos_surface(pose):
    png = cairosvg.svg2png(bytestring=_vos_svg(pose).encode(), output_width=1040, output_height=1640)
    return cairo.ImageSurface.create_from_png(io.BytesIO(png))


VK, VX, VY = 1.12, 540, 1580       # escala de Vos y posición de sus pies


def vpos(x, y, dx=0.0):
    return VX + dx + (x - 260) * VK, VY + (y - 806) * VK


def dibujar_vos(ctx, pose, alpha=1.0, dx=0.0, rot=0.0):
    if alpha <= 0.01:
        return
    s = vos_surface(pose)
    ctx.save()
    ctx.translate(VX + dx, VY)
    ctx.rotate(math.radians(rot))
    ctx.scale(VK / 2, VK / 2)
    ctx.translate(-520, -1612)
    ctx.set_source_surface(s, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def vapor(ctx, x, y, t, t0, lado):
    for k in range(5):
        q = ((t - t0) * 1.3 + k / 5) % 1
        if t - t0 < k * 0.12:
            continue
        r = lerp(18, 60, q)
        ctx.arc(x + lado * q * 90, y - q * 170, r, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 1, 0.75 * (1 - q))
        ctx.fill()


def sudor(ctx, x, y, t, t0, seed):
    r = rng(seed)
    for k in range(6):
        ph = r.uniform(0, 1)
        q = ((t - t0) * 1.1 + ph) % 1
        if t - t0 < ph * 0.4:
            continue
        lado = -1 if k % 2 else 1
        px = x + lado * (60 + q * 160) + r.uniform(-30, 30)
        py = y - 60 + q * q * 420 - 120 * q
        gota(ctx, px, py, 16, AZUL_AGUA, alpha=1 - q * 0.6)


# ------------------------------------------------------------------ escenas
S = [0.0, b(2), b(3), b(4), b(5), b(6), b(7), b(8), b(10), b(12), b(13)]
S = [S[0]] + [x - 0.08 for x in S[1:]]
T_BITE = b(0, "picante") + 0.28
T_QUEMA = b(0, "sabor") + 0.1


def escena_de(t):
    i = 0
    for k, s0 in enumerate(S):
        if t >= s0:
            i = k
    return i


def titulo_gancho(ctx, t, s=1.0):
    cartel(ctx, "EL PICANTE\nNO ES UN SABOR", 540, 245, 84, s=s * (1 + 0.012 * math.sin(t * 2.4)), pad=(56, 26))


def sc_gancho(t):
    s, ctx = lienzo()
    fondo_calido(ctx, t)
    alarma = clamp((t - b(1, "alarma")) / 0.25) if t >= b(1, "alarma") else 0
    if alarma > 0:
        q = 0.5 + 0.5 * math.sin(t * 14)
        g = cairo.RadialGradient(540, 960, 400, 540, 960, 1200)
        g.add_color_stop_rgba(0, 1, 0, 0, 0)
        g.add_color_stop_rgba(1, 1, 0, 0, 0.45 * q * alarma)
        ctx.set_source(g)
        ctx.paint()
    # Vos
    temblor = 7 * math.sin(t * 60) * clamp((t - T_QUEMA) / 0.1) * (1 - clamp((t - T_QUEMA - 0.9) / 0.4))
    if t < T_BITE:
        pose, mord = "aji", 0.0
    elif t < T_QUEMA:
        pose, mord = "mastica", 1.0
    else:
        pose, mord = "quema", 1.0
    if pose == "quema":
        k = clamp((t - T_QUEMA) / 0.18)
        dibujar_vos(ctx, "mastica", alpha=1 - k, dx=temblor)
        dibujar_vos(ctx, "quema", alpha=k, dx=temblor)
    else:
        dibujar_vos(ctx, pose, dx=0)
    # el ají en la mano
    if pose != "quema":
        hx_, hy_ = vpos(372, 436)
        mx_, my_ = vpos(292, 405)
        ang = math.degrees(math.atan2(my_ - hy_, mx_ - hx_))
        aji(ctx, (hx_ + mx_) / 2 + 10, (hy_ + my_) / 2, 0.6, rot=ang + 180 + 180, mordida=mord)
    else:
        q = clamp((t - T_QUEMA) / 0.7)
        hx_, hy_ = vpos(372, 436)
        aji(ctx, hx_ + 60 * q, hy_ + 900 * q * q, 0.6, rot=-160 + 300 * q, mordida=1.0)
    if t >= T_BITE and t < T_BITE + 0.3:
        mx_, my_ = vpos(300, 400)
        for k in range(8):
            a = k * math.pi / 4
            q = (t - T_BITE) / 0.3
            ctx.arc(mx_ + math.cos(a) * 80 * q, my_ + math.sin(a) * 80 * q, 9 * (1 - q), 0, 2 * math.pi)
            ctx.set_source_rgb(*ROJO)
            ctx.fill()
    if t >= T_QUEMA:
        ex, ey = vpos(90, 292)
        vapor(ctx, ex, ey, t, T_QUEMA, -1)
        ex, ey = vpos(430, 292)
        vapor(ctx, ex, ey, t, T_QUEMA, 1)
        fx, fy = vpos(260, 160)
        sudor(ctx, fx, fy, t, T_QUEMA, 3)
        for ox in (200, 320):
            x0, y0 = vpos(ox, 340)
            q = clamp((t - T_QUEMA - 0.2) / 0.5)
            ctx.move_to(x0, y0)
            ctx.line_to(x0 + (ox - 260) * 0.2, y0 + 160 * q)
            ctx.set_source_rgba(*AZUL_AGUA, 0.85)
            ctx.set_line_width(16)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.stroke()
    titulo_gancho(ctx, t)
    if alarma > 0:
        campana(ctx, 540, 560, 0.72 * pop(t, b(1, "alarma"), 0.3), t, sonando=True)
    tsf = b(1, "sin")
    if t >= tsf:
        sp = pop(t, tsf, 0.3)
        llama(ctx, 860, 780, 0.9 * sp, t)
        prohibido(ctx, 860, 760, 110, sp)
        cartel(ctx, "SIN FUEGO", 860, 920, 52, box=BLANCO, s=pop(t, tsf + 0.1), rot=6)
    return a_rgb(s)


SENS = [(190, 860), (360, 800), (540, 780), (720, 800), (890, 860), (260, 1010), (450, 960), (630, 960),
        (820, 1010), (330, 1170), (540, 1120), (750, 1170)]


def temp_lengua(t):
    tq, t43 = b(2, "quema"), b(2, "43")
    if t < tq:
        return 25.0
    if t < t43:
        return lerp(25, 43, ease((t - tq) / (t43 - tq), "in"))
    return min(48, 43 + (t - t43) * 6)


def sc_lengua(t):
    t0 = S[1]
    if t < t0 + 0.35:
        base = sc_gancho(t0 - 0.01)
        mx, my = vpos(260, 410)
        z = P.zexp(t, t0, 0.35, 1.0, 7.0, "in")
        img = zoom_lineal(base, z, mx, my)
        q = clamp((t - t0 - 0.2) / 0.15)
        if q > 0:
            img = (img.astype(np.float32) * (1 - q) + np.array(hx("#250509")) * 255 * q).astype(np.uint8)
        return img
    s, ctx = lienzo()
    fondo_boca(ctx, t)
    zz = 1 + 0.03 * clamp((t - t0) / 5)
    ctx.save()
    ctx.translate(540, 960)
    ctx.scale(zz, zz)
    ctx.translate(-540, -960)
    lengua(ctx, 660, t)
    temp = temp_lengua(t)
    t43 = b(2, "43")
    alarma = clamp((t - t43) / 0.15) if t >= t43 else 0
    if temp > 30:
        ctx.rectangle(0, 0, 1080, 1920)
        ctx.set_source_rgba(1, 0.4, 0.1, 0.18 * clamp((temp - 30) / 15))
        ctx.fill()
    ts = b(2, "sensores")
    for i, (x, y) in enumerate(SENS):
        sp = pop(t, ts + i * 0.05, 0.3)
        sensor(ctx, x, y, 44, alarma, t + i * 0.13, s=sp)
    ctx.restore()
    cartel(ctx, "TU LENGUA", 330, 240, 70, box=BLANCO, s=pop(t, b(2, "lengua")), rot=-3)
    termometro(ctx, 900, 560, 380, (temp - 20) / 30, s=pop(t, b(2, "quema") - 0.2, 0.35))
    if t >= b(2, "quema") - 0.2:
        txt = f"{int(round(temp))} °C"
        texto(ctx, txt, 760, 420, 76, fill=BLANCO if temp < 43 else hx("#FFD600"), sw=9)
    if t >= t43:
        cartel(ctx, "¡ALARMA!", 540, 560, 74, box=hx("#FF2D2D"), fg=BLANCO, s=pop(t, t43), rot=-4)
    return a_rgb(s)


def sc_llave(t):
    t0 = S[2]
    s, ctx = lienzo()
    fondo_boca(ctx, t)
    lengua(ctx, 1150, t, seed=7)
    cx, cy, R = 600, 780, 210
    te, tj, tl = b(3, "encaja"), b(3, "justo"), b(3, "llave")
    ts = b(3, "sustancia")
    alarma = clamp((t - tj - 0.15) / 0.15) if t >= tj + 0.15 else 0
    cerradura(ctx, cx, cy, R, alarma, t, s=pop(t, t0, 0.35))
    cartel(ctx, "SENSOR DE CALOR", 600, 1035, 50, box=BLANCO, s=pop(t, t0 + 0.15), rot=2,
           alpha=1 - clamp((t - b(3, "llave")) / 0.2))
    # ají que entra
    q = prog(t, b(3, "ají") - 0.2, 0.5, "out")
    aji(ctx, lerp(-250, 190, q), 330, 0.95, rot=-20)
    # llave: sale del ají y entra en la cerradura
    if t >= ts:
        kq = prog(t, ts, te - ts + 0.15, "inout")
        x = lerp(260, cx - 6, kq)
        y = lerp(360, cy + 14, kq)
        rot = lerp(-30, 0, kq)
        if t >= tj:
            rot = lerp(0, 90, prog(t, tj, 0.2, "out"))
        sc_ = lerp(0.3, 0.75, ease(min(1, kq * 1.4), "out"))
        llave(ctx, x, y, sc_, rot=rot)
        if t < te:
            for k in range(10):
                qq = ((t - ts) * 1.8 + k / 10) % 1
                ctx.arc(260 + qq * 120 + 30 * math.sin(k), 360 + 40 * math.sin(k * 2 + qq * 3), 9 * (1 - qq), 0, 2 * math.pi)
                ctx.set_source_rgba(1, 0.55, 0.1, 0.9 * (1 - qq))
                ctx.fill()
    if alarma > 0:
        cartel(ctx, "CLIC", 860, 640, 60, box=hx("#FF2D2D"), fg=BLANCO, s=pop(t, tj + 0.15), rot=10,
               alpha=1 - clamp((t - tl + 0.2) / 0.2))
    if t >= tl:
        cartel(ctx, "LLAVE FALSA", 540, 1170, 84, s=pop(t, tl), rot=-3)
    return a_rgb(s)


def senal(ctx, x0, y0, x1, y1, t, t0, color=hx("#FF4D3A")):
    if t < t0:
        return
    q = clamp((t - t0) / 0.4)
    n = 14
    pts = []
    for i in range(n + 1):
        f = i / n * q
        x = lerp(x0, x1, f)
        y = lerp(y0, y1, f)
        if 0 < i < n:
            dxp, dyp = -(y1 - y0), (x1 - x0)
            L = math.hypot(dxp, dyp)
            off = 22 * (1 if i % 2 else -1)
            x += dxp / L * off
            y += dyp / L * off
        pts.append((x, y))
    for lw, col, a in ((22, color, 0.25), (12, color, 0.6), (6, (1, 1, 0.8), 1.0)):
        for i, (x, y) in enumerate(pts):
            (ctx.move_to if i == 0 else ctx.line_to)(x, y)
        ctx.set_source_rgba(*col, a)
        ctx.set_line_width(lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    for k in range(3):
        f = ((t - t0) * 1.4 + k / 3) % 1
        punto_brillo(ctx, lerp(x0, x1, f * q), lerp(y0, y1, f * q), 10, color, 1.0)


def sc_cerebro(t):
    t0 = S[3]
    s, ctx = lienzo()
    fondo_oscuro(ctx, t)
    tc, tr, tse, tca, tpe, tni = (b(4, "cerebro"), b(4, "recibe"), b(4, "señal"), b(4, "café"), b(4, "pero"),
                                  b(4, "ni"))
    bx, by = 540, 470
    fl = 0.0
    for tt in (tse, tca + 0.5):
        if tt <= t < tt + 0.6:
            fl = max(fl, 1 - (t - tt) / 0.6)
    if fl > 0:
        g = cairo.RadialGradient(bx, by, 50, bx, by, 380)
        g.add_color_stop_rgba(0, 1, 0.2, 0.1, 0.7 * fl)
        g.add_color_stop_rgba(1, 1, 0.2, 0.1, 0)
        ctx.set_source(g)
        ctx.paint()
    P.cerebro(ctx, bx, by, 0.95 * pop(t, tc - 0.1, 0.4) * bump(t, tse, 0.3, 0.1) * bump(t, tca + 0.5, 0.3, 0.1))
    # ají (derecha)
    aji(ctx, 780, 1140, 0.8 * pop(t, t0, 0.35), rot=-30)
    senal(ctx, 760, 1050, 600, 640, t, tr)
    termometro(ctx, 960, 1180, 260, 0.33, s=pop(t, t0 + 0.2, 0.35) * bump(t, tpe, 0.35, 0.15))
    if t >= t0 + 0.2:
        texto(ctx, "36 °C", 960, 860, 60, fill=BLANCO, sw=8)
    # café (izquierda)
    if t >= tca - 0.15:
        taza(ctx, 300, 1150, 0.95 * pop(t, tca - 0.15, 0.35), t)
        senal(ctx, 320, 1000, 480, 640, t, tca + 0.1)
        termometro(ctx, 110, 1180, 260, 0.9, s=pop(t, tca, 0.35))
        texto(ctx, "70 °C", 110, 860, 60, fill=BLANCO, sw=8)
    if t >= tse:
        cartel(ctx, "¡QUEMA!", 830, 300, 70, box=hx("#FF2D2D"), fg=BLANCO, s=pop(t, tse), rot=8)
    if t >= tca + 0.5:
        cartel(ctx, "¡QUEMA!", 250, 300, 70, box=hx("#FF2D2D"), fg=BLANCO, s=pop(t, tca + 0.5), rot=-8)
    if t >= tni:
        sello(ctx, "+0 °C", 830, 1000, True, s=pop(t, tni), rot=-10)
    return a_rgb(s)


def icono_insignia(ctx, x, y, s, tipo, t, t0):
    if s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.arc(0, 0, 130, 0, 2 * math.pi)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.stroke()
    if tipo == "sudor":
        for k in range(3):
            q = ((t - t0) * 1.2 + k / 3) % 1
            gota(ctx, -40 + k * 40, -40 + q * 90, 22, AZUL_AGUA, alpha=1 - q * 0.5)
    elif tipo == "rojo":
        k = clamp((t - t0) / 0.6)
        ctx.arc(0, 0, 80, 0, 2 * math.pi)
        ctx.set_source_rgb(*mezcla(hx("#F8C9A2"), hx("#FF5A4A"), k))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7)
        ctx.stroke()
        for j in range(3):
            q = ((t - t0) * 1.5 + j / 3) % 1
            ctx.move_to(-40 + j * 40, -95 - q * 30)
            ctx.curve_to(-50 + j * 40, -110 - q * 30, -30 + j * 40, -120 - q * 30, -40 + j * 40, -135 - q * 30)
            ctx.set_source_rgba(1, 0.3, 0.2, 1 - q)
            ctx.set_line_width(6)
            ctx.stroke()
    elif tipo == "lagrimas":
        ctx.save()
        ctx.scale(1, 0.6)
        ctx.arc(0, -30, 80, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*BLANCO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7)
        ctx.stroke()
        ctx.arc(0, -18, 30, 0, 2 * math.pi)
        ctx.set_source_rgb(*hx("#6B3E26"))
        ctx.fill()
        q = ((t - t0) * 1.2) % 1
        gota(ctx, 40, 40 + q * 60, 20, AZUL_AGUA, alpha=1 - q * 0.5)
    ctx.restore()


def sc_cuerpo(t):
    t0 = S[4]
    s, ctx = lienzo()
    fondo_oscuro(ctx, t)
    ttr, tro, tll, tcu, tap, tne = (b(5, "transpiras"), b(5, "rojo"), b(5, "lloran"), b(5, "cuerpo"),
                                    b(5, "apagar"), b(5, "no"))
    sube = prog(t, tcu - 0.1, 0.5)
    yb = lerp(720, 330, sube)
    kb = lerp(1.0, 0.72, sube)
    for i, (tt, tipo, nom) in enumerate(((ttr, "sudor", "SUDOR"), (tro, "rojo", "ROJO"), (tll, "lagrimas", "LÁGRIMAS"))):
        x = 200 + i * 340
        sp = pop(t, (t0 if i == 0 else tt - 0.05), 0.35) * kb
        icono_insignia(ctx, x, yb, sp, tipo, t, tt)
        if sp > 0.01:
            cartel(ctx, nom, x, yb + 175 * kb, 46, box=AMARILLO, s=sp)
    if t >= tcu - 0.1:
        a = clamp((t - tcu) / 0.3)
        # techo con rociadores
        rrect(ctx, 80, 640, 920, 36, 16)
        ctx.set_source_rgba(0.6, 0.62, 0.66, a)
        ctx.fill_preserve()
        ctx.set_source_rgba(*INK, a)
        ctx.set_line_width(6)
        ctx.stroke()
        for x in (250, 540, 830):
            rrect(ctx, x - 26, 670, 52, 44, 10)
            ctx.set_source_rgba(0.75, 0.75, 0.8, a)
            ctx.fill_preserve()
            ctx.set_source_rgba(*INK, a)
            ctx.stroke()
            if t >= tap:
                r = rng(x)
                for k in range(26):
                    ph = r.uniform(0, 1)
                    q = ((t - tap) * 1.3 + ph) % 1
                    ang = r.uniform(-0.6, 0.6)
                    px = x + math.sin(ang) * q * 520
                    py = 720 + math.cos(ang) * q * 560
                    gota(ctx, px, py, 10, AZUL_AGUA, alpha=0.9 * (1 - q * 0.4), borde=False)
        # piso y fuego que no está
        ctx.rectangle(0, 1290, 1080, 30)
        ctx.set_source_rgba(0.4, 0.2, 0.2, a)
        ctx.fill()
        ctx.save()
        ctx.translate(540, 1180)
        ctx.scale(1.3, 1.3)
        ctx.move_to(0, 60)
        ctx.curve_to(-70, 50, -70, -20, -20, -60)
        ctx.curve_to(-10, -30, 0, -90, 0, -110)
        ctx.curve_to(30, -70, 70, -40, 62, 10)
        ctx.curve_to(60, 50, 30, 62, 0, 60)
        ctx.restore()
        ctx.set_dash([18, 14])
        ctx.set_source_rgba(1, 1, 1, 0.8 * a)
        ctx.set_line_width(7)
        ctx.stroke()
        ctx.set_dash([])
        texto(ctx, "?", 540, 1150, 110, fill=BLANCO, sw=8, alpha=a)
    if t >= tne:
        cartel(ctx, "NO HAY FUEGO", 540, 960, 80, box=hx("#FF2D2D"), fg=BLANCO, s=pop(t, tne), rot=-4)
    return a_rgb(s)


# gotitas de capsaicina sobre la lengua (y0 = 900)
GOT0 = [(470, 1080), (530, 1040), (600, 1090), (560, 1140), (500, 1150), (440, 1120), (620, 1030)]
GOT1 = [(170, 1150), (320, 1010), (900, 1080), (760, 1250), (360, 1330), (130, 1420), (640, 960)]
SENS2 = [(200, 1080), (340, 1000), (540, 990), (740, 1000), (880, 1080), (260, 1260), (540, 1220), (820, 1260),
         (140, 1430), (400, 1380), (680, 1380), (940, 1430)]


def _gotitas_pos(t):
    """Posición de cada gotita: juntas, después repartidas por el agua, después se van con la leche."""
    tm, te_ = b(6, "tomarla"), b(6, "boca", fin=True)
    q = prog(t, tm, te_ - tm, "inout")
    pos = [(lerp(a[0], c[0], q), lerp(a[1], c[1], q)) for a, c in zip(GOT0, GOT1)]
    tdes = b(7, "despega")
    if t >= tdes:
        k = prog(t, tdes, 0.9, "in")
        pos = [(x + (x - 540) * 0.2 * k, y - 1100 * k) for x, y in pos]
    return pos


def _sensores_estado(t, pos):
    est = []
    tcap = b(6, "capsaicina")
    for sx, sy in SENS2:
        d = min(math.hypot(sx - x, sy - y) for x, y in pos)
        a = clamp((200 - d) / 80)
        if t < tcap:
            a = 0
        est.append(a)
    return est


def sc_agua_leche(t):
    s, ctx = lienzo()
    fondo_boca(ctx, t)
    lengua(ctx, 900, t, seed=9)
    pos = _gotitas_pos(t)
    est = _sensores_estado(t, pos)
    for (x, y), a in zip(SENS2, est):
        sensor(ctx, x, y, 34, a, t + x * 0.01, s=1.0)
    # capa de agua
    tme, tle = b(6, "mezcla"), b(7, "leche")
    agua_a = clamp((t - tme - 0.4) / 0.6) * (1 - clamp((t - tle - 0.8) / 0.8))
    if agua_a > 0:
        ctx.rectangle(60, 900, 960, 1020)
        ctx.set_source_rgba(*AZUL_AGUA, 0.28 * agua_a)
        ctx.fill()
        for k in range(6):
            yy = 960 + k * 150 + 10 * math.sin(t * 3 + k)
            ctx.move_to(80, yy)
            for x in range(80, 1010, 40):
                ctx.line_to(x, yy + 8 * math.sin(x * 0.03 + t * 4 + k))
            ctx.set_source_rgba(1, 1, 1, 0.35 * agua_a)
            ctx.set_line_width(4)
            ctx.stroke()
    # leche: glóbulos de grasa que envuelven las gotitas
    tgr, tat, tdes = b(7, "grasa"), b(7, "atrapa"), b(7, "despega")
    env = clamp((t - tat) / 0.7) if t >= tat else 0.0
    if t >= tgr - 0.6 and env < 0.95:
        r = rng(21)
        for k in range(14):
            x0, y0 = 760 + r.uniform(-80, 80), 1000 + r.uniform(-60, 60)
            tx, ty = pos[k % len(pos)]
            a = r.uniform(0, 2 * math.pi)
            tx += math.cos(a) * 34
            ty += math.sin(a) * 34
            q = env
            x = lerp(x0 + 40 * math.sin(t * 2 + k), tx, q)
            y = lerp(y0 + 30 * math.cos(t * 2 + k), ty, q)
            globulo(ctx, x, y, 22 * pop(t, tgr - 0.6 + k * 0.03, 0.3), alpha=1 - env)
    for x, y in pos:
        gotita_aceite(ctx, x, y, 30, envuelta=env)
    # vasos
    tag, tcap = b(6, "agua"), b(6, "capsaicina")
    if t < tle + 1.2:
        ap = pop(t, tme - 0.5, 0.35) * (1 - clamp((t - tle) / 0.3))
        inc = 110 * prog(t, tme, 0.5)
        if ap > 0.01:
            vaso(ctx, 300, 520, 1.0 * ap, inc, AZUL_AGUA, nivel=lerp(0.8, 0.3, prog(t, tme + 0.4, 2.4)))
            if inc > 60 and t < b(6, "boca", fin=True):
                chorro(ctx, 300 + 120 * math.sin(math.radians(inc)), 520 - 120 * math.cos(math.radians(inc)), 520, 1000, AZUL_AGUA, 34, t)
    if t >= tle - 0.2:
        ap = pop(t, tle - 0.2, 0.35)
        inc = -110 * prog(t, tle + 0.2, 0.5)
        vaso(ctx, 780, 520, 1.0 * ap, inc, (1, 1, 0.98), nivel=lerp(0.8, 0.3, prog(t, tle + 0.6, 2.2)), blanco=True)
        if inc < -60 and t < tat + 0.4:
            chorro(ctx, 780 + 120 * math.sin(math.radians(inc)), 520 - 120 * math.cos(math.radians(inc)), 600, 1000, (1, 1, 0.98), 34, t)
    # etiquetas
    if tcap <= t < b(6, "tomarla"):
        cartel(ctx, "CAPSAICINA", 540, 820, 70, s=pop(t, tcap), rot=-3)
        flecha(ctx, 540, 870, 540, 1000, t, curva=0, w=12)
    if b(6, "boca") <= t < tle:
        sello(ctx, "AGUA", 330, 860, False, s=pop(t, b(6, "boca")))
    if tgr <= t < tdes:
        cartel(ctx, "GRASA", 820, 820, 70, box=BLANCO, s=pop(t, tgr), rot=4)
    if t >= b(7, "lengua"):
        sello(ctx, "LECHE", 760, 860, True, s=pop(t, b(7, "lengua")), rot=6)
    return a_rgb(s)


def sc_pajaro(t):
    t0 = S[7]
    s, ctx = lienzo()
    fondo_exterior(ctx, t)
    tqu, tca, tpe, tll, tno = b(8, "quema"), b(9, "calor"), b(9, "pero"), b(9, "llave"), b(9, "encaja")
    # rama y planta
    ctx.move_to(-20, 1160)
    ctx.curve_to(300, 1140, 600, 1180, 1100, 1120)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(46)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*hx("#8B5A2B"))
    ctx.set_line_width(32)
    ctx.stroke()
    aji(ctx, 760, 1230, 0.7, rot=95)
    aji(ctx, 900, 1215, 0.6, rot=80)
    # pájaro
    salto = 0.0
    ojos = "feliz" if t < tca else "normal"
    if tca <= t < tca + 0.8:
        q = (t - tca) / 0.8
        salto = 140 * math.sin(math.pi * q)
        ojos = "grande"
    picoteo = max(0.0, math.sin(t * 9)) if t < tca - 0.2 else 0.0
    pajaro(ctx, 470, 1010 - salto - 10 * picoteo, 1.15, t, aleteo=0.6 if salto > 10 else 0, pico=picoteo * 0.6,
           ojos=ojos)
    if t < tca - 0.2:
        aji(ctx, 620 + 10 * picoteo, 1035, 0.45, rot=180, mordida=0.3)
    if t >= tqu:
        cartel(ctx, "¡NI LO SIENTE!", 470, 760, 66, box=BLANCO, s=pop(t, tqu), rot=-4,
               alpha=1 - clamp((t - tca + 0.2) / 0.2))
    if tca - 0.15 <= t < tca + 1.0:
        llama(ctx, 330, 1100, 0.8 * pop(t, tca - 0.15, 0.2) * (1 - clamp((t - tca - 0.7) / 0.3)), t)
        if t >= tca + 0.1:
            cartel(ctx, "¡AY!", 640, 760, 80, box=hx("#FF2D2D"), fg=BLANCO, s=pop(t, tca + 0.1), rot=8)
    # lupa: la cerradura del pájaro
    if t >= tpe - 0.1:
        ap = pop(t, tpe - 0.1, 0.35)
        ctx.save()
        ctx.translate(540, 470)
        ctx.scale(ap, ap)
        ctx.arc(0, 0, 300, 0, 2 * math.pi)
        ctx.set_source_rgb(*hx("#2A0A10"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(14)
        ctx.stroke_preserve()
        ctx.set_source_rgb(*BLANCO)
        ctx.set_line_width(6)
        ctx.stroke()
        ctx.restore()
        if ap > 0.3:
            cerradura(ctx, 610, 470, 150, 0.0, t, forma="estrella", s=ap)
            kq = prog(t, tll - 0.1, tno - tll + 0.3, "out")
            reb = 0.0
            if t >= tno + 0.2:
                reb = 160 * ease(clamp((t - tno - 0.2) / 0.4), "out")
            llave(ctx, lerp(300, 540, kq) - reb, 470 + (12 * math.sin(t * 50) if t >= tno + 0.2 and reb < 150 else 0),
                  0.55 * ap, rot=-12 * clamp(reb / 160))
            if t >= tno + 0.2:
                prohibido(ctx, 560, 470, 70, pop(t, tno + 0.2, 0.25))
        cartel(ctx, "SENSOR DE PÁJARO", 540, 140, 50, box=BLANCO, s=ap, rot=-2)
        if t >= tno + 0.2:
            cartel(ctx, "NO ENCAJA", 540, 820, 76, box=hx("#FF2D2D"), fg=BLANCO, s=pop(t, tno + 0.2), rot=3)
    return a_rgb(s)


def sc_viaje(t):
    t0 = S[8]
    ttr, tse, tma, tsa, tex, tle, tcr, tnu = (b(10, "tragan"), b(10, "semillas"), b(10, "masticarlas"),
                                               b(10, "salen"), b(10, "excrementos"), b(10, "lejos"),
                                               b(11, "crecen"), b(11, "nuevos"))
    pan = 900 * prog(t, tma + 0.3, tex - tma, "inout")
    s, ctx = lienzo()
    fondo_exterior(ctx, t, pan=pan)
    # planta original (se va a la izquierda)
    planta_aji(ctx, 230 - pan, 1330, 1.1, 1.0, t)
    vuela = t >= tma + 0.2
    if not vuela:
        bx, by = 470, 1000
    else:
        q = prog(t, tma + 0.2, 1.2, "inout")
        bx, by = lerp(470, 640, q), lerp(1000, 640, q)
        sale = prog(t, tle + 0.1, 1.0, "in")
        bx, by = bx + 700 * sale, by - 250 * sale
    xr = clamp((t - tse) / 0.3) if t >= tse else 0
    if t >= tex + 0.9:
        xr *= 1 - clamp((t - tex - 0.9) / 0.3)
    ale = 0.9 * math.sin(t * 22) if vuela else 0.0
    pico = 0.9 * clamp((t - ttr + 0.2) / 0.2) * (1 - clamp((t - ttr - 0.4) / 0.2)) if t < ttr + 0.8 else 0
    pajaro(ctx, bx, by, 1.05, t, aleteo=ale, pico=pico, ojos="feliz" if not vuela else "normal",
           xray=xr, semillas=7, vuelo=vuela)
    # el ají entra entero en el pico
    if t < ttr + 0.5:
        q = prog(t, ttr - 0.1, 0.5, "in")
        aji(ctx, lerp(720, bx + 110, q), lerp(1010, by - 20, q), 0.55 * (1 - 0.6 * q), rot=180)
    if t >= tma:
        cartel(ctx, "SIN MASTICAR", 300, 420, 62, box=BLANCO, s=pop(t, tma), rot=-5, alpha=1 - clamp((t - tex) / 0.2))
    if t >= tse and t < tex:
        cartel(ctx, "SEMILLAS ENTERAS", 760, 300, 58, box=AMARILLO, s=pop(t, tse + 0.2), rot=4)
    # el excremento cae
    caida0 = tex - 0.1
    gx = 640
    if t >= caida0:
        q = clamp((t - caida0) / 0.55)
        gy = lerp(by + 110, 1270, q * q)
        ctx.save()
        ctx.translate(gx, gy)
        sq = 1 + 0.4 * clamp((t - caida0 - 0.55) / 0.1) * (1 - clamp((t - caida0 - 0.65) / 0.2))
        ctx.scale(sq, 1 / sq)
        for dx, dy, r in ((0, 0, 40), (-26, 14, 28), (26, 14, 28), (0, -24, 26)):
            ctx.arc(dx, dy, r, 0, 2 * math.pi)
            ctx.new_sub_path()
        ctx.set_source_rgb(*hx("#F2F0E6"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5)
        ctx.stroke()
        for dx, dy in ((-14, 4), (12, 10), (2, -14)):
            semilla(ctx, dx, dy, 0.55)
        ctx.restore()
    if t >= tle:
        ap = pop(t, tle, 0.3)
        flecha(ctx, 520, 1130, 110, 1130, t, alpha=clamp(ap) * (1 - clamp((t - tcr) / 0.3)), curva=0, w=14, bote=False)
        cartel(ctx, "LEJOS DE LA PLANTA", 330, 1040, 50, box=BLANCO, s=ap, alpha=1 - clamp((t - tcr) / 0.2))
    if t >= tcr:
        planta_aji(ctx, gx, 1300, 1.2, clamp((t - tcr) / 1.1), t)
    if t >= tnu:
        cartel(ctx, "¡AJÍES NUEVOS!", 540, 420, 76, s=pop(t, tnu), rot=-3)
    return a_rgb(s)


def sc_raton(t):
    t0 = S[9]
    tma, tde = b(12, "mastica"), b(12, "destruye")
    s, ctx = lienzo()
    fondo_exterior(ctx, t, pan=900)
    planta_aji(ctx, 900, 1330, 1.0, 1.0, t)
    q = prog(t, t0, 0.5, "out")
    rojo = clamp((t - tma - 0.6) / 0.5)
    raton(ctx, lerp(-200, 470, q), 1050, 1.2, t, mastica=(tma <= t < tde + 0.3), rojo=rojo)
    if t < tma + 0.15:
        aji(ctx, lerp(-200, 470, q) + 210, 1060, 0.5, rot=180)
    if t >= tma:
        r = rng(5)
        for k in range(16):
            ph = r.uniform(0, 0.8)
            if t < tma + ph:
                continue
            qq = clamp((t - tma - ph) / 0.8)
            ang = r.uniform(-1.2, 0.6)
            x = 640 + math.cos(ang) * 320 * qq
            y = 1040 + math.sin(ang) * 260 * qq + 400 * qq * qq
            semilla(ctx, x, y, 1.0, rot=k, rota=clamp(qq * 3))
    if rojo > 0:
        ex, ey = 470 + 1.2 * 40, 1050 - 1.2 * 120
        vapor(ctx, ex - 60, ey, t, tma + 0.6, -1)
        vapor(ctx, ex + 90, ey, t, tma + 0.6, 1)
    if t >= tde:
        sello(ctx, "SEMILLAS\nDESTRUIDAS", 540, 560, False, s=pop(t, tde), rot=-6)
    return a_rgb(s)


def sc_final(t):
    t0 = S[10]
    tci, tex, tesp, tani, tco = (b(13, "científicos"), b(13, "existe"), b(13, "espantar"), b(13, "animales"),
                                 b(14, "Como"))
    s, ctx = lienzo()
    fondo_oscuro(ctx, t)
    aura = clamp((t - tex) / 0.5)
    if aura > 0:
        pul = 0.5 + 0.5 * math.sin(t * 6)
        g = cairo.RadialGradient(540, 900, 80, 540, 900, 520)
        g.add_color_stop_rgba(0, 1, 0.25, 0.1, (0.55 + 0.25 * pul) * aura)
        g.add_color_stop_rgba(1, 1, 0.25, 0.1, 0)
        ctx.set_source(g)
        ctx.paint()
    planta_aji(ctx, 540, 1250, 1.45 * pop(t, t0, 0.4), 1.0, t)
    if t >= tex:
        cartel(ctx, "UNA DEFENSA", 540, 300, 90, box=hx("#FF2D2D"), fg=BLANCO, s=pop(t, tex), rot=-3,
               alpha=1 - clamp((t - b(14, "Como") + 0.3) / 0.2))
    # el ratón se acerca y sale despedido
    if t >= t0:
        q = prog(t, t0 + 0.2, tesp - t0 - 0.2, "out")
        hu = prog(t, tesp, 0.6, "in")
        rx = lerp(-250, 220, q) - 700 * hu
        raton(ctx, rx, 1190, 0.7, t, rojo=clamp((t - tesp) / 0.2))
        if tesp <= t < tesp + 0.8:
            for k in range(3):
                qq = ((t - tesp) * 2 + k / 3) % 1
                ctx.arc(420, 1100, 60 + qq * 220, math.pi * 0.75, math.pi * 1.25)
                ctx.set_source_rgba(1, 0.4, 0.1, 1 - qq)
                ctx.set_line_width(12)
                ctx.stroke()
    # el pájaro llega tranquilo
    if t >= tesp:
        q = prog(t, tesp, 1.0, "out")
        pajaro(ctx, lerp(1250, 760, q), lerp(500, 820, q), 0.6, t, aleteo=0.9 * math.sin(t * 22) if q < 0.95 else 0,
               ojos="feliz", vuelo=q < 0.95)
    if t >= tani:
        cartel(ctx, "LOS QUE MASTICAN", 300, 1420, 54, box=BLANCO, s=pop(t, tani), rot=-4,
               alpha=1 - clamp((t - tco) / 0.15))
    # la boca: "como tú"
    if t >= tco - 0.25:
        q = prog(t, tco - 0.25, 0.35, "out")
        cierre = clamp((t - b(14, "tú")) / 0.18)
        ctx.rectangle(0, 0, 1080, 1920)
        ctx.set_source_rgba(0, 0, 0, 0.45 * q)
        ctx.fill()
        aji(ctx, 540, 960, 1.3 * q, rot=-90)
        boca_grande(ctx, 540, 960, lerp(0.4, 1.35, q), cierre, t)
        if cierre > 0.9:
            campana(ctx, 540, 380, 0.7 * pop(t, b(14, "tú") + 0.18, 0.25), t, sonando=True)
            fl = 1 - clamp((t - b(14, "tú") - 0.18) / 0.3)
            ctx.rectangle(0, 0, 1080, 1920)
            ctx.set_source_rgba(1, 0.1, 0.05, 0.35 * fl)
            ctx.fill()
    return a_rgb(s)


ESCENAS = [sc_gancho, sc_lengua, sc_llave, sc_cerebro, sc_cuerpo, sc_agua_leche, sc_agua_leche, sc_pajaro,
           sc_viaje, sc_raton, sc_final]

CAPS = motor.Captions(WORDS, {"size": 76, "y": 1470, "max_palabras": 3, "max_letras": 18})


def cuadro(t):
    i = escena_de(t)
    try:
        img = ESCENAS[i](t)
    except Exception as e:
        raise RuntimeError(f"falló {ESCENAS[i].__name__} en t={t:.3f}: {e}") from e
    if i > 0 and t - S[i] < 0.08 and i not in (1, 6):
        k = 1 - (t - S[i]) / 0.08
        img = (img.astype(np.float32) * (1 - 0.35 * k) + 255 * 0.35 * k).astype(np.uint8)
    im = Image.fromarray(img)
    CAPS.draw(im, t)
    return im


# ------------------------------------------------------------------ sonido
def _env(n, a=0.005, r=0.05):
    e = np.ones(n, np.float32)
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def s_alarma(d=1.6):
    n = int(d * SR)
    t = np.arange(n) / SR
    f = np.where((t * 8).astype(int) % 2 == 0, 880, 1175)
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 24 * t)))
    return (sig * 0.35 * _env(n, 0.01, 0.2)).astype(np.float32)


def s_crunch(d=0.5, seed=1):
    n = int(d * SR)
    r = np.random.default_rng(seed)
    out = np.zeros(n, np.float32)
    for k in range(int(d * 18)):
        i = int(k / (d * 18) * n) + r.integers(0, 600)
        L = r.integers(600, 1800)
        if i + L >= n:
            break
        out[i:i + L] += r.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 5)) * r.uniform(0.5, 1)
    out = np.diff(out, prepend=0)
    return (out / (np.abs(out).max() + 1e-6) * 0.7).astype(np.float32)


def s_vertido(d=1.4):
    n = int(d * SR)
    t = np.arange(n) / SR
    x = np.random.default_rng(2).standard_normal(n).astype(np.float32)
    x = np.convolve(x, np.ones(12) / 12, mode="same")
    mod = 0.6 + 0.4 * np.sin(2 * np.pi * (7 + 3 * np.sin(2 * np.pi * 0.7 * t)) * t)
    return (x * mod * 0.9 * _env(n, 0.1, 0.3)).astype(np.float32)


def s_trago():
    t = np.arange(int(0.22 * SR)) / SR
    f = 320 * np.exp(-t * 9) + 90
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10) * 0.8).astype(np.float32)


def s_aleteo(d=1.2):
    n = int(d * SR)
    t = np.arange(n) / SR
    x = np.random.default_rng(4).standard_normal(n).astype(np.float32)
    x = np.convolve(x, np.ones(30) / 30, mode="same")
    env = np.maximum(0, np.sin(2 * np.pi * 11 * t)) ** 3
    return (x * env * 2.2 * _env(n, 0.05, 0.2)).astype(np.float32)


def s_plop():
    t = np.arange(int(0.25 * SR)) / SR
    f = 700 * np.exp(-t * 18) + 160
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * 0.8).astype(np.float32)


def s_brote(d=1.0):
    t = np.arange(int(d * SR)) / SR
    f = 400 + 900 * (t / d)
    sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-((t - d * 0.6) ** 2) / 0.08) * 0.4
    for k, ft in enumerate((1568, 2093, 2637)):
        tt = t - d * (0.55 + k * 0.12)
        sig += np.where(tt > 0, np.sin(2 * np.pi * ft * tt) * np.exp(-tt * 12) * 0.35, 0)
    return sig.astype(np.float32)


def s_siseo(d=1.5):
    n = int(d * SR)
    x = np.random.default_rng(6).standard_normal(n).astype(np.float32)
    x = np.diff(x, prepend=0)
    return (x * 0.25 * _env(n, 0.15, 0.4)).astype(np.float32)


def s_clunk():
    t = np.arange(int(0.35 * SR)) / SR
    x = np.random.default_rng(8).standard_normal(len(t)).astype(np.float32) * np.exp(-t * 40) * 0.5
    tone = np.sin(2 * np.pi * 170 * t) * np.exp(-t * 12) * 0.7 + np.sin(2 * np.pi * 410 * t) * np.exp(-t * 20) * 0.3
    return (x + tone).astype(np.float32)


def s_clic():
    out = np.zeros(int(0.12 * SR), np.float32)
    for i0, f in ((0, 3200), (int(0.05 * SR), 2600)):
        t = np.arange(int(0.03 * SR)) / SR
        out[i0:i0 + len(t)] += np.sin(2 * np.pi * f * t) * np.exp(-t * 200) * 0.8
    return out


def snd(kind, **kw):
    f = {"alarma": s_alarma, "crunch": s_crunch, "vertido": s_vertido, "trago": s_trago, "aleteo": s_aleteo,
         "plop": s_plop, "brote": s_brote, "siseo": s_siseo, "clunk": s_clunk, "clic": s_clic}.get(kind)
    if f:
        return f(**kw)
    return P.sonido(kind, **kw)


def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    ev(T_BITE - 0.05, "crunch", 0.9, d=0.35)
    ev(T_QUEMA, "boing", 0.7)
    ev(T_QUEMA + 0.1, "siseo", 0.5, d=1.2)
    ev(b(1, "alarma"), "alarma", 0.8, d=S[1] - b(1, "alarma") + 0.1)
    ev(b(1, "sin"), "pop", 0.8)
    ev(S[1], "zoom", 0.9)
    ev(b(2, "lengua"), "pop", 0.6)
    for i in range(len(SENS)):
        ev(b(2, "sensores") + i * 0.05, "tick", 0.25, f=1400 + i * 60, d=0.05)
    ev(b(2, "quema") - 0.2, "subida", 0.6, d=b(2, "43") - b(2, "quema") + 0.2)
    ev(b(2, "43"), "alarma", 0.7, d=0.8)
    ev(S[2], "whoosh", 0.8)
    ev(b(3, "ají") - 0.2, "whoosh_suave", 0.7)
    ev(b(3, "sustancia"), "subida", 0.4, d=0.6)
    ev(b(3, "justo") + 0.1, "clic", 1.0)
    ev(b(3, "justo") + 0.2, "alarma", 0.6, d=0.9)
    ev(b(3, "llave"), "pop", 0.8)
    ev(S[3], "whoosh", 0.8)
    ev(b(4, "recibe"), "chispa", 0.5, d=0.6, seed=2)
    ev(b(4, "señal"), "pop", 0.7)
    ev(b(4, "café") - 0.15, "pop", 0.6)
    ev(b(4, "café") + 0.1, "chispa", 0.5, d=0.6, seed=3)
    ev(b(4, "café") + 0.5, "pop", 0.7)
    ev(b(4, "ni"), "ding", 0.8)
    ev(S[4], "whoosh", 0.8)
    for w_ in ("transpiras", "rojo", "lloran"):
        ev(b(5, w_) - 0.05, "pop", 0.7)
    ev(b(5, "apagar"), "siseo", 0.7, d=S[5] - b(5, "apagar"))
    ev(b(5, "no"), "boing", 0.6)
    ev(S[5], "whoosh", 0.8)
    ev(b(6, "capsaicina"), "pop", 0.7)
    ev(b(6, "mezcla"), "vertido", 0.8, d=2.4)
    ev(b(6, "tomarla"), "siseo", 0.4, d=1.6)
    ev(b(6, "boca"), "boing", 0.6)
    ev(b(7, "leche") - 0.2, "pop", 0.6)
    ev(b(7, "leche") + 0.3, "vertido", 0.7, d=1.6)
    ev(b(7, "grasa"), "pop", 0.6)
    ev(b(7, "despega"), "whoosh_suave", 0.8)
    ev(b(7, "lengua"), "ding", 0.8)
    ev(S[7], "whoosh", 0.8)
    ev(b(8, "quema"), "pop", 0.6)
    ev(b(9, "calor"), "boing", 0.8)
    ev(b(9, "pero") - 0.1, "zoom", 0.6)
    ev(b(9, "encaja") + 0.2, "clunk", 1.0)
    ev(b(10, "tragan"), "trago", 1.0)
    ev(b(10, "semillas"), "pop", 0.6)
    ev(b(10, "masticarlas") + 0.2, "aleteo", 0.8, d=1.6)
    ev(b(10, "excrementos") + 0.45, "plop", 1.0)
    ev(b(10, "lejos"), "whoosh_suave", 0.6)
    ev(b(11, "crecen"), "brote", 0.8, d=1.1)
    ev(b(11, "nuevos"), "pop", 0.7)
    ev(S[9], "whoosh", 0.7)
    ev(b(12, "mastica"), "crunch", 1.0, d=1.4, seed=3)
    ev(b(12, "destruye"), "boing", 0.7)
    ev(S[10], "whoosh", 0.8)
    ev(b(13, "existe"), "pop", 0.8)
    ev(b(13, "espantar"), "golpe", 0.8)
    ev(b(13, "espantar") + 0.1, "aleteo", 0.5, d=0.9)
    ev(b(14, "Como") - 0.25, "whoosh", 0.9)
    ev(b(14, "tú") + 0.18, "crunch", 1.0, d=0.3, seed=9)
    ev(b(14, "tú") + 0.18, "alarma", 0.8, d=COLA)
    return E


def pista_efectos():
    n = int((TOTAL + 2) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = snd(k, **kw) * v
        i0 = int(t * SR)
        i1 = min(n, i0 + len(x))
        if 0 <= i0 < n:
            mix[i0:i1] += x[:i1 - i0]
    mix *= 0.55 / (np.abs(mix).max() or 1)
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
                    "-filter_complex", "[1:a][2:a]amix=inputs=2:normalize=0:duration=longest,"
                    "alimiter=limit=0.89:level=false[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", salida],
                   check=True)
    for f in os.listdir(tmp):
        os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fotos")
    ap.add_argument("--dir", default=os.path.join(AQUI, "fotos"))
    ap.add_argument("--salida", default=os.path.join(ROOT, "salidas", "el_picante.mp4"))
    ap.add_argument("--hilos", type=int, default=2)
    a = ap.parse_args()
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
