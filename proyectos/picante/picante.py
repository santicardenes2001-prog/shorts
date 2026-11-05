"""Short "El picante no es un sabor" — animación procedural; Vos solo en la apertura.

Estilo de los últimos videos: fondo azul oscuro con puntos, cámara que entra y sale de las escenas,
objetos con cara (la capsaicina es una llave falsa) y la alarma solo al principio y al final.

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
from pantalla import (AMARILLO, BLANCO, INK, a_rgb, bump, cartel, clamp, ease, flecha, hx, lerp, lienzo,  # noqa: E402
                      pop, prog, punto_brillo, rng, rrect, texto)

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
        ctx.set_source_rgba(0.82, 0.94, 1.0, 0.75 * xray)
        ctx.fill()
        ctx.save()
        ctx.translate(0, 25)
        ctx.scale(1, 0.75)
        ctx.arc(0, 0, 78, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_dash([10, 8])
        ctx.set_source_rgba(0.2, 0.45, 0.7, 0.8 * xray)
        ctx.set_line_width(4)
        ctx.stroke()
        ctx.set_dash([])
        aji(ctx, -8, 28, 0.42, rot=-15, alpha=0.55 * xray)
        rr = rng(11)
        for k in range(semillas):
            px, py = rr.uniform(-50, 50), rr.uniform(0, 60)
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


# ------------------------------------------------------------------ cámara y fondo azul (como los últimos videos)
def camara(ctx, fx, fy, z, sx=540, sy=960):
    ctx.translate(sx, sy)
    ctx.scale(z, z)
    ctx.translate(-fx, -fy)


def capa(ctx, fn, t, cam=None, alpha=1.0, dx=0.0, dy=0.0):
    """Dibuja una escena completa con cámara y transparencia."""
    if alpha <= 0.003:
        return
    ctx.save()
    grupo = alpha < 0.997
    if grupo:
        ctx.push_group()
    ctx.translate(dx, dy)
    if cam:
        camara(ctx, *cam)
    fn(ctx, t)
    if grupo:
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)
    ctx.restore()


def zoom_entre(ctx, q, ext, t_ext, f, dentro, t_dentro, g, Z, a0=0.3, a1=0.75):
    """q = 0: 'ext' a pantalla completa; q = 1: 'dentro' a pantalla completa.
    'dentro' vive en el punto f de 'ext' a escala 1/Z (g es su punto que coincide con f)."""
    k = ease(q, "inout")
    sx, sy = lerp(f[0], g[0], k), lerp(f[1], g[1], k)
    z = Z ** k
    capa(ctx, ext, t_ext, cam=(f[0], f[1], z, sx, sy))
    capa(ctx, dentro, t_dentro, cam=(g[0], g[1], z / Z, sx, sy), alpha=clamp((k - a0) / (a1 - a0)))


def _elipse_suave(ctx, x, y, rx, ry, col, a):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
    g.add_color_stop_rgba(0, *col, a)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def fondo_azul(ctx, t, calor=0.0, cx=540, cy=900, rc=760):
    P.fondo(ctx, t)
    _elipse_suave(ctx, 160, 420, 520, 320, hx("#6A5BE0"), 0.16)
    _elipse_suave(ctx, 960, 1380, 540, 360, hx("#2F9BE0"), 0.13)
    _elipse_suave(ctx, 700, 760, 300, 200, hx("#C25BE0"), 0.08)
    if calor > 0:
        g = cairo.RadialGradient(cx, cy, 30, cx, cy, rc)
        g.add_color_stop_rgba(0, 1, 0.45, 0.12, 0.45 * calor)
        g.add_color_stop_rgba(0.5, 1, 0.28, 0.08, 0.17 * calor)
        g.add_color_stop_rgba(1, 1, 0.28, 0.08, 0)
        ctx.set_source(g)
        ctx.paint()


def vineta_roja(ctx, k):
    if k <= 0.01:
        return
    g = cairo.RadialGradient(540, 960, 380, 540, 960, 1250)
    g.add_color_stop_rgba(0, 1, 0, 0, 0)
    g.add_color_stop_rgba(1, 1, 0.05, 0.02, 0.55 * k)
    ctx.set_source(g)
    ctx.paint()


# ------------------------------------------------------------------ caritas (mismo trazo que el video del agua)
def _q(ctx, x0, y0, qx, qy, x1, y1):
    ctx.move_to(x0, y0)
    ctx.curve_to(x0 + 2 / 3 * (qx - x0), y0 + 2 / 3 * (qy - y0), x1 + 2 / 3 * (qx - x1), y1 + 2 / 3 * (qy - y1), x1, y1)


def _trazo(ctx, w, col=INK, a=1.0):
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgba(*col, a)
    ctx.set_line_width(w)
    ctx.stroke()


def ojo(ctx, x, y, r, kind="open", look=(0, 0)):
    if kind in ("open", "wide"):
        rx, ry, pr = (24 * r, 28 * r, 11 * r) if kind == "open" else (30 * r, 34 * r, 8 * r)
        ctx.save()
        ctx.translate(x, y)
        ctx.scale(rx, ry)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*BLANCO)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5 * r)
        ctx.stroke()
        px, py = x + look[0] * 9 * r, y + look[1] * 9 * r + 3 * r
        ctx.arc(px, py, pr, 0, 2 * math.pi)
        ctx.set_source_rgb(*INK)
        ctx.fill()
        ctx.arc(px - pr * 0.35, py - pr * 0.4, max(2.5, pr * 0.32), 0, 2 * math.pi)
        ctx.set_source_rgb(*BLANCO)
        ctx.fill()
    elif kind == "happy":
        _q(ctx, x - 20 * r, y + 8 * r, x, y - 16 * r, x + 20 * r, y + 8 * r)
        _trazo(ctx, 7 * r)
    elif kind == "closed":
        _q(ctx, x - 20 * r, y, x, y + 10 * r, x + 20 * r, y)
        _trazo(ctx, 7 * r)
    elif kind == "dot":
        ctx.arc(x, y, 9 * r, 0, 2 * math.pi)
        ctx.set_source_rgb(*INK)
        ctx.fill()


def boquita(ctx, x, y, kind, r):
    if kind == "smile":
        _q(ctx, x - 26 * r, y, x, y + 24 * r, x + 26 * r, y)
        _trazo(ctx, 7 * r)
    elif kind in ("grin", "o"):
        if kind == "grin":
            ctx.move_to(x - 32 * r, y - 4 * r)
            ctx.curve_to(x - 14 * r, y + 34 * r, x + 14 * r, y + 34 * r, x + 32 * r, y - 4 * r)
            ctx.close_path()
        else:
            ctx.save()
            ctx.translate(x, y + 6 * r)
            ctx.scale(13 * r, 17 * r)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
        path = ctx.copy_path()
        ctx.set_source_rgb(*hx(kit.P["boca"]))
        ctx.fill()
        ctx.save()
        ctx.append_path(path)
        ctx.clip()
        ctx.save()
        ctx.translate(x, y + (18 if kind == "grin" else 20) * r)
        ctx.scale(14 * r, 7 * r)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*hx(kit.P["lengua"]))
        ctx.fill()
        ctx.restore()
        ctx.append_path(path)
        _trazo(ctx, 6 * r)
    elif kind == "flat":
        ctx.move_to(x - 20 * r, y + 6 * r)
        ctx.line_to(x + 20 * r, y + 6 * r)
        _trazo(ctx, 7 * r)
    elif kind == "wavy":
        ctx.move_to(x - 28 * r, y + 6 * r)
        ctx.curve_to(x - 18 * r, y - 4 * r, x - 10 * r, y - 4 * r, x, y + 6 * r)
        ctx.curve_to(x + 10 * r, y + 16 * r, x + 18 * r, y + 16 * r, x + 28 * r, y + 6 * r)
        _trazo(ctx, 7 * r)


def cejas(ctx, x, y, sep, kind, r):
    a, c = x - sep / 2, x + sep / 2
    if kind == "worried":
        ctx.move_to(a - 20 * r, y + 4 * r)
        ctx.line_to(a + 18 * r, y - 8 * r)
        ctx.move_to(c - 18 * r, y - 8 * r)
        ctx.line_to(c + 20 * r, y + 4 * r)
    elif kind == "angry":
        ctx.move_to(a - 20 * r, y - 8 * r)
        ctx.line_to(a + 18 * r, y + 4 * r)
        ctx.move_to(c - 18 * r, y + 4 * r)
        ctx.line_to(c + 20 * r, y - 8 * r)
    elif kind == "up":
        _q(ctx, a - 18 * r, y, a, y - 14 * r, a + 18 * r, y)
        _q(ctx, c - 18 * r, y, c, y - 14 * r, c + 18 * r, y)
    else:
        return
    _trazo(ctx, 7 * r)


def carita(ctx, x, y, sep, r, ojos="open", boca="smile", ceja=None, look=(0, 0), rubor=False, dy_boca=None):
    if rubor:
        for sx in (-1, 1):
            ctx.save()
            ctx.translate(x + sx * sep * 0.72, y + 28 * r)
            ctx.scale(18 * r, 10 * r)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(*hx("#FF8FA8"), 0.6)
            ctx.fill()
    ojo(ctx, x - sep / 2, y, r, ojos, look)
    ojo(ctx, x + sep / 2, y, r, ojos, look)
    if ceja:
        cejas(ctx, x, y - (40 if ojos == "wide" else 34) * r, sep, ceja, r)
    boquita(ctx, x, y + (dy_boca if dy_boca is not None else 36 * r), boca, r)


# ------------------------------------------------------------------ la capsaicina: una llave falsa con cara
CARAS_LLAVE = {
    "picara": dict(ojos="open", boca="grin", ceja="angry", look=(0.5, 0.2)),
    "feliz": dict(ojos="happy", boca="grin"),
    "susto": dict(ojos="wide", boca="o", ceja="worried"),
    "tranqui": dict(ojos="open", boca="smile"),
    "enojo": dict(ojos="open", boca="wavy", ceja="angry"),
}


def llavecita(ctx, x, y, s, rot=0.0, cara="picara", giro=1.0, alpha=1.0, col=NARANJA):
    """(x, y) = punta de la llave. Con rot = 0 apunta hacia abajo (la cabeza queda arriba)."""
    if s <= 0.004 or alpha <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(rot))
    ctx.scale(s, s)
    grupo = alpha < 0.99
    if grupo:
        ctx.push_group()
    lw = max(8.0, 2.4 / s)
    gx = max(0.07, abs(giro))
    ctx.save()
    ctx.scale(gx, 1)
    # dientes de la llave
    ctx.move_to(12, -36)
    ctx.line_to(58, -36)
    ctx.line_to(58, -64)
    ctx.line_to(38, -72)
    ctx.line_to(38, -90)
    ctx.line_to(58, -98)
    ctx.line_to(58, -126)
    ctx.line_to(12, -126)
    ctx.close_path()
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(lw)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    # vástago
    rrect(ctx, -18, -270, 36, 270, 16)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.move_to(-6, -250)
    ctx.line_to(-6, -30)
    ctx.set_source_rgba(1, 1, 1, 0.35)
    ctx.set_line_width(8)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    # cabeza
    g = cairo.RadialGradient(-26, -362, 10, 0, -335, 82)
    g.add_color_stop_rgb(0, *mezcla(col, (1, 1, 1), 0.35))
    g.add_color_stop_rgb(1, *mezcla(col, (0.6, 0.15, 0), 0.25))
    ctx.arc(0, -335, 80, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(lw)
    ctx.stroke()
    ctx.restore()
    if giro > 0.3:
        ctx.save()
        ctx.translate(0, -335)
        ctx.scale(giro, 1)
        carita(ctx, 0, -14, 58, 1.2, **CARAS_LLAVE[cara])
        ctx.restore()
    if grupo:
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(alpha)
    ctx.restore()


# ------------------------------------------------------------------ la boca de frente
PIEL_C, PIEL_O = hx("#F8C9A2"), hx("#E9A982")
LAB_SUP, LAB_SUP2 = hx("#E26A82"), hx("#BC4560")
LAB_INF, LAB_INF2 = hx("#F4889B"), hx("#D05570")
ENCIA, ENCIA2 = hx("#F590A3"), hx("#D9677F")
DIENTE, DIENTE2 = hx("#FFFDF6"), hx("#E6DDCC")
LENG_A, LENG_B, LENG_C = hx("#FFA2B4"), hx("#F27891"), hx("#C94A69")
ROJO_AL = hx("#FF3B2F")
CIAN = P.CIAN
BX = 540
LAB_UP, LAB_DN, LAB_LADO = 64, 86, 62
# sensores sobre la lengua: (dx, dy) desde el punto más alto de la lengua
REC = [(-125, 72), (0, 58), (125, 72), (-255, 152), (-128, 142), (0, 138), (128, 142), (255, 152),
       (-190, 228), (-64, 220), (64, 220), (190, 228)]
DSUP = [(44, 84, 104, False), (126, 72, 92, False), (199, 64, 94, True), (266, 60, 76, False), (329, 58, 66, False)]
DINF = [(30, 56, 56, False), (88, 54, 56, False), (145, 52, 62, True)]


class Boca:
    def __init__(self, a=1.0, top=560):
        self.a = clamp(a)
        self.top = top
        self.J = lerp(196, 770, self.a)
        self.hw = 400
        self.yc = top + 0.27 * self.J + 8
        self.bot = top + self.J
        self.ty = top + 0.47 * self.J
        self.tys = top + 0.76 * self.J

    @staticmethod
    def _u(x, hw):
        return min(1.0, abs(x - BX) / hw)

    def top_in(self, x):
        return self.top + (self.yc - self.top) * self._u(x, self.hw) ** 2.6

    def bot_in(self, x):
        return self.yc + (self.bot - self.yc) * (1 - self._u(x, self.hw) ** 2.2) ** 0.55

    def top_out(self, x):
        hwo = self.hw + LAB_LADO
        u = self._u(x, hwo)
        y0 = self.top - LAB_UP
        d = abs(x - BX)
        arco = 20 * math.exp(-(d / 42) ** 2) - 9 * math.exp(-((d - 88) / 46) ** 2)
        return y0 + (self.yc - y0) * u ** 2.2 + arco * (1 - u)

    def bot_out(self, x):
        u = self._u(x, self.hw + LAB_LADO)
        return self.yc + (self.bot + LAB_DN - self.yc) * (1 - u ** 2.0) ** 0.55

    def lengua_y(self, x):
        u = min(1.25, abs(x - BX) / self.hw)
        return self.ty + (self.tys - self.ty) * u ** 1.8

    @staticmethod
    def xs(hw, n=110):
        return [BX + hw * math.sin(-math.pi / 2 + math.pi * i / n) for i in range(n + 1)]

    def _contorno(self, ctx, fa, fb, hw):
        xs = self.xs(hw)
        ctx.move_to(xs[0], fa(xs[0]))
        for x in xs[1:]:
            ctx.line_to(x, fa(x))
        for x in reversed(xs[1:-1]):
            ctx.line_to(x, fb(x))
        ctx.close_path()

    def camino_in(self, ctx):
        self._contorno(ctx, self.top_in, self.bot_in, self.hw)

    def camino_out(self, ctx):
        self._contorno(ctx, self.top_out, self.bot_out, self.hw + LAB_LADO)

    def rec(self, i):
        dx, dy = REC[i]
        return BX + dx, self.ty + dy


def _pend(f, x):
    return (f(x + 2) - f(x - 2)) / 4


def piel_cara(ctx):
    g = cairo.RadialGradient(540, 980, 120, 540, 980, 1300)
    g.add_color_stop_rgb(0, *PIEL_C)
    g.add_color_stop_rgb(1, *PIEL_O)
    ctx.set_source(g)
    ctx.paint()
    for x in (70, 1010):
        _elipse_suave(ctx, x, 840, 200, 150, hx("#FF8FA8"), 0.5)
    _elipse_suave(ctx, 540, 1620, 380, 120, PIEL_O, 0.7)
    # nariz
    _elipse_suave(ctx, 540, 350, 170, 95, PIEL_O, 0.8)
    ctx.move_to(450, 296)
    ctx.curve_to(432, 352, 468, 394, 506, 382)
    ctx.curve_to(522, 402, 558, 402, 574, 382)
    ctx.curve_to(612, 394, 648, 352, 630, 296)
    _trazo(ctx, 7)
    for sg in (-1, 1):
        ctx.save()
        ctx.translate(540 + sg * 37, 362)
        ctx.rotate(sg * 0.35)
        ctx.scale(19, 10)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*hx("#9C5644"))
        ctx.fill()
        # surco bajo la nariz
        ctx.move_to(540 + sg * 18, 412)
        ctx.line_to(540 + sg * 24, 470)
        _trazo(ctx, 7, PIEL_O, 0.9)


def cavidad(ctx, bo):
    top, J, hw = bo.top, bo.J, bo.hw
    g = cairo.LinearGradient(0, top, 0, bo.bot)
    g.add_color_stop_rgb(0, *hx("#CC5470"))
    g.add_color_stop_rgb(0.4, *hx("#9C2E48"))
    g.add_color_stop_rgb(1, *hx("#5A0F20"))
    ctx.set_source(g)
    ctx.paint()
    # el arco del fondo y la garganta
    aw = 0.36 * hw
    ya = top + 0.15 * J
    yb = bo.ty + 80
    ctx.move_to(BX - aw, yb)
    ctx.curve_to(BX - aw, ya + 0.10 * J, BX - aw * 0.72, ya, BX, ya)
    ctx.curve_to(BX + aw * 0.72, ya, BX + aw, ya + 0.10 * J, BX + aw, yb)
    ctx.close_path()
    arco = ctx.copy_path()
    yg = top + 0.36 * J
    rg = cairo.RadialGradient(BX, yg, 10, BX, yg, aw * 1.15)
    rg.add_color_stop_rgb(0, *hx("#0C0105"))
    rg.add_color_stop_rgb(0.65, *hx("#260410"))
    rg.add_color_stop_rgb(1, *hx("#4E0C1E"))
    ctx.set_source(rg)
    ctx.fill()
    ctx.append_path(arco)
    ctx.set_source_rgba(*hx("#741830"), 0.9)
    ctx.set_line_width(30)
    ctx.stroke()
    ctx.append_path(arco)
    ctx.set_source_rgba(*hx("#E4728A"), 0.7)
    ctx.set_line_width(9)
    ctx.stroke()
    # úvula
    uy0, uy1 = top + 0.07 * J, top + 0.30 * J
    ctx.move_to(BX - 17, uy0)
    ctx.curve_to(BX - 18, uy1 - 46, BX - 30, uy1 - 6, BX, uy1)
    ctx.curve_to(BX + 30, uy1 - 6, BX + 18, uy1 - 46, BX + 17, uy0)
    ctx.close_path()
    g = cairo.LinearGradient(BX - 30, 0, BX + 30, 0)
    g.add_color_stop_rgb(0, *hx("#E8728A"))
    g.add_color_stop_rgb(1, *hx("#B83C58"))
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgba(*INK, 0.85)
    ctx.set_line_width(5)
    ctx.stroke()
    ctx.arc(BX - 8, uy1 - 22, 6, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 1, 1, 0.45)
    ctx.fill()


def lengua_frente(ctx, bo, calor=0.0):
    hw = bo.hw
    xs = [BX - hw * 1.25 + 2.5 * hw * i / 90 for i in range(91)]
    ctx.move_to(xs[0], 2400)
    for x in xs:
        ctx.line_to(x, bo.lengua_y(x))
    ctx.line_to(xs[-1], 2400)
    ctx.close_path()
    camino = ctx.copy_path()
    cy = bo.ty + 0.22 * bo.J
    g = cairo.RadialGradient(BX, cy, 20, BX, cy, hw * 1.05)
    g.add_color_stop_rgb(0, *mezcla(LENG_A, hx("#FFB36B"), calor * 0.6))
    g.add_color_stop_rgb(0.55, *mezcla(LENG_B, hx("#FF6A3D"), calor * 0.5))
    g.add_color_stop_rgb(1, *LENG_C)
    ctx.set_source(g)
    ctx.fill()
    ctx.save()
    ctx.append_path(camino)
    ctx.clip()
    r = rng(7)
    for _ in range(190):
        x = BX + r.uniform(-hw, hw)
        y = bo.ty + r.uniform(0, 0.66 * bo.J)
        rr = r.uniform(3, 7)
        if y < bo.lengua_y(x) + 12:
            continue
        ctx.arc(x, y, rr, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.88, 0.9, 0.32)
        ctx.fill()
    ctx.move_to(BX, bo.ty + 26)
    ctx.curve_to(BX - 6, bo.ty + 0.2 * bo.J, BX + 6, bo.ty + 0.4 * bo.J, BX, bo.bot + 80)
    ctx.set_source_rgba(*LENG_C, 0.6)
    ctx.set_line_width(12)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    for sg in (-1, 1):
        ctx.save()
        ctx.translate(BX + sg * 150, bo.ty + 60)
        ctx.rotate(sg * 0.2)
        ctx.scale(95, 18)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(1, 1, 1, 0.22)
        ctx.fill()
    ctx.restore()
    for i, x in enumerate(xs):
        (ctx.move_to if i == 0 else ctx.line_to)(x, bo.lengua_y(x))
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()


def receptor(ctx, x, y, r, alarma, t, s=1.0):
    """Sensor de calor sobre la lengua: un anillo de neón acostado."""
    if s <= 0.01:
        return
    col = mezcla(CIAN, ROJO_AL, alarma)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s * 0.64)
    g = cairo.RadialGradient(0, 0, r * 0.4, 0, 0, r * 2.6)
    g.add_color_stop_rgba(0, *col, 0.55 + 0.25 * alarma)
    g.add_color_stop_rgba(1, *col, 0)
    ctx.set_source(g)
    ctx.arc(0, 0, r * 2.6, 0, 2 * math.pi)
    ctx.fill()
    if alarma > 0.05:
        for k in range(2):
            q = (t * 1.7 + k * 0.5) % 1
            ctx.arc(0, 0, r * (1.1 + q * 1.5), 0, 2 * math.pi)
            ctx.set_source_rgba(*ROJO_AL, 0.7 * (1 - q) * alarma)
            ctx.set_line_width(r * 0.22)
            ctx.stroke()
    ctx.arc(0, 0, r * 1.12, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgb(*mezcla(hx("#0B3540"), hx("#4A0A0A"), alarma))
    ctx.fill()
    ctx.arc(0, 0, r * 0.84, 0, 2 * math.pi)
    ctx.set_source_rgb(*mezcla(col, (1, 1, 1), 0.25))
    ctx.set_line_width(r * 0.26)
    ctx.stroke()
    # ojo de cerradura
    ctx.arc(0, -r * 0.12, r * 0.2, 0, 2 * math.pi)
    ctx.move_to(-r * 0.1, -r * 0.05)
    ctx.line_to(r * 0.1, -r * 0.05)
    ctx.line_to(r * 0.16, r * 0.38)
    ctx.line_to(-r * 0.16, r * 0.38)
    ctx.close_path()
    ctx.set_source_rgb(*mezcla(col, (1, 1, 1), 0.4))
    ctx.fill()
    ctx.restore()


def diente(ctx, x, y, w, h, ang, colmillo, abajo):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(ang)
    if abajo:
        ctx.scale(1, -1)
    r = w * 0.34
    ctx.move_to(-w / 2, -16)
    ctx.line_to(-w / 2, h - r)
    if colmillo:
        ctx.curve_to(-w / 2, h - r * 0.3, -w * 0.2, h + 2, 0, h + 12)
        ctx.curve_to(w * 0.2, h + 2, w / 2, h - r * 0.3, w / 2, h - r)
    else:
        ctx.curve_to(-w / 2, h - r * 0.2, -w / 2 + r * 0.2, h, -w / 2 + r, h)
        ctx.line_to(w / 2 - r, h)
        ctx.curve_to(w / 2 - r * 0.2, h, w / 2, h - r * 0.2, w / 2, h - r)
    ctx.line_to(w / 2, -16)
    ctx.close_path()
    g = cairo.LinearGradient(-w / 2, 0, w / 2, 0)
    g.add_color_stop_rgb(0, *DIENTE2)
    g.add_color_stop_rgb(0.3, *DIENTE)
    g.add_color_stop_rgb(0.7, *DIENTE)
    g.add_color_stop_rgb(1, *DIENTE2)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.move_to(-w * 0.22, h * 0.15)
    ctx.line_to(-w * 0.22, h * 0.55)
    ctx.set_source_rgba(1, 1, 1, 0.9)
    ctx.set_line_width(w * 0.12)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.restore()


def encia(ctx, bo, abajo):
    xs = bo.xs(bo.hw * 0.995)
    if abajo:
        f, d0, d1 = bo.bot_in, 6, -20
    else:
        f, d0, d1 = bo.top_in, -6, 22
    ctx.move_to(xs[0], f(xs[0]) + d0)
    for x in xs[1:]:
        ctx.line_to(x, f(x) + d0)
    for x in reversed(xs):
        ctx.line_to(x, f(x) + d1)
    ctx.close_path()
    ctx.set_source_rgb(*ENCIA)
    ctx.fill()
    for i, x in enumerate(xs):
        (ctx.move_to if i == 0 else ctx.line_to)(x, f(x) + d1)
    ctx.set_source_rgba(*ENCIA2, 0.9)
    ctx.set_line_width(4)
    ctx.stroke()


def _sobre_curva(f, anchos, hw, gap=5):
    """Centros (x) de piezas puestas una al lado de la otra a lo largo de la curva y = f(x), desde el centro."""
    xs = np.linspace(BX, BX + hw * 0.995, 500)
    ys = np.array([f(x) for x in xs])
    cum = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))])
    out, s = [], gap / 2
    for w in anchos:
        s += w / 2
        out.append(float(np.interp(s, cum, xs)))
        s += w / 2 + gap
    return out


def dientes(ctx, bo):
    ws = [w for _, w, _, _ in DINF]
    cx = _sobre_curva(bo.bot_in, ws, bo.hw)
    for sg in (-1, 1):
        for (dx, w, h, c), x0 in reversed(list(zip(DINF, cx))):
            x = BX + sg * (x0 - BX)
            diente(ctx, x, bo.bot_in(x) - 16, w, h, math.atan(_pend(bo.bot_in, x)) * 0.85, c, True)
    encia(ctx, bo, True)
    fs = [1 - 0.2 * (dx / bo.hw) ** 1.5 for dx, _, _, _ in DSUP]
    cx = _sobre_curva(bo.top_in, [w * f for (_, w, _, _), f in zip(DSUP, fs)], bo.hw, gap=4)
    for sg in (-1, 1):
        for (dx, w, h, c), f, x0 in reversed(list(zip(DSUP, fs, cx))):
            x = BX + sg * (x0 - BX)
            diente(ctx, x, bo.top_in(x) + 18, w * f, h * f, math.atan(_pend(bo.top_in, x)) * 0.9, c, False)
    encia(ctx, bo, False)


def labios(ctx, bo):
    ctx.save()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    bo.camino_out(ctx)
    bo.camino_in(ctx)
    anillo = ctx.copy_path()
    ctx.new_path()
    ctx.save()
    ctx.rectangle(-2000, -2000, 5080, bo.yc + 2000)
    ctx.clip()
    ctx.append_path(anillo)
    g = cairo.LinearGradient(0, bo.top - LAB_UP, 0, bo.top + 20)
    g.add_color_stop_rgb(0, *LAB_SUP)
    g.add_color_stop_rgb(1, *LAB_SUP2)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()
    ctx.save()
    ctx.rectangle(-2000, bo.yc, 5080, 5000)
    ctx.clip()
    ctx.append_path(anillo)
    g = cairo.RadialGradient(BX, bo.bot + 36, 20, BX, bo.bot + 36, bo.hw + 80)
    g.add_color_stop_rgb(0, *LAB_INF)
    g.add_color_stop_rgb(1, *LAB_INF2)
    ctx.set_source(g)
    ctx.fill()
    ctx.restore()
    for (x, y, rx, ry, ang, a) in ((BX, bo.bot + 44, 130, 13, 0, 0.42), (BX - 100, bo.top - 30, 48, 9, -0.12, 0.32),
                                   (BX + 100, bo.top - 30, 48, 9, 0.12, 0.32)):
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(ang)
        ctx.scale(rx, ry)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(1, 1, 1, a)
        ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    bo.camino_out(ctx)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(8)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    bo.camino_in(ctx)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.restore()


def boca_frente(ctx, t, a=1.0, rec=None, calor=0.0, en_lengua=None, liquido=None, entre_dientes=None, piel=True):
    """Primer plano de la cara con la boca abierta. rec = [(alarma, escala)] por sensor."""
    bo = Boca(a)
    if piel:
        piel_cara(ctx)
    ctx.save()
    bo.camino_in(ctx)
    ctx.clip()
    cavidad(ctx, bo)
    lengua_frente(ctx, bo, calor)
    if rec is not None:
        for i, (al, sp) in enumerate(rec):
            x, y = bo.rec(i)
            receptor(ctx, x, y, 27, al, t + i * 0.37, s=sp)
    if calor > 0:
        _elipse_suave(ctx, BX, bo.ty + 140, 520, 260, hx("#FF7A2A"), 0.35 * calor)
    if en_lengua:
        en_lengua(ctx, bo)
    if liquido:
        liquido(ctx, bo)
    if entre_dientes:
        entre_dientes(ctx, bo)
    dientes(ctx, bo)
    bo.camino_in(ctx)
    ctx.set_source_rgba(0.18, 0.0, 0.04, 0.22)
    ctx.set_line_width(34)
    ctx.stroke()
    ctx.restore()
    labios(ctx, bo)
    return bo


# ------------------------------------------------------------------ tiempos clave
T_BITE = b(0, "picante") + 0.28
T_QUEMA = b(0, "sabor") + 0.1
T_ALARMA = b(1, "alarma")
T_SIN = b(1, "sin")
T_SENS, T_QUE, T_43 = b(2, "sensores"), b(2, "quema"), b(2, "43")
T_AJI, T_SUS, T_ENC, T_JUS, T_LLA = b(3, "ají"), b(3, "sustancia"), b(3, "encaja"), b(3, "justo"), b(3, "llave")
T_CER, T_REC, T_SEN, T_CAF, T_PER, T_NI = (b(4, "cerebro"), b(4, "recibe"), b(4, "señal"), b(4, "café"),
                                           b(4, "pero"), b(4, "ni"))
T_TRA, T_ROJ, T_LLO, T_CUE, T_APA, T_NOE = (b(5, "transpiras"), b(5, "rojo"), b(5, "lloran"), b(5, "cuerpo"),
                                            b(5, "apagar"), b(5, "no"))
T_CAP, T_MEZ, T_AGU, T_TOM, T_BOC = (b(6, "capsaicina"), b(6, "mezcla"), b(6, "agua"), b(6, "tomarla"),
                                     b(6, "boca"))
T_LEC, T_GRA, T_ATR, T_DES, T_LEN = b(7, "leche"), b(7, "grasa"), b(7, "atrapa"), b(7, "despega"), b(7, "lengua")
T_PQU = b(8, "quema")
T_CAL, T_PPE, T_PLL, T_PEN = b(9, "calor"), b(9, "pero"), b(9, "llave"), b(9, "encaja")
T_TRG, T_SEM, T_MAS, T_EXC, T_LEJ = (b(10, "tragan"), b(10, "semillas"), b(10, "masticarlas"), b(10, "excrementos"),
                                     b(10, "lejos"))
T_CRE, T_NUE = b(11, "crecen"), b(11, "nuevos")
T_RMA, T_RDE = b(12, "mastica"), b(12, "destruye")
T_EXI, T_ESP = b(13, "existe"), b(13, "espantar")
T_COMO, T_TU = b(14, "Como"), b(14, "tú")

# transiciones (inicio, duración)
Z1 = (b(2) - 0.16, 0.42)            # Vos -> adentro de la boca
Z2 = (T_ENC - 0.17, 0.40)           # boca -> un sensor de cerca
Z3 = (T_CER - 0.30, 0.42)           # sensor -> cerebro (hacia afuera)
Z4 = (b(6) - 0.22, 0.42)            # la cara -> adentro de la boca
B5 = (b(8) - 0.12, 0.36)            # boca -> pájaro (barrido)
T_FIN = T_COMO - 0.26               # la boca entra para el "como tú"

BOCA_C = (540, 945)                 # centro de la boca en el primer plano


def pill(ctx, txt, x, y, t, t0, t1=None, size=70, box=AMARILLO, fg=INK, rot=-3):
    if t < t0 or (t1 is not None and t > t1 + 0.2):
        return
    s = pop(t, t0)
    if t1 is not None:
        s *= 1 - prog(t, t1, 0.2, "in")
    cartel(ctx, txt, x, y, size, box=box, fg=fg, s=s, rot=rot)


# ------------------------------------------------------------------ 1. el gancho: Vos muerde el ají
def d_gancho(ctx, t):
    q_cal = clamp((t - T_QUEMA) / 0.4)
    fondo_azul(ctx, t, calor=0.3 + 0.7 * q_cal, cx=540, cy=1150, rc=950)
    al = 0.0
    if T_ALARMA <= t < T_ALARMA + 1.1:
        al = clamp((t - T_ALARMA) / 0.1) * (1 - clamp((t - T_ALARMA - 0.8) / 0.3)) * (0.6 + 0.4 * math.sin(t * 14))
    vineta_roja(ctx, al)
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
        dibujar_vos(ctx, pose)
    if pose != "quema":
        hx_, hy_ = vpos(372, 436)
        mx_, my_ = vpos(292, 405)
        ang = math.degrees(math.atan2(my_ - hy_, mx_ - hx_))
        aji(ctx, (hx_ + mx_) / 2 + 10, (hy_ + my_) / 2, 0.6, rot=ang + 360, mordida=mord)
    else:
        q = clamp((t - T_QUEMA) / 0.7)
        hx_, hy_ = vpos(372, 436)
        aji(ctx, hx_ + 60 * q, hy_ + 900 * q * q, 0.6, rot=-160 + 300 * q, mordida=1.0)
    if T_BITE <= t < T_BITE + 0.3:
        mx_, my_ = vpos(300, 400)
        q = (t - T_BITE) / 0.3
        for k in range(8):
            a = k * math.pi / 4
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
    cartel(ctx, "EL PICANTE\nNO ES UN SABOR", 540, 245, 84, s=1 + 0.012 * math.sin(t * 2.4), pad=(56, 26))
    if t >= T_ALARMA:
        campana(ctx, 230, 640, 0.6 * pop(t, T_ALARMA, 0.3), t, sonando=t < T_ALARMA + 1.0)
    if t >= T_SIN:
        sp = pop(t, T_SIN, 0.3)
        llama(ctx, 850, 660, 0.85 * sp, t)
        prohibido(ctx, 850, 640, 105, sp)


VOS_BOCA = vpos(260, 410)


# ------------------------------------------------------------------ 2. adentro de la boca: sensores, 43 °C y el ají
R_STAR = 5                                  # el sensor al que entra la cámara
K1 = [0, 2, 4, 6, 9, 11]                    # sensores que ocupan las otras llaves
CHUNK = (566, 958)                          # donde cae el pedazo de ají


def temperatura(t):
    if t < T_QUE:
        return 25.0
    if t < T_43:
        return lerp(25, 43, ease((t - T_QUE) / (T_43 - T_QUE), "in"))
    if t < T_43 + 0.6:
        return 43.0
    return lerp(43, 25, prog(t, T_43 + 0.6, 0.45))


def _salto_llave(i, n):
    """Ruta de cada llave desde el pedazo de ají hasta su sensor."""
    t0 = T_SUS + 0.06 + i * 0.05
    return t0, 0.42 + 0.03 * i


LLAVES1 = K1 + [R_STAR]


def llaves_boca1(ctx, bo, t):
    if t < T_SUS:
        return
    for i, ri in enumerate(LLAVES1):
        t0, d = _salto_llave(i, len(LLAVES1))
        if t < t0:
            continue
        x1, y1 = bo.rec(ri)
        if ri == R_STAR:
            x1 -= 70
            d += 0.25
        q = clamp((t - t0) / d)
        e = ease(q, "inout")
        x = lerp(CHUNK[0], x1, e)
        y = lerp(CHUNK[1] - 10, y1 - 4, e) - 90 * math.sin(math.pi * q)
        rot = lerp(-30 if x1 < CHUNK[0] else 30, 0, e) + (6 * math.sin(t * 18 + i) if q >= 1 else 0)
        s = 0.2 * pop(t, t0, 0.25)
        llavecita(ctx, x, y, s, rot=rot, cara="picara")


def alarma_boca1(t, i):
    a = clamp((t - T_43) / 0.1) * (1 - clamp((t - T_43 - 0.7) / 0.3)) if t >= T_43 else 0.0
    if i in LLAVES1 and i != R_STAR:
        k = LLAVES1.index(i)
        t0, d = _salto_llave(k, len(LLAVES1))
        a = max(a, clamp((t - t0 - d) / 0.12))
    return a


def ajicito(ctx, x, y, s, rot, alpha=1.0):
    aji(ctx, x, y, s, rot=rot, mordida=0.55, alpha=alpha)


def d_boca1(ctx, t):
    temp = temperatura(t)
    calor = clamp((temp - 25) / 18)
    rec = [(alarma_boca1(t, i), pop(t, T_SENS + i * 0.05, 0.3)) for i in range(len(REC))]
    cae = T_AJI - 0.1
    aterriza = cae + 0.42

    def en_lengua(ctx, bo):
        if calor > 0.02:
            for k in range(7):
                q = (t * 0.9 + k / 7) % 1
                x = BX - 300 + k * 100
                y = bo.ty + 120 - q * 380
                ctx.move_to(x, y)
                for j in range(6):
                    ctx.line_to(x + 12 * math.sin(j * 1.3 + t * 6 + k), y - j * 22)
                ctx.set_source_rgba(1, 0.75, 0.4, 0.5 * calor * math.sin(math.pi * q))
                ctx.set_line_width(7)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke()
        if t >= aterriza:
            sq = 1 + 0.25 * (1 - clamp((t - aterriza) / 0.15)) if t < aterriza + 0.15 else 1.0
            ajicito(ctx, CHUNK[0], CHUNK[1], 0.42 * sq, -12)
        llaves_boca1(ctx, bo, t)

    zz = 1 + 0.035 * clamp((t - Z1[0]) / 6.0)
    sac = 6 * math.sin(t * 70) * (1 - clamp((t - T_43) / 0.3)) if T_43 <= t < T_43 + 0.3 else 0.0
    ctx.save()
    camara(ctx, 540, 960, zz, 540 + sac, 960)
    boca_frente(ctx, t, a=1.0, rec=rec, calor=calor, en_lengua=en_lengua)
    ctx.restore()
    # el pedazo de ají cae desde afuera
    if cae <= t < aterriza:
        q = clamp((t - cae) / (aterriza - cae))
        ajicito(ctx, CHUNK[0] + 20 * (1 - q), lerp(150, CHUNK[1], q * q), 0.42 * zz, lerp(-80, -12, q))
    # la temperatura
    if T_QUE - 0.15 <= t < T_43 + 1.1:
        a = 1 - prog(t, T_43 + 0.8, 0.25, "in")
        caliente = temp >= 42.9
        cartel(ctx, f"{int(round(temp))} °C", 540, 175, 84, box=ROJO_AL if caliente else BLANCO,
               fg=BLANCO if caliente else INK, s=pop(t, T_QUE - 0.15) * bump(t, T_43, 0.3, 0.2) * a, rot=-2)


# ------------------------------------------------------------------ 3. de cerca: la llave falsa en el sensor
SOCK = (540, 1090)
SRX, SRY = 250, 96


def lengua_macro(ctx, t, alarma=0.0):
    g = cairo.LinearGradient(0, 0, 0, 720)
    g.add_color_stop_rgb(0, *hx("#16030A"))
    g.add_color_stop_rgb(1, *hx("#5E1426"))
    ctx.set_source(g)
    ctx.paint()
    ctx.move_to(-3000, 720)
    ctx.line_to(-80, 720)
    ctx.curve_to(300, 560, 780, 560, 1160, 720)
    ctx.line_to(4000, 720)
    ctx.line_to(4000, 7000)
    ctx.line_to(-3000, 7000)
    ctx.close_path()
    camino = ctx.copy_path()
    g = cairo.LinearGradient(0, 600, 0, 1920)
    g.add_color_stop_rgb(0, *hx("#B9435F"))
    g.add_color_stop_rgb(0.35, *LENG_B)
    g.add_color_stop_rgb(1, *LENG_A)
    ctx.set_source(g)
    ctx.fill()
    ctx.save()
    ctx.append_path(camino)
    ctx.clip()
    r = rng(12)
    for j in range(15):
        f = (j / 14) ** 1.6
        y = 640 + 1350 * f
        rr = 7 + 34 * f
        paso = rr * 3.3
        x = -40 + (j % 2) * paso / 2 + r.uniform(0, paso / 2)
        while x < 1120:
            xx, yy = x + r.uniform(-rr * 0.4, rr * 0.4), y + r.uniform(-rr * 0.3, rr * 0.3)
            if ((xx - SOCK[0]) / (SRX * 1.25)) ** 2 + ((yy - SOCK[1]) / (SRY * 1.5)) ** 2 > 1:
                ctx.save()
                ctx.translate(xx, yy + rr * 0.18)
                ctx.scale(rr, rr * 0.5)
                ctx.arc(0, 0, 1, 0, 2 * math.pi)
                ctx.restore()
                ctx.set_source_rgba(*LENG_C, 0.35)
                ctx.fill()
                ctx.save()
                ctx.translate(xx, yy)
                ctx.scale(rr, rr * 0.5)
                ctx.arc(0, 0, 1, 0, 2 * math.pi)
                ctx.restore()
                ctx.set_source_rgba(1, 0.8, 0.85, 0.5)
                ctx.fill()
            x += paso
    ctx.move_to(528, 600)
    ctx.line_to(552, 600)
    ctx.line_to(610, 2000)
    ctx.line_to(470, 2000)
    ctx.close_path()
    ctx.set_source_rgba(*LENG_C, 0.3)
    ctx.fill()
    g = cairo.LinearGradient(0, 560, 0, 900)
    g.add_color_stop_rgba(0, 0.1, 0, 0.03, 0.75)
    g.add_color_stop_rgba(1, 0.1, 0, 0.03, 0)
    ctx.set_source(g)
    ctx.paint()
    if alarma > 0:
        _elipse_suave(ctx, SOCK[0], SOCK[1], 700, 420, ROJO_AL, 0.35 * alarma)
    ctx.restore()


def zocalo(ctx, x, y, rx, ry, alarma, t, forma="redonda", s=1.0):
    """Un sensor visto de cerca: un anillo hundido en la superficie con su cerradura."""
    if s <= 0.01:
        return
    col = mezcla(CIAN, ROJO_AL, alarma)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    _elipse_suave(ctx, 0, 0, rx * 1.9, ry * 2.4, col, 0.45 + 0.25 * alarma)
    if alarma > 0.05:
        for k in range(3):
            q = (t * 1.2 + k / 3) % 1
            ctx.save()
            ctx.scale(rx, ry)
            ctx.arc(0, 0, 1.05 + q * 0.9, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgba(*ROJO_AL, 0.75 * (1 - q) * alarma)
            ctx.set_line_width(10)
            ctx.stroke()
    for (k, c) in ((1.1, INK), (1.0, mezcla(hx("#0B3540"), hx("#4A0A0A"), alarma))):
        ctx.save()
        ctx.scale(rx * k, ry * k)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*c)
        ctx.fill()
    # pared interna (se ve la del fondo)
    ctx.save()
    ctx.scale(rx * 0.84, ry * 0.8)
    ctx.arc(0, 0.16, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(*mezcla(hx("#04161C"), hx("#250404"), alarma))
    ctx.fill()
    # aro de luz
    for lw, a in ((26, 0.25), (12, 1.0)):
        ctx.save()
        ctx.scale(rx * 0.93, ry * 0.93)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(*mezcla(col, (1, 1, 1), 0.2), a)
        ctx.set_line_width(lw)
        ctx.stroke()
    # cerradura acostada
    ctx.save()
    ctx.translate(0, ry * 0.12)
    ctx.scale(1, 0.42)
    if forma == "redonda":
        ctx.arc(0, -10, 38, 0, 2 * math.pi)
        ctx.move_to(-20, 0)
        ctx.line_to(20, 0)
        ctx.line_to(30, 80)
        ctx.line_to(-30, 80)
        ctx.close_path()
    else:
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = 70 if i % 2 == 0 else 30
            (ctx.move_to if i == 0 else ctx.line_to)(math.cos(a) * rr, math.sin(a) * rr + 20)
        ctx.close_path()
    path = ctx.copy_path()
    ctx.set_source_rgb(*hx("#020809"))
    ctx.fill()
    ctx.append_path(path)
    ctx.set_source_rgba(*col, 0.9)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.restore()
    ctx.restore()


def d_cerradura(ctx, t):
    t_in = T_JUS - 0.02                         # la llave queda arriba de la cerradura
    t_baja = t_in + 0.22                         # ya entró
    t_g0, t_g1 = t_baja + 0.12, t_baja + 0.56    # gira
    alarma = clamp((t - t_g1) / 0.12)
    zz = 1 + 0.04 * clamp((t - Z2[0]) / 3.0)
    sac = 8 * math.sin(t * 70) * (1 - clamp((t - t_g1) / 0.35)) if t_g1 <= t < t_g1 + 0.35 else 0.0
    ctx.save()
    camara(ctx, 540, 960, zz, 540 + sac, 960)
    lengua_macro(ctx, t, alarma)
    zocalo(ctx, SOCK[0], SOCK[1], SRX, SRY, alarma, t)
    # la llave
    tip_y = SOCK[1] + 12
    if t < t_in:
        q = clamp((t - (Z2[0] + 0.12)) / (t_in - Z2[0] - 0.12))
        x = lerp(-260, SOCK[0], ease(q, "out"))
        y = lerp(tip_y - 300, tip_y - 240, q) - 70 * abs(math.sin(q * math.pi * 3))
        rot = 14 * math.sin(q * math.pi * 6) * (1 - q)
        giro = 1.0
    else:
        x = SOCK[0]
        y = lerp(tip_y - 240, tip_y + 150, ease(clamp((t - t_in) / (t_baja - t_in)), "in"))
        rot = 0.0
        th = 2 * math.pi * ease(clamp((t - t_g0) / (t_g1 - t_g0)), "inout")
        giro = math.cos(th)
    cara = "feliz" if alarma > 0.5 else "picara"
    ctx.save()
    ctx.rectangle(-500, -500, 2080, tip_y + 500 - 4)
    ctx.clip()
    llavecita(ctx, x, y, 1.0, rot=rot, cara=cara, giro=giro)
    ctx.restore()
    ctx.restore()
    if alarma > 0:
        vineta_roja(ctx, 0.6 * alarma * (0.7 + 0.3 * math.sin(t * 12)))
    pill(ctx, "LLAVE FALSA", 540, 330, t, T_LLA, size=92)


# ------------------------------------------------------------------ 4. el cerebro y el cuerpo
BL, BR, BRAD = (290, 1060), (790, 1060), 185
SB = 0.36                                   # escala de la boca dentro de la insignia
_rs = Boca(1.0).rec(R_STAR)
BADGE_STAR = (BL[0] + SB * (_rs[0] - BOCA_C[0]), BL[1] + SB * (_rs[1] - BOCA_C[1]))
CARA = (540, 1040, 290)
CARA_BOCA = (540, CARA[1] - 0.12 * CARA[2] + 0.42 * CARA[2] + 6 * 2.3)


def insignia(ctx, x, y, r, s, dibujo, alpha=1.0):
    if s <= 0.01 or alpha <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.push_group()
    ctx.arc(0, 8, r + 14, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(0, 0, r + 14, 0, 2 * math.pi)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.save()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.clip()
    dibujo(ctx)
    ctx.restore()
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(alpha)
    ctx.restore()


def rec_rojos(lista):
    return [(1.0 if i in lista else 0.0, 1.0) for i in range(len(REC))]


def llaves_quietas(ctx, bo, t, indices, s=0.2, cara="picara"):
    for k, i in enumerate(indices):
        x, y = bo.rec(i)
        llavecita(ctx, x, y - 4, s, rot=6 * math.sin(t * 7 + k), cara=cara)


def boca_insignia(t):
    def dib(ctx):
        ctx.save()
        ctx.scale(SB, SB)
        ctx.translate(-BOCA_C[0], -BOCA_C[1])
        boca_frente(ctx, t, a=1.0, rec=rec_rojos(LLAVES1), en_lengua=lambda c, bo: (
            ajicito(c, CHUNK[0], CHUNK[1], 0.42, -12), llaves_quietas(c, bo, t, LLAVES1)))
        ctx.restore()
    return dib


def cafe_insignia(t):
    def dib(ctx):
        g = cairo.RadialGradient(0, 40, 20, 0, 40, 260)
        g.add_color_stop_rgb(0, *hx("#7A3A1A"))
        g.add_color_stop_rgb(1, *hx("#1A0C10"))
        ctx.set_source(g)
        ctx.paint()
        taza(ctx, -10, 60, 0.95, t)
    return dib


def senal(ctx, x0, y0, x1, y1, t, t0, color=hx("#FF4D3A"), a=1.0):
    if t < t0 or a <= 0.01:
        return
    q = clamp((t - t0) / 0.4)
    n = 14
    pts = []
    for i in range(n + 1):
        f = i / n * q
        x, y = lerp(x0, x1, f), lerp(y0, y1, f)
        if 0 < i < n:
            dxp, dyp = -(y1 - y0), (x1 - x0)
            L = math.hypot(dxp, dyp) or 1
            off = 20 * (1 if i % 2 else -1)
            x += dxp / L * off
            y += dyp / L * off
        pts.append((x, y))
    for lw, col, al in ((22, color, 0.25), (12, color, 0.6), (6, (1, 1, 0.8), 1.0)):
        for i, (x, y) in enumerate(pts):
            (ctx.move_to if i == 0 else ctx.line_to)(x, y)
        ctx.set_source_rgba(*col, al * a)
        ctx.set_line_width(lw)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    for k in range(3):
        f = ((t - t0) * 1.4 + k / 3) % 1
        punto_brillo(ctx, lerp(x0, x1, f * q), lerp(y0, y1, f * q), 10, color, a)


def cara_tu(ctx, x, y, R, t, rojo=0.0, arde=0.0, t_sudor=None, t_lagrimas=None, sac=0.0):
    x += sac
    piel = mezcla(PIEL_C, hx("#FF6A55"), rojo)
    piel2 = mezcla(PIEL_O, hx("#D63E30"), rojo)
    ctx.arc(x, y + 12, R, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    g = cairo.RadialGradient(x - R * 0.3, y - R * 0.35, R * 0.1, x, y, R)
    g.add_color_stop_rgb(0, *mezcla(piel, (1, 1, 1), 0.15))
    g.add_color_stop_rgb(1, *piel2)
    ctx.arc(x, y, R, 0, 2 * math.pi)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(10)
    ctx.stroke()
    for sx in (-1, 1):
        _elipse_suave(ctx, x + sx * R * 0.56, y + R * 0.2, R * 0.2, R * 0.12, hx("#FF5A6E"), 0.5 + 0.3 * rojo)
    ey = y - R * 0.12
    sep = R * 0.66
    if arde > 0.5:
        carita(ctx, x, ey, sep, 2.3, ojos="wide", boca="o", ceja="up", dy_boca=R * 0.42)
    else:
        carita(ctx, x, ey, sep, 2.3, ojos="open", boca="smile", dy_boca=R * 0.42)
    # sudor
    if t_sudor is not None and t >= t_sudor:
        r = rng(4)
        for k in range(6):
            ph = r.uniform(0, 1)
            q = ((t - t_sudor) * 0.7 + ph) % 1
            if t - t_sudor < ph * 0.6:
                continue
            lado = -1 if k % 2 else 1
            ang = math.radians(lerp(-60, -10, q) + r.uniform(-8, 8))
            px = x + lado * R * 0.93 * math.cos(ang) + lado * 10
            py = y + R * 0.93 * math.sin(ang) + q * 40
            gota(ctx, px, py, 17, hx("#BFEFFF"), alpha=1 - q * 0.3)
    # lágrimas
    if t_lagrimas is not None and t >= t_lagrimas:
        q0 = clamp((t - t_lagrimas) / 0.4)
        for sx in (-1, 1):
            x0 = x + sx * sep / 2
            y0 = ey + 70
            y1 = y0 + q0 * R * 0.75
            ctx.move_to(x0, y0)
            ctx.curve_to(x0 + sx * 6, y0 + 40, x0 - sx * 8, y1 - 40, x0 + sx * 4 * math.sin(t * 6), y1)
            for lw, c in ((26, INK), (16, AZUL_AGUA)):
                ctx.set_source_rgb(*c)
                ctx.set_line_width(lw)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.stroke_preserve()
            ctx.new_path()
            for k in range(2):
                qq = ((t - t_lagrimas) * 1.6 + k * 0.5) % 1
                gota(ctx, x0 + sx * 6, y1 + 10 + qq * 260, 13, AZUL_AGUA, alpha=1 - qq)
    if rojo > 0.3:
        vapor(ctx, x - R * 0.55, y - R * 0.8, t, T_ROJ, -1)
        vapor(ctx, x + R * 0.55, y - R * 0.8, t, T_ROJ, 1)


def rociadores(ctx, t, t0, t1, a):
    if a <= 0.01:
        return
    ctx.save()
    ctx.push_group()
    rrect(ctx, 110, 548, 860, 36, 18)
    ctx.set_source_rgb(*hx("#9AA3B5"))
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    for x in (280, 540, 800):
        rrect(ctx, x - 24, 578, 48, 40, 10)
        ctx.set_source_rgb(*hx("#C9D0DD"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.stroke()
        if t0 <= t < t1 + 0.6:
            r = rng(x)
            for k in range(30):
                ph = r.uniform(0, 1)
                q = ((t - t0) * 1.4 + ph) % 1
                nacio = t - q / 1.4
                if nacio < t0 or nacio > t1:
                    continue
                ang = r.uniform(-0.55, 0.55)
                px = x + math.sin(ang) * q * 420
                py = 620 + math.cos(ang) * q * 640 + 120 * q * q
                gota(ctx, px, py, 11, AZUL_AGUA, alpha=0.95, borde=True)
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)
    ctx.restore()


def llama_punteada(ctx, x, y, s, a):
    if a <= 0.01 or s <= 0.01:
        return
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.move_to(0, 60)
    ctx.curve_to(-70, 50, -70, -20, -20, -60)
    ctx.curve_to(-10, -30, 0, -90, 0, -110)
    ctx.curve_to(30, -70, 70, -40, 62, 10)
    ctx.curve_to(60, 50, 30, 62, 0, 60)
    ctx.close_path()
    ctx.restore()
    ctx.set_dash([20, 16])
    ctx.set_source_rgba(1, 1, 1, 0.95 * a)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.set_dash([])
    texto(ctx, "?", x, y - 20 * s, 120 * s, fill=BLANCO, sw=8, alpha=a)


def d_cuerpo(ctx, t):
    sale = prog(t, b(5) - 0.2, 0.45)          # se van las insignias y el cerebro sube
    fl = 0.0
    for tt in (T_REC + 0.4, T_CAF + 0.5):
        if tt <= t < tt + 0.7:
            fl = max(fl, 1 - (t - tt) / 0.7)
    rojo_cara = prog(t, T_ROJ, 0.45)
    fondo_azul(ctx, t, calor=0.25 * fl + 0.5 * rojo_cara * (1 - prog(t, T_NOE, 0.6)), cx=540, cy=1000)
    bx, by = lerp(540, 540, sale), lerp(470, 300, sale)
    bs = lerp(0.95, 0.58, sale)
    if fl > 0:
        _elipse_suave(ctx, bx, by, 420 * bs, 420 * bs, ROJO_AL, 0.6 * fl)
    P.cerebro(ctx, bx, by, bs * pop(t, T_CER - 0.12, 0.4) * bump(t, T_REC + 0.4, 0.3, 0.08) * bump(t, T_CAF + 0.5, 0.3, 0.08))
    k_ins = 1 - sale
    if k_ins > 0.01:
        a_cafe = 1 - 0.55 * prog(t, T_PER, 0.4)
        senal(ctx, BL[0] + 40, BL[1] - BRAD - 10, 470, 620, t, T_REC, a=k_ins)
        senal(ctx, BR[0] - 40, BR[1] - BRAD - 10, 610, 620, t, T_CAF + 0.1, a=k_ins * a_cafe)
        insignia(ctx, BL[0], BL[1], BRAD, k_ins * bump(t, T_PER, 0.35, 0.1), boca_insignia(t))
        if t >= T_CAF - 0.2:
            insignia(ctx, BR[0], BR[1], BRAD, k_ins * pop(t, T_CAF - 0.2), cafe_insignia(t), alpha=a_cafe)
        if t >= T_REC:
            cartel(ctx, "36 °C", BL[0], BL[1] + BRAD + 50, 62, box=BLANCO, s=k_ins * pop(t, T_REC) * bump(t, T_PER, 0.35, 0.2))
        if t >= T_CAF + 0.1:
            cartel(ctx, "70 °C", BR[0], BR[1] + BRAD + 50, 62, box=ROJO_AL, fg=BLANCO, s=k_ins * pop(t, T_CAF + 0.1),
                   alpha=a_cafe)
        if t >= T_SEN:
            cartel(ctx, "¡QUEMA!", 540, 165, 84, box=ROJO_AL, fg=BLANCO,
                   s=k_ins * pop(t, T_SEN) * bump(t, T_CAF + 0.5, 0.3, 0.15), rot=-3)
        if t >= T_NI:
            sello(ctx, "+0 °C", BL[0] + 30, BL[1] + 10, True, s=k_ins * pop(t, T_NI), rot=-8)
    # la cara
    cs = pop(t, b(5) - 0.15, 0.4)
    if cs > 0.01:
        sac = 7 * math.sin(t * 55) * clamp((t - T_CUE) / 0.2) * (1 - clamp((t - T_APA - 0.2) / 0.3))
        senal(ctx, 540, by + 150, 540, CARA[1] - CARA[2] - 10, t, T_TRA - 0.15, a=1 - prog(t, T_NOE, 0.3))
        ctx.save()
        ctx.translate(CARA[0], CARA[1])
        ctx.scale(cs, cs)
        ctx.translate(-CARA[0], -CARA[1])
        cara_tu(ctx, CARA[0], CARA[1], CARA[2], t, rojo=rojo_cara * (1 - 0.6 * prog(t, T_NOE + 0.2, 0.5)),
                arde=1.0 if t >= T_TRA - 0.1 else 0.0, t_sudor=T_TRA, t_lagrimas=T_LLO, sac=sac)
        ctx.restore()
        rociadores(ctx, t, T_APA + 0.15, T_NOE - 0.1, pop(t, T_APA - 0.15, 0.3) * (1 - prog(t, T_NOE + 0.3, 0.3)))
        llama_punteada(ctx, CARA_BOCA[0], CARA_BOCA[1] - 30, 1.0 * pop(t, T_NOE, 0.3), 1 - prog(t, Z4[0] - 0.05, 0.15))
        pill(ctx, "NO HAY FUEGO", 540, 600, t, T_NOE + 0.15, size=84, box=ROJO_AL, fg=BLANCO)


# ------------------------------------------------------------------ 5. agua y leche
D0 = LLAVES1                                  # sensores con llave al empezar
D1 = [1, 3, 8, 7, 10, 5, 0]                   # adónde las lleva el agua (una por llave de D0)


def _pos_llave_agua(bo, k, t):
    """Posición de la llave k durante la escena del agua y la leche."""
    x0, y0 = bo.rec(D0[k])
    x1, y1 = bo.rec(D1[k])
    q = prog(t, T_TOM - 0.1 + 0.08 * k, 1.9, "inout")
    x = lerp(x0, x1, q) + 40 * math.sin(math.pi * q) * math.sin(k * 2.1)
    y = lerp(y0, y1, q) - 70 * math.sin(math.pi * q)
    if t >= T_DES:
        e = prog(t, T_DES + 0.06 * k, 0.6, "in")
        gx, gy = BX, bo.top + 0.36 * bo.J
        x, y = lerp(x, gx, e), lerp(y, gy, e)
    return x, y


def _alarma_agua(bo, i, t):
    """Un sensor queda rojo desde que lo toca una llave hasta que la leche se la lleva."""
    if i in D0:
        on = True
    else:
        on = False
        tm = T_TOM - 0.1
        for k in range(len(D0)):
            tt = tm
            while tt <= min(t, tm + 2.6):
                x, y = _pos_llave_agua(bo, k, tt)
                rx, ry = bo.rec(i)
                if math.hypot(x - rx, y - ry) < 48:
                    on = True
                    break
                tt += 0.08
            if on:
                break
    if not on:
        return 0.0
    if t >= T_DES:
        # se apaga cuando se va la llave que tenía encima
        for k in range(len(D0)):
            if D1[k] == i:
                return 1 - prog(t, T_DES + 0.06 * k + 0.15, 0.25)
        return 1 - prog(t, T_DES + 0.3, 0.3)
    return 1.0


def _nivel(bo, t, t0, d0, t1, d1, alto):
    sube = prog(t, t0, d0, "out")
    baja = prog(t, t1, d1, "in")
    return lerp(bo.bot + 60, alto, sube * (1 - baja))


def liquido(ctx, bo, y, col, a, t, borde=(1, 1, 1)):
    if y > bo.bot + 50:
        return
    xs = range(BX - bo.hw - 20, BX + bo.hw + 40, 20)
    ctx.move_to(BX - bo.hw - 20, 2400)
    for x in xs:
        ctx.line_to(x, y + 9 * math.sin(x * 0.02 + t * 5))
    ctx.line_to(BX + bo.hw + 40, 2400)
    ctx.close_path()
    ctx.set_source_rgba(*col, a)
    ctx.fill()
    for i, x in enumerate(xs):
        (ctx.move_to if i == 0 else ctx.line_to)(x, y + 9 * math.sin(x * 0.02 + t * 5))
    ctx.set_source_rgba(*borde, 0.85)
    ctx.set_line_width(6)
    ctx.stroke()


def globulos(ctx, bo, t):
    if t < T_GRA - 0.2:
        return
    env = prog(t, T_ATR, 0.7)
    r = rng(21)
    for k in range(len(D0)):
        kx, ky = _pos_llave_agua(bo, k, t)
        for j in range(7):
            a0 = r.uniform(0, 2 * math.pi)
            sx, sy = BX + r.uniform(-330, 330), bo.ty + r.uniform(60, 200)
            ang = j * 2 * math.pi / 7 + k
            tx, ty = kx + math.cos(ang) * 46, ky - 36 + math.sin(ang) * 46
            x = lerp(sx + 30 * math.sin(t * 2 + a0), tx, env)
            y = lerp(sy + 20 * math.cos(t * 2 + a0), ty, env)
            rr = 24 * pop(t, T_GRA - 0.2 + 0.03 * (k * 7 + j), 0.3)
            if t >= T_DES:
                rr *= 1 - 0.5 * prog(t, T_DES + 0.06 * k, 0.6, "in")
            if rr > 0.5:
                globulo(ctx, x, y, rr)


def d_boca2(ctx, t):
    def liquidos(ctx, bo):
        ya = _nivel(bo, t, T_AGU, 0.9, T_BOC + 0.15, 0.45, bo.ty + 30)
        liquido(ctx, bo, ya, AZUL_AGUA, 0.55, t)
        yl = _nivel(bo, t, T_LEC + 0.45, 0.9, T_DES + 0.2, 0.55, bo.ty + 50)
        liquido(ctx, bo, yl, (1, 1, 0.97), 0.78, t, borde=(1, 1, 1))
        globulos(ctx, bo, t)
        for k in range(len(D0)):
            x, y = _pos_llave_agua(bo, k, t)
            s = 0.2
            if t >= T_DES:
                s *= 1 - 0.6 * prog(t, T_DES + 0.06 * k, 0.6, "in")
            flota = T_TOM - 0.1 + 0.08 * k <= t < T_TOM + 1.9
            cara = "susto" if t >= T_ATR else ("feliz" if flota else "picara")
            llavecita(ctx, x, y - 4, s, rot=8 * math.sin(t * (9 if flota else 7) + k), cara=cara)

    zz = 1 + 0.03 * clamp((t - Z4[0]) / 11.0)
    ctx.save()
    camara(ctx, 540, 960, zz)
    bo0 = Boca(1.0)
    rec = [(_alarma_agua(bo0, i, t), 1.0) for i in range(len(REC))]
    boca_frente(ctx, t, a=1.0, rec=rec, liquido=liquidos)
    ctx.restore()
    # vaso de agua
    if T_MEZ - 0.3 <= t < T_BOC + 0.6:
        ap = pop(t, T_MEZ - 0.3, 0.35) * (1 - prog(t, T_BOC + 0.3, 0.3, "in"))
        inc = 115 * prog(t, T_MEZ + 0.1, 0.45) * (1 - prog(t, T_BOC - 0.2, 0.4))
        vaso(ctx, 300, 330, 1.0 * ap, inc, AZUL_AGUA, nivel=lerp(0.85, 0.25, prog(t, T_AGU, 2.4)))
        if inc > 70 and T_AGU - 0.1 <= t < T_BOC - 0.1:
            r_ = math.radians(inc)
            chorro(ctx, 300 + 120 * math.sin(r_), 330 - 120 * math.cos(r_), 520, 1000, AZUL_AGUA, 34, t)
    # vaso de leche
    if T_LEC - 0.25 <= t < T_GRA + 0.6:
        ap = pop(t, T_LEC - 0.25, 0.35) * (1 - prog(t, T_GRA + 0.3, 0.3, "in"))
        inc = -115 * prog(t, T_LEC + 0.05, 0.45) * (1 - prog(t, T_GRA - 0.2, 0.4))
        vaso(ctx, 780, 330, 1.0 * ap, inc, (1, 1, 0.98), nivel=lerp(0.85, 0.25, prog(t, T_LEC + 0.4, 1.8)),
             blanco=True)
        if inc < -70 and T_LEC + 0.4 <= t < T_GRA - 0.1:
            r_ = math.radians(inc)
            chorro(ctx, 780 + 120 * math.sin(r_), 330 - 120 * math.cos(r_), 600, 1010, (1, 1, 0.98), 34, t)
    # carteles
    if T_CAP <= t < T_MEZ - 0.1:
        a = 1 - prog(t, T_MEZ - 0.35, 0.25)
        cartel(ctx, "CAPSAICINA", 540, 770, 70, s=pop(t, T_CAP) * a, rot=-3)
        if a > 0.3:
            flecha(ctx, 540, 820, 540, 1005, t, curva=0, w=12, alpha=a)
    if T_BOC <= t < T_LEC + 0.3:
        sello(ctx, "AGUA", 330, 300, False, s=pop(t, T_BOC) * (1 - prog(t, T_LEC, 0.25, "in")))
    if T_GRA <= t < T_DES:
        a = 1 - prog(t, T_DES - 0.25, 0.25)
        cartel(ctx, "GRASA", 540, 770, 70, box=BLANCO, s=pop(t, T_GRA) * a, rot=3)
    if t >= T_LEN:
        sello(ctx, "LECHE", 760, 300, True, s=pop(t, T_LEN), rot=6)


# ------------------------------------------------------------------ 6. pájaros, semillas y el ratón
PLANTA_A = (700, 1.3)
PLANTA_B = (2250, 1.25)
NIDO = (400, 1185)                         # donde está parado el pájaro


def yg(x):
    return 1368 + 16 * math.sin(x * 0.0045) + 10 * math.sin(x * 0.011 + 1)


def suelo(ctx, x0, x1, fx):
    # colinas lejanas
    ctx.move_to(x0, 7000)
    for x in range(int(x0), int(x1) + 40, 40):
        xx = x + fx * 0.45
        ctx.line_to(x, 1250 + 50 * math.sin(xx * 0.003) + 30 * math.sin(xx * 0.0077 + 2))
    ctx.line_to(x1, 7000)
    ctx.close_path()
    ctx.set_source_rgba(*hx("#18305A"), 0.9)
    ctx.fill()
    ctx.move_to(x0, 7000)
    for x in range(int(x0), int(x1) + 20, 20):
        ctx.line_to(x, yg(x))
    ctx.line_to(x1, 7000)
    ctx.close_path()
    g = cairo.LinearGradient(0, 1340, 0, 2400)
    g.add_color_stop_rgb(0, *hx("#2A8A5A"))
    g.add_color_stop_rgb(1, *hx("#0E3330"))
    ctx.set_source(g)
    ctx.fill()
    for i, x in enumerate(range(int(x0), int(x1) + 20, 20)):
        (ctx.move_to if i == 0 else ctx.line_to)(x, yg(x))
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(12)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*hx("#4BD98A"))
    ctx.set_line_width(5)
    ctx.stroke()
    r = rng(3)
    for x in range(int(x0 // 90) * 90, int(x1), 90):
        xx = x + r.uniform(0, 50)
        y = yg(xx)
        ctx.move_to(xx - 14, y + 2)
        ctx.line_to(xx - 6, y - 26)
        ctx.line_to(xx, y + 2)
        ctx.line_to(xx + 8, y - 20)
        ctx.line_to(xx + 14, y + 2)
        ctx.set_source_rgb(*hx("#3CC27A"))
        ctx.fill()


_PB = PLANTA_B[0]
KF = [(B5[0], 560, 1050, 1.12), (T_PPE, 560, 1050, 1.12), (T_TRG + 2.3, 560, 1050, 1.12),
      (T_EXC + 0.25, _PB, 900, 1.0), (T_LEJ - 0.1, _PB, 1000, 1.0), (T_LEJ + 0.5, 1475, 820, 0.52),
      (T_CRE - 0.35, 1475, 820, 0.52), (T_CRE + 0.2, _PB, 1040, 1.0), (b(12) - 0.05, _PB, 1040, 1.0),
      (b(12) + 0.6, _PB - 200, 1120, 1.12), (b(13), _PB - 200, 1120, 1.12), (b(13) + 0.7, _PB - 20, 1010, 0.95),
      (TOTAL + 1, _PB - 20, 1010, 0.95)]


def cam_mundo(t):
    for (t0, x0, y0, z0), (t1, x1, y1, z1) in zip(KF, KF[1:]):
        if t0 <= t < t1:
            q = ease((t - t0) / (t1 - t0), "inout")
            return lerp(x0, x1, q), lerp(y0, y1, q), math.exp(lerp(math.log(z0), math.log(z1), q))
    return KF[-1][1:]


T_VUELO = T_MAS + 0.35
T_SUELTA = T_EXC + 0.12


def pajaro_xy(t):
    if t < T_VUELO:
        salto = 150 * math.sin(math.pi * clamp((t - T_CAL) / 0.75)) if T_CAL <= t < T_CAL + 0.75 else 0.0
        return NIDO[0], NIDO[1] - salto, False
    if t < T_SUELTA + 0.9:
        q = clamp((t - T_VUELO) / (T_EXC + 0.25 - T_VUELO))
        e = ease(q, "inout")
        x = lerp(NIDO[0], PLANTA_B[0], e)
        y = lerp(NIDO[1], 640, ease(min(1, q * 1.8), "out"))
        if t >= T_SUELTA:
            k = prog(t, T_SUELTA + 0.1, 0.8, "in")
            x += 900 * k
            y -= 300 * k
        return x, y, True
    if t >= T_ESP:
        q = prog(t, T_ESP + 0.1, 0.9, "out")
        return lerp(3500, PLANTA_B[0] + 30, q), lerp(600, yg(PLANTA_B[0]) - 360 * PLANTA_B[1] - 60, q), q < 0.97
    return None


def d_mundo(ctx, t):
    fx, fy, z = cam_mundo(t)
    calor_def = prog(t, T_EXI, 0.5) * (1 - prog(t, T_FIN, 0.2))
    fondo_azul(ctx, t)
    ctx.save()
    camara(ctx, fx, fy, z)
    x0, x1 = fx - 540 / z - 60, fx + 540 / z + 60
    if calor_def > 0:
        pul = 0.75 + 0.25 * math.sin(t * 6)
        _elipse_suave(ctx, PLANTA_B[0], yg(PLANTA_B[0]) - 230, 560, 560, ROJO_AL, 0.55 * pul * calor_def)
    suelo(ctx, x0, x1, fx)
    # planta A con sus ajíes
    pa = PLANTA_A[0]
    planta_aji(ctx, pa, yg(pa), PLANTA_A[1], 1.0, t, ajies=False)
    h = 360 * PLANTA_A[1]
    for i, (dx, fy_, rot) in enumerate(((70, -0.68, 80), (-40, -0.85, 110))):
        aji(ctx, pa + dx * PLANTA_A[1], yg(pa) + h * fy_ + 60 * PLANTA_A[1], 0.42 * PLANTA_A[1], rot=rot)
    # el ají que agarra el pájaro
    t_agarra = b(8) + 0.5
    aji_colgado = (pa - 78, yg(pa) - 0.5 * h + 78)
    st = pajaro_xy(t)
    if t < t_agarra:
        aji(ctx, aji_colgado[0], aji_colgado[1], 0.42 * PLANTA_A[1], rot=100)
    # planta B
    pb = PLANTA_B[0]
    if t >= T_CRE:
        planta_aji(ctx, pb, yg(pb), PLANTA_B[1], clamp((t - T_CRE) / 1.1), t)
    # excremento con semillas
    if t >= T_SUELTA and t < T_CRE + 0.6:
        bx_, by_, _ = pajaro_xy(T_SUELTA)
        q = clamp((t - T_SUELTA) / 0.55)
        gx = lerp(bx_, pb, q)
        gyy = lerp(by_ + 80, yg(pb) - 20, q * q)
        a = 1 - prog(t, T_CRE + 0.1, 0.4)
        ctx.save()
        ctx.translate(gx, gyy)
        sq = 1 + 0.4 * clamp((t - T_SUELTA - 0.55) / 0.08) * (1 - clamp((t - T_SUELTA - 0.63) / 0.2))
        ctx.scale(sq, 1 / sq)
        ctx.push_group()
        for dx, dy, r in ((0, 0, 42), (-28, 14, 30), (28, 14, 30), (0, -26, 28)):
            ctx.arc(dx, dy, r, 0, 2 * math.pi)
            ctx.new_sub_path()
        ctx.set_source_rgb(*hx("#F2F0E6"))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5)
        ctx.stroke()
        for dx, dy in ((-14, 4), (14, 10), (2, -16)):
            semilla(ctx, dx, dy, 0.6)
        ctx.pop_group_to_source()
        ctx.paint_with_alpha(a)
        ctx.restore()
    # flecha de distancia
    if T_LEJ + 0.3 <= t < T_CRE:
        a = prog(t, T_LEJ + 0.3, 0.3) * (1 - prog(t, T_CRE - 0.35, 0.2))
        ctx.set_dash([40, 30])
        ctx.move_to(pa + 160, 1000)
        ctx.line_to(pb - 160, 1000)
        ctx.set_source_rgba(1, 1, 1, 0.9 * a)
        ctx.set_line_width(14)
        ctx.stroke()
        ctx.set_dash([])
        for xx, sg in ((pa + 160, -1), (pb - 160, 1)):
            ctx.move_to(xx - sg * 50, 950)
            ctx.line_to(xx, 1000)
            ctx.line_to(xx - sg * 50, 1050)
            ctx.set_source_rgba(1, 1, 1, 0.9 * a)
            ctx.set_line_width(14)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke()
    # ratón
    if b(12) - 0.2 <= t < T_ESP + 1.2:
        aji_suelo = (pb - 150, yg(pb - 150) - 28)
        come = prog(t, T_RMA, 1.2)
        if come < 0.98:
            aji(ctx, aji_suelo[0], aji_suelo[1], 0.5 * (1 - 0.6 * come), rot=-10, mordida=come)
        q = prog(t, b(12) - 0.1, 0.9, "out")
        hu = prog(t, T_ESP, 0.7, "in")
        rx = lerp(1700, aji_suelo[0] - 190, q) - 1400 * hu
        rojo = prog(t, T_RMA + 0.7, 0.5)
        raton(ctx, rx, yg(rx) - 135, 0.95, t, mastica=(T_RMA <= t < T_RDE + 0.2), rojo=rojo)
        if rojo > 0 and hu < 0.5:
            vapor(ctx, rx + 20, yg(rx) - 230, t, T_RMA + 0.7, -1)
            vapor(ctx, rx + 120, yg(rx) - 230, t, T_RMA + 0.7, 1)
        if t >= T_RMA:
            r = rng(5)
            for k in range(14):
                ph = r.uniform(0, 0.9)
                if t < T_RMA + ph:
                    continue
                qq = clamp((t - T_RMA - ph) / 0.7)
                ang = r.uniform(-1.3, 0.2)
                x = aji_suelo[0] - 40 + math.cos(ang) * 230 * qq
                y = aji_suelo[1] - 30 + math.sin(ang) * 220 * qq + 300 * qq * qq
                y = min(y, yg(x) - 10)
                semilla(ctx, x, y, 1.1, rot=k, rota=clamp(qq * 3))
    # pájaro
    if st is not None:
        bx, by, vuela = st
        con_aji = t_agarra <= t < T_TRG + 0.3
        trago = prog(t, T_TRG, 0.35, "in")
        xr = prog(t, T_TRG + 0.2, 0.3) * (1 - prog(t, T_SUELTA, 0.3))
        ojos = "feliz"
        if T_CAL <= t < T_CAL + 0.9:
            ojos = "grande"
        elif vuela:
            ojos = "normal"
        picot = 0.0
        if t_agarra - 0.35 <= t < t_agarra:
            picot = math.sin(math.pi * (t - t_agarra + 0.35) / 0.35)
        s_p = 1.0 if t < T_ESP else 0.8
        ale = 0.9 * math.sin(t * 22) if vuela else (0.6 if T_CAL <= t < T_CAL + 0.75 else 0.0)
        pajaro(ctx, bx + 30 * picot, by + 20 * picot, s_p, t, aleteo=ale, pico=0.5 * picot + (0.4 if con_aji else 0),
               ojos=ojos, xray=xr, semillas=7, vuelo=vuela)
        if con_aji:
            ax = bx + 180 + 100 * 0.45
            ay = by - 20
            aji(ctx, lerp(ax, bx + 20, trago), lerp(ay, by + 30, trago), 0.45 * (1 - 0.7 * trago), rot=lerp(0, 40, trago))
        # el sensor del pájaro
        if t < T_TRG:
            sa = pop(t, B5[0] + 0.5, 0.35) * (1 - prog(t, T_TRG - 0.3, 0.25))
            al = clamp((t - T_CAL - 0.05) / 0.1) * (1 - clamp((t - T_CAL - 0.9) / 0.3))
            sx_, sy_ = bx, by - 300
            if sa > 0.01:
                ctx.set_dash([10, 12])
                ctx.move_to(bx + 60, by - 80)
                ctx.line_to(sx_, sy_ + 40)
                ctx.set_source_rgba(1, 1, 1, 0.7 * sa)
                ctx.set_line_width(5)
                ctx.stroke()
                ctx.set_dash([])
                zocalo(ctx, sx_, sy_, 62, 24, al, t, forma="estrella", s=sa)
                if t >= T_PQU and al < 0.1:
                    sello_mini(ctx, sx_ + 95, sy_ - 30, True, pop(t, T_PQU, 0.3) * (1 - prog(t, T_CAL - 0.2, 0.2)))
    # llama de prueba
    if T_CAL - 0.15 <= t < T_CAL + 1.1:
        llama(ctx, NIDO[0] - 190, yg(NIDO[0] - 190) - 50, 0.8 * pop(t, T_CAL - 0.15, 0.2) * (1 - prog(t, T_CAL + 0.8, 0.3)), t)
    ctx.restore()
    # recuadro: la cerradura del pájaro
    if T_PPE - 0.05 <= t < B5[0] + 8.0 and t < T_TRG + 0.2:
        ap = pop(t, T_PPE - 0.05, 0.35) * (1 - prog(t, T_TRG - 0.25, 0.3, "in"))
        recuadro_pajaro(ctx, t, ap)
    if t >= T_RDE and t < b(13) + 0.6:
        sello(ctx, "SEMILLAS\nDESTRUIDAS", 540, 330, False, s=pop(t, T_RDE) * (1 - prog(t, b(13) + 0.3, 0.25, "in")),
              rot=-5)
    pill(ctx, "UNA DEFENSA", 540, 300, t, T_EXI, size=92, box=ROJO_AL, fg=BLANCO)


def sello_mini(ctx, x, y, ok, s):
    if s <= 0.01:
        return
    col = hx("#2BB24C") if ok else ROJO_AL
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    ctx.arc(0, 0, 40, 0, 2 * math.pi)
    ctx.set_source_rgb(*col)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.move_to(-18, 2)
    ctx.line_to(-4, 17)
    ctx.line_to(20, -15)
    ctx.set_source_rgb(*BLANCO)
    ctx.set_line_width(10)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ctx.restore()


def recuadro_pajaro(ctx, t, ap):
    if ap <= 0.01:
        return
    cx, cy, R = 540, 600, 300
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(ap, ap)
    ctx.arc(0, 12, R + 12, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.fill()
    ctx.arc(0, 0, R + 12, 0, 2 * math.pi)
    ctx.set_source_rgb(*BLANCO)
    ctx.fill()
    ctx.restore()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(ap, ap)
    ctx.arc(0, 0, R, 0, 2 * math.pi)
    ctx.clip()
    g = cairo.LinearGradient(0, -R, 0, R)
    g.add_color_stop_rgb(0, *hx("#0E1640"))
    g.add_color_stop_rgb(1, *hx("#1E2E6E"))
    ctx.set_source(g)
    ctx.paint()
    zocalo(ctx, 0, 150, 190, 72, 0.0, t, forma="estrella")
    # la llave intenta entrar y rebota
    t_llega, t_toca = T_PLL - 0.2, T_PEN + 0.05
    tip_y = 150 + 6
    if t < t_toca:
        q = prog(t, t_llega, t_toca - t_llega - 0.15, "out")
        x = lerp(-420, 0, q)
        y = tip_y - 130 - 40 * abs(math.sin(q * math.pi * 3)) * (1 - q)
        if t >= t_toca - 0.15:
            y = lerp(tip_y - 130, tip_y - 8, ease((t - t_toca + 0.15) / 0.15, "in"))
        rot, cara = 0.0, "picara"
    else:
        q = prog(t, t_toca, 0.5, "out")
        x = lerp(0, -150, q)
        y = tip_y - 8 - 120 * math.sin(math.pi * min(1, q * 1.2)) + 40 * q
        rot = lerp(0, -30, q)
        cara = "enojo"
    llavecita(ctx, x, y, 0.62, rot=rot, cara=cara)
    if t >= t_toca + 0.05:
        prohibido(ctx, 120, 40, 62, pop(t, t_toca + 0.05, 0.25))
    ctx.restore()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(ap, ap)
    ctx.arc(0, 0, R, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.restore()
    if t >= t_toca + 0.1:
        cartel(ctx, "NO ENCAJA", 540, 960, 84, box=ROJO_AL, fg=BLANCO, s=pop(t, t_toca + 0.1) * ap, rot=3)


# ------------------------------------------------------------------ 7. "como tú": la boca muerde
MORD = [T_TU + 0.02, T_TU + 0.36]          # los dos mordiscos


def mandibula(t):
    """Apertura de la boca (1 = abierta) durante los mordiscos."""
    a = 1.0
    m1, m2 = MORD
    cerrada = 0.11                          # los dientes se clavan en el ají
    if t >= m1:
        a = lerp(1.0, cerrada, prog(t, m1, 0.1, "in"))
    if t >= m1 + 0.12:
        a = lerp(cerrada, 0.36, prog(t, m1 + 0.12, 0.12, "out"))
    if t >= m2:
        a = lerp(0.36, cerrada - 0.02, prog(t, m2, 0.09, "in"))
    return a


def d_mordida(ctx, t):
    a = mandibula(t)
    rotura = 0.35 * clamp((t - MORD[0] - 0.08) / 0.05) + 0.35 * clamp((t - MORD[1] - 0.07) / 0.05)

    def entre(ctx, bo):
        ya = bo.top_in(BX) + 18 + 104 + 4
        yb = bo.bot_in(BX) - 16 - 56
        gap = yb - ya
        grosor = 96
        sq = clamp(max(gap, 62) / grosor, 0, 1)
        ctx.save()
        ctx.translate(BX - 30 + 4 * math.sin(t * 9), ya + min(grosor / 2, max(gap, 62) / 2))
        ctx.scale(1.0 + 0.25 * (1 - sq), sq)
        aji(ctx, 0, 0, 1.25, rot=0, mordida=rotura)
        ctx.restore()

    sac = 0.0
    for m in MORD:
        if m + 0.08 <= t < m + 0.4:
            sac = 12 * math.sin(t * 80) * (1 - (t - m - 0.08) / 0.32)
    ctx.save()
    camara(ctx, 540, 960, 1.0, 540 + sac, 960)
    boca_frente(ctx, t, a=max(a, 0.0), rec=[(0.0, 1.0)] * len(REC), entre_dientes=entre)
    ctx.restore()
    for j, m in enumerate(MORD):
        if t < m + 0.08:
            continue
        q = clamp((t - m - 0.08) / 0.6)
        r = rng(8 + j)
        for k in range(14):
            ang = r.uniform(0.15, math.pi - 0.15) * (1 if k % 2 else -1)
            v = r.uniform(260, 560)
            x = 540 + math.cos(ang) * v * q
            y = 700 + math.sin(ang) * v * 0.6 * q + 700 * q * q
            if k % 3 == 0:
                semilla(ctx, x, y, 1.5, rot=k)
            else:
                ctx.arc(x, y, 15 * (1 - q * 0.5), 0, 2 * math.pi)
                ctx.set_source_rgb(*ROJO)
                ctx.fill_preserve()
                ctx.set_source_rgb(*INK)
                ctx.set_line_width(4)
                ctx.stroke()
    if t >= MORD[1] + 0.08:
        q = clamp((t - MORD[1] - 0.08) / 0.9)
        vineta_roja(ctx, (1 - 0.4 * q) * (0.75 + 0.25 * math.sin(t * 16)))


# ------------------------------------------------------------------ composición
def barrido(ctx, q, A, tA, B, tB):
    k = ease(q, "inout")
    for fn, dx in ((A, -1080 * k), (B, 1080 * (1 - k))):
        ctx.save()
        ctx.rectangle(dx, 0, W, H)
        ctx.clip()
        ctx.translate(dx, 0)
        fn(ctx, tB if fn is B else tA)
        ctx.restore()
    # estela del barrido
    a = math.sin(math.pi * q)
    r = rng(2)
    for k_ in range(14):
        y = r.uniform(0, H)
        x = r.uniform(0, W)
        ctx.move_to(x, y)
        ctx.line_to(x + 500, y)
        ctx.set_source_rgba(1, 1, 1, 0.12 * a)
        ctx.set_line_width(r.uniform(4, 14))
        ctx.stroke()


def componer(ctx, t):
    def tr(T):
        return clamp((t - T[0]) / T[1])
    if t < Z1[0]:
        d_gancho(ctx, t)
    elif t < sum(Z1):
        zoom_entre(ctx, tr(Z1), d_gancho, t, VOS_BOCA, d_boca1, t, BOCA_C, 12.8)
    elif t < Z2[0]:
        d_boca1(ctx, t)
    elif t < sum(Z2):
        x, y = Boca(1.0).rec(R_STAR)
        zoom_entre(ctx, tr(Z2), d_boca1, t, (x, y), d_cerradura, t, SOCK, 9.5)
    elif t < Z3[0]:
        d_cerradura(ctx, t)
    elif t < sum(Z3):
        zoom_entre(ctx, 1 - tr(Z3), d_cuerpo, t, BADGE_STAR, d_cerradura, t, SOCK, 26.0, a0=0.45, a1=0.85)
    elif t < Z4[0]:
        d_cuerpo(ctx, t)
    elif t < sum(Z4):
        zoom_entre(ctx, tr(Z4), d_cuerpo, t, CARA_BOCA, d_boca2, t, BOCA_C, 14.0)
    elif t < B5[0]:
        d_boca2(ctx, t)
    elif t < sum(B5):
        barrido(ctx, tr(B5), d_boca2, t, d_mundo, t)
    elif t < T_FIN:
        d_mundo(ctx, t)
    else:
        q = prog(t, T_FIN, 0.26, "out")
        d_mundo(ctx, t)
        ctx.rectangle(0, 0, W, H)
        ctx.set_source_rgba(0, 0, 0, 0.5 * q)
        ctx.fill()
        e = max(motor.ease("back", clamp((t - T_FIN) / 0.26)), 0.0)
        z = lerp(0.2, 1.0, e)
        ctx.save()
        ctx.arc(540, 945, lerp(120, 1250, clamp(e)), 0, 2 * math.pi)
        ctx.clip()
        capa(ctx, d_mordida, t, cam=(540, 945, max(z, 0.05), 540, 945))
        ctx.restore()


CAPS = motor.Captions(WORDS, {"size": 76, "y": 1470, "max_palabras": 3, "max_letras": 18})


def cuadro(t):
    s, ctx = lienzo()
    try:
        componer(ctx, t)
    except Exception as e:
        raise RuntimeError(f"falló el cuadro en t={t:.3f}: {e}") from e
    im = Image.fromarray(a_rgb(s))
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



def s_zap(d=0.3):
    """Chispazo eléctrico corto: el sensor que se activa."""
    n = int(d * SR)
    t = np.arange(n) / SR
    r = np.random.default_rng(13)
    zumb = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.4 + np.sin(2 * np.pi * 880 * t * (1 + 0.3 * t)) * 0.3
    ruido = r.standard_normal(n).astype(np.float32) * 0.35
    env = np.exp(-t * 11) * (0.7 + 0.3 * np.sign(np.sin(2 * np.pi * 37 * t)))
    return ((zumb + ruido) * env * 0.6).astype(np.float32)


def sonido_picante(kind, **kw):
    if kind == "zap":
        return s_zap(**kw)
    return snd(kind, **kw)


def eventos():
    E = []

    def ev(t, k, v=1.0, **kw):
        E.append((t, k, v, kw))

    # gancho: la alarma suena una sola vez
    ev(T_BITE - 0.05, "crunch", 0.9, d=0.35)
    ev(T_QUEMA, "boing", 0.7)
    ev(T_QUEMA + 0.1, "siseo", 0.45, d=1.1)
    ev(T_ALARMA, "alarma", 0.5, d=1.0)
    ev(T_SIN, "pop", 0.8)
    # adentro de la boca
    ev(Z1[0], "zoom", 0.9)
    for i in range(len(REC)):
        ev(T_SENS + i * 0.05, "tick", 0.22, f=1400 + i * 60, d=0.05)
    ev(T_QUE - 0.15, "pop", 0.5)
    ev(T_QUE, "subida", 0.5, d=T_43 - T_QUE)
    ev(T_43, "zap", 0.8)
    ev(T_AJI - 0.1, "whoosh_suave", 0.6)
    ev(T_AJI + 0.32, "plop", 0.8)
    for i in range(len(LLAVES1)):
        ev(T_SUS + 0.06 + i * 0.05, "pop", 0.35)
    # la llave falsa
    ev(Z2[0], "zoom", 0.8)
    ev(T_JUS + 0.1, "click", 0.9)
    ev(T_JUS + 0.42, "clic", 1.0)
    ev(T_JUS + 0.76, "zap", 0.9)
    ev(T_LLA, "pop", 0.8)
    # cerebro y cuerpo
    ev(Z3[0], "whoosh", 0.7)
    ev(T_CER - 0.1, "pop", 0.6)
    ev(T_REC, "chispa", 0.45, d=0.6, seed=2)
    ev(T_SEN, "pop", 0.7)
    ev(T_CAF - 0.2, "pop", 0.6)
    ev(T_CAF + 0.1, "chispa", 0.45, d=0.6, seed=3)
    ev(T_NI, "ding", 0.8)
    ev(b(5) - 0.2, "whoosh_suave", 0.6)
    ev(T_TRA - 0.1, "boing", 0.6)
    ev(T_ROJ, "siseo", 0.4, d=0.9)
    ev(T_LLO, "plop", 0.5)
    ev(T_APA, "vertido", 0.55, d=T_NOE - T_APA)
    ev(T_NOE + 0.15, "pop", 0.8)
    # agua y leche
    ev(Z4[0], "zoom", 0.8)
    ev(T_CAP, "pop", 0.7)
    ev(T_MEZ - 0.3, "pop", 0.5)
    ev(T_AGU - 0.1, "vertido", 0.8, d=T_BOC - T_AGU)
    ev(T_BOC, "boing", 0.6)
    ev(T_BOC + 0.3, "trago", 0.9)
    ev(T_LEC - 0.25, "pop", 0.5)
    ev(T_LEC + 0.4, "vertido", 0.7, d=T_GRA - T_LEC - 0.5)
    for k in range(5):
        ev(T_GRA - 0.2 + k * 0.08, "pop", 0.3)
    ev(T_DES, "whoosh_suave", 0.7)
    ev(T_DES + 0.5, "trago", 0.9)
    ev(T_LEN, "ding", 0.8)
    # pájaros
    ev(B5[0], "whoosh", 0.8)
    ev(b(8) + 0.4, "pop", 0.5)
    ev(T_PQU, "ding", 0.6)
    ev(T_CAL - 0.15, "siseo", 0.4, d=0.8)
    ev(T_CAL, "boing", 0.8)
    ev(T_CAL + 0.05, "zap", 0.5)
    ev(T_PPE - 0.05, "zoom", 0.6)
    ev(T_PEN + 0.05, "clunk", 1.0)
    ev(T_TRG, "trago", 1.0)
    ev(T_SEM, "pop", 0.5)
    ev(T_VUELO, "aleteo", 0.8, d=2.4)
    ev(T_SUELTA + 0.55, "plop", 1.0)
    ev(T_LEJ, "whoosh_suave", 0.6)
    ev(T_CRE, "brote", 0.8, d=1.1)
    ev(T_NUE, "pop", 0.7)
    ev(b(12) - 0.1, "whoosh_suave", 0.5)
    ev(T_RMA, "crunch", 1.0, d=1.3, seed=3)
    ev(T_RDE, "boing", 0.7)
    ev(T_EXI, "pop", 0.8)
    ev(T_ESP, "golpe", 0.8)
    ev(T_ESP + 0.05, "whoosh", 0.6)
    ev(T_ESP + 0.15, "aleteo", 0.5, d=0.9)
    # "como tú": la alarma vuelve a sonar, corta
    ev(T_FIN, "whoosh", 0.9)
    ev(MORD[0] + 0.08, "crunch", 1.0, d=0.25, seed=9)
    ev(MORD[1] + 0.07, "crunch", 1.0, d=0.25, seed=11)
    ev(MORD[1] + 0.1, "alarma", 0.45, d=0.6)
    return E
def pista_efectos():
    n = int((TOTAL + 2) * SR)
    mix = np.zeros(n, np.float32)
    for t, k, v, kw in eventos():
        x = sonido_picante(k, **kw) * v
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
